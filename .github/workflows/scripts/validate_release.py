"""Validate that packages are ready to release.

Runs ``ddev validate version`` (integrations-core only), then checks that
changelog.d/ is empty for every non-pre-release package.

Environment variables: PACKAGES, SOURCE_REPO, REF, TARGET, DRY_RUN, MODE.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_PRE_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+(a|b|rc)\d+")
_STATUS_LABELS = {
    "no_version": "⚠️ No version found",
    "pre_release": "⏭️ Pre-release, skipped",
    "error": "❌ Unreleased changelog fragments",
    "ready": "✅ Ready",
}


def write_summary(content: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(content + "\n")


def get_version(package: str) -> str | None:
    about = next(Path(package).glob("datadog_checks/*/__about__.py"), None)
    if about is None:
        return None
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', about.read_text())
    return match.group(1) if match else None


def has_changelog_fragments(package: str) -> bool:
    changelog_dir = Path(package) / "changelog.d"
    if not changelog_dir.is_dir():
        return False
    return any(changelog_dir.iterdir())


def build_summary(
    results: list[dict],
    mode: str,
    source_repo: str,
    ref: str,
    target: str,
    dry_run: bool,
    footer: str = "",
) -> str:
    source_link = (
        f"[`{source_repo}@{ref[:12]}`](https://github.com/DataDog/{source_repo}/commit/{ref})"
        if ref
        else source_repo
    )
    rows = [
        f"| `{r['package']}` | `{r.get('version') or '—'}` | {_STATUS_LABELS.get(r['status'], '✅ Ready')} |"
        for r in results
    ]

    return (
        "## Wheel Release\n\n"
        "| | |\n|---|---|\n"
        f"| **Mode** | {mode} |\n"
        f"| **Source** | {source_link} |\n"
        f"| **Target** | {target} S3 |\n"
        f"| **Dry run** | {'Yes' if dry_run else 'No'} |\n\n"
        "| Package | Version | Status |\n"
        "|---------|---------|--------|\n"
        + "\n".join(rows)
        + ("\n\n" + footer if footer else "")
        + "\n"
    )


def main() -> None:
    packages = json.loads(os.environ["PACKAGES"])
    source_repo = os.environ["SOURCE_REPO"]
    ref = os.environ.get("REF", "")
    target = os.environ.get("TARGET", "")
    dry_run = os.environ.get("DRY_RUN", "").lower() != "false"
    mode = os.environ.get("MODE", "")

    if source_repo == "integrations-core":
        result = subprocess.run(["ddev", "validate", "version"] + packages)
        if result.returncode != 0:
            sys.exit(result.returncode)

    results = []
    for package in packages:
        raw = get_version(package)
        if raw is None:
            results.append({"package": package, "version": None, "status": "no_version"})
            continue
        if _PRE_RELEASE_RE.search(raw):
            results.append({"package": package, "version": raw, "status": "pre_release"})
            continue
        if has_changelog_fragments(package):
            results.append({"package": package, "version": raw, "status": "error"})
        else:
            results.append({"package": package, "version": raw, "status": "ready"})

    # Save results for the dispatch step to build the comprehensive summary.
    runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
    Path(runner_temp, "release_validation.json").write_text(
        json.dumps({"results": results, "mode": mode, "ref": ref, "target": target, "dry_run": dry_run})
    )

    by_status: dict[str, list] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)
    no_version = by_status.get("no_version", [])
    pre_release = by_status.get("pre_release", [])
    errors = by_status.get("error", [])
    validated = by_status.get("ready", [])

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
            print(f"  {r['package']} ({r['version']}): changelog.d/ contains unreleased fragments", file=sys.stderr)
        print(
            "\nRun 'ddev release make' to consolidate changelog fragments before releasing.",
            file=sys.stderr,
        )
        # Dispatch won't run — write the comprehensive summary here so the failure is visible.
        write_summary(
            build_summary(
                results,
                mode,
                source_repo,
                ref,
                target,
                dry_run,
                footer="> ⚠️ Validation failed — run `ddev release make` to consolidate changelog fragments before releasing.",
            )
        )
        sys.exit(1)

    print(f"\nValidated {len(validated)} package(s):")
    for r in validated:
        print(f"  - {r['package']} ({r['version']})")


if __name__ == "__main__":
    main()
