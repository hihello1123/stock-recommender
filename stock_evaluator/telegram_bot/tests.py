import asyncio

from django.test import SimpleTestCase, override_settings

from stock_evaluator.telegram_bot.bot import TelegramBotConfigError, build_application
from stock_evaluator.telegram_bot.handlers import help_command, ping, start
from stock_evaluator.telegram_bot.messages import help_message, start_message


class FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeUpdate:
    def __init__(self):
        self.effective_message = FakeMessage()


class TelegramMessageTests(SimpleTestCase):
    def test_start_message_mentions_help(self):
        self.assertIn("/help", start_message())

    def test_help_message_lists_basic_commands(self):
        message = help_message()

        self.assertIn("/start", message)
        self.assertIn("/help", message)
        self.assertIn("/ping", message)


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
