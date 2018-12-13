# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from random import SystemRandom

from .utils import get_instance_name

BASE_BACKOFF_SECS = 15
MAX_BACKOFF_SECS = 300


class BackOffRetry(object):
    def __init__(self):
        self.backoff = {}
        self.random = SystemRandom()

    def should_run(self, instance):
        instance_name = get_instance_name(instance)
        if instance_name not in self.backoff:
            self.backoff[instance_name] = {'retries': 0, 'scheduled': time.time()}

        if self.backoff[instance_name]['scheduled'] <= time.time():
            return True

        return False

    def do_backoff(self, instance):
        instance_name = get_instance_name(instance)
        tracker = self.backoff[instance_name]

        self.backoff[instance_name]['retries'] += 1
        jitter = min(MAX_BACKOFF_SECS, BASE_BACKOFF_SECS * 2 ** self.backoff[instance_name]['retries'])

        # let's add some jitter (half jitter)
        backoff_interval = jitter / 2
        backoff_interval += self.random.randint(0, backoff_interval)

        tracker['scheduled'] = time.time() + backoff_interval
        return backoff_interval, self.backoff[instance_name]['retries']

    def reset_backoff(self, instance):
        name = get_instance_name(instance)
        self.backoff[name]['retries'] = 0
        self.backoff[name]['scheduled'] = time.time()
