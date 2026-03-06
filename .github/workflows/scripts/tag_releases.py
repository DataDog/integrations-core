"""Tag all unreleased integrations via ddev and optionally push to origin.

Environment variables:
  TARGET  'prod' pushes tags; 'dev' (default) creates them locally only.
"""
import os
import subprocess
import sys


def main() -> None:
    target = os.environ.get("TARGET", "dev")
    if target != "prod":
        print(f"Target '{target}': tags will be created locally but not pushed to origin")

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    push_flag = "--push" if target == "prod" else "--no-push"
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
