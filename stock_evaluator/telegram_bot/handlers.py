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


@require_allowed_chat
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(start_message())


@require_allowed_chat
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text(help_message())


@require_allowed_chat
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message:
        await update.effective_message.reply_text("pong")


@require_allowed_chat
async def company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ticker = context.args[0] if context and context.args else ""
    try:
        message = await sync_to_async(_company_report_message)(ticker)
    except (ValueError, MarketDataError) as exc:
        message = render_error_message(user_safe_lookup_error(exc))

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
