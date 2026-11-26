import hashlib

import pytest

from shilpsaathi.media import store_media


def test_returns_sha256_of_the_bytes_and_writes_them_unchanged(tmp_path):
    data = b"\xff\xd8photo-bytes"

    stored = store_media(tmp_path, data, "jpg")

    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert stored.path == tmp_path / f"{stored.sha256}.jpg"
    assert stored.path.read_bytes() == data
    assert stored.size == len(data)


def test_creates_the_media_directory_if_missing(tmp_path):
    stored = store_media(tmp_path / "var" / "media", b"voice", "ogg")

    assert stored.path.read_bytes() == b"voice"


def test_same_bytes_are_stored_once(tmp_path):
    first = store_media(tmp_path, b"same", "ogg")
    second = store_media(tmp_path, b"same", "ogg")

    assert first == second
    assert list(tmp_path.iterdir()) == [first.path]


def test_repairs_a_file_whose_content_no_longer_matches_its_hash(tmp_path):
    first = store_media(tmp_path, b"original", "ogg")
    first.path.write_bytes(b"corrupted")

    store_media(tmp_path, b"original", "ogg")

    assert first.path.read_bytes() == b"original"


def test_failed_write_leaves_no_partial_file(tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", fail)

    with pytest.raises(OSError):
        store_media(tmp_path, b"data", "jpg")
    assert list(tmp_path.iterdir()) == []


def test_refuses_empty_data(tmp_path):
    with pytest.raises(ValueError):
        store_media(tmp_path, b"", "jpg")


@pytest.mark.parametrize("ext", ["../evil", "a/b", "", "jpg.exe"])
def test_refuses_an_extension_that_could_escape_the_directory(tmp_path, ext):
    with pytest.raises(ValueError):
        store_media(tmp_path, b"data", ext)
