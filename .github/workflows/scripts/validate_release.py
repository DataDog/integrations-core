"""Validate that packages are ready to release.

Runs ``ddev validate version`` (integrations-core only), then checks that
changelog.d/ is empty for every non-pre-release package.

Environment variables: PACKAGES, SOURCE_REPO.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_PRE_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+(a|b|rc)\d+")


def get_version(package: str) -> str | None:
    about = next(Path(package).glob("datadog_checks/*/__about__.py"), None)
    if about is None:
        return None
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', about.read_text())
    return match.group(1) if match else None


def has_changelog_fragments(package: str) -> bool:
    changelog_dir = Path(package) / "changelog.d"
    if not changelog_dir.is_dir():
        return False
    return any(changelog_dir.iterdir())


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]

    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + packages)
        if result.returncode != 0:
            sys.exit(result.returncode)

    errors = []
    for package in packages:
        raw = get_version(package)
        if raw is None or _PRE_RELEASE_RE.search(raw):
            continue
        if has_changelog_fragments(package):
            errors.append(f"{package} ({raw}): changelog.d/ contains unreleased fragments")

    if errors:
        print("Release validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        print(
            "\nRun 'ddev release make' to consolidate changelog fragments before releasing.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"All {len(packages)} package(s) passed release validation.")


if __name__ == "__main__":
    main()
