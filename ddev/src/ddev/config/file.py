# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import cast

from ddev.config.model import RootConfig
from ddev.config.utils import scrub_config
from ddev.utils.fs import Path
from ddev.utils.toml import load_toml_data


class ConfigFile:
    def __init__(self, path: Path | None = None):
        self._path: Path | None = path
        self.model = cast(RootConfig, None)

    @property
    def path(self):
        if self._path is None:
            self._path = self.get_default_location()

        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    def save(self, content=None):
        import tomli_w

        if not content:
            content = tomli_w.dumps(self.model.raw_data)

        self.path.ensure_parent_dir_exists()
        self.path.write_atomic(content, 'w', encoding='utf-8')

    def load(self):
        self.model = RootConfig(load_toml_data(self.read()))

    def read(self) -> str:
        return self.path.read_text()

    def read_scrubbed(self) -> str:
        import tomli_w

        config = RootConfig(load_toml_data(self.read()))
        scrub_config(config.raw_data)

        return tomli_w.dumps(config.raw_data)

    def reset(self):
        config = RootConfig({})
        config.parse_fields()
        self.model = config

    def restore(self):
        import tomli_w

        self.reset()
        content = tomli_w.dumps(self.model.raw_data)
        self.save(content)

    def update(self):  # no cov
        self.model.parse_fields()
        self.save()

    @classmethod
    def get_default_location(cls) -> Path:
        from platformdirs import user_data_dir

        return Path(user_data_dir('dd-checks-dev', appauthor=False)) / 'config.toml'
