"""Settings read from the environment. Error messages never include a variable's value."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str = field(repr=False)
    artisan_ids: frozenset[int]
    media_dir: Path


def load_config(env: Mapping[str, str]) -> Config:
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN is not set. See .env.example.")

    raw_ids = env.get("ARTISAN_TELEGRAM_IDS", "")
    try:
        artisan_ids = frozenset(int(part) for part in raw_ids.split(",") if part.strip())
    except ValueError:
        raise ConfigError(
            "ARTISAN_TELEGRAM_IDS must be comma-separated numbers. See .env.example."
        ) from None

    media_dir = Path(env.get("MEDIA_DIR", "").strip() or "var/media")
    return Config(token, artisan_ids, media_dir)
