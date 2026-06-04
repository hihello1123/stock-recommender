from django.db import IntegrityError
from django.test import TestCase, override_settings
from unittest.mock import Mock, patch

from stock_evaluator.companies.models import Company
from stock_evaluator.users.models import TelegramUser, WatchlistItem
from stock_evaluator.users.services import WatchlistLimitError, effective_watchlist_items_for_user, watch_ticker


class TelegramUserModelTests(TestCase):
    def test_chat_id_must_be_unique(self):
        TelegramUser.objects.create(chat_id=123, username="george")

        with self.assertRaises(IntegrityError):
            TelegramUser.objects.create(chat_id=123, username="duplicate")


class WatchlistItemModelTests(TestCase):
    def test_user_company_pair_must_be_unique(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        company = Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")
        WatchlistItem.objects.create(user=user, company=company)

        with self.assertRaises(IntegrityError):
            WatchlistItem.objects.create(user=user, company=company)


class WatchlistServiceTests(TestCase):
    def _fill_watchlist(self, user: TelegramUser, count: int = 10) -> None:
        for index in range(count):
            company = Company.objects.create(ticker=f"T{index}", name=f"Company {index}", exchange="NASDAQ")
            WatchlistItem.objects.create(user=user, company=company)

    @override_settings(WATCHLIST_MAX_ITEMS=10, WATCHLIST_LIMIT_EXEMPT_CHAT_IDS=[])
    def test_watch_ticker_rejects_user_over_limit(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        self._fill_watchlist(user)

        with self.assertRaises(WatchlistLimitError):
            watch_ticker(user.chat_id, "AAPL", user.username)

    @override_settings(WATCHLIST_MAX_ITEMS=10, WATCHLIST_LIMIT_EXEMPT_CHAT_IDS=[])
    def test_watch_ticker_allows_existing_item_at_limit(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        self._fill_watchlist(user)

        item, created = watch_ticker(user.chat_id, "T0", user.username)

        self.assertFalse(created)
        self.assertEqual(item.company.ticker, "T0")

    @override_settings(WATCHLIST_MAX_ITEMS=10, WATCHLIST_LIMIT_EXEMPT_CHAT_IDS=[123])
    def test_watch_ticker_allows_exempt_user_over_limit(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        self._fill_watchlist(user)
        company = Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")

        with patch("stock_evaluator.users.services.CompanyLookupService") as lookup_service, patch(
            "stock_evaluator.users.services.save_company_report_data",
            return_value=(company, Mock()),
        ):
            lookup_service.return_value.lookup.return_value = Mock()
            item, created = watch_ticker(user.chat_id, "AAPL", user.username)

        self.assertTrue(created)
        self.assertEqual(item.company.ticker, "AAPL")

    @override_settings(WATCHLIST_MAX_ITEMS=10, WATCHLIST_LIMIT_EXEMPT_CHAT_IDS=[])
    def test_effective_watchlist_uses_first_items_for_limited_user(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        self._fill_watchlist(user, count=12)

        items = effective_watchlist_items_for_user(user)

        self.assertEqual(len(items), 10)
        self.assertEqual([item.company.ticker for item in items], [f"T{index}" for index in range(10)])

    @override_settings(WATCHLIST_MAX_ITEMS=10, WATCHLIST_LIMIT_EXEMPT_CHAT_IDS=[123])
    def test_effective_watchlist_keeps_all_items_for_exempt_user(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        self._fill_watchlist(user, count=12)

        items = effective_watchlist_items_for_user(user)

        self.assertEqual(len(items), 12)
