# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.repo.config import RepositoryConfig


def test_attributes():
    data = {}
    config = RepositoryConfig(data)

    assert config.data is data


class TestOverrides:
    def test_not_table(self, helpers):
        config = RepositoryConfig({'overrides': 9000})

        with helpers.error(TypeError, message='Repository configuration `overrides` must be a table'):
            _ = config.overrides

    def test_correct(self):
        data = {}
        config = RepositoryConfig({'overrides': data})

        assert config.overrides is data


class TestOverridesDisplayName:
    def test_not_table(self, helpers):
        config = RepositoryConfig({'overrides': {'display-name': 9000}})

        with helpers.error(TypeError, message='Repository configuration `overrides.display-name` must be a table'):
            _ = config.display_name_overrides

    def test_correct(self):
        data = {}
        config = RepositoryConfig({'overrides': {'display-name': data}})

        assert config.display_name_overrides is data
