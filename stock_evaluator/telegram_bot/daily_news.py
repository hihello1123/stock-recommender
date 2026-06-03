import json
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib import parse, request
from xml.etree import ElementTree

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from stock_evaluator.companies.models import Company
from stock_evaluator.reports.llm_explainer import LocalLLMExplanationError
from stock_evaluator.telegram_bot.models import NewsArticle
from stock_evaluator.users.models import TelegramUser, WatchlistItem


ARTICLES_PER_SOURCE = 5
REPORT_MESSAGE_CHUNK_SIZE = 3900


class NewsFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeedArticle:
    source: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None


def fetch_watchlist_news(*, per_source: int = ARTICLES_PER_SOURCE) -> tuple[int, list[str]]:
    saved_count = 0
    errors: list[str] = []
    companies = (
        Company.objects.filter(watchlist_items__isnull=False)
        .distinct()
        .order_by("ticker")
    )
    for company in companies:
        articles, company_errors = fetch_company_news(company, per_source=per_source)
        errors.extend(company_errors)
        for article in articles:
            try:
                _, created = NewsArticle.objects.get_or_create(
                    url=article.url,
                    defaults={
                        "company": company,
                        "source": article.source,
                        "title": article.title[:500],
                        "summary": article.summary,
                        "published_at": article.published_at,
                    },
                )
            except IntegrityError:
                created = False
            if created:
                saved_count += 1
    return saved_count, errors


def fetch_company_news(company: Company, *, per_source: int = ARTICLES_PER_SOURCE) -> tuple[list[FeedArticle], list[str]]:
    specs = [
        ("google_news", _google_news_url(company), _company_keywords(company)),
        ("yahoo_finance", _yahoo_finance_url(company), []),
        ("investing", _investing_news_url(), _company_keywords(company)),
    ]
    articles: list[FeedArticle] = []
    errors: list[str] = []
    for source, url, keywords in specs:
        try:
            source_articles = _fetch_feed(source, url)
        except NewsFetchError as exc:
            errors.append(f"{company.ticker} {source}: {exc}")
            continue
        filtered = _filter_articles(source_articles, keywords)
        articles.extend(filtered[:per_source])
    return articles, errors


def build_daily_watchlist_report(user: TelegramUser, *, report_date=None) -> str:
    report_date = report_date or timezone.localdate()
    items = list(
        WatchlistItem.objects.filter(user=user)
        .select_related("company")
        .order_by("company__ticker")
    )
    if not items:
        return ""

    grouped: list[tuple[Company, list[NewsArticle]]] = []
    for item in items:
        articles = list(
            NewsArticle.objects.filter(
                company=item.company,
                fetched_at__date=report_date,
            ).order_by("-published_at", "-fetched_at")[: ARTICLES_PER_SOURCE * 3]
        )
        grouped.append((item.company, articles))

    try:
        llm_summary = _generate_daily_news_analysis(grouped, report_date)
    except LocalLLMExplanationError:
        llm_summary = None
    if llm_summary:
        return llm_summary
    return _fallback_report(grouped, report_date)


def send_telegram_message(bot_token: str, chat_id: int, text: str) -> None:
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for start in range(0, len(text), REPORT_MESSAGE_CHUNK_SIZE):
        payload = parse.urlencode(
            {
                "chat_id": chat_id,
                "text": text[start : start + REPORT_MESSAGE_CHUNK_SIZE],
                "disable_web_page_preview": "true",
            }
        ).encode()
        http_request = request.Request(api_url, data=payload, method="POST")
        with request.urlopen(http_request, timeout=30) as response:
            response.read()


def _fetch_feed(source: str, url: str) -> list[FeedArticle]:
    http_request = request.Request(
        url,
        headers={"User-Agent": "stock-recommender/0.1"},
    )
    try:
        with request.urlopen(http_request, timeout=settings.DAILY_NEWS_RSS_TIMEOUT_SECONDS) as response:
            body = response.read()
    except OSError as exc:
        raise NewsFetchError(str(exc) or exc.__class__.__name__) from exc

    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise NewsFetchError("RSS 파싱에 실패했습니다.") from exc

    articles: list[FeedArticle] = []
    for item in root.findall(".//item"):
        title = _node_text(item, "title")
        url = _node_text(item, "link")
        if not title or not url:
            continue
        articles.append(
            FeedArticle(
                source=source,
                title=title,
                url=url,
                summary=_node_text(item, "description"),
                published_at=_parse_rss_datetime(_node_text(item, "pubDate")),
            )
        )
    return articles


