# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Using System tables to monitor Vertica:
# https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/AdministratorsGuide/Monitoring/Vertica/UsingSystemTables.htm

from collections import OrderedDict


def get_queries(major_version, metric_groups):
    """Get query dicts for use with QueryManager.

    If `metric_groups` is `None` (default), assume all metric_groups.
    """
    queries = []

    metric_groups = set(metric_groups).intersection(METRIC_GROUPS)

    for metric_group in metric_groups:
        queries.extend(METRIC_GROUPS[metric_group](major_version))

    return queries


def build_licenses_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSES.htm
    """
    name = 'licenses'
    fields = (
        'licensetype',
        # We need to cast the time diff to get an actual number easily
        "CASE WHEN end_date IS NOT NULL AND end_date != 'Perpetual' "
        'THEN ((end_date::TIMESTAMPTZ - now()) second)::INT ELSE -1 END',
    )
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)
    return [
        {
            'name': name,
            'query': query,
            'columns': [{'name': 'license_type', 'type': 'tag'}, {'name': 'license.expiration', 'type': 'gauge'}],
        }
    ]


def build_license_audits_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSE_AUDITS.htm
    """
    name = 'license_audits'
    fields = (
        # We need to cast the time diff to get an actual number easily
        'CASE WHEN audit_start_timestamp IS NULL THEN -1 ELSE ((now() - audit_start_timestamp) second)::INT END',
        'license_size_bytes as size',
        'database_size_bytes as used',
        'size - used as usable',
        'used / size * 100 as utilized',
    )
    query = (
        "SELECT {} FROM v_catalog.{} WHERE audited_data = 'Total' "
        "ORDER BY audit_start_timestamp DESC LIMIT 1".format(', '.join(fields), name)
    )

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'license.latest_audit', 'type': 'gauge'},
                {'name': 'license.size', 'type': 'gauge'},
                {'name': 'license.used', 'type': 'gauge'},
                {'name': 'license.usable', 'type': 'gauge'},
                {'name': 'license.utilized', 'type': 'gauge'},
            ],
        }
    ]


def build_system_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/SYSTEM.htm
    """
    name = 'system'

    license_query = 'SELECT node_restriction FROM v_catalog.licenses LIMIT 1'

    fields = (
        'node_count',
        'node_down_count',
        'current_fault_tolerance',
        'designed_fault_tolerance',
        'ahm_epoch',
        'current_epoch',
        'last_good_epoch',
        'license_query.node_restriction as allowed_nodes',
        'CASE WHEN allowed_nodes IS NULL THEN NULL ELSE allowed_nodes - node_count END',
    )
    query = 'WITH license_query AS ({license_query}) SELECT {} FROM v_monitor.{} CROSS JOIN license_query'.format(
        ', '.join(fields), name, license_query=license_query
    )

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'node.total', 'type': 'gauge'},
                {'name': 'node.down', 'type': 'gauge'},
                {'name': 'ksafety.current', 'type': 'gauge'},
                {'name': 'ksafety.intended', 'type': 'gauge'},
                {'name': 'epoch.ahm', 'type': 'gauge'},
                {'name': 'epoch.current', 'type': 'gauge'},
                {'name': 'epoch.last_good', 'type': 'gauge'},
                {'name': 'node.allowed', 'type': 'gauge'},
                {'name': 'node.available', 'type': 'gauge'},
            ],
        }
    ]


def build_nodes_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/NODES.htm
    """
    name = 'nodes'
    fields = ('node_name', 'node_state')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'node_name', 'type': 'tag'},
                {
                    'name': 'node_state',
                    'type': 'service_check',
                    # https://www.vertica.com/docs/9.2.x/HTML/Content/Resources/Images/Node_States_531x851.png
                    # UP is OK, anything on a possible path to UP is WARNING (except DOWN), otherwise CRITICAL
                    'status_map': {
                        'UP': "OK",
                        'DOWN': "CRITICAL",
                        'READY': "WARNING",
                        'UNSAFE': "CRITICAL",
                        'SHUTDOWN': "CRITICAL",
                        'SHUTDOWN ERROR': "CRITICAL",
                        'RECOVERING': "WARNING",
                        'RECOVERY ERROR': "CRITICAL",
                        'RECOVERED': "WARNING",
                        'INITIALIZING': "WARNING",
                        'STAND BY': "WARNING",
                        'NEEDS CATCH UP': "WARNING",
                    },
                    'message': '{node_state}',
                },
            ],
        }
    ]


