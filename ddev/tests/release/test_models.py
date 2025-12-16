import pytest

from ddev.cli.release.stats.size_utils.models import (
    CommitSize,
    ModuleSize,
    PlatformSize,
    PullRequest,
    SizeBlock,
    SizePair,
    SizeValues,
)

size_value_a = SizeValues(bytes=150)
size_value_b = SizeValues(bytes=350)
size_value_c = SizeValues(bytes=500)
size_value_d = SizeValues(bytes=700)
size_value_e = SizeValues(bytes=900)
size_value_f = SizeValues(bytes=1100)
size_value_g = SizeValues(bytes=1050)
size_value_h = SizeValues(bytes=1500)
size_value_i = SizeValues(bytes=650)
size_value_j = SizeValues(bytes=1050)

size_pair_a = SizePair(compressed=size_value_a, uncompressed=size_value_b)
size_pair_b = SizePair(compressed=size_value_c, uncompressed=size_value_d)
size_pair_c = SizePair(compressed=size_value_e, uncompressed=size_value_f)
size_pair_d = SizePair(compressed=size_value_g, uncompressed=size_value_h)
size_pair_e = SizePair(compressed=size_value_i, uncompressed=size_value_j)

size_block_a = SizeBlock(declared=size_pair_a, locked=size_pair_b)
size_block_b = SizeBlock(declared=size_pair_c, locked=size_pair_a)

size_block_c = SizeBlock(declared=size_pair_a, locked=None)
size_block_d = SizeBlock(declared=size_pair_c, locked=None)
size_block_e = SizeBlock(declared=None, locked=size_pair_b)
size_block_f = SizeBlock(declared=None, locked=size_pair_e)

module_size_a = ModuleSize(
    name="int1",
    version="1.0.0",
    platform="linux-aarch64",
    type="integration",
    python_version="3.12",
    module_sha="1234567890",
    size=size_block_a,
)
module_size_b = ModuleSize(
    name="int2",
    version="1.0.0",
    platform="linux-aarch64",
    type="integration",
    python_version="3.12",
    module_sha="2345678901",
    size=size_block_b,
)
module_size_c = ModuleSize(
    name="dep1",
    version="1.0.0",
    platform="macos-x86_64",
    type="dependency",
    python_version="3.12",
    module_sha="3456789012",
    size=size_block_c,
)
module_size_d = ModuleSize(
    name="dep2",
    version="1.0.0",
    platform="macos-x86_64",
    type="dependency",
    python_version="3.12",
    module_sha="4567890123",
    size=size_block_d,
)
module_size_e = ModuleSize(
    name="dep3",
    version="1.0.0",
    platform="linux-aarch64",
    type="dependency",
    python_version="3.12",
    module_sha="5678901234",
    size=size_block_e,
)

commit_size_a = CommitSize(
    commit_sha="1234567890",
    pull_request=PullRequest(number=1, title="Test PR"),
    modules_sizes=[module_size_a, module_size_b, module_size_c],
)

commit_size_b = CommitSize(
    commit_sha="1234567890",
    pull_request=PullRequest(number=1, title="Test PR"),
    modules_sizes=[module_size_d, module_size_e],
)

# --------- SizeValues ---------


@pytest.mark.parametrize(
    "bytes_value, expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (-128, "-128 B"),
        (2048, "2.00 KiB"),
        (5 * 1024**2 + int(0.003 * 1024**2), "5.00 MiB"),
        (3 * 1024**3 + int(0.006 * 1024**3), "3.01 GiB"),
    ],
)
def test_size_values_human_readable(bytes_value: int, expected: str) -> None:
    size = SizeValues(bytes=bytes_value)

    assert size.human_readable == expected


def test_size_values_addition() -> None:
    result = size_value_a + size_value_b

    assert result.bytes == 500


# --------- SizePair ---------


def test_size_pair_addition() -> None:
    result = size_pair_a + size_pair_b

    assert result.compressed.bytes == 650
    assert result.uncompressed.bytes == 1050


# --------- SizeBlock ---------
@pytest.mark.parametrize(
    "size1, size2, expected_declared, expected_locked",
    [
        pytest.param(
            size_block_a,
            size_block_b,
            size_block_a.declared + size_block_b.declared,
            size_block_a.locked + size_block_b.locked,
            id="both-declared-and-locked",
        ),
        pytest.param(
            size_block_c,
            size_block_d,
            size_block_d.declared + size_block_c.declared,
            None,
            id="only-declared",
        ),
        pytest.param(
            size_block_e,
            size_block_f,
            None,
            size_block_e.locked + size_block_f.locked,
            id="only-locked",
        ),
        pytest.param(
            size_block_e,
            size_block_d,
            size_block_d.declared,
            size_block_e.locked,
            id="one-declared-one-locked",
        ),
    ],
)
def test_size_block_addition(
    size1: SizeBlock, size2: SizeBlock, expected_declared: SizePair | None, expected_locked: SizePair | None
) -> None:
    result = size1 + size2

    assert result.declared == expected_declared
    assert result.locked == expected_locked


def test_size_block_init_error() -> None:
    with pytest.raises(ValueError):
        SizeBlock(declared=None, locked=None)


@pytest.mark.parametrize(
    "declared, locked",
    [
        (size_pair_a, None),
        (None, size_pair_b),
    ],
)
def test_size_block_init_success(declared, locked) -> None:
    SizeBlock(declared=declared, locked=locked)


# --------- CommitSize ---------
def test_platforms_size() -> None:
    result = commit_size_a.platforms_size

    assert result == [
        PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_a + size_block_b),
        PlatformSize(platform="macos-x86_64", python_version="3.12", size=size_block_c),
    ]


def test_commit_size_filter() -> None:
    result = commit_size_a.filter(platform="linux-aarch64", python_version="3.12")

    assert result.modules_sizes == [module_size_a, module_size_b]
    assert result.platforms_size == [
        PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_a + size_block_b)
    ]


def test_commit_size_filter_none() -> None:
    result = commit_size_a.filter(platform="linux-aarch64", python_version="3.12", name="fake-name")
    assert result is None


def test_commit_size_join() -> None:
    result = commit_size_a.join(commit_size_b)

    assert result.modules_sizes == [module_size_a, module_size_b, module_size_c, module_size_d, module_size_e]
    assert result.platforms_size == [
        PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_a + size_block_b + size_block_e),
        PlatformSize(platform="macos-x86_64", python_version="3.12", size=size_block_c + size_block_d),
    ]


def test_commit_size_append() -> None:
    commit_size = commit_size_a.model_copy()
    commit_size.append(module_size_d)

    assert commit_size.modules_sizes == [module_size_a, module_size_b, module_size_c, module_size_d]
    assert commit_size.platforms_size == [
        PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_a + size_block_b),
        PlatformSize(platform="macos-x86_64", python_version="3.12", size=size_block_c + size_block_d),
    ]
