# Netlogon Metrics Implementation Summary

## Overview
This implementation adds Netlogon and Security System-Wide Statistics metrics to the Active Directory integration, addressing the feature request for monitoring authentication performance and DC secure channel health.

## Changes Made

### 1. Metrics Configuration (`datadog_checks/active_directory/metrics.py`)
Added two new performance objects to `METRICS_CONFIG`:

- **Netlogon**: 5 metrics for monitoring authentication semaphore performance
  - `semaphore_waiters` (gauge)
  - `semaphore_holders` (gauge)
  - `semaphore_acquires` (count)
  - `semaphore_timeouts` (count)
  - `semaphore_hold_time` (gauge)

- **Security System-Wide Statistics**: 2 metrics for authentication protocol tracking
  - `ntlm_authentications` (rate)
  - `kerberos_authentications` (rate)

### 2. Configuration Example (`datadog_checks/active_directory/data/conf.yaml.example`)
Added documented configuration examples showing how to:
- Enable Netlogon metrics collection
- Configure instance filtering
- Add custom Netlogon counters via extra_metrics

### 3. Tests
- Created comprehensive unit tests in `tests/test_netlogon_metrics.py`:
  - Test basic Netlogon metrics collection
  - Test graceful handling when counters are unavailable
  - Test custom instance filtering
- Updated `tests/common.py` to include Netlogon and Security objects
- Enhanced `tests/test_unit.py` with comprehensive METRICS_CONFIG validation

### 4. Documentation
- Updated `README.md` with:
  - List of performance objects collected
  - Detailed explanation of Netlogon metrics
  - Use cases for authentication monitoring
- Updated `metadata.csv` with all 7 new metrics including proper types, units, and descriptions

## Metrics Details

### Netlogon Metrics (5)
1. `active_directory.netlogon.semaphore_waiters` - Threads waiting for authentication
2. `active_directory.netlogon.semaphore_holders` - Threads processing authentication
3. `active_directory.netlogon.semaphore_acquires` - Total semaphore acquisitions
4. `active_directory.netlogon.semaphore_timeouts` - Authentication timeout count
5. `active_directory.netlogon.semaphore_hold_time` - Average processing time

### Security Metrics (2)
1. `active_directory.security.ntlm_authentications` - NTLM auth rate
2. `active_directory.security.kerberos_authentications` - Kerberos auth rate

## Use Cases Addressed
- Monitor authentication bottlenecks from Cisco ISE NAC devices
- Track authentication processing times
- Identify when MaxConcurrentApi tuning is needed
- Monitor authentication protocol usage (NTLM vs Kerberos)
- Detect authentication timeouts and failures

## Testing Requirements
1. Run unit tests: `ddev test active_directory`
2. Run linting: `ddev lint active_directory`
3. Manual testing on Windows Server with AD role:
   - Verify all 7 metrics appear in Datadog
   - Generate authentication load to see metrics respond
   - Test with different instance configurations

## Next Steps
1. Complete manual testing on Windows Server environment
2. Create pull request with test results
3. Consider future enhancements:
   - DC Locator metrics for Windows Server 2025
   - Additional authentication failure tracking
   - Custom alerting thresholds