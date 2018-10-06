# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .clean import clean
from .config import config
from .create import create
from .dep import dep
from .env import env
from .manifest import manifest
from .meta import meta
from .metadata import metadata
from .release import release
from .run import run
from .test import test

ALL_COMMANDS = (
    clean,
    config,
    create,
    dep,
    env,
    manifest,
    meta,
    metadata,
    release,
    run,
    test,
)
