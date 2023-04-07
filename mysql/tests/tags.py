# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common

METRIC_TAGS = ['tag1:value1', 'tag2:value2']
METRIC_TAGS_WITH_RESOURCE = ['tag1:value1', 'tag2:value2', 'dd.internal.resource:database_instance:stubbed.hostname']
SC_TAGS = [
    'port:' + str(common.PORT),
    'tag1:value1',
    'tag2:value2',
    'dd.internal.resource:database_instance:stubbed.hostname',
]
SC_TAGS_MIN = ['port:' + str(common.PORT), 'dd.internal.resource:database_instance:stubbed.hostname']
SC_TAGS_REPLICA = [
    'port:' + str(common.SLAVE_PORT),
    'tag1:value1',
    'tag2:value2',
    'dd.internal.resource:database_instance:stubbed.hostname',
]
SC_FAILURE_TAGS = ['port:unix_socket', 'dd.internal.resource:database_instance:stubbed.hostname']
