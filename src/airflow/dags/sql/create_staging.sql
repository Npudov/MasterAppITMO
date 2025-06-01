-- Убедимся, что схема staging существует
CREATE SCHEMA IF NOT EXISTS staging;

DROP TRIGGER IF EXISTS gender_updated_at_trigger ON staging.gender;
DROP TRIGGER IF EXISTS patients_updated_at_trigger ON staging.patients;
DROP TRIGGER IF EXISTS procedure_updated_at_trigger ON staging.procedure_table;
DROP TRIGGER IF EXISTS anamnesis_updated_at_trigger ON staging.patient_anamnesis;
DROP TRIGGER IF EXISTS results_updated_at_trigger ON staging.patient_results;

-- Создаем триггерную функцию для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Таблица gender
CREATE TABLE IF NOT EXISTS staging.gender (
    id SERIAL PRIMARY KEY,
    gender_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),  -- Добавляем поле для идентификации источника
	original_id INT,
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Создаем триггер для gender
CREATE TRIGGER gender_updated_at_trigger
BEFORE UPDATE ON staging.gender
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Таблица patients
CREATE TABLE IF NOT EXISTS staging.patients (
    id SERIAL PRIMARY KEY,
    patient_uuid TEXT NOT NULL,
    gender_id INT NOT NULL REFERENCES staging.gender(id),
    date_of_birth DATE NOT NULL,
    surname TEXT NOT NULL,
    name TEXT NOT NULL,
    middle_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),
    original_id INT,  -- ID из исходной системы
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Создаем триггер для patients
CREATE TRIGGER patients_updated_at_trigger
BEFORE UPDATE ON staging.patients
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Таблица procedure (переименовано в procedure_table, чтобы избежать конфликта с ключевым словом)
CREATE TABLE IF NOT EXISTS staging.procedure_table (
    id SERIAL PRIMARY KEY,
    procedure_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),
    original_id INT,
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Создаем триггер для procedure_table
CREATE TRIGGER procedure_updated_at_trigger
BEFORE UPDATE ON staging.procedure_table
FOR EACH ROW EXECUTE FUNCTION update_updated_at();



-- Таблица patient_anamnesis
CREATE TABLE IF NOT EXISTS staging.patient_anamnesis (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES staging.patients(id),
    anamnesis_description TEXT NOT NULL,
    date_anamnesis DATE NOT NULL,
    --procedure_id INT REFERENCES staging.procedure_table(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),
    original_id INT,
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Создаем триггер для patient_anamnesis
CREATE TRIGGER anamnesis_updated_at_trigger
BEFORE UPDATE ON staging.patient_anamnesis
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Таблица mkb_code
CREATE TABLE IF NOT EXISTS staging.mkb_code (
    id SERIAL PRIMARY KEY,
    mkb_code TEXT NOT NULL,
    diagnosis_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),
    original_id INT,
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Создаем триггер для mkb_code
CREATE TRIGGER mkb_code_updated_at_trigger
BEFORE UPDATE ON staging.mkb_code
FOR EACH ROW EXECUTE FUNCTION update_updated_at();



-- Таблица patient_results
CREATE TABLE IF NOT EXISTS staging.patient_results (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES staging.patients(id),
    mkb_id INT REFERENCES staging.mkb_code(id),
    image_path TEXT,
    study_date DATE NOT NULL,
    result_inference TEXT,
    final_diagnosis TEXT,
    procedure_id INT REFERENCES staging.procedure_table(id),
    cost DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR(50),
    original_id INT,
	load_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    --batch_id VARCHAR(50)  -- Для отслеживания загрузок
);

-- Создаем триггер для patient_results
CREATE TRIGGER results_updated_at_trigger
BEFORE UPDATE ON staging.patient_results
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE FUNCTION staging.log_table_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO staging.audit_log (table_name, operation, record_id, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id, to_jsonb(NEW));
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO staging.audit_log (table_name, operation, record_id, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO staging.audit_log (table_name, operation, record_id, old_data)
        VALUES (TG_TABLE_NAME, TG_OP, OLD.id, to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS staging.audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    record_id INT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'staging',
    processed BOOLEAN DEFAULT FALSE
);

DROP TRIGGER IF EXISTS trg_log_gender ON staging.gender;
DROP TRIGGER IF EXISTS trg_log_patients ON staging.patients;
DROP TRIGGER IF EXISTS trg_log_procedure_table ON staging.procedure_table;
DROP TRIGGER IF EXISTS trg_log_patient_anamnesis ON staging.patient_anamnesis;
DROP TRIGGER IF EXISTS trg_log_patient_results ON staging.patient_results;

CREATE TRIGGER trg_log_gender
AFTER INSERT OR UPDATE OR DELETE ON staging.gender
FOR EACH ROW EXECUTE FUNCTION staging.log_table_changes();

CREATE TRIGGER trg_log_patients
AFTER INSERT OR UPDATE OR DELETE ON staging.patients
FOR EACH ROW EXECUTE FUNCTION staging.log_table_changes();

CREATE TRIGGER trg_log_procedure_table
AFTER INSERT OR UPDATE OR DELETE ON staging.procedure_table
FOR EACH ROW EXECUTE FUNCTION staging.log_table_changes();

CREATE TRIGGER trg_log_patient_anamnesis
AFTER INSERT OR UPDATE OR DELETE ON staging.patient_anamnesis
FOR EACH ROW EXECUTE FUNCTION staging.log_table_changes();

CREATE TRIGGER trg_log_patient_results
AFTER INSERT OR UPDATE OR DELETE ON staging.patient_results
FOR EACH ROW EXECUTE FUNCTION staging.log_table_changes();



