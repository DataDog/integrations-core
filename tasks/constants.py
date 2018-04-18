# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os

# the root of the repo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'active_directory',
    'apache',
    'aspdotnet',
    'btrfs',
    'datadog_checks_base',
    'directory',
    'disk',
    'envoy',
    'iis',
    'istio',
    'kafka_consumer',
    'kube_proxy',
    'kubelet',
    'lighttpd',
    'linkerd',
    'mcache',
    'network',
    'nfsstat',
    'pdh_check',
    'postgres',
    'powerdns_recursor',
    'prometheus',
    'redisdb',
    'riak',
    'spark',
    'ssh_check',
    'system_core',
    'teamcity',
    'vsphere',
]
