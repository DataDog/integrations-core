# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from ddev.ai.tools.http.response_store import ResponseStore, ResponseStoreError

from .helpers import saved_files


def save(store: ResponseStore, body: str = "{}") -> object:
    return store.save(body=body, suffix=".json", metadata={"status": 200}, stem="get")


def test_save_writes_body_and_metadata(tmp_path: Path):
    saved = save(ResponseStore(tmp_path, "exec"), '{"a": 1}\n')

    assert saved.path.read_text() == '{"a": 1}\n'
    assert json.loads(saved.metadata_path.read_text()) == {"status": 200, "saved_bytes": 9}
    assert saved.path.parent == tmp_path / "responses" / "exec"


def test_existing_file_is_never_overwritten(tmp_path: Path):
    store = ResponseStore(tmp_path, "exec")
    fixed = uuid.UUID(int=0)
    existing = store.root / f"0001-get-{fixed.hex[:8]}.json"
    existing.parent.mkdir(parents=True)
    existing.write_text("earlier evidence")

    with patch("ddev.ai.tools.http.response_store.uuid.uuid4", return_value=fixed):
        with pytest.raises(ResponseStoreError, match="overwrite"):
            save(store, "new")

    assert existing.read_text() == "earlier evidence"
    assert saved_files(store.root) == [existing]


def test_symlinked_response_directory_is_rejected(tmp_path: Path):
    run_root = tmp_path / "run"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()
    (run_root / "responses").symlink_to(outside)

    with pytest.raises(ResponseStoreError, match="escapes"):
        save(ResponseStore(run_root, "exec"))

    assert list(outside.iterdir()) == []


def test_concurrent_saves_respect_quota(tmp_path: Path):
    body = "x" * 1000
    store = ResponseStore(tmp_path, "exec", quota_bytes=10_000)

    def attempt(_: int) -> bool:
        try:
            save(store, body)
        except ResponseStoreError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(40)))

    written = sum(p.stat().st_size for p in saved_files(store.root))
    assert written <= 10_000
    assert outcomes.count(True) == len(saved_files(store.root)) // 2
    assert False in outcomes


def test_unwritable_directory_raises_store_error_and_releases_quota(tmp_path: Path):
    store = ResponseStore(tmp_path, "exec", quota_bytes=2_000)
    save(store)

    with patch("ddev.ai.tools.http.response_store.tempfile.mkstemp", side_effect=PermissionError("denied")):
        with pytest.raises(ResponseStoreError, match="denied"):
            save(store, "x" * 1500)

    save(store, "x" * 1500)


def test_interrupted_write_leaves_no_partial_files_and_releases_quota(tmp_path: Path):
    store = ResponseStore(tmp_path, "exec", quota_bytes=2_000)
    earlier = save(store, "earlier")

    with patch("ddev.ai.tools.http.response_store.os.link", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            save(store, "x" * 1500)

    assert saved_files(store.root) == sorted([earlier.path, earlier.metadata_path])
    save(store, "x" * 1500)
