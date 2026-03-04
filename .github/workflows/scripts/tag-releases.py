"""Run ddev release tag all and push new tags to origin.

Exit codes:
  0  new tags created and pushed (sets tagged=true)
  0  nothing to tag (sets tagged=false, caller should skip dispatch)
  *  propagated from ddev / git on unexpected failure
"""
import subprocess
import sys

from utils import set_output


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

    if result.returncode == 2:
        print("No new releases — skipping dispatch")
        set_output("tagged", "false")
        return

    if result.returncode != 0:
        sys.exit(result.returncode)

    set_output("tagged", "true")


if __name__ == "__main__":
    main()
