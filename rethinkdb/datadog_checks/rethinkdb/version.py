# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

# See: https://github.com/rethinkdb/rethinkdb/blob/95cfed8a62f08e3198ac25417c9b6900be8b6877/src/utils.hpp#L117
_RETHINKDB_VERSION_STR_REGEX = re.compile(r'^rethinkdb\s+(?P<rethinkdb_version>[\d\.]+)')


def parse_version(rethinkdb_version_string):
    # type: (str) -> str
    """
    Given a RethinkDB version string, extract the SemVer version.

    Example
    -------
    >>> parse_version('rethinkdb 2.4.0~0bionic (CLANG 6.0.0 (tags/RELEASE_600/final))')
    '2.4.0'
    """
    match = _RETHINKDB_VERSION_STR_REGEX.match(rethinkdb_version_string)

    if match is None:
        message = 'Version string {!r} did not match pattern {!r}'.format(
            rethinkdb_version_string, _RETHINKDB_VERSION_STR_REGEX
        )
        raise ValueError(message)

    return match.group('rethinkdb_version')
