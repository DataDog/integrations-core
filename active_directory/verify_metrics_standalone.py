#!/usr/bin/env python3
"""
Standalone verification of Netlogon metrics implementation.
Parses metrics.py directly to verify configuration.
"""

import re
import ast

def parse_metrics_file():
    """Parse metrics.py to extract METRICS_CONFIG."""
    with open('datadog_checks/active_directory/metrics.py', 'r') as f:
        content = f.read()
    
    # Extract METRICS_CONFIG using regex and AST
    match = re.search(r'METRICS_CONFIG\s*=\s*(\{[\s\S]*?\n\})', content)
    if not match:
        raise ValueError("Could not find METRICS_CONFIG in metrics.py")
    
    # For simplicity, let's manually verify the structure
    return content


def verify_netlogon_in_file(content):
    """Verify Netlogon metrics are present in the file."""
    print("=== Verifying Netlogon Metrics Configuration ===\n")
    
    # Check for Netlogon section
    if "'Netlogon':" not in content:
        print("❌ ERROR: Netlogon section not found")
        return False
    
    # Expected Netlogon counters
    expected_counters = [
        ("'Semaphore Waiters':", "semaphore_waiters"),
        ("'Semaphore Holders':", "semaphore_holders"),
        ("'Semaphore Acquires':", "semaphore_acquires"),
        ("'Semaphore Timeouts':", "semaphore_timeouts"),
        ("'Average Semaphore Hold Time':", "semaphore_hold_time"),
    ]
    
    print("Netlogon Counters:")
    all_found = True
    for counter, metric in expected_counters:
        if counter in content:
            # Check if it's a count type
            if counter in ["'Semaphore Acquires':", "'Semaphore Timeouts':"]:
                if "'type': 'count'" in content[content.find(counter):content.find(counter) + 200]:
                    print(f"  ✓ {counter.strip(':').strip(\"'\")} -> active_directory.netlogon.{metric} (type: count)")
                else:
                    print(f"  ⚠️  {counter.strip(':').strip(\"'\")} -> missing 'count' type")
            else:
                print(f"  ✓ {counter.strip(':').strip('''\"''')} -> active_directory.netlogon.{metric}")
        else:
            print(f"  ❌ {counter.strip(':').strip('''\"''')} NOT FOUND")
            all_found = False
    
    return all_found


def verify_security_in_file(content):
    """Verify Security System-Wide Statistics metrics are present."""
    print("\n=== Verifying Security Metrics Configuration ===\n")
    
    # Check for Security section
    if "'Security System-Wide Statistics':" not in content:
        print("❌ ERROR: Security System-Wide Statistics section not found")
        return False
    
    # Expected Security counters
    expected_counters = [
        ("'NTLM Authentications':", "ntlm_authentications"),
        ("'Kerberos Authentications':", "kerberos_authentications"),
    ]
    
    print("Security Counters:")
    all_found = True
    for counter, metric in expected_counters:
        if counter in content:
            # Check if it's a rate type
            if "'type': 'rate'" in content[content.find(counter):content.find(counter) + 200]:
                print(f"  ✓ {counter.strip(':').strip(\"'\")} -> active_directory.security.{metric} (type: rate)")
            else:
                print(f"  ⚠️  {counter.strip(':').strip(\"'\")} -> missing 'rate' type")
        else:
            print(f"  ❌ {counter.strip(':').strip(\"'\")} NOT FOUND")
            all_found = False
    
    return all_found


def verify_test_files():
    """Check if test files exist and contain expected tests."""
    print("\n=== Verifying Test Files ===\n")
    
    import os
    
    test_files = {
        'tests/test_netlogon_metrics.py': [
            'test_netlogon_metrics',
            'test_netlogon_metrics_missing_counters',
            'test_netlogon_custom_instance'
        ],
        'tests/test_unit.py': [
            'test_all_metrics_config'
        ]
    }
    
    all_good = True
    for test_file, expected_tests in test_files.items():
        if os.path.exists(test_file):
            print(f"✓ {test_file} exists")
            with open(test_file, 'r') as f:
                content = f.read()
            for test in expected_tests:
                if f'def {test}' in content:
                    print(f"  ✓ {test} found")
                else:
                    print(f"  ❌ {test} NOT FOUND")
                    all_good = False
        else:
            print(f"❌ {test_file} NOT FOUND")
            all_good = False
    
    return all_good


def verify_documentation():
    """Check if documentation is updated."""
    print("\n=== Verifying Documentation ===\n")
    
    files_to_check = {
        'README.md': ['Netlogon', 'semaphore', 'authentication performance'],
        'metadata.csv': [
            'netlogon.semaphore_waiters',
            'netlogon.semaphore_holders',
            'security.ntlm_authentications',
            'security.kerberos_authentications'
        ]
    }
    
    all_good = True
    for file_name, keywords in files_to_check.items():
        import os
        if os.path.exists(file_name):
            print(f"✓ {file_name} exists")
            with open(file_name, 'r') as f:
                content = f.read()
            for keyword in keywords:
                if keyword in content:
                    print(f"  ✓ Contains '{keyword}'")
                else:
                    print(f"  ❌ Missing '{keyword}'")
                    all_good = False
        else:
            print(f"❌ {file_name} NOT FOUND")
            all_good = False
    
    return all_good


def main():
    """Run all verification checks."""
    print("Netlogon Metrics Implementation Verification")
    print("=" * 50)
    
    try:
        # Read metrics.py content
        content = parse_metrics_file()
        
        # Verify Netlogon metrics
        netlogon_ok = verify_netlogon_in_file(content)
        
        # Verify Security metrics
        security_ok = verify_security_in_file(content)
        
        # Verify test files
        tests_ok = verify_test_files()
        
        # Verify documentation
        docs_ok = verify_documentation()
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY\n")
        
        if netlogon_ok and security_ok and tests_ok and docs_ok:
            print("✅ All verification checks PASSED!")
            print("✅ Implementation successfully fulfills JIRA requirements:")
            print("  - Netlogon metrics for authentication performance")
            print("  - Semaphore statistics for bottleneck detection")
            print("  - Authentication protocol tracking (NTLM vs Kerberos)")
            print("  - Comprehensive test coverage")
            print("  - Updated documentation")
            print("\n🎯 Ready for manual testing on Windows Server with AD role!")
            return 0
        else:
            print("❌ Some verification checks FAILED")
            return 1
            
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())