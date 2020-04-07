# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class Config:
    def __init__(self, instance):
        self.instance = instance

        self.url = instance.get('url', 'http://localhost:8081')
        if self.url.endswith('/'):
            self.url = self.url[:-1]

        self.tags = instance.get('tags', [])

        self.username = instance.get('username')
        self.password = instance.get('password')
        self.project = instance.get('project')
        if self.project:
            self.tags.append("project:{}".format(self.project))

        self.batch_size = instance.get('batch_size', 50)
