"""Markdown summary builder for the wheel release pipeline."""
from . import validation as v

_STATUS_LABELS: dict[str, str] = {
    v.NO_VERSION: "⚠️ No version found",
    v.PRE_RELEASE: "⏭️ Pre-release, skipped",
    v.HAS_FRAGMENTS: "❌ Unreleased changelog fragments",
    v.READY: "✅ Ready",
}

_ACTIONS_URL = "https://github.com/DataDog/agent-integration-wheels-release/actions"


def _source_link(source_repo: str, ref: str) -> str:
    if ref:
        return f"[`{source_repo}@{ref[:12]}`](https://github.com/DataDog/{source_repo}/commit/{ref})"
    return source_repo


def build_summary(
    packages: list[str],
    results: list[dict],
    mode: str,
    source_repo: str,
    ref: str,
    target: str,
    dry_run: bool,
    dispatched: bool,
    footer: str = "",
) -> str:
    """Return the full Markdown summary for GITHUB_STEP_SUMMARY.

    Args:
        packages:   Ordered list of package names to include in the table.
        results:    Validation result dicts (``{"package", "version", "status"}``).
        mode:       Human-readable detection mode string.
        source_repo: Repository name (e.g. ``integrations-core``).
        ref:        Commit SHA or ref used as the build source.
        target:     Deployment target (``dev`` or ``prod``).
        dry_run:    Whether this was a dry run.
        dispatched: Whether wheel-build events were actually dispatched.
        footer:     Optional extra paragraph appended after the package table.
    """
    by_package = {r["package"]: r for r in results}

    rows = []
    for name in packages:
        r = by_package.get(name, {})
        ver = r.get("version") or "—"
        status = r.get("status", v.READY)
        if dry_run and status == v.READY:
            label = "🔄 Dry run"
        elif dispatched and status == v.READY:
            label = "✅ Dispatched"
        else:
            label = _STATUS_LABELS.get(status, "✅ Ready")
        rows.append(f"| `{name}` | `{ver}` | {label} |")

    if not footer:
        if dispatched:
            footer = f"[Track downstream runs →]({_ACTIONS_URL}?query=event:repository_dispatch)"
        elif dry_run:
            footer = "> Dry run — no tags pushed, no builds triggered"

    return (
        "## Wheel Release\n\n"
        "| | |\n|---|---|\n"
        f"| **Mode** | {mode} |\n"
        f"| **Source** | {_source_link(source_repo, ref)} |\n"
        f"| **Target** | {target} S3 |\n"
        f"| **Dry run** | {'Yes' if dry_run else 'No'} |\n\n"
        "| Package | Version | Status |\n"
        "|---------|---------|--------|\n"
        + "\n".join(rows)
        + (f"\n\n{footer}" if footer else "")
        + "\n"
    )
