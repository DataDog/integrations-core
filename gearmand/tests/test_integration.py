# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.gearmand import Gearman

from . import common


def test_service_check_broken(check, aggregator):
    tags = ['server:{}'.format(common.HOST), 'port:{}'.format(common.BAD_PORT)] + common.TAGS2

    with pytest.raises(Exception):
        check.check(common.BAD_INSTANCE)

    aggregator.assert_service_check('gearman.can_connect', status=Gearman.CRITICAL, tags=tags, count=1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(check, aggregator, datadog_agent):
    check.check_id = 'test:123'
    check.check(common.INSTANCE)

    # hardcoded because we only support one docker image for test env
    raw_version = '1.0.6'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
