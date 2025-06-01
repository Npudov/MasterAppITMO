from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import hashlib
import json


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
	'start_date': datetime(2025, 4, 15)
}

def scd2_update_dim_patients():
    pg_hook = PostgresHook(postgres_conn_id='postgres_dwh_connection')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, new_data
        FROM staging.audit_log
        WHERE table_name = 'patients' AND processed = FALSE
    """)
    changes = cursor.fetchall()

    for change_id, new_data in changes:
        data = new_data if isinstance(new_data, dict) else json.loads(new_data)
        uuid = data["patient_uuid"]
        gender_id = int(data["gender_id"])
        date_of_birth = data["date_of_birth"]
        full_hash = hashlib.md5((uuid + "_salt").encode()).hexdigest()

        cursor.execute("SELECT gender_name FROM staging.gender WHERE id = %s", (gender_id,))
        gender_name = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM dds.dim_patients 
            WHERE patient_hash = %s AND is_current = TRUE
        """, (full_hash,))
        existing = cursor.fetchone()

        if existing:
            if existing[2] != gender_name or str(existing[3]) != date_of_birth:
                cursor.execute("""
                    UPDATE dds.dim_patients
                    SET valid_to = now(), is_current = FALSE
                    WHERE patient_hash = %s AND is_current = TRUE
                """, (full_hash,))

                cursor.execute("""
                    INSERT INTO dds.dim_patients (patient_hash, gender_name, date_of_birth, age)
                    VALUES (%s, %s, %s, EXTRACT(YEAR FROM AGE(%s::date)))
                """, (full_hash, gender_name, date_of_birth, date_of_birth))
        else:
            cursor.execute("""
                INSERT INTO dds.dim_patients (patient_hash, gender_name, date_of_birth, age)
                VALUES (%s, %s, %s, EXTRACT(YEAR FROM AGE(%s::date)))
            """, (full_hash, gender_name, date_of_birth, date_of_birth))

        cursor.execute("UPDATE staging.audit_log SET processed = TRUE WHERE id = %s", (change_id,))

    conn.commit()
    cursor.close()


# ===== Загрузка процедур =====
def load_dim_procedures():
    pg_hook = PostgresHook(postgres_conn_id='postgres_dwh_connection')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT procedure_name
        FROM staging.procedure_table
    """)
    procedures = cursor.fetchall()

    for (procedure_name,) in procedures:
        cursor.execute("""
            SELECT procedure_key FROM dds.dim_procedures
            WHERE procedure_name = %s
        """, (procedure_name,))
        existing = cursor.fetchone()

        if existing:
            # Можно здесь добавить дополнительные поля, если нужно обновлять что-то кроме названия
            cursor.execute("""
                UPDATE dds.dim_procedures
                SET procedure_name = %s
                WHERE procedure_key = %s
            """, (procedure_name, existing[0]))
        else:
            cursor.execute("""
                INSERT INTO dds.dim_procedures (procedure_name)
                VALUES (%s)
            """, (procedure_name,))

    conn.commit()
    cursor.close()

def load_dim_mkb_codes():
    pg_hook = PostgresHook(postgres_conn_id='postgres_dwh_connection')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT mkb_code, diagnosis_name
        FROM staging.mkb_code
    """)
    mkb_codes = cursor.fetchall()

    '''for mkb_code, diagnosis_name in mkb_codes:
        cursor.execute("""
            SELECT mkb_code FROM dds.dim_mkb_codes
            WHERE mkb_code = %s
        """, (mkb_code,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE dds.dim_mkb_codes
                SET diagnosis_name = %s
                WHERE mkb_code = %s
            """, (diagnosis_name, mkb_code))
        else:
            cursor.execute("""
                INSERT INTO dds.dim_mkb_codes (mkb_code, diagnosis_name)
                VALUES (%s, %s)
            """, (mkb_code, diagnosis_name))'''
    for mkb_code, diagnosis_name in mkb_codes:
        cursor.execute("""
            INSERT INTO dds.dim_mkb_codes (mkb_code, diagnosis_name)
            VALUES (%s, %s)
            ON CONFLICT (mkb_code)
            DO UPDATE SET diagnosis_name = EXCLUDED.diagnosis_name
        """, (mkb_code, diagnosis_name))

    conn.commit()
    cursor.close()
	

