# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""
https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20cbb10c75191014b47ba845bfe499fe.html

> The views in the SYS_DATABASES schema provide aggregated information from a subset of the views available in the
  SYS schema of all tenant databases in the system. These union views have the additional column DATABASE_NAME to
  allow you to identify to which database the information refers.

To find out exactly what is available in each subset, run:

ALL_SCHEMA = 'SYS_DATABASES'
_ = cur.execute("SELECT VIEW_NAME FROM VIEWS WHERE SCHEMA_NAME = '{ALL_SCHEMA}'")
views = [row[0] for row in sorted(cur.fetchall())]
for view in views:
    print(view)
    _ = cur.execute(f"SELECT COLUMN_NAME FROM VIEW_COLUMNS WHERE SCHEMA_NAME = '{ALL_SCHEMA}' and VIEW_NAME = '{view}'")
    for row in cur.fetchall():
        print(f'    {row[0]}')
"""
import inspect
from collections import defaultdict

from .utils import compact_query

VIEWS_USED = defaultdict(set)


def view(v, user=None):
    VIEWS_USED[user or inspect.getframeinfo(inspect.currentframe().f_back).function].add(v)
    return v


class MasterDatabase:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20ae63aa7519101496f6b832ec86afbd.html
    """

    fields = ('db_name', 'host', 'start_time', 'usage', 'version', 'current_time')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          START_TIME,
          USAGE,
          VERSION,
          CURRENT_UTCTIMESTAMP
        FROM {}
        """.format(
            view('SYS.M_DATABASE')
        )
    )


class SystemDatabases:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/dbbdc0d96675470e80801c5ddfb8d348.html
    """

    fields = ('db_name', 'status', 'details')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          ACTIVE_STATUS,
          ACTIVE_STATUS_DETAILS
        FROM {}
        """.format(
            view('SYS.M_DATABASES')
        )
    )


class GlobalSystemBackupProgress:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/783108ba8b8b4c709959220b4535a010.html
    """

    fields = ('db_name', 'host', 'service', 'status', 'end_time', 'current_time')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          SERVICE_NAME,
          STATE_NAME,
          UTC_END_TIME,
          CURRENT_UTCTIMESTAMP
        FROM {}
        """.format(
            view('SYS_DATABASES.M_BACKUP_PROGRESS')
        )
    )


class GlobalSystemLicenses:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/1d7e7f52f6574a238c137e17b0840673.html
    """

    fields = ('sid', 'product_name', 'limit', 'usage', 'start_date', 'expiration_date')
    query = compact_query(
        """
        SELECT
          SYSTEM_ID,
          PRODUCT_NAME,
          PRODUCT_LIMIT,
          PRODUCT_USAGE,
          START_DATE,
          EXPIRATION_DATE
        FROM {}
        """.format(
            view('SYS_DATABASES.M_LICENSES')
        )
    )


class GlobalSystemConnectionsStatus:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20abcf1f75191014a254a82b3d0f66bf.html
    """

    fields = ('db_name', 'host', 'port', 'status', 'total')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          CONNECTION_STATUS,
          COUNT(*)
        FROM {}
        WHERE CONNECTION_STATUS != ''
        GROUP BY DATABASE_NAME, HOST, PORT, CONNECTION_STATUS
        """.format(
            view('SYS_DATABASES.M_CONNECTIONS')
        )
    )


class GlobalSystemDiskUsage:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/a2aac2ee72b341699fa8eb3988d8cecb.html
    """

    fields = ('db_name', 'host', 'resource', 'used', 'total')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          USAGE_TYPE,
          USED_SIZE,
          TOTAL_SIZE
        FROM {}
        """.format(
            view('SYS_DATABASES.M_DISK_USAGE')
        )
    )


class GlobalSystemServiceMemory:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bf33c975191014bc16d7ffb7717db2.html
    """

    fields = (
        'db_name',
        'host',
        'port',
        'service',
        'virtual',
        'physical',
        'total',
        'used',
        'heap_total',
        'heap_used',
        'shared_total',
        'shared_used',
        'compactors_total',
        'compactors_usable',
    )
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          SERVICE_NAME,
          LOGICAL_MEMORY_SIZE,
          PHYSICAL_MEMORY_SIZE,
          EFFECTIVE_ALLOCATION_LIMIT,
          TOTAL_MEMORY_USED_SIZE,
          HEAP_MEMORY_ALLOCATED_SIZE,
          HEAP_MEMORY_USED_SIZE,
          SHARED_MEMORY_ALLOCATED_SIZE,
          SHARED_MEMORY_USED_SIZE,
          COMPACTORS_ALLOCATED_SIZE,
          COMPACTORS_FREEABLE_SIZE
        FROM {}
        """.format(
            view('SYS_DATABASES.M_SERVICE_MEMORY')
        )
    )


class GlobalSystemServiceComponentMemory:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bed4f675191014a4cf8e62c28d16ae.html
    """

    fields = ('db_name', 'host', 'port', 'component', 'used')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          COMPONENT,
          USED_MEMORY_SIZE
        FROM {}
        """.format(
            view('SYS_DATABASES.M_SERVICE_COMPONENT_MEMORY')
        )
    )


class GlobalSystemRowStoreMemory:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bb47a975191014b1e2f6bd0a685d7b.html
    """

    fields = ('db_name', 'host', 'port', 'category', 'total', 'used', 'usable')
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          CATEGORY,
          ALLOCATED_SIZE,
          USED_SIZE,
          FREE_SIZE
        FROM {}
        """.format(
            view('SYS_DATABASES.M_RS_MEMORY')
        )
    )


class GlobalSystemServiceStatistics:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20c460be751910149173ac5c08d42be5.html
    """

    fields = (
        'db_name',
        'host',
        'port',
        'service',
        'requests_per_second',
        'response_time',
        'requests_active',
        'requests_pending',
        'requests_finished_external',
        'requests_finished_total',
        'threads_total',
        'threads_active',
        'files_open',
        'cpu_time',
    )
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          SERVICE_NAME,
          REQUESTS_PER_SEC,
          RESPONSE_TIME,
          ACTIVE_REQUEST_COUNT,
          PENDING_REQUEST_COUNT,
          FINISHED_NON_INTERNAL_REQUEST_COUNT,
          ALL_FINISHED_REQUEST_COUNT,
          THREAD_COUNT,
          ACTIVE_THREAD_COUNT,
          OPEN_FILE_COUNT,
          PROCESS_CPU_TIME
        FROM {}
        """.format(
            view('SYS_DATABASES.M_SERVICE_STATISTICS')
        )
    )


class GlobalSystemVolumeIO:
    """
    https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20cadec8751910148bab98528e3634a9.html
    """

    fields = (
        'db_name',
        'host',
        'port',
        'resource',
        'path',
        'reads',
        'read_size',
        'read_time',
        'writes',
        'write_size',
        'write_time',
        'io_time',
    )
    query = compact_query(
        """
        SELECT
          DATABASE_NAME,
          HOST,
          PORT,
          TYPE,
          PATH,
          TOTAL_READS,
          TOTAL_READ_SIZE,
          TOTAL_READ_TIME,
          TOTAL_WRITES,
          TOTAL_WRITE_SIZE,
          TOTAL_WRITE_TIME,
          TOTAL_IO_TIME
        FROM {}
        """.format(
            view('SYS_DATABASES.M_VOLUME_IO_TOTAL_STATISTICS')
        )
    )


ALL_VIEWS_USED = tuple(sorted(set(v for vu in VIEWS_USED.values() for v in vu)))
VIEWS_USED = {k: tuple(sorted(v)) for k, v in sorted(VIEWS_USED.items())}
