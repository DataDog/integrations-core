# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class Space:
    def __init__(self, space_json):
        self.id = space_json.get("Id")
        self.name = space_json.get("Name")
        self.slug = space_json.get("Slug")
        self.projects = None
