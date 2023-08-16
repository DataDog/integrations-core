# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.utils.json import JSONPointerFile


class RepositoryConfig(JSONPointerFile):
    """
    Represents a `/.ddev/config.toml` file.
    """

    def load_data(self) -> dict:
        from ddev.utils.toml import load_toml_file

        return load_toml_file(self.path)

    def save_data(self, data: dict):
        import tomli_w

        self.path.write_text(tomli_w.dumps(data))
