# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .clean import clean
from .config import config
from .create import create
from .dep import dep
from .env import env
from .meta import meta
from .release import release
from .run import run
from .test import test
from .validate import validate

ALL_COMMANDS = (
    clean,
    config,
    create,
    dep,
    env,
    meta,
    release,
    run,
    test,
    validate,
)
