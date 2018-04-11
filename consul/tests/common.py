# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

PORT = '8500'
HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')

URL = "http://{0}:{1}".format(HOST, PORT)

CHECK_NAME = 'consul'

HERE = os.path.dirname(os.path.abspath(__file__))