def _node_text(item, tag: str) -> str:
    node = item.find(tag)
    if node is None or node.text is None:
        return ""
    return unescape(node.text).strip()


def _parse_rss_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _filter_articles(articles: list[FeedArticle], keywords: list[str]) -> list[FeedArticle]:
    if not keywords:
        return articles
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    filtered = []
    for article in articles:
        haystack = f"{article.title} {article.summary}".lower()
        if any(keyword in haystack for keyword in lowered_keywords):
            filtered.append(article)
    return filtered


def _company_keywords(company: Company) -> list[str]:
    keywords = [company.ticker, company.name]
    if company.sector:
        keywords.append(company.sector)
    return keywords


def _google_news_url(company: Company) -> str:
    query = f'"{company.name}" OR {company.ticker} stock'
    return "https://news.google.com/rss/search?" + parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    )


def _yahoo_finance_url(company: Company) -> str:
    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={parse.quote(company.ticker)}&region=US&lang=en-US"


def _investing_news_url() -> str:
    return "https://www.investing.com/rss/news_25.rss"


def _generate_daily_news_analysis(grouped: list[tuple[Company, list[NewsArticle]]], report_date) -> str | None:
    if not settings.LOCAL_LLM_MODEL:
        return None

    prompt = _daily_news_prompt(grouped, report_date)
    payload = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 미국 주식 워치리스트 뉴스를 요약하는 투자 리서치 보조자다. "
                    "매수/매도 추천, 목표가, 주문 지시는 절대 쓰지 않는다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    api_url = settings.LOCAL_LLM_BASE_URL.rstrip("/") + "/api/chat"
    http_request = request.Request(
        api_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=settings.DAILY_NEWS_LLM_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise LocalLLMExplanationError("로컬 LLM 호출에 실패했습니다.") from exc

    content = body.get("message", {}).get("content", "").strip()
    return content or None


def _daily_news_prompt(grouped: list[tuple[Company, list[NewsArticle]]], report_date) -> str:
    lines = [
        f"{report_date} 기준 워치리스트 뉴스 리포트를 한국어로 작성해줘.",
        "형식은 아래 구조를 유지해.",
        "",
        "[오늘의 워치리스트 뉴스]",
        "전체 요약:",
        "",
        "TICKER / 회사명",
        "- 주요 뉴스:",
        "- 투자 관점 해석:",
        "- 확인할 리스크:",
        "",
        "규칙:",
        "- 짧고 구체적으로 써.",
        "- 기사에 없는 내용은 추측하지 마.",
        "- 매수/매도 추천, 목표가, 주문 지시는 쓰지 마.",
        "- 각 종목마다 기사 링크를 1~3개 포함해.",
        "",
        "기사:",
    ]
    for company, articles in grouped:
        lines.append(f"\n{company.ticker} / {company.name}")
        if not articles:
            lines.append("- 새로 수집된 기사 없음")
            continue
        for article in articles:
            lines.append(f"- [{article.source}] {article.title} ({article.url})")
            if article.summary:
                lines.append(f"  요약: {article.summary[:300]}")
    return "\n".join(lines)


def _fallback_report(grouped: list[tuple[Company, list[NewsArticle]]], report_date) -> str:
    lines = [f"[오늘의 워치리스트 뉴스] {report_date}", ""]
    for company, articles in grouped:
        lines.append(f"{company.ticker} / {company.name}")
        if not articles:
            lines.append("- 새로 수집된 기사 없음")
        else:
            for article in articles[: ARTICLES_PER_SOURCE * 3]:
                lines.append(f"- [{article.source}] {article.title}")
                lines.append(f"  {article.url}")
        lines.append("")
    lines.append("로컬 LLM 분석을 사용할 수 없어 기사 목록만 보냅니다.")
    return "\n".join(lines).strip()
