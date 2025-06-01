from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from datetime import datetime, timedelta
import pandas as pd

SOURCE_CONN_ID = 'postgres_source_connection'
STAGING_CONN_ID = 'postgres_dwh_connection'
SOURCE_SYSTEM = Variable.get("source_system", default_var="emr_source")

TABLES = ['gender', 'mkb_code', 'procedure', 'patients', 'patient_anamnesis', 'patient_results']

default_args = {
    'owner': 'airflow',
	'depends_on_past': False,
    'start_date': datetime(2025, 4, 15),
}

with DAG(
    dag_id='Incremental_etl_to_staging',
    default_args=default_args,
    #schedule_interval=timedelta(days=1),
    schedule_interval = None, # для целей тестирования
    catchup=True,
    description='ETL с инкрементальной загрузкой в staging',
) as dag:

    start = EmptyOperator(task_id='start')
    end = EmptyOperator(task_id='end')

    def extract_incremental_with_execution_date(table_name, **context):
        start_date = context['data_interval_start'] - timedelta(hours=3)
        end_date = context['data_interval_end'] #+ timedelta(hours=3) # для тестирования пришлось
        
        # Преобразуем формат в "день-месяц-год часы:минуты:секунды"
        start_date_str = start_date.strftime('%d-%m-%Y %H:%M:%S')
        end_date_str = end_date.strftime('%d-%m-%Y %H:%M:%S')

        #start_date = execution_date.strftime('%d-%m-%Y %H:%M:%S')
        #end_date = next_execution_date.strftime('%d-%m-%Y %H:%M:%S')

        source_hook = PostgresHook(postgres_conn_id=SOURCE_CONN_ID)
        target_hook = PostgresHook(postgres_conn_id=STAGING_CONN_ID)
		

        table_mapping = {
            'gender': {
                'query': """
                    SELECT id, gender_name, created_at, updated_at
                    FROM gender
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.gender',
                'columns': ['id', 'gender_name', 'created_at', 'updated_at']
            },
            'mkb_code': {
                'query': """
                    SELECT id, mkb_code, diagnosis_name, created_at, updated_at
                    FROM mkb_code
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.mkb_code',
                'columns': ['id', 'mkb_code', 'diagnosis_name', 'created_at', 'updated_at']
            },
            'procedure': {
                'query': """
                    SELECT id, procedure_name, created_at, updated_at
                    FROM procedure
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.procedure_table',
                'columns': ['id', 'procedure_name', 'created_at', 'updated_at']
            },
            'patients': {
                'query': """
                    SELECT id, patient_uuid, gender_id, date_of_birth, surname, name, middle_name, created_at, updated_at
                    FROM patients
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.patients',
                'columns': ['id', 'patient_uuid', 'gender_id', 'date_of_birth', 'surname', 'name', 'middle_name', 'created_at', 'updated_at']
            },
            'patient_anamnesis': {
                'query': """
                    SELECT id, patient_id, anamnesis_description, date_anamnesis, created_at, updated_at
                    FROM patient_anamnesis
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.patient_anamnesis',
                'columns': ['id', 'patient_id', 'anamnesis_description', 'date_anamnesis', 'created_at', 'updated_at']
            },
            'patient_results': {
                'query': """
                    SELECT id, patient_id, mkb_id, image_path, study_date, result_inference, final_diagnosis,
                           procedure_id, cost, created_at, updated_at
                    FROM patient_results
                    WHERE updated_at >= %s AND updated_at < %s
                """,
                'target': 'staging.patient_results',
                'columns': ['id', 'patient_id', 'mkb_id', 'image_path', 'study_date', 'result_inference',
                            'final_diagnosis', 'procedure_id', 'cost', 'created_at', 'updated_at']
            },
        }

        mapping = table_mapping[table_name]
        rows = source_hook.get_records(mapping['query'], parameters=(start_date, end_date))

        if not rows:
            print(f"No new data found for {table_name} between {start_date_str} and {end_date_str}")
            return
        
        now_ts = datetime.utcnow()

        insert_query = f"""
            INSERT INTO {mapping['target']} ({', '.join(mapping['columns'])}, source_system, original_id)
            VALUES ({', '.join(['%s'] * len(mapping['columns']))}, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """

        enriched_rows = [row + (SOURCE_SYSTEM, row[mapping['columns'].index('id')], now_ts) for row in rows]
        target_fields = mapping['columns'] + ['source_system', 'original_id', 'load_date']
        target_hook.insert_rows(table=mapping['target'], rows=enriched_rows, target_fields=target_fields, commit_every=100)
        print(f"Loaded {len(enriched_rows)} rows into {mapping['target']} between {start_date_str} and {end_date_str}")
        
    previous_task = start
    for table in TABLES:
        extract_task = PythonOperator(
            task_id=f'extract_{table}',
            python_callable=extract_incremental_with_execution_date,
            op_kwargs={'table_name': table},
            provide_context=True,
        )

        previous_task >> extract_task
        previous_task = extract_task
    
    previous_task >> end
        