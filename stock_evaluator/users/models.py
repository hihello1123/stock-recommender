from django.db import models


class TelegramUser(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True)
    is_allowed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["chat_id"]),
            models.Index(fields=["is_allowed"]),
        ]

    def __str__(self) -> str:
        return str(self.chat_id)
