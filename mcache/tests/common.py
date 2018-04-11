# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
USERNAME = 'testuser'
PASSWORD = 'testpass'
