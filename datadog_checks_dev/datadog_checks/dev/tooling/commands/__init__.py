# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .clean import clean
from .config import config
from .create import create
from .dep import dep
from .manifest import manifest
from .release import release
from .test import test

ALL_COMMANDS = (
    clean,
    config,
    create,
    dep,
    manifest,
    release,
    test,
)
