import asyncio
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from telegram.constants import ChatType

from stock_evaluator.companies.models import Company, FinancialSnapshot, LensScore
from stock_evaluator.companies.services.company_lookup import CompanyLookupResult
from stock_evaluator.telegram_bot.auth import ACCESS_DENIED_MESSAGE, is_allowed_chat
from stock_evaluator.telegram_bot.bot import TelegramBotConfigError, build_application
from stock_evaluator.telegram_bot.handlers import (
    _company_report_message,
    _natural_language_response,
    _remember_user,
    _ticker_search_message,
    _unwatch_message,
    _watch_message,
    _watchlist_message,
    company,
    help_command,
    handle_confirmation,
    handle_text,
    ping,
    start,
    ticker,
)
from stock_evaluator.telegram_bot.messages import help_message, start_message
from stock_evaluator.telegram_bot.models import AnalysisJob
from stock_evaluator.telegram_bot.natural_language import (
    NaturalLanguageRoute,
    route_natural_language_message,
    should_route_to_llm,
)
from stock_evaluator.telegram_bot.services import (
    enqueue_analysis_job,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
    queue_position,
    reset_stale_running_jobs,
)
from stock_evaluator.users.models import TelegramUser


class FakeMessage:
    def __init__(self, message_id: int = 555, text: str = ""):
        self.message_id = message_id
        self.text = text
        self.replies: list[str] = []
        self.reply_markups = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.replies.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))


class FakeCallbackQuery:
    def __init__(self, data: str):
        self.data = data
        self.message = FakeMessage()
        self.answered = False
        self.edits: list[str] = []

    async def answer(self) -> None:
        self.answered = True

    async def edit_message_text(self, text: str) -> None:
        self.edits.append(text)


class FakeChat:
    def __init__(self, chat_id: int, chat_type: str = ChatType.PRIVATE):
        self.id = chat_id
        self.type = chat_type


class FakeUser:
    def __init__(self, username: str = "george"):
        self.username = username


class FakeUpdate:
    def __init__(
        self,
        chat_id: int = 123456789,
        chat_type: str = ChatType.PRIVATE,
        callback_query: FakeCallbackQuery | None = None,
    ):
        self.effective_message = FakeMessage()
        self.effective_chat = FakeChat(chat_id, chat_type)
        self.effective_user = FakeUser()
        self.callback_query = callback_query
        if callback_query is None:
            self.effective_message = FakeMessage(text="")


class FakeContext:
    def __init__(self, args=None):
        self.args = args or []


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return BytesIO(json_bytes(self.payload))

    def __exit__(self, exc_type, exc, traceback):
        return False


def json_bytes(payload: dict) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")


class TelegramMessageTests(SimpleTestCase):
    def test_start_message_mentions_help(self):
        self.assertIn("/help", start_message())

    def test_help_message_lists_basic_commands(self):
        message = help_message()

        self.assertIn("/start", message)
        self.assertIn("/help", message)
        self.assertIn("/ping", message)
        self.assertIn("/ticker", message)
        self.assertIn("/company", message)
        self.assertIn("/watch", message)
        self.assertIn("/unwatch", message)
        self.assertIn("/watchlist", message)


class TelegramAuthTests(SimpleTestCase):
    def test_private_chat_passes(self):
        self.assertTrue(is_allowed_chat(FakeUpdate()))

    def test_group_chat_fails(self):
        self.assertFalse(is_allowed_chat(FakeUpdate(chat_type=ChatType.GROUP)))


