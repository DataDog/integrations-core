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


def write_summary(content: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(content + "\n")


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
    no_version = []
    pre_release = []
    validated = []
    for package in packages:
        raw = get_version(package)
        if raw is None:
            no_version.append(package)
            continue
        if _PRE_RELEASE_RE.search(raw):
            pre_release.append(f"{package} ({raw})")
            continue
        if has_changelog_fragments(package):
            errors.append((package, raw))
        else:
            validated.append(f"{package} ({raw})")

    if no_version:
        print("Skipped (no version found):")
        for p in no_version:
            print(f"  - {p}")

    if pre_release:
        print("Skipped (pre-release):")
        for p in pre_release:
            print(f"  - {p}")

    rows = (
        [f"| `{p}` | ⚠️ No version found |" for p in no_version]
        + [f"| `{p}` | ⏭️ Pre-release, skipped |" for p in pre_release]
        + [f"| `{pkg} ({ver})` | ❌ Unreleased changelog fragments |" for pkg, ver in errors]
        + [f"| `{v}` | ✅ Ready |" for v in validated]
    )
    write_summary(
        "## Release Validation\n\n"
        "| Package | Status |\n"
        "|---------|--------|\n"
        + "\n".join(rows)
        + "\n"
    )

    if errors:
        print("\nRelease validation failed:", file=sys.stderr)
        for pkg, ver in errors:
            print(f"  {pkg} ({ver}): changelog.d/ contains unreleased fragments", file=sys.stderr)
        print(
            "\nRun 'ddev release make' to consolidate changelog fragments before releasing.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nValidated {len(validated)} package(s):")
    for v in validated:
        print(f"  - {v}")


if __name__ == "__main__":
    main()
