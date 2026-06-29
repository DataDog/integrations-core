# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Base class for kafka_actions format handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FormatHandler(ABC):
    """Plug-in interface for message-body deserialization.

    Subclasses are instantiated once and reused across messages, so they
    should be stateless or maintain only thread-safe caches.
    """

    name: str = ''

    def build_schema(self, schema_str: str) -> Any:
        """Build a schema object from an inline (config-supplied) schema string.

        Override for formats that need a parsed schema (e.g. Avro, Protobuf).
        Schemaless formats (json, msgpack, raw) can leave the default.
        """
        return None

    def build_schema_from_registry(self, schema_str: str, dep_schemas: list) -> Any:
        """Build a schema object from registry-supplied bytes.

        ``dep_schemas`` is a list of ``(name, base64_bytes)`` tuples for
        dependencies (e.g. imported .proto files).

        Defaults to :meth:`build_schema` for formats that don't distinguish.
        """
        return self.build_schema(schema_str)

    @abstractmethod
    def deserialize(self, message: bytes, schema: Any, *, log, uses_schema_registry: bool) -> str | None:
        """Decode ``message`` and return a JSON string (or None for empty messages)."""
        raise NotImplementedError
