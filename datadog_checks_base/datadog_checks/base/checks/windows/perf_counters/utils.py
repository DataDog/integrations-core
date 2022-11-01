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
    # https://mhammond.github.io/pywin32/win32pdh__MakeCounterPath_meth.html
    return win32pdh.MakeCounterPath((machine_name, object_name, instance_name, None, instance_index, counter_name))


def get_counter_value(counter_handle):
    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue
    # https://mhammond.github.io/pywin32/win32pdh__GetFormattedCounterValue_meth.html
    return win32pdh.GetFormattedCounterValue(counter_handle, COUNTER_VALUE_FORMAT)[1]


def get_counter_values(counter_handle):
    # https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcounterarrayw
    # https://mhammond.github.io/pywin32/win32pdh__GetFormattedCounterValueArray_meth.html (link is broken)
    # http://timgolden.me.uk/pywin32-docs/win32pdh__GetFormattedCounterArray_meth.html
    # https://github.com/mhammond/pywin32/blob/main/win32/src/win32pdhmodule.cpp#L677

    # TBD!!! win32pdh.GetFormattedCounterArray API cannot currently handle non-unique instance name
    # (e.g. for Process object). Remove this comment after implementing Native C API call and
    # raising github issues with mhammond.
    #
    # For reference from Branden slack
    #   * ctypes.windll.pdh.PdhGetFormattedCounterArrayW()
    #   * outbuf = (ctypes.c_byte*1000)() // allocate buffer 1k
    #   * # declare the variable
    #     lpdwBufferSize = ctypes.c_uint32(0)
    #   * Pass to function with byref
    #     ctypes.byref(lpdwBufferSize)
    #   * # get the new value
    #     lpdwBufferSize.value
    #
    #     for getting the values out of the output buf in the type PDH_FMT_COUNTERVALUE_ITEM
    #     you have a few choices. You can define the structure with ctypes. I haven't done that
    #     enough to be able to point you at anything concrete. You can also use python's struct
    #     module and read the bytes yourself with struct.unpack_from

    return win32pdh.GetFormattedCounterArray(counter_handle, COUNTER_VALUE_FORMAT)
