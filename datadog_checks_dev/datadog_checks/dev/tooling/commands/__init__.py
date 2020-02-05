# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .agent import agent
from .ci import ci
from .clean import clean
from .config import config
from .create import create
from .dep import dep
from .docs import docs
from .env import env
from .meta import meta
from .release import release
from .run import run
from .test import test
from .validate import validate

ALL_COMMANDS = (agent, ci, clean, config, create, dep, docs, env, meta, release, run, test, validate)
