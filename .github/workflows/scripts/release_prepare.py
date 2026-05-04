"""Prepare a release: tag packages, detect the release list, and validate readiness.

Environment variables:
  TARGET            'prod' pushes tags; 'dev' (default) creates them locally only
  DRY_RUN           When true, tags are created locally but never pushed
  SELECTED_PACKAGES JSON array of packages to tag, 'all', or empty to tag all
  SOURCE_REPO       Source repository name (integrations-core, integrations-extras, marketplace)
  REF               Commit SHA or ref to build from
  IS_STABLE_RELEASE 'false' for alpha/beta/rc branches; anything else (default) → stable behavior
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _release.github import parse_bool_env, set_outputs, write_summary
from _release.packages import get_all_packages, resolve_packages
from _release.summary import build_summary
from _release.validation import HAS_FRAGMENTS, NO_VERSION, PRE_RELEASE, STABLE, UNRELEASED, validate_packages


def _tag_package_args(selected: str) -> list[str]:
    """Return the package arguments for ``ddev release tag``."""
    selected = selected.strip()
    if not selected:
        return ["all"]
    try:
        packages = json.loads(selected)
    except json.JSONDecodeError as e:
        print(f"SELECTED_PACKAGES is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    return packages if packages else ["all"]


def _parse_is_stable_release() -> bool:
    """Parse IS_STABLE_RELEASE: 'false' → False, anything else (including unset) → True (stable)."""
    return os.environ.get("IS_STABLE_RELEASE", "true").strip().lower() != "false"


def _tag(dry_run: bool, selected: str) -> None:
    """Tag packages via ddev and optionally push to origin."""
    if dry_run:
        print("DRY RUN: tags will be created locally but not pushed to origin")

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    push_flag = "--push" if not dry_run else "--no-push"
    base_cmd = ["ddev", "release", "tag"] + _tag_package_args(selected) + ["--skip-prerelease", push_flag]

    result = subprocess.run(base_cmd)
    if result.returncode == 3:
        # ddev release tag exits 3 when the remote fetch fails (e.g. tags already cached locally).
        # Retry with --no-fetch to use the local tag state.
        result = subprocess.run(base_cmd + ["--no-fetch"])

    # exit 2 means nothing new to tag — not an error, tags may already exist on HEAD
    if result.returncode not in (0, 2):
        print(f"ddev release tag failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def _detect(selected: str) -> tuple[list[str], str]:
    """Resolve the list of packages to release."""
    all_packages = get_all_packages()
    try:
        packages, mode = resolve_packages(selected, all_packages)
    except (ValueError, RuntimeError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(f"Mode: {mode}")

    if packages:
        print(f"\nDetected {len(packages)} package(s) to release:")
        for name in packages:
            print(f"  - {name}")
    else:
        print("No packages detected — nothing to release")

    return packages, mode


def _validate(
    packages: list[str],
    mode: str,
    source_repo: str,
    ref: str,
    dry_run: bool,
    is_stable_release: bool,
) -> None:
    """Validate that packages are ready to release."""
    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + packages)
        if result.returncode != 0:
            sys.exit(result.returncode)

    results = validate_packages(packages, is_stable_release=is_stable_release)

    # Persist results for the dispatch step.
    runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
    Path(runner_temp, "release_validation.json").write_text(
        json.dumps({"results": results, "mode": mode, "ref": ref})
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
        write_summary(
            build_summary(
                packages,
                results,
                mode,
                source_repo,
                ref,
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


def main() -> None:
    dry_run = parse_bool_env("DRY_RUN", default=False)
    selected = os.environ.get("SELECTED_PACKAGES", "")
    source_repo = os.environ.get("SOURCE_REPO", "integrations-core")
    ref = os.environ.get("REF", "")
    is_stable_release = _parse_is_stable_release()

    _tag(dry_run, selected)

    packages, mode = _detect(selected)

    set_outputs(
        packages=json.dumps(packages),
        has_packages="true" if packages else "false",
        mode=mode,
    )

    if not packages:
        write_summary("## Wheel Release\n\nNo packages detected — nothing to release.\n")
        return

    _validate(packages, mode, source_repo, ref, dry_run, is_stable_release)


if __name__ == "__main__":
    main()
