# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any


def initialize_instance(values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    if values.get('compression') == '':
        # An empty string historically meant "no compression". Normalize it to None so it
        # validates against the compression enum declared in the spec.
        values['compression'] = None

    return values
