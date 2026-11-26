"""Content-addressed storage for artisan photos and voice notes on local disk."""

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

_EXTENSION = re.compile(r"[a-z0-9]{1,5}")


@dataclass(frozen=True)
class StoredMedia:
    sha256: str
    path: Path
    size: int


def store_media(root: Path, data: bytes, ext: str) -> StoredMedia:
    """Write data to root/<sha256>.<ext> atomically. Originals are never altered."""
    if not data:
        raise ValueError("refusing to store an empty file")
    if not _EXTENSION.fullmatch(ext):
        raise ValueError("invalid file extension")

    digest = hashlib.sha256(data).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{digest}.{ext}"

    if not (path.exists() and path.read_bytes() == data):
        fd, temp_name = tempfile.mkstemp(dir=root, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    return StoredMedia(sha256=digest, path=path, size=len(data))
