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


def enumerate_windows_services(logger=None, wrap_errors=True):
    """
    Enumerate all Windows services with full details.
    
    Args:
        logger: Optional logger instance for debug/error messages
        wrap_errors: If True, wrap exceptions in generic Exception. If False, let them propagate.
    
    Returns:
        list: List of tuples (short_name, display_name, service_status_tuple)
              where service_status_tuple[1] contains the state code
    
    Raises:
        Exception: When wrap_errors=False and enumeration fails
    """
    if platform.system() != 'Windows':
        if logger:
            logger.debug("Non-Windows platform, returning empty service list")
        return []
    
    try:
        import win32service

        scm_handle = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        service_statuses = win32service.EnumServicesStatus(
            scm_handle, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL
        )
        win32service.CloseServiceHandle(scm_handle)
        
        # Return in the expected format: (short_name, display_name, service_status_tuple)
        return service_statuses
        
    except ImportError as e:
        error_msg = f"pywin32 not available: {e}"
        if logger:
            logger.warning(error_msg)
        if not wrap_errors:
            raise Exception(f'Unable to open SCManager: {error_msg}')
        return []
        
    except Exception as e:
        error_msg = f"Failed to enumerate services: {e}"
        if logger:
            logger.error(error_msg)
        if not wrap_errors:
            raise Exception(f'Unable to open SCManager: {error_msg}')
        return []


def get_windows_service_states(services_to_check, logger=None):
    """
    Get Windows service states for specific services.
    
    Args:
        services_to_check: Set or list of service names to check
        logger: Optional logger instance for debug/error messages
    
    Returns:
        dict: Service name -> state code (1-7), or None if service not found
    """
    if platform.system() != 'Windows':
        if logger:
            logger.debug("Non-Windows platform, returning empty service states")
        return {}
    
    # Get all service states efficiently
    all_states = get_all_windows_service_states(logger)
    if not all_states:
        # Return dict with None values for all requested services
        return {service: None for service in services_to_check}
    
    # Filter to only requested services
    result = {}
    for service_name in services_to_check:
        result[service_name] = all_states.get(service_name)
    
    return result
