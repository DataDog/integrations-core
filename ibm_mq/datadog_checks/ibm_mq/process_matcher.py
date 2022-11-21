# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import psutil

from .limiter import ConditionLimiter

if sys.platform == 'win32':
    import subprocess

    def join_command_args(command_args):
        return subprocess.list2cmdline(command_args)

else:
    import shlex

    def join_command_args(command_args):
        # TODO: when we drop Python 2 use `shlex.join`
        return ' '.join(shlex.quote(arg) for arg in command_args)


class QueueManagerProcessMatcher(ConditionLimiter):
    def __init__(self, limit=1):
        super(QueueManagerProcessMatcher, self).__init__(limit)

    def condition(self, pattern, logger):
        logger.info('Searching for a process that matches: %s', pattern.pattern)
        for process in psutil.process_iter(['cmdline']):
            command = join_command_args(process.info['cmdline'])
            if pattern.search(command):
                logger.info('Process found: %s', command)
                return True
        else:
            return False
