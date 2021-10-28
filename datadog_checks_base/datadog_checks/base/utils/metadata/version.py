# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from ..common import exclude_undefined_keys

# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_PATTERN = re.compile(
    r"""
    v?
    (?P<major>0|[1-9]\d*)
    \.
    (?P<minor>0|[1-9]\d*)
    \.
    (?P<patch>0|[1-9]\d*)
    (?:-(?P<release>
        (?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
        (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*
    ))?
    (?:\+(?P<build>
        [0-9a-zA-Z-]+
        (?:\.[0-9a-zA-Z-]+)*
    ))?
    """,
    re.VERBOSE,
)


def parse_semver(version, options):
    match = SEMVER_PATTERN.search(version)
    if not match:
        raise ValueError('Version does not adhere to semantic versioning')

    return exclude_undefined_keys(match.groupdict())


def parse_regex(version, options):
    pattern = options.get('pattern')
    if not pattern:
        raise ValueError('Version scheme `regex` requires a `pattern` option')

    match = re.search(pattern, version)
    if not match:
        raise ValueError('Version does not match the regular expression pattern')

    parts = match.groupdict()
    if not parts:
        raise ValueError('Regular expression pattern has no named subgroups')

    return exclude_undefined_keys(parts)


def parse_raw(version, options):
    part_map = options.get('part_map')
    if not part_map:
        raise ValueError('Version scheme `parts` requires a `part_map` option')

    return exclude_undefined_keys(part_map)


def parse_version(version, options):
    scheme = options.get('scheme')

    if not scheme:
        scheme = 'semver'
    elif scheme not in SCHEMES:
        raise ValueError('Unsupported version scheme `{}`'.format(scheme))

    return scheme, SCHEMES[scheme](version, options)


SCHEMES = {'semver': parse_semver, 'regex': parse_regex, 'parts': parse_raw}
