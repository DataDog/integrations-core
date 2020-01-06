# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .. import AgentCheck
from .mixins import KubeLeaderElectionMixin


class KubeLeaderElectionBaseCheck(KubeLeaderElectionMixin, AgentCheck):
    """
    KubeLeaderElectioBaseCheck is a class that helps instantiating a Kube Leader
    Election mixin only with YAML configurations.
    Example configuration::

        instances:
        - namespace (prefix for the metrics and check)
          record_kind (endpoints or configmap)
          record_name
          record_namespace
          tags (optional)
    """

    def check(self, instance):
        self.check_election_status(instance)
