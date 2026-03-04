"""Tag releases with ddev and emit the integration list to GITHUB_OUTPUT.

Exit codes mirror ddev's own convention:
  0  success (integrations output set)
  2  nothing to tag (integrations=[] output set, no dispatch needed)
  *  propagated from ddev / git on unexpected failure
"""
import json
import os
import re
import subprocess
import sys


def set_output(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"{key}={value}\n")


manual = os.environ.get("MANUAL_INTEGRATIONS", "").strip()
if manual:
    set_output("integrations", manual)
    sys.exit(0)

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
    set_output("integrations", "[]")
    sys.exit(0)

if result.returncode != 0:
    sys.exit(result.returncode)

tags = subprocess.check_output(["git", "tag", "--points-at", "HEAD"], text=True)
integrations = sorted(
    {re.sub(r"-\d+\.\d+\.\d+.*", "", tag) for tag in tags.splitlines() if tag.strip()}
)
set_output("integrations", json.dumps(integrations))
