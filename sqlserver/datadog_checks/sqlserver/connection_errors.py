# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from enum import Enum

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    import adodbapi
    from adodbapi.apibase import OperationalError
    from pywintypes import com_error
except ImportError:
    adodbapi = None


class SQLConnectionError(Exception):
    """Exception raised for SQL instance connection issues"""

    pass


class ConnectionErrWarning(Enum):
    """
    Denotes the various reasons a connection might fail.
    """

    unknown = "diagnosing-common-connection-issues"
    login_failed_for_user = "sql-server-unable-to-connect-login-failed-for-user"
    tcp_connection_failed = "sql-server-unable-to-connect-due-to-invalid-connection-string-attribute"
    certificate_verify_failed = "ssl-provider-the-certificate-chain-was-issued-by-an-authority-that-is-not-trusted"
    driver_not_installed = "picking-a-sql-server-driver"
    dsn_not_found = "data-source-name-not-found-and-no-default-driver-specified"
    ssl_security_error = 'sql-server-unable-to-connect-ssl-security-error-18'


ODBC_DB_FAILURE_REGEX = "(cannot open database .* requested by the login. the login failed|login timeout expired)"


# Connection error messages, which we expect to get from an ODBC driver
# ODBC drivers have inconsistent error codes across versions, so regex on
# the known error messages
known_odbc_error_patterns = {
    # DSN could be specified incorrectly in config
    "data source name not found, and no default driver specified": ConnectionErrWarning.dsn_not_found,
    # driver not installed on host
    "can't open lib .* file not found": ConnectionErrWarning.driver_not_installed,
    # SSL verification failed
    "certificate verify failed": ConnectionErrWarning.certificate_verify_failed,
    # Connection & login issues
    ODBC_DB_FAILURE_REGEX: ConnectionErrWarning.tcp_connection_failed,
    "login failed for user": ConnectionErrWarning.login_failed_for_user,
    "ssl security error": ConnectionErrWarning.ssl_security_error,
}

# Connection error messages, which we expect to get from an ADO provider
known_ado_errors = {
    # typically results in an -2147467259 error code, which is not very descriptive. Identifying this error
    # can help provide specific troubleshooting help to the customer
    "certificate chain was issued by an authority that is not trusted": ConnectionErrWarning.certificate_verify_failed,
}

# ADO provider connection errors yield a hresult code, which
# can be mapped to helpful err messages
known_hresult_codes = {
    -2147352567: ["unable to connect", ConnectionErrWarning.tcp_connection_failed],
    -2147217843: ["login failed for user", ConnectionErrWarning.login_failed_for_user],
    -2146824582: ["provider not found", ConnectionErrWarning.driver_not_installed],
    # this error can also be e caused by a failed TCP connection, but we are already reporting on the TCP
    # connection status via test_network_connectivity, so we don't need to explicitly state that
    # as an error condition in this message
    -2147467259: ["could not open database requested by login", ConnectionErrWarning.tcp_connection_failed],
}


def warning_with_tags(warning_message, *args, **kwargs):
    if args:
        warning_message = warning_message % args

    return "{msg}\n{tags}".format(
        msg=warning_message, tags=" ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(kwargs.items()))
    )


def format_connection_exception(e, driver):
    """
    Formats the provided database connection exception.
    If the exception comes from an ADO Provider and contains a misleading 'Invalid connection string attribute' message
    then the message is replaced with more descriptive messages based on the contained HResult error codes.
    """
    if adodbapi is not None:
        if isinstance(e, OperationalError) and e.args and isinstance(e.args[0], com_error):
            e_comm = e.args[0]
            hresult = e_comm.hresult
            sub_hresult = None
            internal_message = None
            if e_comm.args and len(e_comm.args) == 4:
                internal_args = e_comm.args[2]
                if len(internal_args) == 6:
                    internal_message = internal_args[2]
                    sub_hresult = internal_args[5]
            base_message, base_conn_err = _lookup_ado_conn_error_and_msg(hresult, internal_message)
            sub_message, sub_conn_err = _lookup_ado_conn_error_and_msg(sub_hresult, internal_message)
            if internal_message == 'Invalid connection string attribute':
                if base_message and sub_message:
                    conn_err = sub_conn_err if sub_conn_err else base_conn_err
                    return base_message + ": " + sub_message, conn_err
            else:
                # else we can return the original exception message + lookup the proper
                # ConnectionErrWarning for this issue
                conn_err = sub_conn_err if sub_conn_err else base_conn_err
                return repr(e), conn_err

    elif pyodbc is not None:
        e_msg = repr(e)
        conn_err = _lookup_odbc_conn_error(e_msg)
        if conn_err == ConnectionErrWarning.driver_not_installed:
            installed, drivers = _get_is_odbc_driver_installed(driver)
            if not installed and drivers:
                e_msg += " configured odbc driver {} not in list of installed drivers: {}".format(driver, drivers)
        return e_msg, conn_err

    return repr(e), None


def _get_is_odbc_driver_installed(configured_driver):
    if pyodbc is not None:
        drivers = pyodbc.drivers()
        return configured_driver in drivers, drivers
    return False, None


def _lookup_odbc_conn_error(msg):
    for k in known_odbc_error_patterns.keys():
        if re.search(k.lower(), msg.lower()):
            return known_odbc_error_patterns[k]


def _lookup_ado_conn_error_and_msg(hresult, msg):
    for k in known_ado_errors.keys():
        if k.lower() in msg.lower():
            return None, known_ado_errors[k]
    if hresult > 0:
        res = known_hresult_codes.get(hresult)
        if len(res) > 0:
            return res[0], res[1]
