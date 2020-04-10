# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# CHANGED

from datadog_checks.base.checks.win import PDHBaseCheck


class PDHCheck(PDHBaseCheck):
    """
    PDH check.

    Windows only.
    """

    def __init__(self, name, init_config, instances=None):
        counter_list = []
        for instance in instances:
            counterset = instance['countersetname']

            counter_list.extend(
                (counterset, None, inst_name, dd_name, mtype) for inst_name, dd_name, mtype in instance['metrics']
            )

        super(PDHCheck, self).__init__(name, init_config, instances, counter_list=counter_list)
