# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32pdh

from .constants import COUNTER_VALUE_FORMAT


def format_instance(instance, index):
    return instance if index == 0 else f'{instance}#{index}'


def construct_counter_path(*, machine_name, object_name, counter_name, instance_name=None, instance_index=0):
    # More info: https://docs.microsoft.com/en-us/windows/win32/perfctrs/specifying-a-counter-path
    #
    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhmakecounterpatha
    # http://timgolden.me.uk/pywin32-docs/win32pdh__MakeCounterPath_meth.html
    return win32pdh.MakeCounterPath((machine_name, object_name, instance_name, None, instance_index, counter_name))


def get_counter_value(counter_handle):
    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue
    # http://timgolden.me.uk/pywin32-docs/win32pdh__GetFormattedCounterValue_meth.html
    return win32pdh.GetFormattedCounterValue(counter_handle, COUNTER_VALUE_FORMAT)[1]
