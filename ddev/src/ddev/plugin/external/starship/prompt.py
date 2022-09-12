# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.file import ConfigFile


def main():
    config = ConfigFile()
    config.load()

    print(f'ddev{{repo: {config.model.repo.name}, org: {config.model.org.name}}}')