# ===== Загрузка фактов результатов исследований =====
def load_fact_results():
    pg_hook = PostgresHook(postgres_conn_id='postgres_dwh_connection')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO dds.fact_results (
            patient_key, procedure_key, mkb_code, study_date,
            image_path, result_inference, final_diagnosis, cost
        )
        SELECT 
            dp.patient_key,
            dp2.procedure_key,
            mk.mkb_code,
            pr.study_date,
            pr.image_path,
            pr.result_inference,
            pr.final_diagnosis,
            pr.cost
        FROM staging.patient_results pr
        JOIN staging.patients p ON pr.patient_id = p.id
        JOIN dds.dim_patients dp ON md5(p.patient_uuid || '_salt') = dp.patient_hash AND dp.is_current = TRUE
        LEFT JOIN staging.procedure_table pt ON pt.id = pr.procedure_id
        LEFT JOIN dds.dim_procedures dp2 ON dp2.procedure_name = pt.procedure_name AND dp2.is_current = TRUE
        LEFT JOIN staging.mkb_code mkstg ON mkstg.id = pr.mkb_id
        LEFT JOIN dds.dim_mkb_codes mk ON mk.mkb_code = mkstg.mkb_code
        WHERE pr.load_date > COALESCE((SELECT MAX(load_date) FROM dds.fact_results), '1970-01-01')
    """)

    conn.commit()
    cursor.close()


# ===== Загрузка анамнеза =====
def load_fact_anamnesis():
    pg_hook = PostgresHook(postgres_conn_id='postgres_dwh_connection')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO dds.fact_anamnesis (
            patient_key, anamnesis_description, anamnesis_date
        )
        SELECT 
            dp.patient_key,
            pa.anamnesis_description,
            pa.date_anamnesis
        FROM staging.patient_anamnesis pa
        JOIN staging.patients p ON pa.patient_id = p.id
        JOIN dds.dim_patients dp ON md5(p.patient_uuid || '_salt') = dp.patient_hash AND dp.is_current = TRUE
        WHERE pa.load_date > COALESCE((SELECT MAX(load_date) FROM dds.fact_anamnesis), '1970-01-01')
    """)

    conn.commit()
    cursor.close()




# ====== DAG DEFINITION ======
with DAG(
    'Incremental_etl_from_staging_to_dds',
    default_args=default_args,
    description='Incremental load from staging to DDS with SCD2 and facts',
    #schedule_interval=timedelta(days=1),
    schedule_interval = None, # для целей тестирования
    catchup=True,
) as dag:

    start = EmptyOperator(task_id='start')

    dim_patients = PythonOperator(task_id='load_dim_patients', python_callable=scd2_update_dim_patients)
    dim_procedures = PythonOperator(task_id='load_dim_procedures', python_callable=load_dim_procedures)
    dim_mkb_codes = PythonOperator(task_id='load_dim_mkb_codes', python_callable=load_dim_mkb_codes)

    fact_results = PythonOperator(task_id='load_fact_results', python_callable=load_fact_results)
    fact_anamnesis = PythonOperator(task_id='load_fact_anamnesis', python_callable=load_fact_anamnesis)

    end = EmptyOperator(task_id='end')

    start >> [dim_patients, dim_procedures, dim_mkb_codes]
    dim_patients >> [fact_results, fact_anamnesis]
    dim_procedures >> [fact_results, fact_anamnesis]
    dim_mkb_codes >> [fact_results, fact_anamnesis]
    [fact_results, fact_anamnesis] >> end