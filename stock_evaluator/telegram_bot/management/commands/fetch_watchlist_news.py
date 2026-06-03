from django.core.management.base import BaseCommand

from stock_evaluator.telegram_bot.daily_news import fetch_watchlist_news


class Command(BaseCommand):
    help = "Fetch RSS news for all watchlist companies."

    def add_arguments(self, parser):
        parser.add_argument("--per-source", type=int, default=5)

    def handle(self, *args, **options):
        del args
        saved_count, errors = fetch_watchlist_news(per_source=options["per_source"])
        self.stdout.write(f"Saved news articles: {saved_count}")
        for error in errors:
            self.stderr.write(error)
