# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common

METRIC_TAGS = ['tag1:value1', 'tag2:value2']
SC_TAGS = ['mysql_port:' + str(common.PORT), 'tag1:value1', 'tag2:value2']
SC_TAGS_MIN = ['mysql_port:' + str(common.PORT)]
SC_TAGS_REPLICA = ['mysql_port:' + str(common.SLAVE_PORT), 'tag1:value1', 'tag2:value2']
SC_FAILURE_TAGS = ['mysql_port:unix_socket']
