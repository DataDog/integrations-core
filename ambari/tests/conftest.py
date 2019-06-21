# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'url': 'localhost',
        'port': 80,
        'username': 'admin',
        'password': 'admin',
        'services': {
            "HDFS": {"NAMENODE": [], "DATANODE": []},
            "YARN": {"NODEMANANGER": ["cpu", "disk", "load", "memory", "network", "process"], "YARNCLIENT": []},
            "MAPREDUCE2": {"HISTORYSERVER": ["BufferPool", "Memory", "jvm"]},
        },
    }


@pytest.fixture
def init_config():
    return {"collect_service_metrics": True, "collect_service_status": True}
