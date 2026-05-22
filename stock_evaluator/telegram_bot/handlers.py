from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes

from stock_evaluator.companies.models import LensScore
from stock_evaluator.companies.services.company_lookup import (
    CompanyLookupService,
    save_company_report_data,
    user_safe_lookup_error,
)
from stock_evaluator.companies.services.market_data_client import MarketDataError
from stock_evaluator.lenses.quality_v1 import QualityLensV1
from stock_evaluator.reports.telegram_renderer import render_company_report, render_error_message
from stock_evaluator.telegram_bot.auth import require_allowed_chat
from stock_evaluator.telegram_bot.messages import help_message, start_message
from stock_evaluator.users.services import (
    get_or_create_telegram_user,
    list_watchlist,
    unwatch_ticker,
    watch_ticker,
)


@require_allowed_chat
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await sync_to_async(_remember_user)(update.effective_chat.id, _username(update))
    if update.effective_message:
        await update.effective_message.reply_text(start_message())


@require_allowed_chat
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await sync_to_async(_remember_user)(update.effective_chat.id, _username(update))
    if update.effective_message:
        await update.effective_message.reply_text(help_message())


@require_allowed_chat
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await sync_to_async(_remember_user)(update.effective_chat.id, _username(update))
    if update.effective_message:
        await update.effective_message.reply_text("pong")


@require_allowed_chat
async def company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ticker = context.args[0] if context and context.args else ""
    try:
        await sync_to_async(_remember_user)(update.effective_chat.id, _username(update))
        message = await sync_to_async(_company_report_message)(ticker)
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))

    if update.effective_message:
        await update.effective_message.reply_text(message)


@require_allowed_chat
async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ticker = context.args[0] if context and context.args else ""
    try:
        message = await sync_to_async(_watch_message)(
            update.effective_chat.id,
            ticker,
            _username(update),
        )
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))

    if update.effective_message:
        await update.effective_message.reply_text(message)


@require_allowed_chat
async def unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ticker = context.args[0] if context and context.args else ""
    try:
        message = await sync_to_async(_unwatch_message)(update.effective_chat.id, ticker)
    except ValueError:
        message = "티커를 입력해주세요. 예: /unwatch AAPL"

    if update.effective_message:
        await update.effective_message.reply_text(message)


@require_allowed_chat
async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = await sync_to_async(_watchlist_message)(update.effective_chat.id)
    if update.effective_message:
        await update.effective_message.reply_text(message)


def _company_report_message(ticker: str) -> str:
    result = CompanyLookupService().lookup(ticker)
    saved_company, snapshot = save_company_report_data(result)
    score_result = QualityLensV1().evaluate(
        snapshot,
        instrument_type=saved_company.instrument_type,
    )
    if score_result.score is not None:
        LensScore.objects.update_or_create(
            company=saved_company,
            snapshot=snapshot,
            lens_name=score_result.lens_name,
            scoring_version=score_result.scoring_version,
            defaults={
                "score": score_result.score,
                "grade": score_result.grade,
                "confidence": score_result.confidence,
                "data_completeness": score_result.data_completeness,
                "passed_rules": score_result.passed_rules,
                "failed_rules": score_result.failed_rules,
                "warnings": score_result.warnings,
                "required_extra_checks": score_result.required_extra_checks,
            },
        )
    return render_company_report(saved_company, snapshot, score_result)


def _watch_message(chat_id: int, ticker: str, username: str = "") -> str:
    item, created = watch_ticker(chat_id, ticker, username)
    if created:
        return f"{item.company.ticker} 관심종목에 추가했습니다."
    return f"{item.company.ticker} 이미 관심종목에 있습니다."


def _unwatch_message(chat_id: int, ticker: str) -> str:
    removed = unwatch_ticker(chat_id, ticker)
    normalized_ticker = ticker.strip().upper()
    if removed:
        return f"{normalized_ticker} 관심종목에서 제거했습니다."
    return f"{normalized_ticker} 관심종목에 없습니다."


def _watchlist_message(chat_id: int) -> str:
    items = list_watchlist(chat_id)
    if not items:
        return "관심종목이 없습니다. /watch AAPL 형식으로 추가하세요."

    lines = ["관심종목"]
    lines.extend(f"- {item.company.ticker} / {item.company.name}" for item in items)
    return "\n".join(lines)


def _username(update: Update) -> str:
    user = update.effective_user
    return user.username if user and user.username else ""


def _remember_user(chat_id: int, username: str = "") -> None:
    get_or_create_telegram_user(chat_id, username, is_allowed=True)
