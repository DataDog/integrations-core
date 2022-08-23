# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datadog_checks.base import AgentCheck


class TddCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tdd'

    def __init__(self, name, init_config, instances):
        super(TddCheck, self).__init__(name, init_config, instances)
        options = {
            'host': self.instance.get('hosts', 'localhost:27017'),
            'serverSelectionTimeoutMS': self.instance.get('timeout', 5) * 1000,
        }
        self._mongo_client = MongoClient(**options)

    def check(self, _):
        try:
            # The ping command is cheap and does not require auth.
            self._mongo_client['admin'].command('ping')
            self.log.debug('Connected')
            self.service_check("can_connect", AgentCheck.OK)
        except (ConnectionFailure, Exception) as e:
            self.log.error('Exception: %s', e)
            self.service_check("can_connect", AgentCheck.CRITICAL)
