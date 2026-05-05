"""Outbound dispatcher used by the alerting service to push messages.

Wraps a `telegram.Bot` instance behind a simple async function so the alerting
service doesn't need to know about telegram-specific types.
"""
from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger("seabeacon.bot.dispatcher")


class TelegramDispatcher:
    def __init__(self, bot: Optional[Bot] = None) -> None:
        self._bot = bot

    def attach(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, chat_id: int, text: str) -> bool:
        if self._bot is None:
            logger.warning("dispatcher: bot not attached, skipping chat_id=%s", chat_id)
            return False
        try:
            await self._bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN
            )
            return True
        except TelegramError as exc:
            logger.warning("telegram send failed for %s: %s", chat_id, exc)
            return False


_dispatcher = TelegramDispatcher()


def get_dispatcher() -> TelegramDispatcher:
    return _dispatcher
