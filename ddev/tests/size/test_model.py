# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.cli.size.utils.size_model import Size, Sizes, convert_to_human_readable_size


@pytest.fixture
def example_sizes() -> Sizes:
    data = [
        Size(
            name="core",
            version="1.2.3",
            size_bytes=1000,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.12",
        ),
        Size(
            name="netutils",
            version="2.0.0",
            size_bytes=800,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.11",
        ),
        Size(
            name="requests",
            version="2.29.0",
            size_bytes=500,
            type="Dependency",
            platform="linux-x86_64",
            python_version="3.12",
        ),
        Size(
            name="pywin32",
            version="301",
            size_bytes=1200,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.12",
        ),
        Size(
            name="core",
            version="1.2.3",
            size_bytes=1111,
            type="Integration",
            platform="macos-x86_64",
            python_version="3.12",
        ),
        Size(
            name="mymodule",
            version="0.1.0",
            size_bytes=555,
            type="Integration",
            platform="macos-aarch64",
            python_version="3.11",
        ),
        Size(
            name="cryptography",
            version="39.0.1",
            size_bytes=3300,
            type="Dependency",
            platform="linux-aarch64",
            python_version="3.12",
        ),
        Size(
            name="setuptools",
            version="68.2.2",
            size_bytes=800,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.10",
        ),
        Size(
            name="pip",
            version="23.0",
            size_bytes=400,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.10",
        ),
    ]
    return Sizes(data)


@pytest.mark.parametrize(
    "platform, python_version, type, expected_sizes",
    [
        pytest.param(
            "linux-x86_64",
            "3.12",
            None,
            Sizes(
                [
                    Size(
                        name="core",
                        version="1.2.3",
                        size_bytes=1000,
                        type="Integration",
                        platform="linux-x86_64",
                        python_version="3.12",
                    ),
                    Size(
                        name="requests",
                        version="2.29.0",
                        size_bytes=500,
                        type="Dependency",
                        platform="linux-x86_64",
                        python_version="3.12",
                    ),
                ]
            ),
            id="linux-x86_64-3.12",
        ),
        pytest.param(
            "windows-x86_64",
            "3.10",
            "Dependency",
            Sizes(
                [
                    Size(
                        name="setuptools",
                        version="68.2.2",
                        size_bytes=800,
                        type="Dependency",
                        platform="windows-x86_64",
                        python_version="3.10",
                    ),
                    Size(
                        name="pip",
                        version="23.0",
                        size_bytes=400,
                        type="Dependency",
                        platform="windows-x86_64",
                        python_version="3.10",
                    ),
                ]
            ),
            id="windows-x86_64-3.10-Dependency",
        ),
    ],
)
def test_filter(example_sizes: Sizes, platform: str, python_version: str, type: str | None, expected_sizes: Sizes):
    sizes = example_sizes.filter(platform=platform, python_version=python_version, type=type)
    assert sizes == expected_sizes


def test_get_size(example_sizes: Sizes):
    size = example_sizes.get_size(platform="linux-x86_64", python_version="3.12", type="Integration", name="core")
    assert size == Size(
        name="core",
        version="1.2.3",
        size_bytes=1000,
        type="Integration",
        platform="linux-x86_64",
        python_version="3.12",
    )


def test_get_dictionary(example_sizes: Sizes):
    dictionary = example_sizes.get_dictionary()
    assert dictionary == {
        ("core", "Integration", "linux-x86_64", "3.12"): Size(
            name="core",
            version="1.2.3",
            size_bytes=1000,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.12",
        ),
        ("netutils", "Integration", "linux-x86_64", "3.11"): Size(
            name="netutils",
            version="2.0.0",
            size_bytes=800,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.11",
        ),
        ("requests", "Dependency", "linux-x86_64", "3.12"): Size(
            name="requests",
            version="2.29.0",
            size_bytes=500,
            type="Dependency",
            platform="linux-x86_64",
            python_version="3.12",
        ),
        ("pywin32", "Dependency", "windows-x86_64", "3.12"): Size(
            name="pywin32",
            version="301",
            size_bytes=1200,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.12",
        ),
        ("core", "Integration", "macos-x86_64", "3.12"): Size(
            name="core",
            version="1.2.3",
            size_bytes=1111,
            type="Integration",
            platform="macos-x86_64",
            python_version="3.12",
        ),
        ("mymodule", "Integration", "macos-aarch64", "3.11"): Size(
            name="mymodule",
            version="0.1.0",
            size_bytes=555,
            type="Integration",
            platform="macos-aarch64",
            python_version="3.11",
        ),
        ("cryptography", "Dependency", "linux-aarch64", "3.12"): Size(
            name="cryptography",
            version="39.0.1",
            size_bytes=3300,
            type="Dependency",
            platform="linux-aarch64",
            python_version="3.12",
        ),
        ("setuptools", "Dependency", "windows-x86_64", "3.10"): Size(
            name="setuptools",
            version="68.2.2",
            size_bytes=800,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.10",
        ),
        ("pip", "Dependency", "windows-x86_64", "3.10"): Size(
            name="pip",
            version="23.0",
            size_bytes=400,
            type="Dependency",
            platform="windows-x86_64",
            python_version="3.10",
        ),
    }


