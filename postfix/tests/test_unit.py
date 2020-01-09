# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.postfix import PostfixCheck

MOCK_VERSION = '1.3.1'


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
