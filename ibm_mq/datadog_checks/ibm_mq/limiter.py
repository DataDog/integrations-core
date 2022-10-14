# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading


class ConditionLimiter(object):
    """
    This class is used to limit the number of concurrent satisfied conditions. This is intended for use in
    scenarios where it is critical that no conditions are satisfied after a certain limit has been reached.
    Therefore, ephemeral false negatives are acceptable in order to maintain this guarantee without blocking.
    After the limit is reached, no conditions are evaluated until an earlier slot is explicitly released.

    Every subclass must implement a `condition` method. For example, if you wanted to only run one check
    instance at a time based on the command line arguments used to start an active process, you could do:

    ```python
    import re
    import shlex

    import psutil

    from datadog_checks.base import AgentCheck
    from datadog_checks.base.utils.concurrency.limiter import ConditionLimiter

    class Limiter(ConditionLimiter):
        def condition(self, pattern, logger):
            logger.info('Searching for a process that matches: %s', pattern)
            for process in psutil.process_iter(['cmdline']):
                command = shlex.join(process.info['cmdline'])
                if re.search(pattern, command):
                    logger.info('Process found: %s', command)
                    return True
            else:
                logger.info('Process not found, skipping check run')
                return False

    class Check(AgentCheck):
        limiter = Limiter()

        def check(self, _):
            if not self.limiter.check_condition(self.check_id, self.config.pattern, self.log):
                return

            try:
                ...
            except Exception:
                self.limiter.remove(self.check_id)
                raise

        def cancel(self):
            self.limiter.remove(self.check_id)
    ```
    """

    def __init__(self, limit=1):
        self.__limit = max(limit, 1)
        self.__cached_identifiers = set()
        self.__lock = threading.Lock()

    def limit_reached(self):
        return len(self.__cached_identifiers) >= self.__limit

    def remove(self, identifier):
        return self.__cached_identifiers.remove(identifier)

    def check_condition(self, identifier, *args, **kwargs):
        # Limit hit, return early
        if self.limit_reached():
            return identifier in self.__cached_identifiers
        # Limit not hit but the condition is already met
        elif identifier in self.__cached_identifiers:
            return True

        # Acquire the lock only after performing the quick state checks
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
