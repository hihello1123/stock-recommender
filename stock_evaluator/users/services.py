from django.conf import settings

from stock_evaluator.companies.services.company_lookup import (
    CompanyLookupService,
    save_company_report_data,
)
from stock_evaluator.companies.services.market_data_client import normalize_ticker
from stock_evaluator.users.models import TelegramUser, WatchlistItem


class WatchlistLimitError(RuntimeError):
    pass


def get_or_create_telegram_user(
    chat_id: int,
    username: str = "",
    *,
    is_allowed: bool = True,
) -> TelegramUser:
    user, _ = TelegramUser.objects.update_or_create(
        chat_id=chat_id,
        defaults={"username": username, "is_allowed": is_allowed},
    )
    return user


def watch_ticker(chat_id: int, ticker: str, username: str = "") -> tuple[WatchlistItem, bool]:
    normalized_ticker = normalize_ticker(ticker)
    user = get_or_create_telegram_user(chat_id, username)
    existing = WatchlistItem.objects.filter(user=user, company__ticker=normalized_ticker).first()
    if existing:
        return existing, False
    if (
        user.chat_id not in settings.WATCHLIST_LIMIT_EXEMPT_CHAT_IDS
        and WatchlistItem.objects.filter(user=user).count() >= settings.WATCHLIST_MAX_ITEMS
    ):
        raise WatchlistLimitError(f"Watchlist limit reached: {settings.WATCHLIST_MAX_ITEMS}")
    result = CompanyLookupService().lookup(normalized_ticker)
    company, _snapshot = save_company_report_data(result)
    return WatchlistItem.objects.get_or_create(user=user, company=company)


def unwatch_ticker(chat_id: int, ticker: str) -> bool:
    normalized_ticker = normalize_ticker(ticker)
    deleted_count, _ = WatchlistItem.objects.filter(
        user__chat_id=chat_id,
        company__ticker=normalized_ticker,
    ).delete()
    return deleted_count > 0


def effective_watchlist_items_for_user(user: TelegramUser) -> list[WatchlistItem]:
    queryset = (
        WatchlistItem.objects.filter(user=user)
        .select_related("company")
        .order_by("created_at", "id")
    )
    if user.chat_id in settings.WATCHLIST_LIMIT_EXEMPT_CHAT_IDS:
        return list(queryset)
    return list(queryset[: settings.WATCHLIST_MAX_ITEMS])


def list_watchlist(chat_id: int) -> list[WatchlistItem]:
    user = TelegramUser.objects.filter(chat_id=chat_id).first()
    if user is None:
        return []
    return sorted(effective_watchlist_items_for_user(user), key=lambda item: item.company.ticker)
