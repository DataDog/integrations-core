# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import psutil

from datadog_checks.base.utils.concurrency.limiter import ConditionLimiter

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
    def condition(self, pattern, logger):
        logger.debug('Searching for a process that matches: %s', pattern.pattern)
        for process in psutil.process_iter(['cmdline']):
            command = join_command_args(process.info['cmdline'])
            if pattern.search(command):
                logger.debug('Process found: %s', command)
                return True
        else:
            return False
