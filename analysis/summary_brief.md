_Generated 2026-04-30. 260 total: 96 generic / 40 custom / 124 impossible / 2 need review (⚠)._

### Generic auto-config possible

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Active Directory (`active_directory`) | — | other | high |
| Aerospike (`aerospike`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Apache (`apache`) | `apache_status_url` | http-path-probe | high |
| Appgate SDP (`appgate_sdp`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Argo Rollouts (`argo_rollouts`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Argo Workflows (`argo_workflows`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| ArgoCD (`argocd`) | — | openmetrics-port-scan | high |
| ASP.NET (`aspdotnet`) | — | other | medium |
| AWS Neuron (`aws_neuron`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Azure IoT Edge (`azure_iot_edge`) | `edge_hub_prometheus_url`, `edge_agent_prometheus_url` | openmetrics-port-scan | high |
| BentoML (`bentoml`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Boundary (`boundary`) | `health_endpoint`, `openmetrics_endpoint` | openmetrics-port-scan | high |
| Btrfs (`btrfs`) | — | other | high |
| Calico (`calico`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Celery (`celery`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| cert-manager (`cert_manager`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Cilium (`cilium`) | `agent_endpoint` | openmetrics-port-scan | high |
| CockroachDB (`cockroachdb`) | — | openmetrics-port-scan | high |
| Consul (`consul`) | `url` | http-path-probe | medium |
| CoreDNS (`coredns`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| CRI-O (`crio`) | `prometheus_url` | openmetrics-port-scan | high |
| Datadog Cluster Agent (`datadog_cluster_agent`) | `prometheus_url` | openmetrics-port-scan | high |
| Datadog CSI Driver (`datadog_csi_driver`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| NVIDIA DCGM (`dcgm`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Disk (`disk`) | — | other | high |
| .NET CLR (`dotnetclr`) | — | other | medium |
| Amazon Fargate (`ecs_fargate`) | — | other | high |
| EKS Fargate (`eks_fargate`) | — | other | high |
| etcd (`etcd`) | `prometheus_url` | openmetrics-port-scan | high |
| Exchange Server (`exchange_server`) | — | other | high |
| External DNS (`external_dns`) | `prometheus_url` | openmetrics-port-scan | high |
| Falco (`falco`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Fluentd (`fluentd`) | `monitor_agent_url` | http-path-probe | high |
| Flux (`fluxcd`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Gearman (`gearmand`) | — | tcp-banner-probe | high |
| HDFS Datanode (`hdfs_datanode`) | `hdfs_datanode_jmx_uri` | http-path-probe | high |
| HDFS Namenode (`hdfs_namenode`) | `hdfs_namenode_jmx_uri` | http-path-probe | high |
| Hugging Face TGI (`hugging_face_tgi`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Hyper-V (`hyperv`) | — | other | high |
| IIS (`iis`) | — | other | medium |
| Infiniband (`infiniband`) | — | other | high |
| Karpenter (`karpenter`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| KEDA (`keda`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kong (`kong`) | — | openmetrics-port-scan | high |
| KrakenD (`krakend`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kubernetes API server metrics (`kube_apiserver_metrics`) | `prometheus_url` | openmetrics-port-scan | high |
| Kubernetes Controller Manager (`kube_controller_manager`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube DNS (`kube_dns`) | `prometheus_endpoint` | openmetrics-port-scan | high |
| Kube metrics server (`kube_metrics_server`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube Proxy (`kube_proxy`) | `prometheus_url` | openmetrics-port-scan | high |
| Kubelet (`kubelet`) | — | other | high |
| Kubernetes Cluster Autoscaler (`kubernetes_cluster_autoscaler`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kubernetes State (`kubernetes_state`) | `kube_state_url` | openmetrics-port-scan | high |
| Kubernetes State Core (`kubernetes_state_core`) | — | other | high |
| KubeVirt API (`kubevirt_api`) | `kubevirt_api_metrics_endpoint` | openmetrics-port-scan | medium |
| KubeVirt Controller (`kubevirt_controller`) | `kubevirt_controller_metrics_endpoint` | openmetrics-port-scan | high |
| KubeVirt Handler (`kubevirt_handler`) | `kubevirt_handler_metrics_endpoint` | openmetrics-port-scan | high |
| Kuma (`kuma`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Kyoto Tycoon (`kyototycoon`) | `report_url` | http-path-probe | high |
| Kyverno (`kyverno`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Lighttpd (`lighttpd`) | `lighttpd_status_url` | http-path-probe | high |
| Linkerd (`linkerd`) | — | openmetrics-port-scan | high |
| Linux Proc Extras (`linux_proc_extras`) | — | other | high |
| LiteLLM (`litellm`) | — | openmetrics-port-scan | high |
| MapReduce (`mapreduce`) | `resourcemanager_uri`, `cluster_name` | http-path-probe | high |
| Memcached (`mcache`) | `url` | tcp-banner-probe | high |
| Mesos Master (`mesos_master`) | `url` | http-path-probe | high |
| Mesos Slave (`mesos_slave`) | `url` | http-path-probe | high |
| Milvus (`milvus`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| n8n (`n8n`) | `openmetrics_endpoint` | openmetrics-port-scan | medium |
| Network (`network`) | — | other | high |
| NGINX Ingress Controller (`nginx_ingress_controller`) | `prometheus_url` | openmetrics-port-scan | high |
| NVIDIA NIM (`nvidia_nim`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| NVIDIA Triton (`nvidia_triton`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Pulsar (`pulsar`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Quarkus (`quarkus`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Ray (`ray`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Redis (`redisdb`) | `host`, `port` | tcp-banner-probe | high |
| Riak (`riak`) | `url` | http-path-probe | high |
| Scylla (`scylla`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Squid (`squid`) | `name` | http-path-probe | high |
| StatsD (`statsd`) | — | tcp-banner-probe | high |
| Strimzi (`strimzi`) | — | openmetrics-port-scan | medium |
| System Core (`system_core`) | — | other | high |
| System Swap (`system_swap`) | — | other | high |
| Teleport (`teleport`) | `teleport_url` | openmetrics-port-scan | high |
| Temporal (`temporal`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Traffic Server (`traffic_server`) | `traffic_server_url` | http-path-probe | high |
| Twemproxy (nutcracker) (`twemproxy`) | `host`, `port` | tcp-banner-probe | high |
| Velero (`velero`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| vLLM (`vllm`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Weaviate (`weaviate`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Event Viewer (`win32_event_log`) | `path` | other | medium |
| Windows Service (`windows_service`) | `services` | other | medium |
| YARN (`yarn`) | `resourcemanager_uri` | http-path-probe | high |
| ZooKeeper (`zk`) | `host` | tcp-banner-probe | high |

### Custom auto-config possible

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| ActiveMQ XML (`activemq_xml`) | `url` | credentials-required | medium |
| Airflow (`airflow`) | `url` | http-path-probe | medium |
| Cassandra Nodetool (`cassandra_nodetool`) | `keyspaces` | other | high |
| Ceph (`ceph`) | — | other | medium |
| CouchDB (`couch`) | `server` | http-path-probe | medium |
| Druid (`druid`) | `url` | http-path-probe | medium |
| Elasticsearch (`elastic`) | `url` | http-path-probe | medium |
| Envoy (`envoy`) | — | http-path-probe | medium |
| GitLab (`gitlab`) | — | http-path-probe | medium |
| GitLab Runner (`gitlab_runner`) | `gitlab_url`, `prometheus_endpoint`, `allowed_metrics` | openmetrics-port-scan | medium |
| GlusterFS (`glusterfs`) | — | other | high |
| HAProxy (`haproxy`) | — | http-path-probe | medium |
| HTTP (`http_check`) | `name`, `url` | other | high |
| Impala (`impala`) | `service_type`, `openmetrics_endpoint` | http-path-probe | high |
| Istio (`istio`) | — | http-path-probe | medium |
| Kafka Consumer (`kafka_consumer`) | `kafka_connect_str` | other | medium |
| Kube Scheduler (`kube_scheduler`) | `prometheus_url` | http-path-probe | high |
| Kubeflow (`kubeflow`) | `openmetrics_endpoint` | http-path-probe | medium |
| LPARStats (`lparstats`) | — | other | high |
| Lustre (`lustre`) | — | other | high |
| Marathon (`marathon`) | `url` | http-path-probe | medium |
| MongoDB (`mongo`) | `hosts` | credentials-required | medium |
| Nagios (`nagios`) | `nagios_conf` | config-file-parse | high |
| Nfsstat (`nfsstat`) | — | other | high |
| NGINX (`nginx`) | `nginx_status_url` | http-path-probe | high |
| PHP-FPM (`php_fpm`) | `status_url` | http-path-probe | medium |
| Postfix (`postfix`) | `directory` | other | medium |
| Prefect (`prefect`) | `prefect_url` | http-path-probe | medium |
| RabbitMQ (`rabbitmq`) | — | http-path-probe | high |
| RethinkDB (`rethinkdb`) | `host`, `port` | credentials-required | medium |
| Slurm (`slurm`) | — | other | high |
| Spark (`spark`) | `spark_url`, `cluster_name` | http-path-probe | medium |
| Supervisord (`supervisord`) | `name` | http-path-probe | medium |
| TCP (`tcp_check`) | `name`, `host`, `port` | other | high |
| Tekton (`tekton`) | — | http-path-probe | high |
| TLS (`tls`) | `server` | other | medium |
| TorchServe (`torchserve`) | — | http-path-probe | high |
| Traefik Mesh (`traefik_mesh`) | `openmetrics_endpoint` | http-path-probe | medium |
| Varnish (`varnish`) | `varnishstat` | other | high |
| Vault (`vault`) | `api_url` | credentials-required | medium |

### Auto-config impossible

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| ActiveMQ (`activemq`) | `host`, `port` | credentials-required | high |
| Amazon MSK (`amazon_msk`) | `cluster_arn` | credentials-required | high |
| Ambari (`ambari`) | `url` | credentials-required | high |
| ArangoDB (`arangodb`) | `openmetrics_endpoint` | credentials-required | high |
| Arctic Wolf Aurora Endpoint Security (`arctic_wolf_aurora_endpoint_security`) | — | other | high |
| Avi Vantage (`avi_vantage`) | `avi_controller_url` | credentials-required | high |
| Barracuda SecureEdge (`barracuda_secure_edge`) | — | other | high |
| BeyondTrust Password Safe (`beyondtrust_password_safe`) | — | other | high |
| BeyondTrust Privileged Remote Access (`beyondtrust_privileged_remote_access`) | — | other | high |
| Cacti (`cacti`) | `mysql_host`, `mysql_user`, `rrd_path` | credentials-required | high |
| Cassandra (`cassandra`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Checkpoint Harmony Endpoint (`checkpoint_harmony_endpoint`) | — | other | high |
| Check Point Quantum Firewall (`checkpoint_quantum_firewall`) | — | other | high |
| Cisco ACI (`cisco_aci`) | `aci_url`, `username`, `pwd` | credentials-required | high |
| Cisco ASA (`cisco_asa`) | — | other | high |
| Cisco Secure Client (`cisco_secure_client`) | — | other | high |
| Cisco Secure Firewall (`cisco_secure_firewall`) | — | other | high |
| Cisco Secure Web Appliance (`cisco_secure_web_appliance`) | — | other | high |
| Citrix Hypervisor (`citrix_hypervisor`) | `url` | credentials-required | high |
| ClickHouse (`clickhouse`) | `server` | credentials-required | high |
| Cloud Foundry API (`cloud_foundry_api`) | `api_url`, `client_id`, `client_secret` | credentials-required | high |
| Cloudera (`cloudera`) | `api_url`, `workload_username`, `workload_password` | credentials-required | high |
| Barracuda CloudGen Firewall (`cloudgen_firewall`) | — | other | high |
| Confluent Platform (`confluent_platform`) | `host`, `port` | credentials-required | high |
| Control-M (`control_m`) | `control_m_api_endpoint` | credentials-required | high |
| Couchbase (`couchbase`) | `server` | credentials-required | high |
| Delinea Privilege Manager (`delinea_privilege_manager`) | — | other | high |
| Delinea Secret Server (`delinea_secret_server`) | — | other | high |
| Directory (`directory`) | `directory` | other | high |
| DNS (`dns_check`) | `hostname` | other | high |
| DO Query Actions (`do_query_actions`) | `db_identifier`, `username`, `password`, `db_type`, `queries` | credentials-required | high |
| DuckDB (`duckdb`) | `db_name` | other | high |
| ESET Protect (`eset_protect`) | — | other | high |
| ESXi (`esxi`) | `host`, `username`, `password` | credentials-required | high |
| Flink (`flink`) | — | other | high |
| Fly.io (`fly_io`) | `org_slug` | credentials-required | high |
| Forescout (`forescout`) | — | other | high |
| FoundationDB (`foundationdb`) | — | credentials-required | high |
| Go Expvar (`go_expvar`) | `expvar_url` | other | high |
| Go-Metro (TCP RTT) (`go_metro`) | `interface`, `ips`, `hosts` | other | high |
| GuardDog (`guarddog`) | `guarddog_path`, `package_ecosystem`, `dependency_file_path` | other | high |
| Gunicorn (`gunicorn`) | `proc_name` | other | high |
| Harbor (`harbor`) | `url`, `username`, `password` | credentials-required | high |
| Hazelcast (`hazelcast`) | `host`, `port` | credentials-required | high |
| Hive (`hive`) | `host`, `port` | credentials-required | high |
| HiveMQ (`hivemq`) | `host`, `port` | credentials-required | high |
| Hudi (`hudi`) | `host`, `port` | credentials-required | high |
| IBM ACE (`ibm_ace`) | `mq_server`, `mq_port`, `channel`, `queue_manager` | credentials-required | high |
| IBM Db2 (`ibm_db2`) | `db`, `username`, `password` | credentials-required | high |
| IBM i ⚠ (`ibm_i`) | `username`, `password`, `driver` | credentials-required | high |
| IBM MQ (`ibm_mq`) | `channel`, `queue_manager` | credentials-required | high |
| IBM Spectrum LSF (`ibm_spectrum_lsf`) | `cluster_name` | other | high |
| IBM WAS (`ibm_was`) | `servlet_url` | credentials-required | high |
| iboss (`iboss`) | — | other | high |
| Ignite (`ignite`) | `host`, `port` | credentials-required | high |
| Ivanti Connect Secure (`ivanti_connect_secure`) | — | other | high |
| JBoss/WildFly (`jboss_wildfly`) | `jmx_url` | credentials-required | high |
| journald (`journald`) | — | other | high |
| Juniper SRX Firewall (`juniper_srx_firewall`) | — | other | high |
| Kafka (`kafka`) | `host`, `port` | credentials-required | high |
| Kafka Actions (`kafka_actions`) | `remote_config_id`, `kafka_connect_str` | other | high |
| Keycloak (`keycloak`) | — | other | high |
| Linux Audit Logs (`linux_audit_logs`) | — | other | high |
| Mac Audit Logs (`mac_audit_logs`) | `MONITOR`, `AUDIT_LOGS_DIR_PATH` | other | high |
| MapR (`mapr`) | — | credentials-required | high |
| MarkLogic (`marklogic`) | `url`, `username`, `password` | credentials-required | high |
| Microsoft DNS (`microsoft_dns`) | — | other | high |
| Microsoft Sysmon (`microsoft_sysmon`) | — | other | high |
| MySQL (`mysql`) | `host`, `username`, `password` | credentials-required | high |
| NiFi (`nifi`) | `api_url` | credentials-required | high |
| Nutanix (`nutanix`) | `pc_ip`, `pc_username`, `pc_password` | credentials-required | high |
| Octopus Deploy (`octopus_deploy`) | `octopus_endpoint`, `api_key` | credentials-required | high |
| OpenLDAP (`openldap`) | `url` | credentials-required | high |
| OpenMetrics (`openmetrics`) | `openmetrics_endpoint`, `namespace`, `metrics` | other | high |
| OpenStack (`openstack`) | `keystone_server_url`, `name`, `user` | credentials-required | high |
| OpenStack Controller (`openstack_controller`) | `keystone_server_url`, `user` | credentials-required | high |
| OpenVPN (`openvpn`) | — | other | high |
| Oracle Database ⚠ (`oracle`) | `server`, `service_name`, `username`, `password` | credentials-required | high |
| OSSEC Security (`ossec_security`) | — | other | high |
| Palo Alto Panorama (`palo_alto_panorama`) | — | other | high |
| Palo Alto Networks Firewall (`pan_firewall`) | — | other | high |
| PDH (`pdh_check`) | `countersetname`, `metrics` | other | high |
| PgBouncer (`pgbouncer`) | `host`, `username` | credentials-required | high |
| PingFederate (`ping_federate`) | — | other | high |
| Postgres (`postgres`) | `host`, `port`, `username`, `password` | credentials-required | high |
| PowerDNS Recursor (`powerdns_recursor`) | `host`, `port`, `api_key` | credentials-required | high |
| Presto (`presto`) | `host`, `port` | credentials-required | high |
| Process (`process`) | `name` | other | high |
| Prometheus (`prometheus`) | `prometheus_url`, `namespace`, `metrics` | other | high |
| Proxmox (`proxmox`) | `proxmox_server`, `headers` | credentials-required | high |
| ProxySQL (`proxysql`) | `host`, `port`, `username`, `password` | credentials-required | high |
| RiakCS (`riakcs`) | `access_id`, `access_secret` | credentials-required | high |
| SAP HANA (`sap_hana`) | `server`, `username`, `password` | credentials-required | high |
| Sidekiq (`sidekiq`) | — | other | high |
| Silk (`silk`) | `host_address`, `username`, `password` | credentials-required | high |
| Silverstripe CMS (`silverstripe_cms`) | `SILVERSTRIPE_DATABASE_TYPE`, `SILVERSTRIPE_DATABASE_NAME`, `SILVERSTRIPE_DATABASE_SERVER_IP`, `SILVERSTRIPE_DATABASE_PORT`, `SILVERSTRIPE_DATABASE_USERNAME`, `SILVERSTRIPE_DATABASE_PASSWORD` | credentials-required | high |
| SingleStore (`singlestore`) | `host`, `username`, `password` | credentials-required | high |
| SNMP (`snmp`) | `ip_address` | credentials-required | high |
| Solr (`solr`) | `host`, `port` | credentials-required | high |
| SonarQube (`sonarqube`) | `web_endpoint` | credentials-required | high |
| Sonatype Nexus (`sonatype_nexus`) | `username`, `password`, `server_url` | credentials-required | high |
| SonicWall Firewall (`sonicwall_firewall`) | — | other | high |
| SQL Server (`sqlserver`) | `host` | credentials-required | high |
| SSH/SFTP (`ssh_check`) | `host`, `username` | credentials-required | high |
| Supabase (`supabase`) | — | credentials-required | high |
| Suricata (`suricata`) | — | other | high |
| Symantec Endpoint Protection (`symantec_endpoint_protection`) | — | other | high |
| TeamCity (`teamcity`) | `server` | credentials-required | high |
| Tenable (Nessus) (`tenable`) | — | other | high |
| Teradata (`teradata`) | `server`, `database`, `username`, `password` | credentials-required | high |
| Tibco EMS (`tibco_ems`) | `username`, `password`, `script_path` | credentials-required | high |
| TokuMX (`tokumx`) | `server` | credentials-required | high |
| Tomcat (`tomcat`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Prisma Cloud Compute (Twistlock) (`twistlock`) | `url`, `username`, `password` | credentials-required | high |
| Vertica (`vertica`) | `server`, `port`, `username`, `password`, `db` | credentials-required | high |
| VoltDB (`voltdb`) | `url`, `username`, `password` | credentials-required | high |
| vSphere (`vsphere`) | `host`, `username`, `password` | credentials-required | high |
| WatchGuard Firebox (`watchguard_firebox`) | — | other | high |
| Wazuh (`wazuh`) | — | other | high |
| WebLogic (`weblogic`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Windows Performance Counters (`windows_performance_counters`) | `metrics` | other | high |
| WMI (`wmi_check`) | `class`, `metrics` | other | high |
| Zeek (`zeek`) | — | other | high |
| Zscaler Private Access (`zscaler_private_access`) | — | other | high |
