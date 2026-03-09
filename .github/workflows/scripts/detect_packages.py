"""Determine which packages to release and emit the list to GITHUB_OUTPUT.

Resolution order for MANUAL_PACKAGES:
  'all' / 'ALL'  → every Python package found in the repo (glob for __about__.py)
  JSON array     → use the provided list as-is
  (empty)        → detect from git tags created at HEAD in this run
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def set_outputs(**kwargs: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for key, value in kwargs.items():
            f.write(f"{key}={value}\n")


def get_all_packages() -> list[str]:
    return sorted(
        {path.parent.name for path in Path(".").glob("*/datadog_checks/*/__about__.py")}
    )


def detect_from_tags() -> list[str]:
    tags = subprocess.check_output(["git", "tag", "--points-at", "HEAD"], text=True)
    return sorted(
        {re.sub(r"-\d+\.\d+\.\d+.*", "", tag) for tag in tags.splitlines() if tag.strip()}
    )


def main() -> None:
    manual = os.environ.get("MANUAL_PACKAGES", "").strip()
    all_packages = get_all_packages()

    if manual.lower() == "all":
        packages = all_packages
    elif manual:
        try:
            packages = json.loads(manual)
        except json.JSONDecodeError as e:
            print(f"MANUAL_PACKAGES is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        packages = detect_from_tags()

    unknown = set(packages) - set(all_packages)
    if unknown:
        print(f"Unknown packages: {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    set_outputs(
        packages=json.dumps(packages),
        has_packages="true" if packages else "false",
    )


if __name__ == "__main__":
    main()
