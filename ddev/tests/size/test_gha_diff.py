from ddev.cli.size.utils.gha_diff import calculate_diffs


def get_test_sizes():
    prev_sizes = [
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
    curr_sizes = [
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
    return prev_sizes, curr_sizes


def test_calculate_diffs():
    prev_sizes, curr_sizes = get_test_sizes()

    diffs, platform, python_version = calculate_diffs(prev_sizes, curr_sizes)
    print(diffs)
    assert diffs['added'] == [
        {
            "Name": "packageD",
            "Version": "4.0.0",
            "Size_Bytes": 4000,  # Added package
            "Size": "4.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        }
    ]
    assert diffs['removed'] == [
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Size_Bytes": 3072,
            "Size": "3.00 KiB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
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
            "Diff": 500,
            "Percentage": 50,
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
            "Diff": 500,
            "Percentage": 25,
        },
    ]
    assert diffs['total_diff'] == 1928
    assert platform == 'test-platform'
    assert python_version == '3.x.x'
