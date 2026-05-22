from stock_evaluator.lenses.base import LensScoreResult


BANNED_ADVICE_WORDS = ["매수 추천", "사라", "팔아라", "매도 추천"]


def render_company_report(company, snapshot, score_result: LensScoreResult) -> str:
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
            "해석",
            *_interpret_score(score_result),
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


def _interpret_score(score_result: LensScoreResult) -> list[str]:
    if score_result.score is None:
        return [
            "- 이 종목은 일반 기업 품질 점수로 단정하기 어렵습니다.",
            "- 상품 구조, 업종 특성, 배당/자산 구성 같은 전용 지표를 먼저 확인해야 합니다.",
        ]

    grade_comment = _grade_comment(score_result.grade)
    confidence_comment = _confidence_comment(score_result.confidence)
    risk_count = len(score_result.failed_rules) + len(score_result.warnings)
    risk_comment = (
        "- 통과 항목이 많지만, 아래 주의 항목은 별도로 확인해야 합니다."
        if risk_count
        else "- 현재 입력된 데이터 기준으로는 큰 품질 경고가 적습니다."
    )
    return [grade_comment, confidence_comment, risk_comment]


def _grade_comment(grade: str) -> str:
    comments = {
        "A": "- 품질 지표가 매우 강한 편입니다.",
        "A-": "- 품질 지표가 강한 편입니다.",
        "B+": "- 품질 지표가 대체로 양호합니다.",
        "B": "- 품질 지표가 보통 이상이지만 약점 확인이 필요합니다.",
        "C": "- 품질 지표가 애매해 세부 리스크 확인이 중요합니다.",
        "D": "- 품질 지표가 약한 편이라 보수적으로 확인해야 합니다.",
    }
    return comments.get(grade, "- 품질 판단을 위해 세부 지표를 함께 확인해야 합니다.")


def _confidence_comment(confidence: str) -> str:
    comments = {
        "high": "- 데이터 완성도가 높아 이 평가의 신뢰도는 높은 편입니다.",
        "medium": "- 일부 데이터가 부족해 이 평가는 중간 신뢰도로 봐야 합니다.",
        "low": "- 데이터가 부족해 이 평가는 낮은 신뢰도로만 참고해야 합니다.",
    }
    return comments.get(confidence, "- 데이터 신뢰도를 함께 확인해야 합니다.")


def _assert_no_banned_advice(message: str) -> None:
    for word in BANNED_ADVICE_WORDS:
        if word in message:
            raise ValueError(f"Advice wording is not allowed: {word}")
