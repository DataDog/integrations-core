# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32api  # no cov


def get_last_error_message():  # no cov
    """
    Helper function to get the error message from the calling thread's most recently failed operation.

    It appears that in most cases pywin32 catches such failures and raises Python exceptions.
    """
    # https://docs.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-getlasterror
    # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-formatmessage
    # https://mhammond.github.io/pywin32/win32api__FormatMessage_meth.html
    return win32api.FormatMessage(0)
