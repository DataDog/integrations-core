# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any


def initialize_config(values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    # This is what is returned by the initial model validator of each config model.
    return values


def check_model(model: Any, **kwargs: Any) -> Any:
    # This is what is returned by the final model validator of each config model.
    return model
