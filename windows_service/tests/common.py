# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
INSTANCE_BASIC = {'services': ['eventlog', 'Dnscache', 'NonExistentService'], 'tags': ['optional:tag1']}
INSTANCE_BASIC_DICT = {
    'services': [
        {'name': 'eventlog'},
        {'name': 'Dnscache'},
        {'name': 'NonExistentService'},
    ],
    'tags': ['optional:tag1'],
    'disable_legacy_service_tag': True,
}
INSTANCE_BASIC_DISABLE_SERVICE_TAG = {
    'services': ['eventlog', 'Dnscache', 'NonExistentService'],
    'tags': ['optional:tag1'],
    'disable_legacy_service_tag': True,
}
INSTANCE_STARTUP_TYPE_FILTER = {
    'windows_service_startup_type_tag': True,
    'disable_legacy_service_tag': True,
}
INSTANCE_WILDCARD = {'host': '.', 'services': ['Event.*', 'Dns%']}
INSTANCE_WILDCARD_DICT = {
    'host': '.',
    'services': [
        {'name': 'Event.*'},
        {'name': 'Dns%'},
    ],
    'disable_legacy_service_tag': True,
}
INSTANCE_ALL = {'services': ['ALL']}
INSTANCE_PREFIX_MATCH = {
    'services': [
        # Include a non-name filter that should match to test that it isn't
        # responsible for the match.
        {'startup_type': 'automatic'},
        # Intentionally use different letter cases to test the sorting
        'event',
        # The more specific filters should come last so our check must
        # do something to ensure they are responsible for the match.
        'EventLog',
        'EventSystem',
    ],
    'disable_legacy_service_tag': True,
}
INSTANCE_TRIGGER_START = {
    'services': [
        {'name': 'eventlog', 'startup_type': 'automatic', 'trigger_start': False},
        {'name': 'dnscache', 'startup_type': 'automatic', 'trigger_start': False},
    ],
    'tags': ['optional:tag1'],
    'disable_legacy_service_tag': True,
}
