# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import common

METRIC_TAGS = ['tag1', 'tag2']
SC_TAGS = ['server:' + common.HOST, 'port:' + str(common.PORT), 'tag1', 'tag2']
SC_TAGS_MIN = ['server:' + common.HOST, 'port:' + str(common.PORT)]
SC_TAGS_REPLICA = ['server:' + common.HOST, 'port:' + str(common.SLAVE_PORT), 'tag1', 'tag2']
SC_FAILURE_TAGS = ['server:' + common.HOST, 'port:unix_socket']
