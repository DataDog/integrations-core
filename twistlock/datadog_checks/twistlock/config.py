# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import is_affirmative


class Config:
    def __init__(self, instance):
        self.instance = instance

        self.url = instance.get('url', 'http://localhost:8081')
        if self.url.endswith('/'):
            self.url = self.url[:-1]

        self.username = instance.get('username')
        self.password = instance.get('password')

        self.tags = instance.get('tags', [])

        self.ssl_verify = is_affirmative(instance.get('ssl_verify', True))
