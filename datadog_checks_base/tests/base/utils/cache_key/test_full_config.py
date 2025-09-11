import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.cache_key.full_config import FullConfigCacheKey


@pytest.fixture
def check():
    check = AgentCheck('test', {}, [{}])
    check.check_id = "test"
    return check


def test_full_config_cache_key(check: AgentCheck):
    cache_key = FullConfigCacheKey(check)
    assert cache_key.base_key() == check.check_id


def test_cache_with_context(check: AgentCheck):
    cache_key = FullConfigCacheKey(check)
    assert cache_key.key_for("test") == f"{check.check_id}_test"
