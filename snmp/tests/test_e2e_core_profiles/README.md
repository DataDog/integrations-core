# E2E core profiles

`test_e2e_core_profiles` is used to test profiles against the SNMP corecheck integration.

The folder contains profile tests with one file for each profile. For example:

```
test_e2e_core_profiles/test_profile_3com.py
test_e2e_core_profiles/test_profile_3com_huawei.py
test_e2e_core_profiles/test_profile_cisco.py
test_e2e_core_profiles/test_profile_cisco_3850.py
```

Each profile test file will assert both metrics and metadata.

(About old profile tests written for python, we can be migrated later if needed.)
