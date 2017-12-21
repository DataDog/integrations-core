# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
'''
Check the performance counters from SQL Server

See http://blogs.msdn.com/b/psssql/archive/2013/09/23/interpreting-the-counter-values-from-sys-dm-os-performance-counters.aspx
for information on how to report the metrics available in the sys.dm_os_performance_counters table
'''
# stdlib
import traceback
from contextlib import contextmanager
from collections import defaultdict
# 3rd party
import adodbapi
try:
    import pyodbc
except ImportError:
    pyodbc = None

from config import _is_affirmative

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'sql server'
ALL_INSTANCES = 'ALL'
VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Queries
COUNTER_TYPE_QUERY = '''select distinct cntr_type
                        from sys.dm_os_performance_counters
                        where counter_name = ?;'''

BASE_NAME_QUERY = '''select distinct counter_name
                     from sys.dm_os_performance_counters
                     where (counter_name=? or counter_name=?
                     or counter_name=?) and cntr_type=%s;''' % PERF_LARGE_RAW_BASE

INSTANCES_QUERY = '''select instance_name
                     from sys.dm_os_performance_counters
                     where counter_name=? and instance_name!='_Total';'''

VALUE_AND_BASE_QUERY = '''select counter_name, cntr_type, cntr_value, instance_name
                          from sys.dm_os_performance_counters
                          where counter_name in (%s)
                          order by cntr_type;'''

DATABASE_EXISTS_QUERY = 'select name from sys.databases;'

# Performance tables
DEFAULT_PERFORMANCE_TABLE = "sys.dm_os_performance_counters"
DM_OS_WAIT_STATS_TABLE = "sys.dm_os_wait_stats"
DM_OS_MEMORY_CLERKS_TABLE = "sys.dm_os_memory_clerks"
DM_OS_VIRTUAL_FILE_STATS = "sys.dm_io_virtual_file_stats"

class SQLConnectionError(Exception):
    """
    Exception raised for SQL instance connection issues
    """
    pass


