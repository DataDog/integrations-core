# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MARKER_PREFIX = '--ddev-pytest-argv='


def main() -> int:
    markers = [arg for arg in sys.argv[1:] if arg.startswith(MARKER_PREFIX)]
    if markers:
        if len(markers) != 1:
            raise SystemExit('Expected exactly one pytest argv marker')
        payload = json.loads(Path(os.environ['DDEV_PYTEST_ARGV_FILE']).read_text(encoding='utf-8'))
        if markers[0] != MARKER_PREFIX + payload['id']:
            raise SystemExit('Pytest argv marker does not match its payload')
        tokens = payload['argv']
        if not isinstance(tokens, list) or not all(isinstance(token, str) for token in tokens):
            raise SystemExit('Pytest argv payload must be a list of strings')
        if any(character in token for token in tokens for character in '\x00\r\n'):
            raise SystemExit('Pytest argv cannot contain NUL, CR or LF')
        index = sys.argv.index(markers[0])
        sys.argv[index : index + 1] = tokens
    # Config discovery and plugin loading must see the restored argv too.
    import pytest

    return pytest.console_main()


if __name__ == '__main__':
    raise SystemExit(main())
