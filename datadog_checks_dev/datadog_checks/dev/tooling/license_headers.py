# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re


_COPYRIGHT_PATTERN = re.compile(
    r"""
    ^(?:\#\ \(C\)\s*.*?\s*)+\n      # Copyright holders
    \#\ All\ rights\ reserved\s*\n
    \#\ .*?(?i:license).*?$    # License info (matching string `license` while ignoring case)
    """,
    re.MULTILINE | re.VERBOSE
)


def parse_license_header(contents):
    """
    Return the license header at the top of the `contents` string.

    It returns an empty string if no license header is found.
    """
    match = _COPYRIGHT_PATTERN.match(contents)
    return match[0] if match else ""
