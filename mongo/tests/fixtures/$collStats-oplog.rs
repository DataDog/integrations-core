[
    {
        "ns": "local.oplog.rs",
        "host": "7515219d9503:27017",
        "localTime": {
            "$date": "2024-07-01T20:36:49.358Z"
        },
        "latencyStats": {
            "reads": {
                "latency": 13165,
                "ops": 10
            },
            "writes": {
                "latency": 8542,
                "ops": 1
            },
            "commands": {
                "latency": 0,
                "ops": 0
            },
            "transactions": {
                "latency": 0,
                "ops": 0
            }
        },
        "storageStats": {
            "size": 907806,
            "count": 4341,
            "avgObjSize": 209,
            "storageSize": 196608,
            "capped": true,
            "max": 10,
            "maxSize": 16777216,
            "sleepCount": 0,
            "sleepMS": 0,
            "wiredTiger": {
                "metadata": {
                    "formatVersion": 1,
                    "oplogKeyExtractionVersion": 1
                },
                "creationString": "access_pattern_hint=none,allocation_size=4KB,app_metadata=(formatVersion=1,oplogKeyExtractionVersion=1),assert=(commit_timestamp=none,durable_timestamp=none,read_timestamp=none),block_allocation=best,block_compressor=snappy,cache_resident=false,checksum=on,colgroups=,collator=,columns=,dictionary=0,encryption=(keyid=,name=),exclusive=false,extractor=,format=btree,huffman_key=,huffman_value=,ignore_in_memory_cache_size=false,immutable=false,internal_item_max=0,internal_key_max=0,internal_key_truncate=true,internal_page_max=4KB,key_format=q,key_gap=10,leaf_item_max=0,leaf_key_max=0,leaf_page_max=32KB,leaf_value_max=64MB,log=(enabled=true),lsm=(auto_throttle=true,bloom=true,bloom_bit_count=16,bloom_config=,bloom_hash_count=8,bloom_oldest=false,chunk_count_limit=0,chunk_max=5GB,chunk_size=10MB,merge_custom=(prefix=,start_generation=0,suffix=),merge_max=15,merge_min=0),memory_page_image_max=0,memory_page_max=10m,os_cache_dirty_max=0,os_cache_max=0,prefix_compression=false,prefix_compression_min=4,source=,split_deepen_min_child=0,split_deepen_per_child=0,split_pct=90,type=file,value_format=u",
                "type": "file",
                "uri": "statistics:table:collection-8--9025131032214742726",
                "LSM": {
                    "bloom filter false positives": 0,
                    "bloom filter hits": 0,
                    "bloom filter misses": 0,
                    "bloom filter pages evicted from cache": 0,
                    "bloom filter pages read into cache": 0,
                    "bloom filters in the LSM tree": 0,
                    "chunks in the LSM tree": 0,
                    "highest merge generation in the LSM tree": 0,
                    "queries that could have benefited from a Bloom filter that did not exist": 0,
                    "sleep for LSM checkpoint throttle": 0,
                    "sleep for LSM merge throttle": 0,
                    "total size of bloom filters": 0
                },
                "block-manager": {
                    "allocations requiring file extension": 56,
                    "blocks allocated": 577,
                    "blocks freed": 146,
                    "checkpoint size": 151552,
                    "file allocation unit size": 4096,
                    "file bytes available for reuse": 28672,
                    "file magic number": 120897,
                    "file major version number": 1,
                    "file size in bytes": 196608,
                    "minor version number": 0
                },
                "btree": {
                    "btree checkpoint generation": 143,
                    "column-store fixed-size leaf pages": 0,
                    "column-store internal pages": 0,
                    "column-store variable-size RLE encoded values": 0,
                    "column-store variable-size deleted values": 0,
                    "column-store variable-size leaf pages": 0,
                    "fixed-record size": 0,
                    "maximum internal page key size": 368,
                    "maximum internal page size": 4096,
                    "maximum leaf page key size": 2867,
                    "maximum leaf page size": 32768,
                    "maximum leaf page value size": 67108864,
                    "maximum tree depth": 3,
                    "number of key/value pairs": 0,
                    "overflow pages": 0,
                    "pages rewritten by compaction": 0,
                    "row-store empty values": 0,
                    "row-store internal pages": 0,
                    "row-store leaf pages": 0
                },
                "cache": {
                    "bytes currently in the cache": 1412447,
                    "bytes dirty in the cache cumulative": 79714225,
                    "bytes read into cache": 0,
                    "bytes written from cache": 14326498,
                    "checkpoint blocked page eviction": 0,
                    "data source pages selected for eviction unable to be evicted": 0,
                    "eviction walk passes of a file": 0,
                    "eviction walk target pages histogram - 0-9": 0,
                    "eviction walk target pages histogram - 10-31": 0,
                    "eviction walk target pages histogram - 128 and higher": 0,
                    "eviction walk target pages histogram - 32-63": 0,
                    "eviction walk target pages histogram - 64-128": 0,
                    "eviction walks abandoned": 0,
                    "eviction walks gave up because they restarted their walk twice": 0,
                    "eviction walks gave up because they saw too many pages and found no candidates": 0,
                    "eviction walks gave up because they saw too many pages and found too few candidates": 0,
                    "eviction walks reached end of tree": 0,
                    "eviction walks started from root of tree": 0,
                    "eviction walks started from saved location in tree": 0,
                    "hazard pointer blocked page eviction": 0,
                    "in-memory page passed criteria to be split": 0,
                    "in-memory page splits": 0,
                    "internal pages evicted": 0,
                    "internal pages split during eviction": 0,
                    "leaf pages split during eviction": 0,
                    "modified pages evicted": 0,
                    "overflow pages read into cache": 0,
                    "page split during eviction deepened the tree": 0,
                    "page written requiring cache overflow records": 0,
                    "pages read into cache": 0,
                    "pages read into cache after truncate": 1,
                    "pages read into cache after truncate in prepare state": 0,
                    "pages read into cache requiring cache overflow entries": 0,
                    "pages requested from the cache": 11348,
                    "pages seen by eviction walk": 0,
                    "pages written from cache": 296,
                    "pages written requiring in-memory restoration": 0,
                    "tracked dirty bytes in the cache": 1411928,
                    "unmodified pages evicted": 0
                },
                "cache_walk": {
                    "Average difference between current eviction generation when the page was last considered": 0,
                    "Average on-disk page image size seen": 0,
                    "Average time in cache for pages that have been visited by the eviction server": 0,
                    "Average time in cache for pages that have not been visited by the eviction server": 0,
                    "Clean pages currently in cache": 0,
                    "Current eviction generation": 0,
                    "Dirty pages currently in cache": 0,
                    "Entries in the root page": 0,
                    "Internal pages currently in cache": 0,
                    "Leaf pages currently in cache": 0,
                    "Maximum difference between current eviction generation when the page was last considered": 0,
                    "Maximum page size seen": 0,
                    "Minimum on-disk page image size seen": 0,
                    "Number of pages never visited by eviction server": 0,
                    "On-disk page image sizes smaller than a single allocation unit": 0,
                    "Pages created in memory and never written": 0,
                    "Pages currently queued for eviction": 0,
                    "Pages that could not be queued for eviction": 0,
                    "Refs skipped during cache traversal": 0,
                    "Size of the root page": 0,
                    "Total number of pages currently in cache": 0
                },
                "compression": {
                    "compressed page maximum internal page size prior to compression": 4096,
                    "compressed page maximum leaf page size prior to compression ": 131072,
                    "compressed pages read": 0,
                    "compressed pages written": 154,
                    "page written failed to compress": 0,
                    "page written was too small to compress": 142
                },
                "cursor": {
                    "bulk loaded cursor insert calls": 0,
                    "cache cursors reuse count": 2843,
                    "close calls that result in cache": 0,
                    "create calls": 62,
                    "insert calls": 4341,
                    "insert key and value bytes": 946875,
                    "modify": 0,
                    "modify key and value bytes affected": 0,
                    "modify value bytes modified": 0,
                    "next calls": 9366,
                    "open cursor count": 0,
                    "operation restarted": 1,
                    "prev calls": 20,
                    "remove calls": 0,
                    "remove key bytes removed": 0,
                    "reserve calls": 0,
                    "reset calls": 12395,
                    "search calls": 6969,
                    "search near calls": 14,
                    "truncate calls": 0,
                    "update calls": 0,
                    "update key and value bytes": 0,
                    "update value size change": 0
                },
                "reconciliation": {
                    "dictionary matches": 0,
                    "fast-path pages deleted": 0,
                    "internal page key bytes discarded using suffix compression": 1409,
                    "internal page multi-block writes": 0,
                    "internal-page overflow keys": 0,
                    "leaf page key bytes discarded using prefix compression": 0,
                    "leaf page multi-block writes": 120,
                    "leaf-page overflow keys": 0,
                    "maximum blocks required for a page": 1,
                    "overflow values written": 0,
                    "page checksum matches": 431,
                    "page reconciliation calls": 282,
                    "page reconciliation calls for eviction": 0,
                    "pages deleted": 0
                },
                "session": {
                    "object compaction": 0
                },
                "transaction": {
                    "update conflicts": 0
                }
            },
            "nindexes": 0,
            "indexDetails": {},
            "indexBuilds": [],
            "totalIndexSize": 0,
            "indexSizes": {},
            "scaleFactor": 1
        },
        "queryExecStats": {
            "collectionScans": {
                "total": 81753,
                "nonTailable": 81750
            }
        }
    }
]