# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from __future__ import division

import time
from random import SystemRandom

BASE_BACKOFF_SECS = 15
MAX_BACKOFF_SECS = 300


class BackOffRetry(object):
    def __init__(self):
        self.backoff = None
        self.random = SystemRandom()

    def should_run(self):
        if self.backoff is None:
            self.backoff = {'retries': 0, 'scheduled': time.time()}

        if self.backoff['scheduled'] <= time.time():
            return True

        return False

    def do_backoff(self):
        tracker = self.backoff

        self.backoff['retries'] += 1
        jitter = min(MAX_BACKOFF_SECS, BASE_BACKOFF_SECS * 2 ** self.backoff['retries'])

        # let's add some jitter (half jitter)
        backoff_interval = jitter // 2
        backoff_interval += self.random.randint(0, backoff_interval)

        tracker['scheduled'] = time.time() + backoff_interval
        return backoff_interval, self.backoff['retries']

    def reset_backoff(self):
        self.backoff['retries'] = 0
        self.backoff['scheduled'] = time.time()
