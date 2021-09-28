# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.couch import CouchDb, errors

from . import common


@pytest.mark.usefixtures("dd_environment")
def test_collect_metadata_instance(aggregator, datadog_agent, instance):
    check = CouchDb(common.CHECK_NAME, {}, [instance])
    check.check_id = common.CHECK_ID
    check.check(instance)
    version = common.COUCH_RAW_VERSION

    major, minor, patch = version.split('.')
    version_metadata = {
        'version.raw': version,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata(common.CHECK_ID, version_metadata)
    datadog_agent.assert_metadata_count(5)


@pytest.mark.unit
def test_empty_config(aggregator, check):
    """
    Test the check with various bogus instances
    """
    check.instance = {}
    with pytest.raises(ConfigurationError):
        # `server` is missing from the instance
        check.check({})


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_bad_server(aggregator, check):
    check.instance = common.BAD_CONFIG
    with pytest.raises(errors.ConnectionError):
        # the server instance is invalid
        check.check({})
        aggregator.assert_service_check(
            CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=common.BAD_CONFIG_TAGS, count=1
        )


@pytest.mark.unit
def test_bad_version(aggregator, check):
    check.instance = common.BAD_CONFIG
    check.get = mock.MagicMock(return_value={'version': '0.1.0'})
    with pytest.raises(errors.BadVersionError):
        # the server has an unsupported version
        check.check({})
        aggregator.assert_service_check(
            CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=common.BAD_CONFIG_TAGS, count=1
        )
