# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from six import iteritems
from pprint import pprint

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.marklogic.api import MarkLogicApi

RESOURCE_TYPES = {
    'cluster': {
        'plural': None,
    },
    'forest': {
        'plural': 'forests',
    },
    'database': {
        'plural': 'databases',
    },
    'host': {
        'plural': 'hosts',
    },
    'server': {
        'plural': 'servers',
    },
}
