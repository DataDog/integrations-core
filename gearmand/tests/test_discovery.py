# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery import Port, Service

pytestmark = pytest.mark.unit


def test_discovery_preserves_raw_ipv6_server() -> None:
    pytest.importorskip('python3_gearman')  # not installed on Windows
    from datadog_checks.gearmand import Gearman

    service = Service(id='gearmand', host='fd00::1', ports=(Port(number=4730),))

    config = next(iter(Gearman.generate_configs(service)))

    assert config['instances'][0]['server'] == 'fd00::1'
