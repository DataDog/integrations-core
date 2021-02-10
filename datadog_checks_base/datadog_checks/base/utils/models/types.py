# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Mapping, Sequence

from immutables import Map


def make_immutable_check_config(obj):
    if isinstance(obj, Sequence) and not isinstance(obj, str):
        return tuple(make_immutable_check_config(item) for item in obj)
    elif isinstance(obj, Mapping):
        # There are no ordering guarantees, see https://github.com/MagicStack/immutables/issues/57
        return Map((k, make_immutable_check_config(v)) for k, v in obj.items())

    return obj