class SQLServer(AgentCheck):

    SERVICE_CHECK_NAME = 'sqlserver.can_connect'
    # FIXME: 6.x, set default to 5s (like every check)
    DEFAULT_COMMAND_TIMEOUT = 30
    DEFAULT_DATABASE = 'master'
    DEFAULT_DRIVER = 'SQL Server'
    DEFAULT_DB_KEY = 'database'
    PROC_GUARD_DB_KEY = 'proc_only_if_database'

    METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', ''),  # RAW_LARGE_FRACTION
        ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.batch_requests', 'Batch Requests/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.connections', 'User Connections', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total'),  # BULK_COUNT
        ('sqlserver.access.page_splits', 'Page Splits/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.procs_blocked', 'Processes blocked', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', '')  # BULK_COUNT
    ]
    valid_connectors = ['adodbapi']
    if pyodbc is not None:
        valid_connectors.append('odbc')
    valid_tables = [
        DEFAULT_PERFORMANCE_TABLE,
        DM_OS_WAIT_STATS_TABLE,
        DM_OS_MEMORY_CLERKS_TABLE,
        DM_OS_VIRTUAL_FILE_STATS
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Cache connections
        self.connections = {}
        self.failed_connections = {}
        self.instances_metrics = {}
        self.instances_per_type_metrics = defaultdict(dict)
        self.existing_databases = None
        self.do_check = {}
        self.proc_type_mapping = {
            'gauge': self.gauge,
            'rate' : self.rate,
            'histogram': self.histogram
        }

        self.connector = init_config.get('connector', 'adodbapi')
        if not self.connector.lower() in self.valid_connectors:
            self.log.error("Invalid database connector %s, defaulting to adodbapi" % self.connector)
            self.connector = 'adodbapi'

        self.log.debug("instances: %s", str(instances))
        # Pre-process the list of metrics to collect
        self.custom_metrics = init_config.get('custom_metrics', [])
        for instance in instances:
            self.log.debug("initializing %s", str(instance))
            try:
                instance_key = self._conn_key(instance, self.DEFAULT_DB_KEY)
                self.do_check[instance_key] = True

                # check to see if the database exists before we try any connections to it
                with self.open_managed_db_connections(instance, None, db_name=self.DEFAULT_DATABASE):
                    db_exists, context = self._check_db_exists(instance)

                if db_exists:
                    if instance.get('stored_procedure') is None:
                        with self.open_managed_db_connections(instance, self.DEFAULT_DB_KEY):
                            self._make_metric_list_to_collect(instance, self.custom_metrics)
                else:
                    # How much do we care that the DB doesn't exist?
                    ignore = _is_affirmative(instance.get("ignore_missing_database", False))
                    if ignore is not None and ignore:
                        # not much : we expect it. leave checks disabled
                        self.do_check[instance_key] = False
                        self.log.warning("Database %s does not exist. Disabling checks for this instance." % (context))
                    else:
                        # yes we do. Keep trying
                        self.log.error("Database %s does not exist. Fix issue and restart agent" % (context))

            except SQLConnectionError:
                self.log.exception("Skipping SQL Server instance")
                continue
            except Exception as e:
                self.log.exception("INitialization exception %s", str(e))
                continue

    def _check_db_exists(self, instance):
        """
        Check if the database we're targeting actually exists
        If not then we won't do any checks
        This allows the same config to be installed on many servers but fail gracefully
        """

        dsn, host, username, password, database, driver = self._get_access_info(instance, self.DEFAULT_DB_KEY)
        context = "%s - %s" % (host, database)
        if self.existing_databases is None:
            cursor = self.get_cursor(instance, None, self.DEFAULT_DATABASE)

            try:
                self.existing_databases = {}
                cursor.execute(DATABASE_EXISTS_QUERY)
                for row in cursor:
                    self.existing_databases[row.name] = True

            except Exception, e:
                self.log.error("Failed to check if database %s exists: %s" % (database, e))
                return False, context
            finally:
                self.close_cursor(cursor)

        return database in self.existing_databases, context

    def _make_metric_list_to_collect(self, instance, custom_metrics):
        """
        Store the list of metrics to collect by instance_key.
        Will also create and cache cursors to query the db.
        """
        metrics_to_collect = []
        for name, counter_name, instance_name in self.METRICS:
            try:
                sql_type, base_name = self.get_sql_type(instance, counter_name)
                cfg = {}
                cfg['name'] = name
                cfg['counter_name'] = counter_name
                cfg['instance_name'] = instance_name

                metrics_to_collect.append(self.typed_metric(instance,
                                                            cfg,
                                                            DEFAULT_PERFORMANCE_TABLE,
                                                            base_name,
                                                            None,
                                                            sql_type,
                                                            None))
            except SQLConnectionError:
                raise
            except Exception:
                self.log.warning("Can't load the metric %s, ignoring", name, exc_info=True)
                continue

        # Load any custom metrics from conf.d/sqlserver.yaml
        for row in custom_metrics:
            db_table = row.get('table', DEFAULT_PERFORMANCE_TABLE)
            if db_table not in self.valid_tables:
                self.log.error('%s has an invalid table name: %s', row['name'], db_table)
                continue

            if db_table == DEFAULT_PERFORMANCE_TABLE:
                user_type = row.get('type')
                if user_type is not None and user_type not in VALID_METRIC_TYPES:
                    self.log.error('%s has an invalid metric type: %s', row['name'], user_type)
                sql_type = None
                try:
                    if user_type is None:
                        sql_type, base_name = self.get_sql_type(instance, row['counter_name'])
                except Exception:
                    self.log.warning("Can't load the metric %s, ignoring", row['name'], exc_info=True)
                    continue

                metrics_to_collect.append(self.typed_metric(instance,
                                                            row,
                                                            db_table,
                                                            base_name,
                                                            user_type,
                                                            sql_type,
                                                            None))

            else:
                for column in row['columns']:
                    metrics_to_collect.append(self.typed_metric(instance,
                                                            row,
                                                            db_table,
                                                            base_name,
                                                            None,
                                                            sql_type,
                                                            column))

        instance_key = self._conn_key(instance, self.DEFAULT_DB_KEY)
        self.instances_metrics[instance_key] = metrics_to_collect
        simple_metrics = []
        fraction_metrics = []
        wait_stat_metrics = []
        vfs_metrics = []
        clerk_metrics = []
        self.log.debug("metrics to collect %s", str(metrics_to_collect))
        for m in metrics_to_collect:
            if type(m) is SqlSimpleMetric:
                self.log.debug("Adding simple metric %s", m.sql_name)
                simple_metrics.append(m.sql_name)
            elif type(m) is SqlFractionMetric or type(m) is SqlIncrFractionMetric:
                self.log.debug("Adding fraction metric %s", m.sql_name)
                fraction_metrics.append(m.sql_name)
                fraction_metrics.append(m.base_name)
            elif type(m) is SqlOsWaitStat:
                self.log.debug("Adding SqlOsWaitStat metric %s", m.sql_name)
                wait_stat_metrics.append(m.sql_name)
            elif type(m) is SqlOsVirtualFileStat:
                self.log.debug("Adding SqlOsVirtualFileStat metric %s", m.sql_name)
                vfs_metrics.append(m.sql_name)
            elif type(m) is SqlOsMemoryClerksStat:
                self.log.debug("Adding SqlOsMemoryClerksStat metric %s", m.sql_name)
                clerk_metrics.append(m.sql_name)

        self.instances_per_type_metrics[instance_key]["SqlSimpleMetric"] = simple_metrics
        self.instances_per_type_metrics[instance_key]["SqlFractionMetric"] = fraction_metrics
        self.instances_per_type_metrics[instance_key]["SqlOsWaitStat"] = wait_stat_metrics
        self.instances_per_type_metrics[instance_key]["SqlOsVirtualFileStat"] = vfs_metrics
        self.instances_per_type_metrics[instance_key]["SqlOsMemoryClerksStat"] = clerk_metrics

    def typed_metric(self, instance, cfg_inst, table, base_name, user_type, sql_type, column):
        '''
        Create the appropriate SqlServerMetric object, each implementing its method to
        fetch the metrics properly.
        If a `type` was specified in the config, it is used to report the value
        directly fetched from SQLServer. Otherwise, it is decided based on the
        sql_type, according to microsoft's documentation.
        '''
        if table == DEFAULT_PERFORMANCE_TABLE:
            metric_type_mapping = {
                PERF_COUNTER_BULK_COUNT: (self.rate, SqlSimpleMetric),
                PERF_COUNTER_LARGE_RAWCOUNT: (self.gauge, SqlSimpleMetric),
                PERF_LARGE_RAW_BASE: (self.gauge, SqlSimpleMetric),
                PERF_RAW_LARGE_FRACTION: (self.gauge, SqlFractionMetric),
                PERF_AVERAGE_BULK: (self.gauge, SqlIncrFractionMetric)
            }
            if user_type is not None:
                # user type overrides any other value
                metric_type = getattr(self, user_type)
                cls = SqlSimpleMetric

            else:
                metric_type, cls = metric_type_mapping[sql_type]
        else:
            table_type_mapping = {
                DM_OS_WAIT_STATS_TABLE: (self.gauge, SqlOsWaitStat),
                DM_OS_MEMORY_CLERKS_TABLE: (self.gauge, SqlOsMemoryClerksStat),
                DM_OS_VIRTUAL_FILE_STATS: (self.gauge, SqlOsVirtualFileStat)
            }
            metric_type, cls = table_type_mapping[table]

        return cls(self._get_connector(instance), cfg_inst, base_name, metric_type, column, self.log)


    def _get_connector(self, instance):
        connector = instance.get('connector', self.connector)
        if connector != self.connector:
            if not connector.lower() in self.valid_connectors:
                self.log.warning("Invalid database connector %s using default %s" ,
                     connector, self.connector)
                connector = self.connector
            else:
                self.log.debug("Overriding default connector for %s with %s", instance['host'], connector)
        return connector

    def _get_access_info(self, instance, db_key, db_name=None):
        ''' Convenience method to extract info from instance
        '''
        dsn = instance.get('dsn')
        host = instance.get('host')
        username = instance.get('username')
        password = instance.get('password')
        database = instance.get(db_key) if db_name is None else db_name
        driver = instance.get('driver')
        if not dsn:
            if not host:
                host = '127.0.0.1,1433'
            if not database:
                database = self.DEFAULT_DATABASE
            if not driver:
                driver = self.DEFAULT_DRIVER
        return dsn, host, username, password, database, driver

    def _conn_key(self, instance, db_key, db_name=None):
        ''' Return a key to use for the connection cache
        '''
        dsn, host, username, password, database, driver = self._get_access_info(instance, db_key, db_name)
        return '%s:%s:%s:%s:%s:%s' % (dsn, host, username, password, database, driver)

    def _conn_string_odbc(self, db_key, instance=None, conn_key=None, db_name=None):
        ''' Return a connection string to use with odbc
        '''
        if instance:
            dsn, host, username, password, database, driver = self._get_access_info(instance, db_key, db_name)
        elif conn_key:
            dsn, host, username, password, database, driver = conn_key.split(":")

        conn_str = ''
        if dsn:
            conn_str = 'DSN=%s;' % (dsn)

        if driver:
            conn_str += 'DRIVER={%s};' % (driver)
        if host:
            conn_str += 'Server=%s;' % (host)
        if database:
            conn_str += 'Database=%s;' % (database)

        if username:
            conn_str += 'UID=%s;' % (username)
        self.log.debug("Connection string (before password) %s" , conn_str)
        if password:
            conn_str += 'PWD=%s;' % (password)

        return conn_str

    def _conn_string_adodbapi(self, db_key, instance=None, conn_key=None, db_name=None):
        ''' Return a connection string to use with adodbapi
        '''
        if instance:
            _, host, username, password, database, _ = self._get_access_info(instance, db_key, db_name)
        elif conn_key:
            _, host, username, password, database, _ = conn_key.split(":")
        conn_str = 'Provider=SQLOLEDB;Data Source=%s;Initial Catalog=%s;' \
            % (host, database)
        if username:
            conn_str += 'User ID=%s;' % (username)
        if password:
            conn_str += 'Password=%s;' % (password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str


    @contextmanager
    def get_managed_cursor(self, instance, db_key, db_name=None):
        cursor = self.get_cursor(instance, db_key, db_name)
        yield cursor

        self.close_cursor(cursor)

    def get_cursor(self, instance, db_key, db_name=None):
        '''
        Return a cursor to execute query against the db
        Cursor are cached in the self.connections dict
        '''
        conn_key = self._conn_key(instance, db_key, db_name)

        conn = self.connections[conn_key]['conn']
        cursor = conn.cursor()
        return cursor

    def get_sql_type(self, instance, counter_name):
        '''
        Return the type of the performance counter so that we can report it to
        Datadog correctly
        If the sql_type is one that needs a base (PERF_RAW_LARGE_FRACTION and
        PERF_AVERAGE_BULK), the name of the base counter will also be returned
        '''
        with self.get_managed_cursor(instance, self.DEFAULT_DB_KEY) as cursor:
            cursor.execute(COUNTER_TYPE_QUERY, (counter_name,))
            (sql_type,) = cursor.fetchone()
            if sql_type == PERF_LARGE_RAW_BASE:
                self.log.warning("Metric %s is of type Base and shouldn't be reported this way",
                                counter_name)
            base_name = None
            if sql_type in [PERF_AVERAGE_BULK, PERF_RAW_LARGE_FRACTION]:
                # This is an ugly hack. For certains type of metric (PERF_RAW_LARGE_FRACTION
                # and PERF_AVERAGE_BULK), we need two metrics: the metrics specified and
                # a base metrics to get the ratio. There is no unique schema so we generate
                # the possible candidates and we look at which ones exist in the db.
                candidates = (counter_name + " base",
                              counter_name.replace("(ms)", "base"),
                              counter_name.replace("Avg ", "") + " base"
                              )
                try:
                    cursor.execute(BASE_NAME_QUERY, candidates)
                    base_name = cursor.fetchone().counter_name.strip()
                    self.log.debug("Got base metric: %s for metric: %s", base_name, counter_name)
                except Exception as e:
                    self.log.warning("Could not get counter_name of base for metric: %s", e)

        return sql_type, base_name

    def check(self, instance):
        if self.do_check[self._conn_key(instance, self.DEFAULT_DB_KEY)]:
            proc = instance.get('stored_procedure')
            if proc is None:
                self.do_perf_counter_check(instance)
            else:
                self.do_stored_procedure_check(instance, proc)
        else:
            self.log.debug("Skipping check")

    def do_perf_counter_check(self, instance):
        """
        Fetch the metrics from the sys.dm_os_performance_counters table
        """
        custom_tags = instance.get('tags', [])
        instance_key = self._conn_key(instance, self.DEFAULT_DB_KEY)

        with self.open_managed_db_connections(instance, self.DEFAULT_DB_KEY):
            # if the server was down at check __init__ key could be missing.
            if instance_key not in self.instances_metrics:
                self._make_metric_list_to_collect(instance, self.custom_metrics)
            metrics_to_collect = self.instances_metrics[instance_key]

            with self.get_managed_cursor(instance, self.DEFAULT_DB_KEY) as cursor:

                simple_rows = SqlSimpleMetric.fetch_all_values(cursor, self.instances_per_type_metrics[instance_key]["SqlSimpleMetric"], self.log)
                fraction_results = SqlFractionMetric.fetch_all_values(cursor, self.instances_per_type_metrics[instance_key]["SqlFractionMetric"], self.log)
                waitstat_rows, waitstat_cols = SqlOsWaitStat.fetch_all_values(cursor, self.instances_per_type_metrics[instance_key]["SqlOsWaitStat"], self.log)
                vfs_rows, vfs_cols = SqlOsVirtualFileStat.fetch_all_values(cursor, self.instances_per_type_metrics[instance_key]["SqlOsVirtualFileStat"], self.log)
                clerk_rows, clerk_cols = SqlOsMemoryClerksStat.fetch_all_values(cursor, self.instances_per_type_metrics[instance_key]["SqlOsMemoryClerksStat"], self.log)

                for metric in metrics_to_collect:
                    try:
                        if type(metric) is SqlSimpleMetric:
                            metric.fetch_metric(cursor, simple_rows, custom_tags)
                        elif type(metric) is SqlFractionMetric or type(metric) is SqlIncrFractionMetric:
                            metric.fetch_metric(cursor, fraction_results, custom_tags)
                        elif type(metric) is SqlOsWaitStat:
                            metric.fetch_metric(cursor, waitstat_rows, waitstat_cols, custom_tags)
                        elif type(metric) is SqlOsVirtualFileStat:
                            metric.fetch_metric(cursor, vfs_rows, vfs_cols, custom_tags)
                        elif type(metric) is SqlOsMemoryClerksStat:
                            metric.fetch_metric(cursor, clerk_rows, clerk_cols, custom_tags)

                    except Exception as e:
                        self.log.warning("Could not fetch metric %s: %s" % (metric.datadog_name, e))

    def do_stored_procedure_check(self, instance, proc):
        """
        Fetch the metrics from the stored proc
        """

        guardSql = instance.get('proc_only_if')

        if (guardSql and self.proc_check_guard(instance, guardSql)) or not guardSql:
            self.open_db_connections(instance, self.DEFAULT_DB_KEY)
            cursor = self.get_cursor(instance, self.DEFAULT_DB_KEY)

            try:
                cursor.callproc(proc)
                rows = cursor.fetchall()
                for row in rows:
                    tags = [] if row.tags is None or row.tags == '' else row.tags.split(',')

                    if row.type in self.proc_type_mapping:
                        self.proc_type_mapping[row.type](row.metric, row.value, tags)
                    else:
                        self.log.warning('%s is not a recognised type from procedure %s, metric %s'
                                         % (row.type, proc, row.metric))

            except Exception, e:
                self.log.warning("Could not call procedure %s: %s" % (proc, e))

            self.close_cursor(cursor)
            self.close_db_connections(instance, self.DEFAULT_DB_KEY)
        else:
            self.log.info("Skipping call to %s due to only_if" % (proc))

    def proc_check_guard(self, instance, sql):
        """
        check to see if the guard SQL returns a single column containing 0 or 1
        We return true if 1, else False
        """
        self.open_db_connections(instance, self.PROC_GUARD_DB_KEY)
        cursor = self.get_cursor(instance, self.PROC_GUARD_DB_KEY)

        should_run = False
        try:
            cursor.execute(sql, ())
            result = cursor.fetchone()
            should_run = result[0] == 1
        except Exception, e:
            self.log.error("Failed to run proc_only_if sql %s : %s" % (sql, e))

        self.close_cursor(cursor)
        self.close_db_connections(instance, self.PROC_GUARD_DB_KEY)
        return should_run

    def close_cursor(self, cursor):
        """
        We close the cursor explicitly b/c we had proven memory leaks
        We handle any exception from closing, although according to the doc:
        "in adodbapi, it is NOT an error to re-close a closed cursor"
        """
        try:
            cursor.close()
        except Exception as e:
            self.log.warning("Could not close adodbapi cursor\n{0}".format(e))

    def close_db_connections(self, instance, db_key, db_name=None):
        """
        We close the db connections explicitly b/c when we don't they keep
        locks on the db. This presents as issues such as the SQL Server Agent
        being unable to stop.
        """
        conn_key = self._conn_key(instance, db_key, db_name)
        if conn_key not in self.connections:
            return

        try:
            self.connections[conn_key]['conn'].close()
            del self.connections[conn_key]
        except Exception as e:
            self.log.warning("Could not close adodbapi db connection\n{0}".format(e))

    @contextmanager
    def open_managed_db_connections(self, instance, db_key, db_name=None):
        self.open_db_connections(instance, db_key, db_name)
        yield

        self.close_db_connections(instance, db_key, db_name)

    def open_db_connections(self, instance, db_key, db_name=None):
        """
        We open the db connections explicitly, so we can ensure they are open
        before we use them, and are closable, once we are finished. Open db
        connections keep locks on the db, presenting issues such as the SQL
        Server Agent being unable to stop.
        """

        conn_key = self._conn_key(instance, db_key, db_name)
        timeout = int(instance.get('command_timeout',
                                   self.DEFAULT_COMMAND_TIMEOUT))

        dsn, host, username, password, database, driver = self._get_access_info(
            instance, db_key, db_name)
        service_check_tags = [
            'host:%s' % host,
            'db:%s' % database
        ]

        try:
            if self._get_connector(instance) == 'adodbapi':
                cs = self._conn_string_adodbapi(db_key, instance=instance, db_name=db_name)
                # autocommit: true disables implicit transaction
                rawconn = adodbapi.connect(cs, {'timeout':timeout, 'autocommit':True})
            else:
                cs = self._conn_string_odbc(db_key, instance=instance, db_name=db_name)
                rawconn = pyodbc.connect(cs, timeout=timeout)

            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)
            if conn_key not in self.connections:
                self.connections[conn_key] = {'conn': rawconn, 'timeout': timeout}
            else:
                try:
                    # explicitly trying to avoid leaks...
                    self.connections[conn_key]['conn'].close()
                except Exception as e:
                    self.log.info("Could not close adodbapi db connection\n{0}".format(e))

                self.connections[conn_key]['conn'] = rawconn
        except Exception as e:
            cx = "%s - %s" % (host, database)
            message = "Unable to connect to SQL Server for instance %s." % cx
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=message)

            password = instance.get('password')
            tracebk = traceback.format_exc()
            if password is not None:
                tracebk = tracebk.replace(password, "*" * 6)

            cxn_failure_exp = SQLConnectionError("%s \n %s" % (message, tracebk))
            raise cxn_failure_exp


