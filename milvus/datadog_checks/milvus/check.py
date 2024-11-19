# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class MilvusCheck(OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'milvus'

    def __init__(self, name, init_config, instances):
        super(MilvusCheck, self).__init__(name, init_config, instances)

        # Use self.instance to read the check configuration
        # self.url = self.instance.get("url")

