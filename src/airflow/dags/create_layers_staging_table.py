from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.providers.postgres.hooks.postgres import PostgresHook




import os
from datetime import datetime




# Определяем параметры DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'start_date': datetime(2024, 1, 1),
}




postgres_scripts_path = Variable.get("createTables")




with DAG(
    'create_staging_table',
    default_args=default_args,
    description='Create tables staging',
    schedule_interval='@once',
    catchup=False,
    template_searchpath=[postgres_scripts_path]
) as dag:
    
    #стартовая точка
    start = EmptyOperator(task_id='start')
    
    
    stg_sql_script = SQLExecuteQueryOperator(
        task_id='create_staging_script',
        conn_id='postgres_dwh_connection',
        sql='create_staging.sql'
    )
    
    end = EmptyOperator(task_id='end_create_tables', trigger_rule=TriggerRule.ALL_SUCCESS)



start >> [stg_sql_script] >> end