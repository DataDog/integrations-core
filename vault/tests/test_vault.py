# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from urllib.parse import urlparse

import pytest

from datadog_checks.vault import Vault
from datadog_checks.vault.common import DEFAULT_API_VERSION

from .common import INSTANCES, auth_required, noauth_required

pytestmark = pytest.mark.usefixtures('dd_environment')


class TestVault:
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_bad_config(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['invalid'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception):
            dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, count=0)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_no_extra_tags(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        instance.pop('tags')

        c = Vault(Vault.CHECK_NAME, {}, [instance])

        tag = ['api_url:{}'.format(INSTANCES['main']['api_url'])]
        dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=tag)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_unsupported_api_version_fallback(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['unsupported_api'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        assert not instance['api_url'].endswith(DEFAULT_API_VERSION)
        dd_run_check(c)
        assert c._api_url.endswith(DEFAULT_API_VERSION)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_connect_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c, dd_run_check)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_connect_fail(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['bad_url'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        if use_openmetrics:
            hostname = urlparse(instance['api_url']).hostname
            expected_exception = r'Connection to {} timed out'.format(hostname)

        else:
            expected_exception = r'^Vault endpoint `{}.+?` timed out after 1\.0 seconds$'.format(
                re.escape(instance['api_url'])
            )

        with pytest.raises(
            Exception,
            match=expected_exception,
        ):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(
            Vault.SERVICE_CHECK_CONNECT,
            status=Vault.CRITICAL,
            tags=['instance:foobar', 'api_url:http://1.2.3.4:555/v1'],
            count=1,
        )

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_unsealed_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, status=Vault.OK, count=1)

    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_service_check_initialized_ok(self, aggregator, dd_run_check, use_openmetrics):
        instance = {'use_openmetrics': use_openmetrics}
        instance.update(INSTANCES['main'])
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        dd_run_check(c)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, status=Vault.OK, count=1)

    @auth_required
    def test_token_renewal(self, caplog, aggregator, dd_run_check, instance, global_tags):
        instance = instance()
        instance['use_openmetrics'] = False
        instance['token_renewal_wait'] = 1
        c = Vault(Vault.CHECK_NAME, {}, [instance])
        renew_client_token = c.renew_client_token

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' not in caplog.text

        c.set_client_token('foo')
        c.renew_client_token = lambda: None
        aggregator.reset()

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)
        assert 'Permission denied, refreshing the client token...' in caplog.text

        aggregator.reset()

        with pytest.raises(Exception, match='^403 Client Error: Forbidden for url'):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags)

        renew_client_token()
        aggregator.reset()

        dd_run_check(c)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)

    @auth_required
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    @pytest.mark.parametrize('use_auth_file', [False, True])
    def test_auth_needed_but_no_token(
        self, aggregator, dd_run_check, instance, global_tags, use_openmetrics, use_auth_file
    ):
        instance = instance(use_auth_file)
        instance['no_token'] = True
        instance['use_openmetrics'] = use_openmetrics
        c = Vault(Vault.CHECK_NAME, {}, [instance])

        with pytest.raises(Exception, match='400 Client Error: Bad Request for url'):
            dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)

        if use_openmetrics:
            tags = global_tags + ['endpoint:{}/sys/metrics?format=prometheus'.format(instance['api_url'])]
            aggregator.assert_service_check('vault.openmetrics.health', status=c.CRITICAL, count=1, tags=tags)
        else:
            aggregator.assert_service_check(
                Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=1, tags=global_tags
            )

    @noauth_required
    @pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
    def test_noauth_needed(self, aggregator, dd_run_check, no_token_instance, global_tags, use_openmetrics):
        no_token_instance['use_openmetrics'] = use_openmetrics
        c = Vault(Vault.CHECK_NAME, {}, [no_token_instance])
        dd_run_check(c, extract_message=True)

        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.OK, count=1, tags=global_tags)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.WARNING, count=0)
        aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, status=Vault.CRITICAL, count=0)

        if use_openmetrics:
            aggregator.assert_service_check('vault.openmetrics.health', status=c.CRITICAL, count=0)
