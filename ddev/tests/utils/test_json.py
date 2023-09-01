# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from ddev.utils.json import JSONPointerFile


def test_attributes(isolation):
    file_path = isolation / 'foo.json'
    pointer_file = JSONPointerFile(file_path)

    assert pointer_file.path is file_path


def test_get(temp_dir):
    data = {'foo': {'bar': ['baz']}}
    pointer_file = JSONPointerFile(temp_dir / 'foo.json')
    pointer_file.path.write_text(json.dumps(data))

    assert pointer_file.get('/foo/bar/0') == 'baz'


def test_set(temp_dir):
    data = {'foo': {'bar': ['baz']}}
    pointer_file = JSONPointerFile(temp_dir / 'foo.json')
    pointer_file.path.write_text(json.dumps(data))

    pointer_file.set('/foo/bar/0', 'test')

    assert pointer_file.get('/foo/bar/0') == 'test'
    assert json.loads(pointer_file.path.read_text()) == data


def test_save(temp_dir):
    data = {'foo': {'bar': ['baz']}}
    pointer_file = JSONPointerFile(temp_dir / 'foo.json')
    pointer_file.path.write_text(json.dumps(data))

    pointer_file.set('/foo/bar/0', 'test')
    pointer_file.save()

    assert pointer_file.get('/foo/bar/0') == 'test'

    new_data = json.loads(pointer_file.path.read_text())
    assert new_data != data

    data['foo']['bar'][0] = 'test'
    assert new_data == data
