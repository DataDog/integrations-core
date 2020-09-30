import pymongo

from datadog_checks.base.utils.common import round_value
from datadog_checks.mongo.collectors.base import MongoCollector


class ReplicationOpLogCollector(MongoCollector):
    """Additional replication metrics regarding the operation log. Useful to check how backed up is a secondary
    compared to the primary."""

    def collect(self, client):
        # Fetch information analogous to Mongo's db.getReplicationInfo()
        localdb = client["local"]

        oplog_data = {}

        for collection_name in ("oplog.rs", "oplog.$main"):
            ol_options = localdb[collection_name].options()
            if ol_options:
                break

        if ol_options:
            try:
                oplog_data['logSizeMB'] = round_value(ol_options['size'] / 2.0 ** 20, 2)

                oplog = localdb[collection_name]

                oplog_data['usedSizeMB'] = round_value(
                    localdb.command("collstats", collection_name)['size'] / 2.0 ** 20, 2
                )

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
