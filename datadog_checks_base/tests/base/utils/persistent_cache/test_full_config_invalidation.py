import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.persistent_cache.full_config_invalidation import FullConfigInvalidationStrategy


@pytest.fixture
def check():
    check = AgentCheck('test', {}, [{}])
    check.check_id = "test"
    return check


def test_full_config_invalidation_strategy(check: AgentCheck):
    cache_key = FullConfigInvalidationStrategy(check)
    assert cache_key.invalidation_token() == check.check_id
    assert cache_key.key_prefix() == check.check_id
