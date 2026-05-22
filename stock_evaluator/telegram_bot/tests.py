import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from telegram.constants import ChatType

from stock_evaluator.companies.models import Company, FinancialSnapshot, LensScore
from stock_evaluator.companies.services.company_lookup import CompanyLookupResult
from stock_evaluator.telegram_bot.auth import ACCESS_DENIED_MESSAGE, is_allowed_chat
from stock_evaluator.telegram_bot.bot import TelegramBotConfigError, build_application
from stock_evaluator.telegram_bot.handlers import (
    _company_report_message,
    _unwatch_message,
    _watch_message,
    _watchlist_message,
    company,
    help_command,
    ping,
    start,
)
from stock_evaluator.telegram_bot.messages import help_message, start_message


class FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeChat:
    def __init__(self, chat_id: int, chat_type: str = ChatType.PRIVATE):
        self.id = chat_id
        self.type = chat_type


class FakeUser:
    def __init__(self, username: str = "george"):
        self.username = username


class FakeUpdate:
    def __init__(self, chat_id: int = 123456789, chat_type: str = ChatType.PRIVATE):
        self.effective_message = FakeMessage()
        self.effective_chat = FakeChat(chat_id, chat_type)
        self.effective_user = FakeUser()


class FakeContext:
    def __init__(self, args=None):
        self.args = args or []


class TelegramMessageTests(SimpleTestCase):
    def test_start_message_mentions_help(self):
        self.assertIn("/help", start_message())

    def test_help_message_lists_basic_commands(self):
        message = help_message()

        self.assertIn("/start", message)
        self.assertIn("/help", message)
        self.assertIn("/ping", message)
        self.assertIn("/company", message)
        self.assertIn("/watch", message)
        self.assertIn("/unwatch", message)
        self.assertIn("/watchlist", message)


@override_settings(ALLOWED_TELEGRAM_CHAT_IDS=[123456789])
class TelegramAuthTests(SimpleTestCase):
    def test_allowed_private_chat_passes(self):
        self.assertTrue(is_allowed_chat(FakeUpdate()))

    def test_denied_chat_id_fails(self):
        self.assertFalse(is_allowed_chat(FakeUpdate(chat_id=999)))

    def test_group_chat_fails(self):
        self.assertFalse(is_allowed_chat(FakeUpdate(chat_type=ChatType.GROUP)))


@override_settings(ALLOWED_TELEGRAM_CHAT_IDS=[123456789])
class TelegramHandlerTests(SimpleTestCase):
    def test_ping_replies_pong(self):
        update = FakeUpdate()

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, ["pong"])

    def test_start_replies_with_start_message(self):
        update = FakeUpdate()

        asyncio.run(start(update, None))

        self.assertEqual(update.effective_message.replies, [start_message()])

    def test_help_replies_with_help_message(self):
        update = FakeUpdate()

        asyncio.run(help_command(update, None))

        self.assertEqual(update.effective_message.replies, [help_message()])

    def test_denied_chat_gets_access_denied(self):
        update = FakeUpdate(chat_id=999)

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, [ACCESS_DENIED_MESSAGE])

    def test_group_chat_gets_access_denied(self):
        update = FakeUpdate(chat_type=ChatType.GROUP)

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, [ACCESS_DENIED_MESSAGE])


