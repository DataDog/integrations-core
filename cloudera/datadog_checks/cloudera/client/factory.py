# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.cloudera.client.client import Client
from datadog_checks.cloudera.client.cm_client import CmClient


def make_client(log, type_client, **kwargs) -> Client:
    log.debug("creating client object of type '%s'", type_client)
    if type_client == 'cm_client':
        return CmClient(log, **kwargs)
    return None
