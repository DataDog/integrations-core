# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.weaviate import WeaviateCheck

from .common import MOCKED_INSTANCE, get_fixture_path

pytestmark = pytest.mark.integration


def test_check_mock_weaviate_metadata(datadog_agent, mock_http_response):
    mock_http_response(file_path=get_fixture_path('weaviate_meta_api.json'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    check._submit_version_metadata()
    raw_version = '1.19.1'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