class TelegramApplicationTests(SimpleTestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_build_application_requires_token(self):
        with self.assertRaises(TelegramBotConfigError):
            build_application()

    def test_build_application_registers_basic_commands(self):
        application = build_application("123456:ABCDEF")
        command_names = {
            command
            for group in application.handlers.values()
            for handler in group
            for command in getattr(handler, "commands", set())
        }

        self.assertSetEqual(
            command_names,
            {"start", "help", "ping", "company", "watch", "unwatch", "watchlist"},
        )


@override_settings(ALLOWED_TELEGRAM_CHAT_IDS=[123456789])
class CompanyCommandTests(TestCase):
    def test_company_success_replies_with_report(self):
        with patch(
            "stock_evaluator.telegram_bot.handlers._company_report_message",
            return_value="[AAPL / Apple Inc.]",
        ):
            update = FakeUpdate()
            asyncio.run(company(update, FakeContext(args=["AAPL"])))

        self.assertEqual(update.effective_message.replies, ["[AAPL / Apple Inc.]"])

    def test_company_missing_ticker_replies_with_safe_error(self):
        update = FakeUpdate()

        asyncio.run(company(update, FakeContext(args=[])))

        self.assertEqual(update.effective_message.replies, ["티커를 입력해주세요. 예: /company AAPL"])


class CompanyReportMessageTests(TestCase):
    def test_company_report_message_saves_data_and_score(self):
        lookup_result = CompanyLookupResult(
            company=Company(
                ticker="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                sector="Technology",
                industry="Consumer Electronics",
                country="United States",
                instrument_type=Company.InstrumentType.COMMON_STOCK,
            ),
            snapshot_values={
                "source": "yfinance",
                "source_url": "https://finance.yahoo.com/quote/AAPL",
                "as_of_date": date(2026, 5, 21),
                "period_end_date": None,
                "period_type": FinancialSnapshot.PeriodType.UNKNOWN,
                "currency": "USD",
                "price": Decimal("190.12"),
                "market_cap": Decimal("3000000000000"),
                "per": Decimal("24"),
                "pbr": Decimal("40"),
                "psr": Decimal("7"),
                "roe": Decimal("0.20"),
                "roic": Decimal("0.15"),
                "revenue": Decimal("383285000000"),
                "operating_income": Decimal("114301000000"),
                "net_income": Decimal("96995000000"),
                "eps": Decimal("6.16"),
                "operating_cash_flow": Decimal("110543000000"),
                "free_cash_flow": Decimal("99584000000"),
                "total_debt": Decimal("50000000000"),
                "cash": Decimal("60000000000"),
                "missing_fields": [],
                "raw_payload": {},
            },
        )
        service = Mock()
        service.lookup.return_value = lookup_result

        with patch("stock_evaluator.telegram_bot.handlers.CompanyLookupService", return_value=service):
            message = _company_report_message("AAPL")

        self.assertIn("[AAPL / Apple Inc.]", message)
        self.assertIn("Quality Lens v1", message)
        self.assertNotIn("매수 추천", message)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(FinancialSnapshot.objects.count(), 1)
        self.assertEqual(LensScore.objects.count(), 1)


class WatchlistMessageTests(TestCase):
    def test_watch_adds_company_to_watchlist(self):
        lookup_result = CompanyLookupResult(
            company=Company(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ"),
            snapshot_values={
                "source": "yfinance",
                "source_url": "https://finance.yahoo.com/quote/AAPL",
                "as_of_date": date(2026, 5, 21),
                "period_end_date": None,
                "period_type": FinancialSnapshot.PeriodType.UNKNOWN,
                "currency": "USD",
                "price": Decimal("190.12"),
                "market_cap": None,
                "per": None,
                "pbr": None,
                "psr": None,
                "roe": None,
                "roic": None,
                "revenue": None,
                "operating_income": None,
                "net_income": None,
                "eps": None,
                "operating_cash_flow": None,
                "free_cash_flow": None,
                "total_debt": None,
                "cash": None,
                "missing_fields": ["roic"],
                "raw_payload": {},
            },
        )
        service = Mock()
        service.lookup.return_value = lookup_result

        with patch("stock_evaluator.users.services.CompanyLookupService", return_value=service):
            message = _watch_message(123456789, "aapl", "george")

        self.assertEqual(message, "AAPL 관심종목에 추가했습니다.")
        self.assertIn("AAPL / Apple Inc.", _watchlist_message(123456789))

    def test_unwatch_removes_company_from_watchlist(self):
        self.test_watch_adds_company_to_watchlist()

        message = _unwatch_message(123456789, "AAPL")

        self.assertEqual(message, "AAPL 관심종목에서 제거했습니다.")
        self.assertEqual(_watchlist_message(123456789), "관심종목이 없습니다. /watch AAPL 형식으로 추가하세요.")
