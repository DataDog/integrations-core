{license_header}from typing import Any, Dict

from datadog_checks.base import AgentCheck


class {check_class}(AgentCheck):
    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        pass
