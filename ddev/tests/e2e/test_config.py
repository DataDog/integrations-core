# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.e2e.config import EnvData, EnvDataStorage


class TestEnvDataStorage:
    def test_nonexistent_okay(self, temp_dir) -> None:
        storage = EnvDataStorage(temp_dir)

        assert not storage.get_integrations()
        assert not storage.get_environments('foo')

    def test_get_integrations(self, temp_dir) -> None:
        storage = EnvDataStorage(temp_dir)
        storage.get('foo', 'env').write_metadata({})
        storage.get('bar', 'env').write_metadata({})

        assert storage.get_integrations() == ['bar', 'foo']

    def test_get_environments(self, temp_dir) -> None:
        storage = EnvDataStorage(temp_dir)
        storage.get('foo', 'env1').write_metadata({})
        storage.get('foo', 'env2').write_metadata({})

        assert storage.get_environments('foo') == ['env1', 'env2']


class TestEnvData:
    def test_default_not_exists(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        assert not env_data.exists()

    def test_metadata(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        metadata = {'foo': 'bar'}
        env_data.write_metadata(metadata)

        assert env_data.exists()
        assert env_data.read_metadata() == metadata

    def test_config_no_instances(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        config = {'foo': 'bar'}
        env_data.write_config(config)

        assert env_data.exists()
        assert env_data.read_config() == {'instances': [config]}

    def test_config_full_config(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        config = {'init_config': {'bar': 'baz'}, 'instances': [{'foo': 'bar'}]}
        env_data.write_config(config)

        assert env_data.exists()
        assert env_data.read_config() == config

    def test_config_none_no_write(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        env_data.write_config(None)

        assert not env_data.exists()

    def test_remove(self, temp_dir) -> None:
        env_data = EnvData(temp_dir / 'path')

        env_data.write_config({'foo': 'bar'})
        assert env_data.exists()

        env_data.remove()
        assert not env_data.exists()
