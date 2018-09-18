# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import time
import random

from .utils import get_instance_key

BASE_BACKOFF_SECS = 15
MAX_BACKOFF_SECS = 300


class BackOffRetry(object):

    def __init__(self, check):
        self.backoff = {}
        random.seed()
        self.check = check

    def should_run(self, instance):
        i_key = get_instance_key(instance)
        if i_key not in self.backoff:
            self.backoff[i_key] = {'retries': 0, 'scheduled': time.time()}

        if self.backoff[i_key]['scheduled'] <= time.time():
            return True

        return False

    def do_backoff(self, instance):
        i_key = get_instance_key(instance)
        tracker = self.backoff[i_key]

        self.backoff[i_key]['retries'] += 1
        jitter = min(MAX_BACKOFF_SECS, BASE_BACKOFF_SECS * 2 ** self.backoff[i_key]['retries'])

        # let's add some jitter  (half jitter)
        backoff_interval = jitter / 2
        backoff_interval += random.randint(0, backoff_interval)

        tags = instance.get('tags', [])
        hypervisor_name = self.check.hypervisor_name_cache.get(i_key)
        if hypervisor_name:
            tags.extend("hypervisor:{}".format(hypervisor_name))

        self.check.gauge("openstack.backoff.interval", backoff_interval, tags=tags)
        self.check.gauge("openstack.backoff.retries", self.backoff[i_key]['retries'], tags=tags)

        tracker['scheduled'] = time.time() + backoff_interval

    def reset_backoff(self, instance):
        i_key = get_instance_key(instance)
        self.backoff[i_key]['retries'] = 0
        self.backoff[i_key]['scheduled'] = time.time()
