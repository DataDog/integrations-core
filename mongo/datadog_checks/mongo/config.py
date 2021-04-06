from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.mongo.common import DEFAULT_TIMEOUT
from datadog_checks.mongo.utils import build_connection_string, parse_mongo_uri


class MongoConfig(object):
    def __init__(self, instance, log):
        self.log = log

        # x.509 authentication
        self.ssl_params = exclude_undefined_keys(
            {
                'ssl': instance.get('ssl', None),
                'ssl_keyfile': instance.get('ssl_keyfile', None),
                'ssl_certfile': instance.get('ssl_certfile', None),
                'ssl_cert_reqs': instance.get('ssl_cert_reqs', None),
                'ssl_ca_certs': instance.get('ssl_ca_certs', None),
            }
        )

        if 'server' in instance:
            self.server = instance['server']
            (
                self.username,
                self.password,
                self.db_name,
                self.hosts,
                _,
                self.auth_source,
            ) = parse_mongo_uri(self.server, sanitize_username=bool(self.ssl_params))
            self.scheme = None
            self.additional_options = {}
            self.hosts = ["%s:%s" % (host[0], host[1]) for host in self.hosts]
        else:
            self.server = None
            self.hosts = instance.get('hosts', [])
            self.username = instance.get('username')
            self.password = instance.get('password')
            self.scheme = instance.get('connection_scheme', 'mongodb')
            self.db_name = instance.get('database')
            self.additional_options = instance.get('options', {})
            self.auth_source = self.additional_options.get('authsource') or self.db_name or 'admin'

        if not self.hosts:
            raise ConfigurationError('No `hosts` specified')

        self.clean_server_name = self._get_clean_server_name()
        if self.password and not self.username:
            raise ConfigurationError('`username` must be set when a `password` is specified')

        if not self.db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            self.db_name = 'admin'

        self.timeout = float(instance.get('timeout', DEFAULT_TIMEOUT)) * 1000
        self.additional_metrics = instance.get('additional_metrics', [])

        # Authenticate
        self.do_auth = True
        self.use_x509 = self.ssl_params and not self.password
        if not self.username:
            self.log.info("Disabling authentication because a username was not provided.")
            self.do_auth = False

        self.replica_check = is_affirmative(instance.get('replica_check', True))
        self.collections_indexes_stats = is_affirmative(instance.get('collections_indexes_stats'))
        self.coll_names = instance.get('collections', [])
        self.custom_queries = instance.get("custom_queries", [])

        self._base_tags = list(set(instance.get('tags', [])))
        self.service_check_tags = self._compute_service_check_tags()
        self.metric_tags = self._compute_metric_tags()

    def _get_clean_server_name(self):
        if not self.server:
            server = build_connection_string(
                self.hosts,
                username=self.username,
                password=self.password,
                scheme=self.scheme,
                database=self.db_name,
                options=self.additional_options,
            )
        else:
            server = self.server
        return parse_mongo_uri(server, sanitize_username=bool(self.ssl_params))[4]

    def _compute_service_check_tags(self):
        main_host = self.hosts[0]
        main_port = "27017"
        if ':' in main_host:
            main_host, main_port = main_host.split(':')

        service_check_tags = ["db:%s" % self.db_name, "host:%s" % main_host, "port:%s" % main_port] + self._base_tags
        return service_check_tags

    def _compute_metric_tags(self):
        return self._base_tags + ['server:%s' % self.clean_server_name]
