# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import socket
from contextlib import closing, contextmanager

from six import raise_from

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import get_check_logger
from datadog_checks.sqlserver.cursor import CommenterCursorWrapper
from datadog_checks.sqlserver.utils import construct_use_statement

try:
    import adodbapi
except ImportError:
    adodbapi = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

from .azure import generate_managed_identity_token
from .connection_errors import ConnectionErrorCode, SQLConnectionError, error_with_tags, format_connection_exception

logger = logging.getLogger(__file__)

DATABASE_EXISTS_QUERY = 'select name, collation_name from sys.databases;'
DEFAULT_CONN_PORT = 1433
SUPPORT_LINK = "https://docs.datadoghq.com/database_monitoring/setup_sql_server/troubleshooting"

# used to specific azure AD access token, see the docs for more information on this attribute
# https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory?view=sql-server-ver16
SQL_COPT_SS_ACCESS_TOKEN = 1256


def split_sqlserver_host_port(host):
    """
    Splits the host & port out of the provided SQL Server host connection string, returning (host, port).
    """
    if not host:
        return host, None
    host_split = [s.strip() for s in host.split(',')]
    if len(host_split) == 1:
        return host_split[0], None
    if len(host_split) == 2:
        return host_split
    # else len > 2
    s_host, s_port = host_split[0:2]
    logger.warning(
        "invalid sqlserver host string has more than one comma: %s. using only 1st two items: host:%s, port:%s",
        host,
        s_host,
        s_port,
    )
    return s_host, s_port


# we're only including the bare minimum set of special characters required to parse the connection string while
# supporting escaping using braces, letting the client library or the database ultimately decide what's valid
CONNECTION_STRING_SPECIAL_CHARACTERS = set('=;{}')


def parse_connection_string_properties(cs):
    """
    Parses the properties portion of a SQL Server connection string (i.e. "key1=value1;key2=value2;...") into a map of
    {key -> value}. The string must contain *properties only*, meaning the subprotocol, serverName, instanceName and
    portNumber are not included in the string.
    See https://docs.microsoft.com/en-us/sql/connect/jdbc/building-the-connection-url
    """
    cs = cs.strip()
    params = {}
    i = 0
    escaping = False
    key, parsed, key_done = "", "", False
    while i < len(cs):
        if escaping:
            if cs[i : i + 2] == '}}':
                parsed += '}'
                i += 2
                continue
            if cs[i] == '}':
                escaping = False
                i += 1
                continue
            parsed += cs[i]
            i += 1
            continue
        if cs[i] == '{':
            escaping = True
            i += 1
            continue
        # ignore leading whitespace, i.e. between two keys "A=B;  C=D"
        if not key_done and not parsed and cs[i] == ' ':
            i += 1
            continue
        if cs[i] == '=':
            if key_done:
                raise ConfigurationError(
                    "Invalid connection string: unexpected '=' while parsing value at index={}: {}".format(i, cs)
                )
            key, parsed, key_done = parsed, "", True
            if not key:
                raise ConfigurationError("Invalid connection string: empty key at index={}: {}".format(i, cs))
            i += 1
            continue
        if cs[i] == ';':
            if not parsed:
                raise ConfigurationError("Invalid connection string: empty value at index={}: {}".format(i, cs))
            params[key] = parsed
            key, parsed, key_done = "", "", False
            i += 1
            continue
        if cs[i] in CONNECTION_STRING_SPECIAL_CHARACTERS:
            raise ConfigurationError(
                "Invalid connection string: invalid character '{}' at index={}: {}".format(cs[i], i, cs)
            )
        parsed += cs[i]
        i += 1
    # the last ';' can be omitted so check for a final remaining param here
    if escaping:
        raise ConfigurationError(
            "Invalid connection string: did not find expected matching closing brace '}}': {}".format(cs)
        )
    if key:
        if not parsed:
            raise ConfigurationError(
                "Invalid connection string: empty value at the end of the connection string: {}".format(cs)
            )
        params[key] = parsed
    return params


