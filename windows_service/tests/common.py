# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
INSTANCE_BASIC = {'services': ['eventlog', 'Dnscache', 'NonExistentService'], 'tags': ['optional:tag1']}
INSTANCE_BASIC_DISABLE_SERVICE_TAG = {
    'services': ['eventlog', 'Dnscache', 'NonExistentService'],
    'tags': ['optional:tag1'],
    'disable_legacy_service_tag': True,
}
INSTANCE_WILDCARD = {'host': '.', 'services': ['Event.*', 'Dns%']}
INSTANCE_ALL = {'services': ['ALL']}
