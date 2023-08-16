# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck

# Events are queried from events endpoint and are filtered by
# only selecting values with timestamp greater than inputted value
# https://github.com/silk-us/silk-sdp-api-docs/blob/e6cccf93051419dd1603fa8cbe6b50d96bf13cc1/events.md
EVENT_PATH = "events?timestamp__gte={start_time}&timestamp__lt={end_time}"

# https://github.com/silk-us/silk-sdp-api-docs/blob/e6cccf93051419dd1603fa8cbe6b50d96bf13cc1/system/state.md
STATE_ENDPOINT = 'system/state'

# https://github.com/silk-us/silk-sdp-api-docs/blob/e6cccf93051419dd1603fa8cbe6b50d96bf13cc1/system/servers.md
SERVERS_ENDPOINT = 'system/servers'

STATE_MAP = {'online': ServiceCheck.OK, 'offline': ServiceCheck.WARNING, 'degraded': ServiceCheck.CRITICAL}

ALERT_TYPES = {"INFO": "info", "ERROR": "error", "WARNING": "warning", "CRITICAL": "error"}

OK_STATE = "ok"
