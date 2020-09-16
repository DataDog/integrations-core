import re
import time
from copy import deepcopy

import pymongo
from datadog_checks.mongo.common import (
    ALLOWED_CUSTOM_METRICS_TYPES,
    ALLOWED_CUSTOM_QUERIES_COMMANDS,
    REPLSET_MEMBER_STATES,
    SOURCE_TYPE_NAME,
)
from datadog_checks.mongo.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES, COLLECTION_METRICS, TOP_METRICS
from six import PY3, iteritems
from six.moves.urllib.parse import urlsplit

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.common import round_value

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

if PY3:
    long = int


class MongoCollector(object):
    def __init__(self, check, db_name):
        self.check = check
        self.db_name = db_name
        self.log = self.check.log
        self.gauge = self.check.gauge
        self.base_tags = self.check.base_tags
        self.metrics_to_collect = self.check.metrics_to_collect

    def collect(self, client):
        raise NotImplementedError()

    def _normalize(self, metric_name, submit_method, prefix=None):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "mongodb." if not prefix else "mongodb.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == AgentCheck.rate else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in iteritems(CASE_SENSITIVE_METRIC_NAME_SUFFIXES):
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.check.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )

    def _submit_payload(self, payload, additional_tags=None, metrics_to_collect=None, prefix=""):
        if metrics_to_collect is None:
            metrics_to_collect = self.metrics_to_collect
        tags = self.base_tags + (additional_tags or [])
        # Go through the metrics and save the values
        for metric_name in metrics_to_collect:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = payload

            try:
                for c in metric_name.split("."):
                    value = value[c]
            except KeyError:
                continue

            # value is now status[x][y][z]
            if not isinstance(value, (int, long, float)):
                raise TypeError(
                    u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
                        metric_name, type(value)
                    )
                )

            # Submit the metric
            submit_method = (
                self.metrics_to_collect[metric_name][0]
                if isinstance(self.metrics_to_collect[metric_name], tuple)
                else self.metrics_to_collect[metric_name]
            )
            metric_name_alias = (
                self.metrics_to_collect[metric_name][1]
                if isinstance(self.metrics_to_collect[metric_name], tuple)
                else metric_name
            )
            metric_name_alias = self._normalize(metric_name_alias, submit_method, prefix)
            submit_method(self.check, metric_name_alias, value, tags=tags)
            if metric_name_alias.endswith("countps"):
                # Keep old incorrect metric name (only 'top' metrics are affected)
                self.gauge(metric_name_alias[:-2], value, tags=tags)


class ServerStatusCollector(MongoCollector):
    def __init__(self, check, db_name, tcmalloc=False):
        super(ServerStatusCollector, self).__init__(check, db_name)
        self.collect_tcmalloc_metrics = tcmalloc

    def collect(self, client):
        db = client[self.db_name]
        # No need to check for `result['ok']`, already handled by pymongo
        payload = db.command('serverStatus', tcmalloc=self.collect_tcmalloc_metrics)

        # If these keys exist, remove them for now as they cannot be serialized.
        payload.get('backgroundFlushing', {}).pop('last_finished', None)
        payload.pop('localTime', None)

        self._submit_payload(payload)


class CurrentOpCollector(MongoCollector):
    def collect(self, client):
        db = client[self.db_name]
        ops = db.current_op()
        payload = {'fsyncLocked': 1 if ops.get('fsyncLock') else 0}
        self._submit_payload(payload)


class DbStatCollector(MongoCollector):
    def collect(self, client):
        db = client[self.db_name]
        # Submit the metric
        additional_tags = [
            u"cluster:db:{0}".format(self.db_name),  # FIXME: 8.x, was kept for backward compatibility
            u"db:{0}".format(self.db_name),
        ]
        stats = {'stats': db.command('dbstats')}
        return self._submit_payload(stats, additional_tags)


