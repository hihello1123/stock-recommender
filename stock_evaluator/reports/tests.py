from dataclasses import dataclass
from datetime import date

from django.test import SimpleTestCase

from stock_evaluator.companies.models import LensScore
from stock_evaluator.lenses.base import LensScoreResult
from stock_evaluator.reports.telegram_renderer import render_company_report, render_error_message


@dataclass
class CompanyFixture:
    ticker: str = "AAPL"
    name: str = "Apple Inc."


@dataclass
class SnapshotFixture:
    source: str = "yfinance"
    as_of_date: date = date(2026, 5, 21)
    missing_fields: list[str] | None = None


class TelegramRendererTests(SimpleTestCase):
    def test_render_normal_report(self):
        message = render_company_report(
            CompanyFixture(),
            SnapshotFixture(missing_fields=[]),
            LensScoreResult(
                lens_name="quality",
                scoring_version="quality-v1",
                score=90,
                grade="A",
                confidence=LensScore.Confidence.HIGH,
                data_completeness=100,
                passed_rules=["FCF가 양수입니다."],
            ),
        )

        self.assertIn("[AAPL / Apple Inc.]", message)
        self.assertIn("점수: 90 / 100", message)
        self.assertIn("선택한 대가 해석", message)
        self.assertIn("로컬 LLM 설명이 비활성화되어 있습니다.", message)
        self.assertIn("이 결과는 자동 매수 신호가 아닙니다.", message)

    def test_render_report_with_llm_explanation(self):
        message = render_company_report(
            CompanyFixture(),
            SnapshotFixture(missing_fields=[]),
            LensScoreResult(
                lens_name="quality",
                scoring_version="quality-v1",
                score=90,
                grade="A",
                confidence=LensScore.Confidence.HIGH,
                data_completeness=100,
            ),
            explanation="[Buffett]\n- 테스트 설명",
        )

        self.assertIn("[Buffett]\n- 테스트 설명", message)

    def test_render_low_confidence_report_without_score(self):
        message = render_company_report(
            CompanyFixture(),
            SnapshotFixture(missing_fields=["roic"]),
            LensScoreResult(
                lens_name="quality",
                scoring_version="quality-v1",
                score=None,
                grade="N/A",
                confidence=LensScore.Confidence.LOW,
                data_completeness=86,
                warnings=["일반 품질 점수를 제공하기 어려운 상품/업종입니다."],
                required_extra_checks=["업종 또는 상품 유형에 맞는 전용 지표 확인"],
            ),
        )

        self.assertIn("일반 품질 점수: 제공하지 않음", message)
        self.assertIn("추가 확인", message)

    def test_error_message_rejects_banned_advice_wording(self):
        with self.assertRaises(ValueError):
            render_error_message("매수 추천")
