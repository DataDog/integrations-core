# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .cache import Cache
from .filter import Filter


class Discovery:
    def __init__(
        self,
        get_items_func,
        limit=None,
        include=None,
        exclude=None,
        interval=None,
        key=None,
    ):
        self._filter = Filter(limit, include, exclude, key)
        self._cache = Cache(get_items_func, interval)

    def get_items(self):
        items = self._cache.get_items()
        return self._filter.get_items(items)
