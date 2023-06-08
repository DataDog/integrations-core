# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pathlib
import re
from collections import namedtuple
from typing import Callable, Iterable, List, Optional

from pathspec.gitignore import GitIgnoreSpec

from ..errors import SubprocessError
from .constants import get_root
from .git import git_show_file
from .utils import get_license_header as get_default_license_header

_COPYRIGHT_PATTERN = re.compile(
    r"""
    ^(?:\#\ \(C\)\s*.*?\s*)+\n      # Copyright holders
    \#\ All\ rights\ reserved\s*\n
    \#\ .*?(?i:license).*?$    # License info (matching string `license` while ignoring case)
    """,
    re.MULTILINE | re.VERBOSE,
)

LicenseHeaderError = namedtuple("LicenseHeaderError", ["message", "path", "fixed"])


def _get_previous(path):
    """Returns contents of previous (origin/master) version of file at `path` if it exists, and `None` otherwise."""
    # git_show_file relies on global context to compute the final path from a relative one,
    # so we need to pass it the relative path it expects
    relpath = path.relative_to(get_root())
    try:
        return git_show_file(str(relpath), "origin/master")
    except SubprocessError:
        return None


def validate_license_headers(
    check_path: pathlib.Path,
    ignore: Optional[Iterable[pathlib.Path]] = None,
    *,
    repo_root: Optional[pathlib.Path] = None,
    get_previous: Callable[[pathlib.Path], Optional[str]] = _get_previous,
) -> List[LicenseHeaderError]:
    """
    Validate license headers under `check_path` and return a list of validation errors.

    Paths on `ignore` will be ignored, as well as their subpaths.

    Assumptions regarding which files require license header validation:
    - Only python (*.py) files need a license header
    - Code under hidden folders (starting with `.`) are ignored
    """
    ignoreset = set(ignore or [])

    def walk_recursively(path, gitignore_matcher):

        for child in path.iterdir():
            # Skip gitignored files
            if gitignore_matcher.match(child):
                return

            # For directories, keep recursing unless folder is blacklisted
            if child.is_dir():
                # Skip hidden folders
                if child.relative_to(child.parent).as_posix().startswith('.'):
                    continue

                relpath = child.relative_to(check_path)
                # Skip blacklisted folders
                if relpath in ignoreset:
                    continue

                yield from walk_recursively(child, gitignore_matcher.for_path(path))
                continue

            # Skip non-python files
            if child.suffix == '.py':
                yield child

    def validate_license_header(path):
        with open(path, encoding='utf-8-sig') as f:
            contents = f.read()

        license_header = parse_license_header(contents)
        relpath = path.relative_to(check_path).as_posix()
        previous = get_previous(path)

        # When file already existed
        if previous is not None:
            original_header = parse_license_header(previous)
            # Check whether the license has changed
            if original_header and license_header != original_header:
                return LicenseHeaderError(
                    "existing file has changed license", relpath, _replace_header(contents, original_header)
                )
            # If the original file didn't have a header and the current one doesn't either
            # we report as missing, but we can't suggest an automatic fix.
            elif not original_header and not license_header:
                return LicenseHeaderError("missing license header", relpath, None)

        # License is missing altogether
        elif not license_header:
            return LicenseHeaderError("missing license header", relpath, f"{get_default_license_header()}\n{contents}")

        # When it's a new file and a license header is found, compare it to the current header template
        elif license_header != get_default_license_header():
            return LicenseHeaderError(
                "file does not match expected license format",
                relpath,
                _replace_header(contents, get_default_license_header()),
            )

    if repo_root:
        gitignore_matcher = _GitIgnoreMatcher.from_path_to_root(check_path, repo_root)
    else:
        gitignore_matcher = _GitIgnoreMatcher(check_path)

    # Walk through subdirs and validate files
    errors = []
    for candidate in walk_recursively(check_path, gitignore_matcher):
        if error := validate_license_header(candidate):
            errors.append(error)

    return errors


def parse_license_header(contents):
    """
    Return the license header at the top of the `contents` string.

    It returns an empty string if no license header is found.
    """
    match = _COPYRIGHT_PATTERN.match(contents)
    return match[0] if match else ""


def _replace_header(contents, new_header):
    return _COPYRIGHT_PATTERN.sub(new_header, contents)


class _GitIgnoreMatcher:
    """A class to find gitignore matches recursively. Each instance represents
    a folder in a directory structure with possibly a `.gitignore` file in it.

    Instances get linked to other instances representing their parent folder,
    so that parents' .gitignore files are taken into account if necessary
    to determine a match.

    This implementation doesn't support overriding (via the negation `!` operator) of
    ignored patterns defined in parents.
    """

    def __init__(self, path, parent=None):
        self._parent = parent
        self._path = path
        self._matcher = _gitignore_spec_from_file(path / '.gitignore')

    @classmethod
    def from_path_to_root(cls, path, repo_root):
        """Create a matcher with parents linked up to the provided `repo_root`"""
        # Create all the intermediate instances between the `repo_root` and the `path`
        # and link them together.
        parents = list(reversed(path.relative_to(repo_root).parents))
        instance = cls(repo_root)
        for parent in parents[1:]:
            instance = instance.for_path(repo_root / parent)

        return instance.for_path(path)

    def for_path(self, path):
        """Returns a new matcher that takes the current matcher as a parent."""
        return self.__class__(path, self)

    def match(self, path):
        """Return whether the given path is matched, checking top to bottom."""
        # Each .gitignore must match relative patterns based on the folder it's in
        path_to_match = path.relative_to(self._path).as_posix()

        if self._matcher and self._matcher.match_file(path_to_match):
            return True
        elif self._parent:
            return self._parent.match(path)
        else:
            return False


def _gitignore_spec_from_file(path):
    try:
        with open(path) as f:
            return GitIgnoreSpec.from_lines(f)
    except FileNotFoundError:
        return None
