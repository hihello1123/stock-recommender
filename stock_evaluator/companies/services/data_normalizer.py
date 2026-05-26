from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import math
from typing import Any

from stock_evaluator.companies.models import FinancialSnapshot
from stock_evaluator.companies.services.market_data_client import MarketDataPayload


SNAPSHOT_FIELDS = [
    "price",
    "market_cap",
    "per",
    "pbr",
    "psr",
    "roe",
    "roic",
    "revenue",
    "operating_income",
    "net_income",
    "eps",
    "operating_cash_flow",
    "free_cash_flow",
    "total_debt",
    "cash",
]


def normalize_market_data(
    payload: MarketDataPayload,
    *,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    info = payload.info
    fast_info = payload.fast_info
    snapshot_date = as_of_date or date.today()

    values = {
        "source": "yfinance",
        "source_url": f"https://finance.yahoo.com/quote/{payload.ticker}",
        "as_of_date": snapshot_date,
        "period_end_date": None,
        "period_type": FinancialSnapshot.PeriodType.UNKNOWN,
        "currency": _first_text([info, fast_info], ["currency", "financialCurrency"]),
        "price": _decimal(_first_value([fast_info, info], ["last_price", "currentPrice"])),
        "market_cap": _decimal(_first_value([fast_info, info], ["market_cap", "marketCap"])),
        "per": _decimal(info.get("trailingPE")),
        "pbr": _decimal(info.get("priceToBook")),
        "psr": _decimal(info.get("priceToSalesTrailing12Months")),
        "roe": _decimal(info.get("returnOnEquity")),
        "roic": _decimal(info.get("returnOnCapital")),
        "revenue": _decimal(info.get("totalRevenue")),
        "operating_income": _decimal(info.get("operatingIncome")),
        "net_income": _decimal(info.get("netIncomeToCommon")),
        "eps": _decimal(info.get("trailingEps")),
        "operating_cash_flow": _decimal(info.get("operatingCashflow")),
        "free_cash_flow": _decimal(info.get("freeCashflow")),
        "total_debt": _decimal(info.get("totalDebt")),
        "cash": _decimal(info.get("totalCash")),
        "raw_payload": {
            "ticker": payload.ticker,
            "info": _json_safe_value(info),
            "fast_info": _json_safe_value(fast_info),
        },
    }
    values["missing_fields"] = [
        field for field in SNAPSHOT_FIELDS if values.get(field) is None
    ]
    return values


def _first_text(sources: list[dict[str, Any]], keys: list[str]) -> str:
    value = _first_value(sources, keys)
    return str(value) if value is not None else ""


def _first_value(sources: list[dict[str, Any]], keys: list[str]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
    return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return str(value) if value.is_finite() else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
