# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.files import FileError, MarkdownFile, YamlFile
from ddev.ai.config.loading.markdown import parse_markdown
from ddev.ai.config.loading.yaml import load_yaml


def discover(dirs: list[Path]) -> Iterator[MarkdownFile | YamlFile | FileError]:
    """Walk the given directories and yield parsed config files or errors."""
    for base in dirs:
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            try:
                if suffix == ".md":
                    result = parse_markdown(path)
                elif suffix in {".yaml", ".yml"}:
                    result = load_yaml(path)
                else:
                    continue
            except ConfigError as e:
                yield FileError(path, str(e))
                continue
            if result is not None:
                yield result
