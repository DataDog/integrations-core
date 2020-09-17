# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy
from distutils.version import LooseVersion

import pymongo
from six import PY3, iteritems, itervalues
from six.moves.urllib.parse import urlsplit

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
from datadog_checks.mongo.common import (
    DEFAULT_TIMEOUT,
    SERVICE_CHECK_NAME,
    MongosDeploymentType,
    ReplicaSetDeploymentType,
    StandaloneDeploymentType,
)

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

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

        # Members' last replica set state
        self._last_state = None

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
        # By default consider that this instance is a standalone, updated on each check run.
        self.deployment_type = StandaloneDeploymentType()

        # Makes a reasonable hostname for a replset membership event to mention.
        uri = urlsplit(self.clean_server_name)
        if '@' in uri.netloc:
            self.hostname = uri.netloc.split('@')[1].split(':')[0]
        else:
            self.hostname = uri.netloc.split(':')[0]
        if self.hostname == 'localhost':
            self.hostname = datadog_agent.get_hostname()

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

    def update_deployment_type(self, admindb):
        props = admindb.command("isMaster")
        if props.get("ismaster") == "isdbgrid":
            self.deployment_type = MongosDeploymentType()
        elif props.get("hosts"):
            repl_set_payload = admindb.command("replSetGetStatus")
            self.deployment_type = ReplicaSetDeploymentType(repl_set_payload)
        else:
            self.deployment_type = StandaloneDeploymentType()

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

        self.update_deployment_type(cli['admin'])
        if isinstance(self.deployment_type, ReplicaSetDeploymentType):
            tags.extend(
                [
                    "replset_name:{}".format(self.deployment_type.replset_name),
                    "replset_state:{}".format(self.deployment_type.replset_state),
                ]
            )

        try:
            mongo_version = cli.server_info().get('version', '0.0')
            self.set_metadata('version', mongo_version)
        except Exception:
            self.log.exception("Error when collecting the version from the mongo server.")
            mongo_version = '0.0'

        collector = ServerStatusCollector(self, self.db_name, tags, tcmalloc=self.collect_tcmalloc_metrics)
        try:
            collector.collect(cli)
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)

        collector = CurrentOpCollector(self, self.db_name, tags)
        collector.collect(cli)

        collector = DbStatCollector(self, self.db_name, tags)
        collector.collect(cli)

        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus  # noqa
        if self.replica_check:
            collector = ReplicaCollector(self, tags, self._last_state)
            try:
                self._last_state = collector.collect(cli)
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
            collector = DbStatCollector(self, db_n, tags)
            collector.collect(cli)

        if self.collections_indexes_stats:
            if LooseVersion(mongo_version) >= LooseVersion("3.2"):
                collector = IndexStatsCollector(self, self.db_name, tags, self.coll_names)
                collector.collect(cli)
            else:
                msg = "'collections_indexes_stats' is only available starting from mongo 3.2: your mongo version is %s"
                self.log.error(msg, mongo_version)

        # Report the usage metrics for dbs/collections
        if 'top' in self.additional_metrics:
            try:
                collector = TopCollector(self, tags)
                collector.collect(cli)
            except Exception as e:
                self.log.warning('Failed to record `top` metrics %s', e)

        if 'local' in dbnames:  # it might not be if we are connecting through mongos
            collector = ReplicationInfoCollector(self, tags)
            collector.collect(cli)
        else:
            self.log.debug('"local" database not in dbnames. Not collecting ReplicationInfo metrics')

        # get collection level stats
        try:
            collector = CollStatsCollector(self, self.db_name, tags, coll_names=self.coll_names)
            collector.collect(cli)
        except Exception as e:
            self.log.warning(u"Failed to record `collection` metrics.")
            self.log.exception(e)

        collector = CustomQueriesCollector(self, self.db_name, tags, self.custom_queries)
        collector.collect(cli)
