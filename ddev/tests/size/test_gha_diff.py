from ddev.cli.size.utils.gha_diff import calculate_diffs, display_diffs


def get_test_sizes():
    prev_sizes = [
        {
            "Name": "packageA",
            "Version": "1.0.0",
            "Size_Bytes": 1000,
            "Size": "1.00 KB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 2000,
            "Size": "2.00 KB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Size_Bytes": 3000,  # Removed package
            "Size": "3.00 KB",
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
            "Size": "1.50 KB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageB",
            "Version": "2.0.0",
            "Size_Bytes": 2500,  # Changed size, same version
            "Size": "2.50 KB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        },
        {
            "Name": "packageD",
            "Version": "4.0.0",
            "Size_Bytes": 4000,  # Added package
            "Size": "4.00 KB",
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
            "Size": "4.00 KB",
            "Type": "Dependency",
            "Platform": "test-platform",
            "Python_Version": "3.x.x",
        }
    ]
    assert diffs['removed'] == [
        {
            "Name": "packageC",
            "Version": "3.0.0",
            "Size_Bytes": 3000,
            "Size": "3.00 KB",
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
    assert diffs['total_diff'] == 2000
    assert platform == 'test-platform'
    assert python_version == '3.x.x'


def test_display_diffs():
    prev_sizes, curr_sizes = get_test_sizes()
    diffs, platform, python_version = calculate_diffs(prev_sizes, curr_sizes)
    import io
    import sys

    captured_output = io.StringIO()
    sys_stdout = sys.stdout
    sys.stdout = captured_output
    try:
        display_diffs(diffs, platform, python_version)
    finally:
        sys.stdout = sys_stdout

    output = captured_output.getvalue()
    # Check that the output contains expected lines
    assert "Dependency Size Differences for test-platform and Python 3.x.x" in output
    assert "Total size difference: +1.95 KB" in output
    assert "Added:" in output
    assert "  + [Dependency] packageD 4.0.0: +4.00 KB" in output
    assert "Removed:" in output
    assert "  - [Dependency] packageC 3.0.0: -3.00 KB" in output
    assert "Changed:" in output
    assert "  * [Dependency] packageA (1.0.0 -> 1.0.1): +500 B (+50.00%)" in output
    assert "  * [Dependency] packageB (2.0.0): +500 B (+25.00%)" in output
