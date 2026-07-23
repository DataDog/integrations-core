# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.nginx import Nginx


def generated_urls(service: Service) -> list[str]:
    return [config['instances'][0]['nginx_status_url'] for config in Nginx.generate_configs(service)]


@pytest.mark.parametrize(
    'port, expected_scheme',
    [
        (Port(number=80), 'http'),
        (Port(number=443), 'https'),
        (Port(number=8443), 'https'),
        (Port(number=9000, name='https'), 'https'),
        (Port(number=9000), 'http'),
    ],
    ids=['port_80', 'port_443', 'port_8443', 'named_https_port', 'unnamed_non_standard_port'],
)
def test_discovery_generates_matching_scheme(port, expected_scheme):
    service = Service(id='nginx', host='127.0.0.1', ports=(port,))

    assert generated_urls(service) == [f'{expected_scheme}://127.0.0.1:{port.number}/nginx_status']


def test_discovery_prefers_http_80_before_https_443():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=80), Port(number=443)))

    urls = generated_urls(service)

    assert urls[0] == 'http://127.0.0.1:80/nginx_status'
    assert 'https://127.0.0.1:443/nginx_status' in urls
    assert 'http://127.0.0.1:443/nginx_status' not in urls
