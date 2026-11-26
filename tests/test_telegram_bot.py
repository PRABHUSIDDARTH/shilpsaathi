"""Runs real python-telegram-bot updates through the app. Only the HTTP layer is faked."""

import asyncio
import hashlib
import io
import json
import logging

import pytest
from telegram import Update
from telegram.request import BaseRequest

from shilpsaathi.channel.telegram_bot import build_application, configure_logging, run
from shilpsaathi.config import Config

TOKEN = "123456:FAKE-token-for-tests"
ARTISAN = 111
STRANGER = 999


class FakeTelegram(BaseRequest):
    def __init__(self, files=None, fail_downloads=False, reject_token=False):
        self.files = files or {}
        self.fail_downloads = fail_downloads
        self.reject_token = reject_token
        self.sent = []
        self.calls = []

    @property
    def read_timeout(self):
        return 1.0

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **timeouts):
        if "/file/bot" in url:
            self.calls.append("download")
            if self.fail_downloads:
                return 500, b'{"ok": false, "description": "boom"}'
            return 200, self.files[url.rsplit("/", 1)[1]]

        api_method = url.rsplit("/", 1)[1]
        self.calls.append(api_method)
        params = request_data.parameters if request_data else {}
        if self.reject_token:
            return 401, b'{"ok": false, "description": "Unauthorized"}'
        if api_method == "getMe":
            result = {"id": 1, "is_bot": True, "first_name": "Bot", "username": "bot"}
        elif api_method == "getFile":
            file_id = params["file_id"]
            result = {"file_id": file_id, "file_unique_id": file_id, "file_path": file_id}
        elif api_method == "sendMessage":
            self.sent.append(params["text"])
            result = {"message_id": 2, "date": 0, "chat": {"id": 1, "type": "private"}}
        else:
            raise AssertionError(f"unexpected API call {api_method}")
        return 200, json.dumps({"ok": True, "result": result}).encode()


def deliver(tmp_path, fake, message, user=ARTISAN, chat_type="private"):
    config = Config(TOKEN, frozenset({ARTISAN}), tmp_path / "media")

    async def go():
        app = build_application(config, request=fake)
        async with app:
            payload = {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "date": 0,
                    "chat": {"id": user, "type": chat_type},
                    "from": {"id": user, "is_bot": False, "first_name": "T"},
                    **message,
                },
            }
            await app.process_update(Update.de_json(payload, app.bot))

    asyncio.run(go())
    return config.media_dir


def photo(file_id, width):
    return {"file_id": file_id, "file_unique_id": file_id, "width": width, "height": width}


VOICE = {"voice": {"file_id": "voice1", "file_unique_id": "voice1", "duration": 3}}


def test_photo_stores_the_largest_size_and_confirms_its_hash(tmp_path):
    fake = FakeTelegram(files={"small": b"small-jpeg", "large": b"large-jpeg"})

    media = deliver(tmp_path, fake, {"photo": [photo("small", 90), photo("large", 1280)]})

    digest = hashlib.sha256(b"large-jpeg").hexdigest()
    assert (media / f"{digest}.jpg").read_bytes() == b"large-jpeg"
    assert len(list(media.iterdir())) == 1
    assert len(fake.sent) == 1 and digest in fake.sent[0] and "Photo" in fake.sent[0]


def test_voice_note_is_stored_as_ogg_and_confirms_its_hash(tmp_path):
    fake = FakeTelegram(files={"voice1": b"OggS-voice"})

    media = deliver(tmp_path, fake, VOICE)

    digest = hashlib.sha256(b"OggS-voice").hexdigest()
    assert (media / f"{digest}.ogg").read_bytes() == b"OggS-voice"
    assert len(fake.sent) == 1 and digest in fake.sent[0] and "Voice note" in fake.sent[0]


@pytest.mark.parametrize("message", [VOICE, {"photo": [photo("p", 90)]}, {"text": "hi"}])
def test_stranger_is_told_their_id_and_nothing_is_downloaded(tmp_path, message):
    fake = FakeTelegram()

    media = deliver(tmp_path, fake, message, user=STRANGER)

    assert not media.exists()
    assert "download" not in fake.calls and "getFile" not in fake.calls
    assert len(fake.sent) == 1 and str(STRANGER) in fake.sent[0]


def test_group_chats_are_ignored(tmp_path):
    fake = FakeTelegram()

    media = deliver(tmp_path, fake, VOICE, chat_type="group")

    assert not media.exists() and fake.sent == []


def test_text_from_the_artisan_is_echoed(tmp_path):
    fake = FakeTelegram()

    deliver(tmp_path, fake, {"text": "vanakkam"})

    assert fake.sent == ["You said: vanakkam"]


def test_start_explains_what_to_send(tmp_path):
    fake = FakeTelegram()
    start = {"text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}

    deliver(tmp_path, fake, start)

    assert len(fake.sent) == 1 and "voice note" in fake.sent[0]


def test_unsupported_message_gets_guidance(tmp_path):
    fake = FakeTelegram()
    document = {"document": {"file_id": "d", "file_unique_id": "d"}}

    deliver(tmp_path, fake, document)

    assert len(fake.sent) == 1 and "voice note" in fake.sent[0]
    assert "getFile" not in fake.calls


def test_failed_download_asks_the_artisan_to_resend(tmp_path):
    fake = FakeTelegram(fail_downloads=True)

    media = deliver(tmp_path, fake, VOICE)

    assert not media.exists()
    assert len(fake.sent) == 1 and "could not confirm" in fake.sent[0]
    assert "not stored" not in fake.sent[0]


@pytest.fixture
def log_output():
    root = logging.getLogger()
    saved = root.handlers[:], root.level, logging.getLogger("httpx").level
    stream = io.StringIO()
    configure_logging(TOKEN, stream=stream)
    yield stream
    root.handlers[:], root.level = saved[0], saved[1]
    logging.getLogger("httpx").setLevel(saved[2])


def test_logs_never_contain_the_token_even_in_tracebacks(log_output):
    try:
        raise RuntimeError(f"request to https://api.telegram.org/bot{TOKEN}/getMe failed")
    except RuntimeError:
        logging.getLogger("telegram").exception("error for %s", TOKEN)

    assert "error for" in log_output.getvalue()
    assert TOKEN not in log_output.getvalue()


def test_httpx_request_urls_are_not_logged(log_output):
    logging.getLogger("httpx").info("HTTP Request: POST https://api.telegram.org/")

    assert log_output.getvalue() == ""


def test_rejected_token_exits_without_printing_it(tmp_path):
    config = Config(TOKEN, frozenset(), tmp_path)
    app = build_application(config, request=FakeTelegram(reject_token=True))
    asyncio.set_event_loop(asyncio.new_event_loop())

    with pytest.raises(SystemExit) as caught:
        run(app)

    assert "TELEGRAM_BOT_TOKEN" in str(caught.value)
    assert TOKEN not in str(caught.value)
    assert caught.value.__suppress_context__
