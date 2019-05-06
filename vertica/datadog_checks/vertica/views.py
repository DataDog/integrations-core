# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# System tables:
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Monitoring/Vertica/UsingSystemTables.htm
# https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/VerticaSystemTables.htm


class View(object):
    name = ''

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, View):
            return self.name == other.name

        return self.name == other

    # TODO: Remove when only on Python 3+
    def __ne__(self, other):
        return not self == other


class Licenses(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSES.htm
    """

    name = 'licenses'
    fields = ('end_date', 'licensetype', 'node_restriction')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


class LicenseAudits(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSE_AUDITS.htm
    """

    name = 'license_audits'
    fields = ('audit_start_timestamp', 'database_size_bytes', 'license_size_bytes')
    query = (
        "SELECT {} FROM v_catalog.{} WHERE audited_data = 'Total' "
        "ORDER BY audit_start_timestamp DESC LIMIT 1".format(', '.join(fields), name)
    )


class System(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/SYSTEM.htm
    """

    name = 'system'
    fields = ('current_fault_tolerance', 'designed_fault_tolerance', 'node_count', 'node_down_count')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class Nodes(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/NODES.htm
    """

    name = 'nodes'
    fields = ('node_name', 'node_state')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


class Projections(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/PROJECTIONS.htm
    """

    name = 'projections'
    fields = ('is_segmented', 'is_up_to_date')
    query = 'SELECT {} FROM v_catalog.{}'.format(', '.join(fields), name)


class ProjectionStorage(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/PROJECTION_STORAGE.htm
    """

    name = 'projection_storage'
    fields = ('anchor_table_name', 'node_name', 'projection_name', 'ros_row_count', 'used_bytes', 'wos_row_count')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)


class QueryMetrics(View):
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


class DiskStorage(View):
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


class HostResources(View):
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


class ResourceUsage(View):
    """
    https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_USAGE.htm
    """

    name = 'resource_usage'
    fields = ('active_thread_count', 'node_name', 'request_count')
    query = 'SELECT {} FROM v_monitor.{}'.format(', '.join(fields), name)
