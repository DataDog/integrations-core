"""Validate that packages are ready to release.

Runs ``ddev validate version`` (integrations-core only), then checks that
changelog.d/ is empty for every stable package.

Environment variables: PACKAGES, SOURCE_REPO, REF, TARGET, DRY_RUN, MODE, IS_STABLE_RELEASE.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.github import parse_bool_env, write_summary
from _release.summary import build_summary
from _release.validation import HAS_FRAGMENTS, NO_VERSION, PRE_RELEASE, STABLE, UNRELEASED, validate_packages


def _parse_is_stable_release() -> bool:
    """Parse IS_STABLE_RELEASE: 'false' → False, anything else (including unset) → True (stable)."""
    return os.environ.get("IS_STABLE_RELEASE", "true").strip().lower() != "false"


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ.get("REF", "")
    target = os.environ.get("TARGET", "")
    dry_run = parse_bool_env("DRY_RUN", default=False)
    is_stable_release: bool = _parse_is_stable_release()
    mode = os.environ.get("MODE", "")

    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + packages)
        if result.returncode != 0:
            sys.exit(result.returncode)

    results = validate_packages(packages, is_stable_release=is_stable_release)

    # Persist results for the dispatch step.
    runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
    Path(runner_temp, "release_validation.json").write_text(
        json.dumps({"results": results, "mode": mode, "ref": ref, "target": target, "dry_run": dry_run})
    )

    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)

    no_version = by_type.get(NO_VERSION, [])
    unreleased = by_type.get(UNRELEASED, [])
    errors = by_type.get(HAS_FRAGMENTS, [])
    validated = [r for r in results if r["dispatch"]]

    if no_version:
        print("Skipped (no version found):")
        for r in no_version:
            print(f"  - {r['package']}")

    if unreleased:
        print("Skipped (unreleased — 0.0.1 placeholder):")
        for r in unreleased:
            print(f"  - {r['package']}")

    # Packages whose type doesn't match the branch context — dispatch=False by validate_package
    if is_stable_release:
        skipped_pre_release = by_type.get(PRE_RELEASE, [])
        if skipped_pre_release:
            print("Skipped (pre-release version on stable branch):")
            for r in skipped_pre_release:
                print(f"  - {r['package']} ({r['version']})")

    if not is_stable_release:
        mismatched_stable = by_type.get(STABLE, [])
        if mismatched_stable:
            print("\nRelease validation failed — stable versions are not allowed on alpha/beta/rc branches:", file=sys.stderr)
            for r in mismatched_stable:
                print(f"  {r['package']} ({r['version']})", file=sys.stderr)
            write_summary(
                build_summary(
                    packages,
                    results,
                    mode,
                    source_repo,
                    ref,
                    target,
                    dry_run,
                    was_dispatched=False,
                    footer="> ⚠️ Validation failed — stable versions cannot be released from an alpha/beta/rc branch.",
                )
            )
            sys.exit(1)

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
                was_dispatched=False,
                footer="> ⚠️ Validation failed — run `ddev release make` to consolidate changelog fragments before releasing.",
            )
        )
        sys.exit(1)

    print(f"\nValidated {len(validated)} package(s):")
    for r in validated:
        suffix = " [pre-release]" if r["type"] == PRE_RELEASE else ""
        print(f"  - {r['package']} ({r['version']}){suffix}")


if __name__ == "__main__":
    main()
