from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from stock_evaluator.companies.models import Company, FinancialSnapshot, LensScore


class CompanyModelTests(TestCase):
    def test_ticker_exchange_must_be_unique(self):
        Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")

        with self.assertRaises(IntegrityError):
            Company.objects.create(ticker="AAPL", name="Apple Duplicate", exchange="NASDAQ")


class FinancialSnapshotModelTests(TestCase):
    def test_snapshot_source_period_must_be_unique(self):
        company = Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")
        FinancialSnapshot.objects.create(
            company=company,
            source="yfinance",
            as_of_date=date(2026, 5, 21),
            period_end_date=date(2025, 12, 31),
            period_type=FinancialSnapshot.PeriodType.ANNUAL,
        )

        with self.assertRaises(IntegrityError):
            FinancialSnapshot.objects.create(
                company=company,
                source="yfinance",
                as_of_date=date(2026, 5, 21),
                period_end_date=date(2025, 12, 31),
                period_type=FinancialSnapshot.PeriodType.ANNUAL,
            )


class LensScoreModelTests(TestCase):
    def test_lens_score_version_must_be_unique_per_snapshot(self):
        company = Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")
        snapshot = FinancialSnapshot.objects.create(
            company=company,
            source="yfinance",
            as_of_date=date(2026, 5, 21),
            period_type=FinancialSnapshot.PeriodType.TTM,
        )
        LensScore.objects.create(
            company=company,
            snapshot=snapshot,
            lens_name="quality",
            scoring_version="quality-v1",
            score=80,
            grade="B+",
            confidence=LensScore.Confidence.MEDIUM,
            data_completeness=90,
        )

        with self.assertRaises(IntegrityError):
            LensScore.objects.create(
                company=company,
                snapshot=snapshot,
                lens_name="quality",
                scoring_version="quality-v1",
                score=81,
                grade="B+",
                confidence=LensScore.Confidence.MEDIUM,
                data_completeness=90,
            )
