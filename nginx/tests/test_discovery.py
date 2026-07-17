# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.nginx import Nginx


def generated_urls(service: Service) -> list[str]:
    return [config['instances'][0]['nginx_status_url'] for config in Nginx.generate_configs(service)]


def test_discovery_generates_http_for_port_80():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=80),))

    assert generated_urls(service) == ['http://127.0.0.1:80/nginx_status']


def test_discovery_generates_https_for_port_443():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=443),))

    assert generated_urls(service) == ['https://127.0.0.1:443/nginx_status']


def test_discovery_generates_https_for_port_8443():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=8443),))

    assert generated_urls(service) == ['https://127.0.0.1:8443/nginx_status']


def test_discovery_generates_https_for_named_https_port():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=9000, name='https'),))

    assert generated_urls(service) == ['https://127.0.0.1:9000/nginx_status']


def test_discovery_generates_http_for_unnamed_non_standard_port():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=9000),))

    assert generated_urls(service) == ['http://127.0.0.1:9000/nginx_status']


def test_discovery_prefers_http_80_before_https_443():
    service = Service(id='nginx', host='127.0.0.1', ports=(Port(number=80), Port(number=443)))

    urls = generated_urls(service)

    assert urls[0] == 'http://127.0.0.1:80/nginx_status'
    assert 'https://127.0.0.1:443/nginx_status' in urls
    assert 'http://127.0.0.1:443/nginx_status' not in urls
