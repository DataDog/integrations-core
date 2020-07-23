# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.utils import read_file, stream_file_lines

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')


def read_fixture(name):
    return read_file(os.path.join(FIXTURES_DIR, name))


def stream_fixture(name):
    return stream_file_lines(os.path.join(FIXTURES_DIR, name))
