# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Any, TextIO

import pytest
from mock import MagicMock

import datadog_checks.base.utils.tailfile as tailfile_utils
from datadog_checks.base.utils.tailfile import TailFile


def test_open_file_closes_crc_file_handle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_file = tmp_path / "test.log"
    log_file.write_text("a" * TailFile.CRC_SIZE)
    opened_files: list[TextIO] = []
    original_open = open

    def tracked_open(*args: Any, **kwargs: Any) -> TextIO:
        file_handle = original_open(*args, **kwargs)
        opened_files.append(file_handle)
        return file_handle

    def callback(_line: str) -> bool:
        return True

    monkeypatch.setattr(tailfile_utils, "open", tracked_open, raising=False)
    tail_file = TailFile(MagicMock(), str(log_file), callback)

    try:
        tail_file._open_file()

        assert len(opened_files) == 2
        assert opened_files[0].closed
        assert not opened_files[1].closed
    finally:
        tail_file.close()
