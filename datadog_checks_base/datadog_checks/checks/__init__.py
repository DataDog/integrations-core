# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from checks import AgentCheck, NetworkCheck
except ImportError:
    from .base import AgentCheck
    from .network import NetworkCheck

__all__ = [
    'AgentCheck',
    'NetworkCheck',
]