class NaturalLanguageRouterTests(SimpleTestCase):
    def test_filter_allows_stock_related_messages(self):
        self.assertTrue(should_route_to_llm("애플 찾아줘"))
        self.assertTrue(should_route_to_llm("AAPL 분석해줘"))
        self.assertTrue(should_route_to_llm("관심종목 보여줘"))

    def test_filter_blocks_sensitive_or_unrelated_messages(self):
        self.assertFalse(should_route_to_llm("비밀번호는 1234야"))
        self.assertFalse(should_route_to_llm("오늘 기분이 안 좋은데 위로해줘"))

    @override_settings(LOCAL_LLM_MODEL="")
    def test_router_returns_unknown_when_model_is_disabled(self):
        route = route_natural_language_message("애플 분석해줘")

        self.assertEqual(route.intent, "unknown")

    @override_settings(LOCAL_LLM_MODEL="mistral-small3.2:24b")
    def test_router_parses_model_json_response(self):
        response = {
            "message": {
                "content": (
                    '{"intent":"analyze_company","query":"",'
                    '"ticker":"aapl","investor":"buffett"}'
                )
            }
        }

        with patch(
            "stock_evaluator.telegram_bot.natural_language.request.urlopen",
            return_value=FakeHTTPResponse(response),
        ):
            route = route_natural_language_message("AAPL 버핏 관점으로 분석해줘")

        self.assertEqual(route.intent, "analyze_company")
        self.assertEqual(route.ticker, "AAPL")
        self.assertEqual(route.investor, "buffett")

    @override_settings(LOCAL_LLM_MODEL="mistral-small3.2:24b")
    def test_router_does_not_call_model_for_blocked_message(self):
        with patch("stock_evaluator.telegram_bot.natural_language.request.urlopen") as urlopen:
            route = route_natural_language_message("오늘 기분이 안 좋은데 위로해줘")

        self.assertEqual(route.intent, "unknown")
        urlopen.assert_not_called()


class TelegramHandlerTests(TestCase):
    def test_ping_replies_pong(self):
        update = FakeUpdate()

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"):
            asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, ["pong"])

    def test_start_replies_with_start_message(self):
        update = FakeUpdate()

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"):
            asyncio.run(start(update, None))

        self.assertEqual(update.effective_message.replies, [start_message()])

    def test_help_replies_with_help_message(self):
        update = FakeUpdate()

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"):
            asyncio.run(help_command(update, None))

        self.assertEqual(update.effective_message.replies, [help_message()])

    def test_group_chat_gets_access_denied(self):
        update = FakeUpdate(chat_type=ChatType.GROUP)

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, [ACCESS_DENIED_MESSAGE])

    def test_remember_user_saves_public_user(self):
        _remember_user(123456789, "george")

        user = TelegramUser.objects.get(chat_id=123456789)
        self.assertEqual(user.username, "george")
        self.assertTrue(user.is_allowed)


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
            {"start", "help", "ping", "ticker", "company", "watch", "unwatch", "watchlist"},
        )


class CompanyCommandTests(TestCase):
    def test_text_message_uses_natural_language_response(self):
        update = FakeUpdate()
        update.effective_message.text = "애플 분석해줘"

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"), patch(
            "stock_evaluator.telegram_bot.handlers._natural_language_response",
            return_value=("AAPL / Buffett 관점 분석을 준비하고 있습니다.", None),
        ):
            asyncio.run(handle_text(update, None))

        self.assertEqual(update.effective_message.replies, ["AAPL / Buffett 관점 분석을 준비하고 있습니다."])

    def test_ticker_replies_with_search_results(self):
        with patch("stock_evaluator.telegram_bot.handlers._remember_user"), patch(
            "stock_evaluator.telegram_bot.handlers._ticker_search_message",
            return_value="'apple' 티커 검색 결과\n1. AAPL / Apple Inc.",
        ):
            update = FakeUpdate()
            asyncio.run(ticker(update, FakeContext(args=["apple"])))

        self.assertEqual(update.effective_message.replies, ["'apple' 티커 검색 결과\n1. AAPL / Apple Inc."])

    def test_ticker_missing_query_replies_with_safe_error(self):
        update = FakeUpdate()

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"):
            asyncio.run(ticker(update, FakeContext(args=[])))

        self.assertEqual(update.effective_message.replies, ["회사명을 입력해주세요. 예: /ticker apple"])

    def test_company_replies_with_confirmation_preview(self):
        with patch("stock_evaluator.telegram_bot.handlers._remember_user"), patch(
            "stock_evaluator.telegram_bot.handlers._company_preview_response",
            return_value=("이 회사를 찾는 게 맞나요? 어떤 관점으로 분석할까요?", "keyboard"),
        ):
            update = FakeUpdate()
            asyncio.run(company(update, FakeContext(args=["AAPL"])))

        self.assertEqual(update.effective_message.replies, ["이 회사를 찾는 게 맞나요? 어떤 관점으로 분석할까요?"])
        self.assertEqual(update.effective_message.reply_markups, ["keyboard"])

    def test_company_missing_ticker_replies_with_safe_error(self):
        update = FakeUpdate()

        with patch("stock_evaluator.telegram_bot.handlers._remember_user"):
            asyncio.run(company(update, FakeContext(args=[])))

        self.assertEqual(update.effective_message.replies, ["티커를 입력해주세요. 예: /company AAPL"])

    def test_company_confirmation_enqueues_analysis_job(self):
        update = FakeUpdate(callback_query=FakeCallbackQuery("company_report:buffett:AAPL"))

        asyncio.run(handle_confirmation(update, None))

        job = AnalysisJob.objects.get()
        self.assertEqual(job.chat_id, update.effective_chat.id)
        self.assertEqual(job.message_id, update.callback_query.message.message_id)
        self.assertEqual(job.ticker, "AAPL")
        self.assertEqual(job.investor, "buffett")
        self.assertTrue(update.callback_query.answered)
        self.assertEqual(
            update.callback_query.edits,
            [
                "\n".join(
                    [
                        "AAPL / Buffett 관점 분석을 준비하고 있습니다.",
                        "자료 조사중...",
                        "현재 대기 순서: 1번째",
                        "완료되면 새 메시지로 리포트를 보내드릴게요.",
                    ]
                )
            ],
        )


