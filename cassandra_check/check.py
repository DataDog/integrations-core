# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3rd party
from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.auth import PlainTextAuthProvider

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'cassandra_check'
DEFAULT_NODE_IP = 'localhost'
DEFAULT_NODE_PORT = 9042


class CassandraCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        # Get the node IP address to connect Cassandra
        node_ip = instance.get("node_ip", DEFAULT_NODE_IP)
        node_port = instance.get("node_port", DEFAULT_NODE_PORT)
        keyspaces = instance.get("keyspaces", [])
        tags = instance.get("tags", [])
        connect_timeout = instance.get("connect_timeout", 5)

        username = instance.get("username", "")
        password = instance.get("password", "")
        auth_provider = PlainTextAuthProvider(username, password)

        # Try to connect to the node
        cluster = Cluster([node_ip], port=node_port, auth_provider=auth_provider, connect_timeout=connect_timeout)
        try:
            cluster.connect(wait_for_all_pools=True)
            if keyspaces:
                for keyspace in keyspaces:
                    token_map = cluster.metadata.token_map
                    down_replicas = 0
                    for token in token_map.ring:
                        replicas = token_map.get_replicas(keyspace, token)
                        down_replicas = max(down_replicas, len([r for r in replicas if not r.is_up]))

                    self.gauge("cassandra.replication_failures", down_replicas,
                        tags=["keyspace:%s" % keyspace, "cluster:%s" % cluster.metadata.cluster_name] + tags)


        except NoHostAvailable as e:
            self.log.error('Could not connect to node %s:%s : %s' % (node_ip, node_port, e))
            node_status = AgentCheck.CRITICAL
        else:
            node_status = AgentCheck.OK
        finally:
            cluster.shutdown()

        self.service_check('cassandra.can_connect', node_status, tags=tags)
