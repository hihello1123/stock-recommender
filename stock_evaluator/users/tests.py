from django.db import IntegrityError
from django.test import TestCase

from stock_evaluator.users.models import TelegramUser


class TelegramUserModelTests(TestCase):
    def test_chat_id_must_be_unique(self):
        TelegramUser.objects.create(chat_id=123, username="george")

        with self.assertRaises(IntegrityError):
            TelegramUser.objects.create(chat_id=123, username="duplicate")
