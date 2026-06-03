from django.db import models


class Company(models.Model):
    class InstrumentType(models.TextChoices):
        COMMON_STOCK = "common_stock", "Common stock"
        REIT = "reit", "REIT"
        ETF = "etf", "ETF"
        FUND = "fund", "Fund"
        SPAC = "spac", "SPAC"
        FINANCIAL = "financial", "Financial"
        UNKNOWN = "unknown", "Unknown"

    ticker = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    exchange = models.CharField(max_length=32)
    sector = models.CharField(max_length=128, blank=True)
    industry = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=64, blank=True)
    cik = models.CharField(max_length=16, blank=True)
    instrument_type = models.CharField(
        max_length=32,
        choices=InstrumentType.choices,
        default=InstrumentType.UNKNOWN,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticker", "exchange"],
                name="unique_company_ticker_exchange",
            ),
        ]
        indexes = [
            models.Index(fields=["ticker"]),
            models.Index(fields=["instrument_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.ticker} ({self.exchange})"


class CompanyAlias(models.Model):
    class Source(models.TextChoices):
        SEED = "seed", "Seed"
        MANUAL = "manual", "Manual"
        GENERATED = "generated", "Generated"

    alias = models.CharField(max_length=128)
    normalized_alias = models.CharField(max_length=128, unique=True)
    ticker = models.CharField(max_length=16)
    company_name = models.CharField(max_length=255, blank=True)
    alternative_tickers = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.SEED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["ticker"], name="companies_c_ticker_f4d9d4_idx"),
            models.Index(fields=["source"], name="companies_c_source_d970e1_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.alias} -> {self.ticker}"


class FinancialSnapshot(models.Model):
    class PeriodType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        QUARTERLY = "quarterly", "Quarterly"
        TTM = "ttm", "Trailing twelve months"
        UNKNOWN = "unknown", "Unknown"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="financial_snapshots",
    )
    source = models.CharField(max_length=64)
    source_url = models.URLField(blank=True)
    as_of_date = models.DateField()
    period_end_date = models.DateField(null=True, blank=True)
    period_type = models.CharField(
        max_length=16,
        choices=PeriodType.choices,
        default=PeriodType.UNKNOWN,
    )
    currency = models.CharField(max_length=8, blank=True)
    price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    market_cap = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    per = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    pbr = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    psr = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    roe = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    roic = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    revenue = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    operating_income = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    net_income = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    eps = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    operating_cash_flow = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        null=True,
        blank=True,
    )
    free_cash_flow = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    total_debt = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    cash = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "source", "as_of_date", "period_end_date", "period_type"],
                name="unique_financial_snapshot_source_period",
            ),
        ]
        indexes = [
            models.Index(fields=["source", "as_of_date"]),
            models.Index(fields=["period_type", "period_end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.ticker} {self.source} {self.as_of_date}"


class FinancialStatementPeriod(models.Model):
    class PeriodType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        QUARTERLY = "quarterly", "Quarterly"

    class FormType(models.TextChoices):
        TEN_K = "10-K", "10-K"
        TEN_K_A = "10-K/A", "10-K/A"
        TEN_Q = "10-Q", "10-Q"
        TEN_Q_A = "10-Q/A", "10-Q/A"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="financial_statement_periods",
    )
    source = models.CharField(max_length=64, default="sec_companyfacts")
    form_type = models.CharField(max_length=8, choices=FormType.choices)
    period_type = models.CharField(max_length=16, choices=PeriodType.choices)
    fiscal_year = models.PositiveSmallIntegerField()
    fiscal_period = models.CharField(max_length=8)
    period_end_date = models.DateField()
    filed_date = models.DateField(null=True, blank=True)
    accession_number = models.CharField(max_length=32)
    currency = models.CharField(max_length=8, blank=True)
    revenue = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    gross_profit = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    operating_income = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    net_income = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    eps_diluted = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    total_assets = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    shareholders_equity = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    current_assets = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    current_liabilities = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    cash = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    operating_cash_flow = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    capital_expenditure = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    dividends_paid = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)
    collected_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "source", "accession_number", "period_end_date", "period_type"],
                name="unique_statement_period_source_accession",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "period_type", "period_end_date"]),
            models.Index(fields=["source", "collected_at"]),
            models.Index(fields=["accession_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.ticker} {self.form_type} {self.period_end_date}"


class LensScore(models.Model):
    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="lens_scores")
    snapshot = models.ForeignKey(
        FinancialSnapshot,
        on_delete=models.CASCADE,
        related_name="lens_scores",
    )
    lens_name = models.CharField(max_length=64)
    scoring_version = models.CharField(max_length=32)
    score = models.PositiveSmallIntegerField()
    grade = models.CharField(max_length=4)
    confidence = models.CharField(max_length=16, choices=Confidence.choices)
    data_completeness = models.PositiveSmallIntegerField()
    passed_rules = models.JSONField(default=list, blank=True)
    failed_rules = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    required_extra_checks = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "snapshot", "lens_name", "scoring_version"],
                name="unique_lens_score_version_per_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["lens_name", "scoring_version"]),
            models.Index(fields=["confidence"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.ticker} {self.lens_name} {self.score}"
