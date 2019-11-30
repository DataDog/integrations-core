# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .amazon_kafka import AmazonKafkaCheck

__all__ = ['__version__', 'AmazonKafkaCheck']
