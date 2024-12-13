# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Source
SOURCE_TYPE_NAME = 'mongodb'

# Service check
SERVICE_CHECK_NAME = 'mongodb.can_connect'

# Replication states
"""
MongoDB replica set states, as documented at
https://docs.mongodb.org/manual/reference/replica-states/
"""
REPLSET_MEMBER_STATES = {
    0: ('STARTUP', 'Starting Up'),
    1: ('PRIMARY', 'Primary'),
    2: ('SECONDARY', 'Secondary'),
    3: ('RECOVERING', 'Recovering'),
    4: ('Fatal', 'Fatal'),  # MongoDB docs don't list this state
    5: ('STARTUP2', 'Starting up (forking threads)'),
    6: ('UNKNOWN', 'Unknown to this replset member'),
    7: ('ARBITER', 'Arbiter'),
    8: ('DOWN', 'Down'),
    9: ('ROLLBACK', 'Rollback'),
    10: ('REMOVED', 'Removed'),
}

PRIMARY_STATE_ID = 1
SECONDARY_STATE_ID = 2
ARBITER_STATE_ID = 7

DEFAULT_TIMEOUT = 30
ALLOWED_CUSTOM_METRICS_TYPES = ['gauge', 'rate', 'count', 'monotonic_count']
ALLOWED_CUSTOM_QUERIES_COMMANDS = ['aggregate', 'count', 'find']


class HostingType:
    ATLAS = "mongodb-atlas"
    ALIBABA_APSARADB = "alibaba-apsaradb"
    DOCUMENTDB = "amazon-documentdb"
    SELF_HOSTED = "self-hosted"
    UNKNOWN = "unknown"


def get_state_name(state):
    """Maps a mongod node state id to a human readable string."""
    if state in REPLSET_MEMBER_STATES:
        return REPLSET_MEMBER_STATES[state][0]
    else:
        return 'UNKNOWN'


def get_long_state_name(state):
    """Maps a mongod node state id to a human readable string."""
    if state in REPLSET_MEMBER_STATES:
        return REPLSET_MEMBER_STATES[state][1]
    else:
        return 'Replset state %d is unknown to the Datadog agent' % state


class Deployment(object):
    def __init__(self, hosting_type):
        self.hosting_type = hosting_type
        self.use_shards = False

    def is_principal(self):
        """In each mongo cluster there should be always one 'principal' node. One node
        that has full visibility on the user data and only one node should match the criteria.
        This is different from the 'isMaster' property as a replica set primary in a shard is considered
        as 'master' but is not 'principal' for the purpose of this integration.

        This method is used to determine if the check will collect statistics on user database, collections
        and indexes."""
        raise NotImplementedError

    @property
    def deployment_tags(self):
        """
        Returns a list of tags related to the deployment type.
        The tags are subject to change in the event of a deployment type update,
        such as a replica set member state change.
        """
        if self.hosting_type:
            return ["hosting_type:{}".format(self.hosting_type)]
        return []

    @property
    def instance_metadata(self):
        """
        Returns a dictionary of metadata related to the deployment type.
        """
        return {}


class MongosDeployment(Deployment):
    def __init__(self, hosting_type, shard_map):
        super(MongosDeployment, self).__init__(hosting_type)
        self.use_shards = True
        self.shard_map = shard_map

    @property
    def shards(self):
        return list(self.shard_map.get('map', {}).values())

    @property
    def hosts(self):
        return list(self.shard_map.get('hosts', {}).keys())

    @property
    def cluster_type(self):
        return "sharded_cluster"

    @property
    def cluster_role(self):
        return "mongos"

    @property
    def deployment_tags(self):
        return super(MongosDeployment, self).deployment_tags + ["sharding_cluster_role:mongos"]

    @property
    def instance_metadata(self):
        return {
            "sharding_cluster_role": self.cluster_role,
            "hosts": self.hosts,
            "shards": self.shards,
            "cluster_type": self.cluster_type,
        }

    def is_principal(self):
        # A mongos has full visibility on the data, Datadog agents should only communicate
        # with one mongos.
        return True

    def __eq__(self, value: object) -> bool:
        # MongosDeployment instances are equal if they have the same shards and hosts.
        # The order of the shards and hosts is not important as long as the sets are equal.
        # Do not compare the shard_map as it is not used for equality.
        return (
            isinstance(value, MongosDeployment)
            and set(self.shards) == set(value.shards)
            and set(self.hosts) == set(value.hosts)
        )

    def __repr__(self) -> str:
        return super().__repr__() + f"({self.hosts}, {self.shards})"


class ReplicaSetDeployment(Deployment):
    def __init__(
        self, hosting_type, replset_name, replset_state, hosts, replset_me, cluster_role=None, replset_tags=None
    ):
        super(ReplicaSetDeployment, self).__init__(hosting_type)
        self.replset_name = replset_name
        self.replset_state = replset_state
        self.replset_me = replset_me
        self.replset_state_name = get_state_name(replset_state).lower()
        self.use_shards = cluster_role is not None
        self.cluster_role = cluster_role
        self.is_primary = replset_state == PRIMARY_STATE_ID
        self.is_secondary = replset_state == SECONDARY_STATE_ID
        self.is_arbiter = replset_state == ARBITER_STATE_ID
        self.hosts = hosts
        self._replset_tags = replset_tags

    def is_principal(self):
        # There is only ever one primary node in a replica set.
        # In case sharding is disabled, the primary can be considered the master.
        return not self.use_shards and self.is_primary

    @property
    def cluster_type(self):
        return "sharded_cluster" if self.use_shards else "replica_set"

    @property
    def deployment_tags(self):
        tags = super(ReplicaSetDeployment, self).deployment_tags + [
            "replset_name:{}".format(self.replset_name),
            "replset_state:{}".format(self.replset_state_name),
            # in a replica set, the 'me' field is the [hostname]:[port]
            # of the node responding to this command.
            "replset_me:{}".format(self.replset_me),
        ]
        if self.use_shards:
            tags.append('sharding_cluster_role:{}'.format(self.cluster_role))
        return tags

    @property
    def replset_tags(self):
        if not self._replset_tags:
            return []
        return ["replset_{}:{}".format(k.lower(), v) for k, v in self._replset_tags.items()]

    @property
    def instance_metadata(self):
        return {
            "replset_name": self.replset_name,
            "replset_state": self.replset_state_name,
            "sharding_cluster_role": self.cluster_role,
            "hosts": self.hosts,
            "cluster_type": self.cluster_type,
        }

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ReplicaSetDeployment)
            and self.replset_name == value.replset_name
            and self.replset_state == value.replset_state
            and set(self.hosts) == set(value.hosts)
            and self.cluster_role == value.cluster_role
        )

    def __repr__(self) -> str:
        return super().__repr__() + f"({self.replset_name}, {self.replset_state}, {self.hosts}, {self.cluster_role})"


class StandaloneDeployment(Deployment):
    def __init__(self, hosting_type):
        super(StandaloneDeployment, self).__init__(hosting_type)

    def is_principal(self):
        # A standalone always have full visibility.
        return True

    def __eq__(self, value: object) -> bool:
        return isinstance(value, StandaloneDeployment)
