# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from six.moves.urllib.parse import urlparse


def get_docker_hostname():
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def pattern_filter(items, whitelist=None, blacklist=None, key=None):
    """This filters `items` by a regular expression `whitelist` and/or
    `blacklist`, with the `whitelist` taking precedence. An optional `key`
    function can be provided that will be passed each item.
    """
    if whitelist:
        key = key or __return_self

        if blacklist:
            whitelist = whitelist or []
            blacklist = blacklist or []
            whitelisted = set()
            blacklisted = set()

            for item in items:
                item_key = key(item)
                whitelisted.update(item_key for pattern in whitelist if re.search(pattern, item_key))
                blacklisted.update(item_key for pattern in blacklist if re.search(pattern, item_key))

            # Remove any whitelisted items from the blacklist.
            blacklisted.difference_update(whitelisted)
            return [item for item in items if key(item) not in blacklisted]
        else:
            whitelisted = {
                key(item) for pattern in whitelist
                for item in items
                if re.search(pattern, key(item))
            }
            return [item for item in items if key(item) in whitelisted]
    elif blacklist:
        key = key or __return_self
        blacklisted = {
            key(item) for pattern in blacklist
            for item in items
            if re.search(pattern, key(item))
        }
        return [item for item in items if key(item) not in blacklisted]
    else:
        return items


def __return_self(obj):
    return obj
