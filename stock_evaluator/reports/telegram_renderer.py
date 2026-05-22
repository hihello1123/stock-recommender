from stock_evaluator.lenses.base import LensScoreResult


BANNED_ADVICE_WORDS = ["매수 추천", "사라", "팔아라", "매도 추천"]


def render_company_report(
    company,
    snapshot,
    score_result: LensScoreResult,
    explanation: str | None = None,
) -> str:
    score_line = (
        "일반 품질 점수: 제공하지 않음"
        if score_result.score is None
        else f"점수: {score_result.score} / 100"
    )
    lines = [
        f"[{company.ticker} / {company.name}]",
        "",
        "데이터",
        f"- 출처: {snapshot.source}",
        f"- 기준일: {snapshot.as_of_date.isoformat()}",
        f"- 누락 필드: {_format_missing_fields(snapshot.missing_fields)}",
        f"- 데이터 완성도: {score_result.data_completeness} / 100",
        "",
        "Quality Lens v1",
        f"- 등급: {score_result.grade}",
        f"- {score_line}",
        f"- 평가 신뢰도: {score_result.confidence}",
    ]
    if score_result.passed_rules:
        lines.extend(["", "통과", *[f"- {rule}" for rule in score_result.passed_rules]])
    if score_result.failed_rules or score_result.warnings:
        lines.extend(
            [
                "",
                "주의",
                *[f"- {rule}" for rule in score_result.failed_rules],
                *[f"- {warning}" for warning in score_result.warnings],
            ]
        )
    if score_result.required_extra_checks:
        lines.extend(
            [
                "",
                "추가 확인",
                *[f"- {check}" for check in score_result.required_extra_checks],
            ]
        )
    lines.extend(
        [
            "",
            "대가별 해석",
            explanation or "로컬 LLM 설명이 비활성화되어 있습니다.",
            "",
            "주의",
            "이 결과는 자동 매수 신호가 아닙니다.",
            "가격, 최근 실적, 업종 리스크를 직접 확인해야 합니다.",
        ]
    )
    message = "\n".join(lines)
    _assert_no_banned_advice(message)
    return message


def render_error_message(message: str) -> str:
    _assert_no_banned_advice(message)
    return message


def _format_missing_fields(missing_fields: list[str]) -> str:
    return ", ".join(missing_fields) if missing_fields else "없음"


def _assert_no_banned_advice(message: str) -> None:
    for word in BANNED_ADVICE_WORDS:
        if word in message:
            raise ValueError(f"Advice wording is not allowed: {word}")
