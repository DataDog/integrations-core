# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading


class ConditionLimiter(object):
    def __init__(self, limit=1):
        self.__limit = max(limit, 1)
        self.__cached_identifiers = set()
        self.__lock = threading.Lock()

    def limit_reached(self):
        return len(self.__cached_identifiers) >= self.__limit

    def remove(self, identifier):
        return self.__cached_identifiers.remove(identifier)

    def check_condition(self, identifier, *args, **kwargs):
        if self.limit_reached():
            return identifier in self.__cached_identifiers

        with self.__lock:
            # Check if the limit has been reached while locked
            if self.limit_reached():
                return identifier in self.__cached_identifiers

            condition_met = self.condition(*args, **kwargs)
            if condition_met:
                self.__cached_identifiers.add(identifier)

            return condition_met

    def condition(self, *args, **kwargs):
        raise NotImplementedError
