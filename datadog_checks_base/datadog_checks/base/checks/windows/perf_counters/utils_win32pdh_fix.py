# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import ctypes

import pywintypes
import win32pdh

from .constants import PDH_CSTATUS_INVALID_DATA, PDH_CSTATUS_NEW_DATA, PDH_CSTATUS_VALID_DATA, PDH_MORE_DATA

#  If the PERF_TYPE_COUNTER value was selected then select one of the
#  following to indicate the type of counter


# typedef struct _PDH_FMT_COUNTERVALUE {
#     DWORD    CStatus;
#     union {
#         LONG        longValue;
#         double      doubleValue;
#         LONGLONG    largeValue;
#         LPCSTR      AnsiStringValue;
#         LPCWSTR     WideStringValue;
#     };
# } PDH_FMT_COUNTERVALUE, * PPDH_FMT_COUNTERVALUE;
class PDH_COUNTERVALUE(ctypes.Union):
    _fields_ = [
        ('longValue', ctypes.c_long),
        ('doubleValue', ctypes.c_double),
        ('largeValue', ctypes.c_longlong),
        ('AnsiStringValue', ctypes.wintypes.LPCSTR),
        ('WideStringValue', ctypes.wintypes.LPCWSTR),
    ]


class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [
        ('CStatus', ctypes.wintypes.DWORD),
        ('value', PDH_COUNTERVALUE),
    ]


# typedef struct _PDH_FMT_COUNTERVALUE_ITEM_W {
#     LPWSTR                  szName;
#     PDH_FMT_COUNTERVALUE    FmtValue;
# } PDH_FMT_COUNTERVALUE_ITEM_W, * PPDH_FMT_COUNTERVALUE_ITEM_W;
class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
    _fields_ = [
        ('szName', ctypes.wintypes.LPCWSTR),
        ('FmtValue', PDH_FMT_COUNTERVALUE),
    ]


# This function is a temporary work around of inability of win32pdh.GetFormattedCounterArray()
# retrieve non-unique instances since win32pdh.GetFormattedCounterArray() is using a simple
# dictionary of name to values. See for details
#        https://github.com/mhammond/pywin32/blob/main/win32/src/win32pdhmodule.cpp#L677
# This function is 4-10x slower than CPython's native implementation - the reason is
# significantly less efficient facilities to parse compact layout of PDH Item Array.
# On the other hand a contribution to overall performance overhead from  this or other PDH
# function calls are very small - around 1% or less.
#
def GetFormattedCounterArray(counter_handle, format):
    # Define PdhGetFormattedCounterArrayW prototype
    # https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcounterarrayw
    PdhGetFormattedCounterArrayW_fn = ctypes.windll.pdh.PdhGetFormattedCounterArrayW
    PdhGetFormattedCounterArrayW_fn.argtypes = [
        ctypes.wintypes.HANDLE,  # [in] PDH_HCOUNTER hCounter,
        ctypes.wintypes.DWORD,  # [in] DWORD dwFormat,
        ctypes.POINTER(ctypes.wintypes.DWORD),  # [in, out] LPDWORD lpdwBufferSize,
        ctypes.POINTER(ctypes.wintypes.DWORD),  # [out] LPDWORD lpdwItemCount,
        ctypes.wintypes.LPVOID,  # [out] PPDH_FMT_COUNTERVALUE_ITEM_W ItemBuffer
    ]

    # Get required buffer size
    buffer_size = ctypes.wintypes.DWORD(0)
    item_count = ctypes.wintypes.DWORD(0)
    handle = ctypes.wintypes.HANDLE(counter_handle)
    result = PdhGetFormattedCounterArrayW_fn(handle, format, ctypes.byref(buffer_size), ctypes.byref(item_count), None)
    if result != PDH_MORE_DATA:
        # To simulate real win32/win32pdh error/exception - no need to convert error to its real string for this
        # temporary function like it is done in
        #      https://github.com/mhammond/pywin32/blob/main/win32/src/PyWinTypesmodule.cpp#L278
        raise pywintypes.error(result, 'PdhGetFormattedCounterArray', 'Failed to retrieve counters values.')

    # Then get items for real
    items_buffer = (ctypes.c_byte * buffer_size.value)()
    result = PdhGetFormattedCounterArrayW_fn(
        handle, format, ctypes.byref(buffer_size), ctypes.byref(item_count), items_buffer
    )
    if result == PDH_CSTATUS_INVALID_DATA:
        raise pywintypes.error(result, 'PdhGetFormattedCounterArray', 'The returned data is not valid.')
    if result != PDH_CSTATUS_VALID_DATA:
        raise pywintypes.error(result, 'PdhGetFormattedCounterArray', 'Failed to retrieve counters values.')

    # Instance values is a dictionary with instance name as a key and value could be a single
    # atomic value or list of them for non-unique instances
    instance_values = {}

    previous_instance_name = ""
    previous_instance_value = None
    instance_count = 0

    # Loop over all collected instances
    if result == 0 and item_count.value > 0:
        for idx in range(item_count.value):
            # Get offset in buffer for item at index idx
            offset = idx * ctypes.sizeof(PDH_FMT_COUNTERVALUE_ITEM_W)

            # Cast byte buffer to item
            item_ptr = ctypes.byref(items_buffer, offset)
            item = ctypes.cast(item_ptr, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W))

            # Typically errored instances are not reported but Microsoft docs implies a stricter validation
            instance_status = item.contents.FmtValue.CStatus
            if instance_status != PDH_CSTATUS_VALID_DATA and instance_status != PDH_CSTATUS_NEW_DATA:
                continue

            # Get instance value pair
            if format & win32pdh.PDH_FMT_DOUBLE:
                # Check this format first since it is hardcoded format (see COUNTER_VALUE_FORMAT)
                instance_value = item.contents.FmtValue.value.doubleValue
            elif format & win32pdh.PDH_FMT_LONG:
                instance_value = item.contents.FmtValue.value.longValue
            elif format & win32pdh.PDH_FMT_LARGE:
                instance_value = item.contents.FmtValue.value.largeValue
            else:
                raise pywintypes.error(-1, 'GetFormattedCounterArray', 'Not supported value of format is specified.')

            # Get instance name
            instance_name = item.contents.szName

            # For performance and to support non-unique instance names do not immedeatly store valuethem
            # in the instance_values but accumulate them over few iterations. Order of instances is
            # sequential
            if len(previous_instance_name) == 0:
                # Very first iteration
                previous_instance_name = instance_name
                previous_instance_value = instance_value
                instance_count = 1
            elif instance_name == previous_instance_name:
                # Second or more instances
                if instance_count == 1:
                    previous_instance_value = [previous_instance_value, instance_value]
                else:
                    previous_instance_value.append(instance_value)

                instance_count += 1
            else:
                # A different instance name cameup - flush previous value(s) to the dictionary
                instance_values[previous_instance_name] = previous_instance_value
                previous_instance_name = instance_name
                previous_instance_value = instance_value
                instance_count = 1

        # Flush last value(s) to the dictionary
        instance_values[previous_instance_name] = previous_instance_value

    return instance_values
