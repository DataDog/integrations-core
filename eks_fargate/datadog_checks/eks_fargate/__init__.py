# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .eks_fargate import EksFargateCheck

__all__ = ['__version__', 'EksFargateCheck']
