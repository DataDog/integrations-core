# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import defaultdict

import mock
import pytest

from six import PY3
from six.moves import winreg

HERE = os.path.abspath(os.path.dirname(__file__))

counters_by_class = defaultdict(set)
instances_by_class = defaultdict(set)
index_array = []
counters_index = defaultdict(list)


@pytest.fixture
def pdh_mocks_fixture():
    if PY3:
        regqueryvalueex = mock.patch('winreg.QueryValueEx', mock_QueryValueEx)
    else:
        regqueryvalueex = mock.patch('_winreg.QueryValueEx', mock_QueryValueEx)

    pdhlookupbyindex = mock.patch('win32pdh.LookupPerfNameByIndex', mock_LookupPerfNameByIndex)
    pdhenumobjectitems = mock.patch('win32pdh.EnumObjectItems', mock_EnumObjectItems)
    pdhmakecounterpath = mock.patch('win32pdh.MakeCounterPath', mock_MakeCounterPath)
    pdhaddcounter = mock.patch('win32pdh.AddCounter', mock_AddCounter)
    pdhgetformattedcountervalue = mock.patch('win32pdh.GetFormattedCounterValue', mock_GetFormattedCounterValue)
    pdhcollectquerydata = mock.patch('win32pdh.CollectQueryData', mock_CollectQueryData)

    yield regqueryvalueex.start(), pdhlookupbyindex.start(), \
        pdhenumobjectitems.start(),  pdhmakecounterpath.start(), \
        pdhaddcounter.start(), pdhgetformattedcountervalue.start(), pdhcollectquerydata.start()

    regqueryvalueex.stop()
    pdhlookupbyindex.stop()
    pdhenumobjectitems.stop()
    pdhmakecounterpath.stop()
    pdhaddcounter.stop()
    pdhgetformattedcountervalue.stop()
    pdhcollectquerydata.stop()


@pytest.fixture
def pdh_mocks_fixture_bad_perf_strings():
    if PY3:
        regqueryvalueex = mock.patch('winreg.QueryValueEx', mock_QueryValueExWithRaise)
    else:
        regqueryvalueex = mock.patch('_winreg.QueryValueEx', mock_QueryValueExWithRaise)

    pdhlookupbyindex = mock.patch('win32pdh.LookupPerfNameByIndex', mock_LookupPerfNameByIndex)
    pdhenumobjectitems = mock.patch('win32pdh.EnumObjectItems', mock_EnumObjectItems)
    pdhmakecounterpath = mock.patch('win32pdh.MakeCounterPath', mock_MakeCounterPath)
    pdhaddcounter = mock.patch('win32pdh.AddCounter', mock_AddCounter)
    pdhgetformattedcountervalue = mock.patch('win32pdh.GetFormattedCounterValue', mock_GetFormattedCounterValue)
    pdhcollectquerydata = mock.patch('win32pdh.CollectQueryData', mock_CollectQueryData)

    yield regqueryvalueex.start(), pdhlookupbyindex.start(), \
        pdhenumobjectitems.start(),  pdhmakecounterpath.start(), \
        pdhaddcounter.start(), pdhgetformattedcountervalue.start(), pdhcollectquerydata.start()

    regqueryvalueex.stop()
    pdhlookupbyindex.stop()
    pdhenumobjectitems.stop()
    pdhmakecounterpath.stop()
    pdhaddcounter.stop()
    pdhgetformattedcountervalue.stop()
    pdhcollectquerydata.stop()


def initialize_pdh_tests(lang=None):
    """
    initialize_pdh_tests

    Reads in the registry data (for mapping english counters to
    non-english) and available counters from the specified
    fixtures, or the default included data if not specified.

    Data from those files is used by any subsequent mocked call.

    Can be re-initialized with new values if desired

    """
    en_us_reg_file = "counter_indexes_en-us.txt"
    if lang is None:
        local_reg_file = en_us_reg_file
        file_base = "allcounters_en-us.txt"
    else:
        local_reg_file = "counter_indexes_%s.txt" % lang
        file_base = "allcounters_%s.txt" % lang

    en_us_reg_file = os.path.join(HERE, 'fixtures', en_us_reg_file)
    local_reg_file = os.path.join(HERE, 'fixtures', local_reg_file)

    counterdata = os.path.join(HERE, 'fixtures', file_base)

    eng_array, eng_indexes = load_registry_values(en_us_reg_file)
    global index_array
    global counters_index
    index_array = eng_array
    if lang is None:
        counters_index = eng_indexes
    else:
        loc_array, loc_indexes = load_registry_values(local_reg_file)
        counters_index = loc_indexes

    read_available_counters(counterdata)


def read_available_counters(fname):
    counters_by_class.clear()
    instances_by_class.clear()

    with open(fname) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue

            try:
                clss, inst, counter = line.split('!')
                clss = clss.strip()
                inst = inst.strip()
                counter = counter.strip()
            except ValueError:
                print(line)
                raise

            counters_by_class[clss].add(counter)
            if inst:
                instances_by_class[clss].add(inst)


def load_registry_values(fname):
    idx_array = []
    ctr_index = defaultdict(list)

    with open(fname) as f:
        linecount = 0
        for line in f:
            line = line.strip()
            if not line or len(line) == 0:
                if linecount % 2 == 0:
                    break
                line = " "

            idx_array.append(line)
            linecount += 1

    idx = 0
    idx_max = len(idx_array)
    while idx < idx_max:
        ctr_index[int(idx_array[idx])] = idx_array[idx+1]
        idx += 2
    return idx_array, ctr_index


def mock_EnumObjectItems(reserved, machine_name, clss, detail):
    ctrs = list(counters_by_class[clss])
    insts = list(instances_by_class[clss])
    return ctrs, insts


def mock_MakeCounterPath(arglist):
    # win32pdh.MakeCounterPath takes as it's first argument a list of parameters
    # to pass to the underlying C API.  Providing the unused parameters (commented
    # out) as "documentation" for the params; especially in the event they're
    # needed in future improvements

    # machine = arglist[0] # remote machine name
    clss = arglist[1]
    inst = arglist[2]
    # parent = arglist[3]
    # iindex = arglist[4]
    cname = arglist[5]
    # do some sanity checking
    if clss not in counters_by_class:
        raise AttributeError("class name {} is invalid".format(clss))
    if inst and inst not in instances_by_class[clss]:
        raise AttributeError("instance name {} is invalid".format(inst))
    if cname not in counters_by_class[clss]:
        raise AttributeError("class name {} is invalid".format(cname))

    if inst:
        p = "%s|%s|%s" % (clss, inst, cname)
    else:
        p = "%s| |%s" % (clss, cname)
    return p


def mock_AddCounter(h, path):
    if path is None or len(path) == 0:
        raise AttributeError("Invalid path")
    return path


def mock_GetFormattedCounterValue(h, p):
    return 1, 1  # for now


def mock_CollectQueryData(h):
    return True


def mock_LookupPerfNameByIndex(machine_name, ndx):
    return counters_index[ndx]


def mock_QueryValueEx(*args, **kwargs):
    return (index_array, winreg.REG_SZ)


def mock_QueryValueExWithRaise(*args, **kwargs):
    raise WindowsError
