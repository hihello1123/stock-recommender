from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fetch watchlist news and send the daily Telegram report."

    def add_arguments(self, parser):
        parser.add_argument("--per-source", type=int, default=5)
        parser.add_argument("--date", help="Report date in YYYY-MM-DD format. Defaults to today.")

    def handle(self, *args, **options):
        del args
        call_command("fetch_watchlist_news", per_source=options["per_source"], stdout=self.stdout, stderr=self.stderr)
        report_options = {}
        if options["date"]:
            report_options["date"] = options["date"]
        call_command("send_daily_watchlist_report", stdout=self.stdout, stderr=self.stderr, **report_options)
