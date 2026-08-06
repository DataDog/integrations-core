"""Promote dependency wheels from dev to stable storage.

Reads lockfiles from .deps/resolved/, identifies every wheel that lives
under the ``dev/`` prefix in GCS, and copies it to the ``stable/`` prefix.
Invoked via ``ddev promote <PR_URL>`` which dispatches the promote workflow.

``--verify`` reports whether those wheels are already in stable storage instead
of copying anything. The promotion gate uses it to tell a PR that still needs
promoting apart from one that is already done.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

try:
    from google.cloud import storage
except ImportError:
    # --verify needs only the standard library, so the bucket client is optional.
    storage = None  # type: ignore[assignment]

BUCKET_NAME = "deps-agent-int-datadoghq-com"
REPO_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE_DIR = REPO_DIR / ".deps" / "resolved"

DEV_PREFIX = "dev/"
STABLE_PREFIX = "stable/"

VERIFY_WORKERS = 16
VERIFY_ATTEMPTS = 3
VERIFY_TIMEOUT = 15

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


STORAGE_BASE = "https://agent-int-packages.datadoghq.com/"
STORAGE_TEMPLATE_PREFIX = f"{STORAGE_BASE}${{INTEGRATIONS_WHEELS_STORAGE}}/"
STABLE_URL_PREFIX = f"{STORAGE_BASE}{STABLE_PREFIX}"


def url_to_blob_path(url: str) -> str | None:
    """Convert a wheel URL to its GCS blob path, or None if not a templated storage URL.

    Handles the templated ``https://agent-int-packages.datadoghq.com/${INTEGRATIONS_WHEELS_STORAGE}/...``
    format used in lockfiles.
    """
    if url.startswith(STORAGE_TEMPLATE_PREFIX):
        return url[len(STORAGE_TEMPLATE_PREFIX):]
    return None


def collect_relative_paths() -> list[str]:
    """Read all lockfiles and return relative wheel paths from ${INTEGRATIONS_WHEELS_STORAGE} entries."""
    lockfile_dir = Path(os.environ.get("PROMOTE_LOCKFILE_DIR", LOCK_FILE_DIR))

    if not lockfile_dir.is_dir():
        print(f"No lockfile directory found at {lockfile_dir}", file=sys.stderr)
        sys.exit(1)

    lockfiles = list(lockfile_dir.glob("*.txt"))
    if not lockfiles:
        print(f"No lockfiles found in {lockfile_dir}", file=sys.stderr)
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

    if storage is None:
        print(
            "google-cloud-storage is not installed, so wheels cannot be promoted. "
            "Install .builders/deps/host_dependencies.txt first.",
            file=sys.stderr,
        )
        sys.exit(1)

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


def stable_wheel_exists(rel_path: str) -> bool:
    """Whether `rel_path` is already published under the stable prefix.

    Raises if the answer cannot be established, rather than assuming either way.
    """
    request = urllib.request.Request(f"{STABLE_URL_PREFIX}{rel_path}", method="HEAD")
    last_error: Exception | None = None
    for attempt in range(VERIFY_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=VERIFY_TIMEOUT) as response:
                return response.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            last_error = e
        except urllib.error.URLError as e:
            last_error = e

        if attempt < VERIFY_ATTEMPTS - 1:
            time.sleep(2**attempt)

    raise RuntimeError(f"Could not determine whether {rel_path} is in stable storage: {last_error}")


def find_unpromoted(rel_paths: list[str]) -> list[str]:
    """Return the wheels in `rel_paths` that are not in stable storage yet."""
    unique_paths = sorted(set(rel_paths))
    with ThreadPoolExecutor(max_workers=VERIFY_WORKERS) as pool:
        checks = pool.map(stable_wheel_exists, unique_paths)
        return [rel_path for rel_path, exists in zip(unique_paths, checks) if not exists]


def write_github_output(name: str, value: str) -> None:
    """Append `name=value` to $GITHUB_OUTPUT, or do nothing outside GitHub Actions."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        print(f"(not running under GitHub Actions) {name}={value}")
        return

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def verify(rel_paths: list[str]) -> None:
    """Report whether every wheel the lockfiles pin is already in stable storage."""
    if not rel_paths:
        # Lockfiles that pin nothing from our storage are broken, not complete.
        print("No ${INTEGRATIONS_WHEELS_STORAGE} wheels found in the lockfiles.", file=sys.stderr)
        sys.exit(1)

    unique_total = len(set(rel_paths))
    print(f"\nChecking {unique_total} wheels against stable storage...\n")

    unpromoted = find_unpromoted(rel_paths)
    for rel_path in unpromoted:
        print(f"  MISSING  {PurePosixPath(rel_path).name}")

    if unpromoted:
        print(f"\n{len(unpromoted)} of {unique_total} wheel(s) are not in stable storage yet.")
    else:
        print(f"All {unique_total} wheel(s) are already in stable storage.")

    write_github_output("promoted", "false" if unpromoted else "true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote dependency wheels from dev to stable storage.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Report whether the wheels are already in stable storage instead of copying them.",
    )
    args = parser.parse_args()

    rel_paths = collect_relative_paths()
    if args.verify:
        verify(rel_paths)
    else:
        promote(rel_paths)


if __name__ == "__main__":
    main()
