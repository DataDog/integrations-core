# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = "elastic"

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "elastic"
PASSWORD = "changeme"
HOST = get_docker_hostname()
PORT = '9200'
BAD_PORT = '9405'
CONF_HOSTNAME = "foo"
TAGS = [u"foo:bar", u"baz"]
CLUSTER_TAG = [u"cluster_name:elasticsearch"]
URL = 'http://{0}:{1}'.format(HOST, PORT)
BAD_URL = 'http://{0}:{1}'.format(HOST, BAD_PORT)

CONFIG = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': TAGS}
BAD_CONFIG = {'url': BAD_URL, 'password': PASSWORD}
