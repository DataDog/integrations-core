# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import re
import warnings
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Text, Union

from six import PY3, iteritems, text_type
from six.moves.urllib.parse import urlparse

from .constants import MILLISECOND


def ensure_bytes(s):
    # type: (Union[Text, bytes]) -> bytes
    if isinstance(s, text_type):
        s = s.encode('utf-8')
    return s


def ensure_unicode(s):
    # type: (Union[Text, bytes]) -> Text
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s

# Note on renaming `to_string` to `to_native_string`.
# `to_string` will be deprecated at some point.
# `to_native_string` is a new feature. When used, it means the integration release won't work
# with old agent with old base package.


if TYPE_CHECKING:
    to_native_string = str
else:
    to_native_string = ensure_unicode if PY3 else ensure_bytes

# TODO: `to_string` will be deprecated with Agent 6.21/7.21
to_string = to_native_string


def compute_percent(part, total):
    if total:
        return part / total * 100

    return 0


def total_time_to_temporal_percent(total_time, scale=MILLISECOND):
    # This is really confusing, sorry.
    #
    # We get the `total_time` in `scale` since the start and we want to compute a percentage.
    # Since the time is monotonically increasing we can't just submit a point-in-time value but
    # rather it needs to be temporally aware, thus we submit the value as a rate.
    #
    # If we submit it as-is, that would be `scale` per second but we need seconds per second
    # since the Agent's check run interval is internally represented as seconds. Hence we divide
    # by 1000, for example, if the `scale` is milliseconds.
    #
    # At this point we have a number that will be no greater than 1 when compared to the last run.
    #
    # To turn it into a percentage we multiply by 100.
    return total_time / scale * 100


def exclude_undefined_keys(mapping):
    return {key: value for key, value in iteritems(mapping) if value is not None}


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
