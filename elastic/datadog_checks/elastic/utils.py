# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division


def ms_to_second(ms):
    return ms / 1000


def byte_to_mebibyte(byte):
    return byte / (1024 * 1024)
