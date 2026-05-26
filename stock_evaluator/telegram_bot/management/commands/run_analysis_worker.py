import time
import traceback
from urllib import parse, request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stock_evaluator.telegram_bot.handlers import _company_report_message
from stock_evaluator.telegram_bot.services import (
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
    next_pending_job,
    reset_stale_running_jobs,
)

TELEGRAM_MESSAGE_CHUNK_SIZE = 3900


class Command(BaseCommand):
    help = "Run the analysis worker queue."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process one pending job and exit.")
        parser.add_argument("--sleep-seconds", type=float, default=2.0)

    def handle(self, *args, **options):
        del args
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is required.")

        reset_count = reset_stale_running_jobs()
        if reset_count:
            self.stdout.write(f"Reset stale running jobs: {reset_count}")
        self.stdout.write("Starting analysis worker...")

        while True:
            processed = self._process_next_job(settings.TELEGRAM_BOT_TOKEN)
            if options["once"]:
                return
            if not processed:
                time.sleep(options["sleep_seconds"])

    def _process_next_job(self, bot_token: str) -> bool:
        job = next_pending_job()
        if job is None:
            return False

        mark_job_running(job)
        try:
            message = _company_report_message(job.ticker, job.investor)
            _send_message(bot_token, job.chat_id, message)
        except Exception as exc:
            self.stderr.write(traceback.format_exc())
            error_message = str(exc) or exc.__class__.__name__
            mark_job_failed(job, error_message)
            try:
                _send_message(bot_token, job.chat_id, "분석 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
            except Exception:
                self.stderr.write(traceback.format_exc())
                pass
            return True

        mark_job_succeeded(job, message)
        return True


def _send_message(bot_token: str, chat_id: int, text: str) -> None:
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for start in range(0, len(text), TELEGRAM_MESSAGE_CHUNK_SIZE):
        payload = parse.urlencode(
            {
                "chat_id": chat_id,
                "text": text[start : start + TELEGRAM_MESSAGE_CHUNK_SIZE],
            }
        ).encode()
        http_request = request.Request(api_url, data=payload, method="POST")
        with request.urlopen(http_request, timeout=30) as response:
            response.read()
