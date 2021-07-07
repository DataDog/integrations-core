# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

DOGWEB_JSON_DASHBOARDS = {'hdfs_datanode', 'hdfs_namenode', 'mesos_master', 'mesos_slave'}
SECONDARY_DASHBOARDS = {
    'cassandra_nodetool',  # included in cassandra
    'kafka_consumer',  # included in kafka
    'openstack_controller',  # same as openstack
}
# Integrations that either do not emit metrics or have a too customer-specific setup to have an OOTBD
DASHBOARD_NOT_POSSIBLE = {
    'agent_metrics',  # Not for the end user
    'amazon_eks',  # collects metrics from Kubernetes, AWS, AWS EC2 integrations
    'go-metro',  # for agent 5 only
    'snmp',  # Too custom
    'openmetrics',  # No default metrics
    'pdh_check',  # No default metrics
    'prometheus',  # No default metrics
    'teamcity',  # No metrics
    'windows_service',  # No metrics
    'win32_event_log',  # No metrics
    'wmi_check',  # No default metrics
    'windows_service',  # No metrics
    'cloud_foundry_api',  # only one standard metric
    'dns_check',  # only one standard metric
    'docker_daemon',  # agent 5 only
    'gke',  # does not emit metrics
    'ntp',  # only one standard metric
    'pivotal_pks',  # does not emit metrics
    'ssh_check',  # only one standard metric
    'supervisord',  # only two standard metrics
    'system_swap',  # only two standard metrics
    'tcp_queue_length',  # only two standard metrics
    'tenable',  # does not emit metrics
    'terraform',  # does not emit metrics
}


# List of integrations where is not possible or it does not make sense to have its own log integration
INTEGRATION_LOGS_NOT_POSSIBLE = {
    'btrfs',  # it emits to the system log
    'datadog_checks_base',
    'datadog_checks_dev',
    'datadog_checks_downloader',
    'directory',  # OS
    'dns_check',  # not a specific service
    'dotnetclr',  # No relevant logs
    'external_dns',  # remote connection
    'go-metro',  # for agent 5 only
    'go_expvar',  # its a go package
    'http_check',  # Its not a service
    'linux_proc_extras',
    'ntp',  # the integration is for a remote ntp server
    'openmetrics',  # base class
    'oracle',  # TODO: requires submitting logs via agent
    'pdh_check',  # base class
    'process',  # system
    'prometheus',  # base class
    'riakcs',  # would require installing agent on each node
    'sap_hana',  # see open questions in the architecture rfc
    'snmp',  # remote connection to the devices
    'snowflake',  # No logs to parse, needs to be from QUERY_HISTORY view
    'ssh_check',  # remote connection
    'system_core',  # system
    'system_swap',  # system
    'tcp_check',  # remote connection
    'tls',  # remote connection
    'tokumx',  # eoled, only available in py2
    'windows_service',  # OS
    'wmi_check',  # base class
}


INTEGRATION_REC_MONITORS_NOT_POSSIBLE = {
    'go-metro',  # agent 5 only
}

PROCESS_SIGNATURE_EXCLUDE = {
    'datadog_checks_base',
    'datadog_checks_dev',
    'datadog_checks_downloader',
    'snowflake',
    'go-metro',
}
