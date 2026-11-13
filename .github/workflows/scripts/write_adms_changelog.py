"""Write `.security` changelog fragments for the checks an ADMS PR changes.

Run by sync-dependency-pins.yaml after `ddev dep sync`. Every top-level folder whose
pyproject.toml differs between the PR's merge base and the working tree gets
`<folder>/changelog.d/<PR>.security` unless it already has a fragment for the PR.

The diff is taken against the working tree, not the PR's own patches, because the sync
can undo a PR change: `ddev dep sync` resets a check pin that ADMS bumped without
bumping agent_requirements.in.
"""

import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

API_URL = "https://api.github.com"
FALLBACK_MESSAGE = "Update dependencies to address security vulnerabilities."
# Folders under the repo root that are not released packages.
NON_PACKAGE_FOLDERS = {".builders"}
# An added dependency line such as `+    "pymongo==4.18.3",` or `+    "virtualenv>=21.14.5",`.
ADDED_PIN = re.compile(r'^\+\s*"([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(?:==|>=|~=)\s*([^",;\s]+)')
# ADMS opens its PR a few seconds after pushing, so the PR should exist by the time this runs.
PR_LOOKUP_ATTEMPTS = 6
PR_LOOKUP_DELAY_SECONDS = 10


def github_get(path: str, token: str) -> object:
    req = urllib.request.Request(
        f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def find_pr(repo: str, branch: str, token: str) -> dict | None:
    owner = repo.split("/")[0]
    for attempt in range(PR_LOOKUP_ATTEMPTS):
        pulls = github_get(f"/repos/{repo}/pulls?head={owner}:{branch}&state=open", token)
        if pulls:
            return pulls[0]
        if attempt < PR_LOOKUP_ATTEMPTS - 1:
            time.sleep(PR_LOOKUP_DELAY_SECONDS)
    return None


def merge_base(repo: str, base_ref: str, head_sha: str, token: str) -> str:
    comparison = github_get(f"/repos/{repo}/compare/{base_ref}...{head_sha}", token)
    return comparison["merge_base_commit"]["sha"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def split_diff_by_file(diff: str) -> dict[str, str]:
    """Split `git diff` output into {path: hunks} keyed by the post-change path."""
    patches: dict[str, str] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[len("+++ b/") :]
            patches[current] = ""
        elif current is not None and not line.startswith(("diff --git", "index ", "--- ")):
            patches[current] += line + "\n"
    return patches


def added_pins(patch: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in patch.splitlines():
        if match := ADDED_PIN.match(line):
            pins.setdefault(match.group(1), match.group(2))
    return pins


def build_message(pins: dict[str, str]) -> str:
    if not pins:
        return FALLBACK_MESSAGE
    bumps = [f"`{name}` to {version}" for name, version in sorted(pins.items())]
    if len(bumps) == 1:
        joined = bumps[0]
    elif len(bumps) == 2:
        joined = f"{bumps[0]} and {bumps[1]}"
    else:
        joined = f"{', '.join(bumps[:-1])}, and {bumps[-1]}"
    return f"Bump {joined}."


def fragments_to_write(patches: dict[str, str], pr_number: int, repo_root: Path) -> dict[Path, str]:
    """Map each fragment path that should be created to its message."""
    pins_by_folder: dict[str, dict[str, str]] = {}
    for path, patch in patches.items():
        parts = path.split("/")
        if len(parts) != 2 or parts[1] != "pyproject.toml" or parts[0] in NON_PACKAGE_FOLDERS:
            continue
        pins_by_folder[parts[0]] = added_pins(patch)

    fragments: dict[Path, str] = {}
    for folder, pins in sorted(pins_by_folder.items()):
        changelog_dir = repo_root / folder / "changelog.d"
        if any(changelog_dir.glob(f"{pr_number}.*")):
            continue
        fragments[changelog_dir / f"{pr_number}.security"] = build_message(pins)
    return fragments


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["GITHUB_REF_NAME"]
    token = os.environ["GITHUB_TOKEN"]

    pr = find_pr(repo, branch, token)
    if pr is None:
        print(f"::warning::No open PR found for {branch}; skipping changelog fragments.")
        return
    pr_number = pr["number"]

    base_sha = merge_base(repo, pr["base"]["ref"], git("rev-parse", "HEAD").strip(), token)
    git("fetch", "--depth=1", "--no-tags", "origin", base_sha)
    patches = split_diff_by_file(git("diff", base_sha, "--", "*/pyproject.toml"))

    for path, message in fragments_to_write(patches, pr_number, Path.cwd()).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{message}\n")
        print(f"Wrote {path}: {message}")


if __name__ == "__main__":
    main()
