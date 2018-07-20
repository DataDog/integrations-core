# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'
CHANGELOG_TYPES = [
    'Added',
    'Changed',
    'Deprecated',
    'Fixed',
    'Removed',
    'Security',
]

# The checks requirement file used by the agent
AGENT_REQ_FILE = 'requirements-agent-release.txt'


# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'active_directory',
    'activemq',
    'activemq_xml',
    'apache',
    'aspdotnet',
    'btrfs',
    'cacti',
    'cassandra',
    'cassandra_nodetool',
    'ceph',
    'cisco_aci',
    'consul',
    'couch',
    'couchbase',
    'datadog_checks_base',
    'datadog_checks_dev',
    'directory',
    'disk',
    'dns_check',
    'dotnetclr',
    'ecs_fargate',
    'elastic',
    'envoy',
    'etcd',
    'exchange_server',
    'fluentd',
    'gearmand',
    'gitlab',
    'gitlab_runner',
    'go_expvar',
    'gunicorn',
    'haproxy',
    'hdfs_datanode',
    'hdfs_namenode',
    'http_check',
    'iis',
    'istio',
    'kafka',
    'kafka_consumer',
    'kong',
    'kube_dns',
    'kube_proxy',
    'kubelet',
    'kubernetes_state',
    'kyototycoon',
    'lighttpd',
    'linkerd',
    'linux_proc_extras',
    'mapreduce',
    'marathon',
    'mcache',
    'mesos_master',
    'mesos_slave',
    'mongo',
    'mysql',
    'nagios',
    'network',
    'nfsstat',
    'nginx',
    'openldap',
    'openstack',
    'oracle',
    'pdh_check',
    'pgbouncer',
    'php_fpm',
    'postfix',
    'postgres',
    'powerdns_recursor',
    'process',
    'prometheus',
    'rabbitmq',
    'redisdb',
    'riak',
    'riakcs',
    'snmp',
    'solr',
    'spark',
    'ssh_check',
    'sqlserver',
    'squid',
    'statsd',
    'supervisord',
    'system_core',
    'system_swap',
    'tcp_check',
    'teamcity',
    'tokumx',
    'tomcat',
    'twemproxy',
    'varnish',
    'vault',
    'vsphere',
    'win32_event_log',
    'windows_service',
    'wmi_check',
    'yarn',
    'zk',
]

AGENT_V5_ONLY = [
    'agent_metrics',
    'docker_daemon',
    'kubernetes',
    'ntp',
]

# If a file changes in a PR with any of these file extensions,
# a test will run against the check containing the file
TESTABLE_FILE_EXTENSIONS = (
    '.py',
    '.ini',
    '.in',
    '.txt',
)


ROOT = ''


def get_root():
    return ROOT


def set_root(path):
    global ROOT
    ROOT = path
