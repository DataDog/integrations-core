# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

import pytest

from ddev.ai.callbacks._dispatch import dispatch


async def test_empty_handlers_is_noop() -> None:
    await dispatch([])


async def test_handler_receives_forwarded_args_with_identity() -> None:
    sentinel_a = object()
    sentinel_b = object()
    received: list[tuple[object, object]] = []

    async def handler(a: object, b: object) -> None:
        received.append((a, b))

    await dispatch([handler], sentinel_a, sentinel_b)

    assert len(received) == 1
    assert received[0][0] is sentinel_a
    assert received[0][1] is sentinel_b


async def test_multiple_handlers_fire_in_registration_order() -> None:
    order: list[int] = []

    async def first() -> None:
        order.append(1)

    async def second() -> None:
        order.append(2)

    async def third() -> None:
        order.append(3)

    await dispatch([first, second, third])

    assert order == [1, 2, 3]


async def test_exception_in_one_handler_is_swallowed_and_others_still_run() -> None:
    received: list[object] = []
    sentinel = object()

    async def bad(arg: object) -> None:
        raise RuntimeError("handler failure")

    async def good(arg: object) -> None:
        received.append(arg)

    await dispatch([bad, good], sentinel)

    assert len(received) == 1
    assert received[0] is sentinel


@pytest.mark.parametrize("exc_type", [KeyboardInterrupt, asyncio.CancelledError])
async def test_base_exception_propagates_out_of_dispatch(exc_type: type[BaseException]) -> None:
    async def raising_handler() -> None:
        raise exc_type()

    with pytest.raises(exc_type):
        await dispatch([raising_handler])
