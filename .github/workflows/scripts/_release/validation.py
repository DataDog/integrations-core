"""Release readiness validation logic."""
import re
from pathlib import Path

_PRE_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+(a|b|rc)\d+")
# Changelog fragment files are named <PR_NUMBER>.<type> (e.g. "1234.fixed").
# This pattern intentionally excludes .gitkeep, README.md, and other non-fragment files.
_FRAGMENT_RE = re.compile(r"^\d+\.[a-z]+$")

NO_VERSION = "no_version"
PRE_RELEASE = "pre_release"
HAS_FRAGMENTS = "error"
READY = "ready"


def get_version(package: str, root: Path = Path(".")) -> str | None:
    """Return the ``__version__`` string from the package's ``__about__.py``, or None."""
    about = next((root / package).glob("datadog_checks/*/__about__.py"), None)
    if about is None:
        return None
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', about.read_text())
    return match.group(1) if match else None


def is_pre_release(version: str) -> bool:
    """Return True if *version* contains a pre-release marker (a/b/rc)."""
    return bool(_PRE_RELEASE_RE.search(version))


def has_changelog_fragments(package: str, root: Path = Path(".")) -> bool:
    """Return True if ``changelog.d/`` contains unreleased fragment files.

    Only files matching ``<digits>.<word>`` are counted as fragments, so
    housekeeping files like ``.gitkeep`` or ``README.md`` are ignored.
    """
    changelog_dir = root / package / "changelog.d"
    if not changelog_dir.is_dir():
        return False
    return any(_FRAGMENT_RE.match(f.name) for f in changelog_dir.iterdir())


def validate_package(package: str, root: Path = Path(".")) -> dict:
    """Validate a single package and return a status dict."""
    version = get_version(package, root)
    if version is None:
        return {"package": package, "version": None, "status": NO_VERSION}
    if is_pre_release(version):
        return {"package": package, "version": version, "status": PRE_RELEASE}
    if has_changelog_fragments(package, root):
        return {"package": package, "version": version, "status": HAS_FRAGMENTS}
    return {"package": package, "version": version, "status": READY}


def validate_packages(packages: list[str], root: Path = Path(".")) -> list[dict]:
    """Validate all packages and return a list of status dicts."""
    return [validate_package(p, root) for p in packages]
