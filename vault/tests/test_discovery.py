# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.vault import Vault

pytestmark = [pytest.mark.unit]


def generated_instances(service: Service) -> list[dict]:
    return [config['instances'][0] for config in Vault.generate_configs(service)]


def test_generates_one_http_candidate() -> None:
    # Only a `no_token=True` candidate is generated. A candidate without `no_token` and without a
    # configured `client_token`/`client_token_path` never attempts a metrics scrape at all (see
    # `VaultCheckV2.metric_collection_enabled`), so it would only ever emit the
    # always-unauthenticated leader/health metrics and never the real metric set. Discovery
    # accepts the first candidate whose check run collects at least one metric with no error, so
    # such a health-only candidate would trivially "succeed" and get locked in permanently — a
    # degraded config masquerading as a working one. We never synthesize a token, so the only way
    # to guarantee a real metrics scrape is `no_token=True`.
    #
    # Only the OpenMetrics mode (`use_openmetrics: true`) is generated; the legacy mode is not
    # covered by discovery. HTTPS is not covered either: the official Vault Helm chart disables
    # TLS by default (`global.tlsDisable: true`), so plain HTTP is the common container listener,
    # and an HTTPS candidate would need a trusted CA to ever succeed.
    service = Service(id='vault', host='127.0.0.1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert [
        (instance['api_url'], instance.get('use_openmetrics'), instance.get('no_token')) for instance in instances
    ] == [
        ('http://127.0.0.1:8200/v1', True, True),
    ]


def test_all_candidates_enable_metric_collection() -> None:
    # Every generated candidate must be able to reach Vault's real metrics scrape, not just the
    # always-unauthenticated leader/health endpoints. `no_token=True` is the only signal discovery
    # can produce on its own; a `client_token`/`client_token_path` can only come from the user.
    service = Service(id='vault', host='127.0.0.1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert all(
        instance.get('no_token') is True or instance.get('client_token') or instance.get('client_token_path')
        for instance in instances
    )


def test_ipv6_host_is_bracketed_in_generated_api_url() -> None:
    service = Service(id='vault', host='fd00::1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert [instance['api_url'] for instance in instances] == [
        'http://[fd00::1]:8200/v1',
    ]
