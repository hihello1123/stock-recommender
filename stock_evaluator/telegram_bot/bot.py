from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

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
    application.add_handler(CommandHandler("ticker", handlers.ticker))
    application.add_handler(CommandHandler("company", handlers.company))
    application.add_handler(CommandHandler("watch", handlers.watch))
    application.add_handler(CommandHandler("unwatch", handlers.unwatch))
    application.add_handler(CommandHandler("watchlist", handlers.watchlist))
    application.add_handler(CallbackQueryHandler(handlers.handle_confirmation))
    application.add_handler(MessageHandler(filters.COMMAND, handlers.unsupported_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
    return application
