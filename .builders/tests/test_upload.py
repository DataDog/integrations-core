from pathlib import Path
from unittest import mock
from zipfile import ZipFile

import pytest

import upload


@pytest.fixture
def setup_fake_bucket(monkeypatch):
    """Patch google storage functions to simulate a bucket."""

    files = {
        'external/updated-version/updated_version-3.13.0-cp311-cp311-manylinux1_x86_64.whl':
        {'requires-python': '', 'sha256': ''},
        'external/existing-version/existing_version-5.14.2-py3-none-any.whl':
        {'requires-python': '', 'sha256': ''},
    }

    uploads = []

    def make_blob(name):
        def fake_upload(wheel_name):
            files[name] = {'requires-python': '', 'sha256': ''}
            uploads.append(wheel_name)

        blob = mock.Mock()
        blob.exists.side_effect = lambda: name in files
        blob.upload_from_filename.side_effect = fake_upload
        blob.name = name
        blob.metadata = files.get(name, None)
        return blob

    def list_blobs(prefix=''):
        return [make_blob(f) for f in files if f.startswith(prefix)]

    bucket = mock.Mock()
    bucket.list_blobs.side_effect = list_blobs
    bucket.blob.side_effect = make_blob

    client = mock.Mock()
    client.bucket.return_value = bucket

    monkeypatch.setattr(upload.storage, 'Client', mock.Mock(return_value=client))
    return bucket, uploads


def write_dummy_wheel(path, project_name, version, requires_python):
    metadata = '\n'.join([
        'Metadata-Version: 2.3',
        f'Name: {project_name}',
        f'Version: {version}',
        f'Requires-Python: {requires_python}',
    ])
    with ZipFile(path, 'w') as zip_archive:
        with zip_archive.open(f'{project_name}-{version}.dist-info/METADATA', 'w') as metadata_file:
            metadata_file.write(metadata.encode('utf-8'))


@pytest.fixture
def setup_targets_dir(tmp_path_factory):
    def _setup(wheels):
        targets_dir = tmp_path_factory.mktemp('output')

        platform = 'linux-x86_64'
        external_dir = targets_dir / platform / 'py3' / 'wheels' / 'external'
        external_dir.mkdir(parents=True)

        for path, *pkginfo in wheels:
            full_path = external_dir / path
            write_dummy_wheel(full_path, *pkginfo)

        return targets_dir

    return _setup


def test_upload_external(setup_targets_dir, setup_fake_bucket):
    wheels = [
        ('all_new-2.31.0-py3-none-any.whl', 'all-new', '2.31.0', '>=3.6'),
        ('updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl', 'updated_version', '3.14.1', '>=3.7'),
        ('existing_version-5.14.2-py3-none-any.whl', 'existing-version', '5.14.2', '>=3.8'),
    ]
    targets_dir = setup_targets_dir(wheels)

    bucket, uploads = setup_fake_bucket
    upload.upload(targets_dir)

    bucket_files = [f.name for f in bucket.list_blobs()]
    assert 'external/all-new/all_new-2.31.0-py3-none-any.whl' in bucket_files
    assert 'external/updated-version/updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl' in bucket_files

    uploads = {str(Path(f).relative_to(targets_dir / 'linux-x86_64' / 'py3' / 'wheels' / 'external')) for f in uploads}
    assert {'all_new-2.31.0-py3-none-any.whl', 'updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl'} <= uploads
