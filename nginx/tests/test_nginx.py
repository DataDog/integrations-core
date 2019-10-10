# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests
import mock

from .common import HOST, PORT, TAGS, USING_VTS

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
def test_metadata(check, instance, aggregator, version_metadata):
    nginx_check = check(instance)
    nginx_check.check_id = 'test:123'

    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        import pdb; pdb.set_trace()
        nginx_check.check(instance)

        for name, value in version_metadata.items():
            m.assert_any_call('test:123', name, value)

        assert m.call_count == len(version_metadata)