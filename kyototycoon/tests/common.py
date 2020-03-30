# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os.path

from datadog_checks.base.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT = '1978'

URL = 'http://{}:{}'.format(HOST, PORT)

HERE = os.path.dirname(os.path.abspath(__file__))

TAGS = ['optional:tag1']

DEFAULT_INSTANCE = {'report_url': '{}/rpc/report'.format(URL), 'tags': TAGS}
