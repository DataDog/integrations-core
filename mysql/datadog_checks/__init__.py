# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This fixes some issues with import paths not being correctly detected by IDEs
__path__ = __import__('pkgutil').extend_path(__path__, __name__)