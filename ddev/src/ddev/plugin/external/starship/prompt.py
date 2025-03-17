# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.file import CombinedConfigFile


def main():
    config = CombinedConfigFile()
    config.load()

    print(f'ddev{{repo: {config.combined_model.repo.name}, org: {config.combined_model.org.name}}}')
