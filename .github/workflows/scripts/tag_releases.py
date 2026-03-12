"""Tag packages via ddev and optionally push to origin.

Environment variables:
  TARGET          'prod' pushes tags; 'dev' (default) creates them locally only
  DRY_RUN         When true, tags are created locally but never pushed
  MANUAL_PACKAGES JSON array of packages to tag, 'all', or empty to tag all
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.github import parse_bool_env


def _package_args(manual: str) -> list[str]:
    """Return the package arguments for ``ddev release tag``."""
    manual = manual.strip()
    if not manual or manual.lower() == "all":
        return ["all"]
    try:
        packages = json.loads(manual)
    except json.JSONDecodeError as e:
        print(f"MANUAL_PACKAGES is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    return packages if packages else ["all"]


def main() -> None:
    target = os.environ.get("TARGET", "dev")
    dry_run = parse_bool_env("DRY_RUN", default=False)
    manual = os.environ.get("MANUAL_PACKAGES", "")

    if dry_run:
        print("DRY RUN: tags will be created locally but not pushed to origin")
    elif target != "prod":
        print(f"Target '{target}': tags will be created locally but not pushed to origin")

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    push_flag = "--push" if (target == "prod" and not dry_run) else "--no-push"
    base_cmd = ["ddev", "release", "tag"] + _package_args(manual) + ["--skip-prerelease", push_flag]

    result = subprocess.run(base_cmd)
    if result.returncode == 3:
        # fetch failed — retry without fetching (tags already up-to-date locally)
        result = subprocess.run(base_cmd + ["--no-fetch"])

    # exit 2 means nothing new to tag — not an error, tags may already exist on HEAD
    if result.returncode not in (0, 2):
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
