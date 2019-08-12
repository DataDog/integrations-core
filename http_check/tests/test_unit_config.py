# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.http_check.config import DEFAULT_EXPECTED_CODE, from_instance
from datadog_checks.utils.headers import headers as agent_headers


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
    params = from_instance({'url': 'https://example.com', 'name': 'UpService'})
    assert len(params) == 18

    # `url` is mandatory
    assert params[0] == 'https://example.com'
    # defualt `client_cert` is None
    assert params[1] is None
    # defualt `client_key` is None
    assert params[2] is None
    # default `method` is get
    assert params[3] == 'get'
    # default `data` is an empty dict
    assert params[4] == {}
    # default `http_response_status_code`
    assert params[5] == DEFAULT_EXPECTED_CODE
    # default `include_content` is False
    assert params[6] is False
    # default headers
    assert params[7] == agent_headers({})
    # default `collect_response_time` is True
    assert params[8] is True
    # default `content_match` is None
    assert params[9] is None
    # default `reverse_content_match` is False
    assert params[10] is False
    # default `tags` is an empty list
    assert params[11] == []
    # default `check_certificate_expiration` is True
    assert params[12] is True
    # default `ca_certs`, it's mocked we don't care
    assert params[13] != ''
    # default `weakciphers` is False
    assert params[14] is False
    # default `check_hostname` is True
    assert params[15] is True
    # default `allow_redirects` is True
    assert params[16] is True
    # default `stream` is False
    assert params[17] is False

    # headers
    params = from_instance(
        {'url': 'https://example.com', 'name': 'UpService', 'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}}
    )

    headers = params[7]
    expected_headers = agent_headers({}).get('User-Agent')
    assert headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers
    assert expected_headers == headers.get('User-Agent'), headers
