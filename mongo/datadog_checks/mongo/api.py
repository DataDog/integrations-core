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

from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment, StandaloneDeployment

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
            'directConnection': True,
            'read_preference': ReadPreference.PRIMARY_PREFERRED,
            'appname': DD_APP_NAME,
        }
        if replicaset:
            options['replicaSet'] = replicaset
        options.update(self._config.additional_options)
        options.update(self._config.tls_params)
        if self._config.do_auth and not self._is_arbiter(options):
            self._log.info("Using '%s' as the authentication database", self._config.auth_source)
            if self._config.username:
                options['username'] = self._config.username
            if self._config.password:
                options['password'] = self._config.password
            if self._config.auth_source:
                options['authSource'] = self._config.auth_source
        self._log.debug("options: %s", options)
        self._cli = MongoClient(**options)
        self.deployment_type = None

    def __getitem__(self, item):
        return self._cli[item]

    def connect(self):
        try:
            # The ping command is cheap and does not require auth.
            self['admin'].command('ping')
        except ConnectionFailure as e:
            self._log.debug('ConnectionFailure: %s', e)
            raise

    def server_info(self, session=None):
        return self._cli.server_info(session)

    def list_database_names(self, session=None):
        return self._cli.list_database_names(session)

    def _is_arbiter(self, options):
        cli = MongoClient(**options)
        is_master_payload = cli['admin'].command('isMaster')
        return is_master_payload.get('arbiterOnly', False)

    @staticmethod
    def _get_rs_deployment_from_status_payload(repl_set_payload, cluster_role):
        replset_name = repl_set_payload["set"]
        replset_state = repl_set_payload["myState"]
        return ReplicaSetDeployment(replset_name, replset_state, cluster_role=cluster_role)

    def refresh_deployment_type(self):
        # getCmdLineOpts is the runtime configuration of the mongo instance. Helpful to know whether the node is
        # a mongos or mongod, if the mongod is in a shard, if it's in a replica set, etc.
        try:
            options = self['admin'].command("getCmdLineOpts")['parsed']
        except Exception as e:
            self._log.debug(
                "Unable to run `getCmdLineOpts`, got: %s. Assuming this is an Alibaba ApsaraDB instance.", str(e)
            )
            # `getCmdLineOpts` is forbidden on Alibaba ApsaraDB
            self.deployment_type = self._get_alibaba_deployment_type()
            return
        cluster_role = None
        if 'sharding' in options:
            if 'configDB' in options['sharding']:
                self._log.debug("Detected MongosDeployment. Node is principal.")
                self.deployment_type = MongosDeployment()
                return
            elif 'clusterRole' in options['sharding']:
                cluster_role = options['sharding']['clusterRole']

        replication_options = options.get('replication', {})
        if 'replSetName' in replication_options or 'replSet' in replication_options:
            repl_set_payload = self['admin'].command("replSetGetStatus")
            replica_set_deployment = self._get_rs_deployment_from_status_payload(repl_set_payload, cluster_role)
            is_principal = replica_set_deployment.is_principal()
            is_principal_log = "" if is_principal else "not "
            self._log.debug("Detected ReplicaSetDeployment. Node is %sprincipal.", is_principal_log)
            self.deployment_type = replica_set_deployment
            return

        self._log.debug("Detected StandaloneDeployment. Node is principal.")
        self.deployment_type = StandaloneDeployment()

    def _get_alibaba_deployment_type(self):
        is_master_payload = self['admin'].command('isMaster')
        if is_master_payload.get('msg') == 'isdbgrid':
            return MongosDeployment()

        # On alibaba cloud, a mongo node is either a mongos or part of a replica set.
        repl_set_payload = self['admin'].command("replSetGetStatus")
        if repl_set_payload.get('configsvr') is True:
            cluster_role = 'configsvr'
        elif self['admin'].command('shardingState').get('enabled') is True:
            # Use `shardingState` command to know whether or not the replicaset
            # is a shard or not.
            cluster_role = 'shardsvr'
        else:
            cluster_role = None
        return self._get_rs_deployment_from_status_payload(repl_set_payload, cluster_role)
