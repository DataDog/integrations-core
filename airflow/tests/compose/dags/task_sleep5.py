import time
from datetime import datetime

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator


def print_hello():
    time.sleep(0.5)
    return 'Hello world OK!'


dag = DAG(
    'hello_world_sleep5',
    description='Simple tutorial DAG',
    schedule_interval='* * * * *',
    start_date=datetime(2017, 3, 20),
    catchup=True,
)

dummy_operator = DummyOperator(task_id='dummy_task', retries=3, dag=dag)

hello_operator = PythonOperator(task_id='hello_world_sleep5_task', python_callable=print_hello, dag=dag)

dummy_operator >> hello_operator
