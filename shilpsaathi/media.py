"""Content-addressed storage for artisan photos and voice notes on local disk."""

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

_EXTENSION = re.compile(r"[a-z0-9]{1,5}")
_HEIF_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"mif1"}


@dataclass(frozen=True)
class StoredMedia:
    sha256: str
    path: Path
    size: int


def image_extension(data: bytes) -> str | None:
    """Identify a supported raster image from its leading bytes, or return None.

    A sender controls a file's name and declared type, so neither is trusted.
    This checks the signature only; it does not decode the image.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS:
        return "heic"
    return None


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