class ReplicaCollector(MongoCollector):
    def __init__(self, check):
        super(ReplicaCollector, self).__init__(check, "admin")
        # Members' last replica set states
        self._last_state_by_server = {}

        # Makes a reasonable hostname for a replset membership event to mention.
        uri = urlsplit(self.check.clean_server_name)
        if '@' in uri.netloc:
            self.hostname = uri.netloc.split('@')[1].split(':')[0]
        else:
            self.hostname = uri.netloc.split(':')[0]
        if self.hostname == 'localhost':
            self.hostname = datadog_agent.get_hostname()

    def _report_replica_set_state(self, state, replset_name):
        """
        Report the member's replica set state
        * Submit a service check.
        * Create an event on state change.
        """
        last_state = self._last_state_by_server.get(self.check.clean_server_name, -1)
        self._last_state_by_server[self.check.clean_server_name] = state
        if last_state == state or last_state == -1:
            return

        status = (
            REPLSET_MEMBER_STATES[state][1]
            if state in REPLSET_MEMBER_STATES
            else 'Replset state %d is unknown to the Datadog agent' % state
        )
        short_status = self._get_state_name(state)
        last_short_status = self._get_state_name(last_state)
        msg_title = "%s is %s for %s" % (self.hostname, short_status, replset_name)
        msg = "MongoDB %s (%s) just reported as %s (%s) for %s; it was %s before."
        msg = msg % (self.hostname, self.check.clean_server_name, status, short_status, replset_name, last_short_status)

        self.check.event(
            {
                'timestamp': int(time.time()),
                'source_type_name': SOURCE_TYPE_NAME,
                'msg_title': msg_title,
                'msg_text': msg,
                'host': self.hostname,
                'tags': [
                    'action:mongo_replset_member_status_change',
                    'member_status:' + short_status,
                    'previous_member_status:' + last_short_status,
                    'replset:' + replset_name,
                ],
            }
        )

    def _get_state_name(self, state):
        if state in REPLSET_MEMBER_STATES:
            return REPLSET_MEMBER_STATES[state][0]
        else:
            return 'UNKNOWN'

    def collect(self, client):
        db = client["admin"]
        status = db.command('replSetGetStatus')
        result = {}

        # Replication set information
        replset_name = status['set']
        replset_state = self._get_state_name(status['myState']).lower()

        # Find nodes: master and current node (ourself)
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
        # TODO: Set those as common tags
        additional_tags = ["replset_name:{}".format(replset_name), "replset_state:{}".format(replset_state)]
        self._submit_payload(result, additional_tags)


