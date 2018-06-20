# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Invoke entrypoint, import here all the tasks we want to make available
"""
from __future__ import print_function, unicode_literals

from invoke import Collection
from colorama import init

# Task functions are added to the root namespace automatically.
# Ignore "imported but unused" flake8 errors for these imports.
from .cleanup import cleanup  # noqa: F401
from .manifest import manifest  # noqa: F401
from .upgrade import upgrade  # noqa: F401
from .test import test  # noqa: F401
from .changelog import update_changelog  # noqa: F401
from .release import (  # noqa: F401
    release_dev, release_prepare, release_tag, release_upload,
    compile_requirements, release_show_pending, print_shippable
)

# the root namespace
root = Collection()

root.configure({
    'run': {
        # set the encoding explicitly so invoke doesn't freak out if a command
        # outputs unicode chars.
        'encoding': 'utf-8',
    }
})

# init colorama
init(autoreset=True)
