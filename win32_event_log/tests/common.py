# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
EVENT_SOURCE = 'DatadogTest'
EVENT_ID = 9000
EVENT_CATEGORY = 42

INSTANCE = {
    'legacy_mode_v2': True,
    'timeout': 2,
    'path': 'Application',
    'filters': {'source': [EVENT_SOURCE]},
}
