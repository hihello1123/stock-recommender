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


class SecIngestJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="sec_ingest_jobs",
        null=True,
        blank=True,
    )
    ticker = models.CharField(max_length=16)
    cik = models.CharField(max_length=16, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    periods_saved = models.PositiveSmallIntegerField(default=0)
    missing_fields_summary = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["ticker", "status"]),
            models.Index(fields=["cik"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["ticker"],
                condition=models.Q(status__in=["pending", "running"]),
                name="unique_active_sec_ingest_job",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ticker} sec-ingest {self.status}"


class SecIngestSubscriber(models.Model):
    job = models.ForeignKey(
        SecIngestJob,
        on_delete=models.CASCADE,
        related_name="subscribers",
    )
    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "chat_id"],
                name="unique_sec_ingest_subscriber_job_chat",
            ),
        ]
        indexes = [
            models.Index(fields=["chat_id", "created_at"]),
            models.Index(fields=["notified_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.chat_id} waiting for {self.job.ticker}"


class NewsArticle(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="news_articles",
    )
    source = models.CharField(max_length=64)
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["url"], name="unique_news_article_url"),
        ]
        indexes = [
            models.Index(fields=["company", "published_at"], name="telegram_bo_company_8c4a93_idx"),
            models.Index(fields=["source", "fetched_at"], name="telegram_bo_source_b34f81_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.company.ticker} {self.source} {self.title}"


class DailyWatchlistReport(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        "users.TelegramUser",
        on_delete=models.CASCADE,
        related_name="daily_watchlist_reports",
    )
    report_date = models.DateField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "report_date"],
                name="unique_daily_watchlist_report_user_date",
            ),
        ]
        indexes = [
            models.Index(fields=["report_date", "status"], name="telegram_bo_report__58542b_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.chat_id} {self.report_date} {self.status}"


class DailyCompanyNewsAnalysis(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FALLBACK = "fallback", "Fallback"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="daily_news_analyses",
    )
    report_date = models.DateField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "report_date"],
                name="unique_daily_company_news_analysis",
            ),
        ]
        indexes = [
            models.Index(fields=["report_date", "status"], name="telegram_bo_report__436077_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.company.ticker} {self.report_date} {self.status}"
