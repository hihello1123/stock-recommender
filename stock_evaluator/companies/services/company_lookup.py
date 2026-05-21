from dataclasses import dataclass

from stock_evaluator.companies.models import Company
from stock_evaluator.companies.services.data_normalizer import normalize_market_data
from stock_evaluator.companies.services.market_data_client import (
    MarketDataError,
    MarketDataPayload,
    YFinanceMarketDataClient,
    normalize_ticker,
)
from stock_evaluator.instruments.classifier import classify_instrument_type


@dataclass(frozen=True)
class CompanyLookupResult:
    company: Company
    snapshot_values: dict


class CompanyLookupService:
    def __init__(self, market_data_client: YFinanceMarketDataClient | None = None):
        self.market_data_client = market_data_client or YFinanceMarketDataClient()

    def lookup(self, ticker: str) -> CompanyLookupResult:
        normalized_ticker = normalize_ticker(ticker)
        payload = self.market_data_client.fetch(normalized_ticker)
        company = get_or_build_company(payload)
        snapshot_values = normalize_market_data(payload)
        return CompanyLookupResult(company=company, snapshot_values=snapshot_values)


def get_or_build_company(payload: MarketDataPayload) -> Company:
    info = payload.info
    exchange = info.get("exchange") or info.get("fullExchangeName") or ""
    instrument_type = classify_instrument_type(
        sector=info.get("sector") or "",
        industry=info.get("industry") or "",
        quote_type=info.get("quoteType") or "",
    )
    return Company(
        ticker=payload.ticker,
        name=info.get("longName") or info.get("shortName") or payload.ticker,
        exchange=exchange,
        sector=info.get("sector") or "",
        industry=info.get("industry") or "",
        country=info.get("country") or "",
        cik=str(info.get("cik") or ""),
        instrument_type=instrument_type,
    )


def save_company_report_data(result: CompanyLookupResult):
    company_values = {
        "name": result.company.name,
        "sector": result.company.sector,
        "industry": result.company.industry,
        "country": result.company.country,
        "cik": result.company.cik,
        "instrument_type": result.company.instrument_type,
        "is_active": result.company.is_active,
    }
    company, _ = Company.objects.update_or_create(
        ticker=result.company.ticker,
        exchange=result.company.exchange,
        defaults=company_values,
    )
    snapshot, _ = company.financial_snapshots.update_or_create(
        source=result.snapshot_values["source"],
        as_of_date=result.snapshot_values["as_of_date"],
        period_end_date=result.snapshot_values["period_end_date"],
        period_type=result.snapshot_values["period_type"],
        defaults={
            key: value
            for key, value in result.snapshot_values.items()
            if key not in {"source", "as_of_date", "period_end_date", "period_type"}
        },
    )
    return company, snapshot


def user_safe_lookup_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return "티커를 입력해주세요. 예: /company AAPL"
    if isinstance(exc, MarketDataError):
        return "데이터 조회에 실패했습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요."
    return "회사 조회 중 오류가 발생했습니다."
