from django.conf import settings
from telegram.ext import Application, CommandHandler

from stock_evaluator.telegram_bot import handlers


class TelegramBotConfigError(RuntimeError):
    pass


def build_application(token: str | None = None) -> Application:
    bot_token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise TelegramBotConfigError("TELEGRAM_BOT_TOKEN is required.")

    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("ping", handlers.ping))
    return application
