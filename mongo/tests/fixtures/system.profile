[
    {
        "op": "update",
        "ns": "integration.customers",
        "command": {
            "q": {
                "age": {
                    "$gt": 20
                }
            },
            "u": {
                "$set": {
                    "subscribed": true
                }
            },
            "multi": true,
            "upsert": false,
            "comment": "update customers subscription status by age"
        },
        "keysExamined": 431,
        "docsExamined": 431,
        "nMatched": 431,
        "nModified": 431,
        "nUpserted": 0,
        "keysInserted": 431,
        "keysDeleted": 431,
        "numYield": 0,
        "locks": {
            "ParallelBatchWriterMode": {
                "acquireCount": {
                    "r": 1
                }
            },
            "FeatureCompatibilityVersion": {
                "acquireCount": {
                    "r": 1,
                    "w": 1
                }
            },
            "ReplicationStateTransition": {
                "acquireCount": {
                    "w": 1
                }
            },
            "Global": {
                "acquireCount": {
                    "r": 1,
                    "w": 1
                }
            },
            "Database": {
                "acquireCount": {
                    "w": 1
                }
            },
            "Collection": {
                "acquireCount": {
                    "w": 1
                }
            }
        },
        "flowControl": {
            "acquireCount": 1
        },
        "storage": {},
        "cpuNanos": 10630666,
        "millis": 10,
        "planSummary": "IXSCAN { age: -1 }",
        "execStats": {
            "stage": "UPDATE",
            "nReturned": 0,
            "executionTimeMillisEstimate": 4,
            "works": 432,
            "advanced": 0,
            "needTime": 431,
            "needYield": 0,
            "saveState": 0,
            "restoreState": 0,
            "isEOF": 1,
            "nMatched": 431,
            "nWouldModify": 431,
            "nWouldUpsert": 0,
            "inputStage": {
                "stage": "FETCH",
                "nReturned": 431,
                "executionTimeMillisEstimate": 0,
                "works": 432,
                "advanced": 431,
                "needTime": 0,
                "needYield": 0,
                "saveState": 431,
                "restoreState": 431,
                "isEOF": 1,
                "docsExamined": 431,
                "alreadyHasObj": 0,
                "inputStage": {
                    "stage": "IXSCAN",
                    "nReturned": 431,
                    "executionTimeMillisEstimate": 0,
                    "works": 432,
                    "advanced": 431,
                    "needTime": 0,
                    "needYield": 0,
                    "saveState": 431,
                    "restoreState": 431,
                    "isEOF": 1,
                    "keyPattern": {
                        "age": -1
                    },
                    "indexName": "age_-1",
                    "isMultiKey": false,
                    "multiKeyPaths": {
                        "age": []
                    },
                    "isUnique": false,
                    "isSparse": false,
                    "isPartial": false,
                    "indexVersion": 2,
                    "direction": "forward",
                    "indexBounds": {
                        "age": [
                            "[inf.0, 20)"
                        ]
                    },
                    "keysExamined": 431,
                    "seeks": 1,
                    "dupsTested": 0,
                    "dupsDropped": 0
                }
            }
        },
        "ts": {
            "$date": "2024-07-09T18:41:23.298Z"
        },
        "client": "192.168.65.1",
        "allUsers": [],
        "user": ""
    },
    {
        "op": "query",
        "ns": "integration.customers",
        "command": {
            "find": "customers",
            "filter": {
                "age": {
                    "$gt": 63
                }
            },
            "sort": {
                "name": 1
            },
            "comment": "query customers by age",
            "limit": 34,
            "$db": "integration"
        },
        "keysExamined": 417,
        "docsExamined": 417,
        "fromPlanCache": true,
        "nBatches": 1,
        "cursorExhausted": true,
        "numYield": 1,
        "nreturned": 0,
        "queryHash": "F286520C",
        "planCacheKey": "4AFF4016",
        "queryFramework": "classic",
        "locks": {
            "FeatureCompatibilityVersion": {
                "acquireCount": {
                    "r": 3
                }
            },
            "Global": {
                "acquireCount": {
                    "r": 3
                }
            }
        },
        "flowControl": {},
        "storage": {},
        "responseLength": 110,
        "protocol": "op_msg",
        "cpuNanos": 85181501,
        "millis": 85,
        "planSummary": "IXSCAN { name: 1 }",
        "planningTimeMicros": 85096,
        "execStats": {
            "stage": "CACHED_PLAN",
            "nReturned": 0,
            "executionTimeMillisEstimate": 84,
            "works": 1,
            "advanced": 0,
            "needTime": 0,
            "needYield": 0,
            "saveState": 1,
            "restoreState": 1,
            "isEOF": 1,
            "inputStage": {
                "stage": "LIMIT",
                "nReturned": 0,
                "executionTimeMillisEstimate": 84,
                "works": 418,
                "advanced": 0,
                "needTime": 417,
                "needYield": 0,
                "saveState": 1,
                "restoreState": 1,
                "isEOF": 1,
                "limitAmount": 34,
                "inputStage": {
                    "stage": "FETCH",
                    "filter": {
                        "age": {
                            "$gt": 63
                        }
                    },
                    "nReturned": 0,
                    "executionTimeMillisEstimate": 84,
                    "works": 418,
                    "advanced": 0,
                    "needTime": 417,
                    "needYield": 0,
                    "saveState": 1,
                    "restoreState": 1,
                    "isEOF": 1,
                    "docsExamined": 417,
                    "alreadyHasObj": 0,
                    "inputStage": {
                        "stage": "IXSCAN",
                        "nReturned": 417,
                        "executionTimeMillisEstimate": 84,
                        "works": 418,
                        "advanced": 417,
                        "needTime": 0,
                        "needYield": 0,
                        "saveState": 1,
                        "restoreState": 1,
                        "isEOF": 1,
                        "keyPattern": {
                            "name": 1
                        },
                        "indexName": "name_1",
                        "isMultiKey": false,
                        "multiKeyPaths": {
                            "name": []
                        },
                        "isUnique": false,
                        "isSparse": false,
                        "isPartial": false,
                        "indexVersion": 2,
                        "direction": "forward",
                        "indexBounds": {
                            "name": [
                                "[MinKey, MaxKey]"
                            ]
                        },
                        "keysExamined": 417,
                        "seeks": 1,
                        "dupsTested": 0,
                        "dupsDropped": 0
                    }
                }
            }
        },
        "ts": {
            "$date": "2024-07-09T18:41:16.223Z"
        },
        "client": "192.168.65.1",
        "allUsers": [],
        "user": ""
    },
    {
        "op": "update",
        "ns": "integration.customers",
        "command": {
            "q": {
                "age": {
                    "$gt": 20
                }
            },
            "u": {
                "$set": {
                    "subscribed": false
                }
            },
            "multi": true,
            "upsert": false,
            "comment": "update customers subscription status by age"
        },
        "keysExamined": 416,
        "docsExamined": 416,
        "nMatched": 416,
        "nModified": 416,
        "nUpserted": 0,
        "keysInserted": 416,
        "keysDeleted": 416,
        "numYield": 1,
        "locks": {
            "ParallelBatchWriterMode": {
                "acquireCount": {
                    "r": 2
                }
            },
            "FeatureCompatibilityVersion": {
                "acquireCount": {
                    "r": 1,
                    "w": 2
                }
            },
            "ReplicationStateTransition": {
                "acquireCount": {
                    "w": 2
                }
            },
            "Global": {
                "acquireCount": {
                    "r": 1,
                    "w": 2
                }
            },
            "Database": {
                "acquireCount": {
                    "w": 2
                }
            },
            "Collection": {
                "acquireCount": {
                    "w": 2
                }
            }
        },
        "flowControl": {
            "acquireCount": 2
        },
        "storage": {},
        "cpuNanos": 21290417,
        "millis": 21,
        "planSummary": "IXSCAN { age: -1 }",
        "execStats": {
            "stage": "UPDATE",
            "nReturned": 0,
            "executionTimeMillisEstimate": 13,
            "works": 417,
            "advanced": 0,
            "needTime": 416,
            "needYield": 0,
            "saveState": 1,
            "restoreState": 1,
            "isEOF": 1,
            "nMatched": 416,
            "nWouldModify": 416,
            "nWouldUpsert": 0,
            "inputStage": {
                "stage": "FETCH",
                "nReturned": 416,
                "executionTimeMillisEstimate": 0,
                "works": 417,
                "advanced": 416,
                "needTime": 0,
                "needYield": 0,
                "saveState": 417,
                "restoreState": 417,
                "isEOF": 1,
                "docsExamined": 416,
                "alreadyHasObj": 0,
                "inputStage": {
                    "stage": "IXSCAN",
                    "nReturned": 416,
                    "executionTimeMillisEstimate": 0,
                    "works": 417,
                    "advanced": 416,
                    "needTime": 0,
                    "needYield": 0,
                    "saveState": 417,
                    "restoreState": 417,
                    "isEOF": 1,
                    "keyPattern": {
                        "age": -1
                    },
                    "indexName": "age_-1",
                    "isMultiKey": false,
                    "multiKeyPaths": {
                        "age": []
                    },
                    "isUnique": false,
                    "isSparse": false,
                    "isPartial": false,
                    "indexVersion": 2,
                    "direction": "forward",
                    "indexBounds": {
                        "age": [
                            "[inf.0, 18)"
                        ]
                    },
                    "keysExamined": 416,
                    "seeks": 1,
                    "dupsTested": 0,
                    "dupsDropped": 0
                }
            }
        },
        "ts": {
            "$date": "2024-07-09T18:41:15.716Z"
        },
        "client": "192.168.65.1",
        "allUsers": [],
        "user": ""
    },
    {
        "op": "query",
        "ns": "integration.customers",
        "command": {
            "find": "customers",
            "filter": {
                "age": {
                    "$gt": 63
                }
            },
            "sort": {
                "name": 1
            },
            "comment": "query customers by age",
            "limit": 34,
            "$db": "integration"
        },
        "keysExamined": 456,
        "docsExamined": 456,
        "fromPlanCache": true,
        "nBatches": 1,
        "cursorExhausted": true,
        "numYield": 1,
        "nreturned": 0,
        "queryHash": "F286520C",
        "planCacheKey": "4AFF4016",
        "queryFramework": "classic",
        "locks": {
            "FeatureCompatibilityVersion": {
                "acquireCount": {
                    "r": 3
                }
            },
            "Global": {
                "acquireCount": {
                    "r": 3
                }
            }
        },
        "flowControl": {},
        "storage": {},
        "responseLength": 110,
        "protocol": "op_msg",
        "cpuNanos": 14135292,
        "millis": 14,
        "planSummary": "IXSCAN { name: 1 }",
        "planningTimeMicros": 13916,
        "hasSortStage": true,
        "replanned": true,
        "execStats": {
            "stage": "CACHED_PLAN",
            "nReturned": 0,
            "executionTimeMillisEstimate": 12,
            "works": 1,
            "advanced": 0,
            "needTime": 0,
            "needYield": 0,
            "saveState": 1,
            "restoreState": 1,
            "isEOF": 1,
            "inputStage": {
                "stage": "LIMIT",
                "nReturned": 0,
                "executionTimeMillisEstimate": 11,
                "works": 457,
                "advanced": 0,
                "needTime": 456,
                "needYield": 0,
                "saveState": 1,
                "restoreState": 1,
                "isEOF": 1,
                "limitAmount": 34,
                "inputStage": {
                    "stage": "FETCH",
                    "filter": {
                        "age": {
                            "$gt": 63
                        }
                    },
                    "nReturned": 0,
                    "executionTimeMillisEstimate": 11,
                    "works": 457,
                    "advanced": 0,
                    "needTime": 456,
                    "needYield": 0,
                    "saveState": 1,
                    "restoreState": 1,
                    "isEOF": 1,
                    "docsExamined": 456,
                    "alreadyHasObj": 0,
                    "inputStage": {
                        "stage": "IXSCAN",
                        "nReturned": 456,
                        "executionTimeMillisEstimate": 0,
                        "works": 457,
                        "advanced": 456,
                        "needTime": 0,
                        "needYield": 0,
                        "saveState": 1,
                        "restoreState": 1,
                        "isEOF": 1,
                        "keyPattern": {
                            "name": 1
                        },
                        "indexName": "name_1",
                        "isMultiKey": false,
                        "multiKeyPaths": {
                            "name": []
                        },
                        "isUnique": false,
                        "isSparse": false,
                        "isPartial": false,
                        "indexVersion": 2,
                        "direction": "forward",
                        "indexBounds": {
                            "name": [
                                "[MinKey, MaxKey]"
                            ]
                        },
                        "keysExamined": 456,
                        "seeks": 1,
                        "dupsTested": 0,
                        "dupsDropped": 0
                    }
                }
            }
        },
        "ts": {
            "$date": "2024-07-09T18:44:27.336Z"
        },
        "client": "192.168.65.1",
        "allUsers": [],
        "user": ""
    }
]