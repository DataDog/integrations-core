# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Functions for issuing SNMP commands to an SNMP host.

A list of all SNMP commands can be found here:
http://net-snmp.sourceforge.net/tutorial/tutorial-5/commands/index.html
"""

import logging
from typing import Sequence

from pysnmp.hlapi import bulkCmd, getCmd, nextCmd

from .config import InstanceConfig
from .models import SNMPCommandResult
from .types import ObjectType
from .utils.snmp import raise_on_error_indication

# NOTE: commands that have not been wrapped around yet are exposed as-is here.
__all__ = ['bulkCmd', 'nextCmd', 'snmp_get']


def snmp_get(
    config,  # type: InstanceConfig
    oids,  # type: Sequence[ObjectType]
    enforce_constraints,  # type: bool
    log,  # type: logging.Logger
):
    # type: (...) -> SNMPCommandResult
    """
    Perform an SNMP GET command on the specified OIDs.

    GET is used to request a specific OID, such as '1.3.6.1.2.1.1.1.0'.

    See Also
    --------
    * Usage guide: http://net-snmp.sourceforge.net/tutorial/tutorial-5/commands/snmpget.html
    * PySNMP docs: http://snmplabs.com/pysnmp/docs/hlapi/asyncore/sync/manager/cmdgen/getcmd.html
    """
    log.debug('Running SNMP command GET on OIDs: %s', oids)

    options = {'lookupMib': enforce_constraints}
    results = config.call_command(getCmd, oids, **options)

    # As far as we're concerned, PySNMP returns a generator of only 1 result in the case of a GET.
    # (We can actually `.send()` a new set of OIDs into the generator, and PySNMP would issue a new
    # command to the SNMP host, but we just don't use that feature.)
    result = next(results)

    log.debug('Returned vars: %s', result.var_binds)

    raise_on_error_indication(result, config)

    return result
