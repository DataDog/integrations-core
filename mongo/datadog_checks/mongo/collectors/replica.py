import time

from six.moves.urllib.parse import urlsplit

from datadog_checks.mongo.api import MongoApi
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import SOURCE_TYPE_NAME, ReplicaSetDeployment, get_long_state_name, get_state_name

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class ReplicaCollector(MongoCollector):
    """Collect replica set metrics by running the replSetGetStatus command. Also keep track of the previous node state
    in order to submit events on any status change.
    """

    def __init__(self, check, tags):
        super(ReplicaCollector, self).__init__(check, tags)
        self._last_states = check.last_states_by_server
        self.hostname = self.extract_hostname_for_event(self.check.config.clean_server_name)

    def compatible_with(self, deployment):
        # Can only be run on mongod that are part of a replica set.
        return isinstance(deployment, ReplicaSetDeployment)

    @staticmethod
    def extract_hostname_for_event(server_uri):
        """Make a reasonable hostname for a replset membership event to mention."""
        uri = urlsplit(server_uri)
        if '@' in uri.netloc:
            hostname = uri.netloc.split('@')[1].split(':')[0]
        else:
            hostname = uri.netloc.split(':')[0]
        if hostname == 'localhost':
            hostname = datadog_agent.get_hostname()

        return hostname

    def _report_replica_set_states(self, members, replset_name):
        """
        Report all the members' state changes in the replica set.
        This method only runs on the primary.
        """

        for member in members:
            # The id field cannot be changed for a given replica set member.
            member_id = member['_id']
            status_id = member['state']
            old_state = self.check.last_states_by_server.get(member_id)
            if not old_state:
                # First time the agent sees this replica set member.
                continue

            if old_state == status_id:
                continue
            previous_short_state_str = get_state_name(old_state)
            short_state_str = get_state_name(status_id)
            long_state_str = get_long_state_name(status_id)
            node_hostname = member['name']

            msg_title = "{} is {} for {}".format(node_hostname, short_state_str, replset_name)
            msg = (
                "MongoDB {node} (_id: {id}, {uri}) just reported as {status} ({status_short}) "
                "for {replset_name}; it was {old_state} before.".format(
                    node=node_hostname,
                    id=member_id,
                    uri=self.check.config.clean_server_name,
                    status=long_state_str,
                    status_short=short_state_str,
                    replset_name=replset_name,
                    old_state=previous_short_state_str,
                )
            )

            event_payload = {
                'timestamp': int(time.time()),
                'source_type_name': SOURCE_TYPE_NAME,
                'msg_title': msg_title,
                'msg_text': msg,
                'host': node_hostname,
                'tags': [
                    'action:mongo_replset_member_status_change',
                    'member_status:' + short_state_str,
                    'previous_member_status:' + previous_short_state_str,
                    'replset:' + replset_name,
                ],
            }
            if node_hostname == 'localhost':
                # Do not submit events with a 'localhost' hostname.
                event_payload['host'] = self.hostname
            self.check.event(event_payload)

    def get_replset_config(self, api):
        """On most nodes, simply runs `replSetGetConfig`.
        Unfortunately when the agent is connected to an arbiter, running the `replSetGetConfig`
        raises authentication errors. And because authenticating on an arbiter is not allowed, the workaround
        in that case is to run the command directly on the primary."""
        if api.deployment_type.is_arbiter:
            try:
                api_primary = MongoApi(self.check.config, self.log, replicaset=api.deployment_type.replset_name)
            except Exception:
                self.log.warning(
                    "Current node is an arbiter, the extra connection to the primary was unsuccessful."
                    " Votes metrics won't be reported."
                )
                return None
            return api_primary['admin'].command('replSetGetConfig')

        return api['admin'].command('replSetGetConfig')

    def collect(self, api):
        db = api["admin"]
        status = db.command('replSetGetStatus')
        result = {}

        # Find nodes: current node (ourself) and the primary
        current = primary = None
        is_primary = False
        for member in status.get('members', []):
            if member.get('self'):
                current = member
                if int(member['state']) == 1:
                    is_primary = True
            if int(member.get('state')) == 1:
                primary = member

        # Compute a lag time
        if current is not None and primary is not None:
            if 'optimeDate' in primary and 'optimeDate' in current:
                lag = primary['optimeDate'] - current['optimeDate']
                result['replicationLag'] = lag.total_seconds()

        if current is not None:
            result['health'] = current['health']

        # Collect the number of votes
        config = self.get_replset_config(api)
        votes = 0
        total = 0.0
        for member in config['config']['members']:
            total += member.get('votes', 1)
            if member['_id'] == current['_id']:
                votes = member.get('votes', 1)
        result['votes'] = votes
        result['voteFraction'] = votes / total
        result['state'] = status['myState']
        self._submit_payload({'replSet': result})
        if is_primary:
            # Submit events
            replset_name = status['set']
            self._report_replica_set_states(status['members'], replset_name)

            # The replset_state tags represents the state of the current node (i.e primary at this point).
            # The next section computes lag time for other nodes, thus `replset_state` is replaced with the
            # state of each node.
            lag_time_tags = [t for t in self.base_tags if not t.startswith('replset_state:')]
            # Compute a lag time
            for member in status.get('members', []):
                if get_state_name(member.get('state')) not in ('SECONDARY', 'PRIMARY'):
                    # Can only compute a meaningful lag time from secondaries and primaries
                    continue
                if 'optimeDate' in primary and 'optimeDate' in member:
                    lag = primary['optimeDate'] - member['optimeDate']
                    tags = lag_time_tags + [
                        'member:{}'.format(member.get('name', 'unknown')),
                        'replset_state:{}'.format(get_state_name(member.get('state')).lower()),
                    ]
                    self.gauge('mongodb.replset.optime_lag', lag.total_seconds(), tags)

        self.check.last_states_by_server = {member['_id']: member['state'] for member in status['members']}
