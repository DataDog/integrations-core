# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

from datadog_checks.base import ConfigurationError
from datadog_checks.ibm_mq.config import IBMMQConfig

from .common import HOST

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'override_hostname, expected_hostname, expected_tag',
    [(False, None, 'mq_host:{}'.format(HOST)), (True, HOST, None)],
)
def test_mq_host_tag(instance, override_hostname, expected_hostname, expected_tag):
    instance['override_hostname'] = override_hostname
    config = IBMMQConfig(instance)

    assert config.hostname == expected_hostname
    if expected_tag:
        assert expected_tag in config.tags


def test_cannot_set_host_and_connection_name(instance):
    instance['connection_name'] = "localhost(8080)"
    with pytest.raises(ConfigurationError, match="Specify only one host/port or connection_name configuration"):
        IBMMQConfig(instance)


def test_cannot_set_override_hostname_and_connection_name(instance):
    instance['connection_name'] = "localhost(8080)"
    del instance['host']
    del instance['port']
    instance['override_hostname'] = True
    with pytest.raises(
        ConfigurationError,
        match="You cannot override the hostname if you provide a `connection_name` instead of a `host`",
    ):
        IBMMQConfig(instance)


def test_cannot_override_hostname_if_no_host_provided(instance):
    del instance['host']
    instance['override_hostname'] = True
    with pytest.raises(ConfigurationError, match="You cannot override the hostname if you don't provide a `host`"):
        IBMMQConfig(instance)


@pytest.mark.skipif(PY2, reason="Config model validation only available in PY3.")
@pytest.mark.parametrize(
    'param, values, should_error',
    [
        pytest.param('queues', ['queue1', 'queue2'], False, id="Unique queues values"),
        pytest.param('queues', ['queue1', 'queue1', 'queue2'], True, id="Non-unique queues values"),
        pytest.param('queue_patterns', ['queue1.*', 'queue2.*'], False, id="Unique queue_patterns values"),
        pytest.param(
            'queue_patterns', ['queue1.*', 'queue2.*', 'queue2.*'], True, id="Non-unique queue_patterns values"
        ),
        pytest.param('queue_regex', [r'^DEV\..*$', r'^SYSTEM\..*$'], False, id="Unique queue_regex values"),
        pytest.param(
            'queue_regex', [r'^DEV\..*$', r'^SYSTEM\..*$', r'^SYSTEM\..*$'], True, id="Non-unique queue_regex values"
        ),
        pytest.param('channels', ['channel_a', 'channel_b'], False, id="Unique channels values"),
        pytest.param('channels', ['channel_a', 'channel_b', 'channel_a'], True, id="Non-unique channels values"),
    ],
)
def test_unique_items_queues_channels(instance, get_check, dd_run_check, param, values, should_error):
    instance[param] = values
    check = get_check(instance)
    if should_error:
        with pytest.raises(Exception, match="`{}` must contain unique values.".format(param)):
            dd_run_check(check)
    else:
        try:
            dd_run_check(check)
        except Exception as e:
            AssertionError("`{}` contains non-unique values. Error is: {}".format(param, e))


@pytest.mark.skipif(PY2, reason="Config model validation only available in PY3.")
@pytest.mark.parametrize(
    'param, values, should_error',
    [
        pytest.param(
            'channel_status_mapping',
            {'inactive': 'critical', 'binding': 'warning', 'starting': 'warning'},
            False,
            id="Valid min properties in channel_status_mapping",
        ),
        pytest.param('channel_status_mapping', {}, True, id="Invalid empty map in channel_status_mapping"),
        pytest.param(
            'queue_tag_re',
            {'SYSTEM.*': 'queue_type:system', 'DEV.*': 'role:dev,queue_type:default'},
            False,
            id="Valid min properties in queue_tag_re",
        ),
        pytest.param('queue_tag_re', {}, True, id="Invalid empty map in queue_tag_re"),
    ],
)
def test_min_properties_queue_tags_channel_status(instance, get_check, dd_run_check, param, values, should_error):
    instance[param] = values
    check = get_check(instance)
    if should_error:
        with pytest.raises(Exception, match="`{}` must contain at least 1 mapping.".format(param)):
            dd_run_check(check)
    else:
        try:
            dd_run_check(check)
        except Exception as e:
            AssertionError("`{}` contains empty mapping. Error is: {}".format(param, e))


@pytest.mark.parametrize(
    'ssl_explicit_disable, ssl_option, expected_ssl',
    [
        pytest.param(
            False,
            'ssl_cipher_spec',
            True,
            id="ssl_cipher_spec enabled, SSL implicitly enabled",
        ),
        pytest.param(
            False,
            'ssl_key_repository_location',
            True,
            id="ssl_key_repository_location enabled, SSL implicitly enabled",
        ),
        pytest.param(
            False,
            'ssl_certificate_label',
            True,
            id="ssl_certificate_label enabled, SSL implicitly enabled",
        ),
        pytest.param(
            True,
            'ssl_cipher_spec',
            False,
            id="ssl_cipher_spec enabled but ssl_auth disabled, SSL explicitly disabled",
        ),
        pytest.param(
            True,
            'ssl_key_repository_location',
            False,
            id="ssl_key_repository_location enabled but ssl_auth disabled, SSL explicitly disabled",
        ),
        pytest.param(
            True,
            'ssl_certificate_label',
            False,
            id="ssl_certificate_label enabled but ssl_auth disabled, SSL explicitly disabled",
        ),
    ],
)
def test_ssl_auth_implicit_enable(instance, ssl_explicit_disable, ssl_option, expected_ssl):
    if ssl_explicit_disable:
        instance['ssl_auth'] = False

    # We only care that the option is enabled
    instance[ssl_option] = "dummy_value"

    config = IBMMQConfig(instance)

    assert config.ssl == expected_ssl
