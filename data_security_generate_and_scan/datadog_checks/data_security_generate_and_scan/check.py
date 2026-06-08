# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.base.agent import datadog_agent


class DataSecurityGenerateAndScanCheck(AgentCheck):

    # This will be the prefix of every metric the integration sends
    __NAMESPACE__ = 'data_security_generate_and_scan'

    def __init__(self, name, init_config, instances):
        super(DataSecurityGenerateAndScanCheck, self).__init__(name, init_config, instances)

        # Arbitrary JSON-serializable data to run through the Sensitive Data Scanner on every check run.
        self.data = (self.instance or {}).get('data')

    def check(self, _):
        # type: (Any) -> None
        matches = []
        if self.data is not None:
            value = self.data if isinstance(self.data, str) else json.dumps(self.data)
            result = datadog_agent.scan(value)
            if result:
                try:
                    parsed = json.loads(result)
                except (TypeError, ValueError):
                    self.log.debug("Could not parse scan result for %r: %r", value, result)
                    parsed = None
                if parsed:
                    matches.extend(parsed)

        self.event(
            {
                'source_type_name': self.__NAMESPACE__,
                'msg_title': 'Sensitive data scan matches',
                'msg_text': json.dumps(matches),
                'tags': (self.instance or {}).get('tags', []),
            }
        )
