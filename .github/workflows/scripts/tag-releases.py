"""Run ddev release tag all and push new tags to origin.

Exit codes:
  0  success — tags created, already existed, or nothing to tag
  *  propagated from ddev / git on unexpected failure
"""
import subprocess
import sys


def main() -> None:
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    result = subprocess.run(["ddev", "release", "tag", "all", "--skip-prerelease", "--push"])
    if result.returncode == 3:
        # fetch failed — retry without fetching (tags already up-to-date locally)
        result = subprocess.run(
            ["ddev", "release", "tag", "all", "--skip-prerelease", "--push", "--no-fetch"]
        )

    # exit 2 means nothing new to tag — not an error, tags may already exist on HEAD
    if result.returncode not in (0, 2):
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
