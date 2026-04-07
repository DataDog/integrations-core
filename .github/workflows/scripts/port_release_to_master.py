#!/usr/bin/env python3
"""Port release changes from a release branch to master.

Semantically merges release artifacts (changelogs, version bumps, requirement
pins) so that version-conflict scenarios are handled correctly — e.g. when
master already has 1.1.0 and the release branch ships 1.0.1.

Exit codes:
    0 — changes ported successfully
    1 — fatal error
    2 — nothing to port (all changes were .in-toto files or empty diff)
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("port-release")


VERSION_RE = re.compile(r"__version__\s*=\s*(['\"])(.+?)\1")
CHANGELOG_HEADING_RE = re.compile(r"^## (\d+\.\d+\.\d+)\s+/")
TOWNCRIER_MARKER = "<!-- towncrier release notes start -->"


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a dotted version string into a comparable tuple."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError as exc:
        raise ValueError(f"Cannot parse version: {version!r}") from exc


def version_gt(a: str, b: str) -> bool:
    """Return True if version *a* is strictly greater than *b*."""
    return parse_version(a) > parse_version(b)


def get_changed_files(merge_sha: str) -> list[str]:
    """Return the list of files changed by *merge_sha* relative to its first parent."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_sha}^1", merge_sha],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def read_file_at_commit(merge_sha: str, path: str) -> str | None:
    """Read the contents of *path* as it exists at *merge_sha*.

    Returns ``None`` when the file does not exist in the commit.
    """
    result = subprocess.run(
        ["git", "show", f"{merge_sha}:{path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def categorize_changes(
    changed_files: list[str],
) -> tuple[dict[str, dict[str, list[str]]], bool]:
    """Group *changed_files* by integration and file type.

    Returns ``(integrations, has_requirements)`` where *integrations* maps
    integration names to dicts of ``{"changelogs": [...], "abouts": [...],
    "fragments": [...]}``, and *has_requirements* is ``True`` when
    ``requirements-agent-release.txt`` was changed.
    """
    integrations: dict[str, dict[str, list[str]]] = {}
    has_requirements = False

    for path in changed_files:
        # Skip .in-toto files
        if path.startswith(".in-toto") or "/.in-toto" in path:
            continue

        parts = path.split("/")

        if path == "requirements-agent-release.txt":
            has_requirements = True
            continue

        if len(parts) < 2:
            continue

        integration = parts[0]
        bucket = integrations.setdefault(integration, {"changelogs": [], "abouts": [], "fragments": []})

        if parts[-1] == "CHANGELOG.md":
            bucket["changelogs"].append(path)
        elif parts[-1] == "__about__.py":
            bucket["abouts"].append(path)
        elif "changelog.d" in parts:
            bucket["fragments"].append(path)

    return integrations, has_requirements


def extract_version_block(content: str, version: str) -> str | None:
    """Extract the full block for *version* from a CHANGELOG.md body.

    The block spans from the ``## <version> /`` heading up to (but not
    including) the next ``## `` heading, preserving one trailing blank line.
    """
    lines = content.splitlines(keepends=True)
    start: int | None = None
    end: int | None = None
    prefix = f"## {version} /"

    for i, line in enumerate(lines):
        if line.startswith(prefix):
            start = i
        elif start is not None and line.startswith("## "):
            end = i
            break

    if start is None:
        return None

    block_lines = lines[start:end]  # end=None → rest of file

    # Strip trailing whitespace-only lines, then ensure one trailing newline
    while block_lines and not block_lines[-1].strip():
        block_lines.pop()

    return "".join(block_lines).rstrip("\n") + "\n"


def process_changelog(integration: str, merge_sha: str) -> bool:
    """Insert the new version entry from the merge commit into master's changelog.

    Returns ``True`` if the file was modified.
    """
    changelog_path = Path(integration, "CHANGELOG.md")

    # Read the release-branch version of the changelog
    release_content = read_file_at_commit(merge_sha, str(changelog_path))
    if release_content is None:
        log.warning("%s: CHANGELOG.md not found in merge commit", integration)
        return False

    # Identify the newest version introduced by the release
    match = CHANGELOG_HEADING_RE.search(release_content)
    if not match:
        log.warning("%s: no version heading found in release CHANGELOG.md", integration)
        return False
    release_version = match.group(1)

    # Read master's changelog
    if not changelog_path.exists():
        log.warning("%s: CHANGELOG.md not found on master", integration)
        return False

    master_content = changelog_path.read_text()

    # Duplicate check
    if re.search(rf"^## {re.escape(release_version)}\s+/", master_content, re.MULTILINE):
        log.info(
            "%s: version %s already in master changelog — skipping",
            integration,
            release_version,
        )
        return False

    # Extract the version block from the release changelog
    block = extract_version_block(release_content, release_version)
    if block is None:
        log.warning("%s: could not extract block for %s", integration, release_version)
        return False

    # Find insertion point in master's changelog
    master_lines = master_content.splitlines(keepends=True)
    release_tuple = parse_version(release_version)
    insertion_idx: int | None = None

    for i, line in enumerate(master_lines):
        m = CHANGELOG_HEADING_RE.match(line)
        if m:
            existing_tuple = parse_version(m.group(1))
            if existing_tuple < release_tuple:
                insertion_idx = i
                break

    if insertion_idx is None:
        # No older version found — look for the towncrier marker
        for i, line in enumerate(master_lines):
            if TOWNCRIER_MARKER in line:
                insertion_idx = i + 1
                break

    if insertion_idx is None:
        log.warning("%s: could not find insertion point in master CHANGELOG.md", integration)
        return False

    # Insert with a blank line separator
    block_with_separator = "\n" + block + "\n"
    master_lines.insert(insertion_idx, block_with_separator)

    changelog_path.write_text("".join(master_lines))
    log.info("%s: inserted changelog entry for %s", integration, release_version)
    return True


def extract_about_version(content: str) -> tuple[str, str] | None:
    """Return ``(version, quote_char)`` from an ``__about__.py`` body."""
    m = VERSION_RE.search(content)
    if m is None:
        return None
    return m.group(2), m.group(1)


def process_about(integration: str, about_paths: list[str], merge_sha: str) -> bool:
    """Update ``__about__.py`` only when the release version is greater.

    Returns ``True`` if the file was modified.
    """
    for about_path in about_paths:
        release_content = read_file_at_commit(merge_sha, about_path)
        if release_content is None:
            continue

        release_info = extract_about_version(release_content)
        if release_info is None:
            log.warning("%s: cannot parse version from release __about__.py", integration)
            continue

        release_version, _ = release_info

        local_path = Path(about_path)
        if not local_path.exists():
            log.warning("%s: __about__.py not found on master at %s", integration, about_path)
            continue

        master_content = local_path.read_text()
        master_info = extract_about_version(master_content)
        if master_info is None:
            log.warning("%s: cannot parse version from master __about__.py", integration)
            continue

        master_version, master_quote = master_info

        if not version_gt(release_version, master_version):
            log.info(
                "%s: master %s >= release %s — skipping __about__.py",
                integration,
                master_version,
                release_version,
            )
            continue

        # Replace in master, preserving quote style
        updated = VERSION_RE.sub(
            rf"__version__ = {master_quote}{release_version}{master_quote}",
            master_content,
        )
        local_path.write_text(updated)
        log.info(
            "%s: updated __about__.py %s → %s",
            integration,
            master_version,
            release_version,
        )
        return True

    return False


def process_fragments(integration: str, fragment_paths: list[str]) -> bool:
    """Delete changelog fragments that were consumed by the release.

    Returns ``True`` if any file was deleted.
    """
    deleted = False
    for frag in fragment_paths:
        p = Path(frag)
        if p.exists():
            p.unlink()
            log.info("%s: deleted fragment %s", integration, frag)
            deleted = True
        else:
            log.debug("%s: fragment %s already absent on master", integration, frag)
    return deleted


REQUIREMENT_RE = re.compile(r"^(datadog-[\w-]+)==([\d.]+)(.*)")


def parse_requirement_line(line: str) -> tuple[str, str, str] | None:
    """Parse a single requirements line.

    Returns ``(package, version, rest)`` where *rest* includes the leading
    ``;`` and any platform markers, or an empty string.
    """
    m = REQUIREMENT_RE.match(line.strip())
    if m is None:
        return None
    return m.group(1), m.group(2), m.group(3)


def process_requirements(merge_sha: str) -> bool:
    """Update ``requirements-agent-release.txt`` on master.

    For each package in the release version of the file:
    - if it exists on master with a lower version, update it
    - if it doesn't exist on master, insert it in sorted position

    Rebuilds the file from a merged dict to avoid index-shift bugs when
    both insertions and updates happen in the same run.

    Returns ``True`` if the file was modified.
    """
    req_path = Path("requirements-agent-release.txt")

    release_content = read_file_at_commit(merge_sha, str(req_path))
    if release_content is None:
        log.warning("requirements-agent-release.txt not found in merge commit")
        return False

    if not req_path.exists():
        log.warning("requirements-agent-release.txt not found on master")
        return False

    master_content = req_path.read_text()

    # Build lookup of release packages: {pkg: (version, rest)}
    release_packages: dict[str, tuple[str, str]] = {}
    for line in release_content.splitlines():
        parsed = parse_requirement_line(line)
        if parsed:
            pkg, ver, rest = parsed
            release_packages[pkg] = (ver, rest)

    # Build lookup of master packages: {pkg: (version, rest)}
    # Also collect header lines (comments, --no-index) separately
    master_lines = master_content.splitlines()
    header_lines: list[str] = []
    master_packages: dict[str, tuple[str, str]] = {}
    for line in master_lines:
        parsed = parse_requirement_line(line)
        if parsed:
            pkg, ver, rest = parsed
            master_packages[pkg] = (ver, rest)
        else:
            header_lines.append(line)

    # Merge: for each release package, update master only when release > master
    modified = False
    merged = dict(master_packages)

    for pkg, (release_ver, release_rest) in release_packages.items():
        if pkg in master_packages:
            master_ver, master_rest = master_packages[pkg]
            if version_gt(release_ver, master_ver):
                merged[pkg] = (release_ver, master_rest)
                log.info(
                    "requirements: updated %s %s → %s",
                    pkg,
                    master_ver,
                    release_ver,
                )
                modified = True
            else:
                log.debug(
                    "requirements: master %s %s >= release %s — skipping",
                    pkg,
                    master_ver,
                    release_ver,
                )
        else:
            merged[pkg] = (release_ver, release_rest)
            log.info("requirements: added %s==%s", pkg, release_ver)
            modified = True

    if modified:
        pkg_lines = sorted(f"{p}=={v}{r}" for p, (v, r) in merged.items())
        req_path.write_text("\n".join(header_lines + pkg_lines) + "\n")

    return modified


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(message)s",
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("merge_sha", help="Merge commit SHA from the release PR")
    args = parser.parse_args()

    merge_sha: str = args.merge_sha

    # 1. Get changed files
    try:
        changed_files = get_changed_files(merge_sha)
    except subprocess.CalledProcessError as exc:
        log.error("Failed to read merge commit %s: %s", merge_sha, exc)
        return 1

    if not changed_files:
        log.info("No files changed in merge commit")
        return 2

    # 2. Categorise
    integrations, has_requirements = categorize_changes(changed_files)

    if not integrations and not has_requirements:
        log.info("No portworthy changes (only .in-toto or unrecognised files)")
        return 2

    # 3. Process each integration
    any_change = False

    for integration, buckets in sorted(integrations.items()):
        log.info("--- %s ---", integration)

        if buckets["fragments"]:
            if process_fragments(integration, buckets["fragments"]):
                any_change = True

        if buckets["changelogs"]:
            if process_changelog(integration, merge_sha):
                any_change = True

        if buckets["abouts"]:
            if process_about(integration, buckets["abouts"], merge_sha):
                any_change = True

    # 4. Process requirements (root-level file)
    if has_requirements:
        if process_requirements(merge_sha):
            any_change = True

    if not any_change:
        log.info("All changes already present on master — nothing to port")
        return 2

    log.info("Done — changes applied to working tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
