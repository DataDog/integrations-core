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
        items = self.data if isinstance(self.data, list) else [self.data]
        for item in items:
            if item is None:
                continue
            value = item if isinstance(item, str) else json.dumps(item)
            result = datadog_agent.scan(value)
            if not result:
                continue
            try:
                parsed = json.loads(result)
            except (TypeError, ValueError):
                self.log.debug("Could not parse scan result for %r: %r", value, result)
                continue
            if parsed:
                matches.extend(parsed)

        # Wrap the JSON in %%% ... %%% so the Datadog event explorer renders it as
        # a Markdown ```json code block (https://app.datadoghq.com/event).
        msg_text = "%%%\n```json\n{}\n```\n%%%".format(json.dumps(matches, indent=2, sort_keys=True))

        self.event(
            {
                'source_type_name': self.__NAMESPACE__,
                'msg_title': 'Sensitive data scan matches',
                'msg_text': msg_text,
                'tags': (self.instance or {}).get('tags', []),
            }
        )
