-- Создаем схему DDS
CREATE SCHEMA IF NOT EXISTS dds;

-- 1. Таблица пациентов (измерение) - обезличенная
CREATE TABLE IF NOT EXISTS dds.dim_patients (
    patient_key SERIAL PRIMARY KEY,
    patient_hash TEXT NOT NULL,  -- Хэш от UUID (md5(uuid + соль))
    gender_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
	age INT,  -- Возраст теперь просто поле, его считаем в ETL,
	valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Таблица процедур (измерение)
CREATE TABLE IF NOT EXISTS dds.dim_procedures (
    procedure_key SERIAL PRIMARY KEY,
    procedure_name TEXT NOT NULL UNIQUE,
	valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Таблица диагнозов МКБ (измерение)
CREATE TABLE IF NOT EXISTS dds.dim_mkb_codes (
    mkb_code TEXT PRIMARY KEY,
    diagnosis_name TEXT NOT NULL,
	--valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    --valid_to TIMESTAMP,
    --is_current BOOLEAN NOT NULL DEFAULT TRUE,
    --load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	--PRIMARY KEY (mkb_code, valid_from),
	-- Уникальность по mkb_code для внешних ключей
    --UNIQUE(mkb_code)
	load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Фактовая таблица результатов исследований
CREATE TABLE IF NOT EXISTS dds.fact_results (
    result_key BIGSERIAL PRIMARY KEY,
    patient_key INT NOT NULL REFERENCES dds.dim_patients(patient_key),
    procedure_key INT REFERENCES dds.dim_procedures(procedure_key),
    mkb_code TEXT REFERENCES dds.dim_mkb_codes(mkb_code),
    study_date DATE NOT NULL,
    image_path TEXT,
    result_inference TEXT,
    final_diagnosis TEXT,
    cost DECIMAL(10, 2),
    load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 5. Фактовая таблица анамнеза
CREATE TABLE IF NOT EXISTS dds.fact_anamnesis (
    anamnesis_key BIGSERIAL PRIMARY KEY,
    patient_key INT NOT NULL REFERENCES dds.dim_patients(patient_key),
    anamnesis_description TEXT NOT NULL,
    anamnesis_date DATE NOT NULL,
    --procedure_key INT REFERENCES dds.dim_procedures(procedure_key),
    load_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
--CREATE INDEX ON dds.fact_results(patient_key);
--CREATE INDEX ON dds.fact_results(study_date);
--CREATE INDEX ON dds.fact_anamnesis(patient_key);