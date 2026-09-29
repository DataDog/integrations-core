# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.vault import Vault

from .common import auth_required, noauth_required
from .utils import assert_collection


@auth_required
@pytest.mark.e2e
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
@pytest.mark.parametrize('use_auth_file', [False, True])
def test_e2e(dd_agent_check, e2e_instance, global_tags, use_openmetrics, use_auth_file):
    instance = dict(e2e_instance(use_auth_file))
    instance['use_openmetrics'] = use_openmetrics
    aggregator = dd_agent_check(instance, rate=True)

    assert_collection(aggregator, global_tags, use_openmetrics, runs=2)


@noauth_required
@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(discovery_min_instances=2, rate=True)

    # The E2E environment has a leader and a replica. Both use the Vault image and must be
    # discovered, so assert against the runtime-resolved URLs rather than one arbitrary instance.
    api_url_tags = {
        tag for metric in aggregator.metrics('vault.is_leader') for tag in metric.tags if tag.startswith('api_url:')
    }
    assert len(api_url_tags) == 2, f'Expected discovery to configure both Vault nodes, got {sorted(api_url_tags)}'

    assert_collection(
        aggregator,
        sorted(api_url_tags),
        use_openmetrics=True,
        runs=4,
        # These metrics only appear once a request has gone through Vault's authenticated
        # logical-request pipeline (ACL/token checks, audit logging, policy lookups, lease
        # issuance). The main `test_e2e` suite gets that incidentally, from auth-related tests
        # that run earlier in the same long-lived container; this test's `no_token` discovery
        # candidate only ever hits unauthenticated status endpoints (health/leader/metrics),
        # which bypass that pipeline entirely, so these metrics can't be guaranteed present here.
        exclude=(
            'vault.vault.audit.log.request.count',
            'vault.vault.audit.log.request.quantile',
            'vault.vault.audit.log.request.sum',
            'vault.vault.audit.log.request.failure.count',
            'vault.vault.audit.log.response.count',
            'vault.vault.audit.log.response.quantile',
            'vault.vault.audit.log.response.sum',
            'vault.vault.audit.log.response.failure.count',
            'vault.vault.core.check.token.count',
            'vault.vault.core.check.token.quantile',
            'vault.vault.core.check.token.sum',
            'vault.vault.core.fetch.acl_and_token.count',
            'vault.vault.core.fetch.acl_and_token.quantile',
            'vault.vault.core.fetch.acl_and_token.sum',
            'vault.vault.core.handle.request.count',
            'vault.vault.core.handle.request.quantile',
            'vault.vault.core.handle.request.sum',
            'vault.vault.expire.num_leases',
            'vault.vault.policy.get_policy.count',
            'vault.vault.policy.get_policy.quantile',
            'vault.vault.policy.get_policy.sum',
            'vault.vault.token.lookup.count',
            'vault.vault.token.lookup.quantile',
            'vault.vault.token.lookup.sum',
        ),
    )


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, Vault, compose_service='vault-leader')
