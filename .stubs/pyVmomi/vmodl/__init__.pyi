from typing import Any

from . import (
    fault,  # noqa: F401
    query,  # noqa: F401
)

class DynamicProperty:
    name: str
    val: Any
