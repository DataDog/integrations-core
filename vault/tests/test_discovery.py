# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.vault import Vault

pytestmark = [pytest.mark.unit]


def generated_instances(service: Service) -> list[dict]:
    return [config['instances'][0] for config in Vault.generate_configs(service)]


def test_generates_one_candidate_per_mode_and_token_strategy() -> None:
    # Order matters: discovery accepts the first candidate whose real check run collects a
    # metric. Both `no_token=True` candidates actually attempt a metrics scrape (the check only
    # skips scraping when neither a token nor `no_token` is configured, see
    # `VaultCheckV2.metric_collection_enabled`), so they must be tried, in either mode, before
    # either `no_token=False` candidate — those never scrape at all and would trivially "succeed"
    # on the always-unauthenticated leader/health metrics alone, permanently starving out a
    # `no_token` candidate that could have collected the full metric set.
    service = Service(id='vault', host='127.0.0.1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert [(instance.get('use_openmetrics'), instance.get('no_token')) for instance in instances] == [
        (True, True),
        (False, True),
        (True, False),
        (False, False),
    ]


def test_all_candidates_target_the_same_api_url() -> None:
    service = Service(id='vault', host='127.0.0.1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert all(instance['api_url'] == 'http://127.0.0.1:8200/v1' for instance in instances)


def test_ipv6_host_is_bracketed_in_generated_api_url() -> None:
    service = Service(id='vault', host='fd00::1', ports=(Port(number=8200),))

    instances = generated_instances(service)

    assert all(instance['api_url'] == 'http://[fd00::1]:8200/v1' for instance in instances)
