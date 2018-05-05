# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from six.moves.urllib.parse import urlparse


def get_docker_hostname():
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def pattern_filter(items, patterns, exclude=False, key=None):
    """This filters `items` by regular expression `patterns`. If `exclude`
    is `True`, treat `patterns` as a blacklist instead. An optional `key`
    function can be provided that will be passed each item.
    """
    if not patterns:
        return items

    key = key or __return_self
    matches = {
        key(item) for pattern in patterns
        for item in items
        if re.search(pattern, key(item))
    }

    if exclude:
        return [item for item in items if key(item) not in matches]
    else:
        return [item for item in items if key(item) in matches]


def __return_self(obj):
    return obj