def build_projections_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/PROJECTIONS.htm
    """
    name = 'projections'
    query = ' '.join(
        [
            'WITH',
            'total_projections AS (SELECT count(*) FROM v_catalog.{name}),',
            'unsegmented_projections AS (SELECT count(*) FROM v_catalog.{name} WHERE NOT is_segmented),',
            'unsafe_projections AS (SELECT count(*) FROM v_catalog.{name} WHERE NOT is_up_to_date)',
            'SELECT',
            'total_projections.count,',
            'unsegmented_projections.count,',
            'unsafe_projections.count,',
            'CASE WHEN total_projections.count = 0 THEN 0 '
            'ELSE unsegmented_projections.count / total_projections.count * 100 END,',
            'CASE WHEN total_projections.count = 0 THEN 0 '
            'ELSE unsafe_projections.count / total_projections.count * 100 END',
            'FROM total_projections CROSS JOIN unsegmented_projections CROSS JOIN unsafe_projections',
        ]
    ).format(name=name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'projection.total', 'type': 'gauge'},
                {'name': 'projection.unsegmented', 'type': 'gauge'},
                {'name': 'projection.unsafe', 'type': 'gauge'},
                {'name': 'projection.unsegmented_percent', 'type': 'gauge'},
                {'name': 'projection.unsafe_percent', 'type': 'gauge'},
            ],
        }
    ]


def build_projection_storage_queries(version):
    """Builds a list of queries for projection_storage metrics depending on the vertica version."""
    # https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/PROJECTION_STORAGE.htm
    common_value_fields = (
        'ros_count',
        'row_count',
        'used_bytes',
    )

    # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/PROJECTION_STORAGE.htm
    legacy_value_fields = (
        'ros_row_count',
        'wos_row_count',
        'ros_used_bytes',
        'wos_used_bytes',
    )

    column_to_metric_mapping = {
        'anchor_table_name': 'table_name',
        'node_name': 'node_name',
        'projection_name': 'projection_name',
        'ros_count': 'ros.containers',
        'row_count': 'row.total',
        'ros_row_count': 'row.ros',
        'wos_row_count': 'row.wos',
        'used_bytes': 'disk.used',
        'ros_used_bytes': 'disk.used.ros',
        'wos_used_bytes': 'disk.used.wos',
    }

    value_fields = common_value_fields + legacy_value_fields if version < 11 else common_value_fields

    sum_fields = ['sum({0}) as {0}'.format(field) for field in value_fields]

    def build_query(grouping, group_fields):
        if not group_fields:
            query_name = 'projection_storage_total'
            query = 'SELECT {} FROM v_monitor.projection_storage'.format(', '.join(sum_fields))
            prefix = ''

        else:
            query_name = 'projection_storage_per_{}'.format(grouping)
            columns = ', '.join(group_fields + sum_fields)
            query = 'SELECT {columns} FROM v_monitor.projection_storage GROUP BY {group_fields}'.format(
                columns=columns, group_fields=', '.join(group_fields)
            )
            prefix = grouping + '.'

        group_columns = [{'name': column_to_metric_mapping[field], 'type': 'tag'} for field in group_fields]

        value_columns = [{'name': prefix + column_to_metric_mapping[field], 'type': 'gauge'} for field in value_fields]

        return {'name': query_name, 'query': query, 'columns': group_columns + value_columns}

    return [
        build_query('projection', ['anchor_table_name', 'node_name', 'projection_name']),
        build_query('table', ['anchor_table_name', 'node_name']),
        build_query('node', ['node_name']),
        build_query('total', []),
    ]


def build_storage_containers_queries(version):
    """Builds a list of queries for storage_containers metrics depending on the vertica version."""
    # https://www.vertica.com/docs/10.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/STORAGE_CONTAINERS.htm
    # https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/STORAGE_CONTAINERS.htm

    queries = []

    column_to_metric_mapping = {
        'node_name': 'node_name',
        'projection_name': 'projection_name',
        'storage_type': 'container_type',
    }

    sum_fields = ['sum(delete_vector_count) as delete_vector_count']

    def build_query(grouping, group_fields):
        if not group_fields:
            query_name = 'storage_containers_total'
            query = 'SELECT {} FROM v_monitor.storage_containers'.format(', '.join(sum_fields))
            prefix = ''

        else:
            query_name = 'storage_containers_per_{}'.format(grouping)
            columns = ', '.join(group_fields + sum_fields)
            query = 'SELECT {columns} FROM v_monitor.storage_containers GROUP BY {group_fields}'.format(
                columns=columns, group_fields=', '.join(group_fields)
            )
            prefix = grouping + '.'

        group_columns = [{'name': column_to_metric_mapping[field], 'type': 'tag'} for field in group_fields]

        value_columns = [{'name': prefix + 'delete_vectors', 'type': 'gauge'}]

        return {'name': query_name, 'query': query, 'columns': group_columns + value_columns}

    if version < 11:
        queries.append(build_query('projection', ['node_name', 'projection_name', 'storage_type']))
    else:
        # Version 11 dropped the storage_type column
        queries.append(build_query('projection', ['node_name', 'projection_name']))

    queries.extend([build_query('node', ['node_name']), build_query('total', [])])

    return queries


def build_host_resources_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/HOST_RESOURCES.htm
    """
    name = 'host_resources'
    fields = (
        'host_name',
        'processor_count',
        'processor_core_count',
        'open_files_limit',
        'opened_file_count',
        'opened_socket_count',
        'threads_limit',
        'total_memory_bytes as total',
        'total_memory_free_bytes as usable',
        'total - usable as used',
        'CASE WHEN total = 0 THEN 0 ELSE used / total * 100 END as utilized',
        'total_swap_memory_bytes as total_swap',
        'total_swap_memory_free_bytes as usable_swap',
        'total_swap - usable_swap as used_swap',
        'CASE WHEN total_swap = 0 THEN 0 ELSE used_swap / total_swap * 100 END as utilized_swap',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'host_name', 'type': 'tag'},
                {'name': 'processor.cpu', 'type': 'gauge'},
                {'name': 'processor.core', 'type': 'gauge'},
                {'name': 'file.max', 'type': 'gauge'},
                {'name': 'file.open', 'type': 'gauge'},
                {'name': 'socket.open', 'type': 'gauge'},
                {'name': 'thread.max', 'type': 'gauge'},
                {'name': 'memory.total', 'type': 'gauge'},
                {'name': 'memory.usable', 'type': 'gauge'},
                {'name': 'memory.used', 'type': 'gauge'},
                {'name': 'memory.utilized', 'type': 'gauge'},
                {'name': 'memory.swap.total', 'type': 'gauge'},
                {'name': 'memory.swap.usable', 'type': 'gauge'},
                {'name': 'memory.swap.used', 'type': 'gauge'},
                {'name': 'memory.swap.utilized', 'type': 'gauge'},
            ],
        }
    ]


