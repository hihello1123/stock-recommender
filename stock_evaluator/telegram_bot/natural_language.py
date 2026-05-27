import json
import re
from dataclasses import dataclass
from urllib import request

from django.conf import settings

from stock_evaluator.reports.llm_explainer import INVESTOR_LABELS, LocalLLMExplanationError


INTENTS = {
    "search_ticker",
    "analyze_company",
    "add_watchlist",
    "remove_watchlist",
    "show_watchlist",
    "help",
    "unknown",
}

SENSITIVE_TERMS = [
    "api key",
    "apikey",
    "password",
    "token",
    "비밀번호",
    "암호",
    "주민번호",
    "전화번호",
    "휴대폰",
    "주소",
    "계좌",
    "카드번호",
    "신용카드",
    "토큰",
    "인증번호",
]

STOCK_ROUTING_TERMS = [
    "ticker",
    "watch",
    "stock",
    "company",
    "티커",
    "주식",
    "종목",
    "회사",
    "검색",
    "찾아",
    "분석",
    "관심종목",
    "관심",
    "추가",
    "제거",
    "삭제",
    "빼줘",
    "보여",
    "목록",
    "버핏",
    "그레이엄",
    "린치",
    "멍거",
]

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}(?:[.-][A-Z]{1,3})?\b")


@dataclass(frozen=True)
class NaturalLanguageRoute:
    intent: str
    query: str = ""
    ticker: str = ""
    investor: str = ""


def route_natural_language_message(text: str) -> NaturalLanguageRoute:
    cleaned_text = text.strip()
    if not cleaned_text:
        return NaturalLanguageRoute(intent="unknown")
    if not should_route_to_llm(cleaned_text):
        return NaturalLanguageRoute(intent="unknown")
    if not settings.LOCAL_LLM_MODEL:
        return NaturalLanguageRoute(intent="unknown")

    payload = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 텔레그램 주식 봇의 자연어 라우터다. "
                    "답변은 JSON 객체 하나만 출력한다. 설명 문장이나 마크다운은 쓰지 않는다. "
                    "지원 intent는 search_ticker, analyze_company, add_watchlist, "
                    "remove_watchlist, show_watchlist, help, unknown 이다. "
                    "투자자 관점은 buffett, graham, lynch, munger 중 하나만 쓴다. "
                    "회사명이나 티커를 확신할 수 없으면 ticker는 비우고 query에 원문 회사명을 넣는다."
                ),
            },
            {
                "role": "user",
                "content": (
                    "아래 사용자 메시지를 분류해서 JSON으로만 반환해.\n"
                    '형식: {"intent":"...","query":"...","ticker":"...","investor":"..."}\n'
                    f"사용자 메시지: {cleaned_text}"
                ),
            },
        ],
        "stream": False,
        "format": "json",
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
        with request.urlopen(http_request, timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise LocalLLMExplanationError("로컬 LLM 호출에 실패했습니다.") from exc

    content = body.get("message", {}).get("content", "").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LocalLLMExplanationError("자연어 라우터 응답을 해석하지 못했습니다.") from exc

    intent = str(parsed.get("intent") or "unknown").strip()
    if intent not in INTENTS:
        intent = "unknown"

    investor = str(parsed.get("investor") or "").strip().lower()
    if investor not in INVESTOR_LABELS:
        investor = ""

    return NaturalLanguageRoute(
        intent=intent,
        query=str(parsed.get("query") or "").strip(),
        ticker=str(parsed.get("ticker") or "").strip().upper(),
        investor=investor,
    )


def should_route_to_llm(text: str) -> bool:
    normalized_text = text.strip()
    if not normalized_text:
        return False

    lowered_text = normalized_text.lower()
    if any(term in lowered_text for term in SENSITIVE_TERMS):
        return False

    if TICKER_PATTERN.search(normalized_text):
        return True

    return any(term in lowered_text for term in STOCK_ROUTING_TERMS)
