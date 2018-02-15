# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import kube_proxy

KubeProxyCheck = kube_proxy.KubeProxyCheck

__version__ = "1.0.0"

__all__ = ['kube_proxy']
