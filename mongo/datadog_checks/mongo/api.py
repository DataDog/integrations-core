# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from pymongo import MongoClient, ReadPreference
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    OperationFailure,
    ProtocolError,
    ServerSelectionTimeoutError,
)

# The name of the application that created this MongoClient instance. MongoDB 3.4 and newer will print this value in
# the server log upon establishing each connection. It is also recorded in the slow query log and profile collections.
DD_APP_NAME = 'datadog-agent'

# We collect here all pymongo exceptions that would result in a CRITICAL service check.
CRITICAL_FAILURE = (
    ConfigurationError,  # This occurs when TLS is misconfigured.
    ConnectionFailure,  # This is a generic exception for any problems when connecting to mongodb.
    OperationFailure,  # This occurs when authentication is incorrect.
    # This means either no server is available or a replicaset has not elected a primary in the timeout window.
    # In both cases it makes sense to submit a CRITICAL service check to Datadog.
    ServerSelectionTimeoutError,
    # Errors at the level of the protocol result in a lost/degraded connection. We can issue a CRITICAL check for this.
    ProtocolError,
)

DD_OPERATION_ATTRIBUTES = {
    'service': DD_APP_NAME,
}


class MongoApi(object):
    """Mongodb connection through pymongo.MongoClient

    :params config: MongoConfig object.
    :params log: Check log.
    :params replicaset: If replication is enabled, this parameter specifies the name of the replicaset.
        Valid for ReplicaSetDeployment deployments
    """

    def __init__(self, config, log, replicaset: str = None):
        self._config = config
        self._log = log
        options = {
            'host': self._config.server if self._config.server else self._config.hosts,
            'socketTimeoutMS': self._config.timeout,
            'connectTimeoutMS': self._config.timeout,
            'serverSelectionTimeoutMS': self._config.timeout,
            'timeoutMS': self._config.timeout,
            'directConnection': True,
            'read_preference': ReadPreference.PRIMARY_PREFERRED,
            'appname': DD_APP_NAME,
            'compressors': 'zlib',  # Enable zlib compression
        }
        if replicaset:
            options['replicaSet'] = replicaset
        options.update(self._config.additional_options)
        options.update(self._config.tls_params)
        if self._config.do_auth and self._is_auth_required(options):
            self._log.info("Using '%s' as the authentication database", self._config.auth_source)
            if self._config.username:
                options['username'] = self._config.username
            if self._config.password:
                options['password'] = self._config.password
            if self._config.auth_source:
                options['authSource'] = self._config.auth_source
        self._log.debug("options: %s", options)
        self._cli = MongoClient(**options)
        self.__hostname = None

        # Check if the server supports the $collStats aggregation pipeline stage.
        self.coll_stats_pipeline_supported = True
        self.__comment = ",".join([f"{k}='{v}'" for k, v in DD_OPERATION_ATTRIBUTES.items()])

    def __getitem__(self, item):
        return self._cli[item]

    def connect(self):
        try:
            # The ping command is cheap and does not require auth.
            self.ping()
        except ConnectionFailure as e:
            self._log.debug('ConnectionFailure: %s', e)
            raise

    def ping(self):
        return self['admin'].command('ping', comment=self.__comment)

    def server_info(self, session=None):
        return self._cli.server_info(session)

    def list_database_names(self, session=None):
        return self._cli.list_database_names(session, comment=self.__comment)

    def current_op(self, session=None):
        # Use $currentOp stage to get all users and idle sessions.
        # Note: Why not use the `currentOp` command?
        # Because the currentOp command and db.currentOp() helper method return the results in a single document,
        # the total size of the currentOp result set is subject to the maximum 16MB BSON size limit for documents.
        # The $currentOp stage returns a cursor over a stream of documents, each of which reports a single operation.
        return self["admin"].aggregate([{'$currentOp': {'allUsers': True}}], session=session, comment=self.__comment)

    def get_collection_stats(self, db_name, coll_name, stats=None, session=None):
        if not self.coll_stats_pipeline_supported:
            return [self.coll_stats_compatible(db_name, coll_name, session)]
        try:
            return self.coll_stats(db_name, coll_name, stats, session)
        except OperationFailure as e:
            if e.code == 13:
                # Unauthorized to run $collStats, do not try use the compatible mode, raise the exception
                raise e
            # Failed to get collection stats using $collStats aggregation
            self._log.debug(
                "Failed to collect stats for collection %s with $collStats, fallback to collStats command",
                coll_name,
                e.details,
            )
            self.coll_stats_pipeline_supported = False
            return [self.coll_stats_compatible(db_name, coll_name, session)]

    def coll_stats(self, db_name, coll_name, stats=None, session=None):
        if not stats:
            stats = {"latencyStats", "storageStats", "queryExecStats"}
        stats = {stat: {} for stat in stats}

        return self[db_name][coll_name].aggregate(
            [
                {
                    "$collStats": stats,
                },
            ],
            session=session,
            comment=self.__comment,
        )

    def coll_stats_compatible(self, db_name, coll_name, session=None):
        # collStats is deprecated in MongoDB 6.2. Use the $collStats aggregation stage instead.
        return self[db_name].command({'collStats': coll_name}, session=session, comment=self.__comment)

    def index_stats(self, db_name, coll_name, session=None):
        return self[db_name][coll_name].aggregate([{"$indexStats": {}}], session=session, comment=self.__comment)

    def index_information(self, db_name, coll_name, session=None):
        return self[db_name][coll_name].index_information(session=session, comment=self.__comment)

    def list_search_indexes(self, db_name, coll_name, session=None):
        return self[db_name][coll_name].list_search_indexes(session=session, comment=self.__comment)

    def sharded_data_distribution_stats(self, session=None):
        return self["admin"].aggregate([{"$shardedDataDistribution": {}}], session=session, comment=self.__comment)

    def _is_auth_required(self, options):
        # Check if the node is an arbiter. If it is, usually it does not require authentication.
        # However this is a best-effort check as the replica set might focce authentication.
        try:
            # Try connect to the admin database to run the isMaster command without authentication.
            cli = MongoClient(**options)
            is_master_payload = cli['admin'].command('isMaster', comment=self.__comment)
            is_arbiter = is_master_payload.get('arbiterOnly', False)
            # If the node is an arbiter and we are able to connect without authentication
            # we can assume that the node does not require authentication.
            return not is_arbiter
        except:
            return True

    def get_profiling_level(self, db_name, session=None):
        return self[db_name].command('profile', -1, session=session, comment=self.__comment)

    def get_profiling_data(self, db_name, ts, session=None):
        filter = {'ts': {'$gt': ts}}
        return self[db_name]['system.profile'].find(filter, session=session, comment=self.__comment).sort('ts', 1)

    def get_log_data(self, session=None):
        return self['admin'].command("getLog", "global", session=session, comment=self.__comment)

    def sample(self, db_name, coll_name, sample_size, session=None):
        return self[db_name][coll_name].aggregate(
            [{"$sample": {"size": sample_size}}], session=session, comment=self.__comment
        )

    def get_cmdline_opts(self):
        return self["admin"].command("getCmdLineOpts", comment=self.__comment)["parsed"]

    def replset_get_status(self):
        return self["admin"].command("replSetGetStatus", comment=self.__comment)

    def is_master(self):
        return self["admin"].command("isMaster", comment=self.__comment)

    def sharding_state_is_enabled(self):
        return self["admin"].command("shardingState", comment=self.__comment).get("enabled", False)

    def get_shard_map(self):
        return self['admin'].command('getShardMap', comment=self.__comment)

    def server_status(self):
        return self['admin'].command('serverStatus', comment=self.__comment)

    def list_authorized_collections(
        self,
        db_name,
        limit=None,
    ):
        coll_names = []
        try:
            coll_names = self[db_name].list_collection_names(
                filter={"type": "collection"},  # Only return collections, not views
                authorizedCollections=True,
                comment=self.__comment,
            )
        except OperationFailure as e:
            if e.code == 303 and e.details.get("errmsg") == "Field 'type' is currently not supported":
                # Filter by type is not supported on AWS DocumentDB
                coll_names = self[db_name].list_collection_names(authorizedCollections=True, comment=self.__comment)
            else:
                # The user is not authorized to run listCollections on this database.
                # This is NOT a critical error, so we log it as a warning.
                self._log.warning(
                    "Not authorized to run 'listCollections' on db %s, "
                    "please make sure the user has read access on the database or "
                    "add the database to the `database_autodiscovery.exclude` list in the configuration file",
                    db_name,
                )
        if limit:
            return coll_names[:limit]
        return coll_names

    def is_collection_sharded(self, db_name, coll_name):
        try:
            # Check if the collection is sharded by looking for the collection config
            # in the config.collections collection.
            collection_config = self["config"]["collections"].find_one(
                {"_id": f"{db_name}.{coll_name}"}, comment=self.__comment
            )
            return collection_config is not None
        except OperationFailure as e:
            self._log.warning("Could not determine if collection %s.%s is sharded: %s", db_name, coll_name, e)
            return False

    @property
    def hostname(self):
        if self.__hostname:
            return self.__hostname
        try:
            self.__hostname = self.server_status()['host']
            if ':' not in self.__hostname:
                # If there is no port, we assume the default port
                self.__hostname += ':27017'
            return self.__hostname
        except Exception as e:
            self._log.error('Unable to get hostname: %s', e)
            return None
