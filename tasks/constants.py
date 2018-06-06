# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os

# the root of the repo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The requirements file used by the agent
AGENT_REQ_FILE = 'requirements-agent-release.txt'

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'active_directory',
    'activemq_xml',
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
    'hdfs_datanode',
    'hdfs_namenode',
    'http_check',
    'iis',
    'istio',
    'kafka_consumer',
    'kube_proxy',
    'kubelet',
    'kyototycoon',
    'lighttpd',
    'linkerd',
    'mapreduce',
    'marathon',
    'mcache',
    'mysql',
    'network',
    'nfsstat',
    'nginx',
    'openstack',
    'oracle',
    'pdh_check',
    'pgbouncer',
    'postgres',
    'powerdns_recursor',
    'prometheus',
    'redisdb',
    'riak',
    'spark',
    'ssh_check',
    'squid',
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
