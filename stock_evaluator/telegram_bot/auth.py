from collections.abc import Awaitable, Callable
from functools import wraps

from django.conf import settings
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes


ACCESS_DENIED_MESSAGE = "접근 권한이 없습니다."

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


def is_allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None or chat.type != ChatType.PRIVATE:
        return False

    return chat.id in settings.ALLOWED_TELEGRAM_CHAT_IDS


def require_allowed_chat(handler: Handler) -> Handler:
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not is_allowed_chat(update):
            if update.effective_message:
                await update.effective_message.reply_text(ACCESS_DENIED_MESSAGE)
            return

        await handler(update, context)

    return wrapper
