# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common

METRIC_TAGS = ['tag1', 'tag2']
SC_TAGS = ['server:' + common.HOST, 'port:' + str(common.PORT), 'tag1', 'tag2']
SC_TAGS_MIN = ['server:' + common.HOST, 'port:' + str(common.PORT)]
SC_TAGS_REPLICA = ['server:' + common.HOST, 'port:' + str(common.SLAVE_PORT), 'tag1', 'tag2']
SC_FAILURE_TAGS = ['server:' + common.HOST, 'port:unix_socket']
