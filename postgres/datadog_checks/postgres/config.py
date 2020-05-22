# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200


class PostgresConfig:
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    def __init__(self, instance):
        self.host = instance.get('host', '')
        self.port = instance.get('port', '')
        if self.port != '':
            self.port = int(self.port)
        self.dbname = instance.get('dbname', 'postgres')
        self.query_timeout = instance.get('query_timeout')
        self.relations = instance.get('relations', [])
        if self.relations and not self.dbname:
            raise ConfigurationError('"dbname" parameter must be set when using the "relations" parameter.')

        self.tags = self._build_tags(instance.get('tags', []))

        ssl = instance.get('ssl', False)
        if ssl in SSL_MODES:
            self.ssl_mode = ssl
        else:
            self.ssl_mode = 'require' if is_affirmative(ssl) else 'disable'

        self.user = instance.get('username', '')
        self.password = instance.get('password', '')

        self.table_count_limit = instance.get('table_count_limit', TABLE_COUNT_LIMIT)
        self.collect_function_metrics = is_affirmative(instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        self.collect_count_metrics = is_affirmative(instance.get('collect_count_metrics', True))
        self.collect_activity_metrics = is_affirmative(instance.get('collect_activity_metrics', False))
        self.collect_database_size_metrics = is_affirmative(instance.get('collect_database_size_metrics', True))
        self.collect_default_db = is_affirmative(instance.get('collect_default_database', False))
        self.collect_statement_metrics = is_affirmative(instance.get('collect_statement_metrics', False))
        self.custom_queries = instance.get('custom_queries', [])

        if not self.host:
            raise ConfigurationError('Please specify a Postgres host to connect to.')
        elif not self.user:
            raise ConfigurationError('Please specify a user to connect to Postgres as.')

        self.tag_replication_role = is_affirmative(instance.get('tag_replication_role', False))
        self.service_check_tags = self._get_service_check_tags()
        self.custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []))
        self.max_relations = int(instance.get('max_relations', 300))

    def _build_tags(self, custom_tags):
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if custom_tags is None:
            tags = []
        else:
            tags = list(set(custom_tags))

        # preset tags to host
        tags.append('server:{}'.format(self.host))
        if self.port:
            tags.append('port:{}'.format(self.port))
        else:
            tags.append('port:socket')

        # preset tags to the database name
        tags.extend(["db:%s" % self.dbname])
        return tags

    def _get_service_check_tags(self):
        service_check_tags = ["host:%s" % self.host]
        service_check_tags.extend(self.tags)
        service_check_tags = list(set(service_check_tags))
        return service_check_tags

    @staticmethod
    def _get_custom_metrics(custom_metrics):
        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

            # Old formatting to new formatting. The first params is always the columns names from which to
            # read metrics. The `relation` param instructs the check to replace the next '%s' with the list of
            # relations names.
            if m['relation']:
                m['query'] = m['query'] % ('{metrics_columns}', '{relations_names}')
            else:
                m['query'] = m['query'] % '{metrics_columns}'

            try:
                for ref, (_, mtype) in iteritems(m['metrics']):
                    cap_mtype = mtype.upper()
                    if cap_mtype not in ('RATE', 'GAUGE', 'MONOTONIC'):
                        raise ConfigurationError(
                            'Collector method {} is not known. '
                            'Known methods are RATE, GAUGE, MONOTONIC'.format(cap_mtype)
                        )

                    m['metrics'][ref][1] = getattr(PostgresConfig, cap_mtype)
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
        return custom_metrics
