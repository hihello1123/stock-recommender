from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from stock_evaluator.companies.models import LensScore
from stock_evaluator.companies.services.company_lookup import (
    CompanyLookupService,
    save_company_report_data,
    user_safe_lookup_error,
)
from stock_evaluator.companies.services.market_data_client import MarketDataError
from stock_evaluator.lenses.quality_v1 import QualityLensV1
from stock_evaluator.reports.llm_explainer import (
    INVESTOR_LABELS,
    LocalLLMExplanationError,
    generate_investor_explanation,
)
from stock_evaluator.reports.telegram_renderer import render_company_report, render_error_message
from stock_evaluator.telegram_bot.auth import is_allowed_chat, require_allowed_chat
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
        message, keyboard = await sync_to_async(_company_preview_response)(ticker)
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))
        keyboard = None

    if update.effective_message:
        await update.effective_message.reply_text(message, reply_markup=keyboard)


@require_allowed_chat
async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ticker = context.args[0] if context and context.args else ""
    try:
        message, keyboard = await sync_to_async(_watch_preview_response)(ticker)
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))
        keyboard = None

    if update.effective_message:
        await update.effective_message.reply_text(message, reply_markup=keyboard)


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    if not is_allowed_chat(update):
        await query.edit_message_text("개인 채팅에서만 사용할 수 있습니다.")
        return

    action, values = _parse_callback_data(query.data or "")
    try:
        if action == "company_report":
            if len(values) != 2:
                message = "알 수 없는 요청입니다. 다시 명령을 보내주세요."
                await query.edit_message_text(message)
                return
            investor, ticker = values
            await query.edit_message_text(_loading_message(ticker, investor))
            message = await sync_to_async(_company_report_message)(ticker, investor)
            if query.message:
                await query.message.reply_text(message)
            else:
                await query.edit_message_text(message)
            return
        elif action == "watch_add":
            ticker = values[0] if values else ""
            message = await sync_to_async(_watch_message)(
                update.effective_chat.id,
                ticker,
                _username(update),
            )
        else:
            message = "알 수 없는 요청입니다. 다시 명령을 보내주세요."
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))

    await query.edit_message_text(message)


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


def _company_report_message(ticker: str, investor: str = "buffett") -> str:
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
    try:
        explanation = generate_investor_explanation(saved_company, snapshot, score_result, investor)
    except LocalLLMExplanationError:
        explanation = "로컬 LLM 설명 생성에 실패했습니다. 로컬 모델 서버 상태를 확인해주세요."
    try:
        return render_company_report(saved_company, snapshot, score_result, explanation=explanation)
    except ValueError:
        return render_company_report(
            saved_company,
            snapshot,
            score_result,
            explanation="로컬 LLM 설명에 제한된 투자 조언 표현이 포함되어 생략했습니다.",
        )


def _company_preview_response(ticker: str) -> tuple[str, InlineKeyboardMarkup]:
    result = CompanyLookupService().lookup(ticker)
    message = _company_confirmation_message(
        result.company,
        action="어떤 관점으로 분석할까요?",
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Buffett", callback_data=f"company_report:buffett:{result.company.ticker}"),
                InlineKeyboardButton("Graham", callback_data=f"company_report:graham:{result.company.ticker}"),
            ],
            [
                InlineKeyboardButton("Lynch", callback_data=f"company_report:lynch:{result.company.ticker}"),
                InlineKeyboardButton("Munger", callback_data=f"company_report:munger:{result.company.ticker}"),
            ],
        ]
    )
    return message, keyboard


def _watch_message(chat_id: int, ticker: str, username: str = "") -> str:
    item, created = watch_ticker(chat_id, ticker, username)
    if created:
        return f"{item.company.ticker} 관심종목에 추가했습니다."
    return f"{item.company.ticker} 이미 관심종목에 있습니다."


def _watch_preview_response(ticker: str) -> tuple[str, InlineKeyboardMarkup]:
    result = CompanyLookupService().lookup(ticker)
    message = _company_confirmation_message(
        result.company,
        action="관심종목에 추가할까요?",
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("맞아요, 추가하기", callback_data=f"watch_add:{result.company.ticker}")]]
    )
    return message, keyboard


def _company_confirmation_message(company, *, action: str) -> str:
    lines = [
        f"이 회사를 찾는 게 맞나요? {action}",
        f"{company.ticker} / {company.name}",
    ]
    if company.exchange:
        lines.append(f"거래소: {company.exchange}")
    if company.sector:
        lines.append(f"섹터: {company.sector}")
    if company.industry:
        lines.append(f"산업: {company.industry}")
    if company.country:
        lines.append(f"국가: {company.country}")
    lines.append("아니면 다른 티커로 다시 명령을 보내주세요.")
    return "\n".join(lines)


def _loading_message(ticker: str, investor: str) -> str:
    investor_label = INVESTOR_LABELS.get(investor, investor)
    return "\n".join(
        [
            f"{ticker} / {investor_label} 관점 분석을 준비하고 있습니다.",
            "자료 조사중...",
            "완료되면 새 메시지로 리포트를 보내드릴게요.",
        ]
    )


def _parse_callback_data(data: str) -> tuple[str, list[str]]:
    action, separator, payload = data.partition(":")
    if not separator:
        return "", []
    values = [value for value in payload.split(":") if value]
    if action == "company_report" and len(values) == 2 and values[0] not in INVESTOR_LABELS:
        return "", []
    return action, values


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
