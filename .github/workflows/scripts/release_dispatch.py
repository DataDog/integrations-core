"""Build repository_dispatch batches and write the release summary.

Environment variables: PACKAGES, SOURCE_REPO, REF, DRY_RUN.
Outputs: batches (JSON array of client_payload dicts, one per batch).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.dispatch import build_batches
from _release.github import parse_bool_env, set_outputs, write_summary
from _release.summary import build_summary


def _load_validation(runner_temp: str) -> dict:
    path = Path(runner_temp) / "release_validation.json"
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(
            f"Error: validation results not found at {path}. "
            "The prepare step likely failed before writing the file.",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(
            f"Warning: validation results at {path} are not valid JSON: {e}. Summary may be incomplete.",
            file=sys.stderr,
        )
        return {}


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ["REF"]

    dry_run = parse_bool_env("DRY_RUN", default=False)

    validation = _load_validation(os.environ.get("RUNNER_TEMP", "/tmp"))
    results = validation.get("results", [])
    mode = validation.get("mode", "")

    print(f"Releasing {len(packages)} package(s) from {source_repo}@{ref}:")

    if dry_run:
        for name in packages:
            print(f"  - {name}")
        print("\nDRY RUN: no tags pushed, no builds triggered")
        write_summary(build_summary(packages, results, mode, source_repo, ref, dry_run=True, was_dispatched=False))
        return

    batches = build_batches(packages, source_repo, ref)
    set_outputs(batches=json.dumps(batches))
    write_summary(build_summary(packages, results, mode, source_repo, ref, dry_run=False, was_dispatched=False))


if __name__ == "__main__":
    main()
