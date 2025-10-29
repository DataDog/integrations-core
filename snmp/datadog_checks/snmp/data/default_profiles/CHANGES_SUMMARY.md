# SNMP Profiles Reorganization - Changes Summary

## Overview

Reorganized Cisco SNMP profiles to introduce the **metric packs** architecture with a clear separation between generic (vendor-agnostic) and vendor-specific metric definitions.

## What Changed

### 1. Created Generic Metric Packs Folder

**Location**: `default_profiles/generic/metric_packs/`

**Contains 7 vendor-agnostic metric packs:**
- `base.yaml` - SNMPv2-MIB system information
- `interfaces.yaml` - IF-MIB interface metrics
- `tcp.yaml` - TCP-MIB protocol metrics
- `udp.yaml` - UDP-MIB protocol metrics
- `ip.yaml` - IP-MIB protocol metrics
- `ospf.yaml` - OSPF-MIB routing metrics
- `bgp.yaml` - BGP4-MIB routing metrics

These metric packs use **standard IETF MIBs** and can be reused across devices from any vendor.

### 2. Created Cisco-Specific Structure

**Location**: `default_profiles/cisco/`

**Contains:**
- `metric_packs/` - 17 Cisco-specific metric pack files
- `profiles/` - 23 device profile files
- `README.md` - Comprehensive documentation
- `PROFILE_MAPPING.md` - Profile to metric pack mappings

### 3. Updated All Cisco Profiles

All 23 Cisco profiles were updated to reference generic metric packs using relative paths:

**Before:**
```yaml
metric_packs:
  - base
  - interfaces
  - tcp
```

**After:**
```yaml
metric_packs:
  - ../../generic/metric_packs/base
  - ../../generic/metric_packs/interfaces
  - ../../generic/metric_packs/tcp
```

### 4. Created Documentation

**Created:**
- `generic/README.md` - Documentation for generic metric packs
- Updated `cisco/README.md` - Added distinction between generic and Cisco-specific packs
- Updated `cisco/PROFILE_MAPPING.md` - Added MIB references and split by pack type

## File Count Summary

| Category | Count | Location |
|----------|-------|----------|
| Generic metric packs | 7 | `generic/metric_packs/` |
| Cisco-specific metric packs | 17 | `cisco/metric_packs/` |
| Cisco profiles | 23 | `cisco/profiles/` |
| Documentation files | 4 | Various |
| **Total files** | **51** | |

## Benefits of This Structure

### 1. Reusability
Generic metric packs can now be used by profiles for **any vendor** (HP, Juniper, Arista, etc.)

### 2. Clarity
Clear separation between:
- Standard MIB-based metrics (generic)
- Vendor proprietary MIB metrics (vendor-specific)

### 3. Maintainability
- Update standard metrics once in `generic/`
- Apply automatically to all vendor profiles

### 4. Extensibility
Easy to add new vendors by:
1. Referencing generic metric packs
2. Adding vendor-specific packs as needed

### 5. Standards Compliance
Generic packs explicitly use IETF standard MIBs with RFC references

## Migration Path for Other Vendors

When creating profiles for other vendors (e.g., HP, Juniper, Arista):

```
default_profiles/
├── generic/
│   └── metric_packs/          # Reuse these
├── cisco/
│   ├── metric_packs/          # Cisco-specific
│   └── profiles/
├── hp/                         # New vendor
│   ├── metric_packs/          # HP-specific only
│   └── profiles/
│       └── hp-procurve.yaml   # References ../../generic/metric_packs/*
└── juniper/                    # New vendor
    ├── metric_packs/          # Juniper-specific only
    └── profiles/
        └── juniper-mx.yaml    # References ../../generic/metric_packs/*
```

## Standard MIBs in Generic Packs

All generic metric packs use industry-standard MIBs:

| Metric Pack | MIB | RFC |
|-------------|-----|-----|
| base | SNMPv2-MIB | RFC 3418 |
| interfaces | IF-MIB | RFC 2863 |
| tcp | TCP-MIB | RFC 4022 |
| udp | UDP-MIB | RFC 4113 |
| ip | IP-MIB | RFC 4293 |
| ospf | OSPF-MIB | RFC 4750 |
| bgp | BGP4-MIB | RFC 4273 |

## Example Profile

```yaml
# cisco/profiles/cisco-catalyst.yaml
device:
  vendor: "cisco"

metadata:
  device:
    fields:
      type:
        value: "switch"

metric_packs:
  # Generic (standard MIBs)
  - ../../generic/metric_packs/base
  - ../../generic/metric_packs/interfaces
  - ../../generic/metric_packs/tcp
  - ../../generic/metric_packs/udp
  - ../../generic/metric_packs/ip
  - ../../generic/metric_packs/ospf
  - ../../generic/metric_packs/bgp
  
  # Cisco-specific (proprietary MIBs)
  - metadata
  - cpu
  - memory
  - environment
  - stackwise

sysobjectid:
  - 1.3.6.1.4.1.9.1.696
```

## Next Steps

### For New Vendors
1. Create vendor folder: `default_profiles/<vendor>/`
2. Reference generic metric packs with relative paths
3. Add vendor-specific metric packs as needed
4. Create profiles for specific device models

### For Existing Vendors
Consider migrating other vendor profiles (if any exist) to use the same structure with generic metric packs.

## Backward Compatibility

The changes maintain full backward compatibility:
- Original `_generic-*.yaml` profiles still exist
- Generic metric packs reference these via `extends:`
- No changes to actual metric definitions or OIDs
- Profile matching logic unchanged (sysObjectID)

