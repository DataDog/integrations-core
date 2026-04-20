"""Client payload builder for repository_dispatch events."""

BATCH_SIZE = 200


def build_client_payload(packages: list[str], source_repo: str, ref: str) -> dict:
    """Return the ``client_payload`` dict for one batch."""
    return {
        "packages": packages,
        "source_repo": source_repo,
        "source_repo_ref": ref,
    }


def build_batches(
    packages: list[str],
    source_repo: str,
    ref: str,
    batch_size: int = BATCH_SIZE,
) -> list[dict]:
    """Split packages into batches and return a list of client_payload dicts."""
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    if not packages:
        return []
    return [
        build_client_payload(packages[i : i + batch_size], source_repo, ref)
        for i in range(0, len(packages), batch_size)
    ]
