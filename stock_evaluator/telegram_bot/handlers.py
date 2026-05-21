from telegram import Update
from telegram.ext import ContextTypes

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
