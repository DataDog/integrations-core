# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common


def database_instance_resource_tags(hostname):
    return [f'dd.internal.resource:database_instance:{hostname}', f'database_hostname:{hostname}']


METRIC_TAGS = ['tag1:value1', 'tag2:value2']
METRIC_TAGS_WITH_RESOURCE = [
    'tag1:value1',
    'tag2:value2',
    *database_instance_resource_tags('stubbed.hostname'),
    'dbms_flavor:{}'.format(common.MYSQL_FLAVOR.lower()),
]
SC_TAGS = [
    'port:' + str(common.PORT),
    'tag1:value1',
    'tag2:value2',
]
SC_TAGS_MIN = [
    'port:' + str(common.PORT),
    *database_instance_resource_tags('stubbed.hostname'),
]
SC_TAGS_REPLICA = [
    'port:' + str(common.SLAVE_PORT),
    'tag1:value1',
    'tag2:value2',
    'dd.internal.resource:database_instance:stubbed.hostname',
    'database_hostname:stubbed.hostname',
]
SC_FAILURE_TAGS = [
    'port:unix_socket',
    *database_instance_resource_tags('stubbed.hostname'),
]
