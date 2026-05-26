import json
from urllib import request

from django.conf import settings

from stock_evaluator.lenses.base import LensScoreResult


class LocalLLMExplanationError(RuntimeError):
    pass


INVESTOR_LABELS = {
    "buffett": "Buffett",
    "graham": "Graham",
    "lynch": "Peter Lynch",
    "munger": "Munger",
}


def generate_investor_explanation(
    company,
    snapshot,
    score_result: LensScoreResult,
    investor: str,
) -> str | None:
    if not settings.LOCAL_LLM_MODEL:
        return None

    normalized_investor = investor.lower()
    if normalized_investor not in INVESTOR_LABELS:
        raise LocalLLMExplanationError("지원하지 않는 투자 전문가입니다.")

    prompt = _build_prompt(company, snapshot, score_result, normalized_investor)
    payload = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 미국 상장기업을 분석하는 보조자다. "
                    "점수 계산은 이미 코드가 끝냈고, 너는 그 결과를 투자 전문가 관점으로 설명만 한다. "
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
        with request.urlopen(http_request, timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise LocalLLMExplanationError("로컬 LLM 호출에 실패했습니다.") from exc

    content = body.get("message", {}).get("content", "").strip()
    if not content:
        raise LocalLLMExplanationError("로컬 LLM 응답이 비어 있습니다.")
    return content


def _build_prompt(company, snapshot, score_result: LensScoreResult, investor: str) -> str:
    investor_label = INVESTOR_LABELS[investor]
    criteria = _investor_criteria(investor)
    return "\n".join(
        [
            f"아래 정량 평가 결과를 바탕으로 {investor_label} 관점의 해석만 작성해줘.",
            "투자 전문가 기준은 아래 내용을 우선 적용해.",
            "형식은 반드시 아래처럼 유지해.",
            "",
            f"[{investor_label}]",
            "- 좋은 점:",
            "- 아쉬운 점:",
            "- 확인할 것:",
            "",
            "규칙:",
            "- 한국어로 짧게 써.",
            "- 각 전문가별로 3줄 이내로 써.",
            "- 제공된 데이터에 없는 내용은 '추가 확인 필요'라고 써.",
            "- 매수 추천, 매도 추천, 사라, 팔아라 같은 표현은 쓰지 마.",
            "",
            "투자 전문가 기준:",
            *criteria,
            "",
            "회사:",
            f"- 티커: {company.ticker}",
            f"- 이름: {company.name}",
            f"- 거래소: {company.exchange}",
            f"- 업종: {company.sector} / {company.industry}",
            f"- 국가: {company.country}",
            "",
            "정량 점수:",
            f"- 렌즈: {score_result.lens_name} {score_result.scoring_version}",
            f"- 등급: {score_result.grade}",
            f"- 점수: {score_result.score}",
            f"- 신뢰도: {score_result.confidence}",
            f"- 데이터 완성도: {score_result.data_completeness}",
            f"- 통과: {score_result.passed_rules}",
            f"- 주의: {score_result.failed_rules}",
            f"- 경고: {score_result.warnings}",
            f"- 추가 확인: {score_result.required_extra_checks}",
            "",
            "주요 데이터:",
            f"- 기준일: {snapshot.as_of_date}",
            f"- 가격: {snapshot.price}",
            f"- 시가총액: {snapshot.market_cap}",
            f"- PER/PBR/PSR: {snapshot.per} / {snapshot.pbr} / {snapshot.psr}",
            f"- ROE/ROIC: {snapshot.roe} / {snapshot.roic}",
            f"- 매출/영업이익/순이익: {snapshot.revenue} / {snapshot.operating_income} / {snapshot.net_income}",
            f"- EPS: {snapshot.eps}",
            f"- 영업현금흐름/FCF: {snapshot.operating_cash_flow} / {snapshot.free_cash_flow}",
            f"- 총부채/현금: {snapshot.total_debt} / {snapshot.cash}",
            f"- 누락 필드: {snapshot.missing_fields}",
        ]
    )


def _investor_criteria(investor: str) -> list[str]:
    criteria = {
        "buffett": [
            "[Buffett 기준]",
            "- 핵심 관점: 좋은 회사를 합리적인 가격에 오래 보유한다.",
            "- 중요 항목: ROE, ROIC, 영업이익률, 순이익 안정성, FCF, 부채 부담, 경제적 해자, 가격 합리성.",
            "- 좋게 보는 조건: 높은 ROE/ROIC, 장기 FCF 플러스, 과하지 않은 부채, 이해 가능한 사업, 브랜드/네트워크 효과/전환비용/규모의 경제.",
            "- 감점 조건: 이익 변동성, 과도한 부채, 마이너스 FCF, 복잡한 사업, 불명확한 경쟁우위, 비싼 가격.",
        ],
        "graham": [
            "[Graham 기준]",
            "- 핵심 관점: 충분히 싼 가격에 안전마진을 확보한다.",
            "- 중요 항목: PER, PBR, 유동비율, 부채비율, NCAV, 배당 이력, 이익 안정성, 안전마진.",
            "- 좋게 보는 조건: 낮은 PER/PBR, 높은 유동성, 낮은 부채, 장기 흑자, 내재가치 대비 할인.",
            "- 감점 조건: 높은 PER/PBR, 적자 지속, 부채 과다, 유동성 부족, 순자산 대비 비싸거나 안전마진 부족.",
        ],
        "lynch": [
            "[Peter Lynch 기준]",
            "- 핵심 관점: 성장하는 회사를 합리적인 가격에 산다.",
            "- 중요 항목: 매출 성장률, EPS 성장률, PEG, 부채비율, 이익 지속성, 사업 이해도, 시장 확장성, 내부자/자사주.",
            "- 좋게 보는 조건: 매출/EPS 증가, 과도하지 않은 PEG, 감당 가능한 부채, 이해 가능한 사업, 성장 여지.",
            "- 감점 조건: 성장률 둔화, 들쭉날쭉한 EPS, 높은 PEG, 부채 의존 성장, 복잡하거나 유행성 테마인 사업.",
        ],
        "munger": [
            "[Munger 기준]",
            "- 핵심 관점: 훌륭한 사업을 오래 보유하고, 나쁜 사업은 아무리 싸도 피한다.",
            "- 중요 항목: 사업 품질, ROIC, 경제적 해자, 가격 결정력, 반복 수익, 경영진 자본배분, 복잡성, 장기 리스크.",
            "- 좋게 보는 조건: 높은 ROIC, 명확한 경쟁우위, 가격 결정력, 반복 매출/고객 충성도, 합리적 자본배분, 장기 생존성.",
            "- 감점 조건: 낮은 사업 품질, 자본집약적 성장, 약한 해자, 기술 변화 취약성, 주주가치 훼손, 복잡한 사업.",
        ],
    }
    return criteria[investor]
