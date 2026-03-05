"""Run ddev release tag all and push new tags to origin.

Exit codes:
  0  success — tags created, already existed, or nothing to tag
  *  propagated from ddev / git on unexpected failure

Environment variables:
  DRY_RUN  if 'true', create tags locally but do not push to origin
"""
import os
import subprocess
import sys


def main() -> None:
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    if dry_run:
        print("Dry-run mode: tags will be created locally but not pushed to origin")

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    push_flag = "--no-push" if dry_run else "--push"
    base_cmd = ["ddev", "release", "tag", "all", "--skip-prerelease", push_flag]

    result = subprocess.run(base_cmd)
    if result.returncode == 3:
        # fetch failed — retry without fetching (tags already up-to-date locally)
        result = subprocess.run(base_cmd + ["--no-fetch"])

    # exit 2 means nothing new to tag — not an error, tags may already exist on HEAD
    if result.returncode not in (0, 2):
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