class Connection(object):
    """Manages the connection to a SQL Server instance."""

    DEFAULT_COMMAND_TIMEOUT = 10
    DEFAULT_DATABASE = 'master'
    DEFAULT_ADOPROVIDER = 'MSOLEDBSQL'
    DEFAULT_CONNECTOR = 'adodbapi'
    DEFAULT_ODBC_DRIVER = '{ODBC Driver 18 for SQL Server}'
    DEFAULT_DB_KEY = 'database'
    DEFAULT_SQLSERVER_VERSION = 1e9
    SQLSERVER_2014 = 2014
    PROC_GUARD_DB_KEY = 'proc_only_if_database'

    VALID_ADOPROVIDERS = ['SQLOLEDB', 'MSOLEDBSQL', 'MSOLEDBSQL19', 'SQLNCLI11']

    def __init__(self, host, init_config, instance_config, service_check_handler):
        self.host = host
        self.instance = instance_config
        self.service_check_handler = service_check_handler
        self.log = get_check_logger()

        self.managed_auth_enabled = False
        self.managed_identity_client_id = None
        self.managed_identity_scope = None
        managed_identity = self.instance.get('managed_identity')
        if managed_identity:
            self.managed_auth_enabled = True
            self.managed_identity_client_id = managed_identity.get("client_id")
            self.managed_identity_scope = managed_identity.get("identity_scope")

        # mapping of raw connections based on conn_key to different databases
        self._conns = {}
        self.timeout = int(self.instance.get('command_timeout', self.DEFAULT_COMMAND_TIMEOUT))
        self.existing_databases = None
        self.server_version = int(self.instance.get('server_version', self.DEFAULT_SQLSERVER_VERSION))
        self.connector = self._get_connector(init_config, instance_config)
        self.adoprovider = self._get_adoprovider(init_config, instance_config)

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
        return CommenterCursorWrapper(conn.cursor())

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

        _, host, _, _, database, driver = self._get_access_info(db_key, db_name)

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
                if self.managed_auth_enabled:
                    token_struct = generate_managed_identity_token(
                        self.managed_identity_client_id, self.managed_identity_scope
                    )
                    rawconn = pyodbc.connect(
                        cs, timeout=self.timeout, autocommit=True, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
                    )
                else:
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
            error_message = self.test_network_connectivity()
            tcp_connection_status = error_message if error_message else "OK"
            exception_msg, conn_warn_msg = format_connection_exception(e, driver)
            if tcp_connection_status != "OK" and conn_warn_msg is ConnectionErrorCode.unknown:
                conn_warn_msg = ConnectionErrorCode.tcp_connection_failed

            password = self.instance.get('password')
            if password is not None:
                exception_msg = exception_msg.replace(password, "*" * 6)

            check_err_message = error_with_tags(
                "Unable to connect to SQL Server, see %s#%s for more details on how to debug this issue. "
                "TCP-connection(%s), Exception: %s",
                SUPPORT_LINK,
                conn_warn_msg.value,
                tcp_connection_status,
                exception_msg,
                host=host,
                connection_host=host,
                database=database,
                code=conn_warn_msg.value,
                connector=self.connector,
                driver=driver,
            )
            self.service_check_handler(AgentCheck.CRITICAL, host, database, check_err_message, is_default=is_default)

            # Only raise exception on the default instance database
            if is_default:
                # the message that is raised here (along with the exception stack trace)
                # is what will be seen in the agent status output.
                raise_from(SQLConnectionError(check_err_message), None)
            else:
                # if not the default db, we should still log this exception
                # to give the customer an opportunity to fix the issue
                self.log.debug(check_err_message)

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
                for row in cursor.fetchall():
                    # collation_name can be NULL if db offline, in that case assume its case_insensitive
                    case_insensitive = not row.collation_name or 'CI' in row.collation_name
                    self.existing_databases[row.name.lower()] = (
                        case_insensitive,
                        row.name,
                    )

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

    def _get_connector(self, init_config, instance_config):
        '''
        Get the connector to use for the instance.
        The connector config value takes precedence in the following order:
        - instance_config
        - init_config
        - DEFAULT_CONNECTOR
        '''
        # First we check the valid connectors available. i.e. adodbapi, odbc
        valid_connectors = []
        if adodbapi is not None:
            valid_connectors.append('adodbapi')
        if pyodbc is not None:
            valid_connectors.append('odbc')

        # Then we check the connector value from the init_config and instance_config
        connector_from_init_config = init_config.get('connector')
        if connector_from_init_config is not None and connector_from_init_config.lower() not in valid_connectors:
            self.log.warning(
                "Invalid database connector %s set in init_config, falling back to default %s",
                connector_from_init_config,
                self.DEFAULT_CONNECTOR,
            )
            connector_from_init_config = None

        connector_from_instance_config = instance_config.get('connector')
        if (
            connector_from_instance_config is not None
            and connector_from_instance_config.lower() not in valid_connectors
        ):
            self.log.warning(
                "Invalid database connector %s set in instance_config, falling back to default %s",
                connector_from_instance_config,
                self.DEFAULT_CONNECTOR,
            )
            connector_from_instance_config = None

        return connector_from_instance_config or connector_from_init_config or self.DEFAULT_CONNECTOR

    def _get_adoprovider(self, init_config, instance_config):
        '''
        Get the adoprovider to use for the instance.
        The adoprovider config value takes precedence in the following order:
        - instance_config
        - init_config
        - DEFAULT_ADOPROVIDER
        '''
        adoprovider_from_init_config = init_config.get('adoprovider')
        if (
            adoprovider_from_init_config is not None
            and adoprovider_from_init_config.upper() not in self.VALID_ADOPROVIDERS
        ):
            self.log.warning(
                "Invalid ADODB provider set in init_config %s, falling back to default %s",
                adoprovider_from_init_config,
                self.DEFAULT_ADOPROVIDER,
            )
            adoprovider_from_init_config = None

        adoprovider_from_instance_config = instance_config.get('adoprovider')
        if (
            adoprovider_from_instance_config is not None
            and adoprovider_from_instance_config.upper() not in self.VALID_ADOPROVIDERS
        ):
            self.log.warning(
                "Invalid ADODB provider set in instance_config %s, falling back to default %s",
                adoprovider_from_instance_config,
                self.DEFAULT_ADOPROVIDER,
            )
            adoprovider_from_instance_config = None

        return adoprovider_from_instance_config or adoprovider_from_init_config or self.DEFAULT_ADOPROVIDER

    def _get_access_info(self, db_key, db_name=None):
        """Convenience method to extract info from instance"""
        dsn = self.instance.get('dsn')
        username = self.instance.get('username')
        password = self.instance.get('password')
        database = self.instance.get(db_key) if db_name is None else db_name
        driver = self.instance.get('driver')
        host = self.get_host_with_port()

        if not dsn:
            if not host:
                self.log.debug("No host provided, falling back to defaults: host=127.0.0.1, port=1433")
                host = "127.0.0.1,1433"
            if not database:
                self.log.debug(
                    "No database provided, falling back to default: %s",
                    self.DEFAULT_DATABASE,
                )
                database = self.DEFAULT_DATABASE
            if not driver and self.connector == 'odbc':
                self.log.debug(
                    "No odbc driver provided, falling back to default: %s",
                    self.DEFAULT_ODBC_DRIVER,
                )
                driver = self.DEFAULT_ODBC_DRIVER
        return dsn, host, username, password, database, driver

    def get_host_with_port(self):
        """Return a string with correctly formatted host and, if necessary, port.
        If the host string in the config contains a port, that port is used.
        If not, any port provided as a separate port config option is used.
        If the port is misconfigured or missing, default port is used.

        In most cases, we return a string of host,port.
        If the user provides a port value of 0, that indicates that they are
        using a port autodiscovery service like Sql Server Browser Service. In
        this case, we return just the host.
        """
        host = self.instance.get("host")
        if not host:
            return None

        port = DEFAULT_CONN_PORT
        split_host, split_port = split_sqlserver_host_port(host)
        config_port = self.instance.get("port")

        if split_port is not None:
            port = split_port
        elif config_port is not None:
            port = config_port
        try:
            int(port)
        except ValueError:
            self.log.warning("Invalid port %s; falling back to default 1433", port)
            port = DEFAULT_CONN_PORT

        # If the user provides a port of 0, they are indicating that they
        # are using a port autodiscovery service, and we want their connection
        # string to include just the host.
        if int(port) == 0:
            return split_host

        return split_host + "," + str(port)

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

        if self.managed_auth_enabled:
            if username or password:
                raise ConfigurationError(
                    "Azure AD Authentication is configured, but username and password properties are also set "
                    "please remove `username` and `password` from your instance config to use"
                    "AD Authentication with a Managed Identity"
                )
            # client_id is used as the user id for managed user identities or server principals
            if not self.managed_identity_client_id:
                raise ConfigurationError(
                    "Azure Managed Identity Authentication is not properly configured "
                    "missing required property, client_id"
                )

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
            self.log.warning(
                "%s option will be ignored since %s connection is used",
                option,
                self.connector,
            )

        if cs is None:
            return

        parsed_cs = parse_connection_string_properties(cs)
        lowercased_keys_cs = {k.lower(): v for k, v in parsed_cs.items()}

        if lowercased_keys_cs.get('trusted_connection', "false").lower() in {
            'yes',
            'true',
        } and (username or password):
            self.log.warning("Username and password are ignored when using Windows authentication")

        for key, value in connector_options.items():
            if key.lower() in lowercased_keys_cs and self.instance.get(value) is not None:
                raise ConfigurationError(
                    "%s has been provided both in the connection string and as a "
                    "configuration option (%s), please specify it only once" % (key, value)
                )
        for key in other_connector_options.keys():
            if key.lower() in lowercased_keys_cs:
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

        if self.managed_auth_enabled:
            # if managed_identity authentication is configured,
            # remove the username/password from the CS, if set
            username = None
            password = None

        # The connection resiliency feature is supported on Microsoft Azure SQL Database
        # and SQL Server 2014 (and later) server versions. See the SQLServer docs for more information
        # https://docs.microsoft.com/en-us/sql/connect/odbc/connection-resiliency?view=sql-server-ver15
        conn_str = ''
        if self.server_version >= self.SQLSERVER_2014:
            conn_str += 'ConnectRetryCount=2;'
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

        retry_conn_count = ''
        if self.server_version >= self.SQLSERVER_2014:
            retry_conn_count = 'ConnectRetryCount=2;'
        conn_str = '{}Provider={};Data Source={};Initial Catalog={};'.format(
            retry_conn_count, self.adoprovider, host, database
        )

        if username:
            conn_str += 'User ID={};'.format(username)
        self.log.debug("Connection string (before password) %s", conn_str)
        if password:
            conn_str += 'Password={};'.format(password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str

    def test_network_connectivity(self):
        """
        Tries to establish a TCP connection to the database host.
        If there is an error, it returns a description of the error.

        :return: error_message if failed connection else None
        """
        host, port = split_sqlserver_host_port(self.instance.get('host'))
        if port is None:
            port = DEFAULT_CONN_PORT
            provided_port = self.instance.get("port")
            if provided_port is not None:
                port = provided_port

        try:
            port = int(port)
        except ValueError as e:
            return "ERROR: invalid port: {}".format(repr(e))

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(self.timeout)
            try:
                sock.connect((host, port))
            except Exception as e:
                return "ERROR: {}".format(e.strerror if hasattr(e, 'strerror') else repr(e))

        return None

    def _get_current_database_context(self):
        """
        Get the current database name.
        """
        with self.get_managed_cursor() as cursor:
            cursor.execute('select DB_NAME()')
            data = cursor.fetchall()
            return data[0][0]

    @contextmanager
    def restore_current_database_context(self):
        """
        Restores the default database after executing use statements.
        """
        current_db = self._get_current_database_context()
        try:
            yield
        finally:
            if current_db:
                try:
                    self.log.debug("Restoring the original database context %s", current_db)
                    with self.get_managed_cursor() as cursor:
                        cursor.execute(construct_use_statement(current_db))
                except Exception as e:
                    self.log.error("Failed to switch back to the original database context %s: %s", current_db, e)
