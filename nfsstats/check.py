# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib

# 3rd party

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'nfsstats'


class NfsstatsCheck(AgentCheck):

    def check(self, instance):
        pass
