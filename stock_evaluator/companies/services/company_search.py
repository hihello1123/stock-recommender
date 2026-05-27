from dataclasses import dataclass
from typing import Any

import yfinance as yf

from stock_evaluator.companies.services.market_data_client import MarketDataError


@dataclass(frozen=True)
class CompanySearchResult:
    ticker: str
    name: str
    exchange: str = ""
    quote_type: str = ""


class YFinanceCompanySearchClient:
    def search(self, query: str, limit: int = 5) -> list[CompanySearchResult]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query is required.")

        try:
            search = yf.Search(
                normalized_query,
                max_results=limit,
                news_count=0,
                lists_count=0,
                timeout=10,
                raise_errors=True,
            )
        except Exception as exc:
            raise MarketDataError("Failed to search companies.") from exc

        return _normalize_quotes(search.quotes, limit)


def _normalize_quotes(quotes: list[dict[str, Any]], limit: int) -> list[CompanySearchResult]:
    results = []
    for quote in quotes:
        ticker = str(quote.get("symbol") or "").strip().upper()
        if not ticker:
            continue

        name = str(quote.get("longname") or quote.get("shortname") or ticker).strip()
        results.append(
            CompanySearchResult(
                ticker=ticker,
                name=name,
                exchange=str(quote.get("exchDisp") or quote.get("exchange") or "").strip(),
                quote_type=str(quote.get("quoteType") or quote.get("typeDisp") or "").strip(),
            )
        )
        if len(results) >= limit:
            break

    return results
