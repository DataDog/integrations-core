"""Dispatch build-wheels events to agent-integration-wheels-release in batches.

Environment variables: GH_TOKEN, PACKAGES, SOURCE_REPO, REF, TARGET.
"""
import json
import os
import sys
import urllib.error
import urllib.request

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


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ["REF"]
    target = os.environ["TARGET"]
    dry_run = os.environ.get("DRY_RUN", "").lower() != "false"

    source_link = f"[`{source_repo}@{ref[:12]}`](https://github.com/DataDog/{source_repo}/commit/{ref})"
    print(f"Releasing {len(packages)} package(s) from {source_repo}@{ref} → {target} S3:")
    for name in packages:
        print(f"  - {name}")

    if dry_run:
        print("\nDRY RUN: no tags pushed, no builds triggered")
        rows = "\n".join(f"| `{name}` |" for name in packages)
        write_summary(
            f"## Release Dispatch (Dry Run)\n\n"
            f"**Source:** {source_link} → {target} S3\n\n"
            f"| Package |\n"
            f"|---------|\n"
            f"{rows}\n\n"
            f"> Dry run — no tags pushed, no builds triggered\n"
        )
        return

    token = os.environ["GH_TOKEN"]
    batches = [packages[i : i + BATCH_SIZE] for i in range(0, len(packages), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f"\nBatch {i}/{len(batches)}:")
        for name in batch:
            print(f"  - {name}")
        dispatch(batch, source_repo, ref, target, token)

    print(f"\nTrack runs: {ACTIONS_URL}?query=event:repository_dispatch")
    actions_link = f"[Track downstream runs →]({ACTIONS_URL}?query=event:repository_dispatch)"
    write_summary(
        f"## Release Dispatch\n\n"
        f"**Source:** {source_link} → {target} S3\n\n"
        f"| Package | Status |\n"
        f"|---------|--------|\n"
        + "\n".join(f"| `{name}` | ✅ Dispatched |" for name in packages)
        + f"\n\n{actions_link}\n"
    )


if __name__ == "__main__":
    main()
