# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))

EXPECTED_METRICS = [
    'systemd.units.inactive',
    'systemd.units.active',
    'systemd.unit.processes'
]

EXPECTED_TAGS = [
    'unit:ssh.service',
    'unit:cron.service',
    'unit:networking.service'
]

EXPECTED_SERVICE_CHECK = 'systemd.unit.active'
