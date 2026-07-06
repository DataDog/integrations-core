# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

import pytest
from pydantic import BaseModel, Field, ValidationError

from ddev.ai.tools.core.validation import format_validation_error


class Item(BaseModel):
    name: Annotated[str, Field(pattern=r"^[a-z]+$")]


class Model(BaseModel):
    items: Annotated[list[Item], Field(min_length=1)]
    count: Annotated[int, Field(ge=1)] = 1


def test_single_error_header_and_line():
    with pytest.raises(ValidationError) as exc_info:
        Model(items=[{"name": "ok"}], count=0)
    msg = format_validation_error(exc_info.value)
    assert msg.startswith("1 validation error:\n")


def test_plural_header_counts_all_errors():
    with pytest.raises(ValidationError) as exc_info:
        Model(items=[{"name": "BAD"}], count=0)
    msg = format_validation_error(exc_info.value)
    assert msg.startswith("2 validation errors:\n")


def test_no_pydantic_docs_url():
    with pytest.raises(ValidationError) as exc_info:
        Model(items=[{"name": "BAD"}], count=0)
    msg = format_validation_error(exc_info.value)
    assert "errors.pydantic.dev" not in msg
    assert "https://" not in msg


def test_does_not_echo_offending_input():
    with pytest.raises(ValidationError) as exc_info:
        Model(items=[{"name": "BAD_VALUE_123"}], count=1)
    msg = format_validation_error(exc_info.value)
    assert "BAD_VALUE_123" not in msg


@pytest.mark.parametrize(
    "kwargs, expected_loc",
    [
        ({"items": [{"name": "ok"}], "count": 0}, "count"),
        ({"items": [], "count": 1}, "items"),
        ({"items": [{"name": "BAD"}], "count": 1}, "items[0].name"),
    ],
)
def test_loc_paths(kwargs, expected_loc):
    with pytest.raises(ValidationError) as exc_info:
        Model(**kwargs)
    msg = format_validation_error(exc_info.value)
    assert f"- {expected_loc}: " in msg
