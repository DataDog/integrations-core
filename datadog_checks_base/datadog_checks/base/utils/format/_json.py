# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

try:
    import orjson

    logger.debug('Using JSON implementation from orjson')

    def decode(s: str | bytes) -> Any:
        return orjson.loads(s)

    def encode(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> str:
        return encode_bytes(obj, sort_keys=sort_keys, default=default).decode()

    def encode_bytes(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> bytes:
        if sort_keys:
            return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS, default=default)

        return orjson.dumps(obj, default=default)

except ImportError:
    import json

    logger.debug('Using JSON implementation from stdlib')

    def decode(s: str | bytes) -> Any:
        return json.loads(s)

    def encode(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> str:
        return json.dumps(obj, sort_keys=sort_keys, separators=(',', ':'), default=default)

    def encode_bytes(obj: Any, *, sort_keys: bool = False, default: Callable[[Any], Any] | None = None) -> bytes:
        return encode(obj, sort_keys=sort_keys, default=default).encode()
