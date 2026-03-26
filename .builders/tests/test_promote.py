from pathlib import Path
from unittest import mock

import pytest
import promote


def write_lockfile(path: Path, entries: list[str]) -> None:
    path.write_text("\n".join(entries))


def test_parse_lockfile_urls_templated(tmp_path):
    """parse_lockfile_urls extracts URLs from ${PACKAGE_BASE_URL} lockfile entries."""
    lockfile = tmp_path / "linux-x86_64_3.13.txt"
    write_lockfile(lockfile, [
        "aerospike @ ${PACKAGE_BASE_URL}/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl#sha256=abc",
        "requests @ ${PACKAGE_BASE_URL}/external/requests/requests-2.32.0-py3-none-any.whl#sha256=def",
        "",
    ])

    urls = promote.parse_lockfile_urls(lockfile)

    assert urls == [
        "${PACKAGE_BASE_URL}/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl",
        "${PACKAGE_BASE_URL}/external/requests/requests-2.32.0-py3-none-any.whl",
    ]


def test_url_to_blob_path_templated():
    """url_to_blob_path extracts the relative path from a ${PACKAGE_BASE_URL} URL."""
    url = "${PACKAGE_BASE_URL}/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl"
    assert promote.url_to_blob_path(url) == "built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl"


def test_url_to_blob_path_returns_none_for_other_urls():
    """url_to_blob_path returns None for non-templated URLs."""
    assert promote.url_to_blob_path("https://example.com/some.whl") is None
    assert promote.url_to_blob_path("https://agent-int-packages.datadoghq.com/built/foo/foo-1.0.whl") is None


def test_collect_relative_paths(tmp_path):
    """collect_relative_paths reads all lockfiles and returns relative paths."""
    lock_dir = tmp_path / ".deps" / "resolved"
    lock_dir.mkdir(parents=True)

    write_lockfile(lock_dir / "linux-x86_64_3.13.txt", [
        "aerospike @ ${PACKAGE_BASE_URL}/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl#sha256=abc",
    ])
    write_lockfile(lock_dir / "linux-aarch64_3.13.txt", [
        "aerospike @ ${PACKAGE_BASE_URL}/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_aarch64.whl#sha256=xyz",
    ])

    with mock.patch.object(promote, "LOCK_FILE_DIR", lock_dir):
        paths = promote.collect_relative_paths()

    assert sorted(paths) == [
        "built/aerospike/aerospike-7.1.1-cp313-cp313-linux_aarch64.whl",
        "built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl",
    ]


def test_collect_relative_paths_deduplicates(tmp_path):
    """collect_relative_paths deduplicates paths that appear in multiple lockfiles."""
    lock_dir = tmp_path / ".deps" / "resolved"
    lock_dir.mkdir(parents=True)

    shared_entry = "requests @ ${PACKAGE_BASE_URL}/external/requests/requests-2.32.0-py3-none-any.whl#sha256=def"
    write_lockfile(lock_dir / "linux-x86_64_3.13.txt", [shared_entry])
    write_lockfile(lock_dir / "linux-aarch64_3.13.txt", [shared_entry])

    with mock.patch.object(promote, "LOCK_FILE_DIR", lock_dir):
        paths = promote.collect_relative_paths()

    assert paths.count("external/requests/requests-2.32.0-py3-none-any.whl") == 2


def test_promote_copies_blobs():
    """promote copies each relative path from dev/ to stable/ in GCS."""
    rel_paths = [
        "built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl",
        "external/requests/requests-2.32.0-py3-none-any.whl",
    ]

    mock_client = mock.Mock()
    mock_bucket = mock.Mock()
    mock_client.bucket.return_value = mock_bucket

    source_blob = mock.Mock()
    source_blob.exists.return_value = True
    mock_bucket.blob.return_value = source_blob

    with mock.patch("promote.storage.Client", return_value=mock_client):
        promote.promote(rel_paths)

    assert mock_bucket.blob.call_count == 2
    mock_bucket.blob.assert_any_call("dev/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl")
    mock_bucket.blob.assert_any_call("dev/external/requests/requests-2.32.0-py3-none-any.whl")

    assert mock_bucket.copy_blob.call_count == 2
    mock_bucket.copy_blob.assert_any_call(
        source_blob, mock_bucket, "stable/built/aerospike/aerospike-7.1.1-cp313-cp313-linux_x86_64.whl"
    )
    mock_bucket.copy_blob.assert_any_call(
        source_blob, mock_bucket, "stable/external/requests/requests-2.32.0-py3-none-any.whl"
    )


def test_promote_is_idempotent():
    """promote succeeds even if the destination blob already exists (GCS copy is idempotent)."""
    rel_paths = ["built/foo/foo-1.0-cp313-cp313-linux_x86_64.whl"]

    mock_client = mock.Mock()
    mock_bucket = mock.Mock()
    mock_client.bucket.return_value = mock_bucket

    source_blob = mock.Mock()
    source_blob.exists.return_value = True
    mock_bucket.blob.return_value = source_blob

    with mock.patch("promote.storage.Client", return_value=mock_client):
        promote.promote(rel_paths)
        promote.promote(rel_paths)

    assert mock_bucket.copy_blob.call_count == 2


def test_promote_fails_if_source_missing(capsys):
    """promote exits with error if a source blob is not found in dev/."""
    rel_paths = ["built/missing/missing-1.0-cp313-cp313-linux_x86_64.whl"]

    mock_client = mock.Mock()
    mock_bucket = mock.Mock()
    mock_client.bucket.return_value = mock_bucket

    source_blob = mock.Mock()
    source_blob.exists.return_value = False
    mock_bucket.blob.return_value = source_blob

    with mock.patch("promote.storage.Client", return_value=mock_client):
        with pytest.raises(SystemExit) as exc_info:
            promote.promote(rel_paths)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "MISSING" in captured.out or "not found" in captured.err


def test_promote_nothing_to_promote():
    """promote prints a message and returns early when given no paths."""
    with mock.patch("promote.storage.Client") as mock_client_cls:
        promote.promote([])

    mock_client_cls.assert_not_called()
