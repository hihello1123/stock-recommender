from stock_evaluator.companies.models import Company


LOW_CONFIDENCE_TYPES = {
    Company.InstrumentType.REIT,
    Company.InstrumentType.ETF,
    Company.InstrumentType.FUND,
    Company.InstrumentType.SPAC,
    Company.InstrumentType.FINANCIAL,
    Company.InstrumentType.UNKNOWN,
}


FINANCIAL_SECTORS = {"financial services", "financial", "banks", "insurance"}


def classify_instrument_type(sector: str = "", industry: str = "", quote_type: str = "") -> str:
    normalized_quote_type = quote_type.strip().lower()
    normalized_sector = sector.strip().lower()
    normalized_industry = industry.strip().lower()

    if normalized_quote_type in {"etf"}:
        return Company.InstrumentType.ETF
    if normalized_quote_type in {"mutualfund", "fund"}:
        return Company.InstrumentType.FUND
    if "reit" in normalized_industry:
        return Company.InstrumentType.REIT
    if "spac" in normalized_industry:
        return Company.InstrumentType.SPAC
    if normalized_sector in FINANCIAL_SECTORS:
        return Company.InstrumentType.FINANCIAL
    if normalized_quote_type in {"equity", "stock"}:
        return Company.InstrumentType.COMMON_STOCK
    return Company.InstrumentType.UNKNOWN


def is_low_confidence_type(instrument_type: str) -> bool:
    return instrument_type in LOW_CONFIDENCE_TYPES
