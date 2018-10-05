# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.utils.headers import headers as agent_headers
from datadog_checks.http_check.config import from_instance, DEFAULT_EXPECTED_CODE


@pytest.mark.unit
def test_from_instance():
    """
    Test the defaults and the pieces of _load_conf that actually perform some logic
    """
    # misconfiguration
    with pytest.raises(Exception) as e:
        from_instance({})
        assert 'Bad configuration' in str(e)

    # defaults
    params = from_instance({
        'url': 'https://example.com',
        'name': 'UpService',
    })
    assert len(params) == 24

    # `url` is mandatory
    assert params[0] == 'https://example.com'
    # default `ntlm_domain` is None
    assert params[1] is None
    # default `username` is None
    assert params[2] is None
    # default `password` is None
    assert params[3] is None
    # defualt `client_cert` is None
    assert params[4] is None
    # defualt `client_key` is None
    assert params[5] is None
    # default `method` is get
    assert params[6] == 'get'
    # default `data` is an empty dict
    assert params[7] == {}
    # default `http_response_status_code`
    assert params[8] == DEFAULT_EXPECTED_CODE
    # default `timeout` is 10
    assert params[9] == 10
    # default `include_content` is False
    assert params[10] is False
    # default headers
    assert params[11] == agent_headers({})
    # default `collect_response_time` is True
    assert params[12] is True
    # default `content_match` is None
    assert params[13] is None
    # default `reverse_content_match` is False
    assert params[14] is False
    # default `tags` is an empty list
    assert params[15] == []
    # default `disable_ssl_validation` is True
    assert params[16] is True
    # default `check_certificate_expiration` is True
    assert params[17] is True
    # default `ca_certs`, it's mocked we don't care
    assert params[18] != ''
    # default `weakciphers` is False
    assert params[19] is False
    # default `check_hostname` is True
    assert params[20] is True
    # default `ignore_ssl_warning` is False
    assert params[21] is False
    # default `skip_proxy` is False
    assert params[22] is False
    # default `allow_redirects` is True
    assert params[23] is True

    # headers
    params = from_instance({
        'url': 'https://example.com',
        'name': 'UpService',
        'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}
    })

    headers = params[11]
    expected_headers = agent_headers({}).get('User-Agent')
    assert headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers
    assert expected_headers == headers.get('User-Agent'), headers

    # proxy
    params = from_instance({
        'url': 'https://example.com',
        'name': 'UpService',
        'no_proxy': True,
    })
    assert params[22] is True

    params = from_instance({
        'url': 'https://example.com',
        'name': 'UpService',
        'no_proxy': False,
        'skip_proxy': True,
    })
    assert params[22] is True
