import re


def normalize_alias(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


SEED_COMPANY_ALIASES = [
    {
        "alias": "구글",
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "alternative_tickers": ["GOOG"],
    },
    {
        "alias": "알파벳",
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "alternative_tickers": ["GOOG"],
    },
    {"alias": "애플", "ticker": "AAPL", "company_name": "Apple Inc."},
    {"alias": "마이크로소프트", "ticker": "MSFT", "company_name": "Microsoft Corporation"},
    {"alias": "마소", "ticker": "MSFT", "company_name": "Microsoft Corporation"},
    {"alias": "테슬라", "ticker": "TSLA", "company_name": "Tesla, Inc."},
    {"alias": "엔비디아", "ticker": "NVDA", "company_name": "NVIDIA Corporation"},
    {"alias": "메타", "ticker": "META", "company_name": "Meta Platforms, Inc."},
    {"alias": "페이스북", "ticker": "META", "company_name": "Meta Platforms, Inc."},
    {"alias": "코카콜라", "ticker": "KO", "company_name": "The Coca-Cola Company"},
    {"alias": "포드", "ticker": "F", "company_name": "Ford Motor Company"},
    {"alias": "인텔", "ticker": "INTC", "company_name": "Intel Corporation"},
    {"alias": "리얼티인컴", "ticker": "O", "company_name": "Realty Income Corporation"},
    {"alias": "유니티", "ticker": "U", "company_name": "Unity Software Inc."},
    {"alias": "줌", "ticker": "ZM", "company_name": "Zoom Communications, Inc."},
    {"alias": "팔란티어", "ticker": "PLTR", "company_name": "Palantir Technologies Inc."},
    {"alias": "아마존", "ticker": "AMZN", "company_name": "Amazon.com, Inc."},
    {"alias": "넷플릭스", "ticker": "NFLX", "company_name": "Netflix, Inc."},
    {"alias": "브로드컴", "ticker": "AVGO", "company_name": "Broadcom Inc."},
    {"alias": "오라클", "ticker": "ORCL", "company_name": "Oracle Corporation"},
]
