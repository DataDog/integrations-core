# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

if __name__ == '__main__':
    from ddev.plugin.external.starship.prompt import main

    sys.exit(main())
