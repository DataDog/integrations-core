# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes
import ctypes.wintypes

import pytest

from datadog_checks.dev.testing import requires_windows

pytestmark = [requires_windows]


def format_counter_array(mocker, slots, data_call_result=None):
    """`slots` holds `(name, cstatus, value)` tuples; `None` leaves a slot zeroed, as if pdh.dll never wrote it.

    The data call returns `PDH_CALC_NEGATIVE_VALUE` unless `data_call_result` is given, and reports the
    item count only when it succeeds, as pdh.dll does.
    """
    from datadog_checks.base.checks.windows.perf_counters.constants import (
        COUNTER_VALUE_FORMAT,
        PDH_CALC_NEGATIVE_VALUE,
        PDH_CSTATUS_VALID_DATA,
        PDH_MORE_DATA,
    )
    from datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix import (
        PDH_FMT_COUNTERVALUE_ITEM_W,
        GetFormattedCounterArray,
    )

    names = [None if slot is None else ctypes.create_unicode_buffer(slot[0]) for slot in slots]

    def fake(handle, fmt, buf_size_ptr, item_count_ptr, item_buffer):
        buf_size = ctypes.cast(buf_size_ptr, ctypes.POINTER(ctypes.wintypes.DWORD)).contents
        item_count = ctypes.cast(item_count_ptr, ctypes.POINTER(ctypes.wintypes.DWORD)).contents
        if item_buffer is None:
            buf_size.value = ctypes.sizeof(PDH_FMT_COUNTERVALUE_ITEM_W) * len(slots)
            item_count.value = len(slots)
            return PDH_MORE_DATA

        items = (PDH_FMT_COUNTERVALUE_ITEM_W * len(slots)).from_address(ctypes.addressof(item_buffer))
        for item, name, slot in zip(items, names, slots):
            if slot is not None:
                item.szName = ctypes.addressof(name)
                item.FmtValue.CStatus = slot[1] & 0xFFFFFFFF
                item.FmtValue.value.doubleValue = slot[2]
        result = PDH_CALC_NEGATIVE_VALUE if data_call_result is None else data_call_result
        item_count.value = len(slots) if result == PDH_CSTATUS_VALID_DATA else 0
        return result

    mock_windll = mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix.ctypes.windll', create=True
    )
    mock_windll.pdh.PdhGetFormattedCounterArrayW.side_effect = fake
    return GetFormattedCounterArray(1, COUNTER_VALUE_FORMAT)


def test_get_formatted_counter_array_negative_value_last_instance(mocker):
    from datadog_checks.base.checks.windows.perf_counters.constants import (
        PDH_CSTATUS_INVALID_DATA,
        PDH_CSTATUS_VALID_DATA,
    )
    from datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix import PartialCounterValues

    slots = [
        ('bad_share', PDH_CSTATUS_INVALID_DATA, 0.0),
        ('healthy_share', PDH_CSTATUS_VALID_DATA, 42.5),
        ('_Total', PDH_CSTATUS_INVALID_DATA, 0.0),
    ]
    result = format_counter_array(mocker, slots)
    assert result == {'healthy_share': 42.5}
    assert isinstance(result, PartialCounterValues)
    assert result.invalid_instances == ['bad_share', '_Total']


def test_get_formatted_counter_array_valid_data_returns_plain_dict(mocker):
    from datadog_checks.base.checks.windows.perf_counters.constants import (
        PDH_CSTATUS_INVALID_DATA,
        PDH_CSTATUS_VALID_DATA,
    )
    from datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix import PartialCounterValues

    slots = [
        ('bad_share', PDH_CSTATUS_INVALID_DATA, 0.0),
        ('healthy_share', PDH_CSTATUS_VALID_DATA, 42.5),
    ]
    result = format_counter_array(mocker, slots, data_call_result=PDH_CSTATUS_VALID_DATA)
    assert result == {'healthy_share': 42.5}
    assert not isinstance(result, PartialCounterValues)


