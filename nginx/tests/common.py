# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

CHECK_NAME = 'nginx'

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')

HOST = get_docker_hostname()
PORT = '8080'
PORT_SSL = '8081'
TAGS = ['foo:foo', 'bar:bar']
USING_VTS = os.getenv('NGINX_IMAGE', '').endswith('nginx-vts')
USING_LATEST = os.getenv('NGINX_IMAGE', '').endswith('latest')
NGINX_VERSION = os.getenv('NGINX_VERSION', os.environ.get('NGINX_IMAGE'))
