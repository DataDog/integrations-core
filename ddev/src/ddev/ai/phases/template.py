# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Callable, Iterator, Mapping
from string import Template
from typing import Any


class _FlowTemplate(Template):
    braceidpattern = rf"{Template.idpattern}(?:\.{Template.idpattern})?"


class _SafeMapping(Mapping[str, str]):
    """Returns the resolver result or an UNDEFINED placeholder for missing keys instead of raising."""

    def __init__(self, context: dict[str, Any], resolver: Callable[[str], str] | None = None) -> None:
        self._context = context
        self._resolver = resolver

    def __getitem__(self, key: str) -> str:
        if "." in key:
            object_name, field_name = key.split(".", 1)
            if object_name not in self._context:
                raise ValueError(f"Object variable {object_name!r} is missing")
            value = self._context[object_name]
            if not isinstance(value, Mapping):
                raise ValueError(f"Variable {object_name!r} is not an object")
            if field_name not in value:
                raise ValueError(f"Object field {key!r} is missing")
            return str(value[field_name])
        if key in self._context:
            value = self._context[key]
            if isinstance(value, Mapping):
                return json.dumps(dict(value), separators=(",", ":"), ensure_ascii=False)
            return str(value)
        if self._resolver is not None:
            return self._resolver(key)
        return f"<VARIABLE UNDEFINED: {key}>"

    def __iter__(self) -> Iterator[str]:
        return iter(self._context)

    def __len__(self) -> int:
        return len(self._context)


def render_inline(prompt: str, context: dict[str, Any], resolver: Callable[[str], str] | None = None) -> str:
    """Render an inline prompt string with the given context."""
    return _FlowTemplate(prompt).substitute(_SafeMapping(context, resolver))
