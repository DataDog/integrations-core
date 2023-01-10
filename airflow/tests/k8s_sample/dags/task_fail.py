# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator


def print_hello():
    raise Exception('Hello world fail!')


dag = DAG(
    'hello_world_fail',
    description='Simple tutorial DAG Fail',
    schedule_interval='*/1 * * * *',
    start_date=datetime(2017, 3, 20),
    catchup=False,
)

dummy_operator = DummyOperator(task_id='dummy_task', retries=3, dag=dag)

hello_operator = PythonOperator(task_id='hello_world_fail_task', python_callable=print_hello, dag=dag)

dummy_operator >> hello_operator
