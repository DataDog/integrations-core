# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil

from ddev.utils.fs import Path


def reset_fragments_dir(path: Path) -> Path:
    """Recreate ``path`` as an empty directory."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path
