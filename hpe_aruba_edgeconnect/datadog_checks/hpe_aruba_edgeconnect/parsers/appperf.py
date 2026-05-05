# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from datadog_checks.hpe_aruba_edgeconnect.constants import (
    APPPERF_COL_APP_DELAY,
    APPPERF_COL_APP_NAME,
    APPPERF_COL_CND_DELAY,
    APPPERF_COL_SND_DELAY,
    APPPERF_COL_TRANSPORT_TYPE,
    APPPERF_COL_TUNNEL_NAME,
)
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore


@dataclass(init=False, slots=True)
class AppperfStats:
    app_name: str
    tunnel_name: str | None
    transport_type: str | None
    cnd_delay: float | None
    snd_delay: float | None
    app_delay: float | None

    def __init__(self, cols: list[str]) -> None:
        self.app_name = cols[APPPERF_COL_APP_NAME]
        self.tunnel_name = cols[APPPERF_COL_TUNNEL_NAME] if len(cols) > APPPERF_COL_TUNNEL_NAME else None
        self.transport_type = cols[APPPERF_COL_TRANSPORT_TYPE] if len(cols) > APPPERF_COL_TRANSPORT_TYPE else None
        self.cnd_delay = float(cols[APPPERF_COL_CND_DELAY]) if len(cols) > APPPERF_COL_CND_DELAY else None
        self.snd_delay = float(cols[APPPERF_COL_SND_DELAY]) if len(cols) > APPPERF_COL_SND_DELAY else None
        self.app_delay = float(cols[APPPERF_COL_APP_DELAY]) if len(cols) > APPPERF_COL_APP_DELAY else None

    def record(self, store: MetricsStore, base_tags: list[str]) -> None:
        app_tags = base_tags + [f'application:{self.app_name}']
        if self.tunnel_name:
            app_tags = app_tags + [f'tunnel_name:{self.tunnel_name}']
        if self.transport_type:
            app_tags = app_tags + [f'transport_type:{self.transport_type}']
        for latency_type, value in [
            ('cnd', self.cnd_delay),
            ('snd', self.snd_delay),
            ('app', self.app_delay),
        ]:
            if value is not None:
                store.record('application.latency', value, app_tags + [f'latency_type:{latency_type}'], AggType.AVG)

    @classmethod
    def parse(cls, content: str) -> Iterator[AppperfStats]:
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            yield cls(line.split(','))
