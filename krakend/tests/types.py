# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Protocol


# Type alias for instance builder function
class InstanceBuilder(Protocol):
    def __call__(self, go_metrics=True, process_metrics=True, host="localhost", port=9090) -> dict[str, Any]: ...
