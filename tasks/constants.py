# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os

# the root of the repo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Github API url
GITHUB_API_URL = 'https://api.github.com'

# The requirements file used by the agent
AGENT_REQ_FILE = 'requirements-agent-release.txt'

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'active_directory',
    'apache',
    'aspdotnet',
    'btrfs',
    'ceph',
    'consul',
    'couch',
    'couchbase',
    'datadog_checks_base',
    'directory',
    'disk',
    'dotnetclr',
    'elastic',
    'envoy',
    'exchange_server',
    'haproxy',
    'iis',
    'istio',
    'kafka_consumer',
    'kube_proxy',
    'kubelet',
    'kyototycoon',
    'lighttpd',
    'linkerd',
    'marathon',
    'mcache',
    'mysql',
    'network',
    'nfsstat',
    'nginx',
    'pdh_check',
    'pgbouncer',
    'postgres',
    'powerdns_recursor',
    'prometheus',
    'redisdb',
    'riak',
    'spark',
    'ssh_check',
    'system_core',
    'teamcity',
    'varnish',
    'vsphere',
]

AGENT_V5_ONLY = [
    'agent_metrics',
    'docker_daemon',
    'kubernetes',
    'ntp',
]
