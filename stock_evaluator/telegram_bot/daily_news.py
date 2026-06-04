from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import escape, unescape
from urllib import parse, request
from xml.etree import ElementTree

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from stock_evaluator.companies.models import Company
from stock_evaluator.reports.llm_client import LocalLLMClientError, chat_completion
from stock_evaluator.reports.llm_explainer import LocalLLMExplanationError
from stock_evaluator.telegram_bot.models import DailyCompanyNewsAnalysis, NewsArticle
from stock_evaluator.users.models import TelegramUser, WatchlistItem


ARTICLES_PER_SOURCE = 5
REPORT_MESSAGE_CHUNK_SIZE = 3900
LOCAL_LLM_LIMITATION_NOTICE = (
    "로컬 LLM 해석은 제한된 RSS 입력과 모델 성능에 따른 자동 요약입니다. "
    "기사 원문, 공시, 가격 데이터를 직접 확인해야 합니다."
)


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

    analyses: list[DailyCompanyNewsAnalysis] = []
    for item in items:
        analyses.append(get_or_create_company_news_analysis(item.company, report_date))

    return _combined_user_report(analyses, report_date)


def get_or_create_company_news_analysis(company: Company, report_date) -> DailyCompanyNewsAnalysis:
    existing = DailyCompanyNewsAnalysis.objects.filter(company=company, report_date=report_date).first()
    if existing:
        return existing

    articles = _company_articles_for_report(company, report_date)
    try:
        llm_summary = _generate_company_news_analysis(company, articles, report_date)
    except LocalLLMExplanationError as exc:
        llm_summary = None
        error_message = str(exc) or exc.__class__.__name__
    else:
        error_message = ""

    if llm_summary:
        message = escape(llm_summary)
        status = DailyCompanyNewsAnalysis.Status.SUCCEEDED
    else:
        message = _fallback_company_report(company, articles)
        status = DailyCompanyNewsAnalysis.Status.FALLBACK

    try:
        return DailyCompanyNewsAnalysis.objects.create(
            company=company,
            report_date=report_date,
            message=message,
            status=status,
            error_message=error_message,
        )
    except IntegrityError:
        return DailyCompanyNewsAnalysis.objects.get(company=company, report_date=report_date)


def send_telegram_message(bot_token: str, chat_id: int, text: str) -> None:
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for start in range(0, len(text), REPORT_MESSAGE_CHUNK_SIZE):
        payload = parse.urlencode(
            {
                "chat_id": chat_id,
                "text": text[start : start + REPORT_MESSAGE_CHUNK_SIZE],
                "parse_mode": "HTML",
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


def _company_articles_for_report(company: Company, report_date) -> list[NewsArticle]:
    return list(
        NewsArticle.objects.filter(
            company=company,
            fetched_at__date=report_date,
        ).order_by("-published_at", "-fetched_at")[: ARTICLES_PER_SOURCE * 3]
    )


def _generate_company_news_analysis(company: Company, articles: list[NewsArticle], report_date) -> str | None:
    if not settings.LOCAL_LLM_MODEL:
        return None

    prompt = _company_news_prompt(company, articles, report_date)
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
    try:
        body = chat_completion(payload, timeout_seconds=settings.DAILY_NEWS_LLM_TIMEOUT_SECONDS)
    except LocalLLMClientError as exc:
        raise LocalLLMExplanationError("로컬 LLM 호출에 실패했습니다.") from exc

    content = body.get("message", {}).get("content", "").strip()
    return content or None


def _company_news_prompt(company: Company, articles: list[NewsArticle], report_date) -> str:
    lines = [
        f"{report_date} 기준 {company.ticker} / {company.name} 뉴스 분석을 한국어로 작성해줘.",
        "형식은 아래 구조를 유지해.",
        "",
        f"{company.ticker} / {company.name}",
        "- 주요 뉴스:",
        "- 투자 관점 해석:",
        "- 확인할 리스크:",
        "",
        "규칙:",
        "- 짧고 구체적으로 써.",
        "- 기사에 없는 내용은 추측하지 마.",
        "- 매수/매도 추천, 목표가, 주문 지시는 쓰지 마.",
        "- 기사 링크를 1~3개 포함해.",
        "",
        "기사:",
    ]
    if not articles:
        lines.append("- 새로 수집된 기사 없음")
    for article in articles:
        lines.append(f"- [{article.source}] {article.title} ({article.url})")
        if article.summary:
            lines.append(f"  요약: {article.summary[:300]}")
    return "\n".join(lines)


def _combined_user_report(analyses: list[DailyCompanyNewsAnalysis], report_date) -> str:
    lines = [f"[오늘의 워치리스트 뉴스] {escape(str(report_date))}", ""]
    fallback_count = 0
    for analysis in analyses:
        lines.append(analysis.message)
        lines.append("")
        if analysis.status == DailyCompanyNewsAnalysis.Status.FALLBACK:
            fallback_count += 1
    if fallback_count:
        lines.append(f"참고: {fallback_count}개 종목은 로컬 LLM 분석에 실패해 기사 목록으로 대체했습니다.")
    if any(analysis.status == DailyCompanyNewsAnalysis.Status.SUCCEEDED for analysis in analyses):
        lines.extend(["", "로컬 모델 한계", LOCAL_LLM_LIMITATION_NOTICE])
    return "\n".join(lines).strip()


def _fallback_company_report(company: Company, articles: list[NewsArticle]) -> str:
    lines = [f"{escape(company.ticker)} / {escape(company.name)}"]
    if not articles:
        lines.append("- 새로 수집된 기사 없음")
    else:
        for article in articles[: ARTICLES_PER_SOURCE * 3]:
            source = escape(article.source)
            title = escape(article.title)
            url = escape(article.url, quote=True)
            lines.append(f'- [{source}] <a href="{url}">{title}</a>')
    return "\n".join(lines).strip()
