"""HTTP dispatch logic for repository_dispatch events."""
import json
import sys
import urllib.error
import urllib.request

BATCH_SIZE = 200
_TARGET_REPO = "DataDog/agent-integration-wheels-release"
_DISPATCH_URL = f"https://api.github.com/repos/{_TARGET_REPO}/dispatches"


def build_payload(batch: list[str], source_repo: str, ref: str, target: str) -> dict:
    """Return the ``repository_dispatch`` payload for one batch."""
    return {
        "event_type": "build-wheels",
        "client_payload": {
            "packages": batch,
            "source_repo": source_repo,
            "source_repo_ref": ref,
            "target": target,
        },
    }


def send_dispatch(payload: dict, token: str) -> None:
    """POST a single ``repository_dispatch`` event to the wheels-release repo.

    Calls ``sys.exit(1)`` on HTTP errors.
    """
    req = urllib.request.Request(
        _DISPATCH_URL,
        data=json.dumps(payload).encode(),
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


def dispatch_in_batches(
    packages: list[str],
    source_repo: str,
    ref: str,
    target: str,
    token: str,
) -> None:
    """Dispatch all packages to the wheels-release repo, batching if needed."""
    batches = [packages[i : i + BATCH_SIZE] for i in range(0, len(packages), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f"\nBatch {i}/{len(batches)}:")
        for name in batch:
            print(f"  - {name}")
        send_dispatch(build_payload(batch, source_repo, ref, target), token)
