"""python-telegram-bot v21+ Application bootstrap.

Two entry points:

  1. `python -m seabeacon.bot.telegram_bot` — runs the bot in standalone polling
      mode for local testing of the subscription flow.

  2. `lifespan_start(app_settings)` — used by FastAPI's lifespan manager so
     the bot runs in the same process as the API. The `Application` is started
     with `initialize() / start()` (NOT `run_polling()` which owns the loop)
     so it cooperates with the FastAPI loop.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram.ext import Application, ApplicationBuilder

from ..config import get_settings
from . import handlers
from .dispatcher import get_dispatcher

logger = logging.getLogger("seabeacon.bot")


_app: Optional[Application] = None


def _build(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()
    handlers.register(app)
    return app


async def lifespan_start() -> Optional[Application]:
    """Start the Telegram bot inside an existing asyncio loop. Returns the app
    instance (or None if no token configured)."""
    global _app
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled.")
        return None

    _app = _build(token)
    await _app.initialize()
    await _app.start()
    if _app.updater is not None:
        await _app.updater.start_polling(drop_pending_updates=True)

    get_dispatcher().attach(_app.bot)
    logger.info("telegram bot started")
    return _app


async def lifespan_stop() -> None:
    global _app
    if _app is None:
        return
    if _app.updater is not None and _app.updater.running:
        await _app.updater.stop()
    if _app.running:
        await _app.stop()
    await _app.shutdown()
    _app = None
    logger.info("telegram bot stopped")


def main_polling() -> None:
    """Standalone polling mode for local bot testing."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    from ..db import init_db
    init_db()
    app = _build(token)
    app.run_polling()


if __name__ == "__main__":
    main_polling()
