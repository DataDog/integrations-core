# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .__about__ import __version__
from .istio import Istio

__all__ = ['Istio', '__version__']
