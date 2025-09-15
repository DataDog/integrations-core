from typing import Any

import pytest

from datadog_checks.base.checks.base import AgentCheck
from datadog_checks.base.utils.containers import hash_mutable
from datadog_checks.base.utils.persistent_cache.config_set_invalidation import ConfigSetInvalidationStrategy


@pytest.fixture(scope='module')
def config() -> dict[str, str]:
    return {
        'init_option1': 'init_value1',
        'init_option2': 'init_value2',
        'global': 'init_global_value',
    }


@pytest.fixture(scope='module')
def instance() -> dict[str, str]:
    return {
        'instance_option1': 'instance_value1',
        'instance_option2': 'instance_value2',
        'global': 'instance_global_value',
    }


def build_check(init_config: dict[str, Any], instance: dict[str, Any]) -> AgentCheck:
    return TestCheck('test', init_config, [instance])


@pytest.fixture(scope='module')
def check(config: dict[str, Any], instance: dict[str, Any]) -> AgentCheck:
    return build_check(config, instance)


@pytest.fixture(scope='module')
def cache_key(check: AgentCheck) -> ConfigSetInvalidationStrategy:
    return ConfigSetInvalidationStrategy(check, init_config_options=['init_option1'])


class TestCheck(AgentCheck):
    def check(self, instance):
        pass


def normalized_hash(value: object) -> str:
    return str(hash_mutable(value)).replace("-", "")


def test_config_set_caches_invalidation_token(cache_key: ConfigSetInvalidationStrategy):
    assert cache_key._ConfigSetInvalidationStrategy__invalidation_token is None  # type: ignore
    assert cache_key.invalidation_token() == normalized_hash(('init_value1',))
    assert cache_key._ConfigSetInvalidationStrategy__invalidation_token is not None  # type: ignore


def test_config_set_respect_cached_invalidation_token(cache_key: ConfigSetInvalidationStrategy):
    cache_key._ConfigSetInvalidationStrategy__invalidation_token = "123"  # type: ignore
    assert cache_key.invalidation_token() == "123"


def test_initialization_fails_without_any_options(check: AgentCheck):
    with pytest.raises(ValueError):
        ConfigSetInvalidationStrategy(check)


def test_same_invalidation_token_on_changes_in_unlesected_other_options(config: dict[str, Any], check: AgentCheck):
    cache_key = ConfigSetInvalidationStrategy(check, init_config_options=['init_option1'])
    expected_invalidation_token = normalized_hash(('init_value1',))
    assert cache_key.invalidation_token() == expected_invalidation_token

    config['init_option2'] = 'something elese'
    cache_key = ConfigSetInvalidationStrategy(check, init_config_options=['init_option1'])
    assert cache_key.invalidation_token() == expected_invalidation_token


@pytest.mark.parametrize(
    'extra_option',
    [
        ["item1", "item2"],
        ("item1", "item3"),
        {"key1": "item1", "key2": "item2"},
        {"key1": {"key2": "item2", "key3": "item3"}},
    ],
    ids=["list", "tuple", "dict", "nested_dict"],
)
def test_support_for_complex_option_values(
    check: AgentCheck,
    instance: dict[str, Any],
    extra_option: list[str] | tuple[str, str] | dict[str, str] | dict[str, dict[str, str]],
):
    instance['extra_option'] = extra_option
    cache_key = ConfigSetInvalidationStrategy(check, instance_config_options=['extra_option'])
    expected_invalidation_token = normalized_hash((extra_option,))
    assert cache_key.invalidation_token() == expected_invalidation_token


def deep_reverse(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: deep_reverse(v) for k, v in reversed(list(obj.items()))}
    if isinstance(obj, list):
        return [deep_reverse(e) for e in reversed(obj)]
    if isinstance(obj, tuple):
        return tuple(deep_reverse(e) for e in reversed(obj))
    return obj


@pytest.mark.parametrize(
    'extra_option',
    [
        ["item1", "item2"],
        ("item1", "item2"),
        {"key1": "item1", "key2": "item2"},
        {
            "key1": {"key2": "item2", "key3": ["item3", "item4"]},
        },
    ],
    ids=["list", "tuple", "dict", "nested_dict"],
)
def test_order_does_not_affect_key(
    check: AgentCheck,
    instance: dict[str, Any],
    extra_option: list[str] | tuple[str, str] | dict[str, str] | dict[str, dict[str, str]],
):
    instance['extra_option'] = extra_option
    cache_key = ConfigSetInvalidationStrategy(check, instance_config_options=['extra_option'])
    expected_invalidation_token = normalized_hash((extra_option,))

    instance['extra_option'] = deep_reverse(extra_option)
    cache_key = ConfigSetInvalidationStrategy(check, instance_config_options=['extra_option'])
    assert cache_key.invalidation_token() == expected_invalidation_token


def test_same_option_names_in_init_config_and_instance_config(check: AgentCheck, instance: dict[str, Any]):
    cache_key = ConfigSetInvalidationStrategy(check, init_config_options=['global'])
    expected_invalidation_token = normalized_hash(('init_global_value',))

    # Modifying the same option name in instance has no effect on key
    instance['global'] = 'something'

    assert cache_key.invalidation_token() == expected_invalidation_token
