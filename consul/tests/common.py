# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

PORT = '6379'
PASSWORD = 'devops-best-friend'
MASTER_PORT = '6382'
REPLICA_PORT = '6380'
UNHEALTHY_REPLICA_PORT = '6381'


HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')

HERE = os.path.dirname(os.path.abspath(__file__))
