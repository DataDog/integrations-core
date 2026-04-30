_Generated 2026-04-30. 115 total: 39 generic / 27 custom / 49 impossible / 0 need review (⚠)._

### Generic auto-config possible

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| Active Directory (`active_directory`) | — | other | high |
| Aerospike (`aerospike`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Apache (`apache`) | `apache_status_url` | http-path-probe | high |
| Btrfs (`btrfs`) | — | other | high |
| cert-manager (`cert_manager`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Cilium (`cilium`) | `agent_endpoint` | openmetrics-port-scan | high |
| CockroachDB (`cockroachdb`) | — | openmetrics-port-scan | high |
| Consul (`consul`) | `url` | http-path-probe | medium |
| CoreDNS (`coredns`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Datadog Cluster Agent (`datadog_cluster_agent`) | `prometheus_url` | openmetrics-port-scan | high |
| etcd (`etcd`) | `prometheus_url` | openmetrics-port-scan | high |
| Exchange Server (`exchange_server`) | — | other | high |
| Fluentd (`fluentd`) | `monitor_agent_url` | http-path-probe | high |
| Flux (`fluxcd`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| HDFS Datanode (`hdfs_datanode`) | `hdfs_datanode_jmx_uri` | http-path-probe | high |
| HDFS Namenode (`hdfs_namenode`) | `hdfs_namenode_jmx_uri` | http-path-probe | high |
| Hyper-V (`hyperv`) | — | other | high |
| IIS (`iis`) | — | other | medium |
| Kong (`kong`) | — | openmetrics-port-scan | high |
| Kubernetes Controller Manager (`kube_controller_manager`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube DNS (`kube_dns`) | `prometheus_endpoint` | openmetrics-port-scan | high |
| Kube metrics server (`kube_metrics_server`) | `prometheus_url` | openmetrics-port-scan | high |
| Kube Proxy (`kube_proxy`) | `prometheus_url` | openmetrics-port-scan | high |
| Lighttpd (`lighttpd`) | `lighttpd_status_url` | http-path-probe | high |
| Linkerd (`linkerd`) | — | openmetrics-port-scan | high |
| MapReduce (`mapreduce`) | `resourcemanager_uri`, `cluster_name` | http-path-probe | high |
| Memcached (`mcache`) | `url` | tcp-banner-probe | high |
| Mesos Master (`mesos_master`) | `url` | http-path-probe | high |
| NGINX Ingress Controller (`nginx_ingress_controller`) | `prometheus_url` | openmetrics-port-scan | high |
| Pulsar (`pulsar`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Redis (`redisdb`) | `host`, `port` | tcp-banner-probe | high |
| Riak (`riak`) | `url` | http-path-probe | high |
| Scylla (`scylla`) | `openmetrics_endpoint` | openmetrics-port-scan | high |
| Squid (`squid`) | `name` | http-path-probe | high |
| StatsD (`statsd`) | — | tcp-banner-probe | high |
| Twemproxy (nutcracker) (`twemproxy`) | `host`, `port` | tcp-banner-probe | high |
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
| Druid (`druid`) | `url` | http-path-probe | medium |
| Elasticsearch (`elastic`) | `url` | http-path-probe | medium |
| Envoy (`envoy`) | — | http-path-probe | medium |
| GitLab (`gitlab`) | — | http-path-probe | medium |
| GitLab Runner (`gitlab_runner`) | `gitlab_url`, `prometheus_endpoint`, `allowed_metrics` | openmetrics-port-scan | medium |
| GlusterFS (`glusterfs`) | — | other | high |
| HAProxy (`haproxy`) | — | http-path-probe | medium |
| Istio (`istio`) | — | http-path-probe | medium |
| Kafka Consumer (`kafka_consumer`) | `kafka_connect_str` | other | medium |
| Kube Scheduler (`kube_scheduler`) | `prometheus_url` | http-path-probe | high |
| Marathon (`marathon`) | `url` | http-path-probe | medium |
| MongoDB (`mongo`) | `hosts` | credentials-required | medium |
| Nagios (`nagios`) | `nagios_conf` | config-file-parse | high |
| NGINX (`nginx`) | `nginx_status_url` | http-path-probe | high |
| PHP-FPM (`php_fpm`) | `status_url` | http-path-probe | medium |
| Postfix (`postfix`) | `directory` | other | medium |
| RabbitMQ (`rabbitmq`) | — | http-path-probe | high |
| RethinkDB (`rethinkdb`) | `host`, `port` | credentials-required | medium |
| Spark (`spark`) | `spark_url`, `cluster_name` | http-path-probe | medium |
| Supervisord (`supervisord`) | `name` | http-path-probe | medium |
| TLS (`tls`) | `server` | other | medium |
| Varnish (`varnish`) | `varnishstat` | other | high |
| Vault (`vault`) | `api_url` | credentials-required | medium |

### Auto-config impossible

| Integration | Required fields | Method | Conf. |
|---|---|---|---|
| ActiveMQ (`activemq`) | `host`, `port` | credentials-required | high |
| Ambari (`ambari`) | `url` | credentials-required | high |
| ArangoDB (`arangodb`) | `openmetrics_endpoint` | credentials-required | high |
| Cacti (`cacti`) | `mysql_host`, `mysql_user`, `rrd_path` | credentials-required | high |
| Cassandra (`cassandra`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Cisco ACI (`cisco_aci`) | `aci_url`, `username`, `pwd` | credentials-required | high |
| ClickHouse (`clickhouse`) | `server` | credentials-required | high |
| Confluent Platform (`confluent_platform`) | `host`, `port` | credentials-required | high |
| Couchbase (`couchbase`) | `server` | credentials-required | high |
| Flink (`flink`) | — | other | high |
| Gunicorn (`gunicorn`) | `proc_name` | other | high |
| Harbor (`harbor`) | `url`, `username`, `password` | credentials-required | high |
| Hazelcast (`hazelcast`) | `host`, `port` | credentials-required | high |
| Hive (`hive`) | `host`, `port` | credentials-required | high |
| HiveMQ (`hivemq`) | `host`, `port` | credentials-required | high |
| IBM Db2 (`ibm_db2`) | `db`, `username`, `password` | credentials-required | high |
| IBM MQ (`ibm_mq`) | `channel`, `queue_manager` | credentials-required | high |
| IBM WAS (`ibm_was`) | `servlet_url` | credentials-required | high |
| Ignite (`ignite`) | `host`, `port` | credentials-required | high |
| JBoss/WildFly (`jboss_wildfly`) | `jmx_url` | credentials-required | high |
| journald (`journald`) | — | other | high |
| MySQL (`mysql`) | `host`, `username`, `password` | credentials-required | high |
| OpenLDAP (`openldap`) | `url` | credentials-required | high |
| OpenMetrics (`openmetrics`) | `openmetrics_endpoint`, `namespace`, `metrics` | other | high |
| OpenStack (`openstack`) | `keystone_server_url`, `name`, `user` | credentials-required | high |
| OpenStack Controller (`openstack_controller`) | `keystone_server_url`, `user` | credentials-required | high |
| PgBouncer (`pgbouncer`) | `host`, `username` | credentials-required | high |
| Postgres (`postgres`) | `host`, `port`, `username`, `password` | credentials-required | high |
| PowerDNS Recursor (`powerdns_recursor`) | `host`, `port`, `api_key` | credentials-required | high |
| Presto (`presto`) | `host`, `port` | credentials-required | high |
| Prometheus (`prometheus`) | `prometheus_url`, `namespace`, `metrics` | other | high |
| ProxySQL (`proxysql`) | `host`, `port`, `username`, `password` | credentials-required | high |
| SAP HANA (`sap_hana`) | `server`, `username`, `password` | credentials-required | high |
| Sidekiq (`sidekiq`) | — | other | high |
| SingleStore (`singlestore`) | `host`, `username`, `password` | credentials-required | high |
| SNMP (`snmp`) | `ip_address` | credentials-required | high |
| Solr (`solr`) | `host`, `port` | credentials-required | high |
| SonarQube (`sonarqube`) | `web_endpoint` | credentials-required | high |
| SQL Server (`sqlserver`) | `host` | credentials-required | high |
| SSH/SFTP (`ssh_check`) | `host`, `username` | credentials-required | high |
| TeamCity (`teamcity`) | `server` | credentials-required | high |
| Tenable (Nessus) (`tenable`) | — | other | high |
| Tomcat (`tomcat`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Prisma Cloud Compute (Twistlock) (`twistlock`) | `url`, `username`, `password` | credentials-required | high |
| Vertica (`vertica`) | `server`, `port`, `username`, `password`, `db` | credentials-required | high |
| vSphere (`vsphere`) | `host`, `username`, `password` | credentials-required | high |
| WebLogic (`weblogic`) | `host`, `port`, `user`, `password` | credentials-required | high |
| Windows Performance Counters (`windows_performance_counters`) | `metrics` | other | high |
| WMI (`wmi_check`) | `class`, `metrics` | other | high |
