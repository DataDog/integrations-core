# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from datetime import datetime


class ElectionRecord(object):
    def __init__(self):
        super(ElectionRecord, self).__init__()

    @property
    def seconds_until_renew(self):
        """
        Returns the number of seconds between the current time
        and the set renew time. It can be negative if the
        leader election is running late.
        """
        delta = self.renew_time - datetime.now(self.renew_time.tzinfo)
        return delta.total_seconds()

    @property
    def summary(self):
        return "Leader: {} since {}, next renew {}".format(self.leader_name, self.acquire_time, self.renew_time)


# Import lazily to reduce memory footprint
parse_rfc3339 = None

# If these fields are missing or empty, the service check
# will fail inconditionnaly. Fields taken from
# https://godoc.org/k8s.io/client-go/tools/leaderelection/resourcelock#LeaderElectionRecord
REQUIRED_FIELDS = [
    ("holderIdentity", "no current leader recorded"),
    ("leaseDurationSeconds", "no lease duration set"),
    ("renewTime", "no renew time set"),
    ("acquireTime", "no acquire time recorded"),
]


class ElectionRecordAnnotation(ElectionRecord):
    def __init__(self, record_kind, record_string):
        super(ElectionRecordAnnotation, self).__init__()
        self._kind = record_kind
        self._record = json.loads(record_string)

    def validate(self):
        reason_prefix = "Invalid record: "
        # Test for required fields
        for field, message in REQUIRED_FIELDS:
            if field not in self._record or not self._record[field]:
                return False, reason_prefix + message

        if not self.renew_time:
            return False, reason_prefix + "bad format for renewTime field"
        if not self.acquire_time:
            return False, reason_prefix + "bad format for acquireTime field"

        # No issue, record is valid
        return True, None

    @property
    def leader_name(self):
        return self._record["holderIdentity"]

    @property
    def lease_duration(self):
        return int(self._record["leaseDurationSeconds"])

    @property
    def renew_time(self):
        global parse_rfc3339
        if parse_rfc3339 is None:
            from kubernetes.config.dateutil import parse_rfc3339  # noqa F401

        try:
            return parse_rfc3339(self._record.get("renewTime"))
        except Exception:
            return None

    @property
    def acquire_time(self):
        global parse_rfc3339
        if parse_rfc3339 is None:
            from kubernetes.config.dateutil import parse_rfc3339  # noqa F401

        try:
            return parse_rfc3339(self._record.get("acquireTime"))
        except Exception:
            return None

    @property
    def transitions(self):
        return self._record.get("leaderTransitions", 0)

    @property
    def kind(self):
        return self._kind


class ElectionRecordLease(ElectionRecord):
    def __init__(self, lease):
        super(ElectionRecordLease, self).__init__()
        self._lease = lease.spec

    def validate(self):
        from kubernetes.client.models.v1_lease_spec import V1LeaseSpec  # noqa F401

        return isinstance(self._lease, V1LeaseSpec), None

    @property
    def leader_name(self):
        return self._lease.holder_identity

    @property
    def lease_duration(self):
        return self._lease.lease_duration_seconds

    @property
    def renew_time(self):
        return self._lease.renew_time

    @property
    def acquire_time(self):
        return self._lease.acquire_time

    @property
    def transitions(self):
        return self._lease.lease_transitions

    @property
    def kind(self):
        return "lease"
