from dataclasses import dataclass
from datetime import date

from django.test import SimpleTestCase

from stock_evaluator.companies.models import LensScore
from stock_evaluator.lenses.base import LensScoreResult
from stock_evaluator.reports.llm_explainer import _build_prompt


@dataclass
class CompanyFixture:
    ticker: str = "AAPL"
    name: str = "Apple Inc."
    exchange: str = "NASDAQ"
    sector: str = "Technology"
    industry: str = "Consumer Electronics"
    country: str = "United States"


@dataclass
class SnapshotFixture:
    as_of_date: date = date(2026, 5, 21)
    price: str = "190.12"
    market_cap: str = "3000000000000"
    per: str = "24"
    pbr: str = "40"
    psr: str = "7"
    roe: str = "0.20"
    roic: str = "0.15"
    revenue: str = "383285000000"
    operating_income: str = "114301000000"
    net_income: str = "96995000000"
    eps: str = "6.16"
    operating_cash_flow: str = "110543000000"
    free_cash_flow: str = "99584000000"
    total_debt: str = "50000000000"
    cash: str = "60000000000"
    missing_fields: list[str] | None = None


class LocalLLMExplainerPromptTests(SimpleTestCase):
    def test_prompt_includes_investor_criteria_from_idea(self):
        prompt = _build_prompt(
            CompanyFixture(),
            SnapshotFixture(),
            LensScoreResult(
                lens_name="quality",
                scoring_version="quality-v1",
                score=90,
                grade="A",
                confidence=LensScore.Confidence.HIGH,
                data_completeness=100,
            ),
            "buffett",
        )

        self.assertIn("[Buffett 기준]", prompt)
        self.assertIn("ROE, ROIC, 영업이익률", prompt)
        self.assertNotIn("[Graham 기준]", prompt)
