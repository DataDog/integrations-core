# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

EXPECTED_METRICS = [
    'systemd.units.inactive',
    'systemd.units.active'
]

EXPECTED_TAGS = [
    'unit:ssh.service',
    'unit:cron.service',
    'unit:networking.service'
]

EXPECTED_SERVICE_CHECK = 'systemd.unit.active'
