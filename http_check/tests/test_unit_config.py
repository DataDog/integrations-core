# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.http_check.config import DEFAULT_EXPECTED_CODE, from_instance
from datadog_checks.base.utils.headers import headers as agent_headers


def test_from_instance():
    """
    Test the defaults and the pieces of _load_conf that actually perform some logic
    """
    # misconfiguration
    with pytest.raises(ConfigurationError) as e:
        from_instance({})
        assert 'Bad configuration' in str(e)

    # misconfiguration
    with pytest.raises(ConfigurationError) as e:
        from_instance({'url': 'example.com'})
        assert 'scheme' in str(e)

    # defaults
    config = from_instance({'url': 'https://example.com', 'name': 'UpService'})
    assert len(config) == 18

    # `url` is mandatory
    assert config.url == 'https://example.com'

    # assert defaults
    assert config.client_cert is None
    assert config.client_key is None
    assert config.method == 'get'
    assert config.data == {}
    assert config.http_response_status_code == DEFAULT_EXPECTED_CODE
    assert config.include_content is False
    assert config.headers == agent_headers({})
    assert config.response_time is True
    assert config.content_match is None
    assert config.reverse_content_match is False
    assert config.tags == []
    assert config.ssl_expire is True
    assert config.instance_ca_certs != ''  # `ca_certs`, it's mocked we don't care
    assert config.weakcipher is False
    assert config.check_hostname is True
    assert config.allow_redirects is True
    assert config.stream is False

    # headers
    config = from_instance(
        {'url': 'https://example.com', 'name': 'UpService', 'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}}
    )

    headers = config.headers
    expected_headers = agent_headers({}).get('User-Agent')
    assert headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers
    assert expected_headers == headers.get('User-Agent'), headers


def test_instance_ca_cert():
    """
    `instance_ca_cert` should default to the trusted ca_cert of the system
    if `tls_ca_cert` and `ca_certs` are unavailable.
    """
    # Ensure that 'tls_ca_cert' takes precedence
    params_with_all = from_instance(
        {'url': 'https://example2.com', 'name': 'UpService', 'tls_ca_cert': 'foobar', 'ca_certs': 'barfoo'},
        'default_ca_cert',
    )
    assert params_with_all.instance_ca_certs == 'foobar'

    # Original config option for ca_certs
    params_only_ca_certs = from_instance({'url': 'https://example2.com', 'name': 'UpService', 'ca_certs': 'ca_cert'})
    assert params_only_ca_certs.instance_ca_certs == 'ca_cert'

    # Default if there is no cert path is configured
    params_no_certs = from_instance({'url': 'https://example2.com', 'name': 'UpService'}, 'default_ca_cert')
    assert params_no_certs.instance_ca_certs == 'default_ca_cert'

    # No default ca_cert
    params_no_default = from_instance({'url': 'https://example2.com', 'name': 'UpService'})
    assert params_no_default.instance_ca_certs is None
