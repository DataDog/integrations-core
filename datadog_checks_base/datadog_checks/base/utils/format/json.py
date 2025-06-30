# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import lazy_loader

if TYPE_CHECKING:
    from collections.abc import Callable

    from datadog_checks.base.utils.format import _json

with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='lazy_loader')
    json: _json = lazy_loader.load('datadog_checks.base.utils.format._json')


def decode(s: str | bytes) -> Any:
    return json.decode(s)


def encode(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> str:
    return json.encode(obj, sort_keys=sort_keys, default=default)


def encode_bytes(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> bytes:
    return json.encode_bytes(obj, sort_keys=sort_keys, default=default)
