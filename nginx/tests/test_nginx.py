# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests

from .common import FIXTURES_PATH, HOST, NGINX_VERSION, PORT_SSL, TAGS_WITH_HOST, TAGS_WITH_HOST_AND_PORT, USING_VTS
from .utils import mocked_perform_request, requires_static_version

pytestmark = [pytest.mark.skipif(USING_VTS, reason='Using VTS'), pytest.mark.integration]


@pytest.mark.usefixtures('dd_environment')
def test_connect(check, instance, aggregator):
    """
    Testing that connection will work with instance
    """
    check = check(instance)
    check.check(instance)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS_WITH_HOST_AND_PORT, count=1)
    aggregator.assert_service_check('nginx.can_connect', tags=TAGS_WITH_HOST_AND_PORT)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'disable_generic_tags, host_tag',
    [
        pytest.param(True, [], id="disabled"),
        pytest.param(False, ['host:{}'.format(HOST)], id="enabled"),
    ],
)
def test_generic_tags(check, instance, aggregator, disable_generic_tags, host_tag):
    """
    Generic tags should be removed from with the appropriate config toggle.

    Important: this only applies to service checks, metrics always have only 'nginx_host' tag.
    """
    instance['disable_generic_tags'] = disable_generic_tags
    check = check(instance)
    check.check(instance)
    tags = TAGS_WITH_HOST_AND_PORT
    aggregator.assert_metric("nginx.net.connections", tags=tags, count=1)
    aggregator.assert_service_check('nginx.can_connect', tags=tags + host_tag)


@pytest.mark.usefixtures('dd_environment')
def test_connect_ssl(check, instance_ssl, aggregator):
    """
    Testing ssl connection
    """
    instance_ssl['ssl_validation'] = False
    check_no_ssl = check(instance_ssl)
    check_no_ssl.check(instance_ssl)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS_WITH_HOST + ['port:{}'.format(PORT_SSL)], count=1)

    # assert ssl validation throws an error
    with pytest.raises(requests.exceptions.SSLError):
        instance_ssl['ssl_validation'] = True
        check_ssl = check(instance_ssl)
        check_ssl.check(instance_ssl)


@requires_static_version
@pytest.mark.usefixtures('dd_environment')
def test_metadata(check, instance, datadog_agent):
    nginx_check = check(instance)
    nginx_check.check_id = 'test:123'

    if USING_VTS:
        # vts currently defaults to using version 1.13
        version = '1.13'
    else:
        version = NGINX_VERSION.split(':')[1]

    major, minor = version.split('.')

    version_metadata = {'version.scheme': 'semver', 'version.major': major, 'version.minor': minor}

    nginx_check.check(instance)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 2)


@mock.patch(
    'datadog_checks.nginx.Nginx._get_plus_api_data',
    return_value=open(os.path.join(FIXTURES_PATH, 'v1/' 'plus_api_nginx.json')).read(),
)
def test_metadata_plus(_, aggregator, check, datadog_agent):
    # Hardcoded in the fixture
    version = '1.13.7'
    instance = {
        'nginx_status_url': 'dummy_url',
        'use_plus_api': True,
        'disable_generic_tags': True,
    }

    nginx_check = check(instance)
    nginx_check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    nginx_check.check_id = 'test:123'

    major, minor, patch = version.split('.')

    version_metadata = {
        'version.raw': version,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    nginx_check.check(instance)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