class SqlServerMetric(object):
    '''General class for common methods, should never be instantiated directly
    '''

    def __init__(self, connector,  cfg_instance, base_name,
                 report_function, column, logger):
        self.connector = connector
        self.cfg_instance = cfg_instance
        self.datadog_name = cfg_instance['name']
        self.sql_name = cfg_instance['counter_name']
        self.base_name = base_name
        self.report_function = report_function
        self.instance = cfg_instance.get('instance_name', '')
        self.tag_by = cfg_instance.get('tag_by', None)
        self.column = column
        self.instances = None
        self.past_values = {}
        self.log = logger

    def fetch_metrics(self, cursor, tags):
        raise NotImplementedError


class SqlSimpleMetric(SqlServerMetric):

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = '''
            select counter_name, instance_name, cntr_value
            from sys.dm_os_performance_counters where counter_name in (%s)
            ''' % placeholders

        logger.debug("query base: %s", query_base)
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        return rows

    def fetch_metric(self, cursor, rows, tags):
        for counter_name_long, instance_name_long, cntr_value in rows:
            counter_name = counter_name_long.strip()
            instance_name = instance_name_long.strip()
            if counter_name.strip() == self.sql_name:
                matched = False
                if self.instance == ALL_INSTANCES and instance_name != "_Total":
                    matched = True
                else:
                    if instance_name == self.instance:
                        matched = True
                if matched:
                    metric_tags = tags
                    if self.instance == ALL_INSTANCES:
                        metric_tags = metric_tags + ['%s:%s' % (self.tag_by, instance_name.strip())]
                    self.report_function(self.datadog_name, cntr_value,
                                        tags=metric_tags)
                    if self.instance != ALL_INSTANCES:
                        break


