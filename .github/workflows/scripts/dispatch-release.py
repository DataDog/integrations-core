"""Send repository_dispatch events to agent-integration-wheels-release.

Integrations are split into batches and dispatched as separate workflow runs
to stay within payload size limits.

Required environment variables:
  GH_TOKEN      short-lived token from dd-octo-sts
  INTEGRATIONS  JSON array of integration names
  SOURCE_REPO   source repository name (e.g. integrations-core)
  REF           commit SHA or ref to build from
"""
import json
import os
import sys
import urllib.error
import urllib.request

BATCH_SIZE = 200
DISPATCH_URL = "https://api.github.com/repos/DataDog/agent-integration-wheels-release/dispatches"


def dispatch(batch: list[str], source_repo: str, ref: str) -> None:
    payload = json.dumps(
        {
            "event_type": "build-integrations",
            "client_payload": {
                "integrations": batch,
                "source_repo": source_repo,
                "source_repo_ref": ref,
            },
        }
    ).encode()

    req = urllib.request.Request(
        DISPATCH_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
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
        raise


def main() -> None:
    integrations = json.loads(os.environ["INTEGRATIONS"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ["REF"]

    batches = [integrations[i : i + BATCH_SIZE] for i in range(0, len(integrations), BATCH_SIZE)]

    print(f"Releasing {len(integrations)} integration(s) from {source_repo}@{ref} in {len(batches)} batch(es):")
    for name in integrations:
        print(f"  - {name}")

    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)} ({len(batch)} integrations)")
        dispatch(batch, source_repo, ref)


if __name__ == "__main__":
    main()
