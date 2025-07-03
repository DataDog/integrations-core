from pathlib import Path
from unittest import mock
from zipfile import ZipFile
import fnmatch

import pytest

import upload_and_lock
import generate_lock


@pytest.fixture
def workflow_id():
    return '1234567890'

@pytest.fixture
def setup_fake_bucket(monkeypatch):
    """Patch google storage functions to simulate a bucket."""

    def _setup_bucket(files):
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

        def list_blobs(*, prefix='', match_glob='*'):
            # Note that this is a limited emulation of match_glob, as fnmatch doesn't treat '/' specially,
            # but it should be good enough for what we use it for.
            return (
                make_blob(f) for f in files
                if f.startswith(prefix) and fnmatch.fnmatch(f, match_glob)
            )

        bucket = mock.Mock()
        bucket.list_blobs.side_effect = list_blobs
        bucket.blob.side_effect = make_blob

        client = mock.Mock()
        client.bucket.return_value = bucket

        monkeypatch.setattr(upload_and_lock.storage, 'Client', mock.Mock(return_value=client))
        return bucket, uploads

    return _setup_bucket


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
    def _setup(wheels, platform='linux-x86_64', python_major_version='3'):
        targets_dir = tmp_path_factory.mktemp('output')

        for artifact_type, wheel_entries in wheels.items():
            external_dir = targets_dir / platform / f'py{python_major_version}' / 'wheels' / artifact_type
            external_dir.mkdir(parents=True)

            for path, *pkginfo in wheel_entries:
                full_path = external_dir / path
                write_dummy_wheel(full_path, *pkginfo)

        with open(targets_dir / platform / f'py{python_major_version}' / 'frozen.txt', 'w') as f:
            f.write('existing==1.1.1\n')

        return targets_dir

    return _setup


@pytest.fixture
def setup_fake_hash(monkeypatch):
    def _setup_hash(mapping):
        def fake_hash(path: Path):
            return mapping.get(path.name, '')

        monkeypatch.setattr(upload_and_lock, 'hash_file', fake_hash)

    return _setup_hash


def test_upload_external(setup_targets_dir, setup_fake_bucket):
    wheels = {
        'external': [
            ('all_new-2.31.0-py3-none-any.whl', 'all-new', '2.31.0', '>=3.6'),
            ('updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl', 'updated_version', '3.14.1', '>=3.7'),
            ('existing_version-5.14.2-py3-none-any.whl', 'existing-version', '5.14.2', '>=3.8'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'external/updated-version/updated_version-3.13.0-cp311-cp311-manylinux1_x86_64.whl':
        {'requires-python': '', 'sha256': ''},
        'external/existing-version/existing_version-5.14.2-py3-none-any.whl':
        {'requires-python': '', 'sha256': ''},
    }
    bucket, uploads = setup_fake_bucket(bucket_files)

    upload_and_lock.upload(targets_dir, workflow_id)

    bucket_files = [f.name for f in bucket.list_blobs()]
    assert 'external/all-new/all_new-2.31.0-py3-none-any.whl' in bucket_files
    assert 'external/updated-version/updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl' in bucket_files

    uploads = {str(Path(f).relative_to(targets_dir / 'linux-x86_64' / 'py3' / 'wheels' / 'external')) for f in uploads}
    assert {'all_new-2.31.0-py3-none-any.whl', 'updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl'} <= uploads


def test_upload_built_no_conflict(setup_targets_dir, setup_fake_bucket, workflow_id):
    wheels = {
        'built': [
            ('without_collision-3.14.1-cp311-cp311-manylinux2010_x86_64.whl', 'without-collision', '3.14.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket, uploads = setup_fake_bucket({})

    upload_and_lock.upload(targets_dir, workflow_id)

    bucket_files = [f.name for f in bucket.list_blobs()]
    assert (
        f'built/without-collision/without_collision-3.14.1-{workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl'
        in bucket_files
    )


def test_upload_built_existing_sha_match_does_not_upload(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):
    whl_hash = 'some-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': whl_hash},
    }
    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': whl_hash,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    assert not uploads


def test_upload_built_existing_different_sha_does_upload(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):
    original_hash = 'first-hash'
    new_hash = 'second-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
    }
    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': new_hash,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    uploads = {str(Path(f).name) for f in uploads}

    assert uploads == {'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl'}

    bucket_files = {f.name for f in bucket.list_blobs()}
    assert f'built/existing/existing-1.1.1-{workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl' in bucket_files


def test_upload_built_existing_sha_match_does_not_upload_multiple_existing_builds(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):
    matching_hash = 'some-hash'
    non_matching_hash = 'xxxx'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': non_matching_hash},
        'built/existing/existing-1.1.1-20241326000000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': non_matching_hash},
        'built/existing/existing-1.1.1-20241327000000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': matching_hash},
        # The following two builds are for different platforms and should therefore not count
        'built/existing/existing-1.1.1-2024132700001-cp311-cp311-manylinux2010_aarch64.whl':
        {'requires-python': '', 'sha256': non_matching_hash},
        'built/existing/existing-1.1.1-2024132700002-py27-py27mu-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': non_matching_hash},
    }
    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': matching_hash,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    assert not uploads


def test_upload_built_existing_different_sha_does_upload_multiple_existing_builds(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):
    original_hash = 'first-hash'
    new_hash = 'second-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'built/existing/existing-1.1.1-2024132600000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': 'b'},
        'built/existing/existing-1.1.1-2024132700000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
    }
    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': new_hash,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    uploads = {str(Path(f).name) for f in uploads}

    assert uploads == {'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl'}

    bucket_files = {f.name for f in bucket.list_blobs()}
    assert f'built/existing/existing-1.1.1-{workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl' in bucket_files


