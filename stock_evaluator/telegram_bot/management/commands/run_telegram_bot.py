from django.core.management.base import BaseCommand, CommandError

from stock_evaluator.telegram_bot.bot import TelegramBotConfigError, build_application


class Command(BaseCommand):
    help = "Run the Telegram bot with long polling."

    def handle(self, *args, **options):
        del args, options
        try:
            application = build_application()
        except TelegramBotConfigError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("Starting Telegram bot polling...")
        application.run_polling()
