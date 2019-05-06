# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck

# https://www.vertica.com/docs/9.2.x/HTML/Content/Resources/Images/Node_States_531x851.png
#
# UP is OK, anything on a possible path to UP is WARNING (except DOWN), otherwise CRITICAL
NODE_STATES = {
    'UP': ServiceCheck.OK,
    'DOWN': ServiceCheck.CRITICAL,
    'READY': ServiceCheck.WARNING,
    'UNSAFE': ServiceCheck.CRITICAL,
    'SHUTDOWN': ServiceCheck.CRITICAL,
    'SHUTDOWN ERROR': ServiceCheck.CRITICAL,
    'RECOVERING': ServiceCheck.WARNING,
    'RECOVERY ERROR': ServiceCheck.CRITICAL,
    'RECOVERED': ServiceCheck.WARNING,
    'INITIALIZING': ServiceCheck.WARNING,
    'STAND BY': ServiceCheck.WARNING,
    'NEEDS CATCH UP': ServiceCheck.WARNING,
}


def node_state_to_service_check(node_state):
    return NODE_STATES.get(node_state, ServiceCheck.UNKNOWN)
