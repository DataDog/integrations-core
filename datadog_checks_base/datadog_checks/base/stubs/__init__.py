# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .aggregator import aggregator
from .tagging import tagger

__all__ = ['aggregator', 'datadog_agent', 'tagger']
