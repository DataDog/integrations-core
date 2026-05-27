# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tiny stand-in for ``pytest.MonkeyPatch`` so adapter modules can import it.

The Agent's embedded Python does not ship pytest, but the existing no-Agent
replay adapters take a ``pytest.MonkeyPatch`` instance and call only
``.setattr``. We expose the same interface here without pulling pytest into
the Agent artifact (and without distorting the artifact-membership oracle
the Tier 3 work exists to feed).
"""

from __future__ import annotations

import importlib
from typing import Any

_SENTINEL = object()


class MonkeyPatch:
    """Subset of ``pytest.MonkeyPatch`` needed by the replay adapters."""

    def __init__(self) -> None:
        self._undo: list[tuple[Any, str, Any]] = []

    def setattr(
        self,
        target: Any,
        name: Any = _SENTINEL,
        value: Any = _SENTINEL,
        raising: bool = True,
    ) -> None:
        """Replicate the two ``pytest.MonkeyPatch.setattr`` call shapes.

        - ``setattr(module_obj, "attr", value)``
        - ``setattr("module.path.attr", value)``
        """

        if isinstance(target, str):
            if value is _SENTINEL:
                value = name
                name = _SENTINEL
            modpath, _, attr = target.rpartition('.')
            obj = importlib.import_module(modpath) if modpath else __import__('builtins')
            name = attr
        else:
            if name is _SENTINEL or value is _SENTINEL:
                raise TypeError('setattr requires an attribute name and value')
            obj = target

        if raising and not hasattr(obj, name):
            raise AttributeError(f'{obj!r} has no attribute {name!r}')

        old = getattr(obj, name, _SENTINEL)
        setattr(obj, name, value)
        self._undo.append((obj, name, old))

    def undo(self) -> None:
        while self._undo:
            obj, name, old = self._undo.pop()
            if old is _SENTINEL:
                try:
                    delattr(obj, name)
                except AttributeError:
                    pass
            else:
                setattr(obj, name, old)
