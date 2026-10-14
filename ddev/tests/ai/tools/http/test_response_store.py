# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from ddev.ai.tools.http.response_store import ResponseStore, ResponseStoreError, SavedResponse

from .helpers import saved_files


def save(store: ResponseStore, body: str = "{}", metadata: dict | None = None) -> SavedResponse:
    return store.save(body=body, suffix=".json", metadata=metadata or {"status": 200}, stem="get")


def test_save_writes_body_and_metadata(tmp_path: Path):
    saved = save(ResponseStore(tmp_path / "exec"), '{"a": 1}\n')

    assert saved.path.read_text() == '{"a": 1}\n'
    assert json.loads(saved.metadata_path.read_text()) == {"status": 200}
    assert saved.path.parent == tmp_path / "exec"


@pytest.mark.parametrize("existing_suffix", [".json", ".meta.json"])
def test_existing_file_is_never_overwritten_and_failed_save_leaves_nothing(tmp_path: Path, existing_suffix: str):
    store = ResponseStore(tmp_path / "exec")
    fixed = uuid.UUID(int=0)
    existing = store.root / f"0001-get-{fixed.hex[:8]}{existing_suffix}"
    existing.parent.mkdir(parents=True)
    existing.write_text("earlier evidence")

    with patch("ddev.ai.tools.http.response_store.uuid.uuid4", return_value=fixed):
        with pytest.raises(ResponseStoreError, match="overwrite"):
            save(store, "new")

    assert existing.read_text() == "earlier evidence"
    assert saved_files(store.root) == [existing]


def test_directory_that_cannot_be_created_raises_store_error(tmp_path: Path):
    blocker = tmp_path / "exec"
    blocker.write_text("not a directory")

    with pytest.raises(ResponseStoreError, match="Cannot create response directory"):
        save(ResponseStore(blocker / "responses"))


def test_lone_surrogates_are_saved_as_json_escapes(tmp_path: Path):
    value = json.loads('{"a": "\\ud800"}')

    saved = save(
        ResponseStore(tmp_path / "exec"),
        json.dumps(value, ensure_ascii=False),
        metadata={"request_body": value},
    )

    assert json.loads(saved.path.read_text()) == value
    assert json.loads(saved.metadata_path.read_text()) == {"request_body": value}
