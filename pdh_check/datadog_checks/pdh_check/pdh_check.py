# (C) Datadog, Inc. 2013-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.checks.win import PDHBaseCheck


class PDHCheck(PDHBaseCheck):
    """
    PDH check.

    Windows only.
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        counter_list = []
        for instance in instances:
            counterset = instance['countersetname']

            counter_list.extend(
                (counterset, None, inst_name, dd_name, mtype) for inst_name, dd_name, mtype in instance['metrics']
            )

        PDHBaseCheck.__init__(self, name, init_config, agentConfig, instances, counter_list)
