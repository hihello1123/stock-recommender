from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from stock_evaluator.telegram_bot.models import AnalysisJob


ACTIVE_STATUSES = [AnalysisJob.Status.PENDING, AnalysisJob.Status.RUNNING]


def enqueue_analysis_job(
    *,
    chat_id: int,
    message_id: int | None,
    ticker: str,
    investor: str,
) -> tuple[AnalysisJob, bool, int]:
    normalized_ticker = ticker.strip().upper()
    normalized_investor = investor.strip().lower()
    try:
        with transaction.atomic():
            existing = (
                AnalysisJob.objects.filter(
                    chat_id=chat_id,
                    ticker=normalized_ticker,
                    investor=normalized_investor,
                    status__in=ACTIVE_STATUSES,
                )
                .order_by("created_at")
                .first()
            )
            if existing:
                return existing, False, queue_position(existing)

            job = AnalysisJob.objects.create(
                chat_id=chat_id,
                message_id=message_id,
                ticker=normalized_ticker,
                investor=normalized_investor,
            )
    except IntegrityError:
        existing = (
            AnalysisJob.objects.filter(
                chat_id=chat_id,
                ticker=normalized_ticker,
                investor=normalized_investor,
                status__in=ACTIVE_STATUSES,
            )
            .order_by("created_at")
            .first()
        )
        if existing:
            return existing, False, queue_position(existing)
        raise
    return job, True, queue_position(job)


def queue_position(job: AnalysisJob) -> int:
    if job.status not in ACTIVE_STATUSES:
        return 0
    return (
        AnalysisJob.objects.filter(
            status__in=ACTIVE_STATUSES,
            created_at__lte=job.created_at,
        ).count()
    )


def next_pending_job() -> AnalysisJob | None:
    return AnalysisJob.objects.filter(status=AnalysisJob.Status.PENDING).order_by("created_at").first()


def mark_job_running(job: AnalysisJob) -> AnalysisJob:
    job.status = AnalysisJob.Status.RUNNING
    job.attempts += 1
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "attempts", "started_at", "error_message"])
    return job


def mark_job_succeeded(job: AnalysisJob, result_message: str) -> AnalysisJob:
    job.status = AnalysisJob.Status.SUCCEEDED
    job.result_message = result_message
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "result_message", "finished_at"])
    return job


def mark_job_failed(job: AnalysisJob, error_message: str) -> AnalysisJob:
    job.status = AnalysisJob.Status.FAILED
    job.error_message = error_message
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at"])
    return job


def reset_stale_running_jobs(*, stale_after_minutes: int = 30) -> int:
    cutoff = timezone.now() - timedelta(minutes=stale_after_minutes)
    return AnalysisJob.objects.filter(
        status=AnalysisJob.Status.RUNNING,
        started_at__lt=cutoff,
    ).update(status=AnalysisJob.Status.PENDING, started_at=None)
