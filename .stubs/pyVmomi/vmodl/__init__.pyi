from typing import Any

from . import fault as fault
from . import query as query

class DynamicProperty:
    name: str
    val: Any
