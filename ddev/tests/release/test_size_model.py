import pytest

from ddev.cli.release.stats.size_utils.size_models import (
    CommitSize,
    ModuleSize,
    PlatformSize,
    PullRequest,
    SizeBlock,
    SizePair,
    SizeValues,
)

size_value_a = SizeValues(bytes=150, human_readable="150.0 B")
size_value_b = SizeValues(bytes=350, human_readable="350.0 B")
size_value_c = SizeValues(bytes=500, human_readable="500.0 B")
size_value_d = SizeValues(bytes=700, human_readable="700.0 B")
size_value_e = SizeValues(bytes=900, human_readable="900.0 B")
size_value_f = SizeValues(bytes=1100, human_readable="1.07 KiB")
size_value_g = SizeValues(bytes=1050, human_readable="1.02 KiB")
size_value_h = SizeValues(bytes=1500, human_readable="1.46 KiB")
size_value_i = SizeValues(bytes=650, human_readable="650.0 B")
size_value_j = SizeValues(bytes=1050, human_readable="1.02 KiB")

size_pair_a = SizePair(compressed=size_value_a, uncompressed=size_value_b)
size_pair_b = SizePair(compressed=size_value_c, uncompressed=size_value_d)
size_pair_c = SizePair(compressed=size_value_e, uncompressed=size_value_f)
size_pair_d = SizePair(compressed=size_value_g, uncompressed=size_value_h)
size_pair_e = SizePair(compressed=size_value_i, uncompressed=size_value_j)

size_block_a = SizeBlock(declared=size_pair_a, locked=size_pair_b)
size_block_b = SizeBlock(declared=size_pair_c, locked=size_pair_a)

size_block_c = SizeBlock(declared=size_pair_a, locked=None)
size_block_d = SizeBlock(declared=size_pair_c, locked=None)
size_block_e = SizeBlock(declared=size_pair_b, locked=None)
size_block_f = SizeBlock(declared=size_pair_d, locked=None)
size_block_g = SizeBlock(declared=size_pair_e, locked=None)

size_block_h = SizeBlock(declared=None, locked=size_pair_b)
size_block_i = SizeBlock(declared=None, locked=size_pair_e)

module_size_a = ModuleSize(
    name="int1",
    version="1.0.0",
    platform="linux-aarch64",
    type="integration",
    python_version="3.12",
    module_sha="1234567890",
    size=size_block_c,
)
module_size_b = ModuleSize(
    name="int2",
    version="1.0.0",
    platform="linux-aarch64",
    type="integration",
    python_version="3.12",
    module_sha="2345678901",
    size=size_block_d,
)
module_size_c = ModuleSize(
    name="dep1",
    version="1.0.0",
    platform="macos-x86_64",
    type="dependency",
    python_version="3.12",
    module_sha="3456789012",
    size=size_block_e,
)


module_size_d = ModuleSize(
    name="dep2",
    version="1.0.0",
    platform="macos-x86_64",
    type="dependency",
    python_version="3.12",
    module_sha="4567890123",
    size=size_block_f,
)
module_size_e = ModuleSize(
    name="dep3",
    version="1.0.0",
    platform="linux-aarch64",
    type="dependency",
    python_version="3.12",
    module_sha="5678901234",
    size=size_block_g,
)

platform_size_a_linuc = PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_c + size_block_d)
platform_size_a_macos = PlatformSize(platform="macos-x86_64", python_version="3.12", size=size_block_e)
platform_size_b_linux = PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_g)
platform_size_b_macos = PlatformSize(platform="macos-x86_64", python_version="3.12", size=size_block_f)

commit_size_a = CommitSize(
    commit_sha="1234567890",
    pull_request=PullRequest(number=1, title="Test PR"),
    modules_sizes=[module_size_a, module_size_b, module_size_c],
    platforms_size=[platform_size_a_linuc, platform_size_a_macos],
)

commit_size_b = CommitSize(
    commit_sha="1234567890",
    pull_request=PullRequest(number=1, title="Test PR"),
    modules_sizes=[module_size_d, module_size_e],
    platforms_size=[platform_size_b_linux, platform_size_b_macos],
)


# --------- SizeValues ---------


def test_size_values_addition() -> None:
    result = size_value_a + size_value_b

    assert result.bytes == 500
    assert result.human_readable == "500.0 B"


def test_size_values_subtraction() -> None:
    result = size_value_a - size_value_b

    assert result.bytes == -200
    assert result.human_readable == "-200.0 B"


# --------- SizePair ---------
def test_size_pair_addition() -> None:
    result = size_pair_a + size_pair_b

    assert result.compressed.bytes == 650
    assert result.compressed.human_readable == "650.0 B"
    assert result.uncompressed.bytes == 1050
    assert result.uncompressed.human_readable == "1.03 KiB"


def test_size_pair_subtraction() -> None:
    result = size_pair_a - size_pair_b

    assert result.compressed.bytes == -350.0
    assert result.compressed.human_readable == "-350.0 B"
    assert result.uncompressed.bytes == -350.0
    assert result.uncompressed.human_readable == "-350.0 B"


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
            size_block_h,
            size_block_i,
            None,
            size_block_h.locked + size_block_i.locked,
            id="only-locked",
        ),
    ],
)
def test_size_block_addition(
    size1: SizeBlock, size2: SizeBlock, expected_declared: SizePair | None, expected_locked: SizePair | None
) -> None:
    result = size1 + size2

    assert result.declared == expected_declared
    assert result.locked == expected_locked


def test_size_addition_error() -> None:
    with pytest.raises(ValueError):
        size_block_d + size_block_h


@pytest.mark.parametrize(
    "size1, size2, expected_declared, expected_locked",
    [
        pytest.param(
            size_block_a,
            size_block_b,
            size_block_a.declared - size_block_b.declared,
            size_block_a.locked - size_block_b.locked,
            id="both-declared-and-locked",
        ),
        pytest.param(
            size_block_c,
            size_block_d,
            size_block_c.declared - size_block_d.declared,
            None,
            id="only-declared",
        ),
        pytest.param(
            size_block_h,
            size_block_i,
            None,
            size_block_h.locked - size_block_i.locked,
            id="only-locked",
        ),
    ],
)
def test_size_block_subtraction(
    size1: SizeBlock, size2: SizeBlock, expected_declared: SizePair | None, expected_locked: SizePair | None
) -> None:
    result = size1 - size2

    assert result.declared == expected_declared
    assert result.locked == expected_locked


def test_size_block_subtraction_error() -> None:
    with pytest.raises(ValueError):
        size_block_d - size_block_h


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


# --------- PlatformSize ---------
def test_platform_size_subtraction() -> None:
    platform_size_a = PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_c + size_block_d)
    platform_size_b = PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_c)

    assert platform_size_a - platform_size_b == PlatformSize(
        platform="linux-aarch64", python_version="3.12", size=size_block_d
    )


def test_platform_size_subtraction_error() -> None:
    with pytest.raises(ValueError):
        PlatformSize(platform="linux-aarch64", python_version="3.12", size=size_block_c + size_block_d) - PlatformSize(
            platform="linux-x86_64", python_version="3.12", size=size_block_c
        )


# --------- CommitSize ---------
def test_commit_size_filter() -> None:
    result = commit_size_a.filter(platform="linux-aarch64", python_version="3.12")

    assert result == [module_size_a, module_size_b]


def test_commit_size_filter_none() -> None:
    result = commit_size_a.filter(platform="linux-aarch64", python_version="3.12", name="fake-name")
    assert result == []
