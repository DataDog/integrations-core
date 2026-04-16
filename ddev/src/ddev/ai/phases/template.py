# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable, Mapping
from pathlib import Path
from string import Template
from typing import Any


class _SafeMapping(Mapping[str, str]):
    """Returns the resolver result or an UNDEFINED placeholder for missing keys instead of raising."""

    def __init__(self, context: dict[str, Any], resolver: Callable[[str], str] | None = None) -> None:
        self._context = context
        self._resolver = resolver

    def __getitem__(self, key: str) -> str:
        if key in self._context:
            return str(self._context[key])
        if self._resolver is not None:
            return self._resolver(key)
        return f"<VARIABLE UNDEFINED: {key}>"

    def __iter__(self):
        return iter(self._context)

    def __len__(self) -> int:
        return len(self._context)


def render_prompt(template_path: Path, context: dict[str, Any], resolver: Callable[[str], str] | None = None) -> str:
    """Render a template file with the given context."""
    return Template(template_path.read_text()).substitute(_SafeMapping(context, resolver))


def render_inline(prompt: str, context: dict[str, Any], resolver: Callable[[str], str] | None = None) -> str:
    """Render an inline prompt string with the given context."""
    return Template(prompt).substitute(_SafeMapping(context, resolver))
