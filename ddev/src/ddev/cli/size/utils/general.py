# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re

from ddev.utils.fs import Path


def get_valid_platforms(repo_path: Path | str, versions: set[str]) -> set[str]:
    """
    Extracts the platforms we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, ".deps", "resolved")
    platforms = []
    for file in os.listdir(resolved_path):
        if any(version in file for version in versions):
            platforms.append("_".join(file.split("_")[:-1]))
    return set(platforms)


def get_valid_versions(repo_path: Path | str) -> set[str]:
    """
    Extracts the Python versions we support from the .deps/resolved file names.
    """
    resolved_path = os.path.join(repo_path, ".deps", "resolved")
    versions = []
    pattern = re.compile(r"\d+\.\d+")
    for file in os.listdir(resolved_path):
        match = pattern.search(file)
        if match:
            versions.append(match.group())
    return set(versions)


def convert_to_human_readable_size(size_bytes: float) -> str:
    for unit in [" B", " KiB", " MiB", " GiB"]:
        if abs(size_bytes) < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"

