"""Determine which integrations to release and emit the list to GITHUB_OUTPUT.

Resolution order for MANUAL_INTEGRATIONS:
  'all' / 'ALL'  → every integration found in the repo (glob for __about__.py)
  JSON array     → use the provided list as-is
  (empty)        → detect from git tags created at HEAD in this run
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from utils import set_output


def get_all_integrations() -> list[str]:
    return sorted(
        {path.parent.name for path in Path(".").glob("*/src/datadog_checks/*/__about__.py")}
    )


def detect_from_tags() -> list[str]:
    tags = subprocess.check_output(["git", "tag", "--points-at", "HEAD"], text=True)
    return sorted(
        {re.sub(r"-\d+\.\d+\.\d+.*", "", tag) for tag in tags.splitlines() if tag.strip()}
    )


def main() -> None:
    manual = os.environ.get("MANUAL_INTEGRATIONS", "").strip()

    if manual.lower() == "all":
        integrations = get_all_integrations()
    elif manual:
        try:
            integrations = json.loads(manual)
        except json.JSONDecodeError as e:
            print(f"MANUAL_INTEGRATIONS is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        integrations = detect_from_tags()

    set_output("integrations", json.dumps(integrations))


if __name__ == "__main__":
    main()
