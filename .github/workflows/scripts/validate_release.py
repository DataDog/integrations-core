"""Validate that packages are ready to release.

Runs ``ddev validate version`` (integrations-core only), then checks that
changelog.d/ is empty for every non-pre-release package.

Environment variables: PACKAGES, SOURCE_REPO, REF, TARGET, DRY_RUN, MODE.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.github import parse_bool_env, write_summary
from _release.summary import build_summary
from _release.validation import HAS_FRAGMENTS, NO_VERSION, PRE_RELEASE, READY, validate_packages


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ.get("REF", "")
    target = os.environ.get("TARGET", "")
    dry_run = parse_bool_env("DRY_RUN", default=False)
    mode = os.environ.get("MODE", "")

    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + packages)
        if result.returncode != 0:
            sys.exit(result.returncode)

    results = validate_packages(packages)

    # Persist results for the dispatch step.
    runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
    Path(runner_temp, "release_validation.json").write_text(
        json.dumps({"results": results, "mode": mode, "ref": ref, "target": target, "dry_run": dry_run})
    )

    by_status: dict[str, list] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    no_version = by_status.get(NO_VERSION, [])
    pre_release = by_status.get(PRE_RELEASE, [])
    errors = by_status.get(HAS_FRAGMENTS, [])
    validated = by_status.get(READY, [])

    if no_version:
        print("Skipped (no version found):")
        for r in no_version:
            print(f"  - {r['package']}")

    if pre_release:
        print("Skipped (pre-release):")
        for r in pre_release:
            print(f"  - {r['package']} ({r['version']})")

    if errors:
        print("\nRelease validation failed:", file=sys.stderr)
        for r in errors:
            print(
                f"  {r['package']} ({r['version']}): changelog.d/ contains unreleased fragments",
                file=sys.stderr,
            )
        print(
            "\nRun 'ddev release make' to consolidate changelog fragments before releasing.",
            file=sys.stderr,
        )
        # Dispatch won't run — write the comprehensive summary here.
        write_summary(
            build_summary(
                packages,
                results,
                mode,
                source_repo,
                ref,
                target,
                dry_run,
                dispatched=False,
                footer="> ⚠️ Validation failed — run `ddev release make` to consolidate changelog fragments before releasing.",
            )
        )
        sys.exit(1)

    print(f"\nValidated {len(validated)} package(s):")
    for r in validated:
        print(f"  - {r['package']} ({r['version']})")


if __name__ == "__main__":
    main()
