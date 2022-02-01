# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import contextmanager

from six import raise_from

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import get_check_logger

try:
    import adodbapi
except ImportError:
    adodbapi = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

DATABASE_EXISTS_QUERY = 'select name, collation_name from sys.databases;'


class SQLConnectionError(Exception):
    """Exception raised for SQL instance connection issues"""

    pass


class Connection(object):
    """Manages the connection to a SQL Server instance."""

    DEFAULT_COMMAND_TIMEOUT = 5
    DEFAULT_DATABASE = 'master'
    DEFAULT_DRIVER = 'SQL Server'
    DEFAULT_DB_KEY = 'database'
    PROC_GUARD_DB_KEY = 'proc_only_if_database'

    valid_adoproviders = ['SQLOLEDB', 'MSOLEDBSQL', 'SQLNCLI11']
    default_adoprovider = 'SQLOLEDB'

    def __init__(self, init_config, instance_config, service_check_handler):
        self.instance = instance_config
        self.service_check_handler = service_check_handler
        self.log = get_check_logger()

        # mapping of raw connections based on conn_key to different databases
        self._conns = {}
        self.timeout = int(self.instance.get('command_timeout', self.DEFAULT_COMMAND_TIMEOUT))
        self.existing_databases = None

        self.adoprovider = self.default_adoprovider

        self.valid_connectors = []
        if adodbapi is not None:
            self.valid_connectors.append('adodbapi')
        if pyodbc is not None:
            self.valid_connectors.append('odbc')

        self.default_connector = init_config.get('connector', 'adodbapi')
        if self.default_connector.lower() not in self.valid_connectors:
            self.log.error("Invalid database connector %s, defaulting to adodbapi", self.default_connector)
            self.default_connector = 'adodbapi'

        self.connector = self.get_connector()

        self.adoprovider = init_config.get('adoprovider', self.default_adoprovider)
        if self.adoprovider.upper() not in self.valid_adoproviders:
            self.log.error(
                "Invalid ADODB provider string %s, defaulting to %s", self.adoprovider, self.default_adoprovider
            )
            self.adoprovider = self.default_adoprovider

        self.log.debug('Connection initialized.')

    @contextmanager
    def get_managed_cursor(self, key_prefix=None):
        cursor = self.get_cursor(self.DEFAULT_DB_KEY, key_prefix=key_prefix)
        try:
            yield cursor
        finally:
            self.close_cursor(cursor)

    def get_cursor(self, db_key, db_name=None, key_prefix=None):
        """
        Return a cursor to execute query against the db
        Cursor are cached in the self.connections dict
        """
        conn_key = self._conn_key(db_key, db_name, key_prefix)
        try:
            conn = self._conns[conn_key]
        except KeyError:
            # We catch KeyError to avoid leaking the auth info used to compose the key
            # FIXME: we should find a better way to compute unique keys to map opened connections other than
            # using auth info in clear text!
            raise SQLConnectionError("Cannot find an opened connection for host: {}".format(self.instance.get('host')))
        return conn.cursor()

    def close_cursor(self, cursor):
        """
        We close the cursor explicitly b/c we had proven memory leaks
        We handle any exception from closing, although according to the doc:
        "in adodbapi, it is NOT an error to re-close a closed cursor"
        """
        try:
            cursor.close()
        except Exception as e:
            self.log.warning("Could not close adodbapi cursor\n%s", e)

    def check_database(self):
        with self.open_managed_default_database():
            db_exists, context = self._check_db_exists()

        return db_exists, context

    def check_database_conns(self, db_name):
        self.open_db_connections(None, db_name=db_name, is_default=False)
        self.close_db_connections(None, db_name)

    @contextmanager
    def open_managed_default_database(self):
        with self._open_managed_db_connections(None, db_name=self.DEFAULT_DATABASE):
            yield

    @contextmanager
    def open_managed_default_connection(self, key_prefix=None):
        with self._open_managed_db_connections(self.DEFAULT_DB_KEY, key_prefix=key_prefix):
            yield

    @contextmanager
    def _open_managed_db_connections(self, db_key, db_name=None, key_prefix=None):
        self.open_db_connections(db_key, db_name, key_prefix=key_prefix)
        try:
            yield
        finally:
            self.close_db_connections(db_key, db_name, key_prefix=key_prefix)

    def open_db_connections(self, db_key, db_name=None, is_default=True, key_prefix=None):
        """
        We open the db connections explicitly, so we can ensure they are open
        before we use them, and are closable, once we are finished. Open db
        connections keep locks on the db, presenting issues such as the SQL
        Server Agent being unable to stop.
        """
        conn_key = self._conn_key(db_key, db_name, key_prefix)

        _, host, _, _, database, _ = self._get_access_info(db_key, db_name)

        cs = self.instance.get('connection_string', '')
        cs += ';' if cs != '' else ''

        self._connection_options_validation(db_key, db_name)

        try:
            if self.connector == 'adodbapi':
                cs += self._conn_string_adodbapi(db_key, db_name=db_name)
                # autocommit: true disables implicit transaction
                rawconn = adodbapi.connect(cs, {'timeout': self.timeout, 'autocommit': True})
            else:
                cs += self._conn_string_odbc(db_key, db_name=db_name)
                rawconn = pyodbc.connect(cs, timeout=self.timeout, autocommit=True)
                rawconn.timeout = self.timeout

            self.service_check_handler(AgentCheck.OK, host, database, is_default=is_default)
            if conn_key not in self._conns:
                self._conns[conn_key] = rawconn
            else:
                try:
                    # explicitly trying to avoid leaks...
                    self._conns[conn_key].close()
                except Exception as e:
                    self.log.info("Could not close adodbapi db connection\n%s", e)

                self._conns[conn_key] = rawconn
            self._setup_new_connection(rawconn)
        except Exception as e:
            cx = "{} - {}".format(host, database)

            if is_default:
                message = "Unable to connect to SQL Server for instance {}: {}".format(cx, repr(e))
            else:
                message = "Unable to connect to Database: {} for instance {}: {}".format(database, host, repr(e))
            password = self.instance.get('password')
            if password is not None:
                message = message.replace(password, "*" * 6)

            self.service_check_handler(AgentCheck.CRITICAL, host, database, message, is_default=is_default)

            raise_from(SQLConnectionError(message), None)

    def _setup_new_connection(self, rawconn):
        with rawconn.cursor() as cursor:
            # ensure that by default, the agent's reads can never block updates to any tables it's reading from
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")

    def close_db_connections(self, db_key, db_name=None, key_prefix=None):
        """
        We close the db connections explicitly b/c when we don't they keep
        locks on the db. This presents as issues such as the SQL Server Agent
        being unable to stop.
        """
        conn_key = self._conn_key(db_key, db_name, key_prefix)
        if conn_key not in self._conns:
            return

        try:
            self._conns[conn_key].close()
            del self._conns[conn_key]
        except Exception as e:
            self.log.warning("Could not close adodbapi db connection\n%s", e)

    def _check_db_exists(self):
        """
        Check for existence of a database, but take into consideration whether the db is case-sensitive or not.

        If not case-sensitive, then we normalize the database name to lowercase on both sides and check.
        If case-sensitive, then we only accept exact-name matches.

        If the check fails, then we won't do any checks if `ignore_missing_database` is enabled, or we will fail
        with a ConfigurationError otherwise.
        """

        _, host, _, _, database, _ = self._get_access_info(self.DEFAULT_DB_KEY)
        context = "{} - {}".format(host, database)
        if self.existing_databases is None:
            cursor = self.get_cursor(None, self.DEFAULT_DATABASE)

            try:
                self.existing_databases = {}
                cursor.execute(DATABASE_EXISTS_QUERY)
                for row in cursor:
                    # collation_name can be NULL if db offline, in that case assume its case_insensitive
                    case_insensitive = not row.collation_name or 'CI' in row.collation_name
                    self.existing_databases[row.name.lower()] = case_insensitive, row.name

            except Exception as e:
                self.log.error("Failed to check if database %s exists: %s", database, e)
                return False, context
            finally:
                self.close_cursor(cursor)

        exists = False
        if database.lower() in self.existing_databases:
            case_insensitive, cased_name = self.existing_databases[database.lower()]
            if case_insensitive or database == cased_name:
                exists = True

        return exists, context

    def get_connector(self):
        connector = self.instance.get('connector', self.default_connector)
        if connector != self.default_connector:
            if connector.lower() not in self.valid_connectors:
                self.log.warning("Invalid database connector %s using default %s", connector, self.default_connector)
                connector = self.default_connector
            else:
                self.log.debug("Overriding default connector for %s with %s", self.instance['host'], connector)
        return connector

    def _get_adoprovider(self):
        provider = self.instance.get('adoprovider', self.default_adoprovider)
        if provider != self.adoprovider:
            if provider.upper() not in self.valid_adoproviders:
                self.log.warning("Invalid ADO provider %s using default %s", provider, self.adoprovider)
                provider = self.adoprovider
            else:
                self.log.debug("Overriding default ADO provider for %s with %s", self.instance['host'], provider)
        return provider

    def _get_access_info(self, db_key, db_name=None):
        """Convenience method to extract info from instance"""
        dsn = self.instance.get('dsn')
        host = self.instance.get('host')
        username = self.instance.get('username')
        password = self.instance.get('password')
        database = self.instance.get(db_key) if db_name is None else db_name
        driver = self.instance.get('driver')
        if not dsn:
            if not host:
                host = '127.0.0.1,1433'
            if not database:
                database = self.DEFAULT_DATABASE
            if not driver:
                driver = self.DEFAULT_DRIVER
        return dsn, host, username, password, database, driver

    def _conn_key(self, db_key, db_name=None, key_prefix=None):
        """Return a key to use for the connection cache"""
        dsn, host, username, password, database, driver = self._get_access_info(db_key, db_name)
        if not key_prefix:
            key_prefix = ""
        return '{}{}:{}:{}:{}:{}:{}'.format(key_prefix, dsn, host, username, password, database, driver)

    def _connection_options_validation(self, db_key, db_name):
        cs = self.instance.get('connection_string')
        username = self.instance.get('username')
        password = self.instance.get('password')

        adodbapi_options = {
            'PROVIDER': 'adoprovider',
            'Data Source': 'host',
            'Initial Catalog': db_name or db_key,
            'User ID': 'username',
            'Password': 'password',
        }
        odbc_options = {
            'DSN': 'dsn',
            'DRIVER': 'driver',
            'SERVER': 'host',
            'DATABASE': db_name or db_key,
            'UID': 'username',
            'PWD': 'password',
        }

        if self.connector == 'adodbapi':
            other_connector = 'odbc'
            connector_options = adodbapi_options
            other_connector_options = odbc_options

        else:
            other_connector = 'adodbapi'
            connector_options = odbc_options
            other_connector_options = adodbapi_options

        for option in {
            value
            for key, value in other_connector_options.items()
            if value not in connector_options.values() and self.instance.get(value) is not None
        }:
            self.log.warning("%s option will be ignored since %s connection is used", option, self.connector)

        if cs is None:
            return

        if 'Trusted_Connection=yes' in cs and (username or password):
            self.log.warning("Username and password are ignored when using Windows authentication")
        cs = cs.upper()

        for key, value in connector_options.items():
            if key.upper() in cs and self.instance.get(value) is not None:
                raise ConfigurationError(
                    "%s has been provided both in the connection string and as a "
                    "configuration option (%s), please specify it only once" % (key, value)
                )
        for key in other_connector_options.keys():
            if key.upper() in cs:
                raise ConfigurationError(
                    "%s has been provided in the connection string. "
                    "This option is only available for %s connections,"
                    " however %s has been selected" % (key, other_connector, self.connector)
                )

    def _conn_string_odbc(self, db_key, conn_key=None, db_name=None):
        """Return a connection string to use with odbc"""
        if conn_key:
            dsn, host, username, password, database, driver = conn_key.split(":")
        else:
            dsn, host, username, password, database, driver = self._get_access_info(db_key, db_name)

        conn_str = 'ConnectRetryCount=2;'
        if dsn:
            conn_str += 'DSN={};'.format(dsn)

        if driver:
            conn_str += 'DRIVER={};'.format(driver)
        if host:
            conn_str += 'Server={};'.format(host)
        if database:
            conn_str += 'Database={};'.format(database)

        if username:
            conn_str += 'UID={};'.format(username)
        self.log.debug("Connection string (before password) %s", conn_str)
        if password:
            conn_str += 'PWD={};'.format(password)
        return conn_str

    def _conn_string_adodbapi(self, db_key, conn_key=None, db_name=None):
        """Return a connection string to use with adodbapi"""
        if conn_key:
            _, host, username, password, database, _ = conn_key.split(":")
        else:
            _, host, username, password, database, _ = self._get_access_info(db_key, db_name)

        provider = self._get_adoprovider()
        conn_str = 'ConnectRetryCount=2;Provider={};Data Source={};Initial Catalog={};'.format(provider, host, database)

        if username:
            conn_str += 'User ID={};'.format(username)
        self.log.debug("Connection string (before password) %s", conn_str)
        if password:
            conn_str += 'Password={};'.format(password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str
