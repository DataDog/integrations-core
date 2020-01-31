# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.couch import CouchDb

from . import common

COUCHDB2_VERSIONS = {'2_3': '2.3.1'}


@pytest.mark.usefixtures("dd_environment")
def test_collect_metadata_instance(aggregator, datadog_agent, instance):
    check = CouchDb(common.CHECK_NAME, {}, [instance])
    check.check_id = common.CHECK_ID
    check.check(instance)
    version = common.COUCH_RAW_VERSION

    # CouchDB2 version is formatted differently for the datadog hosted image
    if common.COUCH_MAJOR_VERSION == 2:
        version = COUCHDB2_VERSIONS[common.COUCH_RAW_VERSION]

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
