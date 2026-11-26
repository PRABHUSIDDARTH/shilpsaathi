"""Telegram adapter. M0: echo text, store photos and voice notes, confirm their hashes.

Run with: uv run python -m shilpsaathi.channel.telegram_bot
"""

import logging
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.error import InvalidToken
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import BaseRequest

from shilpsaathi.config import Config, ConfigError, load_config
from shilpsaathi.media import store_media

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEND_GUIDE = "Send a photo or a voice note."

log = logging.getLogger(__name__)


class _RedactingFormatter(logging.Formatter):
    """Removes the bot token from the final log line, tracebacks included."""

    def __init__(self, secret: str):
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._secret = secret

    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).replace(self._secret, "<redacted>")


def configure_logging(token: str, stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(_RedactingFormatter(token))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # httpx logs every request URL at INFO, and Bot API URLs contain the token.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def build_application(config: Config, request: BaseRequest | None = None) -> Application:
    builder = Application.builder().token(config.telegram_bot_token)
    if request is not None:
        builder = builder.request(request).get_updates_request(request)
    app = builder.build()

    # New messages in private chats only: replies must never expose an artisan to a group.
    base = filters.UpdateType.MESSAGE & filters.ChatType.PRIVATE
    allowed = base & filters.User(user_id=config.artisan_ids, allow_empty=False)

    async def refuse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            f"This bot is private and nothing was stored. Your Telegram user ID is "
            f"{update.effective_user.id}. The operator can add it to ARTISAN_TELEGRAM_IDS."
        )

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(f"Vanakkam! {SEND_GUIDE}")

    async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Telegram caps a message at 4096 characters.
        await update.message.reply_text(f"You said: {update.message.text}"[:4096])

    async def save(message: Message, file_id: str, ext: str, label: str) -> None:
        telegram_file = await message.get_bot().get_file(file_id)
        data = bytes(await telegram_file.download_as_bytearray())
        stored = store_media(config.media_dir, data, ext)
        await message.reply_text(
            f"{label} stored ({stored.size} bytes).\nsha256: {stored.sha256}"
        )

    async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        largest = update.message.photo[-1]  # Telegram lists sizes smallest first
        await save(update.message, largest.file_id, "jpg", "Photo")

    async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await save(update.message, update.message.voice.file_id, "ogg", "Voice note")

    async def unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(f"I can't use that yet. {SEND_GUIDE}")

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("failed to handle an update", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Something went wrong and I could not confirm that. Please send it again."
            )

    # Order matters: within a group only the first matching handler runs.
    app.add_handler(CommandHandler("start", start, filters=allowed))
    app.add_handler(MessageHandler(allowed & filters.PHOTO, photo))
    app.add_handler(MessageHandler(allowed & filters.VOICE, voice))
    app.add_handler(MessageHandler(allowed & filters.TEXT & ~filters.COMMAND, echo))
    app.add_handler(MessageHandler(allowed, unsupported))
    app.add_handler(MessageHandler(base, refuse))
    app.add_error_handler(on_error)
    return app


def run(app: Application) -> None:
    try:
        app.run_polling(allowed_updates=[Update.MESSAGE])
    except InvalidToken:
        # The library's own message includes the token, so it is dropped here.
        raise SystemExit("Telegram rejected TELEGRAM_BOT_TOKEN. Check it in .env.") from None
    except Exception:
        # Left uncaught, Python would print the traceback without redaction.
        log.exception("the bot stopped unexpectedly")
        raise SystemExit(1) from None


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        config = load_config(os.environ)
    except ConfigError as error:
        raise SystemExit(str(error)) from None
    config = replace(config, media_dir=PROJECT_ROOT / config.media_dir)
    configure_logging(config.telegram_bot_token)
    if not config.artisan_ids:
        log.warning("ARTISAN_TELEGRAM_IDS is empty: nothing will be stored")
    run(build_application(config))


if __name__ == "__main__":
    main()
