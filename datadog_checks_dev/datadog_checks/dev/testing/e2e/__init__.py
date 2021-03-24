# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .config import get_active_checks, get_configured_checks, get_configured_envs
from .core import create_interface, derive_interface
from .run import start_environment, stop_environment

E2E_SUPPORTED_TYPES = {'docker', 'local'}
