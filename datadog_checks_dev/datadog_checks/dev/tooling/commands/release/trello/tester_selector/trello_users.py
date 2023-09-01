# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Dict, cast


class TrelloUser:
    def __init__(self, data: Dict[str, object]):
        self.id = cast(str, data['id'])
        self.full_name = cast(str, data['fullName'])
        self.username = cast(str, data['username'])
