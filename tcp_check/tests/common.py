# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CHECK_NAME = "tcp_check"

INSTANCE = {'host': 'datadoghq.com', 'port': 80, 'timeout': 1.5, 'name': 'UpService', 'tags': ["foo:bar"]}

INSTANCE_KO = {'host': '127.0.0.1', 'port': 65530, 'timeout': 1.5, 'name': 'DownService', 'tags': ["foo:bar"]}
