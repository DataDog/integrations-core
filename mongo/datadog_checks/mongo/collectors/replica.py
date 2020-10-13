import time

from six.moves.urllib.parse import urlsplit

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import REPLSET_MEMBER_STATES, SOURCE_TYPE_NAME, get_state_name

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class ReplicaCollector(MongoCollector):
    """Collect replica set metrics by running the replSetGetStatus command. Also keep track of the previous node state
    in order to submit events on any status change.
    """

    def __init__(self, check, tags, last_state):
        super(ReplicaCollector, self).__init__(check, tags=tags)
        # Member's last replica set state
        self._last_state = last_state
        self.hostname = self.extract_hostname_for_event(self.check.clean_server_name)

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

    def _report_replica_set_state(self, state, replset_name):
        """
        Report the member's replica set state
        * Submit a service check.
        * Create an event on state change.
        """
        # Don't submit an event if the state hasn't changed or if the previous state is unset.
        if state == self._last_state or self._last_state is None:
            return

        state_str = (
            REPLSET_MEMBER_STATES[state][1]
            if state in REPLSET_MEMBER_STATES
            else 'Replset state %d is unknown to the Datadog agent' % state
        )
        short_state_str = get_state_name(state)
        previous_short_state_str = get_state_name(self._last_state)
        msg_title = "%s is %s for %s" % (self.hostname, short_state_str, replset_name)
        msg = "MongoDB %s (%s) just reported as %s (%s) for %s; it was %s before."
        msg = msg % (
            self.hostname,
            self.check.clean_server_name,
            state_str,
            short_state_str,
            replset_name,
            previous_short_state_str,
        )

        self.check.event(
            {
                'timestamp': int(time.time()),
                'source_type_name': SOURCE_TYPE_NAME,
                'msg_title': msg_title,
                'msg_text': msg,
                'host': self.hostname,
                'tags': [
                    'action:mongo_replset_member_status_change',
                    'member_status:' + short_state_str,
                    'previous_member_status:' + previous_short_state_str,
                    'replset:' + replset_name,
                ],
            }
        )

    def collect(self, client):
        db = client["admin"]
        status = db.command('replSetGetStatus')
        result = {}

        # Find nodes: current node (ourself) and the primary
        current = primary = None
        for member in status.get('members'):
            if member.get('self'):
                current = member
            if int(member.get('state')) == 1:
                primary = member

        # Compute a lag time
        if current is not None and primary is not None:
            if 'optimeDate' in primary and 'optimeDate' in current:
                lag = primary['optimeDate'] - current['optimeDate']
                result['replicationLag'] = lag.total_seconds()

        if current is not None:
            result['health'] = current['health']

        if current is not None:
            # We used to collect those with a new connection to the primary, this is not required.
            total = 0.0
            cfg = client['local']['system.replset'].find_one()
            for member in cfg.get('members'):
                total += member.get('votes', 1)
                if member['_id'] == current['_id']:
                    result['votes'] = member.get('votes', 1)
            result['voteFraction'] = result['votes'] / total

        result['state'] = status['myState']

        self._submit_payload({'replSet': result})
        self._report_replica_set_state(status['myState'], status['set'])
