from datetime import date
from decimal import Decimal
import math
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from stock_evaluator.companies.models import FinancialSnapshot
from stock_evaluator.companies.services.company_lookup import CompanyLookupService
from stock_evaluator.companies.services.company_search import (
    CompanySearchResult,
    YFinanceCompanySearchClient,
    _normalize_quotes,
    rank_ticker_matches,
)
from stock_evaluator.companies.services.data_normalizer import normalize_market_data
from stock_evaluator.companies.services.market_data_client import (
    MarketDataPayload,
    MarketDataError,
    TickerNotFoundError,
    YFinanceMarketDataClient,
    normalize_ticker,
)


class TickerNormalizerTests(SimpleTestCase):
    def test_normalize_ticker_strips_and_uppercases(self):
        self.assertEqual(normalize_ticker(" aapl "), "AAPL")

    def test_normalize_ticker_preserves_punctuation(self):
        self.assertEqual(normalize_ticker(" brk.b "), "BRK.B")

    def test_normalize_ticker_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            normalize_ticker(" ")


class YFinanceMarketDataClientTests(SimpleTestCase):
    def test_fetch_wraps_library_exception(self):
        with patch(
            "stock_evaluator.companies.services.market_data_client.yf.Ticker",
            side_effect=RuntimeError("network down"),
        ):
            client = YFinanceMarketDataClient()

            with self.assertRaises(MarketDataError):
                client.fetch("AAPL")

    def test_fetch_rejects_empty_result(self):
        fake_ticker = Mock()
        fake_ticker.info = {}
        fake_ticker.fast_info = {}

        with patch(
            "stock_evaluator.companies.services.market_data_client.yf.Ticker",
            return_value=fake_ticker,
        ):
            client = YFinanceMarketDataClient()

            with self.assertRaises(TickerNotFoundError):
                client.fetch("BAD")


class CompanySearchTests(SimpleTestCase):
    def test_normalize_quotes_returns_search_results(self):
        results = _normalize_quotes(
            [
                {
                    "symbol": "aapl",
                    "longname": "Apple Inc.",
                    "exchDisp": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            ],
            limit=5,
        )

        self.assertEqual(results[0].ticker, "AAPL")
        self.assertEqual(results[0].name, "Apple Inc.")
        self.assertEqual(results[0].exchange, "NASDAQ")
        self.assertEqual(results[0].quote_type, "EQUITY")

    def test_search_rejects_empty_query(self):
        client = YFinanceCompanySearchClient()

        with self.assertRaises(ValueError):
            client.search(" ")

    def test_search_wraps_library_exception(self):
        with patch(
            "stock_evaluator.companies.services.company_search.yf.Search",
            side_effect=RuntimeError("network down"),
        ):
            client = YFinanceCompanySearchClient()

            with self.assertRaises(MarketDataError):
                client.search("apple")

    def test_rank_ticker_matches_ignores_common_separators(self):
        matches = rank_ticker_matches(
            "BRK.B",
            [
                CompanySearchResult(ticker="BRK-A", name="Berkshire Hathaway Inc."),
                CompanySearchResult(ticker="BRK-B", name="Berkshire Hathaway Inc."),
            ],
        )

        self.assertEqual(matches[0].ticker, "BRK-B")
        self.assertEqual(matches[0].similarity, 1)


class DataNormalizerTests(SimpleTestCase):
    def test_normalize_full_payload(self):
        payload = MarketDataPayload(
            ticker="AAPL",
            info={
                "currency": "USD",
                "currentPrice": 190.12,
                "marketCap": 3000000000000,
                "trailingPE": 31.5,
                "priceToBook": 45.2,
                "priceToSalesTrailing12Months": 7.8,
                "returnOnEquity": 1.45,
                "returnOnCapital": 0.55,
                "totalRevenue": 383285000000,
                "operatingIncome": 114301000000,
                "netIncomeToCommon": 96995000000,
                "trailingEps": 6.16,
                "operatingCashflow": 110543000000,
                "freeCashflow": 99584000000,
                "totalDebt": 111088000000,
                "totalCash": 62639000000,
            },
            fast_info={},
        )

        values = normalize_market_data(payload, as_of_date=date(2026, 5, 21))

        self.assertEqual(values["source"], "yfinance")
        self.assertEqual(values["as_of_date"], date(2026, 5, 21))
        self.assertEqual(values["period_type"], FinancialSnapshot.PeriodType.UNKNOWN)
        self.assertEqual(values["currency"], "USD")
        self.assertEqual(values["price"], Decimal("190.12"))
        self.assertEqual(values["market_cap"], Decimal("3000000000000"))
        self.assertEqual(values["missing_fields"], [])

    def test_missing_fields_are_recorded(self):
        payload = MarketDataPayload(
            ticker="AAPL",
            info={"currency": "USD", "currentPrice": 190.12},
            fast_info={},
        )

        values = normalize_market_data(payload, as_of_date=date(2026, 5, 21))

        self.assertIn("roic", values["missing_fields"])
        self.assertIn("free_cash_flow", values["missing_fields"])
        self.assertEqual(values["price"], Decimal("190.12"))

    def test_invalid_numeric_field_becomes_missing(self):
        payload = MarketDataPayload(
            ticker="AAPL",
            info={"currentPrice": "not-a-number"},
            fast_info={},
        )

        values = normalize_market_data(payload, as_of_date=date(2026, 5, 21))

        self.assertIsNone(values["price"])
        self.assertIn("price", values["missing_fields"])

    def test_non_finite_numbers_become_json_safe_missing_values(self):
        payload = MarketDataPayload(
            ticker="APPL",
            info={"currentPrice": math.nan, "nested": {"bad": math.inf}},
            fast_info={"last_price": math.nan},
        )

        values = normalize_market_data(payload, as_of_date=date(2026, 5, 21))

        self.assertIsNone(values["price"])
        self.assertIn("price", values["missing_fields"])
        self.assertIsNone(values["raw_payload"]["info"]["currentPrice"])
        self.assertIsNone(values["raw_payload"]["info"]["nested"]["bad"])
        self.assertIsNone(values["raw_payload"]["fast_info"]["last_price"])


class FakeMarketDataClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def fetch(self, ticker):
        if self.error:
            raise self.error
        return self.payload


class CompanyLookupServiceTests(SimpleTestCase):
    def test_lookup_returns_unsaved_company_and_snapshot_values(self):
        payload = MarketDataPayload(
            ticker="AAPL",
            info={
                "longName": "Apple Inc.",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "country": "United States",
                "currentPrice": 190.12,
            },
            fast_info={},
        )
        service = CompanyLookupService(FakeMarketDataClient(payload=payload))

        result = service.lookup("aapl")

        self.assertEqual(result.company.ticker, "AAPL")
        self.assertEqual(result.company.name, "Apple Inc.")
        self.assertEqual(result.company.exchange, "NASDAQ")
        self.assertEqual(result.snapshot_values["price"], Decimal("190.12"))

    def test_lookup_propagates_domain_errors(self):
        service = CompanyLookupService(
            FakeMarketDataClient(error=TickerNotFoundError("Ticker not found: BAD"))
        )

        with self.assertRaises(TickerNotFoundError):
            service.lookup("BAD")
