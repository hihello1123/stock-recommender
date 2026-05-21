from django.test import SimpleTestCase

from stock_evaluator.companies.models import Company
from stock_evaluator.instruments.classifier import (
    classify_instrument_type,
    is_low_confidence_type,
)


class InstrumentClassifierTests(SimpleTestCase):
    def test_common_stock_from_quote_type(self):
        self.assertEqual(
            classify_instrument_type(quote_type="EQUITY"),
            Company.InstrumentType.COMMON_STOCK,
        )

    def test_reit_from_industry(self):
        self.assertEqual(
            classify_instrument_type(industry="REIT - Retail"),
            Company.InstrumentType.REIT,
        )

    def test_etf_from_quote_type(self):
        self.assertEqual(
            classify_instrument_type(quote_type="ETF"),
            Company.InstrumentType.ETF,
        )

    def test_financial_from_sector(self):
        self.assertEqual(
            classify_instrument_type(sector="Financial Services"),
            Company.InstrumentType.FINANCIAL,
        )

    def test_unknown_is_low_confidence(self):
        self.assertTrue(is_low_confidence_type(Company.InstrumentType.UNKNOWN))
