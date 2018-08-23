# stdlib
import binascii
import logging
import os
from random import sample, shuffle
import getpass

import pytest

from datadog_checks.postfix import PostfixCheck
from datadog_checks.dev.utils import temp_dir, create_file

log = logging.getLogger()


@pytest.fixture
def setup_postfix():
    with temp_dir() as tempdir:
        queue_root = os.path.join(tempdir, 'var', 'spool', 'postfix')

        queues = [
            'active',
            'maildrop',
            'bounce',
            'incoming',
            'deferred'
        ]

        in_count = {}

        for queue in queues:
            try:
                os.makedirs(os.path.join(queue_root, queue))
                in_count[queue] = [0, 0]
            except Exception:
                pass

        return_value = {
            'queue_root': queue_root,
            'queues': queues,
            'in_count': in_count
        }

        add_messages(queue_root, queues, in_count)

        yield return_value


def add_messages(queue_root, queues, in_count):
    for _ in range(10000):
        shuffle(queues)
        rand_queue = sample(queues, 1)[0]
        queue_file = binascii.b2a_hex(os.urandom(7))

        create_file(os.path.join(queue_root, rand_queue, queue_file))

        # keep track of what we put in
        in_count[rand_queue][0] += 1


@pytest.fixture
def check():
    return PostfixCheck('postfix', {}, {})


def test_check(setup_postfix, check, aggregator):

    queue_root = setup_postfix['queue_root']
    queues = setup_postfix['queues']
    in_count = setup_postfix['in_count']

    instance = {
        'directory': queue_root,
        'queues': queues,
        'postfix_user': getpass.getuser()
    }

    check.check(instance)

    for queue, count in in_count.iteritems():
        tags = ['instance:postfix', 'queue:{}'.format(queue)]
        aggregator.assert_metric('postfix.queue.size',
                                 value=count[0],
                                 tags=tags)
