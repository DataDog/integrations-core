# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time


class Cache:
    def __init__(self, get_items_func, interval):
        self._get_items_func = get_items_func
        self._interval = interval
        self._last_get_items_time = None
        self._cached_items = []

    def get_items(self):
        if not self.__interval_configured() or self.__should_refresh_now():
            self.__refresh()
        return self._cached_items

    def __interval_configured(self):
        return self._interval is not None and self._interval > 0

    def __should_refresh_now(self):
        return self._last_get_items_time is None or (time.time() > self._last_get_items_time + self._interval)

    def __refresh(self):
        self._cached_items = self._get_items_func()
        self._last_get_items_time = time.time()
