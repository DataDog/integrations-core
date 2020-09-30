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

DEFAULT_TIMEOUT = 30
ALLOWED_CUSTOM_METRICS_TYPES = ['gauge', 'rate', 'count', 'monotonic_count']
ALLOWED_CUSTOM_QUERIES_COMMANDS = ['aggregate', 'count', 'find']


def get_state_name(state):
    """Maps a mongod node state id to a human readable string."""
    if state in REPLSET_MEMBER_STATES:
        return REPLSET_MEMBER_STATES[state][0]
    else:
        return 'UNKNOWN'


class Deployment(object):
    def get_available_metrics(self):
        # TODO: Use this method to know what metrics to collect based on the deployment type.
        raise NotImplementedError


class MongosDeployment(Deployment):
    def get_available_metrics(self):
        return None


class ReplicaSetDeployment(Deployment):
    def __init__(self, replset_name, replset_state):
        self.replset_name = replset_name
        self.replset_state = replset_state
        self.replset_state_name = get_state_name(replset_state).lower()

    def get_available_metrics(self):
        return None


class StandaloneDeployment(Deployment):
    def get_available_metrics(self):
        return None
