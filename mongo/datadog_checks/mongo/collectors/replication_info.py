# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pymongo

from datadog_checks.base.utils.common import round_value
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import ReplicaSetDeployment


class ReplicationOpLogCollector(MongoCollector):
    """Additional replication metrics regarding the operation log. Useful to check how backed up is a secondary
    compared to the primary."""

    def compatible_with(self, deployment):
        # Can only be run on mongod node that is part of a replica set. Not possible on arbiters.
        if not isinstance(deployment, ReplicaSetDeployment):
            self.log.debug("ReplicationOpLogCollector can only be run on mongod nodes, replicaset deployment detected.")
            return False

        if deployment.is_arbiter:
            self.log.debug("ReplicationOpLogCollector can only be run on mongod nodes, arbitrer node detected.")
            return False

        return True

    def _get_oplog_size(self, api, oplog_collection_name):
        try:
            oplog_storage_stats = list(
                api.get_collection_stats("local", oplog_collection_name, stats=["storageStats"])
            )[0]
        except pymongo.errors.OperationFailure as e:
            self.log.warning(
                "Could not collect oplog used size for collection %s: %s", oplog_collection_name, e.details
            )
            return
        except Exception as e:
            self.log.error(
                "Unexpected error when fetch oplog used size for collection %s: %s", oplog_collection_name, e
            )
            return

        if api.coll_stats_pipeline_supported:
            return oplog_storage_stats.get("storageStats", {}).get("size")
        return oplog_storage_stats.get('size')

    def collect(self, api):
        # Fetch information analogous to Mongo's db.getReplicationInfo()
        localdb = api["local"]

        oplog_data = {}
        try:
            for collection_name in ("oplog.rs", "oplog.$main"):
                ol_options = localdb[collection_name].options()
                if ol_options:
                    break
        except pymongo.errors.OperationFailure as e:
            # In theory this error should only happen when connected to mongos or arbiter.
            self.log.debug("Unable to collect oplog metrics from replica set member. Error is: %s", e)
            return

        if ol_options:
            try:
                oplog_data['logSizeMB'] = round_value(ol_options['size'] / 2.0**20, 2)

                oplog = localdb[collection_name]

                oplog_data_size = self._get_oplog_size(api, collection_name)
                if oplog_data_size is not None:
                    oplog_data['usedSizeMB'] = round_value(oplog_data_size / 2.0**20, 2)

                op_asc_cursor = oplog.find({"ts": {"$exists": 1}}).sort("$natural", pymongo.ASCENDING).limit(1)
                op_dsc_cursor = oplog.find({"ts": {"$exists": 1}}).sort("$natural", pymongo.DESCENDING).limit(1)

                try:
                    first_timestamp = op_asc_cursor[0]['ts'].as_datetime()
                    last_timestamp = op_dsc_cursor[0]['ts'].as_datetime()
                    time_diff = last_timestamp - first_timestamp
                    oplog_data['timeDiff'] = time_diff.total_seconds()
                except (IndexError, KeyError):
                    # if the oplog collection doesn't have any entries
                    # if an object in the collection doesn't have a ts value, we ignore it
                    pass
            except KeyError:
                # encountered an error trying to access options.size for the oplog collection
                self.log.warning(u"Failed to record `ReplicationInfo` metrics.")

        self._submit_payload({'oplog': oplog_data})
