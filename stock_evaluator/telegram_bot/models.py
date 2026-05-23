from django.db import models


class AnalysisJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField(null=True, blank=True)
    ticker = models.CharField(max_length=16)
    investor = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result_message = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["chat_id", "ticker", "investor", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["chat_id", "ticker", "investor"],
                condition=models.Q(status__in=["pending", "running"]),
                name="unique_active_analysis_job",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.chat_id} {self.ticker} {self.investor} {self.status}"
