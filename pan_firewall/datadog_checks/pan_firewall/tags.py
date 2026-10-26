# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def tag_tuple(*pairs: tuple[str, str | None]) -> tuple[str, ...]:
    return tuple(f'{name}:{value}' for name, value in pairs if value)
