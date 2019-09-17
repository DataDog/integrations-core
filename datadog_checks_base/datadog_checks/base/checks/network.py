# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import AgentCheck


class Status:
    DOWN = "DOWN"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UP = "UP"


STATUS_TO_SERVICE_CHECK = {
        Status.UP: AgentCheck.OK,
        Status.WARNING: AgentCheck.WARNING,
        Status.CRITICAL: AgentCheck.CRITICAL,
        Status.DOWN: AgentCheck.CRITICAL,
    }
