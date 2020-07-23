# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .__about__ import __version__
from .kafka_consumer import KafkaCheck

__all__ = ['__version__', 'KafkaCheck']
