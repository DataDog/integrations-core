# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path


class FileRegistry:
    """Registry of the files that have been created by the CreateFileTool."""

    def __init__(self):
        self._files: set[str] = set()

    def register_file(self, path: str):
        self._files.add(Path(path).resolve().as_posix())

    def is_registered(self, path: str) -> bool:
        return Path(path).resolve().as_posix() in self._files
