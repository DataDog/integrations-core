"""Package detection and resolution logic."""
import json
import re
import subprocess
from pathlib import Path

_VERSION_SUFFIX_RE = re.compile(r"-\d+\.\d+\.\d+.*$")


def get_all_packages(root: Path = Path(".")) -> list[str]:
    """Return sorted list of all Python packages found under *root*."""
    return sorted(
        {p.parent.parent.parent.name for p in root.glob("*/datadog_checks/*/__about__.py")}
    )


def get_tags_at_head() -> list[str]:
    """Return the list of git tags pointing at HEAD."""
    try:
        return subprocess.check_output(["git", "tag", "--points-at", "HEAD"], text=True).splitlines()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get git tags at HEAD: {e}") from e


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
    """Resolve packages to release from a JSON list, or from tags at HEAD when empty.

    A JSON list errors on unknown names; tag detection ignores tags with no matching package.
    """
    selected = selected.strip()
    known = set(all_packages)

    if selected:
        try:
            packages = json.loads(selected)
        except json.JSONDecodeError as e:
            raise ValueError(f"SELECTED_PACKAGES is not valid JSON: {e}") from e
        unknown = sorted(set(packages) - known)
        if unknown:
            raise ValueError(f"Unknown packages: {', '.join(unknown)}")
        return packages, f"manual ({selected})"

    tags = head_tags if head_tags is not None else get_tags_at_head()
    detected = detect_from_tags(tags)
    packages = [name for name in detected if name in known]
    ignored = sorted(set(detected) - known)
    if ignored:
        print(f"Ignoring tag(s) at HEAD with no matching package: {', '.join(ignored)}")

    return packages, "auto-detect from tags at HEAD"
