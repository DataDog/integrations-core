# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# System tables:
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Monitoring/Vertica/UsingSystemTables.htm
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/VerticaSystemTables.htm


class Licenses:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSES.htm
    """

    name = 'licenses'
    fields = ('end_date', 'licensetype', 'node_restriction')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


class LicenseAudits:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSE_AUDITS.htm
    """

    name = 'license_audits'
    fields = ('audit_start_timestamp', 'database_size_bytes', 'license_size_bytes')
    query = (
        "SELECT {} FROM v_catalog.{} WHERE audited_data = 'Total' "
        "ORDER BY audit_start_timestamp DESC LIMIT 1".format(', '.join(fields), name)
    )


class System:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/SYSTEM.htm
    """

    name = 'system'
    fields = (
        'ahm_epoch',
        'current_epoch',
        'current_fault_tolerance',
        'designed_fault_tolerance',
        'last_good_epoch',
        'node_count',
        'node_down_count',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class Nodes:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/NODES.htm
    """

    name = 'nodes'
    fields = ('node_name', 'node_state')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


class Projections:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/PROJECTIONS.htm
    """

    name = 'projections'
    fields = ('is_segmented', 'is_up_to_date')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


def make_projection_storage_queries(version):
    """Builds a dict of queries for projection_storage metrics depending on the vertica version."""
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

    value_fields = common_value_fields + legacy_value_fields if version < 11 else common_value_fields

    sum_fields = ['sum({0}) as {0}'.format(field) for field in value_fields]

    def build_query(group_fields):
        columns = ', '.join(group_fields + sum_fields)
        return ('SELECT {columns} FROM v_monitor.projection_storage GROUP BY {group_fields}').format(
            columns=columns, group_fields=', '.join(group_fields)
        )

    return {
        'per_projection': build_query(['anchor_table_name', 'node_name', 'projection_name']),
        'per_table': build_query(['anchor_table_name', 'node_name']),
        'per_node': build_query(['node_name']),
        'total': 'SELECT {} FROM v_monitor.projection_storage'.format(', '.join(sum_fields)),
    }


class StorageContainers:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/STORAGE_CONTAINERS.htm
    """

    name = 'storage_containers'
    fields = ('delete_vector_count', 'node_name', 'projection_name', 'storage_type')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class QueryMetrics:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/QUERY_METRICS.htm
    """

    name = 'query_metrics'
    fields = (
        'active_user_session_count',
        'executed_query_count',
        'node_name',
        'running_query_count',
        'total_user_session_count',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class DiskStorage:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/DISK_STORAGE.htm
    """

    name = 'disk_storage'
    fields = (
        'disk_block_size_bytes',
        'disk_space_free_blocks',
        'disk_space_used_blocks',
        'latency',
        'node_name',
        'storage_status',
        'storage_usage',
        'throughput',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class HostResources:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/HOST_RESOURCES.htm
    """

    name = 'host_resources'
    fields = (
        'host_name',
        'open_files_limit',
        'opened_file_count',
        'opened_socket_count',
        'processor_core_count',
        'processor_count',
        'threads_limit',
        'total_memory_bytes',
        'total_memory_free_bytes',
        'total_swap_memory_bytes',
        'total_swap_memory_free_bytes',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class ResourceUsage:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_USAGE.htm
    """

    name = 'resource_usage'
    fields = ('active_thread_count', 'node_name', 'request_count')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class ResourcePoolStatus:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_POOL_STATUS.htm
    """

    name = 'resource_pool_status'
    fields = (
        'general_memory_borrowed_kb',
        'max_memory_size_kb',
        'memory_inuse_kb',
        'node_name',
        'pool_name',
        'running_query_count',
    )
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class Version:
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Diagnostics/DeterminingYourVersionOfVertica.htm
    """

    name = 'version'
    query = 'SELECT version()'
