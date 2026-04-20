# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Scanner, env-var resolver, and manifest helpers for `ddev validate images`.

Public surface:
  scan_repo(app) -> Manifest
  load_manifest(path) -> Manifest
  write_manifest(path, manifest) -> None
  diff_manifests(old, new) -> ManifestDiff
  classify(image, prefixes) -> bool
"""
from __future__ import annotations
