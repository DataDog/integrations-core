"""Dispatch build-integrations events to agent-integration-wheels-release in batches.

Environment variables: GH_TOKEN, INTEGRATIONS, SOURCE_REPO, REF, TARGET.
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
            "event_type": "build-integrations",
            "client_payload": {
                "integrations": batch,
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
    integrations = json.loads(os.environ["INTEGRATIONS"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ["REF"]
    target = os.environ["TARGET"]
    token = os.environ["GH_TOKEN"]

    batches = [integrations[i : i + BATCH_SIZE] for i in range(0, len(integrations), BATCH_SIZE)]

    print(f"Releasing {len(integrations)} integration(s) from {source_repo}@{ref} in {len(batches)} batch(es):")
    for name in integrations:
        print(f"  - {name}")

    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)} ({len(batch)} integrations)")
        dispatch(batch, source_repo, ref, target, token)


if __name__ == "__main__":
    main()
