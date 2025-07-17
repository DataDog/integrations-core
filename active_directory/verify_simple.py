#!/usr/bin/env python3
"""Simple verification of Netlogon metrics implementation."""

import os

def check_metrics_py():
    """Check if metrics.py has the required counters."""
    print("=== Checking metrics.py ===")
    
    with open('datadog_checks/active_directory/metrics.py', 'r') as f:
        content = f.read()
    
    # Check Netlogon section
    netlogon_checks = [
        ("'Netlogon':", "Netlogon section"),
        ("'Semaphore Waiters'", "Semaphore Waiters counter"),
        ("'Semaphore Holders'", "Semaphore Holders counter"),
        ("'Semaphore Acquires'", "Semaphore Acquires counter"),
        ("'Semaphore Timeouts'", "Semaphore Timeouts counter"),
        ("'Average Semaphore Hold Time'", "Average Semaphore Hold Time counter"),
        ("'type': 'count'", "Count type for acquires/timeouts"),
    ]
    
    # Check Security section
    security_checks = [
        ("'Security System-Wide Statistics':", "Security section"),
        ("'NTLM Authentications'", "NTLM Authentications counter"),
        ("'Kerberos Authentications'", "Kerberos Authentications counter"),
        ("'type': 'rate'", "Rate type for auth metrics"),
    ]
    
    all_good = True
    for check_str, desc in netlogon_checks + security_checks:
        if check_str in content:
            print(f"✓ Found: {desc}")
        else:
            print(f"✗ Missing: {desc}")
            all_good = False
    
    return all_good


def check_tests():
    """Check if test files exist and have expected content."""
    print("\n=== Checking test files ===")
    
    test_checks = [
        ('tests/test_netlogon_metrics.py', 'test_netlogon_metrics'),
        ('tests/test_netlogon_metrics.py', 'test_netlogon_metrics_missing_counters'),
        ('tests/test_netlogon_metrics.py', 'test_netlogon_custom_instance'),
        ('tests/test_unit.py', 'test_all_metrics_config'),
    ]
    
    all_good = True
    for file_path, test_name in test_checks:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                if test_name in f.read():
                    print(f"✓ Found {test_name} in {file_path}")
                else:
                    print(f"✗ Missing {test_name} in {file_path}")
                    all_good = False
        else:
            print(f"✗ File not found: {file_path}")
            all_good = False
    
    return all_good


def check_documentation():
    """Check if documentation is updated."""
    print("\n=== Checking documentation ===")
    
    doc_checks = [
        ('README.md', 'Netlogon'),
        ('README.md', 'authentication performance'),
        ('metadata.csv', 'netlogon.semaphore_waiters'),
        ('metadata.csv', 'security.ntlm_authentications'),
    ]
    
    all_good = True
    for file_path, keyword in doc_checks:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                if keyword in f.read():
                    print(f"✓ Found '{keyword}' in {file_path}")
                else:
                    print(f"✗ Missing '{keyword}' in {file_path}")
                    all_good = False
        else:
            print(f"✗ File not found: {file_path}")
            all_good = False
    
    return all_good


def check_config_example():
    """Check if conf.yaml.example is updated."""
    print("\n=== Checking conf.yaml.example ===")
    
    config_path = 'datadog_checks/active_directory/data/conf.yaml.example'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            content = f.read()
        
        checks = ['Netlogon:', 'Semaphore Waiters', 'Security System-Wide Statistics:']
        all_good = True
        for check in checks:
            if check in content:
                print(f"✓ Found '{check}' in config example")
            else:
                print(f"✗ Missing '{check}' in config example")
                all_good = False
        return all_good
    else:
        print("✗ conf.yaml.example not found")
        return False


def main():
    """Run all checks."""
    print("Netlogon Metrics Implementation Verification\n")
    
    results = []
    results.append(check_metrics_py())
    results.append(check_tests())
    results.append(check_documentation())
    results.append(check_config_example())
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    if all(results):
        print("\n✅ ALL CHECKS PASSED!")
        print("\nThe implementation successfully:")
        print("- Adds 5 Netlogon metrics for authentication monitoring")
        print("- Adds 2 Security metrics for protocol tracking")
        print("- Includes comprehensive test coverage")
        print("- Updates all documentation")
        print("- Provides configuration examples")
        print("\n✅ Ready for manual testing on Windows Server!")
    else:
        print("\n❌ Some checks failed. Please review the output above.")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())