class AnalysisJobServiceTests(TestCase):
    def test_enqueue_analysis_job_normalizes_input(self):
        job, created, position = enqueue_analysis_job(
            chat_id=123,
            message_id=456,
            ticker=" aapl ",
            investor=" Buffett ",
        )

        self.assertTrue(created)
        self.assertEqual(position, 1)
        self.assertEqual(job.ticker, "AAPL")
        self.assertEqual(job.investor, "buffett")

    def test_enqueue_analysis_job_reuses_active_duplicate(self):
        first, _, _ = enqueue_analysis_job(chat_id=123, message_id=1, ticker="AAPL", investor="buffett")
        second, created, position = enqueue_analysis_job(chat_id=123, message_id=2, ticker="AAPL", investor="buffett")

        self.assertFalse(created)
        self.assertEqual(second.id, first.id)
        self.assertEqual(position, 1)
        self.assertEqual(AnalysisJob.objects.count(), 1)

    def test_queue_position_counts_active_jobs_in_order(self):
        first, _, _ = enqueue_analysis_job(chat_id=1, message_id=1, ticker="AAPL", investor="buffett")
        second, _, _ = enqueue_analysis_job(chat_id=2, message_id=2, ticker="MSFT", investor="graham")
        mark_job_succeeded(first, "done")

        self.assertEqual(queue_position(first), 0)
        self.assertEqual(queue_position(second), 1)

    def test_reset_stale_running_jobs_returns_jobs_to_pending(self):
        job, _, _ = enqueue_analysis_job(chat_id=123, message_id=1, ticker="AAPL", investor="buffett")
        mark_job_running(job)
        AnalysisJob.objects.filter(id=job.id).update(started_at=timezone.now() - timedelta(minutes=31))

        reset_count = reset_stale_running_jobs(stale_after_minutes=30)

        job.refresh_from_db()
        self.assertEqual(reset_count, 1)
        self.assertEqual(job.status, AnalysisJob.Status.PENDING)
        self.assertIsNone(job.started_at)

    def test_mark_job_failed_records_error(self):
        job, _, _ = enqueue_analysis_job(chat_id=123, message_id=1, ticker="AAPL", investor="buffett")

        mark_job_failed(job, "boom")

        job.refresh_from_db()
        self.assertEqual(job.status, AnalysisJob.Status.FAILED)
        self.assertEqual(job.error_message, "boom")
        self.assertIsNotNone(job.finished_at)


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

        with patch("stock_evaluator.telegram_bot.handlers.CompanyLookupService", return_value=service), patch(
            "stock_evaluator.telegram_bot.handlers.generate_investor_explanation",
            return_value="[Buffett]\n- 테스트 설명",
        ) as explainer:
            message = _company_report_message("AAPL", "buffett")

        self.assertIn("[AAPL / Apple Inc.]", message)
        self.assertIn("Quality Lens v1", message)
        self.assertIn("[Buffett]\n- 테스트 설명", message)
        self.assertNotIn("매수 추천", message)
        explainer.assert_called_once()
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(FinancialSnapshot.objects.count(), 1)
        self.assertEqual(LensScore.objects.count(), 1)


