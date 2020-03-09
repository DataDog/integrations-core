# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Re-export PySNMP exceptions that we use, so that we can access them from a single module.
"""

from pysnmp.error import PySnmpError
from pysnmp.smi.error import SmiError

__all__ = ['PySnmpError', 'SmiError']
