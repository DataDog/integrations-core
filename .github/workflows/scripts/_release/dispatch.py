"""HTTP dispatch logic for repository_dispatch events."""
import json
import sys
import time
import urllib.error
import urllib.request

BATCH_SIZE = 200
_TARGET_REPO = "DataDog/agent-integration-wheels-release"
DISPATCH_URL = f"https://api.github.com/repos/{_TARGET_REPO}/dispatches"
MAX_ATTEMPTS = 5


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


def _urlopen(req: urllib.request.Request):
    """Thin urllib wrapper — exists so tests can patch it without touching stdlib."""
    return urllib.request.urlopen(req)


def send_dispatch(
    payload: dict,
    token: str,
    *,
    dispatch_url: str = DISPATCH_URL,
    max_attempts: int = MAX_ATTEMPTS,
) -> None:
    """POST a single ``repository_dispatch`` event to the wheels-release repo.

    Retries up to ``max_attempts`` times on 5xx errors with exponential backoff.
    Calls ``sys.exit(1)`` on 4xx errors or after exhausting retries.
    """
    req = urllib.request.Request(
        dispatch_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    for attempt in range(1, max_attempts + 1):
        try:
            with _urlopen(req) as resp:
                print(f"  Dispatched: HTTP {resp.status}")
                return
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code < 500 or attempt == max_attempts:
                print(body, file=sys.stderr)
                sys.exit(1)
            print(f"  HTTP {e.code} on attempt {attempt}/{max_attempts}, retrying...", file=sys.stderr)
            time.sleep(2**attempt)


def dispatch_in_batches(
    packages: list[str],
    source_repo: str,
    ref: str,
    target: str,
    token: str,
    batch_size: int = BATCH_SIZE,
) -> None:
    """Dispatch all packages to the wheels-release repo, batching if needed."""
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    nbr_packages = len(packages)
    if nbr_packages == 0:
        return
    total_batches = (nbr_packages + batch_size - 1) // batch_size
    for batch_num, start in enumerate(range(0, nbr_packages, batch_size), 1):
        end = min(start + batch_size, nbr_packages)
        current_batch = packages[start:end]
        print(f"\nBatch {batch_num}/{total_batches}:")
        print("\n".join(f"  - {name}" for name in current_batch))
        send_dispatch(build_payload(current_batch, source_repo, ref, target), token)
