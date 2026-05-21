from dataclasses import dataclass
from typing import Any

import yfinance as yf


class MarketDataError(RuntimeError):
    pass


class TickerNotFoundError(MarketDataError):
    pass


@dataclass(frozen=True)
class MarketDataPayload:
    ticker: str
    info: dict[str, Any]
    fast_info: dict[str, Any]


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("Ticker is required.")
    return normalized


class YFinanceMarketDataClient:
    source = "yfinance"

    def fetch(self, ticker: str) -> MarketDataPayload:
        normalized_ticker = normalize_ticker(ticker)

        try:
            yf_ticker = yf.Ticker(normalized_ticker)
            info = dict(yf_ticker.info or {})
            fast_info = dict(yf_ticker.fast_info or {})
        except Exception as exc:
            raise MarketDataError("Failed to fetch market data.") from exc

        if not info and not fast_info:
            raise TickerNotFoundError(f"Ticker not found: {normalized_ticker}")

        return MarketDataPayload(
            ticker=normalized_ticker,
            info=info,
            fast_info=fast_info,
        )
