# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

FLUENTD_VERSION = os.environ.get('FLUENTD_VERSION')
FLUENTD_IMAGE_TAG = os.environ.get('FLUENTD_IMAGE_TAG')
FLUENTD_CONTAINER_NAME = 'dd-test-fluentd'

HOST = get_docker_hostname()
PORT = 24220
BAD_PORT = 24222

URL = "http://{}:{}/api/plugins.json".format(HOST, PORT)
BAD_URL = "http://{}:{}/api/plugins.json".format(HOST, BAD_PORT)

CHECK_NAME = 'fluentd'

DEFAULT_INSTANCE = {"monitor_agent_url": URL}
INSTANCE_WITH_PLUGIN = {"monitor_agent_url": URL, "plugin_ids": "plg1"}

EXPECTED_GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']
