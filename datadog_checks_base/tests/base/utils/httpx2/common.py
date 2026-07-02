# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64


def parse_basic_auth(header_value: str) -> tuple[str, str]:
    scheme, _, b64 = header_value.partition(' ')
    assert scheme.lower() == 'basic'
    user_pass = base64.b64decode(b64).decode('utf-8')
    user, _, password = user_pass.partition(':')
    return user, password