class ReplicationInfoCollector(MongoCollector):
    def __init__(self, check):
        super(ReplicationInfoCollector, self).__init__(check, "local")

    def collect(self, client):
        # Fetch information analogous to Mongo's db.getReplicationInfo()
        localdb = client[self.db_name]

        oplog_data = {}

        for ol_collection_name in ("oplog.rs", "oplog.$main"):
            ol_options = localdb[ol_collection_name].options()
            if ol_options:
                break

        if ol_options:
            try:
                oplog_data['logSizeMB'] = round_value(ol_options['size'] / 2.0 ** 20, 2)

                oplog = localdb[ol_collection_name]

                oplog_data['usedSizeMB'] = round_value(
                    localdb.command("collstats", ol_collection_name)['size'] / 2.0 ** 20, 2
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

        self._submit_payload(oplog_data)


class IndexStatsCollector(MongoCollector):
    def __init__(self, check, db_name, coll_names=None):
        super(IndexStatsCollector, self).__init__(check, db_name)
        self.coll_names = coll_names

    def collect(self, client):
        db = client[self.db_name]
        for coll_name in self.coll_names:
            try:
                for stats in db[coll_name].aggregate([{"$indexStats": {}}], cursor={}):
                    idx_tags = self.base_tags + [
                        "name:{0}".format(stats.get('name', 'unknown')),
                        "collection:{0}".format(coll_name),
                    ]
                    val = int(stats.get('accesses', {}).get('ops', 0))
                    self.gauge('mongodb.collection.indexes.accesses.ops', val, idx_tags)
            except Exception as e:
                self.log.error("Could not fetch indexes stats for collection %s: %s", coll_name, e)


class CollStatsCollector(MongoCollector):
    def __init__(self, check, db_name, coll_names=None):
        super(CollStatsCollector, self).__init__(check, db_name)
        self.coll_names = coll_names

    def collect(self, client):
        # Ensure that you're on the right db
        db = client[self.db_name]
        # loop through the collections
        for coll_name in self.coll_names:
            # grab the stats from the collection
            payload = {'collection': db.command("collstats", coll_name)}
            additional_tags = ["db:%s" % self.db_name, "collection:%s" % coll_name]
            self._submit_payload(payload, additional_tags, COLLECTION_METRICS)

            # Submit the indexSizes metrics manually
            index_sizes = payload['collection'].get('indexSizes', {})
            metric_name_alias = self._normalize("collection.indexSizes", AgentCheck.gauge)
            for idx, val in iteritems(index_sizes):
                # we tag the index
                idx_tags = additional_tags + ["index:%s" % idx]
                self.gauge(self, metric_name_alias, val, tags=idx_tags)


class TopCollector(MongoCollector):
    def __init__(self, check):
        super(TopCollector, self).__init__(check, "admin")

    # mongod only
    def collect(self, client):
        dbtop = client[self.db_name].command('top')
        for ns, ns_metrics in iteritems(dbtop['totals']):
            if "." not in ns:
                continue

            # configure tags for db name and collection name
            dbname, collname = ns.split(".", 1)
            additional_tags = ["db:%s" % dbname, "collection:%s" % collname]

            self._submit_payload(ns_metrics, additional_tags, TOP_METRICS, prefix="usage")


class CustomQueriesCollector(MongoCollector):
    def __init__(self, check, db_name, custom_queries):
        super(CustomQueriesCollector, self).__init__(check, db_name)
        self.custom_queries = custom_queries

    @staticmethod
    def _extract_command_from_mongo_query(mongo_query):
        """Extract the command (find, count or aggregate) from the query. Even though mongo and pymongo are supposed
        to work with the query as a single document, pymongo expects the command to be the `first` element of the
        query dict.
        Because python 2 dicts are not ordered, the command is extracted to be later run as the first argument
        of pymongo `runcommand`
        """
        for command in ALLOWED_CUSTOM_QUERIES_COMMANDS:
            if command in mongo_query:
                return command
        raise ValueError("Custom query command must be of type {}".format(ALLOWED_CUSTOM_QUERIES_COMMANDS))

    def _get_submission_method(self, method_name):
        if method_name not in ALLOWED_CUSTOM_METRICS_TYPES:
            raise ValueError('Metric type {} is not one of {}.'.format(method_name, ALLOWED_CUSTOM_METRICS_TYPES))
        return getattr(self.check, method_name)

    def _collect_custom_metrics_for_query(self, db, raw_query):
        """Validates the raw_query object, executes the mongo query then submits the metrics to datadog"""
        tags = self.base_tags + ["db:{}".format(self.db_name)]
        metric_prefix = raw_query.get('metric_prefix')
        if not metric_prefix:  # no cov
            raise ValueError("Custom query field `metric_prefix` is required")
        metric_prefix = metric_prefix.rstrip('.')

        mongo_query = deepcopy(raw_query.get('query'))
        if not mongo_query:  # no cov
            raise ValueError("Custom query field `query` is required")
        mongo_command = self._extract_command_from_mongo_query(mongo_query)
        collection_name = mongo_query[mongo_command]
        del mongo_query[mongo_command]
        if mongo_command not in ALLOWED_CUSTOM_QUERIES_COMMANDS:
            raise ValueError("Custom query command must be of type {}".format(ALLOWED_CUSTOM_QUERIES_COMMANDS))

        submit_method = self.gauge
        fields = []

        if mongo_command == 'count':
            count_type = raw_query.get('count_type')
            if not count_type:  # no cov
                raise ValueError('Custom query field `count_type` is required with a `count` query')
            submit_method = self._get_submission_method(count_type)
        else:
            fields = raw_query.get('fields')
            if not fields:  # no cov
                raise ValueError('Custom query field `fields` is required')

        for field in fields:
            field_name = field.get('field_name')
            if not field_name:  # no cov
                raise ValueError('Field `field_name` is required for metric_prefix `{}`'.format(metric_prefix))

            name = field.get('name')
            if not name:  # no cov
                raise ValueError('Field `name` is required for metric_prefix `{}`'.format(metric_prefix))

            field_type = field.get('type')
            if not field_type:  # no cov
                raise ValueError('Field `type` is required for metric_prefix `{}`'.format(metric_prefix))
            if field_type not in ALLOWED_CUSTOM_METRICS_TYPES + ['tag']:
                raise ValueError('Field `type` must be one of {}'.format(ALLOWED_CUSTOM_METRICS_TYPES + ['tag']))

        tags = list(tags)
        tags.extend(raw_query.get('tags', []))
        tags.append('collection:{}'.format(collection_name))

        try:
            # This is where it is necessary to extract the command and its argument from the query to pass it as the
            # first two params.
            result = db.command(mongo_command, collection_name, **mongo_query)
            if result['ok'] == 0:
                raise pymongo.errors.PyMongoError(result['errmsg'])
        except pymongo.errors.PyMongoError:
            self.log.error("Failed to run custom query for metric %s", metric_prefix)
            raise

        if mongo_command == 'count':
            # A count query simply returns a number, no need to iterate through it.
            submit_method(metric_prefix, result['n'], tags)
            return

        cursor = pymongo.command_cursor.CommandCursor(
            pymongo.collection.Collection(db, collection_name), result['cursor'], None
        )

        for row in cursor:
            metric_info = []
            query_tags = list(tags)

            for field in fields:
                field_name = field['field_name']
                if field_name not in row:
                    # Each row can have different fields, do not fail here.
                    continue

                field_type = field['type']
                if field_type == 'tag':
                    tag_name = field['name']
                    query_tags.append('{}:{}'.format(tag_name, row[field_name]))
                else:
                    metric_suffix = field['name']
                    submit_method = self._get_submission_method(field_type)
                    metric_name = '{}.{}'.format(metric_prefix, metric_suffix)
                    try:
                        metric_info.append((metric_name, float(row[field_name]), submit_method))
                    except (TypeError, ValueError):
                        continue

            for metric_name, metric_value, submit_method in metric_info:
                submit_method(metric_name, metric_value, tags=query_tags)

    def collect(self, client):
        for raw_query in self.custom_queries:
            try:
                self._collect_custom_metrics_for_query(client[self.db_name], raw_query)
            except Exception as e:
                metric_prefix = raw_query.get('metric_prefix')
                self.log.warning("Errors while collecting custom metrics with prefix %s", metric_prefix, exc_info=e)
