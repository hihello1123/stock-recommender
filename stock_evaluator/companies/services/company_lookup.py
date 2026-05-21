from dataclasses import dataclass

from stock_evaluator.companies.models import Company
from stock_evaluator.companies.services.data_normalizer import normalize_market_data
from stock_evaluator.companies.services.market_data_client import (
    MarketDataPayload,
    YFinanceMarketDataClient,
    normalize_ticker,
)


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
        company = _company_from_payload(payload)
        snapshot_values = normalize_market_data(payload)
        return CompanyLookupResult(company=company, snapshot_values=snapshot_values)


def _company_from_payload(payload: MarketDataPayload) -> Company:
    info = payload.info
    return Company(
        ticker=payload.ticker,
        name=info.get("longName") or info.get("shortName") or payload.ticker,
        exchange=info.get("exchange") or info.get("fullExchangeName") or "",
        sector=info.get("sector") or "",
        industry=info.get("industry") or "",
        country=info.get("country") or "",
        cik=str(info.get("cik") or ""),
    )
