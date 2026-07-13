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
    """Walk the given directories and yield parsed config files or errors.

    Each physical file is yielded once: overlapping directories and symlink aliases
    resolve to the same path, so a file reachable from several roots is not read twice.
    """
    seen: set[Path] = set()
    for base in dirs:
        for root, dirnames, filenames in base.walk():
            dirnames.sort()
            for filename in sorted(filenames):
                path = root / filename
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
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
