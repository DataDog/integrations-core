# Persistent cache

Read this when the PR reads or writes the persistent cache, or adds state that has to survive an Agent restart. No `AGENTS.md` covers it. Every rule here is PR scope: it applies to what the PR adds or changes.

- State that must survive an Agent restart (cursors, last-seen timestamps) uses `read_persistent_cache`/`write_persistent_cache`, not the check's own files, and only that state: everything else stays in memory (**Request**).
- Not read or written in `__init__`: the key prefix is set in `check_initializations` and `check_id` is still empty (**Request**).
- Works with an empty cache (a missing key returns `''`) and with a value written by an older version: parse failures start fresh. A test covers both (**Request**).
- Bounded: old entries removed or replaced so it doesn't grow run after run (**Request**); large values rewritten every run questioned for their per-run cost (**Question**).
- Cache ID fits the data: override `persistent_cache_id()` (as `pan_firewall` and `control_m` do), or use `config_set_persistent_cache_id`, with only the options that matter (**Question**).
