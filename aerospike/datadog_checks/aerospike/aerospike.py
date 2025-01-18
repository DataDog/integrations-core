# (C) Datadog, Inc. 2019-present
# (C) 2018 Aerospike, Inc.
# (C) 2017 Red Sift
# (C) 2015 Pippio, Inc. All rights reserved.
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from datadog_checks.base import AgentCheck

# Local Imports
from .check import AerospikeCheckV2


class AerospikeCheck(AgentCheck):
    """
    We will support only openmetrics based implementation,
    as aerospike-prometheus-exporter is capable of taking to different server versions and make server calls seamlessly.
    and expose metrics in openmetrics format.
    """

    def __new__(cls, name, init_config, instances):
        return AerospikeCheckV2(name, init_config, instances)
