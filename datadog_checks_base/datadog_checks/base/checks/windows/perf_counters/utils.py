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

    # Currently when duplicates are no concern, calla  win32pdh.GetFormattedCounterArray()
    # function is 5-10x slower faster than pure python wrapper over Windows PdhGetFormattedCounterArray()
    # API call. See detailed comment for 'only_unique_instances' configuration
    if not duplicate_instances_exist:
        # This function cannot handle duplicate/non-unique instances (e.g. for "Process" counters)
        # See its implementation at
        #     https://github.com/mhammond/pywin32/blob/main/win32/src/win32pdhmodule.cpp#L677
        return win32pdh.GetFormattedCounterArray(counter_handle, COUNTER_VALUE_FORMAT)

    # utils_win32pdh_fix.GetFormattedCounterArray
    return GetFormattedCounterArray(counter_handle, COUNTER_VALUE_FORMAT)


# Validate path function is using PdhValidatePath if the path is already localized
# If not, it will convert English counter name into its localized version via
# intermediate calls to PdhAddEnglishCounter() and PdhGetCounterInfo()
# If specified object and counter is using localized name then a user should configure
# the check using `use_localized_counters` set to true. It is incorrect to use
# PdhAddEnglishCounter() or PdhAddCounter() for path validation because these
# are not validating functions and many invalid path will not be validated until
# corresponding data is queried.
#
def validate_path(query_handle, use_localized_counters, path):
    try:
        # If localized name is already used we can directly validate it
        if use_localized_counters:
            return True if win32pdh.ValidatePath(path) == 0 else False

        # ... otherwise we need to localize English object/counter names
        counter_handle = win32pdh.AddEnglishCounter(query_handle, path)
        if counter_handle is not None:
            try:
                # https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetcounterinfoa
                # https://mhammond.github.io/pywin32/win32pdh__GetCounterInfo_meth.html
                # win32pdh.GetCounterInfo() return tuples forming listr of PDH_COUNTER_INFO fields
                #    https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_counter_info_a
                counter_info = win32pdh.GetCounterInfo(counter_handle, False)
                localized_path = counter_info[6]
                return True if win32pdh.ValidatePath(localized_path) == 0 else False

            except Exception:
                pass
            finally:
                # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
                # https://mhammond.github.io/pywin32/win32pdh__RemoveCounter_meth.html
                win32pdh.RemoveCounter(counter_handle)

    except Exception:
        pass

    return False
