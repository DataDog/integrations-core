"""Dispatch build-wheels events to agent-integration-wheels-release in batches.

Environment variables: GH_TOKEN, PACKAGES, SOURCE_REPO, REF, TARGET.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BATCH_SIZE = 200
DISPATCH_URL = "https://api.github.com/repos/DataDog/agent-integration-wheels-release/dispatches"


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

    bucket = f"https://agent-integration-wheels-{target}.s3.amazonaws.com"
    print(f"Releasing {len(packages)} package(s) from {source_repo}@{ref} → {bucket}:")
    for name in packages:
        print(f"  - {name}")

    if dry_run:
        print("\nDRY RUN: no tags pushed, no builds triggered")
        return

    token = os.environ["GH_TOKEN"]
    batches = [packages[i : i + BATCH_SIZE] for i in range(0, len(packages), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)} ({len(batch)} packages)")
        dispatch(batch, source_repo, ref, target, token)


if __name__ == "__main__":
    main()
