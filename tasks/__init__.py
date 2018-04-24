# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Invoke entrypoint, import here all the tasks we want to make available
"""
from __future__ import print_function, unicode_literals

from invoke import Collection

# task functions are added to the root namespace automatically
from .cleanup import cleanup
from .manifest import manifest
from .upgrade import upgrade
from .test import test
from .changelog import update_changelog

# the root namespace
root = Collection()

root.configure({
    'run': {
        # set the encoding explicitly so invoke doesn't freak out if a command
        # outputs unicode chars.
        'encoding': 'utf-8',
    }
})
