from django.db import IntegrityError
from django.test import TestCase

from stock_evaluator.companies.models import Company
from stock_evaluator.users.models import TelegramUser, WatchlistItem


class TelegramUserModelTests(TestCase):
    def test_chat_id_must_be_unique(self):
        TelegramUser.objects.create(chat_id=123, username="george")

        with self.assertRaises(IntegrityError):
            TelegramUser.objects.create(chat_id=123, username="duplicate")


class WatchlistItemModelTests(TestCase):
    def test_user_company_pair_must_be_unique(self):
        user = TelegramUser.objects.create(chat_id=123, username="george")
        company = Company.objects.create(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ")
        WatchlistItem.objects.create(user=user, company=company)

        with self.assertRaises(IntegrityError):
            WatchlistItem.objects.create(user=user, company=company)
