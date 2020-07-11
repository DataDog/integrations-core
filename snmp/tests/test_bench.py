# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.snmp import SnmpCheck
from .common import BULK_TABULAR_OBJECTS, TABULAR_OBJECTS, create_check, generate_instance_config

pytestmark = pytest.mark.usefixtures("dd_environment")


def test_tabular_enforce(benchmark):
    instance = generate_instance_config(TABULAR_OBJECTS)
    check = create_check(instance)

    benchmark(check.check, instance)


def test_tabular_no_enforce(benchmark):
    instance = generate_instance_config(TABULAR_OBJECTS)
    instance["enforce_mib_constraints"] = False
    check = create_check(instance)

    benchmark(check.check, instance)


def test_tabular_bulk(benchmark):
    instance = generate_instance_config(BULK_TABULAR_OBJECTS)
    instance['bulk_threshold'] = 5
    check = create_check(instance)

    benchmark(check.check, instance)


def test_tabular_no_bulk(benchmark):
    instance = generate_instance_config(BULK_TABULAR_OBJECTS)
    # Don't use bulk requests
    instance['bulk_threshold'] = 100
    check = create_check(instance)

    benchmark(check.check, instance)

instance = generate_instance_config([])
instance['community_string'] = 'f5'

check10 = SnmpCheck('snmp', {'oid_batch_size': 10}, [instance])
check32 = SnmpCheck('snmp', {'oid_batch_size': 32}, [instance])
check64 = SnmpCheck('snmp', {'oid_batch_size': 64}, [instance])
check128 = SnmpCheck('snmp', {'oid_batch_size': 128}, [instance])
check256 = SnmpCheck('snmp', {'oid_batch_size': 256}, [instance])
# check512 = SnmpCheck('snmp', {'oid_batch_size': 512}, [instance])

check10.check(None)
check32.check(None)
check64.check(None)
check128.check(None)
check256.check(None)
# check512.check(None)


def test_profile_f5_10(benchmark):
    benchmark(check10.check, instance)


def test_profile_f5_32(benchmark):
    benchmark(check32.check, instance)


def test_profile_f5_64(benchmark):
    benchmark(check64.check, instance)


def test_profile_f5_128(benchmark):
    benchmark(check128.check, instance)


def test_profile_f5_256(benchmark):
    benchmark(check256.check, instance)

# def test_profile_f5_512(benchmark):
#     benchmark(check512.check, instance)
