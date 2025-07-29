# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import platform
from typing import Tuple, Optional

from datadog_checks.base.constants import ServiceCheck

# Map Windows service states to Datadog service check statuses
# This mapping is used by both windows_service and active_directory integrations
STATE_TO_STATUS = {
    1: ServiceCheck.CRITICAL,   # SERVICE_STOPPED
    2: ServiceCheck.WARNING,    # SERVICE_START_PENDING
    3: ServiceCheck.WARNING,    # SERVICE_STOP_PENDING
    4: ServiceCheck.OK,         # SERVICE_RUNNING
    5: ServiceCheck.WARNING,    # SERVICE_CONTINUE_PENDING
    6: ServiceCheck.WARNING,    # SERVICE_PAUSE_PENDING
    7: ServiceCheck.WARNING,    # SERVICE_PAUSED
}


def is_service_running(service_name: str, log=None) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Check if a Windows service is running.
    
    Args:
        service_name: Name of the Windows service to check
        log: Optional logger instance for debugging
        
    Returns:
        Tuple of (is_running, state, error_message)
        - is_running: True if service is in RUNNING state
        - state: The actual service state code (1-7) or None if error
        - error_message: Error description if any, None if successful
    """
    # Check platform
    if platform.system() != 'Windows':
        if log:
            log.debug("Not running on Windows, assuming service %s is running", service_name)
        return True, 4, None  # Assume running on non-Windows for dev/testing
    
    try:
        import win32service
        import win32serviceutil
        
        # Query service status
        status = win32serviceutil.QueryServiceStatus(service_name)
        state = status[1]  # Current state is at index 1
        
        # State 4 is SERVICE_RUNNING
        is_running = (state == 4)
        
        if log:
            log.debug("Service %s state: %s (running: %s)", service_name, state, is_running)
            
        return is_running, state, None
        
    except ImportError as e:
        error_msg = "pywin32 not available: {}".format(str(e))
        if log:
            log.error(error_msg)
        return False, None, error_msg
        
    except Exception as e:
        error_msg = "Failed to check service {}: {}".format(service_name, str(e))
        if log:
            log.debug(error_msg)
        return False, None, error_msg