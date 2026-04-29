"""Markdown summary builder for the wheel release pipeline."""
from typing import Any

from . import TARGET_REPO
from . import validation as v

ACTIONS_URL = f"https://github.com/{TARGET_REPO}/actions"


def _source_link(source_repo: str, ref: str) -> str:
    if ref:
        return f"[`{source_repo}@{ref[:12]}`](https://github.com/DataDog/{source_repo}/commit/{ref})"
    return source_repo


def _ineligible_label(typ: str) -> str:
    if typ == v.STABLE:
        return "❌ Stable release blocked (pre-release branch)"
    if typ == v.PRE_RELEASE:
        return "⏭️ Pre-release skipped (stable branch)"
    if typ == v.NO_VERSION:
        return "⚠️ No version found"
    if typ == v.UNRELEASED:
        return "⏭️ Placeholder version (0.0.1)"
    if typ == v.HAS_FRAGMENTS:
        return "❌ Pending changelog fragments"
    raise ValueError(f"unexpected validation type: {typ!r}")


def build_summary(
    packages: list[str],
    results: list[Any],
    mode: str,
    source_repo: str,
    ref: str,
    dry_run: bool,
    was_dispatched: bool,
    footer: str = "",
) -> str:
    """Return the full Markdown summary for GITHUB_STEP_SUMMARY.

    Args:
        packages:      Ordered list of package names to include in the table.
        results:       Validation result dicts (``{"package", "version", "type", "dispatch"}``).
        mode:          Human-readable detection mode string.
        source_repo:   Repository name (e.g. ``integrations-core``).
        ref:           Commit SHA or ref used as the build source.
        dry_run:       Whether this was a dry run.
        was_dispatched: Whether wheel-build events were actually dispatched.
        footer:        Optional extra paragraph appended after the package table.
    """
    by_package = {r["package"]: r for r in results}

    rows = []
    for name in packages:
        r = by_package.get(name, {})
        ver = r.get("version") or "—"
        typ = r.get("type", v.STABLE)
        eligible = r.get("dispatch", True)
        if eligible:
            label = "🔄 Dry run" if dry_run else ("✅ Dispatched" if was_dispatched else "✅ Validated")
        else:
            label = _ineligible_label(typ)
        rows.append(f"| `{name}` | `{ver}` | {label} |")

    if not footer:
        if was_dispatched:
            footer = f"[Track downstream runs →]({ACTIONS_URL}?query=event:repository_dispatch)"
        elif dry_run:
            footer = "> Dry run — no tags pushed, no builds triggered"

    return (
        "## Wheel Release\n\n"
        "| | |\n|---|---|\n"
        f"| **Mode** | {mode} |\n"
        f"| **Source** | {_source_link(source_repo, ref)} |\n"
        f"| **Dry run** | {'Yes' if dry_run else 'No'} |\n\n"
        "| Package | Version | Status |\n"
        "|---------|---------|--------|\n"
        + "\n".join(rows)
        + (f"\n\n{footer}" if footer else "")
        + "\n"
    )
