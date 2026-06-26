# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from pydantic import ValidationError

from ddev.ai.accounting.tokens import Tokens
from ddev.ai.agent.types import TokenUsage


def test_default_is_zero():
    assert Tokens() == Tokens(input=0, output=0, cache_read=0, cache_creation=0)


def test_add_sums_every_field():
    a = Tokens(input=1, output=2, cache_read=3, cache_creation=4)
    b = Tokens(input=10, output=20, cache_read=30, cache_creation=40)
    assert a + b == Tokens(input=11, output=22, cache_read=33, cache_creation=44)


def test_addition_is_commutative_and_associative():
    a = Tokens(input=1, output=2, cache_read=3, cache_creation=4)
    b = Tokens(input=5, output=6, cache_read=7, cache_creation=8)
    c = Tokens(input=9, output=10, cache_read=11, cache_creation=12)
    assert a + b == b + a
    assert (a + b) + c == a + (b + c)


def test_is_frozen():
    a = Tokens(input=1)
    with pytest.raises(ValidationError):
        a.input = 2


def test_from_usage_maps_all_four_fields():
    usage = TokenUsage(
        input_tokens=5,
        output_tokens=6,
        cache_read_input_tokens=7,
        cache_creation_input_tokens=8,
    )
    assert usage.to_tokens() == Tokens(input=5, output=6, cache_read=7, cache_creation=8)
