"""Validate that integrations are ready to release.

Runs ``ddev validate version`` (integrations-core only), then checks that
changelog.d/ is empty for every non-pre-release integration.

Environment variables: INTEGRATIONS, SOURCE_REPO.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_PRE_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+(a|b|rc)\d+")


def get_version(integration: str) -> str | None:
    about = next(Path(integration).glob("datadog_checks/*/__about__.py"), None)
    if about is None:
        return None
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', about.read_text())
    return match.group(1) if match else None


def has_changelog_fragments(integration: str) -> bool:
    changelog_dir = Path(integration) / "changelog.d"
    if not changelog_dir.is_dir():
        return False
    return any(changelog_dir.iterdir())


def main() -> None:
    integrations = json.loads(os.environ["INTEGRATIONS"])
    source_repo = os.environ["SOURCE_REPO"]

    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + integrations)
        if result.returncode != 0:
            sys.exit(result.returncode)

    errors = []
    for integration in integrations:
        raw = get_version(integration)
        if raw is None or _PRE_RELEASE_RE.search(raw):
            continue
        if has_changelog_fragments(integration):
            errors.append(f"{integration} ({raw}): changelog.d/ contains unreleased fragments")

    if errors:
        print("Release validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        print(
            "\nRun 'ddev release make' to consolidate changelog fragments before releasing.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"All {len(integrations)} integration(s) passed release validation.")


if __name__ == "__main__":
    main()
