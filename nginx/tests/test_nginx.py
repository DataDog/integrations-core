# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from .common import HOST, NGINX_VERSION, PORT, TAGS, USING_VTS

pytestmark = pytest.mark.skipif(USING_VTS, reason='Using VTS')


@pytest.mark.usefixtures('dd_environment')
def test_connect(check, instance, aggregator):
    """
    Testing that connection will work with instance
    """
    check = check(instance)
    check.check(instance)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS, count=1)
    extra_tags = ['host:{}'.format(HOST), 'port:{}'.format(PORT)]
    aggregator.assert_service_check('nginx.can_connect', tags=TAGS + extra_tags)


@pytest.mark.usefixtures('dd_environment')
def test_connect_ssl(check, instance_ssl, aggregator):
    """
    Testing ssl connection
    """
    instance_ssl['ssl_validation'] = False
    check_no_ssl = check(instance_ssl)
    check_no_ssl.check(instance_ssl)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS, count=1)

    # assert ssl validation throws an error
    with pytest.raises(requests.exceptions.SSLError):
        instance_ssl['ssl_validation'] = True
        check_ssl = check(instance_ssl)
        check_ssl.check(instance_ssl)


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
