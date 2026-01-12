# MySQL Schema Collection Backward Compatibility Plan

## Context
Branch: `seth.samuel/DBMON-5801-move-my-sql-to-new-schema-collector` introduced a new schema collection method that uses MySQL 8+ JSON functions (`json_arrayagg`, `json_object`). This breaks compatibility with older MySQL versions.

**Target Branch:** `eric.weaver/DBMON-6038`

## Problem
- New method uses `json_arrayagg()` and `json_object()` (MySQL 8.0.19+, MariaDB 10.5.0+)
- Legacy method works with all MySQL/MariaDB versions
- Need to support both old and new versions

## Version Requirements
- **New method:** MySQL >= 8.0.19, MariaDB >= 10.5.0
- **Legacy method:** All older versions

## File Changes Summary
- **Deleted:** `mysql/datadog_checks/mysql/databases_data.py` (448 lines) - legacy approach
- **Added:** `mysql/datadog_checks/mysql/schemas.py` (256 lines) - new approach
- **Modified:** `mysql/datadog_checks/mysql/metadata.py` - integration point
- **Modified:** `mysql/datadog_checks/mysql/queries.py` - query definitions

---

## Implementation Checklist

### ☐ Setup: Merge Changes
**Status:** Pending
**Branch:** Switch to `eric.weaver/DBMON-6038` and merge `seth.samuel/DBMON-5801-move-my-sql-to-new-schema-collector`

**Actions:**
```bash
git checkout eric.weaver/DBMON-6038
git merge seth.samuel/DBMON-5801-move-my-sql-to-new-schema-collector
```

---

### ☐ Commit 1: Create schemas_legacy.py
**Status:** Pending
**Description:** Preserve the legacy collection method by recreating the deleted `databases_data.py` as `schemas_legacy.py`

**Actions:**
1. Extract `databases_data.py` from `origin/master`
2. Save as `mysql/datadog_checks/mysql/schemas_legacy.py`
3. Rename class: `DatabasesData` → `MySqlSchemaCollectorLegacy`
4. Update imports to use legacy query names (will be renamed in commit 2)

**Files Created:**
- `mysql/datadog_checks/mysql/schemas_legacy.py`

**Key Classes:**
- `MySqlSchemaCollectorLegacy` (formerly `DatabasesData`)
- `SubmitData` (helper class for batching)

**Legacy Approach:**
- Queries each database separately with `WHERE TABLE_SCHEMA = %s`
- Makes multiple queries per database (tables, columns, indexes, foreign keys, partitions)
- Processes in chunks (500 tables at a time)
- Aggregates results in Python

---

### ☐ Commit 2: Rename Queries with SQL_SCHEMAS_* Prefix
**Status:** Pending
**Description:** Rename all schema-related queries to follow naming convention:
- Legacy queries: `SQL_SCHEMAS_LEGACY_*`
- New queries: `SQL_SCHEMAS_*`

**File:** `mysql/datadog_checks/mysql/queries.py`

**Legacy Query Renames (for old approach):**
```python
SQL_DATABASES         → SQL_SCHEMAS_LEGACY_DATABASES
SQL_TABLES            → SQL_SCHEMAS_LEGACY_TABLES
SQL_COLUMNS           → SQL_SCHEMAS_LEGACY_COLUMNS
SQL_INDEXES           → SQL_SCHEMAS_LEGACY_INDEXES
SQL_INDEXES_8_0_13    → SQL_SCHEMAS_LEGACY_INDEXES_8_0_13
SQL_FOREIGN_KEYS      → SQL_SCHEMAS_LEGACY_FOREIGN_KEYS
SQL_PARTITION         → SQL_SCHEMAS_LEGACY_PARTITION
get_indexes_query()   → get_indexes_query_legacy()
```

**New Query Renames (for new approach):**
```python
SQL_DATABASES         → SQL_SCHEMAS_DATABASES
SQL_TABLES            → SQL_SCHEMAS_TABLES
SQL_COLUMNS           → SQL_SCHEMAS_COLUMNS
SQL_INDEXES           → SQL_SCHEMAS_INDEXES
SQL_INDEXES_8_0_13    → SQL_SCHEMAS_INDEXES_8_0_13
SQL_FOREIGN_KEYS      → SQL_SCHEMAS_FOREIGN_KEYS
SQL_PARTITION         → SQL_SCHEMAS_PARTITION
```

**Key Differences:**
- **Legacy queries:** Have `WHERE table_schema = %s AND table_name IN ({})` - parameterized per database
- **New queries:** No WHERE clause filters - get all databases at once, use JSON aggregation

**Files Modified:**
- `mysql/datadog_checks/mysql/queries.py`
- `mysql/datadog_checks/mysql/schemas.py` (update imports)
- `mysql/datadog_checks/mysql/schemas_legacy.py` (update imports)

---

### ☐ Commit 3: Add Version Detection Logic
**Status:** Pending
**Description:** Add method to detect if MySQL version supports JSON aggregation functions

