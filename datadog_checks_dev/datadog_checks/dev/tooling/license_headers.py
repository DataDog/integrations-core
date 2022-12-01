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

LicenseHeaderError = namedtuple("LicenseHeaderError", ["message", "path"])


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
    get_previous: Callable[[pathlib.Path], Optional[str]] = _get_previous,
) -> List[LicenseHeaderError]:
    """
    Validate license headers under `check_path` and return a list of validation errors.

    Paths on `ignore` will be ignored, as well as their subpaths.

    Assumptions regarding which files require license header validation:
    - Only python (*.py) files need a license header
    - Code under hidden folders (starting with `.`) are ignored
    """
    root = check_path
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

                relpath = child.relative_to(root)
                # Skip blacklisted folders
                if relpath in ignoreset:
                    continue

                yield from walk_recursively(child, gitignore_matcher.with_file(path))
                continue

            # Skip non-python files
            if child.suffix == '.py':
                yield child

    def validate_license_header(path):
        with open(path) as f:
            contents = f.read()

        license_header = parse_license_header(contents)
        relpath = path.relative_to(root).as_posix()

        # License is missing altogether
        if not license_header:
            return LicenseHeaderError("missing license header", relpath)

        # When file already existed, check whether the license has changed
        previous = get_previous(path)
        if previous:
            if license_header != parse_license_header(previous):
                return LicenseHeaderError("existing file has changed license", relpath)
        # When it's a new file, compare it to the current header template
        elif license_header != get_default_license_header():
            return LicenseHeaderError("file does not match expected license format", relpath)

    errors = []
    for candidate in walk_recursively(root, _GitIgnoreMatcher(root)):
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


class _GitIgnoreMatcher:
    """Class to combine multiple `GitIgnoreSpec`s"""

    def __init__(self, path, parent=None):
        self._parent = parent
        self._path = path
        self._matcher = _gitignore_spec_from_file(path / '.gitignore')

    def with_file(self, path):
        """Returns a copy with the patterns from `gitignore_path` added (with greater priority).

        If `gitignore_path` doesn't exist, it silently ignores the error and returns a copy of the original matcher.
        """
        return self.__class__(path, self)

    def match(self, relpath):
        """Return whether the given relative path is matched, checking parents if necessary."""
        path_to_match = relpath.relative_to(self._path).as_posix()
        if self._matcher and self._matcher.match_file(path_to_match):
            return True
        elif self._parent:
            return self._parent.match(relpath)
        else:
            return False


def _gitignore_spec_from_file(path):
    try:
        with open(path) as f:
            return GitIgnoreSpec.from_lines(f)
    except FileNotFoundError:
        return None
