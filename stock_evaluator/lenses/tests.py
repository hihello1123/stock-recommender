from dataclasses import dataclass
from decimal import Decimal

from django.test import SimpleTestCase

from stock_evaluator.companies.models import Company, LensScore
from stock_evaluator.lenses.quality_v1 import QualityLensV1


@dataclass
class SnapshotFixture:
    roe: Decimal | None = Decimal("0.20")
    roic: Decimal | None = Decimal("0.15")
    free_cash_flow: Decimal | None = Decimal("100")
    total_debt: Decimal | None = Decimal("50")
    cash: Decimal | None = Decimal("100")
    net_income: Decimal | None = Decimal("90")
    per: Decimal | None = Decimal("24")
    missing_fields: list[str] | None = None


class QualityLensV1Tests(SimpleTestCase):
    def test_high_quality_complete_data_scores_well(self):
        result = QualityLensV1().evaluate(
            SnapshotFixture(missing_fields=[]),
            instrument_type=Company.InstrumentType.COMMON_STOCK,
        )

        self.assertEqual(result.score, 100)
        self.assertEqual(result.grade, "A")
        self.assertEqual(result.confidence, LensScore.Confidence.HIGH)
        self.assertEqual(result.data_completeness, 100)

    def test_weak_company_scores_low(self):
        result = QualityLensV1().evaluate(
            SnapshotFixture(
                roe=Decimal("0.03"),
                roic=Decimal("0.02"),
                free_cash_flow=Decimal("-1"),
                total_debt=Decimal("100"),
                cash=Decimal("10"),
                net_income=Decimal("-1"),
                per=Decimal("60"),
                missing_fields=[],
            ),
            instrument_type=Company.InstrumentType.COMMON_STOCK,
        )

        self.assertEqual(result.score, 8)
        self.assertEqual(result.grade, "D")
        self.assertIn("FCF가 양수가 아닙니다.", result.failed_rules)

    def test_missing_fields_lower_confidence_without_zero_filling(self):
        result = QualityLensV1().evaluate(
            SnapshotFixture(roic=None, free_cash_flow=None, missing_fields=["roic", "free_cash_flow"]),
            instrument_type=Company.InstrumentType.COMMON_STOCK,
        )

        self.assertEqual(result.data_completeness, 71)
        self.assertEqual(result.confidence, LensScore.Confidence.MEDIUM)
        self.assertIn("ROIC 데이터가 없습니다.", result.warnings)
        self.assertIn("FCF 데이터가 없습니다.", result.warnings)

    def test_low_confidence_instrument_suppresses_score(self):
        result = QualityLensV1().evaluate(
            SnapshotFixture(missing_fields=[]),
            instrument_type=Company.InstrumentType.REIT,
        )

        self.assertIsNone(result.score)
        self.assertEqual(result.grade, "N/A")
        self.assertEqual(result.confidence, LensScore.Confidence.LOW)
        self.assertTrue(result.required_extra_checks)

    def test_grade_boundaries(self):
        lens = QualityLensV1()

        result = lens.evaluate(
            SnapshotFixture(per=Decimal("45"), missing_fields=[]),
            instrument_type=Company.InstrumentType.COMMON_STOCK,
        )

        self.assertEqual(result.grade, "A-")
