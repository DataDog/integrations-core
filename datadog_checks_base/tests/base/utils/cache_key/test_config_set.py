from collections.abc import Callable
from typing import Any

import pytest

from datadog_checks.base.checks.base import AgentCheck
from datadog_checks.base.utils.cache_key import ConfigSetCacheKey


@pytest.fixture
def config() -> dict[str, str]:
    return {
        'option1': 'value1',
        'option2': 'value2',
    }


@pytest.fixture
def instance() -> dict[str, str]:
    return {
        'option1': 'value1',
        'option2': 'value2',
    }


class TestCheck(AgentCheck):
    def check(self, instance):
        pass


def build_check(init_config: dict[str, Any], instance: dict[str, Any]) -> AgentCheck:
    return TestCheck('test', init_config, [instance])


def test_config_set_caches_key(config: dict[str, Any], instance: dict[str, Any]):
    check = build_check(config, instance)
    cache_key = ConfigSetCacheKey(check, ['option1'])
    assert cache_key._ConfigSetCacheKey__key is None  # type: ignore
    assert cache_key.base_key() == str(hash(('value1',)))
    assert cache_key._ConfigSetCacheKey__key is not None  # type: ignore


def test_config_set_respect_cached_key(config: dict[str, Any], instance: dict[str, Any]):
    check = build_check(config, instance)
    cache_key = ConfigSetCacheKey(check, ['option1'])
    cache_key._ConfigSetCacheKey__key = "123"  # type: ignore
    assert cache_key.base_key() == "123"


def test_same_key_on_changes_in_other_options(config: dict[str, Any], instance: dict[str, Any]):
    cache_key = ConfigSetCacheKey(build_check(config, instance), ['option2'])
    expected_key = str(hash(('value2',)))
    assert cache_key.base_key() == expected_key

    config['option1'] = 'something elese'
    cache_key = ConfigSetCacheKey(build_check(config, instance), ['option2'])
    assert cache_key.base_key() == expected_key


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
    config: dict[str, Any],
    instance: dict[str, Any],
    extra_option: list[str] | tuple[str, str] | dict[str, str] | dict[str, dict[str, str]],
):
    instance['extra_option'] = extra_option
    check = build_check(config, instance)
    cache_key = ConfigSetCacheKey(check, ['extra_option'])
    expected_key = str(hash(cache_key._ConfigSetCacheKey__sorted_values((extra_option,))))  # type: ignore
    assert cache_key.base_key() == expected_key


def reorder_dict(option: dict[str, Any]) -> dict[str, Any]:
    return dict(reversed(option.items()))


def reorder_list_tuple(option: list[str] | tuple[str, ...]) -> list[str] | tuple[str, ...]:
    return list(reversed(option))


def reorder_nested_dict(option: dict[str, Any]) -> dict[str, Any]:
    return {k: reversed(v) for k, v in reversed(option.items())}


@pytest.mark.parametrize(
    'extra_option, reorder_function',
    [
        (["item1", "item2"], reorder_list_tuple),
        (("item1", "item2"), reorder_list_tuple),
        ({"key1": "item1", "key2": "item2"}, reorder_dict),
        ({"key1": {"key2": "item2", "key3": "item3"}}, reorder_nested_dict),
    ],
    ids=["list", "tuple", "dict", "nested_dict"],
)
def test_order_does_not_affect_key(
    config: dict[str, Any],
    instance: dict[str, Any],
    extra_option: list[str] | tuple[str, str] | dict[str, str] | dict[str, dict[str, str]],
    reorder_function: Callable,
):
    cache_key = ConfigSetCacheKey(build_check({}, {}), ["extra_option"])
    expected_key = str(hash(cache_key._ConfigSetCacheKey__sorted_values((extra_option,))))  # type: ignore

    instance['extra_option'] = reorder_function(extra_option)
    cache_key = ConfigSetCacheKey(build_check(config, instance), ["extra_option"])
    assert cache_key.base_key() == expected_key
