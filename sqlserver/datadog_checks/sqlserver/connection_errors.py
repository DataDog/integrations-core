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


class ConnectionErrorCode(Enum):
    """
    Denotes the various reasons a connection might fail.
    """

    unknown = "common-connection-issues"
    login_failed_for_user = "login-failed-for-user"
    tcp_connection_failed = "tcp-connection-error"
    certificate_verify_failed = "certificate-verify-fail"
    driver_not_found = "common-driver-issues"
    ssl_security_error = 'ssl-security-error'


# Connection error messages, which we expect to get from an ADO provider or
# ODBC. These drivers can have inconsistent error codes across versions, so regex on
# the known error messages
known_error_patterns = {
    # typically results in an -2147467259 ADO error code, which is not very descriptive. Identifying this error
    # can help provide specific troubleshooting help to the customer
    "(certificate verify failed|"
    "certificate chain was issued by an authority that is not trusted)": ConnectionErrorCode.certificate_verify_failed,
    # DSN could be specified incorrectly in config
    "data source name not found.* and no default driver specified": ConnectionErrorCode.driver_not_found,
    # driver not installed on host
    "(can't open lib .* file not found|Provider cannot be found)": ConnectionErrorCode.driver_not_found,
    # Connection & login issues
    "(cannot open database .* requested by the login|"
    "login timeout expired)": ConnectionErrorCode.tcp_connection_failed,
    "(login failed for user|The login is from an untrusted domain)": ConnectionErrorCode.login_failed_for_user,
    "ssl security error": ConnectionErrorCode.ssl_security_error,
}

# ADO provider connection errors yield a hresult code, which
# can be mapped to helpful err messages
known_hresult_codes = {
    -2147352567: ["unable to connect", ConnectionErrorCode.tcp_connection_failed],
    -2147217843: ["login failed for user", ConnectionErrorCode.login_failed_for_user],
    -2146824582: ["provider not found", ConnectionErrorCode.driver_not_found],
    # this error can also be e caused by a failed TCP connection, but we are already reporting on the TCP
    # connection status via test_network_connectivity, so we don't need to explicitly state that
    # as an error condition in this message
    -2147467259: ["could not open database requested by login", ConnectionErrorCode.tcp_connection_failed],
}


def error_with_tags(error_message, *args, **kwargs):
    if args:
        error_message = error_message % args

    return "{msg}\n{tags}".format(
        msg=error_message, tags=" ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(kwargs.items()))
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
            base_message, base_conn_err = _lookup_conn_error_and_msg(hresult, internal_message)
            sub_message, sub_conn_err = _lookup_conn_error_and_msg(sub_hresult, internal_message)
            if internal_message == 'Invalid connection string attribute':
                if base_message and sub_message:
                    conn_err = sub_conn_err if sub_conn_err else base_conn_err
                    return base_message + ": " + sub_message, conn_err
            else:
                # else we can return the original exception message + lookup the proper
                # ConnectionErrorCode for this issue
                conn_err = sub_conn_err if sub_conn_err else base_conn_err
                return repr(e), conn_err
        else:
            # if not an Operational error, try looking up ConnectionErr type
            # by doing a regex search on the whole exception message
            e_msg = repr(e)
            _, conn_err = _lookup_conn_error_and_msg(0, e_msg)
            return e_msg, conn_err

    elif pyodbc is not None:
        e_msg = repr(e)
        _, conn_err = _lookup_conn_error_and_msg(0, e_msg)
        if conn_err == ConnectionErrorCode.driver_not_found:
            installed, drivers = _get_is_odbc_driver_installed(driver)
            if not installed and drivers:
                e_msg += " configured odbc driver {} not in list of installed drivers: {}".format(driver, drivers)
        return e_msg, conn_err

    return repr(e), ConnectionErrorCode.unknown


def _get_is_odbc_driver_installed(configured_driver):
    if pyodbc is not None:
        drivers = pyodbc.drivers()
        return configured_driver in drivers, drivers
    return False, None


def _lookup_conn_error_and_msg(hresult, msg):
    for k in known_error_patterns.keys():
        if re.search(k, msg, re.IGNORECASE):
            return None, known_error_patterns[k]
    # if we cannot determine the type or error based on the msg, try to look it up by its hresult
    # this will be true for error messages like 'Invalid connection string attribute'
    if hresult:
        res = known_hresult_codes.get(hresult)
        if res and len(res) == 2:
            return res[0], res[1]
    return None, ConnectionErrorCode.unknown
