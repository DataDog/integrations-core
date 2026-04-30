_Generated 2026-04-30. 260 total: 96 generic / 40 custom / 124 impossible / 2 need review (⚠)._

**Sections:** [Fully generic](#fully-generic) · [HTTP probe with integration-specific verification](#http-probe-with-integration-specific-verification) · [TCP probe with integration-specific protocol](#tcp-probe-with-integration-specific-protocol) · [Local detection (no network, no credentials)](#local-detection-no-network-no-credentials) · [Credentials required](#credentials-required) · [No probe surface](#no-probe-surface)

## Fully generic

_No integration-specific verification code; the discovery layer carries at most a per-integration port + path table._

### `generic-openmetrics-scan` (51)

Probe a port for `/metrics`, validate Prometheus exposition format. Per-integration data is just port + path.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Aerospike (`aerospike`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Appgate SDP (`appgate_sdp`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Argo Rollouts (`argo_rollouts`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Argo Workflows (`argo_workflows`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| ArgoCD (`argocd`) | — | openmetrics-port-scan | high |
| AWS Neuron (`aws_neuron`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Azure IoT Edge (`azure_iot_edge`) | `edge_hub_prometheus_url`, `edge_agent_prometheus_url` | openmetrics-port-scan | high |
| BentoML (`bentoml`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Boundary (`boundary`) | `health_endpoint`, `openmetrics_endpoint` | openmetrics-port-scan | high |
| Calico (`calico`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Celery (`celery`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| cert-manager (`cert_manager`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Cilium (`cilium`) | `agent_endpoint` | openmetrics-port-scan | high |
| CockroachDB (`cockroachdb`) | — | openmetrics-port-scan | high |
| CoreDNS (`coredns`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| CRI-O (`crio`) | `prometheus_url` | openmetrics-port-scan | high |
| Datadog Cluster Agent (`datadog_cluster_agent`) | `prometheus_url` | openmetrics-port-scan | high |
| Datadog CSI Driver (`datadog_csi_driver`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| NVIDIA DCGM (`dcgm`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| etcd (`etcd`) | `prometheus_url` | openmetrics-port-scan | high |
| External DNS (`external_dns`) | `prometheus_url` | openmetrics-port-scan | high |
| Falco (`falco`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Flux (`fluxcd`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Hugging Face TGI (`hugging_face_tgi`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Karpenter (`karpenter`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| KEDA (`keda`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kong (`kong`) | — | openmetrics-port-scan | high |
| KrakenD (`krakend`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kube DNS (`kube_dns`) | `prometheus_endpoint` | openmetrics-port-scan | high |
| Kube Proxy (`kube_proxy`) | `prometheus_url` | openmetrics-port-scan | high |
| Kubernetes Cluster Autoscaler (`kubernetes_cluster_autoscaler`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kubernetes State (`kubernetes_state`) | `kube_state_url` | openmetrics-port-scan | high |
| Kuma (`kuma`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kyverno (`kyverno`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Linkerd (`linkerd`) | — | openmetrics-port-scan | high |
| LiteLLM (`litellm`) | — | openmetrics-port-scan | high |
| Milvus (`milvus`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| n8n (`n8n`) | `openmetrics_endpoint` | openmetrics-port-scan | medium |
| NGINX Ingress Controller (`nginx_ingress_controller`) | `prometheus_url` | openmetrics-port-scan | high |
| NVIDIA NIM (`nvidia_nim`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| NVIDIA Triton (`nvidia_triton`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Pulsar (`pulsar`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Quarkus (`quarkus`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Ray (`ray`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Scylla (`scylla`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Strimzi (`strimzi`) | — | openmetrics-port-scan | medium |
| Teleport (`teleport`) | `teleport_url` | openmetrics-port-scan | high |
| Temporal (`temporal`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Velero (`velero`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| vLLM (`vllm`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Weaviate (`weaviate`) | `openmetrics_endpoint` | openmetrics-port-scan | high |

### `generic-incluster-bearer-token` (10)

Same as openmetrics-scan but the Agent's pod ServiceAccount token is auto-injected for HTTPS+auth endpoints. Per-integration data is just port + path.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| EKS Fargate (`eks_fargate`) | — | other | high |
| Kubernetes API server metrics (`kube_apiserver_metrics`) | `prometheus_url` | openmetrics-port-scan | high |
| Kubernetes Controller Manager (`kube_controller_manager`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube metrics server (`kube_metrics_server`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube Scheduler (`kube_scheduler`) | `prometheus_url` | http-path-probe | high |
| Kubelet (`kubelet`) | — | other | high |
| Kubernetes State Core (`kubernetes_state_core`) | — | other | high |
| KubeVirt API (`kubevirt_api`) | `kubevirt_api_metrics_endpoint` | openmetrics-port-scan | medium |
| KubeVirt Controller (`kubevirt_controller`) | `kubevirt_controller_metrics_endpoint` | openmetrics-port-scan | high |
| KubeVirt Handler (`kubevirt_handler`) | `kubevirt_handler_metrics_endpoint` | openmetrics-port-scan | high |

### `generic-windows-perf` (6)

Detect a PDH counter set on the local Windows host (e.g. `IIS`, `MSExchange*`). Per-integration data is the counter set name + counter list.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Active Directory (`active_directory`) | — | other | high |
| ASP.NET (`aspdotnet`) | — | other | medium |
| .NET CLR (`dotnetclr`) | — | other | medium |
| Exchange Server (`exchange_server`) | — | other | high |
| Hyper-V (`hyperv`) | — | other | high |
| IIS (`iis`) | — | other | medium |

### `generic-linux-procfs` (7)

Read host-local files under `/proc` or `/sys`. Per-integration data is just the file paths.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Btrfs (`btrfs`) | — | other | high |
| Disk (`disk`) | — | other | high |
| Infiniband (`infiniband`) | — | other | high |
| Linux Proc Extras (`linux_proc_extras`) | — | other | high |
| Network (`network`) | — | other | high |
| System Core (`system_core`) | — | other | high |
| System Swap (`system_swap`) | — | other | high |

## HTTP probe with integration-specific verification

_Fixed URL on a known port, but the discovery layer needs integration-specific verification code (more than just "is this Prometheus exposition format?") to confirm the target._

### `http-text-format` (4)

Fixed URL, integration-specific text/HTML format (e.g. apache mod_status, squid Cache Manager `key = value`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Apache (`apache`) | `apache_status_url` | http-path-probe | high |
| Kyoto Tycoon (`kyototycoon`) | `report_url` | http-path-probe | high |
| Lighttpd (`lighttpd`) | `lighttpd_status_url` | http-path-probe | high |
| Squid (`squid`) | `name` | http-path-probe | high |

### `http-json-shape` (10)

Fixed URL, JSON shape verification with integration-specific keys (e.g. `version`+`cluster` for mesos master, `id`+`frameworks` for mesos slave).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Consul (`consul`) | `url` | http-path-probe | medium |
| Fluentd (`fluentd`) | `monitor_agent_url` | http-path-probe | high |
| HDFS Datanode (`hdfs_datanode`) | `hdfs_datanode_jmx_uri` | http-path-probe | high |
| HDFS Namenode (`hdfs_namenode`) | `hdfs_namenode_jmx_uri` | http-path-probe | high |
| MapReduce (`mapreduce`) | `resourcemanager_uri`, `cluster_name` | http-path-probe | high |
| Mesos Master (`mesos_master`) | `url` | http-path-probe | high |
| Mesos Slave (`mesos_slave`) | `url` | http-path-probe | high |
| Riak (`riak`) | `url` | http-path-probe | high |
| Traffic Server (`traffic_server`) | `traffic_server_url` | http-path-probe | high |
| YARN (`yarn`) | `resourcemanager_uri` | http-path-probe | high |

### `http-multi-path` (21)

Try several plausible paths or modes per integration (e.g. nginx stub_status / Plus API / VTS; rabbitmq Prometheus + management plugin).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Airflow (`airflow`) | `url` | http-path-probe | medium |
| CouchDB (`couch`) | `server` | http-path-probe | medium |
| Druid (`druid`) | `url` | http-path-probe | medium |
| Elasticsearch (`elastic`) | `url` | http-path-probe | medium |
| Envoy (`envoy`) | — | http-path-probe | medium |
| GitLab (`gitlab`) | — | http-path-probe | medium |
| GitLab Runner (`gitlab_runner`) | `gitlab_url`, `prometheus_endpoint`, `allowed_metrics` | openmetrics-port-scan | medium |
| HAProxy (`haproxy`) | — | http-path-probe | medium |
| Impala (`impala`) | `service_type`, `openmetrics_endpoint` | http-path-probe | high |
| Istio (`istio`) | — | http-path-probe | medium |
| Kubeflow (`kubeflow`) | `openmetrics_endpoint` | http-path-probe | medium |
| Marathon (`marathon`) | `url` | http-path-probe | medium |
| NGINX (`nginx`) | `nginx_status_url` | http-path-probe | high |
| PHP-FPM (`php_fpm`) | `status_url` | http-path-probe | medium |
| Prefect (`prefect`) | `prefect_url` | http-path-probe | medium |
| RabbitMQ (`rabbitmq`) | — | http-path-probe | high |
| Spark (`spark`) | `spark_url`, `cluster_name` | http-path-probe | medium |
| Supervisord (`supervisord`) | `name` | http-path-probe | medium |
| Tekton (`tekton`) | — | http-path-probe | high |
| TorchServe (`torchserve`) | — | http-path-probe | high |
| Traefik Mesh (`traefik_mesh`) | `openmetrics_endpoint` | http-path-probe | medium |

## TCP probe with integration-specific protocol

_Open a TCP socket, exchange integration-specific bytes to confirm the target._

### `tcp-banner-server-greets` (1)

Server speaks first with an integration-specific reply (e.g. twemproxy emits its stats JSON on connect).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Twemproxy (nutcracker) (`twemproxy`) | `host`, `port` | tcp-banner-probe | high |

### `tcp-protocol-handshake` (5)

Client sends fixed bytes, integration-specific reply (memcached `version`, redis `PING`/`+PONG`, zookeeper `ruok`/`imok`, gearmand admin protocol, statsd `health`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Gearman (`gearmand`) | — | tcp-banner-probe | high |
| Memcached (`mcache`) | `url` | tcp-banner-probe | high |
| Redis (`redisdb`) | `host`, `port` | tcp-banner-probe | high |
| StatsD (`statsd`) | — | tcp-banner-probe | high |
| ZooKeeper (`zk`) | `host` | tcp-banner-probe | high |

## Local detection (no network, no credentials)

_The integration runs against host-local state; discovery is "is this thing present on the Agent host?"._

### `local-cli-binary` (10)

Shell out to a local CLI binary (`varnishstat`, `ceph`, `gstatus`, `nodetool`, `lctl`, `slurm`, `lparstat`, `tibemsadmin`, `nfsiostat`, `postqueue`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Cassandra Nodetool (`cassandra_nodetool`) | `keyspaces` | other | high |
| Ceph (`ceph`) | — | other | medium |
| GlusterFS (`glusterfs`) | — | other | high |
| LPARStats (`lparstats`) | — | other | high |
| Lustre (`lustre`) | — | other | high |
| Nfsstat (`nfsstat`) | — | other | high |
| Postfix (`postfix`) | `directory` | other | medium |
| Slurm (`slurm`) | — | other | high |
| Tibco EMS (`tibco_ems`) | `username`, `password`, `script_path` | credentials-required | high |
| Varnish (`varnish`) | `varnishstat` | other | high |

### `local-scm-enumeration` (1)

Enumerate the Windows Service Control Manager.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Windows Service (`windows_service`) | `services` | other | medium |

### `cloud-task-metadata` (1)

Hit the link-local task metadata endpoint of the cloud platform (`ECS_CONTAINER_METADATA_URI_V4`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Amazon Fargate (`ecs_fargate`) | — | other | high |

### `local-config-file` (2)

Read a user-supplied local config or DB file (`duckdb` `.db` file, nagios `nagios.cfg`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| DuckDB (`duckdb`) | `db_name` | other | high |
| Nagios (`nagios`) | `nagios_conf` | config-file-parse | high |

## Credentials required

_The check needs credentials that cannot be discovered from the wire. Sub-bucketed by what kind of credential._

### `creds-spec-mandated` (24)

Spec marks `username`/`password` (or equivalent) as required with no default. Typical for traditional databases.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Cacti (`cacti`) | `mysql_host`, `mysql_user`, `rrd_path` | credentials-required | high |
| ClickHouse (`clickhouse`) | `server` | credentials-required | high |
| Couchbase (`couchbase`) | `server` | credentials-required | high |
| DO Query Actions (`do_query_actions`) | `db_identifier`, `username`, `password`, `db_type`, `queries` | credentials-required | high |
| ESXi (`esxi`) | `host`, `username`, `password` | credentials-required | high |
| Harbor (`harbor`) | `url`, `username`, `password` | credentials-required | high |
| MarkLogic (`marklogic`) | `url`, `username`, `password` | credentials-required | high |
| MySQL (`mysql`) | `host`, `username`, `password` | credentials-required | high |
| OpenLDAP (`openldap`) | `url` | credentials-required | high |
| PgBouncer (`pgbouncer`) | `host`, `username` | credentials-required | high |
| Postgres (`postgres`) | `host`, `port`, `username`, `password` | credentials-required | high |
| ProxySQL (`proxysql`) | `host`, `port`, `username`, `password` | credentials-required | high |
| RethinkDB (`rethinkdb`) | `host`, `port` | credentials-required | medium |
| Silverstripe CMS (`silverstripe_cms`) | `SILVERSTRIPE_DATABASE_TYPE`, `SILVERSTRIPE_DATABASE_NAME`, `SILVERSTRIPE_DATABASE_SERVER_IP`, `SILVERSTRIPE_DATABASE_PORT`, `SILVERSTRIPE_DATABASE_USERNAME`, `SILVERSTRIPE_DATABASE_PASSWORD` | credentials-required | high |
| SingleStore (`singlestore`) | `host`, `username`, `password` | credentials-required | high |
| SonarQube (`sonarqube`) | `web_endpoint` | credentials-required | high |
| Sonatype Nexus (`sonatype_nexus`) | `username`, `password`, `server_url` | credentials-required | high |
| SQL Server (`sqlserver`) | `host` | credentials-required | high |
| SSH/SFTP (`ssh_check`) | `host`, `username` | credentials-required | high |
| Teradata (`teradata`) | `server`, `database`, `username`, `password` | credentials-required | high |
| TokuMX (`tokumx`) | `server` | credentials-required | high |
| Vertica (`vertica`) | `server`, `port`, `username`, `password`, `db` | credentials-required | high |
| VoltDB (`voltdb`) | `url`, `username`, `password` | credentials-required | high |
| vSphere (`vsphere`) | `host`, `username`, `password` | credentials-required | high |

### `creds-jmx-rmi` (14)

JMX/RMI integrations (`is_jmx: true`, `template: instances/jmx`). Production deployments enable JMX authentication; ports are not standardized.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| ActiveMQ (`activemq`) | `host`, `port` | credentials-required | high |
| Cassandra (`cassandra`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Confluent Platform (`confluent_platform`) | `host`, `port` | credentials-required | high |
| Hazelcast (`hazelcast`) | `host`, `port` | credentials-required | high |
| Hive (`hive`) | `host`, `port` | credentials-required | high |
| HiveMQ (`hivemq`) | `host`, `port` | credentials-required | high |
| Hudi (`hudi`) | `host`, `port` | credentials-required | high |
| Ignite (`ignite`) | `host`, `port` | credentials-required | high |
| JBoss/WildFly (`jboss_wildfly`) | `jmx_url` | credentials-required | high |
| Kafka (`kafka`) | `host`, `port` | credentials-required | high |
| Presto (`presto`) | `host`, `port` | credentials-required | high |
| Solr (`solr`) | `host`, `port` | credentials-required | high |
| Tomcat (`tomcat`) | `host`, `port`, `user`, `password` | credentials-required | high |
| WebLogic (`weblogic`) | `host`, `port`, `user`, `password` | credentials-required | high |

### `creds-api-token` (24)

Vendor REST API behind an API key, OAuth client credentials, or bearer token.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Amazon MSK (`amazon_msk`) | `cluster_arn` | credentials-required | high |
| Ambari (`ambari`) | `url` | credentials-required | high |
| ArangoDB (`arangodb`) | `openmetrics_endpoint` | credentials-required | high |
| Avi Vantage (`avi_vantage`) | `avi_controller_url` | credentials-required | high |
| Cisco ACI (`cisco_aci`) | `aci_url`, `username`, `pwd` | credentials-required | high |
| Citrix Hypervisor (`citrix_hypervisor`) | `url` | credentials-required | high |
| Cloud Foundry API (`cloud_foundry_api`) | `api_url`, `client_id`, `client_secret` | credentials-required | high |
| Cloudera (`cloudera`) | `api_url`, `workload_username`, `workload_password` | credentials-required | high |
| Control-M (`control_m`) | `control_m_api_endpoint` | credentials-required | high |
| Fly.io (`fly_io`) | `org_slug` | credentials-required | high |
| IBM WAS (`ibm_was`) | `servlet_url` | credentials-required | high |
| NiFi (`nifi`) | `api_url` | credentials-required | high |
| Nutanix (`nutanix`) | `pc_ip`, `pc_username`, `pc_password` | credentials-required | high |
| Octopus Deploy (`octopus_deploy`) | `octopus_endpoint`, `api_key` | credentials-required | high |
| OpenStack (`openstack`) | `keystone_server_url`, `name`, `user` | credentials-required | high |
| OpenStack Controller (`openstack_controller`) | `keystone_server_url`, `user` | credentials-required | high |
| PowerDNS Recursor (`powerdns_recursor`) | `host`, `port`, `api_key` | credentials-required | high |
| Proxmox (`proxmox`) | `proxmox_server`, `headers` | credentials-required | high |
| RiakCS (`riakcs`) | `access_id`, `access_secret` | credentials-required | high |
| Silk (`silk`) | `host_address`, `username`, `password` | credentials-required | high |
| SNMP (`snmp`) | `ip_address` | credentials-required | high |
| Supabase (`supabase`) | — | credentials-required | high |
| TeamCity (`teamcity`) | `server` | credentials-required | high |
| Prisma Cloud Compute (Twistlock) (`twistlock`) | `url`, `username`, `password` | credentials-required | high |

### `creds-proprietary-client` (9)

Needs a proprietary client library installed on the Agent host (Oracle Instant Client, IBM `ibm_db`, `pymqi`, `hdbcli`, FoundationDB cluster file, …) plus credentials.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| FoundationDB (`foundationdb`) | — | credentials-required | high |
| IBM ACE (`ibm_ace`) | `mq_server`, `mq_port`, `channel`, `queue_manager` | credentials-required | high |
| IBM Db2 (`ibm_db2`) | `db`, `username`, `password` | credentials-required | high |
| IBM i ⚠ (`ibm_i`) | `username`, `password`, `driver` | credentials-required | high |
| IBM MQ (`ibm_mq`) | `channel`, `queue_manager` | credentials-required | high |
| IBM Spectrum LSF (`ibm_spectrum_lsf`) | `cluster_name` | other | high |
| MapR (`mapr`) | — | credentials-required | high |
| Oracle Database ⚠ (`oracle`) | `server`, `service_name`, `username`, `password` | credentials-required | high |
| SAP HANA (`sap_hana`) | `server`, `username`, `password` | credentials-required | high |

### `creds-auth-optional-practical` (4)

Spec marks auth as optional but production deployments invariably need it (xpack-secured Elasticsearch, MongoDB with auth enabled, Vault token-gated metrics, etc.).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| ActiveMQ XML (`activemq_xml`) | `url` | credentials-required | medium |
| Kafka Consumer (`kafka_consumer`) | `kafka_connect_str` | other | medium |
| MongoDB (`mongo`) | `hosts` | credentials-required | medium |
| Vault (`vault`) | `api_url` | credentials-required | medium |

## No probe surface

_No reachable upstream service to probe at all. The integration is a logs sink, a DogStatsD listener, a generic configuration template, or a synthetic check._

### `logs-only` (38)

Vendor security tile or log-only integration. The Agent ingests logs; there is no metric check to schedule.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Arctic Wolf Aurora Endpoint Security (`arctic_wolf_aurora_endpoint_security`) | — | other | high |
| Barracuda SecureEdge (`barracuda_secure_edge`) | — | other | high |
| BeyondTrust Password Safe (`beyondtrust_password_safe`) | — | other | high |
| BeyondTrust Privileged Remote Access (`beyondtrust_privileged_remote_access`) | — | other | high |
| Checkpoint Harmony Endpoint (`checkpoint_harmony_endpoint`) | — | other | high |
| Check Point Quantum Firewall (`checkpoint_quantum_firewall`) | — | other | high |
| Cisco ASA (`cisco_asa`) | — | other | high |
| Cisco Secure Client (`cisco_secure_client`) | — | other | high |
| Cisco Secure Firewall (`cisco_secure_firewall`) | — | other | high |
| Cisco Secure Web Appliance (`cisco_secure_web_appliance`) | — | other | high |
| Barracuda CloudGen Firewall (`cloudgen_firewall`) | — | other | high |
| Delinea Privilege Manager (`delinea_privilege_manager`) | — | other | high |
| Delinea Secret Server (`delinea_secret_server`) | — | other | high |
| ESET Protect (`eset_protect`) | — | other | high |
| Flink (`flink`) | — | other | high |
| Forescout (`forescout`) | — | other | high |
| iboss (`iboss`) | — | other | high |
| Ivanti Connect Secure (`ivanti_connect_secure`) | — | other | high |
| journald (`journald`) | — | other | high |
| Juniper SRX Firewall (`juniper_srx_firewall`) | — | other | high |
| Keycloak (`keycloak`) | — | other | high |
| Linux Audit Logs (`linux_audit_logs`) | — | other | high |
| Mac Audit Logs (`mac_audit_logs`) | `MONITOR`, `AUDIT_LOGS_DIR_PATH` | other | high |
| Microsoft DNS (`microsoft_dns`) | — | other | high |
| Microsoft Sysmon (`microsoft_sysmon`) | — | other | high |
| OpenVPN (`openvpn`) | — | other | high |
| OSSEC Security (`ossec_security`) | — | other | high |
| Palo Alto Panorama (`palo_alto_panorama`) | — | other | high |
| Palo Alto Networks Firewall (`pan_firewall`) | — | other | high |
| PingFederate (`ping_federate`) | — | other | high |
| SonicWall Firewall (`sonicwall_firewall`) | — | other | high |
| Suricata (`suricata`) | — | other | high |
| Symantec Endpoint Protection (`symantec_endpoint_protection`) | — | other | high |
| Tenable (Nessus) (`tenable`) | — | other | high |
| WatchGuard Firebox (`watchguard_firebox`) | — | other | high |
| Wazuh (`wazuh`) | — | other | high |
| Zeek (`zeek`) | — | other | high |
| Zscaler Private Access (`zscaler_private_access`) | — | other | high |

### `dogstatsd-only` (1)

Application instruments via DogStatsD; the Agent only listens — no probe.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Sidekiq (`sidekiq`) | — | other | high |

### `user-schema-template` (6)

The integration is a configuration framework: the user supplies the URL / counter list / metric mapping that defines what to collect.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Kafka Actions (`kafka_actions`) | `remote_config_id`, `kafka_connect_str` | other | high |
| OpenMetrics (`openmetrics`) | `openmetrics_endpoint`, `namespace`, `metrics` | other | high |
| PDH (`pdh_check`) | `countersetname`, `metrics` | other | high |
| Prometheus (`prometheus`) | `prometheus_url`, `namespace`, `metrics` | other | high |
| Windows Performance Counters (`windows_performance_counters`) | `metrics` | other | high |
| WMI (`wmi_check`) | `class`, `metrics` | other | high |

### `user-intent-synthetic` (6)

User nominates an arbitrary target to probe (`http_check`, `tcp_check`, `dns_check`, `tls`, `directory`, `win32_event_log`).

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Directory (`directory`) | `directory` | other | high |
| DNS (`dns_check`) | `hostname` | other | high |
| HTTP (`http_check`) | `name`, `url` | other | high |
| TCP (`tcp_check`) | `name`, `host`, `port` | other | high |
| TLS (`tls`) | `server` | other | medium |
| Event Viewer (`win32_event_log`) | `path` | other | medium |

### `per-process-discovery` (5)

User picks which application to monitor by name; the check enumerates host processes.

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Go Expvar (`go_expvar`) | `expvar_url` | other | high |
| Go-Metro (TCP RTT) (`go_metro`) | `interface`, `ips`, `hosts` | other | high |
| GuardDog (`guarddog`) | `guarddog_path`, `package_ecosystem`, `dependency_file_path` | other | high |
| Gunicorn (`gunicorn`) | `proc_name` | other | high |
| Process (`process`) | `name` | other | high |