class TickerSearchMessageTests(TestCase):
    def test_ticker_search_message_lists_results_and_next_commands(self):
        result = SimpleNamespace(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ", quote_type="EQUITY")
        service = Mock()
        service.search.return_value = [result]

        with patch("stock_evaluator.telegram_bot.handlers.YFinanceCompanySearchClient", return_value=service):
            message = _ticker_search_message("apple")

        self.assertIn("1. AAPL / Apple Inc. (NASDAQ / EQUITY)", message)
        self.assertIn("/company AAPL", message)
        self.assertIn("/watch AAPL", message)

    def test_ticker_search_message_handles_empty_results(self):
        service = Mock()
        service.search.return_value = []

        with patch("stock_evaluator.telegram_bot.handlers.YFinanceCompanySearchClient", return_value=service):
            message = _ticker_search_message("unknown")

        self.assertEqual(message, "'unknown' 검색 결과가 없습니다.")


class NaturalLanguageResponseTests(TestCase):
    def test_analyze_company_with_ticker_enqueues_job(self):
        with patch(
            "stock_evaluator.telegram_bot.handlers.route_natural_language_message",
            return_value=NaturalLanguageRoute(intent="analyze_company", ticker="AAPL", investor="munger"),
        ):
            message, keyboard = _natural_language_response(987654321, 555, "AAPL 멍거 관점으로 분석해줘")

        self.assertIsNone(keyboard)
        self.assertIn("AAPL / Munger 관점 분석을 준비하고 있습니다.", message)
        job = AnalysisJob.objects.get(chat_id=987654321, ticker="AAPL", investor="munger")
        self.assertEqual(job.ticker, "AAPL")
        self.assertEqual(job.investor, "munger")

    def test_analyze_company_with_name_falls_back_to_ticker_search(self):
        with patch(
            "stock_evaluator.telegram_bot.handlers.route_natural_language_message",
            return_value=NaturalLanguageRoute(intent="analyze_company", query="애플"),
        ), patch(
            "stock_evaluator.telegram_bot.handlers._ticker_search_message",
            return_value="'애플' 티커 검색 결과",
        ):
            message, keyboard = _natural_language_response(987654321, 555, "애플 분석해줘")

        self.assertIsNone(keyboard)
        self.assertEqual(message, "'애플' 티커 검색 결과")
        self.assertFalse(AnalysisJob.objects.filter(chat_id=987654321, ticker="AAPL").exists())

    def test_show_watchlist_returns_watchlist(self):
        with patch(
            "stock_evaluator.telegram_bot.handlers.route_natural_language_message",
            return_value=NaturalLanguageRoute(intent="show_watchlist"),
        ):
            message, keyboard = _natural_language_response(123456789, 555, "관심종목 보여줘")

        self.assertIsNone(keyboard)
        self.assertEqual(message, "관심종목이 없습니다. /watch AAPL 형식으로 추가하세요.")


class AnalysisWorkerTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="123456:ABCDEF")
    def test_worker_processes_one_pending_job(self):
        job, _, _ = enqueue_analysis_job(chat_id=123, message_id=1, ticker="AAPL", investor="buffett")

        with patch(
            "stock_evaluator.telegram_bot.management.commands.run_analysis_worker._company_report_message",
            return_value="report",
        ), patch("stock_evaluator.telegram_bot.management.commands.run_analysis_worker._send_message") as send_message:
            call_command("run_analysis_worker", "--once", stderr=StringIO())

        job.refresh_from_db()
        self.assertEqual(job.status, AnalysisJob.Status.SUCCEEDED)
        self.assertEqual(job.result_message, "report")
        send_message.assert_called_once()

    @override_settings(TELEGRAM_BOT_TOKEN="123456:ABCDEF")
    def test_worker_marks_job_failed_when_report_generation_fails(self):
        job, _, _ = enqueue_analysis_job(chat_id=123, message_id=1, ticker="AAPL", investor="buffett")

        with patch(
            "stock_evaluator.telegram_bot.management.commands.run_analysis_worker._company_report_message",
            side_effect=RuntimeError("failed"),
        ), patch("stock_evaluator.telegram_bot.management.commands.run_analysis_worker._send_message") as send_message:
            stderr = StringIO()
            call_command("run_analysis_worker", "--once", stderr=stderr)

        job.refresh_from_db()
        self.assertEqual(job.status, AnalysisJob.Status.FAILED)
        self.assertEqual(job.error_message, "failed")
        self.assertIn("RuntimeError: failed", stderr.getvalue())
        send_message.assert_called_once_with(ANY, 123, "분석 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")


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
