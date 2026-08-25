"""Release readiness validation logic."""
import re
from pathlib import Path
from typing import TypedDict

_PRE_RELEASE_RE = re.compile(r"\d+\.\d+\.\d+(a|b|rc)\d+")
# Changelog fragment files are named <PR_NUMBER>.<type> (e.g. "1234.fixed").
# This pattern intentionally excludes .gitkeep, README.md, and other non-fragment files.
_FRAGMENT_RE = re.compile(r"^\d+\.[a-z]+$")

class PackageValidationResult(TypedDict):
    package: str
    version: str | None
    type: str
    dispatch: bool


NO_VERSION = "no_version"
UNRELEASED = "unreleased"
PRE_RELEASE = "pre_release"
HAS_FRAGMENTS = "has_fragments"
STABLE = "stable"


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


def validate_package(package: str, root: Path = Path("."), is_stable_release: bool = True) -> PackageValidationResult:
    """Validate a single package and return a result dict with ``type`` and ``dispatch`` keys.

    ``is_stable_release`` encodes the git ref context:
    - ``True``  (master/X.X.x/...): pre-release versions are not dispatched.
    - ``False`` (alpha/beta/rc):    stable versions are not dispatched.
    """
    version = get_version(package, root)
    if version is None:
        return {"package": package, "version": None, "type": NO_VERSION, "dispatch": False}
    if version == "0.0.1":
        return {"package": package, "version": version, "type": UNRELEASED, "dispatch": False}
    if is_pre_release(version):
        # PEP 440 pre-release (alpha/beta/rc) — skip fragment check, dispatch unless on a stable branch
        return {"package": package, "version": version, "type": PRE_RELEASE, "dispatch": not is_stable_release}
    if has_changelog_fragments(package, root):
        return {"package": package, "version": version, "type": HAS_FRAGMENTS, "dispatch": False}
    return {"package": package, "version": version, "type": STABLE, "dispatch": is_stable_release}


def validate_packages(packages: list[str], root: Path = Path("."), is_stable_release: bool = True) -> list[PackageValidationResult]:
    """Validate all packages and return a list of result dicts."""
    return [validate_package(p, root, is_stable_release) for p in packages]
