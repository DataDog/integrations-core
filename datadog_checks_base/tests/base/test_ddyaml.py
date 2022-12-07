import os
import tempfile

import pytest
import yaml

from datadog_checks.base.ddyaml import (
    monkey_patch_pyyaml,
    monkey_patch_pyyaml_reverse,
    safe_yaml_dump_all,
    safe_yaml_load,
    safe_yaml_load_all,
    yaml_load_force_loader,
    yDumper,
)

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'fixtures', 'ddyaml')


class Dummy(object):
    def __init__(self):
        self.foo = 1
        self.bar = 'a'
        self.qux = {self.foo: self.bar}

    def get_foo(self):
        return self.foo

    def get_bar(self):
        return self.bar

    def get_qux(self):
        return self.qux


@pytest.fixture(scope="module", autouse=True)
def patch_yaml():
    monkey_patch_pyyaml()
    yield
    monkey_patch_pyyaml_reverse()


def test_monkey_patch():
    assert yaml.dump_all == safe_yaml_dump_all
    assert yaml.load_all == safe_yaml_load_all
    assert yaml.load == safe_yaml_load


def test_load():
    conf = os.path.join(FIXTURE_PATH, "valid_conf.yaml")
    with open(conf) as f:
        stream = f.read()

        yaml_config_safe = safe_yaml_load(stream)
        yaml_config_native = yaml.load(stream)
        assert yaml_config_safe is not None
        assert yaml_config_native is not None
        assert yaml_config_native == yaml_config_safe

        yaml_config_safe = [entry for entry in safe_yaml_load_all(stream)]
        yaml_config_native = [entry for entry in yaml.load_all(stream)]
        assert yaml_config_safe is not []
        assert yaml_config_native is not []
        assert len(yaml_config_safe) == len(yaml_config_native)
        for safe, native in zip(yaml_config_safe, yaml_config_native):
            assert safe == native


def test_unsafe():
    dummy = Dummy()

    with pytest.raises(yaml.representer.RepresenterError):
        yaml.dump_all([dummy])

    with pytest.raises(yaml.representer.RepresenterError):
        yaml.dump(dummy, Dumper=yDumper)

    # reverse monkey patch and try again
    monkey_patch_pyyaml_reverse()

    with tempfile.TemporaryFile(suffix='.yaml', mode='w+t') as f:
        yaml.dump_all([dummy], stream=f)
        f.seek(0)  # rewind

        doc_unsafe = yaml.load(f, Loader=yaml.Loader)
        assert type(doc_unsafe) is Dummy

        monkey_patch_pyyaml()
        with pytest.raises(yaml.constructor.ConstructorError):
            f.seek(0)  # rewind
            safe_yaml_load(f)

        with pytest.raises(yaml.constructor.ConstructorError):
            f.seek(0)  # rewind
            yaml.load(f)


def test_force_loader():
    conf = os.path.join(FIXTURE_PATH, "valid_conf.yaml")
    with open(conf) as f:
        stream = f.read()
        yaml_config = yaml_load_force_loader(stream, yaml.SafeLoader)
        assert yaml_config is not None
