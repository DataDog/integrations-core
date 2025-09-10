from collections.abc import Callable

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.cache_key import CacheKey, CacheKeyManager, CacheKeyType, FullConfigCacheKey


class TestCacheKey(CacheKey):
    def base_key(self):
        return "test"


@pytest.fixture
def check():
    check = AgentCheck(None)
    check.check_id = "test"
    return check


def test_manager_stores_cache_keys(check: AgentCheck):
    manager = CacheKeyManager(check)
    manager.add(cache_key_type=CacheKeyType.LOG_CURSOR, key_factory=lambda: TestCacheKey(check))
    assert manager.has_cache_key(CacheKeyType.LOG_CURSOR)


@pytest.mark.parametrize(
    "override, expected_key",
    [(False, TestCacheKey), (True, FullConfigCacheKey)],
    ids=["with_override", "without_override"],
)
def test_keys_not_added_if_present(check: AgentCheck, override: bool, expected_key: type[CacheKey]):
    manager = CacheKeyManager(check)
    manager.add(cache_key_type=CacheKeyType.LOG_CURSOR, key_factory=lambda: TestCacheKey(check))
    manager.add(
        cache_key_type=CacheKeyType.LOG_CURSOR,
        key_factory=lambda: FullConfigCacheKey(check),
        override=override,
    )
    key = manager.get(cache_key_type=CacheKeyType.LOG_CURSOR)
    assert isinstance(key, expected_key)


def default_factory(check: AgentCheck) -> Callable[[], CacheKey]:
    def factory():
        return TestCacheKey(check)

    return factory


@pytest.mark.parametrize(
    "default_factory, expected_key",
    [(None, FullConfigCacheKey), (default_factory, TestCacheKey)],
    ids=["with_default_factory", "without_default_factory"],
)
def test_get_default_factory_behavior(
    check: AgentCheck,
    default_factory: Callable[[AgentCheck], Callable[[], CacheKey]] | None,
    expected_key: type[CacheKey],
):
    manager = CacheKeyManager(check)
    factory = default_factory(check) if default_factory is not None else None
    key = manager.get(cache_key_type=CacheKeyType.LOG_CURSOR, default_factory=factory)
    assert isinstance(key, expected_key)
