# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
DATA_TYPE_INT = 0
DATA_TYPE_DOUBLE = 1


class WinPDHCounter(object):
    def is_single_instance(self):
        return False

    def get_single_value(self):
        return None

    def get_all_values(self):
        return {}

    def _get_counter_dictionary(self):
        return
