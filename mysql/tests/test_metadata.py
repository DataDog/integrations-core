# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mysql import MySql
from deepdiff import DeepDiff

from . import common
import pdb

@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {'enabled': False}
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return instance_complex

#TODO uncoment this
#@pytest.mark.integration
#@pytest.mark.usefixtures('dd_environment')
#def test_collect_mysql_settings(aggregator, dbm_instance, dd_run_check):
    # test to make sure we continue to support the old key
#    pdb.set_trace()
#    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
#    dd_run_check(mysql_check)
#    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
#    event = next((e for e in dbm_metadata if e['kind'] == 'mysql_variables'), None)
#    assert event is not None
#    assert event['host'] == "stubbed.hostname"
#    assert event['dbms'] == "mysql"
#    assert len(event["metadata"]) > 0

#TODO add more tests
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_schemas(aggregator, dd_run_check, dbm_instance):
    databases_to_find = ['datadog_test_schemas', 'datadog_test_schemas_second']
        
    exp_datadog_test_schemas = {
            "name":"datadog_test_schemas",
            "default_character_set_name":"latin1",
            "default_collation_name":"latin1_swedish_ci",
            "tables":[
                {
                    "name":"RestaurantReviews",
                    "columns":[
                        {
                            "name":"RestaurantName",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"1"
                        },
                        {
                            "name":"District",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"2"
                        },
                        {
                            "name":"Review",
                            "data_type":"text",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"3"
                        }
                    ],
                    "foreign_keys":[
                        {
                            "constraint_schema":"datadog_test_schemas",
                            "constraint_name":"FK_RestaurantNameDistrict",
                            "column_names":"RestaurantName,District",
                            "referenced_table_schema":"datadog_test_schemas",
                            "referenced_table_name":"Restaurants",
                            "referenced_column_names":"RestaurantName,District"
                        }
                    ],
                    "indexes":[
                        {
                            "index_name":"FK_RestaurantNameDistrict",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1,2",
                            "columns":"RestaurantName,District",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"true,true",
                            "non_uniques":"1,1"
                        }
                    ]
                },
                {
                    "name":"Restaurants",
                    "columns":[
                        {
                            "name":"RestaurantName",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"1"
                        },
                        {
                            "name":"District",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"2"
                        },
                        {
                            "name":"Cuisine",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"3"
                        }
                    ],
                    "indexes":[
                        {
                            "index_name":"UC_RestaurantNameDistrict",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1,2",
                            "columns":"RestaurantName,District",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"true,true",
                            "non_uniques":"0,0"
                        }
                    ]
                },
                {
                    "name":"cities",
                    "columns":[
                        {
                            "name":"id",
                            "data_type":"int",
                            "default":"0",
                            "nullable":False,
                            "ordinal_position":"1"
                        },
                        {
                            "name":"name",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"2"
                        },
                        {
                            "name":"population",
                            "data_type":"int",
                            "default":"0",
                            "nullable":False,
                            "ordinal_position":"3"
                        }
                    ],
                    "indexes":[
                        {
                            "index_name":"PRIMARY",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1",
                            "columns":"id",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"false",
                            "non_uniques":"0"
                        },
                        {
                            "index_name":"single_column_index",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1",
                            "columns":"population",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"false",
                            "non_uniques":"1"
                        },
                        {
                            "index_name":"two_columns_index",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1,2",
                            "columns":"id,name",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"false,true",
                            "non_uniques":"1,1"
                        }
                    ]
                },
                {
                    "name":"cities_partitioned",
                    "columns":[
                        {
                            "name":"id",
                            "data_type":"int",
                            "default":"0",
                            "nullable":False,
                            "ordinal_position":"1"
                        },
                        {
                            "name":"name",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"2"
                        },
                        {
                            "name":"population",
                            "data_type":"int",
                            "default":"0",
                            "nullable":False,
                            "ordinal_position":"3"
                        }
                    ],
                    "partitions":[
                        {
                            "partition_name":"p0",
                            "subpartition_names":"None",
                            "partition_ordinal_position":"1",
                            "subpartition_ordinal_positions":"None",
                            "partition_method":"RANGE",
                            ".subpartition_ordinal_positions":"None",
                            "partition_expression":"id",
                            "subpartition_expressions":"None",
                            "partition_description":"100",
                            "table_rows":"0",
                            "data_lengths":"16384",
                            "max_data_lengths":"None",
                            "index_lengths":"0",
                            "data_free":"0",
                            "partition_comment":"",
                            "tablespace_name":"None"
                        },
                        {
                            "partition_name":"p1",
                            "subpartition_names":"None",
                            "partition_ordinal_position":"2",
                            "subpartition_ordinal_positions":"None",
                            "partition_method":"RANGE",
                            ".subpartition_ordinal_positions":"None",
                            "partition_expression":"id",
                            "subpartition_expressions":"None",
                            "partition_description":"200",
                            "table_rows":"0",
                            "data_lengths":"16384",
                            "max_data_lengths":"None",
                            "index_lengths":"0",
                            "data_free":"0",
                            "partition_comment":"",
                            "tablespace_name":"None"
                        },
                        {
                            "partition_name":"p2",
                            "subpartition_names":"None",
                            "partition_ordinal_position":"3",
                            "subpartition_ordinal_positions":"None",
                            "partition_method":"RANGE",
                            ".subpartition_ordinal_positions":"None",
                            "partition_expression":"id",
                            "subpartition_expressions":"None",
                            "partition_description":"300",
                            "table_rows":"0",
                            "data_lengths":"16384",
                            "max_data_lengths":"None",
                            "index_lengths":"0",
                            "data_free":"0",
                            "partition_comment":"",
                            "tablespace_name":"None"
                        },
                        {
                            "partition_name":"p3",
                            "subpartition_names":"None",
                            "partition_ordinal_position":"4",
                            "subpartition_ordinal_positions":"None",
                            "partition_method":"RANGE",
                            ".subpartition_ordinal_positions":"None",
                            "partition_expression":"id",
                            "subpartition_expressions":"None",
                            "partition_description":"MAXVALUE",
                            "table_rows":"0",
                            "data_lengths":"16384",
                            "max_data_lengths":"None",
                            "index_lengths":"0",
                            "data_free":"0",
                            "partition_comment":"",
                            "tablespace_name":"None"
                        }
                    ],
                    "indexes":[
                        {
                            "index_name":"PRIMARY",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1",
                            "columns":"id",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"false",
                            "non_uniques":"0"
                        }
                    ]
                },
                {
                    "name":"landmarks",
                    "columns":[
                        {
                            "name":"name",
                            "data_type":"varchar",
                            "default":"None",
                            "nullable":True,
                            "ordinal_position":"1"
                        },
                        {
                            "name":"city_id",
                            "data_type":"int",
                            "default":"0",
                            "nullable":True,
                            "ordinal_position":"2"
                        }
                    ],
                    "foreign_keys":[
                        {
                            "constraint_schema":"datadog_test_schemas",
                            "constraint_name":"FK_CityId",
                            "column_names":"city_id",
                            "referenced_table_schema":"datadog_test_schemas",
                            "referenced_table_name":"cities",
                            "referenced_column_names":"id"
                        }
                    ],
                    "indexes":[
                        {
                            "index_name":"FK_CityId",
                            "collation":"A",
                            "cardinality":"0",
                            "index_type":"BTREE",
                            "seq_in_index":"1",
                            "columns":"city_id",
                            "sub_parts":"None",
                            "packed":"None",
                            "nullables":"true",
                            "non_uniques":"1"
                        }
                    ]
                }
            ]
        }
    exp_datadog_test_schemas_second = {
    "name":"datadog_test_schemas_second",
    "default_character_set_name":"latin1",
    "default_collation_name":"latin1_swedish_ci",
    "tables":[
        {
            #TODO May be on the backend and also check sqlserver ? 
            "name":"ϑings",
            "columns":[
                {
                    "name":"id",
                    "data_type":"int",
                    "default":"0",
                    "nullable":True,
                    "ordinal_position":"1"
                },
                {
                    "name":"name",
                    "data_type":"varchar",
                    "default":"None",
                    "nullable":True,
                    "ordinal_position":"2"
                }
            ],
            "indexes":[
                {
                    "index_name":"thingsindex",
                    "collation":"A",
                    "cardinality":"2",
                    "index_type":"BTREE",
                    "seq_in_index":"1",
                    "columns":"name",
                    "sub_parts":"None",
                    "packed":"None",
                    "nullables":"true",
                    "non_uniques":"0"
                }
            ]
        },
        {
            "name":"ts",
            "columns":[
                {
                    "name":"id",
                    "data_type":"int",
                    "default":"None",
                    "nullable":True,
                    "ordinal_position":"1"
                },
                {
                    "name":"purchased",
                    "data_type":"date",
                    "default":"None",
                    "nullable":True,
                    "ordinal_position":"2"
                }
            ],
            #TODO ask team collapse all these stuff ?
            "partitions":[
                {
                    "partition_name":"p0",
                    "subpartition_names":"p0sp0,p0sp1",
                    "partition_ordinal_position":"1",
                    "subpartition_ordinal_positions":"1,2",
                    "partition_method":"RANGE",
                    ".subpartition_ordinal_positions":"HASH,HASH",
                    "partition_expression":" YEAR(purchased)",
                    "subpartition_expressions":" TO_DAYS(purchased), TO_DAYS(purchased)",
                    "partition_description":"1990",
                    "table_rows":"0",
                    "data_lengths":"16384,16384",
                    "max_data_lengths":"None",
                    "index_lengths":"0,0",
                    "data_free":"0,0",
                    "partition_comment":"",
                    "tablespace_name":"None"
                },
                {
                    "partition_name":"p1",
                    "subpartition_names":"p1sp0,p1sp1",
                    "partition_ordinal_position":"2",
                    "subpartition_ordinal_positions":"1,2",
                    "partition_method":"RANGE",
                    ".subpartition_ordinal_positions":"HASH,HASH",
                    "partition_expression":" YEAR(purchased)",
                    "subpartition_expressions":" TO_DAYS(purchased), TO_DAYS(purchased)",
                    "partition_description":"2000",
                    "table_rows":"0",
                    "data_lengths":"16384,16384",
                    "max_data_lengths":"None",
                    "index_lengths":"0,0",
                    "data_free":"0,0",
                    "partition_comment":"",
                    "tablespace_name":"None"
                },
                {
                    "partition_name":"p2",
                    "subpartition_names":"p2sp0,p2sp1",
                    "partition_ordinal_position":"3",
                    "subpartition_ordinal_positions":"1,2",
                    "partition_method":"RANGE",
                    ".subpartition_ordinal_positions":"HASH,HASH",
                    "partition_expression":" YEAR(purchased)",
                    "subpartition_expressions":" TO_DAYS(purchased), TO_DAYS(purchased)",
                    "partition_description":"MAXVALUE",
                    "table_rows":"0",
                    "data_lengths":"16384,16384",
                    "max_data_lengths":"None",
                    "index_lengths":"0,0",
                    "data_free":"0,0",
                    "partition_comment":"",
                    "tablespace_name":"None"
                }
            ]
        }
    ]
}

    #if running_on_windows_ci():
    #    exp_datadog_test['owner'] = 'None'
    #    exp_datadog_test_schemas['owner'] = 'None'

    expected_data_for_db = {
        'datadog_test_schemas': exp_datadog_test_schemas,
        'datadog_test_schemas_second': exp_datadog_test_schemas_second,
    }

    dbm_instance['schemas_collection'] = {"enabled": True}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(mysql_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    actual_payloads = {}

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'mysql_databases'):
        assert schema_event.get("timestamp") is not None
        assert schema_event["host"] == "stubbed.hostname"
        assert schema_event["agent_version"] == "0.0.0"
        assert schema_event["dbms"] == "mysql"
        assert schema_event.get("collection_interval") is not None
        assert schema_event.get("dbms_version") is not None

        database_metadata = schema_event['metadata']
        assert len(database_metadata) == 1
        db_name = database_metadata[0]['name']
        if db_name not in databases_to_find:
            continue

        if db_name in actual_payloads:
            actual_payloads[db_name]['schemas'] = actual_payloads[db_name]['schemas'] + database_metadata[0]['schemas']
        else:
            actual_payloads[db_name] = database_metadata[0]

    assert len(actual_payloads) == len(expected_data_for_db)

    for db_name, actual_payload in actual_payloads.items():

        assert db_name in databases_to_find

        # id's are env dependant
       # normalize_ids(actual_payload)

        # index columns may be in any order
        #normalize_indexes_columns(actual_payload)
        pdb.set_trace()
        difference = DeepDiff(actual_payload, expected_data_for_db[db_name], ignore_order=True)

        if difference:
            raise AssertionError(Exception("found the following diffs: " + str(difference)))
        #diff_keys = list(difference.keys())
        # schema data also collects certain builtin default schemas which are ignored in the test
        #if len(diff_keys) > 0 and diff_keys != ['iterable_item_removed']:
        #    raise AssertionError(Exception("found the following diffs: " + str(difference)))