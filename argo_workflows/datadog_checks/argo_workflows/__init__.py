# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import ArgoWorkflowsCheck

__all__ = ['__version__', 'ArgoWorkflowsCheck']
