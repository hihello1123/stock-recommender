from dataclasses import dataclass, field


@dataclass(frozen=True)
class LensScoreResult:
    lens_name: str
    scoring_version: str
    score: int | None
    grade: str
    confidence: str
    data_completeness: int
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_extra_checks: list[str] = field(default_factory=list)


class InvestorLens:
    name: str
    scoring_version: str

    def evaluate(self, snapshot, *, instrument_type: str) -> LensScoreResult:
        raise NotImplementedError
