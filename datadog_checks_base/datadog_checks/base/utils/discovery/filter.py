# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re


class Filter:
    def __init__(self, limit, include, exclude, key):
        self._limit = limit
        self._include = include
        self._exclude = re.compile('|'.join(exclude)) if exclude else None
        self._key = key
        self._compiled_include_patterns = (
            {pattern: re.compile(pattern) for pattern in include.keys()} if include is not None else None
        )

    def get_items(self, items):
        if self._include is None:
            return
        key = self._key or (lambda item: item)
        discovered_item_keys = set()
        excluded_item_keys = (
            [key(item) for item in items if re.search(self._exclude, key(item))] if self._exclude else []
        )
        for pattern, config in self._include.items():
            for item in items:
                if len(discovered_item_keys) == self._limit:
                    return
                if (
                    key(item) not in excluded_item_keys
                    and key(item) not in discovered_item_keys
                    and re.search(self._compiled_include_patterns[pattern], key(item))
                ):
                    discovered_item_keys.add(key(item))
                    yield pattern, key(item), item, config