@pytest.mark.parametrize(
    "new_size",
    [
        pytest.param(
            Size(
                name="new",
                version="1.0.0",
                size_bytes=1000,
                type="Integration",
                platform="linux-x86_64",
                python_version="3.12",
            ),
            id="append-existing-platform",
        ),
        pytest.param(
            Size(
                name="new-module",
                version="1.0.0",
                size_bytes=1000,
                type="Integration",
                platform="new-platform",
                python_version="3.13",
            ),
            id="append-new-platform",
        ),
    ],
)
def test_append(example_sizes: Sizes, new_size: Size):
    new_sizes = Sizes(example_sizes.root.copy())
    new_sizes.append(new_size)

    assert len(new_sizes.root) == len(example_sizes.root) + 1
    assert new_sizes.root[-1] == new_size
    assert (
        new_sizes._total_sizes[new_size.platform][new_size.python_version]
        == example_sizes._total_sizes[new_size.platform][new_size.python_version] + new_size.size_bytes
    )


def test_diff_no_changes(example_sizes: Sizes):
    diff = example_sizes.diff(example_sizes)
    assert len(diff.filter(delta_type="Unchanged")) == len(example_sizes)
    assert len(diff.filter(delta_type="Modified")) == 0
    assert len(diff.filter(delta_type="New")) == 0
    assert len(diff.filter(delta_type="Removed")) == 0


def test_diff_with_changes(example_sizes: Sizes):
    modified_sizes = Sizes([])
    for size in example_sizes.root:
        if size.name == "pip":
            # Modify pip size
            modified_sizes.append(
                Size(
                    name=size.name,
                    version="23.1",  # New version
                    size_bytes=size.size_bytes + 100,  # Increased size
                    type=size.type,
                    platform=size.platform,
                    python_version=size.python_version,
                )
            )
        elif size.name == "setuptools":
            # Exclude setuptools to simulate removal
            continue
        else:
            modified_sizes.append(size)
    # Add a new integration
    modified_sizes.append(
        Size(
            name="http",
            version="2.0.0",
            size_bytes=900,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.10",
        )
    )

    diff = modified_sizes.diff(example_sizes)

    pip_diff = diff.filter(name="pip")
    assert len(pip_diff) == 1
    assert pip_diff.root[0].delta_type == "Modified"
    assert pip_diff.root[0].size_bytes == 100
    assert pip_diff.root[0].version == "23.0 -> 23.1"

    setuptools_diff = diff.filter(name="setuptools")
    assert len(setuptools_diff) == 1
    assert setuptools_diff.root[0].delta_type == "Removed"

    http_diff = diff.filter(name="http")
    assert len(http_diff) == 1
    assert http_diff.root[0].delta_type == "New"

    unchanged = diff.filter(delta_type="Unchanged")
    untouched_names = {s.name for s in unchanged.root}
    assert sorted(untouched_names) == ["core", "cryptography", "mymodule", "netutils", "pywin32", "requests"]

    modified = diff.filter(delta_type="Modified")
    new = diff.filter(delta_type="New")
    removed = diff.filter(delta_type="Removed")
    assert len(modified) == 1
    assert len(new) == 1
    assert len(removed) == 1
    assert len(unchanged) == 7


def test_add(example_sizes: Sizes):
    new_sizes = example_sizes + example_sizes
    assert len(new_sizes) == len(example_sizes) * 2
    assert new_sizes.root == example_sizes.root * 2
    assert new_sizes._platforms == example_sizes._platforms | example_sizes._platforms
    assert new_sizes._python_versions == example_sizes._python_versions
    for platform in example_sizes._platforms:
        for python_version in example_sizes._python_versions:
            assert (
                new_sizes._total_sizes[platform][python_version]
                == example_sizes._total_sizes[platform][python_version] * 2
            )


def test_len(example_sizes: Sizes):
    assert len(example_sizes) == len(example_sizes.root)


def test_len_empty_sizes():
    assert not Sizes([])


@pytest.mark.parametrize(
    "sizes, expected_len",
    [
        pytest.param(Sizes([]), 0, id="empty"),
        pytest.param(
            Sizes(
                [
                    Size(
                        name="core",
                        version="1.2.3",
                        size_bytes=0,
                        type="Integration",
                        platform="linux-x86_66",
                        python_version="3.12",
                    )
                ]
            ),
            0,
            id="zero-sized",
        ),
    ],
)
def test_len_non_zero_none(sizes: Sizes, expected_len: int):
    assert sizes.len_non_zero() == expected_len


def test_len_non_zero_no_zeros(example_sizes: Sizes):
    assert example_sizes.len_non_zero() == len(example_sizes)


def test_len_non_zero_with_zeros(example_sizes: Sizes):
    example_sizes.append(
        Size(
            name="core",
            version="1.2.3",
            size_bytes=0,
            type="Integration",
            platform="linux-x86_64",
            python_version="3.12",
        )
    )
    assert example_sizes.len_non_zero() == len(example_sizes) - 1


@pytest.mark.parametrize(
    "size_bytes, expected_string",
    [
        pytest.param(500, "500 B", id="Bytes"),
        pytest.param(1024, "1.00 KiB", id="KiB"),
        pytest.param(1048576, "1.00 MiB", id="MiB"),
        pytest.param(1073741824, "1.00 GiB", id="GiB"),
    ],
)
def test_convert_to_human_readable_size(size_bytes, expected_string):
    assert convert_to_human_readable_size(size_bytes) == expected_string