def test_build_tag_use_workflow_id(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):  
    hash_one = 'hash-one'
    hash_two = 'hash-two'
    hash_three = 'hash-three'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        'built/existing/existing-1.1.1-2024132600000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': hash_one},
        'built/existing/existing-1.1.1-2024132700000-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': hash_two}
    }
    
    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': hash_three,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    uploads = {str(Path(f).name) for f in uploads}

    assert uploads == {'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl'}

    bucket_files = {f.name for f in bucket.list_blobs()}
    assert f'built/existing/existing-1.1.1-{workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl' in bucket_files


def test_use_current_workflow_id(
    setup_targets_dir,
    setup_fake_bucket,
    setup_fake_hash,
    workflow_id,
):
    original_hash = 'first-hash'
    new_hash = 'second-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{previous_workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': new_hash,
    })

    upload_and_lock.upload(targets_dir, workflow_id)

    uploads = {str(Path(f).name) for f in uploads}

    assert uploads == {'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl'}

    bucket_files = {f.name for f in bucket.list_blobs()}
    assert f'built/existing/existing-1.1.1-{workflow_id}WID-cp311-cp311-manylinux2010_x86_64.whl' in bucket_files


def test_lockfile_generation(tmp_path, setup_targets_dir, setup_fake_bucket, workflow_id):
    original_hash = 'first-hash'
    new_hash = 'second-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]   
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': new_hash},
        f'built/existing/existing-1.1.1-{previous_workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(generate_lock, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(generate_lock, "LOCK_FILE_DIR", fake_resolved_dir):
        
        generate_lock.lock(str(targets_dir), workflow_id)

        lock_files = list(fake_resolved_dir.glob("*.txt"))
        assert lock_files, "No lock files generated"
        contents = lock_files[0].read_text().strip()
        assert f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl#sha256={new_hash}' == contents


# Test when there are built and external packages for a dependency and the built wheel is the prefered dependency i.e it's workflow_id is the current build number
def test_built_wheel_priority(tmp_path, setup_targets_dir, setup_fake_bucket, workflow_id):
    original_hash = 'first-hash'
    new_hash = 'second-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]   
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': new_hash},
        f'built/existing/existing-1.1.1-{previous_workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
        'external/existing/existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': ''},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(generate_lock, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(generate_lock, "LOCK_FILE_DIR", fake_resolved_dir):
        
        generate_lock.lock(str(targets_dir), workflow_id)
        lock_files = list(fake_resolved_dir.glob("*.txt"))
        contents = lock_files[0].read_text().strip()
        assert f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl#sha256={new_hash}' == contents

# Test when there are built and external packages for a dependency and the external wheel is the prefered dependency i.e no workflow_id matches
def test_external_wheel_priority(tmp_path, setup_targets_dir, setup_fake_bucket, workflow_id):
    original_hash = 'first-hash'
    external_hash = 'external-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]   
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{previous_workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
        'external/existing/existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': external_hash},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(generate_lock, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(generate_lock, "LOCK_FILE_DIR", fake_resolved_dir):
        
        generate_lock.lock(str(targets_dir), workflow_id)
        lock_files = list(fake_resolved_dir.glob("*.txt"))
        contents = lock_files[0].read_text().strip()
        assert f'existing @ https://agent-int-packages.datadoghq.com/external/existing/existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl#sha256={external_hash}' == contents


# Test if nothing matches, we raise an error: RuntimeError(f'Could not find any wheels for target {target}: {project}=={version}')
def test_no_wheel_match(tmp_path, setup_targets_dir, setup_fake_bucket, workflow_id):
    original_hash = 'first-hash'
    new_hash = 'second-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id
    other_workflow_id = '1234567892'

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]   
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{previous_workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
        f'built/existing/existing-1.1.1-{other_workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': new_hash},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(generate_lock, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(generate_lock, "LOCK_FILE_DIR", fake_resolved_dir):
        
        with pytest.raises(RuntimeError, match=f'Could not find any wheels for target linux-x86_64: existing==1.1.1'):
            generate_lock.lock(str(targets_dir), workflow_id)

# Test the old format of the built wheel i.e build number is a timestamp (int) with no workflow_id
def test_old_format_built_wheel(tmp_path, setup_targets_dir, setup_fake_bucket, workflow_id):
    original_hash = 'first-hash'
    new_hash = 'second-hash'
    previous_workflow_id = '1234567891' # this workflow_id is already uploaded to the bucket even though it has a later workflow id

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]   
    }
    
    targets_dir = setup_targets_dir(wheels)

    bucket_files = {
        f'built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': new_hash},
        f'built/existing/existing-1.1.1-2024132600000-cp312-cp312-manylinux2010_x86_64.whl':
        {'requires-python': '', 'sha256': original_hash},
    }

    bucket, uploads = setup_fake_bucket(bucket_files)

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(generate_lock, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(generate_lock, "LOCK_FILE_DIR", fake_resolved_dir):
        
        generate_lock.lock(str(targets_dir), workflow_id)
        lock_files = list(fake_resolved_dir.glob("*.txt"))
        contents = lock_files[0].read_text().strip()
        assert f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{workflow_id}WID-cp312-cp312-manylinux2010_x86_64.whl#sha256={new_hash}' == contents