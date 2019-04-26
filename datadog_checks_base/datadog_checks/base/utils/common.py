# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from decimal import ROUND_HALF_UP, Decimal

from six import PY3
from six.moves.urllib.parse import urlparse


def ensure_bytes(s):
    if not isinstance(s, bytes):
        s = s.encode('utf-8')
    return s


def ensure_unicode(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


to_string = ensure_unicode if PY3 else ensure_bytes


def round_value(value, precision=0, rounding_method=ROUND_HALF_UP):
    precision = '0.{}'.format('0' * precision)
    return float(Decimal(str(value)).quantize(Decimal(precision), rounding=rounding_method))


def get_docker_hostname():
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def pattern_filter(items, whitelist=None, blacklist=None, key=None):
    """This filters `items` by a regular expression `whitelist` and/or
    `blacklist`, with the `blacklist` taking precedence. An optional `key`
    function can be provided that will be passed each item.
    """
    key = key or __return_self
    if whitelist:
        whitelisted = _filter(items, whitelist, key)

        if blacklist:
            blacklisted = _filter(items, blacklist, key)
            # Remove any blacklisted items from the whitelisted ones.
            whitelisted.difference_update(blacklisted)

        return [item for item in items if key(item) in whitelisted]

    elif blacklist:
        blacklisted = _filter(items, blacklist, key)
        return [item for item in items if key(item) not in blacklisted]

    else:
        return items


def _filter(items, pattern_list, key):
    return {key(item) for pattern in pattern_list for item in items if re.search(pattern, key(item))}


def __return_self(obj):
    return obj