**File:** `mysql/datadog_checks/mysql/schemas.py`

**Add Method to MySqlSchemaCollector:**
```python
def _supports_json_aggregation(self):
    """
    Check if MySQL/MariaDB version supports json_arrayagg and json_object.

    - MySQL: json_arrayagg introduced in 8.0.19
    - MariaDB: json_arrayagg introduced in 10.5.0

    Returns:
        bool: True if version supports JSON aggregation functions
    """
    if self._check.is_mariadb:
        return self._check.version.version_compatible((10, 5, 0))
    else:
        return self._check.version.version_compatible((8, 0, 19))
```

**Reference:**
- `self._check.version.version_compatible()` is already used in line 98 and 159 of metadata.py
- `self._check.is_mariadb` is a boolean flag

**Files Modified:**
- `mysql/datadog_checks/mysql/schemas.py`

---

### ☐ Commit 4: Implement Dual-Mode Collection
**Status:** Pending
**Description:** Enable automatic fallback to legacy collection for older MySQL versions

**Decision Point:** Where to handle the collector swap?
- **Option A:** Inside `MySqlSchemaCollector` (composition pattern)
- **Option B:** Inside `metadata.py` (factory/selection pattern)

**To Discuss:** Which location is cleaner for the swap logic?

**Approach (if in schemas.py):**
```python
class MySqlSchemaCollector:
    def __init__(self, check):
        # ... existing init ...
        self._legacy_collector = None
        if not self._supports_json_aggregation():
            from datadog_checks.mysql.schemas_legacy import MySqlSchemaCollectorLegacy
            self._legacy_collector = MySqlSchemaCollectorLegacy(...)

    def collect_schemas(self):
        if self._legacy_collector:
            return self._legacy_collector.collect_schemas()
        # ... existing new approach ...
```

**Files Modified:**
- TBD based on decision (either `schemas.py` or `metadata.py`)

---

### ☐ Commit 5: Update Integration Points
**Status:** Pending
**Description:** Ensure `metadata.py` correctly initializes and uses the version-aware collector

**File:** `mysql/datadog_checks/mysql/metadata.py`

**Current State:** Lines 11, 87 reference non-existent `databases_data` module (on seth.samuel branch)
**Target State:** Should reference unified schema collector interface

**Files Modified:**
- `mysql/datadog_checks/mysql/metadata.py`

---

### ☐ Commit 6: Add Tests
**Status:** Pending
**Description:** Add comprehensive tests for both collection paths

**Test Coverage Needed:**
1. **Unit Tests:**
   - Mock version checks to test both code paths
   - Test version detection logic (`_supports_json_aggregation`)
   - Test legacy collector independently
   - Test new collector independently

2. **Integration Tests:**
   - MySQL 5.7 (should use legacy)
   - MySQL 8.0 (should use new)
   - MariaDB < 10.5 (should use legacy)
   - MariaDB >= 10.5 (should use new)

**Files Modified:**
- `mysql/tests/test_schemas.py`
- Possibly add `mysql/tests/test_schemas_legacy.py`

**Reference:** Existing test file `test_schemas.py` has 95 lines

---

### ☐ Final: Verify & Lint
**Status:** Pending
**Description:** Run linting and tests to ensure everything works

**Commands:**
```bash
# Format code
ddev test -fs mysql

# Run tests
ddev --no-interactive test mysql

# Run specific schema tests
ddev --no-interactive test mysql -- -k test_schemas
```

---

## Key Technical Details

### Legacy Collection Method (databases_data.py → schemas_legacy.py)
- **Class:** `MySqlSchemaCollectorLegacy`
- **Query Pattern:** Multiple queries per database with parameterization
- **Chunking:** 500 tables per batch
- **Max Columns:** 100,000 per event
- **Max Execution Time:** Configurable (default 60s)
- **Data Processing:** Python-side aggregation

### New Collection Method (schemas.py)
- **Class:** `MySqlSchemaCollector`
- **Query Pattern:** Single complex JOIN query for all databases
- **JSON Functions:** `json_arrayagg()`, `json_object()`
- **Data Processing:** SQL-side aggregation
- **Performance:** Faster for MySQL 8+ due to single query

### Version Detection
- Access via: `self._check.version.version_compatible((major, minor, patch))`
- MariaDB check: `self._check.is_mariadb`
- Already used in codebase (see metadata.py line 159)

---

## Notes & Open Questions

1. **Collector Swap Location:** Decide between metadata.py vs schemas.py for version logic
2. **Test Strategy:** Full integration test matrix or mocked unit tests?
3. **Backwards Compatibility:** Ensure both collectors emit same event format
4. **Error Handling:** Verify both collectors handle errors consistently

---

## Progress Tracking

- [ ] Setup complete
- [ ] Commit 1 complete
- [ ] Commit 2 complete
- [ ] Commit 3 complete
- [ ] Commit 4 complete
- [ ] Commit 5 complete
- [ ] Commit 6 complete
- [ ] Final verification complete

Last Updated: 2026-01-12