def build_query_metrics_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/QUERY_METRICS.htm
    """
    name = 'query_metrics'
    fields = (
        'node_name',
        'active_user_session_count',
        'total_user_session_count',
        'running_query_count',
        'executed_query_count',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'node_name', 'type': 'tag'},
                {'name': 'connection.active', 'type': 'gauge'},
                {'name': 'connection.total', 'type': 'monotonic_count'},
                {'name': 'query.active', 'type': 'gauge'},
                {'name': 'query.total', 'type': 'monotonic_count'},
            ],
        }
    ]


def build_resource_pool_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_POOL_STATUS.htm
    """
    name = 'resource_pool_status'
    fields = (
        'node_name',
        'pool_name',
        'general_memory_borrowed_kb * 1000',
        'max_memory_size_kb * 1000',
        'memory_inuse_kb * 1000',
        'running_query_count',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'node_name', 'type': 'tag'},
                {'name': 'pool_name', 'type': 'tag'},
                {'name': 'resource_pool.memory.borrowed', 'type': 'gauge'},
                {'name': 'resource_pool.memory.max', 'type': 'gauge'},
                {'name': 'resource_pool.memory.used', 'type': 'gauge'},
                {'name': 'resource_pool.query.running', 'type': 'gauge'},
            ],
        }
    ]


def build_disk_storage_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/DISK_STORAGE.htm
    """
    name = 'disk_storage'
    fields = (
        'node_name',
        'storage_status',
        'storage_usage',
        'disk_block_size_bytes * disk_space_free_blocks as usable',
        'disk_block_size_bytes * disk_space_used_blocks as used',
        'usable + used as total',
        'CASE WHEN total = 0 THEN 0 ELSE used / total * 100 END as utilized',
        'latency',
        'throughput',
        'CASE WHEN latency = 0 THEN 0 ELSE 1 / latency END as latency_reciprocal',
        'CASE WHEN throughput = 0 THEN 0 ELSE 1 / throughput END as throughput_reciprocal',
        'latency_reciprocal + throughput_reciprocal',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'node_name', 'type': 'tag'},
                {'name': 'storage_status', 'type': 'tag'},
                {'name': 'storage_usage', 'type': 'tag'},
                {'name': 'storage.usable', 'type': 'gauge'},
                {'name': 'storage.used', 'type': 'gauge'},
                {'name': 'storage.size', 'type': 'gauge'},
                {'name': 'storage.utilized', 'type': 'gauge'},
                {'name': 'storage.latency', 'type': 'gauge'},
                {'name': 'storage.throughput', 'type': 'gauge'},
                {'name': 'latency_reciprocal', 'type': 'source'},
                {'name': 'throughput_reciprocal', 'type': 'source'},
                {'name': 'storage.speed', 'type': 'gauge'},
            ],
        }
    ]


def build_resource_usage_queries(_version=None):
    """
    https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_USAGE.htm
    """

    name = 'resource_usage'
    fields = ('active_thread_count', 'node_name', 'request_count')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)

    return [
        {
            'name': name,
            'query': query,
            'columns': [
                {'name': 'thread.active', 'type': 'gauge'},
                {'name': 'node_name', 'type': 'tag'},
                {'name': 'node.resource_requests', 'type': 'gauge'},
            ],
        }
    ]


# If you create a new group, please add it to `METRIC_GROUPS` below and
# the config file (under `metric_groups`).
METRIC_GROUPS = OrderedDict(
    [
        ('licenses', build_licenses_queries),
        ('license_audits', build_license_audits_queries),
        ('system', build_system_queries),
        ('nodes', build_nodes_queries),
        ('projections', build_projections_queries),
        ('projection_storage', build_projection_storage_queries),
        ('storage_containers', build_storage_containers_queries),
        ('host_resources', build_host_resources_queries),
        ('query_metrics', build_query_metrics_queries),
        ('resource_pool_status', build_resource_pool_queries),
        ('disk_storage', build_disk_storage_queries),
        ('resource_usage', build_resource_usage_queries),
    ]
)
