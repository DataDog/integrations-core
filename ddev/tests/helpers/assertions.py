import asyncio
from unittest.mock import _Call, call

import pytest


async def assert_blocks(coro, timeout: float = 0.05) -> None:
    """Assert that a coroutine blocks without completing within the timeout."""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(coro, timeout=timeout)


def assert_calls(actual_calls: list[_Call], expected_calls: list[_Call], ignored_kwargs: list[str] | None = None):
    """
    Asserts that expected and actual calls are the same.

    Pass a list of argument names to `ignore_kwargs` to ignore them when comparing the calls.
    """
    ignored_set = set(ignored_kwargs) if ignored_kwargs else set()

    cleaned_actual_calls = []
    for single_call in actual_calls:
        cleaned_call = call(
            *single_call.args, **{key: value for key, value in single_call.kwargs.items() if key not in ignored_set}
        )
        cleaned_actual_calls.append(cleaned_call)

    cleaned_expected_calls = []
    for single_call in expected_calls:
        cleaned_call = call(
            *single_call.args, **{key: value for key, value in single_call.kwargs.items() if key not in ignored_set}
        )
        cleaned_expected_calls.append(cleaned_call)

    assert cleaned_actual_calls == cleaned_expected_calls
