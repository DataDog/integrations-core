# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, Generator, List, Tuple

from datadog_checks.base import AgentCheck

from ..constants import STATUS_CODE_HEALTH


def parse_summary_health(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    health_report = data['cluster-health-report']

    for resource in health_report:
        if resource['resource-type'] == 'database':
            status_code = STATUS_CODE_HEALTH.get(resource['code'], AgentCheck.UNKNOWN)
            resource_tags = tags + ['database_name:{}'.format(resource['resource-name'])]
            message = '{}: {}'.format(resource['code'], resource.get('message', 'No message.'))
            yield ('database.health', status_code, message, resource_tags)
