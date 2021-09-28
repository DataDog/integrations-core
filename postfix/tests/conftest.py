# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import binascii
import os
from random import sample, shuffle

import pytest

from datadog_checks.base import ensure_unicode
from datadog_checks.dev import LazyFunction, TempDir
from datadog_checks.dev.env import environment_run, serialize_data, set_env_vars
from datadog_checks.dev.fs import create_file

from .common import get_e2e_instance, get_e2e_metadata


class CreateQueues(LazyFunction):
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def __call__(self):
        queue_root = os.path.join(self.data_dir, 'var', 'spool', 'postfix_data')

        queues = ['active', 'maildrop', 'bounce', 'incoming', 'deferred']

        in_count = {}

        for queue in queues:
            try:
                os.makedirs(os.path.join(queue_root, queue))
                in_count[queue] = [0, 0]
            except Exception:
                pass

        self.add_messages(queue_root, queues, in_count)

        return {'data_dir': queue_root, 'postfix_queues': queues, 'queue_counts': in_count}

    @classmethod
    def add_messages(cls, queue_root, queues, in_count):
        for _ in range(10000):
            shuffle(queues)
            rand_queue = sample(queues, 1)[0]
            queue_file = ensure_unicode(binascii.b2a_hex(os.urandom(7)))

            create_file(os.path.join(queue_root, rand_queue, queue_file))

            # keep track of what we put in
            in_count[rand_queue][0] += 1


@pytest.fixture(scope='session')
def dd_environment():
    with TempDir() as temp_dir:
        # No tear down necessary as `TempDir` will do the clean up
        with environment_run(CreateQueues(temp_dir), lambda: None) as result:
            set_env_vars({k: serialize_data(v) for k, v in result.items()})

            yield get_e2e_instance(), get_e2e_metadata()
