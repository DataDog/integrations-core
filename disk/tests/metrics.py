# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CORE_GAUGES = {
    'system.disk.total': 5,
    'system.disk.used': 4,
    'system.disk.free': 1,
    'system.disk.in_use': 0.80,
    'system.disk.utilized': 80,
}
CORE_RATES = {'system.disk.write_time_pct': 9.0, 'system.disk.read_time_pct': 5.0}
CORE_COUNTS = {'system.disk.write_time': 90.0, 'system.disk.read_time': 50.0}
UNIX_GAUGES = {
    'system.fs.inodes.total': 10,
    'system.fs.inodes.used': 1,
    'system.fs.inodes.free': 9,
    'system.fs.inodes.in_use': 0.10,
    'system.fs.inodes.utilized': 10,
}
UNIX_GAUGES.update(CORE_GAUGES)
