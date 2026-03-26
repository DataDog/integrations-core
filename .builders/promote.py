"""Promote dependency wheels from dev to stable storage.

Reads lockfiles from .deps/resolved/, identifies every wheel that lives
under the ``dev/`` prefix in GCS, and copies it to the ``stable/`` prefix.
Invoked via ``ddev promote <PR_URL>`` which dispatches the promote workflow.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

from google.cloud import storage

BUCKET_NAME = "deps-agent-int-datadoghq-com"
REPO_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE_DIR = REPO_DIR / ".deps" / "resolved"

DEV_PREFIX = "dev/"
STABLE_PREFIX = "stable/"

LOCKFILE_ENTRY = re.compile(
    r"^(?P<name>\S+)\s+@\s+(?P<url>\S+)$"
)


def parse_lockfile_urls(lockfile: Path) -> list[str]:
    """Extract wheel URLs from a lockfile."""
    urls: list[str] = []
    for line in lockfile.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        m = LOCKFILE_ENTRY.match(line)
        if m:
            urls.append(m.group("url").split("#")[0])
    return urls


def url_to_blob_path(url: str) -> str | None:
    """Convert a wheel URL to its GCS blob path, or None if not a dev/ path.

    Handles the templated ``\${PACKAGE_BASE_URL}/...`` format used in lockfiles.
    """
    if url.startswith("${PACKAGE_BASE_URL}/"):
        return url[len("${PACKAGE_BASE_URL}/"):]
    return None


def collect_relative_paths() -> list[str]:
    """Read all lockfiles and return relative wheel paths from \${PACKAGE_BASE_URL} entries."""
    if not LOCK_FILE_DIR.is_dir():
        print(f"No lockfile directory found at {LOCK_FILE_DIR}", file=sys.stderr)
        sys.exit(1)

    lockfiles = list(LOCK_FILE_DIR.glob("*.txt"))
    if not lockfiles:
        print(f"No lockfiles found in {LOCK_FILE_DIR}", file=sys.stderr)
        sys.exit(1)

    rel_paths: list[str] = []
    for lockfile in sorted(lockfiles):
        print(f"Reading {lockfile.name}")
        for url in parse_lockfile_urls(lockfile):
            rel_path = url_to_blob_path(url)
            if rel_path:
                rel_paths.append(rel_path)

    return rel_paths


def promote(rel_paths: list[str]) -> None:
    """Copy blobs from dev/ to stable/ in GCS."""
    if not rel_paths:
        print("No templated wheels found in lockfiles — nothing to promote.")
        return

    unique_paths = sorted(set(rel_paths))
    print(f"\nPromoting {len(unique_paths)} wheels from dev to stable...\n")

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    failed: list[str] = []
    for rel_path in unique_paths:
        dev_path = DEV_PREFIX + rel_path
        stable_path = STABLE_PREFIX + rel_path
        name = PurePosixPath(rel_path).name
        source_blob = bucket.blob(dev_path)

        if not source_blob.exists():
            print(f"  MISSING  {name}")
            failed.append(dev_path)
            continue

        bucket.copy_blob(source_blob, bucket, stable_path)
        print(f"  OK       {name}")

    print()
    if failed:
        print(
            f"ERROR: {len(failed)} wheel(s) not found in dev storage.\n"
            "The resolve-build-deps workflow may not have finished yet.\n"
            "Wait for it to complete, then run ddev promote again.",
            file=sys.stderr,
        )
        for p in failed:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. {len(unique_paths)} wheel(s) promoted to stable.")


if __name__ == "__main__":
    rel_paths = collect_relative_paths()
    promote(rel_paths)
