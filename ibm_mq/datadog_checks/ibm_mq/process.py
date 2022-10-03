from __future__ import annotations

import re
import threading

import psutil

from .utils import join_command_args


class QueueManagerProcessFinder:
    def __init__(self, limit=1):
        self.__lock = threading.Lock()
        self.__limit = limit
        self.__cached_check_ids = set()

    def limit_reached(self):
        return len(self.__cached_check_ids) >= self.__limit

    def remove(self, check_id: str):
        return self.__cached_check_ids.remove(check_id)

    def check_condition(self, check_id: str, *args, **kwargs):
        if self.limit_reached():
            return check_id in self.__cached_check_ids

        with self.__lock:
            # Check if the limit has been reached while locked
            if self.limit_reached():
                return check_id in self.__cached_check_ids

            condition_met = self.condition(*args, **kwargs)
            if condition_met:
                self.__cached_check_ids.add(check_id)

            return condition_met

    def condition(self, pattern: re.Pattern, logger):
        logger.info('Searching for a process that matches: %s', pattern.pattern)
        for process in psutil.process_iter(['cmdline']):
            command = join_command_args(process.info['cmdline'])
            if pattern.search(command):
                logger.info('Process found: %s', command)
                return True
        else:
            logger.info('Process not found, skipping check run')
            return False