def test_get_formatted_counter_array_all_instances_invalid(mocker):
    from datadog_checks.base.checks.windows.perf_counters.constants import PDH_CSTATUS_INVALID_DATA

    assert format_counter_array(mocker, [('bad_share', PDH_CSTATUS_INVALID_DATA, 0.0)]) == {}


def test_get_formatted_counter_array_null_szname_skipped(mocker):
    from datadog_checks.base.checks.windows.perf_counters.constants import PDH_CSTATUS_VALID_DATA

    result = format_counter_array(mocker, [('healthy_share', PDH_CSTATUS_VALID_DATA, 12.0), None])
    assert result == {'healthy_share': 12.0}
    assert result.invalid_instances == []


def test_get_formatted_counter_array_sizing_call_error(mocker):
    import pywintypes

    from datadog_checks.base.checks.windows.perf_counters.constants import COUNTER_VALUE_FORMAT, PDH_NO_DATA
    from datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix import GetFormattedCounterArray

    mock_windll = mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix.ctypes.windll', create=True
    )
    mock_windll.pdh.PdhGetFormattedCounterArrayW.return_value = PDH_NO_DATA

    with pytest.raises(pywintypes.error) as exc_info:
        GetFormattedCounterArray(1, COUNTER_VALUE_FORMAT)

    assert exc_info.value.winerror == PDH_NO_DATA
    assert exc_info.value.strerror == 'Failed to get the buffer size for counters values.'


def test_get_formatted_counter_array_data_call_error(mocker):
    import pywintypes

    from datadog_checks.base.checks.windows.perf_counters.constants import PDH_CSTATUS_VALID_DATA, PDH_NO_DATA

    with pytest.raises(pywintypes.error) as exc_info:
        format_counter_array(mocker, [('healthy_share', PDH_CSTATUS_VALID_DATA, 1.0)], data_call_result=PDH_NO_DATA)

    assert exc_info.value.winerror == PDH_NO_DATA
    assert exc_info.value.strerror == 'Failed to retrieve counters values.'


def test_get_counter_values_duplicate_instances_false_falls_back_on_negative_value(mocker):
    import pywintypes

    from datadog_checks.base.checks.windows.perf_counters.constants import (
        COUNTER_VALUE_FORMAT,
        PDH_CALC_NEGATIVE_VALUE,
    )
    from datadog_checks.base.checks.windows.perf_counters.utils import get_counter_values

    mocker.patch(
        'win32pdh.GetFormattedCounterArray',
        side_effect=pywintypes.error(PDH_CALC_NEGATIVE_VALUE, 'PdhGetFormattedCounterArray', 'Negative value'),
    )
    mock_fallback = mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.utils.GetFormattedCounterArray',
        return_value={'healthy_share': 99.0},
    )

    result = get_counter_values(1, duplicate_instances_exist=False)
    assert result == {'healthy_share': 99.0}
    mock_fallback.assert_called_once_with(1, COUNTER_VALUE_FORMAT)


def test_get_counter_values_duplicate_instances_false_reraises_non_negative_error(mocker):
    import pywintypes

    from datadog_checks.base.checks.windows.perf_counters.constants import PDH_INVALID_DATA
    from datadog_checks.base.checks.windows.perf_counters.utils import get_counter_values

    mocker.patch(
        'win32pdh.GetFormattedCounterArray',
        side_effect=pywintypes.error(PDH_INVALID_DATA, 'PdhGetFormattedCounterArray', 'Invalid data'),
    )
    mock_fallback = mocker.patch('datadog_checks.base.checks.windows.perf_counters.utils.GetFormattedCounterArray')

    with pytest.raises(pywintypes.error) as exc_info:
        get_counter_values(1, duplicate_instances_exist=False)

    assert exc_info.value.winerror == PDH_INVALID_DATA
    mock_fallback.assert_not_called()