class SqlFractionMetric(SqlServerMetric):

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = VALUE_AND_BASE_QUERY % placeholders

        logger.debug("query base: %s, %s", query_base, str(counters_list))
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        results = defaultdict(list)
        for counter_name, cntr_type, cntr_value, instance_name in rows:
            rowlist = [cntr_type, cntr_value, instance_name.strip()]
            logger.debug("Adding new rowlist %s", str(rowlist))
            results[counter_name.strip()].append(rowlist)
        return results

    def set_instances(self, cursor):
        if self.instance == ALL_INSTANCES:
            cursor.execute(INSTANCES_QUERY, (self.sql_name,))
            self.instances = [row.instance_name for row in cursor.fetchall()]
        else:
            self.instances = [self.instance]

    def fetch_metric(self, cursor, results, tags):
        '''
        Because we need to query the metrics by matching pairs, we can't query
        all of them together without having to perform some matching based on
        the name afterwards so instead we query instance by instance.
        We cache the list of instance so that we don't have to look it up every time
        '''
        if self.sql_name not in results:
            self.log.warning("Couldn't find %s in results", self.sql_name)
            return

        results_list = results[self.sql_name]
        done_instances = []
        for ndx, row in enumerate(results_list):
            ctype = row[0]
            cval = row[1]
            inst = row[2]

            if inst in done_instances:
                continue

            if self.instance != ALL_INSTANCES and inst != self.instance:
                done_instances.append(inst)
                continue

            #find the next row which has the same instance
            cval2 = None
            ctype2 = None
            for second_row in results_list[:ndx+1]:
                if inst == second_row[2]:
                    cval2 = second_row[1]
                    ctype2 = second_row[0]

            if cval2 is None:
                self.log.warning("Couldn't find second value for %s", self.sql_name)
                continue
            done_instances.append(inst)
            if ctype < ctype2:
                value = cval
                base = cval2
            else:
                value = cval2
                base = cval

            metric_tags = tags
            if self.instance == ALL_INSTANCES:
                metric_tags = metric_tags + ['%s:%s' % (self.tag_by, inst.strip())]
            self.report_fraction(value, base, metric_tags)

    def report_fraction(self, value, base, metric_tags):
        try:
            result = value / float(base)
            self.report_function(self.datadog_name, result, tags=metric_tags)
        except ZeroDivisionError:
            self.log.debug("Base value is 0, won't report metric %s for tags %s",
                           self.datadog_name, metric_tags)

