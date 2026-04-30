"""Assign discovery_bucket to every analysis/integrations/*.json.

Buckets are explicit per-integration assignments based on the prior wave-1..5
analyses. Run once to back-fill the field; idempotent.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INT_DIR = ROOT / "analysis" / "integrations"

ASSIGNMENTS = {
    # generic-openmetrics-scan
    "aerospike": "generic-openmetrics-scan",
    "appgate_sdp": "generic-openmetrics-scan",
    "argo_rollouts": "generic-openmetrics-scan",
    "argo_workflows": "generic-openmetrics-scan",
    "argocd": "generic-openmetrics-scan",
    "aws_neuron": "generic-openmetrics-scan",
    "azure_iot_edge": "generic-openmetrics-scan",
    "bentoml": "generic-openmetrics-scan",
    "boundary": "generic-openmetrics-scan",
    "calico": "generic-openmetrics-scan",
    "celery": "generic-openmetrics-scan",
    "cert_manager": "generic-openmetrics-scan",
    "cilium": "generic-openmetrics-scan",
    "cockroachdb": "generic-openmetrics-scan",
    "coredns": "generic-openmetrics-scan",
    "crio": "generic-openmetrics-scan",
    "datadog_cluster_agent": "generic-openmetrics-scan",
    "datadog_csi_driver": "generic-openmetrics-scan",
    "dcgm": "generic-openmetrics-scan",
    "etcd": "generic-openmetrics-scan",
    "external_dns": "generic-openmetrics-scan",
    "falco": "generic-openmetrics-scan",
    "fluxcd": "generic-openmetrics-scan",
    "hugging_face_tgi": "generic-openmetrics-scan",
    "karpenter": "generic-openmetrics-scan",
    "keda": "generic-openmetrics-scan",
    "kong": "generic-openmetrics-scan",
    "krakend": "generic-openmetrics-scan",
    "kube_dns": "generic-openmetrics-scan",
    "kube_proxy": "generic-openmetrics-scan",
    "kubernetes_cluster_autoscaler": "generic-openmetrics-scan",
    "kubernetes_state": "generic-openmetrics-scan",
    "kuma": "generic-openmetrics-scan",
    "kyverno": "generic-openmetrics-scan",
    "linkerd": "generic-openmetrics-scan",
    "litellm": "generic-openmetrics-scan",
    "milvus": "generic-openmetrics-scan",
    "n8n": "generic-openmetrics-scan",
    "nginx_ingress_controller": "generic-openmetrics-scan",
    "nvidia_nim": "generic-openmetrics-scan",
    "nvidia_triton": "generic-openmetrics-scan",
    "pulsar": "generic-openmetrics-scan",
    "quarkus": "generic-openmetrics-scan",
    "ray": "generic-openmetrics-scan",
    "scylla": "generic-openmetrics-scan",
    "strimzi": "generic-openmetrics-scan",
    "teleport": "generic-openmetrics-scan",
    "temporal": "generic-openmetrics-scan",
    "velero": "generic-openmetrics-scan",
    "vllm": "generic-openmetrics-scan",
    "weaviate": "generic-openmetrics-scan",

    # generic-incluster-bearer-token
    "eks_fargate": "generic-incluster-bearer-token",
    "kube_apiserver_metrics": "generic-incluster-bearer-token",
    "kube_controller_manager": "generic-incluster-bearer-token",
    "kube_metrics_server": "generic-incluster-bearer-token",
    "kube_scheduler": "generic-incluster-bearer-token",
    "kubelet": "generic-incluster-bearer-token",
    "kubernetes_state_core": "generic-incluster-bearer-token",
    "kubevirt_api": "generic-incluster-bearer-token",
    "kubevirt_controller": "generic-incluster-bearer-token",
    "kubevirt_handler": "generic-incluster-bearer-token",

    # generic-windows-perf
    "active_directory": "generic-windows-perf",
    "aspdotnet": "generic-windows-perf",
    "dotnetclr": "generic-windows-perf",
    "exchange_server": "generic-windows-perf",
    "hyperv": "generic-windows-perf",
    "iis": "generic-windows-perf",

    # generic-linux-procfs
    "btrfs": "generic-linux-procfs",
    "disk": "generic-linux-procfs",
    "infiniband": "generic-linux-procfs",
    "linux_proc_extras": "generic-linux-procfs",
    "network": "generic-linux-procfs",
    "system_core": "generic-linux-procfs",
    "system_swap": "generic-linux-procfs",

    # http-text-format
    "apache": "http-text-format",
    "kyototycoon": "http-text-format",
    "lighttpd": "http-text-format",
    "squid": "http-text-format",

    # http-json-shape
    "consul": "http-json-shape",
    "fluentd": "http-json-shape",
    "hdfs_datanode": "http-json-shape",
    "hdfs_namenode": "http-json-shape",
    "mapreduce": "http-json-shape",
    "mesos_master": "http-json-shape",
    "mesos_slave": "http-json-shape",
    "riak": "http-json-shape",
    "traffic_server": "http-json-shape",
    "yarn": "http-json-shape",

    # http-multi-path
    "airflow": "http-multi-path",
    "couch": "http-multi-path",
    "druid": "http-multi-path",
    "elastic": "http-multi-path",
    "envoy": "http-multi-path",
    "gitlab": "http-multi-path",
    "gitlab_runner": "http-multi-path",
    "haproxy": "http-multi-path",
    "impala": "http-multi-path",
    "istio": "http-multi-path",
    "kubeflow": "http-multi-path",
    "marathon": "http-multi-path",
    "nginx": "http-multi-path",
    "php_fpm": "http-multi-path",
    "prefect": "http-multi-path",
    "rabbitmq": "http-multi-path",
    "spark": "http-multi-path",
    "supervisord": "http-multi-path",
    "tekton": "http-multi-path",
    "torchserve": "http-multi-path",
    "traefik_mesh": "http-multi-path",

    # tcp-banner-server-greets
    "twemproxy": "tcp-banner-server-greets",

    # tcp-protocol-handshake
    "gearmand": "tcp-protocol-handshake",
    "mcache": "tcp-protocol-handshake",
    "redisdb": "tcp-protocol-handshake",
    "statsd": "tcp-protocol-handshake",
    "zk": "tcp-protocol-handshake",

    # local-cli-binary
    "cassandra_nodetool": "local-cli-binary",
    "ceph": "local-cli-binary",
    "glusterfs": "local-cli-binary",
    "lparstats": "local-cli-binary",
    "lustre": "local-cli-binary",
    "nfsstat": "local-cli-binary",
    "postfix": "local-cli-binary",
    "slurm": "local-cli-binary",
    "tibco_ems": "local-cli-binary",
    "varnish": "local-cli-binary",

    # local-scm-enumeration
    "windows_service": "local-scm-enumeration",

    # cloud-task-metadata
    "ecs_fargate": "cloud-task-metadata",

    # local-config-file
    "duckdb": "local-config-file",
    "nagios": "local-config-file",

    # creds-spec-mandated
    "cacti": "creds-spec-mandated",
    "clickhouse": "creds-spec-mandated",
    "couchbase": "creds-spec-mandated",
    "do_query_actions": "creds-spec-mandated",
    "esxi": "creds-spec-mandated",
    "harbor": "creds-spec-mandated",
    "marklogic": "creds-spec-mandated",
    "mysql": "creds-spec-mandated",
    "openldap": "creds-spec-mandated",
    "pgbouncer": "creds-spec-mandated",
    "postgres": "creds-spec-mandated",
    "proxysql": "creds-spec-mandated",
    "rethinkdb": "creds-spec-mandated",
    "silverstripe_cms": "creds-spec-mandated",
    "singlestore": "creds-spec-mandated",
    "sonarqube": "creds-spec-mandated",
    "sonatype_nexus": "creds-spec-mandated",
    "sqlserver": "creds-spec-mandated",
    "ssh_check": "creds-spec-mandated",
    "teradata": "creds-spec-mandated",
    "tokumx": "creds-spec-mandated",
    "vertica": "creds-spec-mandated",
    "voltdb": "creds-spec-mandated",
    "vsphere": "creds-spec-mandated",

    # creds-jmx-rmi
    "activemq": "creds-jmx-rmi",
    "cassandra": "creds-jmx-rmi",
    "confluent_platform": "creds-jmx-rmi",
    "hazelcast": "creds-jmx-rmi",
    "hive": "creds-jmx-rmi",
    "hivemq": "creds-jmx-rmi",
    "hudi": "creds-jmx-rmi",
    "ignite": "creds-jmx-rmi",
    "jboss_wildfly": "creds-jmx-rmi",
    "kafka": "creds-jmx-rmi",
    "presto": "creds-jmx-rmi",
    "solr": "creds-jmx-rmi",
    "tomcat": "creds-jmx-rmi",
    "weblogic": "creds-jmx-rmi",

    # creds-api-token
    "amazon_msk": "creds-api-token",
    "ambari": "creds-api-token",
    "arangodb": "creds-api-token",
    "avi_vantage": "creds-api-token",
    "cisco_aci": "creds-api-token",
    "citrix_hypervisor": "creds-api-token",
    "cloud_foundry_api": "creds-api-token",
    "cloudera": "creds-api-token",
    "control_m": "creds-api-token",
    "fly_io": "creds-api-token",
    "ibm_was": "creds-api-token",
    "nifi": "creds-api-token",
    "nutanix": "creds-api-token",
    "octopus_deploy": "creds-api-token",
    "openstack": "creds-api-token",
    "openstack_controller": "creds-api-token",
    "powerdns_recursor": "creds-api-token",
    "proxmox": "creds-api-token",
    "riakcs": "creds-api-token",
    "silk": "creds-api-token",
    "snmp": "creds-api-token",
    "supabase": "creds-api-token",
    "teamcity": "creds-api-token",
    "twistlock": "creds-api-token",

    # creds-proprietary-client
    "foundationdb": "creds-proprietary-client",
    "ibm_ace": "creds-proprietary-client",
    "ibm_db2": "creds-proprietary-client",
    "ibm_i": "creds-proprietary-client",
    "ibm_mq": "creds-proprietary-client",
    "ibm_spectrum_lsf": "creds-proprietary-client",
    "mapr": "creds-proprietary-client",
    "oracle": "creds-proprietary-client",
    "sap_hana": "creds-proprietary-client",

    # creds-auth-optional-practical
    "activemq_xml": "creds-auth-optional-practical",
    "kafka_consumer": "creds-auth-optional-practical",
    "mongo": "creds-auth-optional-practical",
    "vault": "creds-auth-optional-practical",

    # logs-only
    "arctic_wolf_aurora_endpoint_security": "logs-only",
    "barracuda_secure_edge": "logs-only",
    "beyondtrust_password_safe": "logs-only",
    "beyondtrust_privileged_remote_access": "logs-only",
    "checkpoint_harmony_endpoint": "logs-only",
    "checkpoint_quantum_firewall": "logs-only",
    "cisco_asa": "logs-only",
    "cisco_secure_client": "logs-only",
    "cisco_secure_firewall": "logs-only",
    "cisco_secure_web_appliance": "logs-only",
    "cloudgen_firewall": "logs-only",
    "delinea_privilege_manager": "logs-only",
    "delinea_secret_server": "logs-only",
    "eset_protect": "logs-only",
    "flink": "logs-only",
    "forescout": "logs-only",
    "iboss": "logs-only",
    "ivanti_connect_secure": "logs-only",
    "journald": "logs-only",
    "juniper_srx_firewall": "logs-only",
    "keycloak": "logs-only",
    "linux_audit_logs": "logs-only",
    "mac_audit_logs": "logs-only",
    "microsoft_dns": "logs-only",
    "microsoft_sysmon": "logs-only",
    "openvpn": "logs-only",
    "ossec_security": "logs-only",
    "palo_alto_panorama": "logs-only",
    "pan_firewall": "logs-only",
    "ping_federate": "logs-only",
    "sonicwall_firewall": "logs-only",
    "suricata": "logs-only",
    "symantec_endpoint_protection": "logs-only",
    "tenable": "logs-only",
    "watchguard_firebox": "logs-only",
    "wazuh": "logs-only",
    "zeek": "logs-only",
    "zscaler_private_access": "logs-only",

    # dogstatsd-only
    "sidekiq": "dogstatsd-only",

    # user-schema-template
    "kafka_actions": "user-schema-template",
    "openmetrics": "user-schema-template",
    "pdh_check": "user-schema-template",
    "prometheus": "user-schema-template",
    "windows_performance_counters": "user-schema-template",
    "wmi_check": "user-schema-template",

    # user-intent-synthetic
    "directory": "user-intent-synthetic",
    "dns_check": "user-intent-synthetic",
    "http_check": "user-intent-synthetic",
    "tcp_check": "user-intent-synthetic",
    "tls": "user-intent-synthetic",
    "win32_event_log": "user-intent-synthetic",

    # per-process-discovery
    "go_expvar": "per-process-discovery",
    "go_metro": "per-process-discovery",
    "guarddog": "per-process-discovery",
    "gunicorn": "per-process-discovery",
    "process": "per-process-discovery",
}


def main():
    files = sorted(INT_DIR.glob("*.json"))
    missing = []
    updated = 0
    for f in files:
        rec = json.loads(f.read_text())
        bucket = ASSIGNMENTS.get(rec["name"])
        if bucket is None:
            missing.append(rec["name"])
            continue
        if rec.get("discovery_bucket") != bucket:
            rec["discovery_bucket"] = bucket
            f.write_text(json.dumps(rec, indent=2) + "\n")
            updated += 1
    print(f"updated {updated}/{len(files)} files")
    if missing:
        print(f"MISSING ({len(missing)}): {missing}")
        sys.exit(1)


if __name__ == "__main__":
    main()
