# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Mapping, Sequence


def copy_raw(obj):
    if isinstance(obj, Sequence) and not isinstance(obj, str):
        return [copy_raw(item) for item in obj]
    elif isinstance(obj, Mapping):
        return {k: copy_raw(v) for k, v in obj.items()}

    return obj
