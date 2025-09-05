from ddev.cli.size.utils.gha_diff import calculate_diffs


def get_test_sizes():
    prev_compressed_sizes = [
        {
            "Name": "packageA",
            "Version": "1.0.0",
            "Size_Bytes": 1000,
            "Size": "1.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 2000,
            "Size": "2.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Size_Bytes": 3072,  # Removed package
            "Size": "3.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
    ]
    curr_compressed_sizes = [
        {
            "Name": "packageA",
            "Version": "1.0.1",
            "Size_Bytes": 1500,  # Changed size and version
            "Size": "1.50 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 2500,  # Changed size, same version
            "Size": "2.50 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageD",
            "Version": "4.0.0",
            "Size_Bytes": 4000,  # Added package
            "Size": "4.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
    ]

    prev_uncompressed_sizes = [
        {
            "Name": "packageA",
            "Version": "1.0.0",
            "Size_Bytes": 2000,  # 2x compressed size
            "Size": "2.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 4000,  # 2x compressed size
            "Size": "4.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Size_Bytes": 6144,  # 2x compressed size
            "Size": "6.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
    ]
    curr_uncompressed_sizes = [
        {
            "Name": "packageA",
            "Version": "1.0.1",
            "Size_Bytes": 3000,  # 2x compressed size
            "Size": "3.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 5000,  # 2x compressed size
            "Size": "5.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageD",
            "Version": "4.0.0",
            "Size_Bytes": 8000,  # 2x compressed size
            "Size": "8.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
    ]

    return prev_compressed_sizes, curr_compressed_sizes, prev_uncompressed_sizes, curr_uncompressed_sizes


def test_calculate_diffs():
    prev_compressed_sizes, curr_compressed_sizes, prev_uncompressed_sizes, curr_uncompressed_sizes = get_test_sizes()

    diffs, platform, python_version = calculate_diffs(
        prev_compressed_sizes, curr_compressed_sizes, prev_uncompressed_sizes, curr_uncompressed_sizes
    )
    print(diffs)
    assert diffs['added'] == [
        {
            "Name": "packageD",
            "Version": "4.0.0",
            "Compressed_Size_Bytes": 4000,  # Added package
            "Size": "4.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
            "Uncompressed_Size_Bytes": 8000,
        }
    ]
    assert diffs['removed'] == [
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Compressed_Size_Bytes": 3072,
            "Size": "3.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
            "Uncompressed_Size_Bytes": 6144,
        }
    ]
    assert diffs['changed'] == [
        {
            "Name": "packageA",
            "Version": "1.0.1",
            "Prev Version": "1.0.0",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
            "Type": "Dependency",
            "Prev_Size_Bytes": 1000,
            "Curr_Size_Bytes": 1500,
            "Compressed_Diff": 500,
            "Uncompressed_Diff": 1000,
            "Compressed_Percentage": 50.0,
            "Uncompressed_Percentage": 50.0,
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Prev Version": "2.0.0",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
            "Type": "Dependency",
            "Prev_Size_Bytes": 2000,
            "Curr_Size_Bytes": 2500,
            "Compressed_Diff": 500,
            "Uncompressed_Diff": 1000,
            "Compressed_Percentage": 25.0,
            "Uncompressed_Percentage": 25.0,
        },
    ]
    assert diffs['total_diff'] == 1928
    assert platform == 'test-platform'
    assert python_version == '3.x.x'
