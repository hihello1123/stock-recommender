from decimal import Decimal
from typing import Any

from stock_evaluator.companies.models import Company, LensScore
from stock_evaluator.instruments.classifier import is_low_confidence_type
from stock_evaluator.lenses.base import InvestorLens, LensScoreResult


class QualityLensV1(InvestorLens):
    name = "quality"
    scoring_version = "quality-v1"

    def evaluate(self, snapshot, *, instrument_type: str) -> LensScoreResult:
        missing_fields = set(getattr(snapshot, "missing_fields", []) or [])
        data_completeness = _data_completeness(missing_fields)

        if is_low_confidence_type(instrument_type):
            return LensScoreResult(
                lens_name=self.name,
                scoring_version=self.scoring_version,
                score=None,
                grade="N/A",
                confidence=LensScore.Confidence.LOW,
                data_completeness=data_completeness,
                warnings=["일반 품질 점수를 제공하기 어려운 상품/업종입니다."],
                required_extra_checks=["업종 또는 상품 유형에 맞는 전용 지표 확인"],
            )

        passed: list[str] = []
        failed: list[str] = []
        warnings: list[str] = []

        score = 0
        score += _score_profitability(snapshot, missing_fields, passed, failed, warnings)
        score += _score_cash_flow(snapshot, missing_fields, passed, failed, warnings)
        score += _score_balance_sheet(snapshot, missing_fields, passed, failed, warnings)
        score += _score_earnings_quality(snapshot, missing_fields, passed, failed, warnings)
        score += _score_price(snapshot, missing_fields, passed, failed, warnings)

        confidence = _confidence(data_completeness)
        return LensScoreResult(
            lens_name=self.name,
            scoring_version=self.scoring_version,
            score=score,
            grade=_grade(score),
            confidence=confidence,
            data_completeness=data_completeness,
            passed_rules=passed,
            failed_rules=failed,
            warnings=warnings,
        )


def _score_profitability(snapshot: Any, missing_fields: set[str], passed, failed, warnings) -> int:
    if {"roe", "roic"}.issubset(missing_fields):
        warnings.append("수익성 핵심 지표가 부족합니다.")
        return 0

    score = 0
    if _gte(snapshot.roe, "0.15"):
        score += 12
        passed.append("ROE가 양호합니다.")
    elif "roe" not in missing_fields:
        failed.append("ROE가 낮습니다.")

    if _gte(snapshot.roic, "0.12"):
        score += 13
        passed.append("ROIC가 양호합니다.")
    elif "roic" not in missing_fields:
        failed.append("ROIC가 낮습니다.")
    else:
        warnings.append("ROIC 데이터가 없습니다.")
    return score


def _score_cash_flow(snapshot: Any, missing_fields: set[str], passed, failed, warnings) -> int:
    if "free_cash_flow" in missing_fields:
        warnings.append("FCF 데이터가 없습니다.")
        return 0

    if _gt(snapshot.free_cash_flow, "0"):
        passed.append("FCF가 양수입니다.")
        return 25

    failed.append("FCF가 양수가 아닙니다.")
    return 0


def _score_balance_sheet(snapshot: Any, missing_fields: set[str], passed, failed, warnings) -> int:
    if {"total_debt", "cash"}.issubset(missing_fields):
        warnings.append("부채와 현금 데이터가 부족합니다.")
        return 0

    total_debt = _decimal(snapshot.total_debt)
    cash = _decimal(snapshot.cash)
    if total_debt is not None and cash is not None and cash >= total_debt:
        passed.append("현금이 총부채 이상입니다.")
        return 20
    if total_debt is not None and _gt(total_debt, "0"):
        failed.append("현금 대비 부채 확인이 필요합니다.")
        return 8

    warnings.append("부채 안정성 판단 데이터가 부족합니다.")
    return 0


def _score_earnings_quality(snapshot: Any, missing_fields: set[str], passed, failed, warnings) -> int:
    if "net_income" in missing_fields:
        warnings.append("순이익 데이터가 없습니다.")
        return 0

    if _gt(snapshot.net_income, "0"):
        passed.append("순이익이 양수입니다.")
        return 15

    failed.append("순이익이 양수가 아닙니다.")
    return 0


def _score_price(snapshot: Any, missing_fields: set[str], passed, failed, warnings) -> int:
    if "per" in missing_fields:
        warnings.append("PER 데이터가 없습니다.")
        return 0

    per = _decimal(snapshot.per)
    if per is None:
        warnings.append("PER 데이터가 없습니다.")
        return 0
    if per <= Decimal("25"):
        passed.append("PER 기준 가격 부담이 과도하지 않습니다.")
        return 15
    if per <= Decimal("40"):
        failed.append("PER 기준 가격 부담이 있습니다.")
        return 7

    failed.append("PER 기준 가격 부담이 큽니다.")
    return 0


def _data_completeness(missing_fields: set[str]) -> int:
    required_fields = {
        "roe",
        "roic",
        "free_cash_flow",
        "total_debt",
        "cash",
        "net_income",
        "per",
    }
    missing_required = len(required_fields.intersection(missing_fields))
    return round((len(required_fields) - missing_required) / len(required_fields) * 100)


def _confidence(data_completeness: int) -> str:
    if data_completeness >= 85:
        return LensScore.Confidence.HIGH
    if data_completeness >= 70:
        return LensScore.Confidence.MEDIUM
    return LensScore.Confidence.LOW


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 70:
        return "B+"
    if score >= 60:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def _gte(value: Any, threshold: str) -> bool:
    decimal = _decimal(value)
    return decimal is not None and decimal >= Decimal(threshold)


def _gt(value: Any, threshold: str) -> bool:
    decimal = _decimal(value)
    return decimal is not None and decimal > Decimal(threshold)


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
