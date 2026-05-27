from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any

import yfinance as yf

from stock_evaluator.companies.services.market_data_client import MarketDataError


@dataclass(frozen=True)
class CompanySearchResult:
    ticker: str
    name: str
    exchange: str = ""
    quote_type: str = ""
    similarity: float = 0


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


def rank_ticker_matches(query: str, results: list[CompanySearchResult]) -> list[CompanySearchResult]:
    normalized_query = _canonical_ticker(query)
    if not normalized_query:
        return results

    ranked_results = []
    for result in results:
        similarity = SequenceMatcher(None, normalized_query, _canonical_ticker(result.ticker)).ratio()
        ranked_results.append(
            CompanySearchResult(
                ticker=result.ticker,
                name=result.name,
                exchange=result.exchange,
                quote_type=result.quote_type,
                similarity=similarity,
            )
        )

    return sorted(ranked_results, key=lambda result: result.similarity, reverse=True)


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


def _canonical_ticker(ticker: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", ticker.upper())
