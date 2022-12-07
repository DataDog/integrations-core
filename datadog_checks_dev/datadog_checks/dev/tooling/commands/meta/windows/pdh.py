# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import textwrap
from collections import defaultdict

import click

from ...console import CONTEXT_SETTINGS, echo_info

# https://docs.microsoft.com/en-us/windows/win32/wmisdk/wmi-performance-counter-types
# https://docs.microsoft.com/en-us/dotnet/api/system.diagnostics.performancecountertype
COUNTER_TYPES = {
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc776459(v=ws.10)
    0: ('PERF_COUNTER_RAWCOUNT_HEX', 'NumberOfItemsHEX32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc776544(v=ws.10)
    256: ('PERF_COUNTER_LARGE_RAWCOUNT_HEX', 'NumberOfItemsHEX64'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc780161(v=ws.10)
    2816: ('PERF_COUNTER_TEXT', ''),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc757032(v=ws.10)
    65536: ('PERF_COUNTER_RAWCOUNT', 'NumberOfItems32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc780300(v=ws.10)
    65792: ('PERF_COUNTER_LARGE_RAWCOUNT', 'NumberOfItems64'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc778579(v=ws.10)
    4195328: ('PERF_COUNTER_DELTA', 'CounterDelta32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc758091(v=ws.10)
    4195584: ('PERF_COUNTER_LARGE_DELTA', 'CounterDelta64'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc740231(v=ws.10)
    4260864: ('PERF_SAMPLE_COUNTER', 'SampleCounter'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc736359(v=ws.10)
    4523008: ('PERF_COUNTER_QUEUELEN_TYPE', 'CountPerTimeInterval32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc776041(v=ws.10)
    4523264: ('PERF_COUNTER_LARGE_QUEUELEN_TYPE', 'CountPerTimeInterval64'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc781696(v=ws.10)
    5571840: ('PERF_COUNTER_100NS_QUEUELEN_TYPE', ''),
    # ???
    6620416: ('PERF_COUNTER_OBJ_TIME_QUEUELEN_TYPE', ''),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc740048(v=ws.10)
    272696320: ('PERF_COUNTER_COUNTER', 'RateOfCountsPerSecond32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc757486(v=ws.10)
    272696576: ('PERF_COUNTER_BULK_COUNT', 'RateOfCountsPerSecond64'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc779364(v=ws.10)
    537003008: ('PERF_RAW_FRACTION', 'RawFraction'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc781623(v=ws.10)
    541132032: ('PERF_COUNTER_TIMER', 'CounterTimer'),
    # ???
    541525248: ('PERF_PRECISION_SYSTEM_TIMER', ''),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc728274(v=ws.10)
    542180608: ('PERF_100NSEC_TIMER', 'Timer100Ns'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc756128(v=ws.10)
    542573824: ('PERF_PRECISION_100NS_TIMER', ''),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc758837(v=ws.10)
    543229184: ('PERF_OBJ_TIME_TIMER', ''),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc783987(v=ws.10)
    549585920: ('PERF_SAMPLE_FRACTION', 'SampleFraction'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc728053(v=ws.10)
    557909248: ('PERF_COUNTER_TIMER_INV', 'CounterTimerInverse'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc757283(v=ws.10)
    558957824: ('PERF_100NSEC_TIMER_INV', 'Timer100NsInverse'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc736593(v=ws.10)
    574686464: ('PERF_COUNTER_MULTI_TIMER', 'CounterMultiTimer'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc780074(v=ws.10)
    575735040: ('PERF_100NSEC_MULTI_TIMER', 'CounterMultiTimer100Ns'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc756801(v=ws.10)
    591463680: ('PERF_COUNTER_MULTI_TIMER_INV', 'CounterMultiTimerInverse'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc779374(v=ws.10)
    592512256: ('PERF_100NSEC_MULTI_TIMER_INV', 'CounterMultiTimer100NsInverse'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc783087(v=ws.10)
    805438464: ('PERF_AVERAGE_TIMER', 'AverageTimer32'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc756820(v=ws.10)
    807666944: ('PERF_ELAPSED_TIME', 'ElapsedTime'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc782574(v=ws.10)
    1073874176: ('PERF_AVERAGE_BULK', 'AverageCount64'),
    # ???
    1073939457: ('PERF_SAMPLE_BASE', 'SampleBase'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc739892(v=ws.10)
    1073939458: ('PERF_AVERAGE_BASE', 'AverageBase'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc758504(v=ws.10)
    1073939459: ('PERF_RAW_BASE', 'RawBase'),
    # https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc739322(v=ws.10)
    1073939712: ('PERF_LARGE_RAW_BASE', ''),
    # ???
    1107494144: ('PERF_COUNTER_MULTI_BASE', 'CounterMultiBase'),
}


@click.group(context_settings=CONTEXT_SETTINGS, short_help='PDH utilities')
def pdh():
    pass


@pdh.command(context_settings=CONTEXT_SETTINGS, short_help='Explore performance counters')
@click.argument('counterset', required=False)
def browse(counterset):
    """
    Explore performance counters.

    You'll need to install pywin32 manually beforehand.
    """
    # Leave imports in function to not add the dependencies
    import win32pdh

    if not counterset:
        echo_info('Searching for available countersets:')
        countersets = sorted(win32pdh.EnumObjects(None, None, win32pdh.PERF_DETAIL_WIZARD, True))
        for name in countersets:
            echo_info(name)

        return

    description_prefix = '    Description: '
    description_indent = ' ' * len(description_prefix)

    def display_counter(handle):
        counter_info = win32pdh.GetCounterInfo(handle, True)
        counter_description = counter_info[-1]

        counter_type = counter_info[0]
        if counter_type in COUNTER_TYPES:
            counter_type_name = COUNTER_TYPES[counter_type][0]
        else:
            counter_type_name = 'unknown'

        echo_info(f'--> {counter}')
        echo_info(f'    Type: {counter_type_name}')
        echo_info(description_prefix, nl=False)
        echo_info(textwrap.indent(textwrap.fill(counter_description), description_indent).lstrip())

    query_handle = win32pdh.OpenQuery()

    try:
        header = f'<<< {counterset} >>>'
        echo_info(header)
        echo_info('-' * len(header))
        echo_info('')
        counters, instances = win32pdh.EnumObjectItems(None, None, counterset, win32pdh.PERF_DETAIL_WIZARD)
        counters.sort()

        if instances:
            header = 'Instances'
            echo_info(header)
            echo_info('=' * len(header))
            instance_index = defaultdict(int)
            for instance in instances:
                instance_index[instance] += 1
                echo_info(instance)
            echo_info('')

            header = 'Counters'
            echo_info(header)
            echo_info('=' * len(header))

            for counter in counters:
                for instance, num_instances in instance_index.items():
                    for index in range(num_instances):
                        path = win32pdh.MakeCounterPath((None, counterset, instance, None, index, counter))
                        counter_handle = win32pdh.AddCounter(query_handle, path)
                        display_counter(counter_handle)

                        # Only need information from one instance
                        break
                    break
        else:
            header = 'Counters'
            echo_info(header)
            echo_info('=' * len(header))

            for counter in counters:
                path = win32pdh.MakeCounterPath((None, counterset, None, None, 0, counter))
                if win32pdh.ValidatePath(path) != 0:
                    echo_info(f'--> {counter}')
                    echo_info('    Error: no current instances')
                    continue

                counter_handle = win32pdh.AddCounter(query_handle, path)
                display_counter(counter_handle)
    finally:
        win32pdh.CloseQuery(query_handle)
