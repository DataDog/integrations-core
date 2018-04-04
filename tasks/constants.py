# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os


ROOT = os.path.dirname(os.path.abspath(__file__))

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'apache',
    'datadog-checks-base',
    'disk',
    'directory',
    'envoy',
    'istio',
    'kube_proxy',
    'kubelet',
    'linkerd',
    'nfsstat',
    'prometheus',
    'redisdb',
    'spark',
    'vsphere',
    'postgres',
]
