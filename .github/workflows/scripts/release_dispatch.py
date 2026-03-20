"""Dispatch build-wheels events to agent-integration-wheels-release in batches.

Environment variables: GH_TOKEN, PACKAGES, SOURCE_REPO, REF, TARGET, DRY_RUN.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.dispatch import DispatchError, dispatch_in_batches
from _release.github import parse_bool_env, write_summary
from _release.summary import build_summary


def _load_validation(runner_temp: str) -> dict:
    path = Path(runner_temp) / "release_validation.json"
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(
            f"Warning: validation results not found at {path}. Summary may be incomplete.",
            file=sys.stderr,
        )
        return {}
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
    target = os.environ["TARGET"]

    validation = _load_validation(os.environ.get("RUNNER_TEMP", "/tmp"))
    results = validation.get("results", [])
    mode = validation.get("mode", "")
    dry_run = validation.get("dry_run", parse_bool_env("DRY_RUN", default=False))

    print(f"Releasing {len(packages)} package(s) from {source_repo}@{ref} → {target} S3:")

    if dry_run:
        for name in packages:
            print(f"  - {name}")
        print("\nDRY RUN: no tags pushed, no builds triggered")
        write_summary(build_summary(packages, results, mode, source_repo, ref, target, dry_run, was_dispatched=False))
        return

    token = os.environ["GH_TOKEN"]
    try:
        dispatch_in_batches(packages, source_repo, ref, target, token)
    except DispatchError:
        sys.exit(1)

    write_summary(build_summary(packages, results, mode, source_repo, ref, target, dry_run, was_dispatched=True))


if __name__ == "__main__":
    main()
