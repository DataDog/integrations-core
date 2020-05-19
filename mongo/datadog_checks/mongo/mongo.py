# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re
import time
from copy import deepcopy
from distutils.version import LooseVersion

import pymongo
from six import PY3, iteritems, itervalues
from six.moves.urllib.parse import unquote_plus, urlsplit, urlunparse, urlencode, quote_plus

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import round_value

from . import metrics

if PY3:
    long = int

DEFAULT_TIMEOUT = 30
ALLOWED_CUSTOM_METRICS_TYPES = ['gauge', 'rate', 'count', 'monotonic_count']
ALLOWED_CUSTOM_QUERIES_COMMANDS = ['aggregate', 'count', 'find']


def build_url(scheme, host, path='/', username=None, password=None, query_params=None):
    # type: (str, str, str, str, str, dict) -> str
    """Build an URL from individual parts. Makes sure that parts are properly URL-encoded."""
    if username and password:
        netloc = '{}:{}@{}'.format(quote_plus(username), quote_plus(password), host)
    else:
        netloc = host

    params = ""
    query = urlencode(query_params or {})
    fragment = ""

    return urlunparse([scheme, netloc, path, params, query, fragment])


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

    # Source
    SOURCE_TYPE_NAME = 'mongodb'

    # Service check
    SERVICE_CHECK_NAME = 'mongodb.can_connect'

    # Replication states
    """
    MongoDB replica set states, as documented at
    https://docs.mongodb.org/manual/reference/replica-states/
    """
    REPLSET_MEMBER_STATES = {
        0: ('STARTUP', 'Starting Up'),
        1: ('PRIMARY', 'Primary'),
        2: ('SECONDARY', 'Secondary'),
        3: ('RECOVERING', 'Recovering'),
        4: ('Fatal', 'Fatal'),  # MongoDB docs don't list this state
        5: ('STARTUP2', 'Starting up (forking threads)'),
        6: ('UNKNOWN', 'Unknown to this replset member'),
        7: ('ARBITER', 'Arbiter'),
        8: ('DOWN', 'Down'),
        9: ('ROLLBACK', 'Rollback'),
        10: ('REMOVED', 'Removed'),
    }

    def __init__(self, name, init_config, instances=None):
        super(MongoDb, self).__init__(name, init_config, instances)

        # Members' last replica set states
        self._last_state_by_server = {}

        self.collection_metrics_names = (key.split('.')[1] for key in metrics.COLLECTION_METRICS)

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
            self.server = self._build_connection_string(
                hosts,
                scheme=self.instance.get('connection_scheme', 'mongodb'),
                username=self.instance.get('username'),
                password=self.instance.get('password'),
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
        ) = self._parse_uri(self.server, sanitize_username=bool(self.ssl_params))

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
        self.tags = custom_tags + ['server:%s' % self.clean_server_name]

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

    def get_state_description(self, state):
        if state in self.REPLSET_MEMBER_STATES:
            return self.REPLSET_MEMBER_STATES[state][1]
        else:
            return 'Replset state %d is unknown to the Datadog agent' % state

    def get_state_name(self, state):
        if state in self.REPLSET_MEMBER_STATES:
            return self.REPLSET_MEMBER_STATES[state][0]
        else:
            return 'UNKNOWN'

    def _report_replica_set_state(self, state, replset_name):
        """
        Report the member's replica set state
        * Submit a service check.
        * Create an event on state change.
        """
        last_state = self._last_state_by_server.get(self.clean_server_name, -1)
        self._last_state_by_server[self.clean_server_name] = state
        if last_state != state and last_state != -1:
            return self.create_event(last_state, state, replset_name)

    def hostname_for_event(self, clean_server_name):
        """Return a reasonable hostname for a replset membership event to mention."""
        uri = urlsplit(clean_server_name)
        if '@' in uri.netloc:
            hostname = uri.netloc.split('@')[1].split(':')[0]
        else:
            hostname = uri.netloc.split(':')[0]
        if hostname == 'localhost':
            hostname = self.hostname
        return hostname

    def create_event(self, last_state, state, replset_name):
        """Create an event with a message describing the replication
            state of a mongo node"""

        status = self.get_state_description(state)
        short_status = self.get_state_name(state)
        last_short_status = self.get_state_name(last_state)
        hostname = self.hostname_for_event(self.clean_server_name)
        msg_title = "%s is %s for %s" % (hostname, short_status, replset_name)
        msg = "MongoDB %s (%s) just reported as %s (%s) for %s; it was %s before."
        msg = msg % (hostname, self.clean_server_name, status, short_status, replset_name, last_short_status)

        self.event(
            {
                'timestamp': int(time.time()),
                'source_type_name': self.SOURCE_TYPE_NAME,
                'msg_title': msg_title,
                'msg_text': msg,
                'host': hostname,
                'tags': [
                    'action:mongo_replset_member_status_change',
                    'member_status:' + short_status,
                    'previous_member_status:' + last_short_status,
                    'replset:' + replset_name,
                ],
            }
        )

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

    def _resolve_metric(self, original_metric_name, metrics_to_collect, prefix=""):
        """
        Return the submit method and the metric name to use.

        The metric name is defined as follow:
        * If available, the normalized metric name alias
        * (Or) the normalized original metric name
        """

        submit_method = (
            metrics_to_collect[original_metric_name][0]
            if isinstance(metrics_to_collect[original_metric_name], tuple)
            else metrics_to_collect[original_metric_name]
        )
        metric_name = (
            metrics_to_collect[original_metric_name][1]
            if isinstance(metrics_to_collect[original_metric_name], tuple)
            else original_metric_name
        )

        return submit_method, self._normalize(metric_name, submit_method, prefix)

    def _normalize(self, metric_name, submit_method, prefix):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "mongodb." if not prefix else "mongodb.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == metrics.RATE else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in iteritems(metrics.CASE_SENSITIVE_METRIC_NAME_SUFFIXES):
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )

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
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags, message=message
            )
            raise Exception(message)

        return authenticated

    def _build_connection_string(self, hosts, scheme, username=None, password=None, database=None, options=None):
        # type: (list, str, str, str, str, dict) -> str
        """
        Build a server connection string.

        See https://docs.mongodb.com/manual/reference/connection-string/
        """

        def add_default_port(host):
            # type: (str) -> str
            if ':' not in host:
                return '{}:27017'.format(host)
            return host

        return build_url(
            scheme,
            host=','.join(add_default_port(host) for host in hosts),
            path='/{}'.format(database) if database else '/',
            username=username,
            password=password,
            query_params=options,
        )

    @classmethod
    def _parse_uri(cls, server, sanitize_username=False):
        """
        Parses a MongoDB-formatted URI (e.g. mongodb://user:pass@server/db) and returns parsed elements
        and a sanitized URI.
        """
        parsed = pymongo.uri_parser.parse_uri(server)

        username = parsed.get('username')
        password = parsed.get('password')
        db_name = parsed.get('database')
        nodelist = parsed.get('nodelist')
        auth_source = parsed.get('options', {}).get('authsource')

        # Remove password (and optionally username) from sanitized server URI.
        # To ensure that the `replace` works well, we first need to url-decode the raw server string
        # since the password parsed by pymongo is url-decoded
        decoded_server = unquote_plus(server)
        clean_server_name = decoded_server.replace(password, "*" * 5) if password else decoded_server

        if sanitize_username and username:
            username_pattern = u"{}[@:]".format(re.escape(username))
            clean_server_name = re.sub(username_pattern, "", clean_server_name)

        return username, password, db_name, nodelist, clean_server_name, auth_source

    def _collect_indexes_stats(self, db, tags):
        """
        Collect indexes statistics for all collections in the configuration.
        This use the "$indexStats" command.
        """
        for coll_name in self.coll_names:
            try:
                for stats in db[coll_name].aggregate([{"$indexStats": {}}], cursor={}):
                    idx_tags = tags + [
                        "name:{0}".format(stats.get('name', 'unknown')),
                        "collection:{0}".format(coll_name),
                    ]
                    val = int(stats.get('accesses', {}).get('ops', 0))
                    self.gauge('mongodb.collection.indexes.accesses.ops', val, idx_tags)
            except Exception as e:
                self.log.error("Could not fetch indexes stats for collection %s: %s", coll_name, e)

    def _get_submission_method(self, method_name):
        if method_name not in ALLOWED_CUSTOM_METRICS_TYPES:
            raise ValueError('Metric type {} is not one of {}.'.format(method_name, ALLOWED_CUSTOM_METRICS_TYPES))
        return getattr(self, method_name)

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

    def _collect_custom_metrics_for_query(self, db, raw_query, tags):
        """Validates the raw_query object, executes the mongo query then submits the metrics to datadog"""
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

    def check(self, _):
        """
        Returns a dictionary that looks a lot like what's sent back by
        db.serverStatus()
        """

        def total_seconds(td):
            """
            Returns total seconds of a timedelta in a way that's safe for
            Python < 2.7
            """
            if hasattr(td, 'total_seconds'):
                return td.total_seconds()
            else:
                return (lag.microseconds + (lag.seconds + lag.days * 24 * 3600) * 10 ** 6) / 10.0 ** 6

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
            admindb = cli['admin']
            db = cli[self.db_name]
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            raise

        if self.do_auth:
            if self.auth_source:
                msg = "authSource was specified in the the server URL: using '%s' as the authentication database"
                self.log.info(msg, self.auth_source)
                self._authenticate(cli[self.auth_source])
            else:
                self._authenticate(db)

        try:
            status = db.command('serverStatus', tcmalloc=self.collect_tcmalloc_metrics)
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)

        if status['ok'] == 0:
            raise Exception(status['errmsg'].__str__())

        ops = db.current_op()
        status['fsyncLocked'] = 1 if ops.get('fsyncLock') else 0

        status['stats'] = db.command('dbstats')
        dbstats = {self.db_name: {'stats': status['stats']}}
        try:
            mongo_version = cli.server_info().get('version', '0.0')
            self.set_metadata('version', mongo_version)
        except Exception:
            self.log.exception("Error when collecting the version from the mongo server.")
            mongo_version = '0.0'

        tags = deepcopy(self.tags)
        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus  # noqa
        if self.replica_check:
            try:
                data = {}

                replSet = admindb.command('replSetGetStatus')
                if replSet:
                    primary = None
                    current = None

                    # need a new connection to deal with replica sets
                    setname = replSet.get('set')
                    cli_rs = pymongo.mongo_client.MongoClient(
                        self.server,
                        socketTimeoutMS=self.timeout,
                        connectTimeoutMS=self.timeout,
                        serverSelectionTimeoutMS=self.timeout,
                        replicaset=setname,
                        read_preference=pymongo.ReadPreference.NEAREST,
                        **self.ssl_params
                    )

                    if self.do_auth:
                        if self.auth_source:
                            self._authenticate(cli_rs[self.auth_source])
                        else:
                            self._authenticate(cli_rs[self.db_name])

                    # Replication set information
                    replset_name = replSet['set']
                    replset_state = self.get_state_name(replSet['myState']).lower()

                    tags.extend([u"replset_name:{0}".format(replset_name), u"replset_state:{0}".format(replset_state)])

                    # Find nodes: master and current node (ourself)
                    for member in replSet.get('members'):
                        if member.get('self'):
                            current = member
                        if int(member.get('state')) == 1:
                            primary = member

                    # Compute a lag time
                    if current is not None and primary is not None:
                        if 'optimeDate' in primary and 'optimeDate' in current:
                            lag = primary['optimeDate'] - current['optimeDate']
                            data['replicationLag'] = total_seconds(lag)

                    if current is not None:
                        data['health'] = current['health']

                    data['state'] = replSet['myState']

                    if current is not None:
                        total = 0.0
                        cfg = cli_rs['local']['system.replset'].find_one()
                        for member in cfg.get('members'):
                            total += member.get('votes', 1)
                            if member['_id'] == current['_id']:
                                data['votes'] = member.get('votes', 1)
                        data['voteFraction'] = data['votes'] / total

                    status['replSet'] = data

                    # Submit events
                    self._report_replica_set_state(data['state'], replset_name)

            except Exception as e:
                if "OperationFailure" in repr(e) and (
                    "not running with --replSet" in str(e) or "replSetGetStatus" in str(e)
                ):
                    pass
                else:
                    raise e

        # If these keys exist, remove them for now as they cannot be serialized
        try:
            status['backgroundFlushing'].pop('last_finished')
        except KeyError:
            pass
        try:
            status.pop('localTime')
        except KeyError:
            pass

        dbnames = cli.list_database_names()
        self.gauge('mongodb.dbs', len(dbnames), tags=tags)

        for db_n in dbnames:
            db_aux = cli[db_n]
            dbstats[db_n] = {'stats': db_aux.command('dbstats')}

        # Go through the metrics and save the values
        for metric_name in self.metrics_to_collect:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = status

            if metric_name.startswith('stats'):
                continue
            else:
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
            submit_method, metric_name_alias = self._resolve_metric(metric_name, self.metrics_to_collect)
            submit_method(self, metric_name_alias, value, tags=tags)

        for st, value in iteritems(dbstats):
            for metric_name in self.metrics_to_collect:
                if not metric_name.startswith('stats.'):
                    continue

                try:
                    val = value['stats'][metric_name.split('.')[1]]
                except KeyError:
                    continue

                # value is now status[x][y][z]
                if not isinstance(val, (int, long, float)):
                    raise TypeError(
                        u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
                            metric_name, type(val)
                        )
                    )

                # Submit the metric
                metrics_tags = tags + [
                    u"cluster:db:{0}".format(st),  # FIXME 6.0 - keep for backward compatibility
                    u"db:{0}".format(st),
                ]

                submit_method, metric_name_alias = self._resolve_metric(metric_name, self.metrics_to_collect)
                submit_method(self, metric_name_alias, val, tags=metrics_tags)

        if self.collections_indexes_stats:
            if LooseVersion(mongo_version) >= LooseVersion("3.2"):
                self._collect_indexes_stats(db, tags)
            else:
                msg = "'collections_indexes_stats' is only available starting from mongo 3.2: your mongo version is %s"
                self.log.error(msg, mongo_version)

        # Report the usage metrics for dbs/collections
        if 'top' in self.additional_metrics:
            try:
                dbtop = admindb.command('top')
                for ns, ns_metrics in iteritems(dbtop['totals']):
                    if "." not in ns:
                        continue

                    # configure tags for db name and collection name
                    dbname, collname = ns.split(".", 1)
                    ns_tags = tags + ["db:%s" % dbname, "collection:%s" % collname]

                    # iterate over DBTOP metrics
                    for m in metrics.TOP_METRICS:
                        # each metric is of the form: x.y.z with z optional
                        # and can be found at ns_metrics[x][y][z]
                        value = ns_metrics
                        try:
                            for c in m.split("."):
                                value = value[c]
                        except Exception:
                            continue

                        # value is now status[x][y][z]
                        if not isinstance(value, (int, long, float)):
                            raise TypeError(
                                u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
                                    m, type(value)
                                )
                            )

                        # Submit the metric
                        submit_method, metric_name_alias = self._resolve_metric(
                            m, self.metrics_to_collect, prefix="usage"
                        )
                        submit_method(self, metric_name_alias, value, tags=ns_tags)
                        # Keep old incorrect metric
                        if metric_name_alias.endswith('countps'):
                            self.gauge(metric_name_alias[:-2], value, tags=ns_tags)
            except Exception as e:
                self.log.warning('Failed to record `top` metrics %s', e)

        if 'local' in dbnames:  # it might not be if we are connectiing through mongos
            # Fetch information analogous to Mongo's db.getReplicationInfo()
            localdb = cli['local']

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
                        oplog_data['timeDiff'] = total_seconds(last_timestamp - first_timestamp)
                    except (IndexError, KeyError):
                        # if the oplog collection doesn't have any entries
                        # if an object in the collection doesn't have a ts value, we ignore it
                        pass
                except KeyError:
                    # encountered an error trying to access options.size for the oplog collection
                    self.log.warning(u"Failed to record `ReplicationInfo` metrics.")

            for m, value in iteritems(oplog_data):
                submit_method, metric_name_alias = self._resolve_metric('oplog.%s' % m, self.metrics_to_collect)
                submit_method(self, metric_name_alias, value, tags=tags)

        else:
            self.log.debug('"local" database not in dbnames. Not collecting ReplicationInfo metrics')

        # get collection level stats
        try:
            # Ensure that you're on the right db
            db = cli[self.db_name]
            # loop through the collections
            for coll_name in self.coll_names:
                # grab the stats from the collection
                stats = db.command("collstats", coll_name)
                # loop through the metrics
                for m in self.collection_metrics_names:
                    coll_tags = tags + ["db:%s" % self.db_name, "collection:%s" % coll_name]
                    value = stats.get(m, None)
                    if not value:
                        continue

                    # if it's the index sizes, then it's a dict.
                    if m == 'indexSizes':
                        submit_method, metric_name_alias = self._resolve_metric(
                            'collection.%s' % m, metrics.COLLECTION_METRICS
                        )
                        # loop through the indexes
                        for idx, val in iteritems(value):
                            # we tag the index
                            idx_tags = coll_tags + ["index:%s" % idx]
                            submit_method(self, metric_name_alias, val, tags=idx_tags)
                    else:
                        submit_method, metric_name_alias = self._resolve_metric(
                            'collection.%s' % m, metrics.COLLECTION_METRICS
                        )
                        submit_method(self, metric_name_alias, value, tags=coll_tags)
        except Exception as e:
            self.log.warning(u"Failed to record `collection` metrics.")
            self.log.exception(e)

        custom_query_tags = tags + ["db:{}".format(self.db_name)]
        for raw_query in self.custom_queries:
            try:
                self._collect_custom_metrics_for_query(db, raw_query, custom_query_tags)
            except Exception as e:
                metric_prefix = raw_query.get('metric_prefix')
                self.log.warning("Errors while collecting custom metrics with prefix %s", metric_prefix, exc_info=e)
