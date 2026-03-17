"""Package detection and resolution logic."""
import json
import re
import subprocess
import sys
from pathlib import Path

_VERSION_SUFFIX_RE = re.compile(r"-\d+\.\d+\.\d+.*$")


def get_all_packages(root: Path = Path(".")) -> list[str]:
    """Return sorted list of all Python packages found under *root*."""
    return sorted(
        {p.parent.parent.parent.name for p in root.glob("*/datadog_checks/*/__about__.py")}
    )


def get_tags_at_head() -> list[str]:
    """Return the list of git tags pointing at HEAD."""
    return subprocess.check_output(["git", "tag", "--points-at", "HEAD"], text=True).splitlines()


def detect_from_tags(tags: list[str]) -> list[str]:
    """Return sorted unique package names extracted from release tags.

    Tags are expected in the form ``<package>-X.Y.Z[...]``.
    The version suffix is stripped to recover the package name.
    """
    return sorted({_VERSION_SUFFIX_RE.sub("", t) for t in tags if t.strip()})


def resolve_packages(
    selected: str,
    all_packages: list[str],
    head_tags: list[str] | None = None,
) -> tuple[list[str], str]:
    """Resolve the list of packages to release.

    Resolution order:
    - ``'all'`` / ``'ALL'`` → every package in the repo
    - JSON array            → use the provided list verbatim
    - empty string          → auto-detect from git tags at HEAD

    Returns ``(packages, mode_description)``.
    Calls ``sys.exit(1)`` on invalid input or unknown package names.
    """
    selected = selected.strip()

    if selected.lower() == "all":
        return all_packages, f"all ({len(all_packages)} packages in repo)"

    if selected:
        try:
            packages = json.loads(selected)
        except json.JSONDecodeError as e:
            print(f"selected_PACKAGES is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        mode = f"manual ({selected})"
    else:
        tags = head_tags if head_tags is not None else get_tags_at_head()
        packages = detect_from_tags(tags)
        mode = "auto-detect from tags at HEAD"

    unknown = sorted(set(packages) - set(all_packages))
    if unknown:
        print(f"Unknown packages: {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    return packages, mode