class SqlIncrFractionMetric(SqlFractionMetric):

    def report_fraction(self, value, base, metric_tags):
        key = "key:" + "".join(metric_tags)
        if key in self.past_values:
            old_value, old_base = self.past_values[key]
            diff_value = value - old_value
            diff_base = base - old_base
            try:
                result = diff_value / float(diff_base)
                self.report_function(self.datadog_name, result, tags=metric_tags)
            except ZeroDivisionError:
                self.log.debug("Base value is 0, won't report metric %s for tags %s",
                               self.datadog_name, metric_tags)
        self.past_values[key] = (value, base)



class SqlOsWaitStat(SqlServerMetric):

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = '''
            select * from sys.dm_os_wait_stats where wait_type in (%s)
            ''' % placeholders
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        name_column_index = columns.index("wait_type")
        value_column_index = columns.index(self.column)
        value = None
        for row in rows:
            if row[name_column_index] == self.sql_name:
                value = row[value_column_index]
                break
        if value is None:
            self.log.debug("Didn't find %s %s", self.sql_name, self.column)
            return

        self.log.debug("Value for %s %s is %d", self.sql_name, self.column, value)
        metric_tags = tags
        self.report_function(self.datadog_name, value, tags=metric_tags)

class SqlOsVirtualFileStat(SqlServerMetric):

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        query_base = "select * from sys.dm_io_virtual_file_stats(null, null)"
        cursor.execute(query_base)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def __init__(self, connector,  cfg_instance, base_name,
                 report_function, column, logger):
        super(SqlOsVirtualFileStat, self).__init__(connector, cfg_instance,
                                              base_name, report_function, column,
                                              logger)
        self.dbid = self.cfg_instance.get('database_id', None)
        self.fid = self.cfg_instance.get('file_id', None)
        self.pvs_vals = defaultdict(lambda:None)

    def fetch_metric(self, cursor, rows, columns, tags):
        dbid_ndx = columns.index("database_id")
        fileid_ndx = columns.index("file_id")
        column_ndx = columns.index(self.column)
        for row in rows:
            dbid = row[dbid_ndx]
            fid = row[fileid_ndx]
            value = row[column_ndx]

            if self.dbid and self.dbid != dbid:
                continue
            if self.fid and self.fid != fid:
                continue
            if not self.pvs_vals[dbid, fid]:
                self.pvs_vals[dbid, fid] = value
                continue

            report_value = value - self.pvs_vals[dbid, fid]
            self.pvs_vals[dbid, fid] = value
            metric_tags = tags
            metric_tags = metric_tags + ['database_id:%s' % (str(dbid).strip())]
            metric_tags = metric_tags + ['file_id:%s' % (str(fid).strip())]
            metric_name = '%s.%s' % (self.datadog_name, self.column)
            self.report_function(metric_name, report_value,
                                 tags=metric_tags)

class SqlOsMemoryClerksStat(SqlServerMetric):

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = '''
            select * from sys.dm_os_memory_clerks where type in (%s)
            ''' % placeholders
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        type_column_index = columns.index("type")
        value_column_index = columns.index(self.column)
        memnode_index = columns.index("memory_node_id")

        for row in rows:
            column_val = row[value_column_index]
            node_id = row[memnode_index]
            met_type = row[type_column_index]
            if met_type != self.sql_name:
                continue

            metric_tags = tags
            metric_tags = metric_tags + ['memory_node_id:%s' % (str(node_id))]
            metric_name = '%s.%s' % (self.datadog_name, self.column)
            self.report_function(metric_name, column_val,
                                 tags=metric_tags)
