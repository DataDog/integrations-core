# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.dev import get_here
from datadog_checks.postfix import PostfixCheck

MOCK_VERSION = '1.3.1'


def test__get_postqueue_stats(aggregator):
    check = PostfixCheck('postfix', {}, [])
    common_tags = ['instance:/etc/postfix', 'foo:bar']

    filepath = os.path.join(get_here(), 'fixtures', 'postqueue_p.txt')
    with open(filepath, 'r') as f:
        mocked_output = f.read()

    with mock.patch('datadog_checks.postfix.postfix.get_subprocess_output') as s:
        s.side_effect = [(False, None, None), (mocked_output, None, None)]
        check._get_postqueue_stats('/etc/postfix', ['foo:bar'])

        aggregator.assert_metric('postfix.queue.size', 1, tags=common_tags + ['queue:active'])
        aggregator.assert_metric('postfix.queue.size', 1, tags=common_tags + ['queue:hold'])
        aggregator.assert_metric('postfix.queue.size', 2, tags=common_tags + ['queue:deferred'])


def test__get_postqueue_stats_empty(aggregator):
    check = PostfixCheck('postfix', {}, [])
    common_tags = ['instance:/etc/postfix']

    with mock.patch('datadog_checks.postfix.postfix.get_subprocess_output') as s:
        s.side_effect = [(False, None, None), ('Mail queue is empty', None, None)]
        check._get_postqueue_stats('/etc/postfix', [])

        aggregator.assert_metric('postfix.queue.size', 0, tags=common_tags + ['queue:active'])
        aggregator.assert_metric('postfix.queue.size', 0, tags=common_tags + ['queue:active'])
        aggregator.assert_metric('postfix.queue.size', 0, tags=common_tags + ['queue:deferred'])


@mock.patch(
    'datadog_checks.postfix.postfix.get_subprocess_output',
    return_value=('mail_version = {}'.format(MOCK_VERSION), None, None),
)
def test_collect_metadata(aggregator, datadog_agent):
    # TODO: Migrate this test as e2e test when it's possible to retrieve the metadata from the Agent
    check = PostfixCheck('postfix', {}, [{}])
    check.check_id = 'test:123'

    check._collect_metadata()

    major, minor, patch = MOCK_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': MOCK_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
