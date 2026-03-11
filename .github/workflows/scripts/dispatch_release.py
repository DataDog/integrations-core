"""Dispatch build-wheels events to agent-integration-wheels-release in batches.

Environment variables: GH_TOKEN, PACKAGES, SOURCE_REPO, REF, TARGET, DRY_RUN.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BATCH_SIZE = 200
TARGET_REPO = "DataDog/agent-integration-wheels-release"
DISPATCH_URL = f"https://api.github.com/repos/{TARGET_REPO}/dispatches"
ACTIONS_URL = f"https://github.com/{TARGET_REPO}/actions"


def write_summary(content: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(content + "\n")


def dispatch(batch: list[str], source_repo: str, ref: str, target: str, token: str) -> None:
    payload = json.dumps(
        {
            "event_type": "build-wheels",
            "client_payload": {
                "packages": batch,
                "source_repo": source_repo,
                "source_repo_ref": ref,
                "target": target,
            },
        }
    ).encode()

    req = urllib.request.Request(
        DISPATCH_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"  Dispatched: HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        sys.exit(1)


def build_summary(
    packages: list[str],
    validation: dict,
    source_repo: str,
    ref: str,
    target: str,
    dry_run: bool,
    dispatched: bool,
) -> str:
    source_link = f"[`{source_repo}@{ref[:12]}`](https://github.com/DataDog/{source_repo}/commit/{ref})"
    mode = validation.get("mode", "")
    by_package = {r["package"]: r for r in validation.get("results", [])}

    rows = []
    for name in packages:
        r = by_package.get(name, {})
        ver = r.get("version") or "—"
        s = r.get("status", "ready")
        if s == "no_version":
            status = "⚠️ No version found"
        elif s == "pre_release":
            status = "⏭️ Pre-release, skipped"
        elif dry_run:
            status = "🔄 Dry run"
        else:
            status = "✅ Dispatched"
        rows.append(f"| `{name}` | `{ver}` | {status} |")

    if dispatched:
        footer = f"[Track downstream runs →]({ACTIONS_URL}?query=event:repository_dispatch)"
    else:
        footer = "> Dry run — no tags pushed, no builds triggered"

    return (
        "## Wheel Release\n\n"
        "| | |\n|---|---|\n"
        f"| **Mode** | {mode} |\n"
        f"| **Source** | {source_link} |\n"
        f"| **Target** | {target} S3 |\n"
        f"| **Dry run** | {'Yes' if dry_run else 'No'} |\n\n"
        "| Package | Version | Status |\n"
        "|---------|---------|--------|\n"
        + "\n".join(rows)
        + f"\n\n{footer}\n"
    )


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ["REF"]
    target = os.environ["TARGET"]
    dry_run = os.environ.get("DRY_RUN", "").lower() != "false"

    results_path = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "release_validation.json"
    try:
        validation = json.loads(results_path.read_text())
    except FileNotFoundError:
        validation = {}

    print(f"Releasing {len(packages)} package(s) from {source_repo}@{ref} → {target} S3:")

    if dry_run:
        for name in packages:
            print(f"  - {name}")
        print("\nDRY RUN: no tags pushed, no builds triggered")
        write_summary(build_summary(packages, validation, source_repo, ref, target, dry_run, dispatched=False))
        return

    token = os.environ["GH_TOKEN"]
    batches = [packages[i : i + BATCH_SIZE] for i in range(0, len(packages), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f"\nBatch {i}/{len(batches)}:")
        for name in batch:
            print(f"  - {name}")
        dispatch(batch, source_repo, ref, target, token)

    print(f"\nTrack runs: {ACTIONS_URL}?query=event:repository_dispatch")
    write_summary(build_summary(packages, validation, source_repo, ref, target, dry_run, dispatched=True))


if __name__ == "__main__":
    main()
