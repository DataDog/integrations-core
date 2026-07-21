"""Push locally prepared release tags.

Environment variables: NEW_TAGS (JSON array of tag names).
"""
import json
import os
import subprocess
import sys


def main() -> None:
    tags = json.loads(os.environ["NEW_TAGS"])
    if not tags:
        print("Error: no release tags were provided", file=sys.stderr)
        sys.exit(1)

    refspecs = [f"refs/tags/{tag}:refs/tags/{tag}" for tag in tags]
    subprocess.run(["git", "push", "--atomic", "origin", *refspecs], check=True)


if __name__ == "__main__":
    main()
