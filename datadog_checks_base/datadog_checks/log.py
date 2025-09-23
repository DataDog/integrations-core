# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# ruff: noqa
from .base.log import *  # Import explicitly for use in https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/config.py
from .base.log import _get_py_loglevel
