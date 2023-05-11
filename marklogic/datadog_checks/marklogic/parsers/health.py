# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

from datadog_checks.base import AgentCheck

from ..constants import STATE_HEALTH_MAPPER


def parse_summary_health(data):
    # type: (Dict[str, Any]) -> Dict[str, Dict]
    raw_health_report = data['cluster-health-report']
    health_report = {
        'database': {},
        'forest': {},
    }  # type: Dict[str, Dict]

    for resource in raw_health_report:
        # This integration sends service checks for databases and forests only.
        res_type = resource['resource-type']
        res_name = resource['resource-name']
        if res_type == 'database' or res_type == 'forest':
            status_code = STATE_HEALTH_MAPPER.get(resource.get('state'), AgentCheck.UNKNOWN)
            message = '{} ({}): {}'.format(
                resource['code'], resource.get('state', 'unknown'), resource.get('message', 'No message.')
            )

            # A resource can have multiple health reports.
            # If a resource has 2 health report with different severity (e.g. one at 0 OK and the other at 1 WARNING)
            # we keep the higher severity.
            if health_report[res_type].get(res_name):
                health_report[res_type][res_name]['code'] = max(health_report[res_type][res_name]['code'], status_code)
                health_report[res_type][res_name]['message'] += ' ' + message
            else:
                health_report[res_type][res_name] = {
                    'code': status_code,
                    'message': message,
                }

    return health_report
