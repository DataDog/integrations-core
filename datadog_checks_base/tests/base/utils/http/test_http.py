# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest
import requests
import requests_unixsocket
from flaky import flaky
from six import PY2, iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper, is_uds_url, quote_uds_url
from datadog_checks.dev.utils import ON_WINDOWS


class TestAttribute:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])

        assert not hasattr(check, '_http')

    def test_activate(self):
        check = AgentCheck('test', {}, [{}])

        assert check.http == check._http
        assert isinstance(check.http, RequestsWrapper)


class TestRequestSize:
    def test_behavior_correct(self, mock_http_response):
        instance = {'request_size': 0.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        chunk_size = 512
        payload_size = 1000
        mock_http_response('a' * payload_size)

        with http.get('https://www.google.com', stream=True) as response:
            chunks = list(response.iter_content())

        assert len(chunks) == 2
        assert len(chunks[0]) == chunk_size
        assert len(chunks[1]) == payload_size - chunk_size


class TestUnixDomainSocket:
    @pytest.mark.parametrize(
        'value, expected',
        [
            pytest.param('http://example.org', False, id='non-uds-url'),
            pytest.param('unix:///var/run/test.sock/info', True, id='unquoted'),
            pytest.param('unix://%2Fvar%2Frun%2Ftest.sock', True, id='quoted'),
        ],
    )
    def test_is_uds_url(self, value, expected):
        # type: (str, bool) -> None
        assert is_uds_url(value) == expected

    @pytest.mark.parametrize(
        'value, expected',
        [
            pytest.param('http://example.org', 'http://example.org', id='non-uds-url'),
            pytest.param('unix:///var/run/test.sock/info', 'unix://%2Fvar%2Frun%2Ftest.sock/info', id='uds-url'),
            pytest.param('unix:///var/run/test.sock', 'unix://%2Fvar%2Frun%2Ftest.sock', id='uds-url-no-path'),
            pytest.param(
                'unix://%2Fvar%2Frun%2Ftest.sock/info', 'unix://%2Fvar%2Frun%2Ftest.sock/info', id='already-quoted'
            ),
        ],
    )
    def test_quote_uds_url(self, value, expected):
        # type: (str, str) -> None
        assert quote_uds_url(value) == expected

    def test_adapter_mounted(self):
        # type: () -> None
        http = RequestsWrapper({}, {})
        url = 'unix:///var/run/test.sock'
        adapter = http.session.get_adapter(url=url)
        assert adapter is not None
        assert isinstance(adapter, requests_unixsocket.UnixAdapter)

    @flaky(max_runs=3, rerun_filter=lambda err, name, test, plugin: PY2)
    @pytest.mark.skipif(ON_WINDOWS, reason='AF_UNIX not supported by Python on Windows yet')
    def test_uds_request(self, uds_path):
        # type: (str) -> None
        http = RequestsWrapper({}, {})
        url = 'unix://{}'.format(uds_path)
        response = http.get(url)
        assert response.status_code == 200
        assert response.text == 'Hello, World!'


class TestSession:
    def test_default_none(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http._session is None

    def test_lazy_create(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.session is http._session
        assert isinstance(http.session, requests.Session)

    def test_attributes(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        for key, value in iteritems(http.options):
            assert hasattr(http.session, key)
            assert getattr(http.session, key) == value


class TestLogger:
    def test_default(self, caplog):
        check = AgentCheck('test', {}, [{}])

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_instance(self, caplog):
        instance = {'log_requests': True}
        init_config = {}
        check = AgentCheck('test', init_config, [instance])

        assert check.http.logger is check.log

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_init_config(self, caplog):
        instance = {}
        init_config = {'log_requests': True}
        check = AgentCheck('test', init_config, [instance])

        assert check.http.logger is check.log

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_instance_override(self, caplog):
        instance = {'log_requests': False}
        init_config = {'log_requests': True}
        check = AgentCheck('test', init_config, [instance])

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message


class TestIntegration:
    def test_session_timeout(self):
        http = RequestsWrapper({'persist_connections': True}, {'timeout': 0.08})
        with pytest.raises(requests.exceptions.Timeout):
            http.get('https://httpbin.org/delay/0.10')
