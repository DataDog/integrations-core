from pymongo import MongoClient, ReadPreference
from pymongo.errors import PyMongoError

from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment, StandaloneDeployment

# The name of the application that created this MongoClient instance. MongoDB 3.4 and newer will print this value in
# the server log upon establishing each connection. It is also recorded in the slow query log and profile collections.
DD_APP_NAME = 'datadog-agent'


class MongoApi(object):
    def __init__(self, config, log, replicaset=None):
        self._config = config
        self._log = log
        self.deployment_type = None
        if self._config.server:
            # Deprecated option
            self._cli = MongoClient(
                self._config.server,
                socketTimeoutMS=self._config.timeout,
                connectTimeoutMS=self._config.timeout,
                serverSelectionTimeoutMS=self._config.timeout,
                read_preference=ReadPreference.PRIMARY_PREFERRED,
                replicaSet=replicaset,
                **self._config.ssl_params
            )
        else:
            merged_options_dict = {}
            merged_options_dict.update(self._config.additional_options)
            merged_options_dict.update(self._config.ssl_params)
            self._cli = MongoClient(
                host=self._config.hosts,
                socketTimeoutMS=self._config.timeout,
                connectTimeoutMS=self._config.timeout,
                serverSelectionTimeoutMS=self._config.timeout,
                read_preference=ReadPreference.PRIMARY_PREFERRED,
                replicaSet=replicaset,
                appname=DD_APP_NAME,
                **merged_options_dict
            )
        self._initialize()

    def __getitem__(self, item):
        return self._cli[item]

    def server_info(self, session=None):
        return self._cli.server_info(session)

    def list_database_names(self, session=None):
        return self._cli.list_database_names(session)

    def _initialize(self):
        self._log.debug("Connecting to '%s'", self._config.hosts)

        is_master_payload = self['admin'].command('isMaster')
        is_arbiter = is_master_payload.get('arbiterOnly', False)

        if not is_arbiter and self._config.do_auth:
            self._log.info("Using '%s' as the authentication database", self._config.auth_source)
            self._authenticate()

        self.deployment_type = self._get_deployment_type()

    def _authenticate(self):
        """
        Authenticate to the database.

        Available mechanisms:
        * Username & password
        * X.509

        More information:
        https://api.mongodb.com/python/current/examples/authentication.html
        """
        authenticated = False
        database = self[self._config.auth_source]
        username = self._config.username
        try:
            # X.509
            if self._config.use_x509 and username:
                self._log.debug(u"Authenticate `%s` to `%s` using `MONGODB-X509` mechanism", username, database)
                authenticated = database.authenticate(username, mechanism='MONGODB-X509')
            elif self._config.use_x509:
                self._log.debug(u"Authenticate to `%s` using `MONGODB-X509` mechanism", database)
                authenticated = database.authenticate(mechanism='MONGODB-X509')
            # Username & password
            else:
                authenticated = database.authenticate(username, self._config.password)

        except PyMongoError as e:
            self._log.error(u"Authentication failed due to invalid credentials or configuration issues. %s", e)

        return authenticated

    def _get_deployment_type(self):
        # getCmdLineOpts is the runtime configuration of the mongo instance. Helpful to know whether the node is
        # a mongos or mongod, if the mongod is in a shard, if it's in a replica set, etc.
        options = self['admin'].command("getCmdLineOpts")['parsed']
        cluster_role = None
        if 'sharding' in options:
            if 'configDB' in options['sharding']:
                return MongosDeployment()
            elif 'clusterRole' in options['sharding']:
                cluster_role = options['sharding']['clusterRole']

        replication_options = options.get('replication', {})
        if 'replSetName' in replication_options or 'replSet' in replication_options:
            repl_set_payload = self['admin'].command("replSetGetStatus")
            replset_name = repl_set_payload["set"]
            replset_state = repl_set_payload["myState"]
            return ReplicaSetDeployment(replset_name, replset_state, cluster_role=cluster_role)

        return StandaloneDeployment()
