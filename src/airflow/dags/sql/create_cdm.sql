-- Создаем схему CDM
CREATE SCHEMA IF NOT EXISTS cdm;

--Распределение степеней сколиоза между мужчинами и женщинами
CREATE OR REPLACE VIEW cdm.scoliosis_distribution_by_gender AS
SELECT
    dp.gender_name,
    CASE
        WHEN fr.final_diagnosis ILIKE '%сколиоз отсутствует%' THEN 'Нет сколиоза'
        WHEN fr.final_diagnosis ILIKE '%первой степени%' THEN 'Сколиоз 1 степени'
        WHEN fr.final_diagnosis ILIKE '%второй степени%' THEN 'Сколиоз 2 степени'
        WHEN fr.final_diagnosis ILIKE '%третьей степени%' THEN 'Сколиоз 3 степени'
        ELSE 'Не определено'
    END AS scoliosis_stage,
    COUNT(*) AS patient_count
FROM dds.fact_results fr
JOIN dds.dim_patients dp ON fr.patient_key = dp.patient_key
WHERE fr.load_date >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY dp.gender_name, scoliosis_stage;


--Распределение степеней сколиоза по возрастным диапазонам между мужчинами и женщинами
CREATE OR REPLACE VIEW cdm.scoliosis_distribution_by_age_gender AS
SELECT
    dp.gender_name,
    CASE
        WHEN dp.age BETWEEN 0 AND 17 THEN '0-17'
        WHEN dp.age BETWEEN 18 AND 30 THEN '18-30'
        WHEN dp.age BETWEEN 31 AND 45 THEN '31-45'
        WHEN dp.age BETWEEN 46 AND 60 THEN '46-60'
        ELSE '60+'
    END AS age_range,
    CASE
        WHEN fr.final_diagnosis ILIKE '%сколиоз отсутствует%' THEN 'Нет сколиоза'
        WHEN fr.final_diagnosis ILIKE '%первой степени%' THEN 'Сколиоз 1 степени'
        WHEN fr.final_diagnosis ILIKE '%второй степени%' THEN 'Сколиоз 2 степени'
        WHEN fr.final_diagnosis ILIKE '%третьей степени%' THEN 'Сколиоз 3 степени'
        ELSE 'Не определено'
    END AS scoliosis_stage,
    COUNT(*) AS patient_count
FROM dds.fact_results fr
JOIN dds.dim_patients dp ON fr.patient_key = dp.patient_key
WHERE fr.load_date >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY dp.gender_name, age_range, scoliosis_stage;


--Распределение стоимости страховых случаев со сколиозом по возрастным диапазонам
CREATE OR REPLACE VIEW cdm.scoliosis_cost_distribution_by_age AS
SELECT
    CASE
        WHEN dp.age BETWEEN 0 AND 17 THEN '0-17'
        WHEN dp.age BETWEEN 18 AND 30 THEN '18-30'
        WHEN dp.age BETWEEN 31 AND 45 THEN '31-45'
        WHEN dp.age BETWEEN 46 AND 60 THEN '46-60'
        ELSE '60+'
    END AS age_range,
    SUM(fr.cost) AS total_case_cost
FROM dds.fact_results fr
JOIN dds.dim_patients dp ON fr.patient_key = dp.patient_key
WHERE fr.final_diagnosis ILIKE '%сколиоз%' AND fr.load_date >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY age_range;

--Распределение стоимости страховых случаев со сколиозом по степеням сколиоза
CREATE OR REPLACE VIEW cdm.scoliosis_cost_distribution_by_stage AS
SELECT
    CASE
        WHEN fr.final_diagnosis ILIKE '%сколиоз отсутствует%' THEN 'Нет сколиоза'
        WHEN fr.final_diagnosis ILIKE '%первой степени%' THEN 'Сколиоз 1 степени'
        WHEN fr.final_diagnosis ILIKE '%второй степени%' THEN 'Сколиоз 2 степени'
        WHEN fr.final_diagnosis ILIKE '%третьей степени%' THEN 'Сколиоз 3 степени'
        ELSE 'Не определено'
    END AS scoliosis_stage,
    SUM(fr.cost) AS total_case_cost
FROM dds.fact_results fr
WHERE fr.final_diagnosis ILIKE '%сколиоз%' AND fr.load_date >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY scoliosis_stage;

