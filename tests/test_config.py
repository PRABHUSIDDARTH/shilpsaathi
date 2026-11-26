from pathlib import Path

import pytest

from shilpsaathi.config import ConfigError, load_config

TOKEN = "123456:FAKE-token-for-tests"


def test_loads_token_allowlist_and_media_dir():
    config = load_config(
        {
            "TELEGRAM_BOT_TOKEN": TOKEN,
            "ARTISAN_TELEGRAM_IDS": "111, 222,",
            "MEDIA_DIR": "somewhere/media",
        }
    )

    assert config.telegram_bot_token == TOKEN
    assert config.artisan_ids == frozenset({111, 222})
    assert config.media_dir == Path("somewhere/media")


def test_allowlist_is_empty_and_media_dir_defaults_when_unset():
    config = load_config({"TELEGRAM_BOT_TOKEN": TOKEN})

    assert config.artisan_ids == frozenset()
    assert config.media_dir == Path("var/media")


@pytest.mark.parametrize("env", [{}, {"TELEGRAM_BOT_TOKEN": "  "}])
def test_missing_token_names_the_variable(env):
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        load_config(env)


def test_bad_allowlist_error_does_not_echo_the_value():
    # A secret pasted into the wrong variable must not reach the terminal.
    with pytest.raises(ConfigError) as caught:
        load_config({"TELEGRAM_BOT_TOKEN": TOKEN, "ARTISAN_TELEGRAM_IDS": TOKEN})

    assert "ARTISAN_TELEGRAM_IDS" in str(caught.value)
    assert TOKEN not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_config_repr_hides_the_token():
    assert TOKEN not in repr(load_config({"TELEGRAM_BOT_TOKEN": TOKEN}))
