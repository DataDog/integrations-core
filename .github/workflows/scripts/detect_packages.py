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


def write_summary(content: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(content + "\n")


def get_all_packages() -> list[str]:
    return sorted(
        {path.parent.parent.parent.name for path in Path(".").glob("*/datadog_checks/*/__about__.py")}
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
        mode = f"all ({len(all_packages)} packages in repo)"
        packages = all_packages
    elif manual:
        mode = f"manual ({manual})"
        try:
            packages = json.loads(manual)
        except json.JSONDecodeError as e:
            print(f"MANUAL_PACKAGES is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        mode = "auto-detect from tags at HEAD"
        packages = detect_from_tags()

    print(f"Mode: {mode}")

    unknown = set(packages) - set(all_packages)
    if unknown:
        print(f"Unknown packages: {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    if packages:
        print(f"\nDetected {len(packages)} package(s) to release:")
        for name in packages:
            print(f"  - {name}")
    else:
        print("No packages detected — nothing to release")
        write_summary("## Wheel Release\n\nNo packages detected — nothing to release.\n")

    set_outputs(
        packages=json.dumps(packages),
        has_packages="true" if packages else "false",
        mode=mode,
    )


if __name__ == "__main__":
    main()
