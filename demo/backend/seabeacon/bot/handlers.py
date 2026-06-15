"""Telegram conversation handlers: subscribe / language / country / status / stop."""
from __future__ import annotations

import logging

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from ..db import session_scope
from ..models import Country, Subscription

logger = logging.getLogger("seabeacon.bot")


# Demo countries — others greyed out per spec.
DEMO_COUNTRIES = ["PH", "VN", "TH"]
ALL_COUNTRIES = ["PH", "VN", "TH", "ID", "MY", "MM", "SG", "KH", "LA", "BN"]
LANGUAGES = [("en", "English"), ("fil", "Filipino"), ("vi", "Tiếng Việt"), ("th", "ไทย")]


WELCOME = (
    "*SEABeacon* — cross-border disaster early warning for ASEAN.\n\n"
    "Subscribe with /subscribe to receive localized alerts before, during, and after a "
    "regional hazard. Use /language and /country to change your preferences. "
    "Stop alerts any time with /stop.\n\n"
    "_This is a hackathon demo. The current scenario replays Typhoon Kammuri (December 2019)._"
)


def _country_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for code in ALL_COUNTRIES:
        label = code if code in DEMO_COUNTRIES else f"{code} (soon)"
        cb = f"country:{code}" if code in DEMO_COUNTRIES else "country:disabled"
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"language:{code}")]
        for code, label in LANGUAGES
    ])


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)


async def cmd_subscribe(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Pick the country whose alerts you want to receive:",
        reply_markup=_country_keyboard(),
    )


async def cmd_language(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Pick your preferred alert language:",
        reply_markup=_language_keyboard(),
    )


async def cmd_country(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Pick your country:",
        reply_markup=_country_keyboard(),
    )


async def cmd_status(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    with session_scope() as session:
        sub = session.execute(
            select(Subscription).where(Subscription.telegram_chat_id == chat_id)
        ).scalar_one_or_none()
        if sub is None:
            await update.message.reply_text(
                "No subscription yet. Run /subscribe to begin."
            )
            return
        msg = (
            f"Subscription active: *{sub.active}*\n"
            f"Country: *{sub.country_code}*\n"
            f"Language: *{sub.language}*\n"
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_stop(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    with session_scope() as session:
        sub = session.execute(
            select(Subscription).where(Subscription.telegram_chat_id == chat_id)
        ).scalar_one_or_none()
        if sub:
            sub.active = False
    await update.message.reply_text(
        "Alerts paused. Run /subscribe again to resume.",
    )


async def on_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not query.data:
        return

    chat_id = update.effective_chat.id

    if query.data.startswith("country:"):
        code = query.data.split(":", 1)[1]
        if code == "disabled":
            await query.edit_message_text(
                "That country isn't part of the demo yet. Pick PH, VN, or TH.",
                reply_markup=_country_keyboard(),
            )
            return
        with session_scope() as session:
            country = session.get(Country, code)
            sub = session.execute(
                select(Subscription).where(Subscription.telegram_chat_id == chat_id)
            ).scalar_one_or_none()
            default_lang = country.default_language if country else "en"
            if sub is None:
                sub = Subscription(
                    telegram_chat_id=chat_id,
                    language=default_lang,
                    country_code=code,
                    active=True,
                )
                session.add(sub)
            else:
                sub.country_code = code
                sub.active = True
        await query.edit_message_text(
            f"Country set to *{code}*. Now pick your language:",
            reply_markup=_language_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif query.data.startswith("language:"):
        lang = query.data.split(":", 1)[1]
        with session_scope() as session:
            sub = session.execute(
                select(Subscription).where(Subscription.telegram_chat_id == chat_id)
            ).scalar_one_or_none()
            if sub is None:
                sub = Subscription(
                    telegram_chat_id=chat_id, language=lang, country_code="PH", active=True
                )
                session.add(sub)
            else:
                sub.language = lang
                sub.active = True
            country_code = sub.country_code
        await query.edit_message_text(
            f"You're subscribed to *{country_code}* alerts in *{lang}*. "
            f"You'll get a Telegram message when SEABeacon issues an alert for your area. "
            f"Use /stop to pause.",
            parse_mode=ParseMode.MARKDOWN,
        )


def register(app) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("country", cmd_country))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CallbackQueryHandler(on_callback))
