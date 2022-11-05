# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32pdh

from .constants import COUNTER_VALUE_FORMAT
from .utils_win32pdh_fix import GetFormattedCounterArray


def format_instance(instance, index):
    return instance if index == 0 else f'{instance}#{index}'


def construct_counter_path(*, machine_name, object_name, counter_name, instance_name=None, instance_index=0):
    # More info: https://docs.microsoft.com/en-us/windows/win32/perfctrs/specifying-a-counter-path
    #
    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhmakecounterpatha
    # https://mhammond.github.io/pywin32/win32pdh__MakeCounterPath_meth.html
    return win32pdh.MakeCounterPath((machine_name, object_name, instance_name, None, instance_index, counter_name))


def get_counter_value(counter_handle):
    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue
    # https://mhammond.github.io/pywin32/win32pdh__GetFormattedCounterValue_meth.html
    return win32pdh.GetFormattedCounterValue(counter_handle, COUNTER_VALUE_FORMAT)[1]


def get_counter_values(counter_handle, duplicate_instances_exist):
    # https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcounterarrayw
    # https://mhammond.github.io/pywin32/win32pdh__GetFormattedCounterValueArray_meth.html (link is broken)
    # http://timgolden.me.uk/pywin32-docs/win32pdh__GetFormattedCounterArray_meth.html
    # https://github.com/mhammond/pywin32/blob/main/win32/src/win32pdhmodule.cpp#L677

    # Currently when duplicates are no concern call win32pdh.GetFormattedCounterArray()
    # function is 5-10x slower then its alternative. See detailed comment for
    # 'only_unique_instances' configuration
    if not duplicate_instances_exist:
        # This function cannot handle duplicate/non-unique instances (e.g. for "Process" counters)
        # See its implementation at
        #     https://github.com/mhammond/pywin32/blob/main/win32/src/win32pdhmodule.cpp#L677
        return win32pdh.GetFormattedCounterArray(counter_handle, COUNTER_VALUE_FORMAT)

    # utils_win32pdh_fix.GetFormattedCounterArray
    return GetFormattedCounterArray(counter_handle, COUNTER_VALUE_FORMAT)
