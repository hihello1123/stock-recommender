import asyncio

from django.test import SimpleTestCase, override_settings
from telegram.constants import ChatType

from stock_evaluator.telegram_bot.auth import ACCESS_DENIED_MESSAGE, is_allowed_chat
from stock_evaluator.telegram_bot.bot import TelegramBotConfigError, build_application
from stock_evaluator.telegram_bot.handlers import help_command, ping, start
from stock_evaluator.telegram_bot.messages import help_message, start_message


class FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeChat:
    def __init__(self, chat_id: int, chat_type: str = ChatType.PRIVATE):
        self.id = chat_id
        self.type = chat_type


class FakeUpdate:
    def __init__(self, chat_id: int = 123456789, chat_type: str = ChatType.PRIVATE):
        self.effective_message = FakeMessage()
        self.effective_chat = FakeChat(chat_id, chat_type)


class TelegramMessageTests(SimpleTestCase):
    def test_start_message_mentions_help(self):
        self.assertIn("/help", start_message())

    def test_help_message_lists_basic_commands(self):
        message = help_message()

        self.assertIn("/start", message)
        self.assertIn("/help", message)
        self.assertIn("/ping", message)


@override_settings(ALLOWED_TELEGRAM_CHAT_IDS=[123456789])
class TelegramAuthTests(SimpleTestCase):
    def test_allowed_private_chat_passes(self):
        self.assertTrue(is_allowed_chat(FakeUpdate()))

    def test_denied_chat_id_fails(self):
        self.assertFalse(is_allowed_chat(FakeUpdate(chat_id=999)))

    def test_group_chat_fails(self):
        self.assertFalse(is_allowed_chat(FakeUpdate(chat_type=ChatType.GROUP)))


@override_settings(ALLOWED_TELEGRAM_CHAT_IDS=[123456789])
class TelegramHandlerTests(SimpleTestCase):
    def test_ping_replies_pong(self):
        update = FakeUpdate()

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, ["pong"])

    def test_start_replies_with_start_message(self):
        update = FakeUpdate()

        asyncio.run(start(update, None))

        self.assertEqual(update.effective_message.replies, [start_message()])

    def test_help_replies_with_help_message(self):
        update = FakeUpdate()

        asyncio.run(help_command(update, None))

        self.assertEqual(update.effective_message.replies, [help_message()])

    def test_denied_chat_gets_access_denied(self):
        update = FakeUpdate(chat_id=999)

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, [ACCESS_DENIED_MESSAGE])

    def test_group_chat_gets_access_denied(self):
        update = FakeUpdate(chat_type=ChatType.GROUP)

        asyncio.run(ping(update, None))

        self.assertEqual(update.effective_message.replies, [ACCESS_DENIED_MESSAGE])


class TelegramApplicationTests(SimpleTestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_build_application_requires_token(self):
        with self.assertRaises(TelegramBotConfigError):
            build_application()

    def test_build_application_registers_basic_commands(self):
        application = build_application("123456:ABCDEF")
        command_names = {
            command
            for group in application.handlers.values()
            for handler in group
            for command in getattr(handler, "commands", set())
        }

        self.assertSetEqual(command_names, {"start", "help", "ping"})
