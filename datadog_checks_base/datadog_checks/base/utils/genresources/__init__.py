# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .inclusion import INCLUDE_ALL, apply_allow_list, find_invalid_include
from .proto.genericresource_pb2 import GenericResource, GenericResourceEvent

GENRESOURCES_TRACK = "genresources"
INTEGRATIONS_CORE_SOURCE = "integrations-core"
MAX_FIELDS_JSON_BYTES = 1_000_000

__all__ = [
    "GENRESOURCES_TRACK",
    "INCLUDE_ALL",
    "INTEGRATIONS_CORE_SOURCE",
    "MAX_FIELDS_JSON_BYTES",
    "GenericResource",
    "GenericResourceEvent",
    "apply_allow_list",
    "find_invalid_include",
]
