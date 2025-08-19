# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import platform


def get_all_windows_service_states(logger=None):
    """
    Get all Windows service states using bulk enumeration.
    Returns:
        dict: Service name -> state code (1-7), or empty dict if error
        On non-Windows: returns empty dict
    """
    if platform.system() != 'Windows':
        if logger:
            logger.debug("Non-Windows platform, returning empty service states")
        return {}
    try:
        import win32service

        scm_handle = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        service_statuses = win32service.EnumServicesStatus(
            scm_handle, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        win32service.CloseServiceHandle(scm_handle)
        # Build dict of service_name -> state
        return {name: state_tuple[1] for name, display_name, state_tuple in service_statuses}  # state is at index 1
    except ImportError as e:
        if logger:
            logger.warning("pywin32 not available: %s", e)
        return {}
    except Exception as e:
        if logger:
            logger.error("Failed to enumerate services: %s", e)
        return {}


def is_windows_service_running(service_name, logger=None):
    """
    Check if a Windows service is running (simple wrapper for compatibility).
    Returns:
        bool: True if running or unable to determine, False if stopped
    """
    states = get_all_windows_service_states(logger)
    if not states:
        # No states available (non-Windows or error) - be optimistic
        return True

    state = states.get(service_name)
    if state is None:
        # Service not found - be optimistic
        if logger:
            logger.debug("Service %s not found", service_name)
        return True

    # State 4 is SERVICE_RUNNING
    return state == 4
