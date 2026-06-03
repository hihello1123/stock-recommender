import traceback

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.utils import timezone

from stock_evaluator.telegram_bot.daily_news import (
    build_daily_watchlist_report,
    send_telegram_message,
)
from stock_evaluator.telegram_bot.models import DailyWatchlistReport
from stock_evaluator.users.models import TelegramUser


class Command(BaseCommand):
    help = "Send the daily watchlist news report to Telegram users."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Report date in YYYY-MM-DD format. Defaults to today.")

    def handle(self, *args, **options):
        del args
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is required.")

        report_date = (
            timezone.datetime.strptime(options["date"], "%Y-%m-%d").date()
            if options["date"]
            else timezone.localdate()
        )
        users = TelegramUser.objects.filter(watchlist_items__isnull=False).distinct().order_by("chat_id")
        sent_count = 0
        skipped_count = 0
        failed_count = 0

        for user in users:
            if DailyWatchlistReport.objects.filter(user=user, report_date=report_date).exists():
                skipped_count += 1
                continue

            message = build_daily_watchlist_report(user, report_date=report_date)
            if not message:
                _create_report(user, report_date, "", DailyWatchlistReport.Status.SKIPPED)
                skipped_count += 1
                continue

            try:
                send_telegram_message(settings.TELEGRAM_BOT_TOKEN, user.chat_id, message)
            except Exception as exc:
                self.stderr.write(traceback.format_exc())
                _create_report(
                    user,
                    report_date,
                    message,
                    DailyWatchlistReport.Status.FAILED,
                    str(exc) or exc.__class__.__name__,
                )
                failed_count += 1
                continue

            _create_report(
                user,
                report_date,
                message,
                DailyWatchlistReport.Status.SENT,
                sent_at=timezone.now(),
            )
            sent_count += 1

        self.stdout.write(
            f"Daily watchlist reports: sent={sent_count} skipped={skipped_count} failed={failed_count}"
        )


def _create_report(user, report_date, message, status, error_message="", sent_at=None):
    try:
        return DailyWatchlistReport.objects.create(
            user=user,
            report_date=report_date,
            message=message,
            status=status,
            error_message=error_message,
            sent_at=sent_at,
        )
    except IntegrityError:
        return None
