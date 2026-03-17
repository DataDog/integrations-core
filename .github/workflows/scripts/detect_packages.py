"""Determine which packages to release and emit the list to GITHUB_OUTPUT.

Resolution order for SELECTED_PACKAGES:
  'all' / 'ALL'  → every Python package found in the repo (glob for __about__.py)
  JSON array     → use the provided list as-is
  (empty)        → detect from git tags created at HEAD in this run
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.github import set_outputs, write_summary
from _release.packages import get_all_packages, resolve_packages


def main() -> None:
    selected = os.environ.get("SELECTED_PACKAGES", "").strip()
    all_packages = get_all_packages()
    packages, mode = resolve_packages(selected, all_packages)

    print(f"Mode: {mode}")

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
