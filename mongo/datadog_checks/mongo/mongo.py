# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy
from distutils.version import LooseVersion

import pymongo
from datadog_checks.mongo.collectors import (
    CollStatsCollector,
    CurrentOpCollector,
    CustomQueriesCollector,
    DbStatCollector,
    IndexStatsCollector,
    ReplicaCollector,
    ReplicationInfoCollector,
    ServerStatusCollector,
    TopCollector,
)
from datadog_checks.mongo.common import DEFAULT_TIMEOUT, SERVICE_CHECK_NAME
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from . import metrics
from .utils import build_connection_string, parse_mongo_uri

if PY3:
    long = int


class MongoDb(AgentCheck):
    """
    MongoDB agent check.

    # Metrics
    Metric available for collection are listed by topic as `MongoDb` class variables.

    Various metric topics are collected by default. Others require the
    corresponding option enabled in the check configuration file.

    ## Format
    Metrics are listed with the following format:
        ```
        metric_name -> metric_type
        ```
        or
        ```
        metric_name -> (metric_type, alias)*
        ```

    * `alias` parameter is optional, if unspecified, MongoDB metrics are reported
       with their original metric names.

    # Service checks
    Available service checks:
    * `mongodb.can_connect`
      Connectivity health to the instance.
    * `mongodb.replica_set_member_state`
      Disposition of the member replica set state.
    """

    def __init__(self, name, init_config, instances=None):
        super(MongoDb, self).__init__(name, init_config, instances)

        # Members' last replica set states
        self._last_state_by_server = {}

        self.collection_metrics_names = tuple(key.split('.')[1] for key in metrics.COLLECTION_METRICS)

        # x.509 authentication
        ssl_params = {
            'ssl': self.instance.get('ssl', None),
            'ssl_keyfile': self.instance.get('ssl_keyfile', None),
            'ssl_certfile': self.instance.get('ssl_certfile', None),
            'ssl_cert_reqs': self.instance.get('ssl_cert_reqs', None),
            'ssl_ca_certs': self.instance.get('ssl_ca_certs', None),
        }
        self.ssl_params = {key: value for key, value in iteritems(ssl_params) if value is not None}

        if 'server' in self.instance:
            self.warning('Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.')
            self.server = self.instance['server']
        else:
            hosts = self.instance.get('hosts', [])
            if not hosts:
                raise ConfigurationError('No `hosts` specified')

            username = self.instance.get('username')
            password = self.instance.get('password')

            if username and not password:
                raise ConfigurationError('`password` must be set when a `username` is specified')

            if password and not username:
                raise ConfigurationError('`username` must be set when a `password` is specified')

            self.server = build_connection_string(
                hosts,
                scheme=self.instance.get('connection_scheme', 'mongodb'),
                username=username,
                password=password,
                database=self.instance.get('database'),
                options=self.instance.get('options'),
            )

        (
            self.username,
            self.password,
            self.db_name,
            self.nodelist,
            self.clean_server_name,
            self.auth_source,
        ) = parse_mongo_uri(self.server, sanitize_username=bool(self.ssl_params))

        self.additional_metrics = self.instance.get('additional_metrics', [])

        # Get the list of metrics to collect
        self.collect_tcmalloc_metrics = 'tcmalloc' in self.additional_metrics
        self.metrics_to_collect = self._build_metric_list_to_collect()

        if not self.db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            self.db_name = 'admin'

        # Tagging
        custom_tags = list(set(self.instance.get('tags', [])))
        self.service_check_tags = ["db:%s" % self.db_name] + custom_tags

        # ...add the `server` tag to the metrics' tags only
        # (it's added in the backend for service checks)
        self.base_tags = custom_tags + ['server:%s' % self.clean_server_name]

        if self.nodelist:
            host = self.nodelist[0][0]
            port = self.nodelist[0][1]
            self.service_check_tags = self.service_check_tags + ["host:%s" % host, "port:%s" % port]

        self.timeout = float(self.instance.get('timeout', DEFAULT_TIMEOUT)) * 1000

        # Authenticate
        self.do_auth = True
        self.use_x509 = self.ssl_params and not self.password
        if not self.username:
            self.log.debug(u"A username is required to authenticate to `%s`", self.server)
            self.do_auth = False

        self.replica_check = is_affirmative(self.instance.get('replica_check', True))
        self.collections_indexes_stats = is_affirmative(self.instance.get('collections_indexes_stats'))
        self.coll_names = self.instance.get('collections', [])
        self.custom_queries = self.instance.get("custom_queries", [])

    @classmethod
    def get_library_versions(cls):
        return {'pymongo': pymongo.version}

    def _build_metric_list_to_collect(self):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Defaut metrics
        for default_metrics in itervalues(metrics.DEFAULT_METRICS):
            metrics_to_collect.update(default_metrics)

        # Additional metrics metrics
        for option in self.additional_metrics:
            additional_metrics = metrics.AVAILABLE_METRICS.get(option)
            if not additional_metrics:
                if option in metrics.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated. The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect: unrecognized `%s` option", option
                    )
                continue

            self.log.debug(u"Adding `%s` corresponding metrics to the list of metrics to collect.", option)
            metrics_to_collect.update(additional_metrics)

        return metrics_to_collect

    def _authenticate(self, database):
        """
        Authenticate to the database.

        Available mechanisms:
        * Username & password
        * X.509

        More information:
        https://api.mongodb.com/python/current/examples/authentication.html
        """
        authenticated = False
        try:
            # X.509
            if self.use_x509:
                self.log.debug(u"Authenticate `%s`  to `%s` using `MONGODB-X509` mechanism", self.username, database)
                authenticated = database.authenticate(self.username, mechanism='MONGODB-X509')

            # Username & password
            else:
                authenticated = database.authenticate(self.username, self.password)

        except pymongo.errors.PyMongoError as e:
            self.log.error(u"Authentication failed due to invalid credentials or configuration issues. %s", e)

        if not authenticated:
            message = "Mongo: cannot connect with config %s" % self.clean_server_name
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags, message=message)
            raise Exception(message)

        return authenticated

    def check(self, _):
        """
        Returns a dictionary that looks a lot like what's sent back by
        db.serverStatus()
        """
        try:
            cli = pymongo.mongo_client.MongoClient(
                self.server,
                socketTimeoutMS=self.timeout,
                connectTimeoutMS=self.timeout,
                serverSelectionTimeoutMS=self.timeout,
                read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,
                **self.ssl_params
            )
            # some commands can only go against the admin DB
            db = cli[self.db_name]
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            raise

        if self.do_auth:
            if self.auth_source:
                msg = "authSource was specified in the the server URL: using '%s' as the authentication database"
                self.log.info(msg, self.auth_source)
                self._authenticate(cli[self.auth_source])
            else:
                self._authenticate(db)

        tags = deepcopy(self.base_tags)
        try:
            mongo_version = cli.server_info().get('version', '0.0')
            self.set_metadata('version', mongo_version)
        except Exception:
            self.log.exception("Error when collecting the version from the mongo server.")
            mongo_version = '0.0'

        collector = ServerStatusCollector(self, self.db_name, tcmalloc=self.collect_tcmalloc_metrics)
        try:
            collector.collect(cli)
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)

        # Replaces
        #
        #     try:
        #         status = db.command('serverStatus', tcmalloc=self.collect_tcmalloc_metrics)
        #     except Exception:
        #         self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
        #         raise
        #     else:
        #         self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)
        #
        #     if status['ok'] == 0:
        #         raise Exception(status['errmsg'].__str__())

        collector = CurrentOpCollector(self, self.db_name)
        collector.collect(cli)
        # Replaces
        #
        #    ops = db.current_op()
        #    status['fsyncLocked'] = 1 if ops.get('fsyncLock') else 0

        collector = DbStatCollector(self, self.db_name)
        collector.collect(cli)
        # Replaces
        #
        #    status['stats'] = db.command('dbstats')
        #   dbstats = {self.db_name: {'stats': status['stats']}}

        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus  # noqa
        if self.replica_check:
            collector = ReplicaCollector(self)
            try:
                collector.collect(cli)
                # Replaces
                # data = {}
                #
                # replSet = admindb.command('replSetGetStatus')
                # if replSet:
                #     primary = None
                #     current = None
                #
                #     # need a new connection to deal with replica sets
                #     setname = replSet.get('set')
                #     cli_rs = pymongo.mongo_client.MongoClient(
                #         self.server,
                #         socketTimeoutMS=self.timeout,
                #         connectTimeoutMS=self.timeout,
                #         serverSelectionTimeoutMS=self.timeout,
                #         replicaset=setname,
                #         read_preference=pymongo.ReadPreference.NEAREST,
                #         **self.ssl_params
                #     )
                #
                #     if self.do_auth:
                #         if self.auth_source:
                #             self._authenticate(cli_rs[self.auth_source])
                #         else:
                #             self._authenticate(cli_rs[self.db_name])
                #
                #     # Replication set information
                #     replset_name = replSet['set']
                #     replset_state = self.get_state_name(replSet['myState']).lower()
                #
                #     tags.extend([
                #         u"replset_name:{0}".format(replset_name),
                #         u"replset_state:{0}".format(replset_state)]
                #     )
                #
                #     # Find nodes: master and current node (ourself)
                #     for member in replSet.get('members'):
                #         if member.get('self'):
                #             current = member
                #         if int(member.get('state')) == 1:
                #             primary = member
                #
                #     # Compute a lag time
                #     if current is not None and primary is not None:
                #         if 'optimeDate' in primary and 'optimeDate' in current:
                #             lag = primary['optimeDate'] - current['optimeDate']
                #             data['replicationLag'] = total_seconds(lag)
                #
                #     if current is not None:
                #         data['health'] = current['health']
                #
                #     data['state'] = replSet['myState']
                #
                #     if current is not None:
                #         total = 0.0
                #         cfg = cli_rs['local']['system.replset'].find_one()
                #         for member in cfg.get('members'):
                #             total += member.get('votes', 1)
                #             if member['_id'] == current['_id']:
                #                 data['votes'] = member.get('votes', 1)
                #         data['voteFraction'] = data['votes'] / total
                #
                #     status['replSet'] = data
                #
                #     # Submit events
                #     self._report_replica_set_state(data['state'], replset_name)
            except Exception as e:
                if "OperationFailure" in repr(e) and (
                    "not running with --replSet" in str(e) or "replSetGetStatus" in str(e)
                ):
                    pass
                else:
                    raise e

        dbnames = cli.list_database_names()
        self.gauge('mongodb.dbs', len(dbnames), tags=tags)

        for db_n in dbnames:
            collector = DbStatCollector(self, db_n)
            collector.collect(cli)
            # Replaces
            #
            #     db_aux = cli[db_n]
            #     dbstats[db_n] = {'stats': db_aux.command('dbstats')}

        # -- Removed by collectors: --
        # # Go through the metrics and save the values
        # for metric_name in self.metrics_to_collect:
        #     # each metric is of the form: x.y.z with z optional
        #     # and can be found at status[x][y][z]
        #     value = status
        #
        #     if metric_name.startswith('stats'):
        #         continue
        #     else:
        #         try:
        #             for c in metric_name.split("."):
        #                 value = value[c]
        #         except KeyError:
        #             continue
        #
        #     # value is now status[x][y][z]
        #     if not isinstance(value, (int, long, float)):
        #         raise TypeError(
        #             u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
        #                 metric_name, type(value)
        #             )
        #         )
        #
        #     # Submit the metric
        #     submit_method, metric_name_alias = self._resolve_metric(metric_name, self.metrics_to_collect)
        #     submit_method(self, metric_name_alias, value, tags=tags)

        # -- Removed by collectors: --
        #
        # for st, value in iteritems(dbstats):
        #     for metric_name in self.metrics_to_collect:
        #         if not metric_name.startswith('stats.'):
        #             continue
        #
        #         try:
        #             val = value['stats'][metric_name.split('.')[1]]
        #         except KeyError:
        #             continue
        #
        #         # value is now status[x][y][z]
        #         if not isinstance(val, (int, long, float)):
        #             raise TypeError(
        #                 u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
        #                     metric_name, type(val)
        #                 )
        #             )
        #
        #         # Submit the metric
        #         metrics_tags = tags + [
        #             u"cluster:db:{0}".format(st),  # FIXME: 8.x, was kept for backward compatibility
        #             u"db:{0}".format(st),
        #         ]
        #
        #         submit_method, metric_name_alias = self._resolve_metric(metric_name, self.metrics_to_collect)
        #         submit_method(self, metric_name_alias, val, tags=metrics_tags)

        if self.collections_indexes_stats:
            if LooseVersion(mongo_version) >= LooseVersion("3.2"):
                collector = IndexStatsCollector(self, self.db_name, self.coll_names)
                collector.collect(cli)
                # Removed by collectors:
                # self._collect_indexes_stats(db, tags)
            else:
                msg = "'collections_indexes_stats' is only available starting from mongo 3.2: your mongo version is %s"
                self.log.error(msg, mongo_version)

        # Report the usage metrics for dbs/collections
        if 'top' in self.additional_metrics:
            try:
                collector = TopCollector(self)
                collector.collect(cli)

                # Replaces:
                #     dbtop = admindb.command('top')
                #     for ns, ns_metrics in iteritems(dbtop['totals']):
                #         if "." not in ns:
                #             continue
                #
                #         # configure tags for db name and collection name
                #         dbname, collname = ns.split(".", 1)
                #         ns_tags = tags + ["db:%s" % dbname, "collection:%s" % collname]
                #
                #         # iterate over DBTOP metrics
                #         for m in metrics.TOP_METRICS:
                #             # each metric is of the form: x.y.z with z optional
                #             # and can be found at ns_metrics[x][y][z]
                #             value = ns_metrics
                #             try:
                #                 for c in m.split("."):
                #                     value = value[c]
                #             except Exception:
                #                 continue
                #
                #             # value is now status[x][y][z]
                #             if not isinstance(value, (int, long, float)):
                #                 raise TypeError(
                #                     u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
                #                         m, type(value)
                #                     )
                #                 )
                #
                #             # Submit the metric
                #             submit_method, metric_name_alias = self._resolve_metric(
                #                 m, self.metrics_to_collect, prefix="usage"
                #             )
                #             submit_method(self, metric_name_alias, value, tags=ns_tags)
                #             # Keep old incorrect metric
                #             if metric_name_alias.endswith('countps'):
                #                 self.gauge(metric_name_alias[:-2], value, tags=ns_tags)
            except Exception as e:
                self.log.warning('Failed to record `top` metrics %s', e)

        if 'local' in dbnames:  # it might not be if we are connecting through mongos
            collector = ReplicationInfoCollector(self)
            collector.collect(cli)
            # Replaces:
            # # Fetch information analogous to Mongo's db.getReplicationInfo()
            # localdb = cli['local']
            #
            # oplog_data = {}
            #
            # for ol_collection_name in ("oplog.rs", "oplog.$main"):
            #     ol_options = localdb[ol_collection_name].options()
            #     if ol_options:
            #         break
            #
            # if ol_options:
            #     try:
            #         oplog_data['logSizeMB'] = round_value(ol_options['size'] / 2.0 ** 20, 2)
            #
            #         oplog = localdb[ol_collection_name]
            #
            #         oplog_data['usedSizeMB'] = round_value(
            #             localdb.command("collstats", ol_collection_name)['size'] / 2.0 ** 20, 2
            #         )
            #
            #         op_asc_cursor = oplog.find({"ts": {"$exists": 1}}).sort("$natural", pymongo.ASCENDING).limit(1)
            #         op_dsc_cursor = oplog.find({"ts": {"$exists": 1}}).sort("$natural", pymongo.DESCENDING).limit(1)
            #
            #         try:
            #             first_timestamp = op_asc_cursor[0]['ts'].as_datetime()
            #             last_timestamp = op_dsc_cursor[0]['ts'].as_datetime()
            #             oplog_data['timeDiff'] = total_seconds(last_timestamp - first_timestamp)
            #         except (IndexError, KeyError):
            #             # if the oplog collection doesn't have any entries
            #             # if an object in the collection doesn't have a ts value, we ignore it
            #             pass
            #     except KeyError:
            #         # encountered an error trying to access options.size for the oplog collection
            #         self.log.warning(u"Failed to record `ReplicationInfo` metrics.")
            #
            # for m, value in iteritems(oplog_data):
            #     submit_method, metric_name_alias = self._resolve_metric('oplog.%s' % m, self.metrics_to_collect)
            #     submit_method(self, metric_name_alias, value, tags=tags)
        else:
            self.log.debug('"local" database not in dbnames. Not collecting ReplicationInfo metrics')

        # get collection level stats
        try:
            collector = CollStatsCollector(self, self.db_name, coll_names=self.coll_names)
            collector.collect(cli)

            # Replaces
            # # Ensure that you're on the right db
            # db = cli[self.db_name]
            # # loop through the collections
            # for coll_name in self.coll_names:
            #     # grab the stats from the collection
            #     stats = db.command("collstats", coll_name)
            #     # loop through the metrics
            #     for m in self.collection_metrics_names:
            #         coll_tags = tags + ["db:%s" % self.db_name, "collection:%s" % coll_name]
            #         value = stats.get(m, None)
            #         if value is None:
            #             continue
            #
            #         # if it's the index sizes, then it's a dict.
            #         if m == 'indexSizes':
            #             submit_method, metric_name_alias = self._resolve_metric(
            #                 'collection.%s' % m, metrics.COLLECTION_METRICS
            #             )
            #             # loop through the indexes
            #             for idx, val in iteritems(value):
            #                 # we tag the index
            #                 idx_tags = coll_tags + ["index:%s" % idx]
            #                 submit_method(self, metric_name_alias, val, tags=idx_tags)
            #         else:
            #             submit_method, metric_name_alias = self._resolve_metric(
            #                 'collection.%s' % m, metrics.COLLECTION_METRICS
            #             )
            #             submit_method(self, metric_name_alias, value, tags=coll_tags)
        except Exception as e:
            self.log.warning(u"Failed to record `collection` metrics.")
            self.log.exception(e)

        collector = CustomQueriesCollector(self, self.db_name, self.custom_queries)
        collector.collect(cli)

        # Replaces:
        # custom_query_tags = tags + ["db:{}".format(self.db_name)]
        # for raw_query in self.custom_queries:
        #     try:
        #         self._collect_custom_metrics_for_query(db, raw_query, custom_query_tags)
        #     except Exception as e:
        #         metric_prefix = raw_query.get('metric_prefix')
        #         self.log.warning("Errors while collecting custom metrics with prefix %s", metric_prefix, exc_info=e)
