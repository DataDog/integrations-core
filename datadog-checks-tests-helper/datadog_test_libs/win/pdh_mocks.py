# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import re
import string
import _winreg
from collections import defaultdict

HERE = os.path.abspath(os.path.dirname(__file__))

counters_by_class = defaultdict(set)
instances_by_class = defaultdict(set)
index_array = []
counters_index = defaultdict(list)


def initialize_pdh_tests(regdata = None, counterdata = None):
    """
    initialize_pdh_tests

    Reads in the registry data (for mapping english counters to
    non-english) and available counters from the specified
    fixtures, or the default included data if not specified.

    Data from those files is used by any subsequent mocked call.

    Can be re-initialized with new values if desired

    Parameters:
    regdata     Filename of fixture that contains the registry
                data.  If not specified, the provided data is
                used.

    counterdata Filename which contains the available installed
                counters

    """
    if regdata is None:
        regdata = os.path.join(HERE, 'fixtures', 'counter_indexes_en.txt')
    if counterdata is None:
        counterdata = os.path.join(HERE, 'fixtures', 'allcounters.txt')

    load_registry_values(regdata)
    read_available_counters(counterdata)

def read_available_counters(fname):
    counters_by_class.clear()
    instances_by_class.clear()
    regex = r'(\\[^(]+)(?:\(([^)]+)\))?(\\[^(]+)'
    compiled_regex = re.compile(regex)

    with open(fname) as f:
        for line in f:
            line = line.rstrip()
            clss, inst, counter = [x if not x else x.lstrip('\\') for x in compiled_regex.search(line).groups()]
            counters_by_class[clss].add(counter)
            if inst:
                instances_by_class[clss].add(inst)


def load_registry_values(fname):
    global index_array
    index_array = []
    counters_index.clear()

    with open(fname) as f:
        linecount = 0
        for line in f:
            line = string.strip(line)
            if not line or len(line) == 0:
                if linecount % 2 == 0:
                    break
                line = " "

            index_array.append(line)
            linecount += 1

    idx = 0
    idx_max = len(index_array)
    while idx < idx_max:
        counters_index[int(index_array[idx])] = index_array[idx+1]
        idx += 2

def mock_EnumObjectItems(reserved, machine_name, clss, detail):
    ctrs = list(counters_by_class[clss])
    insts = list(instances_by_class[clss])
    return ctrs, insts

def mock_MakeCounterPath(machine, clss, inst, parent, iindex, cname):
    ## do some sanity checking
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
    return path

def mock_GetFormattedCounterValue(h, p):
    return 1, 0 # for now

def mock_CollectQueryData(h):
    return True


def mock_QueryValueEx(*args, **kwargs):
    return (index_array, _winreg.REG_SZ)


def mock_LookupPerfNameByIndex(machine_name, ndx):
    return counters_index[ndx]
