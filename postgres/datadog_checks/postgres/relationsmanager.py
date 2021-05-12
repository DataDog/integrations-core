# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any, Dict, List, Union

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import get_check_logger

ALL_SCHEMAS = object()
RELATION_NAME = 'relation_name'
RELATION_REGEX = 'relation_regex'
SCHEMAS = 'schemas'

LOCK_METRICS = {
    'descriptors': [
        ('mode', 'lock_mode'),
        ('locktype', 'lock_type'),
        ('nspname', 'schema'),
        ('datname', 'db'),
        ('relname', 'table'),
    ],
    'metrics': {'lock_count': ('postgresql.locks', AgentCheck.gauge)},
    'query': """
SELECT mode,
       locktype,
       pn.nspname,
       pd.datname,
       pc.relname,
       count(*) AS {metrics_columns}
  FROM pg_locks l
  JOIN pg_database pd ON (l.database = pd.oid)
  JOIN pg_class pc ON (l.relation = pc.oid)
  LEFT JOIN pg_namespace pn ON (pn.oid = pc.relnamespace)
 WHERE {relations}
   AND l.mode IS NOT NULL
   AND pc.relname NOT LIKE 'pg_%%'
 GROUP BY pd.datname, pc.relname, pn.nspname, locktype, mode""",
    'relation': True,
}

REL_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
    'metrics': {
        'seq_scan': ('postgresql.seq_scans', AgentCheck.rate),
        'seq_tup_read': ('postgresql.seq_rows_read', AgentCheck.rate),
        'idx_scan': ('postgresql.index_rel_scans', AgentCheck.rate),
        'idx_tup_fetch': ('postgresql.index_rel_rows_fetched', AgentCheck.rate),
        'n_tup_ins': ('postgresql.rows_inserted', AgentCheck.rate),
        'n_tup_upd': ('postgresql.rows_updated', AgentCheck.rate),
        'n_tup_del': ('postgresql.rows_deleted', AgentCheck.rate),
        'n_tup_hot_upd': ('postgresql.rows_hot_updated', AgentCheck.rate),
        'n_live_tup': ('postgresql.live_rows', AgentCheck.gauge),
        'n_dead_tup': ('postgresql.dead_rows', AgentCheck.gauge),
    },
    'query': """
SELECT relname,schemaname,{metrics_columns}
  FROM pg_stat_user_tables
 WHERE {relations}""",
    'relation': True,
}

IDX_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema'), ('indexrelname', 'index')],
    'metrics': {
        'idx_scan': ('postgresql.index_scans', AgentCheck.rate),
        'idx_tup_read': ('postgresql.index_rows_read', AgentCheck.rate),
        'idx_tup_fetch': ('postgresql.index_rows_fetched', AgentCheck.rate),
    },
    'query': """
SELECT relname,
       schemaname,
       indexrelname,
       {metrics_columns}
  FROM pg_stat_user_indexes
 WHERE {relations}""",
    'relation': True,
}

SIZE_METRICS = {
    'descriptors': [('nspname', 'schema'), ('relname', 'table')],
    'metrics': {
        'pg_table_size(C.oid) as table_size': ('postgresql.table_size', AgentCheck.gauge),
        'pg_indexes_size(C.oid) as index_size': ('postgresql.index_size', AgentCheck.gauge),
        'pg_total_relation_size(C.oid) as total_size': ('postgresql.total_size', AgentCheck.gauge),
    },
    'relation': True,
    'query': """
SELECT
  N.nspname,
  relname,
  {metrics_columns}
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
WHERE nspname NOT IN ('pg_catalog', 'information_schema') AND
  nspname !~ '^pg_toast' AND
  relkind = 'r' AND
  {relations}""",
}

STATIO_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
    'metrics': {
        'heap_blks_read': ('postgresql.heap_blocks_read', AgentCheck.rate),
        'heap_blks_hit': ('postgresql.heap_blocks_hit', AgentCheck.rate),
        'idx_blks_read': ('postgresql.index_blocks_read', AgentCheck.rate),
        'idx_blks_hit': ('postgresql.index_blocks_hit', AgentCheck.rate),
        'toast_blks_read': ('postgresql.toast_blocks_read', AgentCheck.rate),
        'toast_blks_hit': ('postgresql.toast_blocks_hit', AgentCheck.rate),
        'tidx_blks_read': ('postgresql.toast_index_blocks_read', AgentCheck.rate),
        'tidx_blks_hit': ('postgresql.toast_index_blocks_hit', AgentCheck.rate),
    },
    'query': """
SELECT relname,
       schemaname,
       {metrics_columns}
  FROM pg_statio_user_tables
 WHERE {relations}""",
    'relation': True,
}


RELATION_METRICS = [LOCK_METRICS, REL_METRICS, IDX_METRICS, SIZE_METRICS, STATIO_METRICS]


class RelationsManager(object):
    def __init__(self, yamlconfig):
        # type: (List[Union[str, Dict]]) -> None
        self.log = get_check_logger()
        self.config = self._build_relations_config(yamlconfig)
        self.has_relations = len(self.config) > 0

    def build_relations_filter(self, schema_field):
        # type (str) -> str
        """Build a WHERE clause filtering relations based on relations_config."""
        relations_filter = []
        for r in self.config.values():
            relation_filter = []
            if r.get(RELATION_NAME):
                relation_filter.append("( relname = '{}'".format(r[RELATION_NAME]))
            elif r.get(RELATION_REGEX):
                relation_filter.append("( relname ~ '{}'".format(r[RELATION_REGEX]))

            if ALL_SCHEMAS not in r[SCHEMAS]:
                schema_filter = ' ,'.join("'{}'".format(s) for s in r[SCHEMAS])
                relation_filter.append('AND {} = ANY(array[{}]::text[])'.format(schema_field, schema_filter))

            relation_filter.append(')')
            relations_filter.append(' '.join(relation_filter))

        return ' OR '.join(relations_filter)

    @staticmethod
    def validate_relations_config(yamlconfig):
        # type: (Dict) -> None
        for element in yamlconfig:
            if isinstance(element, dict):
                if not (RELATION_NAME in element or RELATION_REGEX in element):
                    raise ConfigurationError(
                        "Parameter '%s' or '%s' is required for relation element %s",
                        RELATION_NAME,
                        RELATION_REGEX,
                        element,
                    )
                if RELATION_NAME in element and RELATION_REGEX in element:
                    raise ConfigurationError(
                        "Expecting only of parameters '%s', '%s' for relation element %s",
                        RELATION_NAME,
                        RELATION_REGEX,
                        element,
                    )
                if not isinstance(element.get(SCHEMAS, []), list):
                    raise ConfigurationError("Expected '%s' to be a list for %s", SCHEMAS, element)
            else:
                raise ConfigurationError('Unhandled relations config type: %s', element)

    @staticmethod
    def _build_relations_config(yamlconfig):
        # type:  (List[Union[str, Dict]]) -> Dict[str, Dict[str, Any]]
        """Builds a dictionary from relations configuration while maintaining compatibility"""
        config = {}
        for element in yamlconfig:
            if isinstance(element, str):
                config[element] = {RELATION_NAME: element, SCHEMAS: [ALL_SCHEMAS]}
            elif isinstance(element, dict):
                relname = element.get(RELATION_NAME)
                rel_regex = element.get(RELATION_REGEX)
                schemas = element.get(SCHEMAS, [])
                name = relname or rel_regex
                config[name] = element.copy()
                if len(schemas) == 0:
                    config[name][SCHEMAS] = [ALL_SCHEMAS]
        return config
