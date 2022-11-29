# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pathlib
import re
from collections import namedtuple
from typing import Callable, List, Optional

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
    check_path: pathlib.Path, *, get_previous: Callable[[pathlib.Path], Optional[str]] = _get_previous
) -> List[LicenseHeaderError]:
    """
    Validate license headers under `check_path` and return a list of validation errors.

    Assumptions regarding which files require license header validation:
    - Only python (*.py) files need a license header
    - Code under hidden folders (starting with `.`) are ignored
    - Files under the following folders are not checked, as it's where integration
      testing environments are typically defined, where licenses may be a bit more heterogeneous:
      - tests/docker
      - tests/compose
    """
    root = check_path

    def walk_recursively(path):
        for child in path.iterdir():
            # For directories, keep recursing unless folder is blacklisted
            if child.is_dir():
                # Skip hidden folders
                if child.relative_to(child.parent).as_posix().startswith('.'):
                    continue

                # Skip blacklisted folders
                relpath = child.relative_to(root)
                if relpath.as_posix() in ("tests/docker", "tests/compose"):
                    continue

                yield from walk_recursively(child)
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
            return LicenseHeaderError("missing", relpath)

        # When file already existed, check whether the license has changed
        previous = get_previous(path)
        if previous:
            if license_header != parse_license_header(previous):
                return LicenseHeaderError("existing file has changed license", relpath)
        # When it's a new file, compare it to the current header template
        elif license_header != get_default_license_header():
            return LicenseHeaderError("new file does not match template", relpath)

    errors = []
    for candidate in walk_recursively(root):
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
