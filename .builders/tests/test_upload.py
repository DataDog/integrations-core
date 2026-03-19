import email.message
import json
from hashlib import sha256
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

import pytest
import upload




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

        return targets_dir

    return _setup


@pytest.fixture
def setup_fake_hash(monkeypatch):
    def _setup_hash(mapping):
        def fake_hash(path: Path):
            return mapping.get(path.name, '')

        monkeypatch.setattr(upload, 'hash_file', fake_hash)

    return _setup_hash


@pytest.fixture
def frozen_timestamp(monkeypatch):
    timestamp = 20241327_090504
    monkeypatch.setattr(upload, 'timestamp_build_number', mock.Mock(return_value=timestamp))
    return timestamp


def test_upload_external(setup_targets_dir, setup_fake_hash):
    wheels = {
        'external': [
            ('all_new-2.31.0-py3-none-any.whl', 'all-new', '2.31.0', '>=3.6'),
            ('updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl', 'updated_version', '3.14.1', '>=3.7'),
            ('existing_version-5.14.2-py3-none-any.whl', 'existing-version', '5.14.2', '>=3.8'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    # Set up hash values for the wheels
    setup_fake_hash({
        'all_new-2.31.0-py3-none-any.whl': 'hash_all_new',
        'updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl': 'hash_updated',
        'existing_version-5.14.2-py3-none-any.whl': 'hash_existing',
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    def blob_exists(path):
        # existing_version already exists with same hash
        return path == 'external/existing-version/existing_version-5.14.2-py3-none-any.whl'

    def get_blob_metadata(path):
        if path == 'external/existing-version/existing_version-5.14.2-py3-none-any.whl':
            return {'sha256': 'hash_existing'}
        return {}

    def upload_file(local_path, blob_path, metadata=None):
        uploaded_files.append(blob_path)

    mock_bucket.blob_exists.side_effect = blob_exists
    mock_bucket.get_blob_metadata.side_effect = get_blob_metadata
    mock_bucket.upload_file.side_effect = upload_file
    mock_bucket.find_matching_wheels.return_value = []
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert 'external/all-new/all_new-2.31.0-py3-none-any.whl' in uploaded_files
    assert 'external/updated-version/updated_version-3.14.1-cp311-cp311-manylinux1_x86_64.whl' in uploaded_files
    assert 'external/existing-version/existing_version-5.14.2-py3-none-any.whl' not in uploaded_files


def test_upload_external_existing_returns_full_url_with_hash(setup_targets_dir, setup_fake_hash):
    """When an external wheel already exists, lockfile should contain full URL with hash."""
    existing_hash = 'existinghash123'

    wheels = {
        'external': [
            ('existing_pkg-1.0.0-py3-none-any.whl', 'existing-pkg', '1.0.0', '>=3.6'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing_pkg-1.0.0-py3-none-any.whl': 'newhash456',
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    def blob_exists(path):
        return path == 'external/existing-pkg/existing_pkg-1.0.0-py3-none-any.whl'

    def get_blob_metadata(path):
        if path == 'external/existing-pkg/existing_pkg-1.0.0-py3-none-any.whl':
            return {'sha256': existing_hash}
        return {}

    mock_bucket.blob_exists.side_effect = blob_exists
    mock_bucket.get_blob_metadata.side_effect = get_blob_metadata
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.find_matching_wheels.return_value = []
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_string.return_value = None

    lockfiles = upload.upload(targets_dir, bucket=mock_bucket)

    assert not uploaded_files
    assert lockfiles == {'linux-x86_64': [
        f'existing-pkg @ https://agent-int-packages.datadoghq.com/external/existing-pkg/'
        f'existing_pkg-1.0.0-py3-none-any.whl#sha256={existing_hash}',
        '',
    ]}


def test_upload_built_no_conflict(setup_targets_dir, setup_fake_hash, frozen_timestamp):
    wheels = {
        'built': [
            ('without_collision-3.14.1-cp311-cp311-manylinux2010_x86_64.whl', 'without-collision', '3.14.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'without_collision-3.14.1-cp311-cp311-manylinux2010_x86_64.whl': 'hash1',
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = []
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert (
        f'built/without-collision/without_collision-3.14.1-{frozen_timestamp}-cp311-cp311-manylinux2010_x86_64.whl'
        in uploaded_files
    )


def test_upload_built_existing_sha_match_does_not_upload(
    setup_targets_dir,
    setup_fake_hash,
):
    whl_hash = 'some-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': whl_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheel = {
        'name': 'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl',
        'metadata': {'sha256': whl_hash}
    }

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = [existing_wheel]
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert not uploaded_files


def test_upload_built_existing_sha_match_returns_full_url_with_hash(
    setup_targets_dir,
    setup_fake_hash,
):
    """When a built wheel already exists with matching hash, lockfile should contain full URL with hash."""
    whl_hash = 'abc123def456'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': whl_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheel = {
        'name': 'built/existing/existing-1.1.1-20241201000000-cp311-cp311-manylinux2010_x86_64.whl',
        'metadata': {'sha256': whl_hash}
    }

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = [existing_wheel]
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    lockfiles = upload.upload(targets_dir, bucket=mock_bucket)

    assert not uploaded_files
    assert lockfiles == {'linux-x86_64': [
        f'existing @ https://agent-int-packages.datadoghq.com/built/existing/'
        f'existing-1.1.1-20241201000000-cp311-cp311-manylinux2010_x86_64.whl#sha256={whl_hash}',
        '',
    ]}


def test_upload_built_existing_different_sha_does_upload(
    setup_targets_dir,
    setup_fake_hash,
    frozen_timestamp,
):
    original_hash = 'first-hash'
    new_hash = 'second-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': new_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheel = {
        'name': 'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl',
        'metadata': {'sha256': original_hash}
    }

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = [existing_wheel]
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert f'built/existing/existing-1.1.1-{frozen_timestamp}-cp311-cp311-manylinux2010_x86_64.whl' in uploaded_files


def test_upload_built_existing_sha_match_does_not_upload_multiple_existing_builds(
    setup_targets_dir,
    setup_fake_hash,
):
    matching_hash = 'some-hash'
    non_matching_hash = 'xxxx'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': matching_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheels = [
        {'name': 'built/existing/existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl',
         'metadata': {'sha256': non_matching_hash}},
        {'name': 'built/existing/existing-1.1.1-20241326000000-cp311-cp311-manylinux2010_x86_64.whl',
         'metadata': {'sha256': non_matching_hash}},
        {'name': 'built/existing/existing-1.1.1-20241327000000-cp311-cp311-manylinux2010_x86_64.whl',
         'metadata': {'sha256': matching_hash}},
    ]

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = existing_wheels
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert not uploaded_files


def test_upload_built_existing_different_sha_does_upload_multiple_existing_builds(
    setup_targets_dir,
    setup_fake_hash,
    frozen_timestamp,
):
    original_hash = 'first-hash'
    new_hash = 'second-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp311-cp311-manylinux2010_x86_64.whl': new_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheels = [
        {'name': 'built/existing/existing-1.1.1-2024132600000-cp311-cp311-manylinux2010_x86_64.whl',
         'metadata': {'sha256': 'b'}},
        {'name': 'built/existing/existing-1.1.1-2024132700000-cp311-cp311-manylinux2010_x86_64.whl',
         'metadata': {'sha256': original_hash}},
    ]

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = existing_wheels
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    upload.upload(targets_dir, bucket=mock_bucket)

    assert f'built/existing/existing-1.1.1-{frozen_timestamp}-cp311-cp311-manylinux2010_x86_64.whl' in uploaded_files


def test_external_wheel_priority(tmp_path, setup_targets_dir, setup_fake_hash):
    original_hash = 'first-hash'
    external_hash = 'external-hash'

    wheels = {
        'external': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }

    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl': external_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    def blob_exists(path):
        return path == 'external/existing/existing-1.1.0-cp312-cp312-manylinux2010_x86_64.whl'

    def get_blob_metadata(path):
        if path == 'external/existing/existing-1.1.0-cp312-cp312-manylinux2010_x86_64.whl':
            return {'sha256': external_hash}
        return {}

    mock_bucket.blob_exists.side_effect = blob_exists
    mock_bucket.get_blob_metadata.side_effect = get_blob_metadata
    mock_bucket.find_matching_wheels.return_value = []
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    targets = upload.upload(targets_dir, bucket=mock_bucket)
    assert targets ==  {'linux-x86_64': [
        f'existing @ https://agent-int-packages.datadoghq.com/external/existing/existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl#sha256={external_hash}',
          '']}

def test_built_wheel_priority(tmp_path, setup_targets_dir, setup_fake_hash, frozen_timestamp):
    original_hash = 'first-hash'
    external_hash = 'external-hash'
    built_hash = 'built-hash'

    wheels = {
        'built': [
            ('existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl', 'existing', '1.1.1', '>=3.7'),
        ]
    }

    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({
        'existing-1.1.1-cp312-cp312-manylinux2010_x86_64.whl': built_hash,
    })

    mock_bucket = mock.Mock(spec=upload.Bucket)
    uploaded_files = []

    existing_wheels = [
        {'name': 'built/existing/existing-1.1.1-20241326000000-cp312-cp312-manylinux2010_x86_64.whl',
         'metadata': {'sha256': original_hash}},
    ]

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = existing_wheels
    mock_bucket.list_wheels_with_prefix.return_value = []
    mock_bucket.upload_file.side_effect = lambda l, b, metadata=None: uploaded_files.append(b)
    mock_bucket.upload_string.return_value = None

    targets = upload.upload(targets_dir, bucket=mock_bucket)
    assert targets ==  {'linux-x86_64': [
        f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{frozen_timestamp}-cp312-cp312-manylinux2010_x86_64.whl#sha256={built_hash}',
          '']}


def test_lockfile_generation(tmp_path, setup_targets_dir):

    lockfile = {
        'linux-x86_64': [
            f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{frozen_timestamp}-cp312-cp312-manylinux2010_x86_64.whl#sha256=built-hash', ''], # noqa: E501
        'linux-aarch64': [
            f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{frozen_timestamp}-cp312-cp312-manylinux2010_aarch64.whl#sha256=built-hash', ''], # noqa: E501
    }
    # We don't need to upload anything, we just need to generate the lockfile
    targets_dir = setup_targets_dir({})
    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    with mock.patch.object(upload, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(upload, "LOCK_FILE_DIR", fake_resolved_dir):

        upload.generate_lockfiles(targets_dir, lockfile)
        lock_files = list(fake_resolved_dir.glob("*.txt"))
        assert lock_files, "No lock files generated"
        lockfile_map = {lock_file.name: lock_file.read_text().strip() for lock_file in lock_files}
        linux_x86_64_lockfile = lockfile_map[f"linux-x86_64_{upload.CURRENT_PYTHON_VERSION}.txt"]
        assert linux_x86_64_lockfile == f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{frozen_timestamp}-cp312-cp312-manylinux2010_x86_64.whl#sha256=built-hash'
        linux_aarch64_lockfile = lockfile_map[f"linux-aarch64_{upload.CURRENT_PYTHON_VERSION}.txt"]
        assert linux_aarch64_lockfile == f'existing @ https://agent-int-packages.datadoghq.com/built/existing/existing-1.1.1-{frozen_timestamp}-cp312-cp312-manylinux2010_aarch64.whl#sha256=built-hash'
        assert len(lock_files) == 2


def test_generate_lockfiles_accepts_string_path(tmp_path):

    lockfile = {'linux-x86_64': ['dep @ https://example.com/dep.whl#sha256=abc', '']}

    fake_deps_dir = tmp_path / ".deps"
    fake_resolved_dir = fake_deps_dir / "resolved"
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()
    (tmp_path / "targets").mkdir()

    with mock.patch.object(upload, "RESOLUTION_DIR", fake_deps_dir), \
         mock.patch.object(upload, "LOCK_FILE_DIR", fake_resolved_dir):
        # Should not raise TypeError: unsupported operand type(s) for /: 'str' and 'str'
        upload.generate_lockfiles(str(tmp_path / "targets"), lockfile)


def test_collect_and_validate_wheels(tmp_path):
    """Test that collect_and_validate_wheels correctly collects and validates wheel metadata."""
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()

    write_dummy_wheel(wheel_dir / "package1-1.0.0-py3-none-any.whl", "package1", "1.0.0", ">=3.6")
    write_dummy_wheel(wheel_dir / "package2-2.0.0-py3-none-any.whl", "package2", "2.0.0", ">=3.7")

    upload_data = upload.collect_and_validate_wheels(wheel_dir)

    assert len(upload_data) == 2
    assert upload_data[0][0] == "package1"
    assert upload_data[0][1]["Name"] == "package1"
    assert upload_data[0][1]["Version"] == "1.0.0"
    assert upload_data[1][0] == "package2"
    assert upload_data[1][1]["Name"] == "package2"
    assert upload_data[1][1]["Version"] == "2.0.0"


def test_collect_and_validate_wheels_invalid_name(tmp_path):
    """Test that collect_and_validate_wheels raises error for invalid project names."""
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()

    write_dummy_wheel(wheel_dir / "-invalid-1.0.0-py3-none-any.whl", "-invalid", "1.0.0", ">=3.6")

    with pytest.raises(RuntimeError) as exc_info:
        upload.collect_and_validate_wheels(wheel_dir)

    assert "Invalid project name" in str(exc_info.value)


def test_process_wheel_for_upload_external_new(setup_fake_hash):
    """Test processing a new external wheel that needs to be uploaded."""
    wheel_path = Path("test.whl")
    metadata = email.message.Message()
    metadata["Name"] = "test-pkg"
    metadata["Version"] = "1.0.0"

    mock_bucket = mock.Mock(spec=upload.Bucket)
    mock_bucket.blob_exists.return_value = False

    setup_fake_hash({"test.whl": "abc123"})

    lockfile_entry, artifact_name = upload.process_wheel_for_upload(
        wheel_path, "external", "test-pkg", metadata, mock_bucket, "(1/1)"
    )

    assert artifact_name == "test.whl"
    assert "test-pkg @ https://agent-int-packages.datadoghq.com/external/test-pkg/test.whl#sha256=abc123" == lockfile_entry


def test_process_wheel_for_upload_external_existing(setup_fake_hash):
    """Test processing an existing external wheel that doesn't need upload."""
    wheel_path = Path("test.whl")
    metadata = email.message.Message()
    metadata["Name"] = "test-pkg"
    metadata["Version"] = "1.0.0"

    mock_bucket = mock.Mock(spec=upload.Bucket)
    mock_bucket.blob_exists.return_value = True
    mock_bucket.get_blob_metadata.return_value = {"sha256": "existing123"}

    setup_fake_hash({"test.whl": "abc123"})

    lockfile_entry, artifact_name = upload.process_wheel_for_upload(
        wheel_path, "external", "test-pkg", metadata, mock_bucket, "(1/1)"
    )

    assert artifact_name is None
    assert "test-pkg @ https://agent-int-packages.datadoghq.com/external/test-pkg/test.whl#sha256=existing123" == lockfile_entry


def test_generate_artifact_listings():
    """Test that generate_artifact_listings creates proper HTML index pages."""
    mock_bucket = mock.Mock(spec=upload.Bucket)

    wheel1 = {
        'name': "external/package1/package1-1.0.0.whl",
        'project': 'package1',
        'metadata': {"requires-python": ">=3.6", "sha256": "hash1"}
    }

    wheel2 = {
        'name': "external/package2/package2-2.0.0.whl",
        'project': 'package2',
        'metadata': {"requires-python": ">=3.7", "sha256": "hash2"}
    }

    mock_bucket.list_wheels_with_prefix.return_value = [wheel1, wheel2]

    created_content = {}
    def track_upload(content, path, content_type='text/plain', cache_control=None):
        created_content[path] = content

    mock_bucket.upload_string.side_effect = track_upload

    upload.generate_artifact_listings({"external"}, mock_bucket)

    assert "external/" in created_content
    assert "external/package1/" in created_content
    assert "external/package2/" in created_content

    root_html = created_content["external/"]
    assert "<h1>Agent integrations dependencies</h1>" in root_html
    assert 'href="package1/"' in root_html
    assert 'href="package2/"' in root_html


@pytest.fixture
def patched_input_files(tmp_path, monkeypatch):
    dep_content = b'requests==2.31.0\n'
    dep_file = tmp_path / 'agent_requirements.in'
    dep_file.write_bytes(dep_content)

    workflow_content = b'on: push\n'
    workflow_file = tmp_path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    workflow_file.parent.mkdir(parents=True)
    workflow_file.write_bytes(workflow_content)

    builder_dir = tmp_path / '.builders'
    builder_dir.mkdir()
    (builder_dir / 'upload.py').write_bytes(b'# script\n')

    monkeypatch.setattr(upload, 'REPO_DIR', tmp_path)
    monkeypatch.setattr(upload, 'DIRECT_DEP_FILE', dep_file)
    monkeypatch.setattr(upload, 'WORKFLOW_FILE', workflow_file)
    monkeypatch.setattr(upload, 'BUILDER_DIR', builder_dir)

    return dep_content, workflow_content, builder_dir


def test_hash_directory(tmp_path):
    (tmp_path / 'a.txt').write_bytes(b'hello')
    (tmp_path / 'b.txt').write_bytes(b'world')

    result = upload.hash_directory(tmp_path)
    assert result == upload.hash_directory(tmp_path)

    (tmp_path / 'a.txt').write_bytes(b'changed')
    assert upload.hash_directory(tmp_path) != result

    (tmp_path / 'a.txt').write_bytes(b'hello')
    assert upload.hash_directory(tmp_path) == result

    (tmp_path / 'a.txt').rename(tmp_path / 'z.txt')
    assert upload.hash_directory(tmp_path) != result


def test_compute_input_hashes(patched_input_files):
    dep_content, workflow_content, builder_dir = patched_input_files

    result = upload.compute_input_hashes()

    assert set(result.keys()) == {'agent_requirements.in', '.github/workflows/resolve-build-deps.yaml', '.builders'}
    assert result['agent_requirements.in'] == sha256(dep_content).hexdigest()
    assert result['.github/workflows/resolve-build-deps.yaml'] == sha256(workflow_content).hexdigest()
    assert result['.builders'] == upload.hash_directory(builder_dir)


def test_generate_lockfiles_metadata_contains_inputs(tmp_path, patched_input_files, monkeypatch):
    dep_content, _, _ = patched_input_files

    fake_deps_dir = tmp_path / '.deps'
    fake_resolved_dir = fake_deps_dir / 'resolved'
    fake_deps_dir.mkdir()
    fake_resolved_dir.mkdir()

    monkeypatch.setattr(upload, 'RESOLUTION_DIR', fake_deps_dir)
    monkeypatch.setattr(upload, 'LOCK_FILE_DIR', fake_resolved_dir)

    upload.generate_lockfiles(tmp_path, {})

    metadata = json.loads((fake_deps_dir / 'metadata.json').read_text())
    assert 'inputs' in metadata
    assert set(metadata['inputs'].keys()) == {'agent_requirements.in', '.github/workflows/resolve-build-deps.yaml', '.builders'}
    assert metadata['inputs']['agent_requirements.in'] == sha256(dep_content).hexdigest()
    assert metadata['sha256'] == sha256(dep_content).hexdigest()


def test_upload(setup_targets_dir, setup_fake_hash):
    """Basic end-to-end test of upload with a mocked bucket."""
    wheels = {
        'external': [
            ('test_pkg-1.0.0-py3-none-any.whl', 'test-pkg', '1.0.0', '>=3.6'),
        ]
    }
    targets_dir = setup_targets_dir(wheels)

    setup_fake_hash({'test_pkg-1.0.0-py3-none-any.whl': 'abc123'})

    mock_bucket = mock.Mock(spec=upload.Bucket)

    uploaded_files = []

    mock_bucket.blob_exists.return_value = False
    mock_bucket.find_matching_wheels.return_value = []
    mock_bucket.list_wheels_with_prefix.return_value = []

    def track_upload(local_path, blob_path, metadata=None):
        uploaded_files.append(blob_path)

    mock_bucket.upload_file.side_effect = track_upload
    mock_bucket.upload_string.return_value = None

    lockfiles = upload.upload(targets_dir, bucket=mock_bucket)

    assert 'external/test-pkg/test_pkg-1.0.0-py3-none-any.whl' in uploaded_files
    assert 'test-pkg @ https://agent-int-packages.datadoghq.com/external/test-pkg/test_pkg-1.0.0-py3-none-any.whl#sha256=abc123' in lockfiles['linux-x86_64'][0]
