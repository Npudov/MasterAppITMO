import asyncio
import random
import uuid
from datetime import datetime, date, timedelta

import pandas as pd
from faker import Faker
from pathlib import Path

from app.models import (
    GenderModel,
    PatientModel,
    PatientAnamnesisModel,
    MKBCodeModel,
    ProcedureModel,
    engine,
    new_session,
    Base, setup_database
)

from app.inferenceApi.config_сlass_inference import DIAGNOSIS_DICT
from app.models import PatientResultsModel

# Инициализация Faker с русской локалью
fake = Faker('ru_RU')

DIAGNOSES = [
    ("М41.9", "Сколиоз неуточненный")
]

PROCEDURES = ["Рентгенография"]

# Получаем абсолютный путь к файлу независимо от места запуска скрипта
current_script_path = Path(__file__).parent  # Папка utils
project_root = current_script_path.parent  # Поднимаемся на уровень выше
csv_path = project_root / "assets" / "metadata_patients.csv"


async def fake_database(population: int):
    async with new_session() as session:
        # 1. Заполняем таблицу gender
        genders = [
            GenderModel(gender_name="Мужской"),
            GenderModel(gender_name="Женский"),
        ]
        session.add_all(genders)
        await session.flush()

        # 2. Заполняем таблицу mkb_code
        mkb_codes = [
            MKBCodeModel(mkb_code=code, diagnosis_name=name)
            for code, name in DIAGNOSES
        ]
        session.add_all(mkb_codes)
        await session.flush()

        # 3. Генерация 100 пациентов
        patients = []
        for _ in range(population):
            gender = random.choice(genders)

            # Генерация ФИО в зависимости от пола
            if gender.gender_name == "Мужской":
                surname = fake.last_name_male()
                first_name = fake.first_name_male()
                middle_name = fake.middle_name_male()
            elif gender.gender_name == "Женский":
                surname = fake.last_name_female()
                first_name = fake.first_name_female()
                middle_name = fake.middle_name_female()

            # Дата рождения (от 18 до 90 лет назад)
            birth_date = fake.date_of_birth(minimum_age=5, maximum_age=80)
            formatted_birth_date = birth_date.strftime("%d.%m.%Y")  # Преобразуем в нужный формат

            patient = PatientModel(
                gender_id=gender.id,
                surname=surname,
                name=first_name,
                middle_name=middle_name,
                date_of_birth=datetime.strptime(formatted_birth_date, "%d.%m.%Y").date(),
                patient_uuid=str(uuid.uuid4())
            )
            patients.append(patient)

        session.add_all(patients)
        await session.flush()

        # Генерация процедур
        procedures = [ProcedureModel(procedure_name=proc_name) for proc_name in PROCEDURES]
        session.add_all(procedures)
        await session.flush()

        anamnes_df = pd.read_csv(csv_path)

        # 4. Генерация анамнезов
        for patient in patients:
            random_number = random.randint(0, anamnes_df.shape[0])

            # Дата анамнеза должна быть после даты рождения
            min_date = date.today() - timedelta(days=random.randint(1, 365) * random.randint(1, 5))
            max_date = date.today()

            # Гарантируем, что дата анамнеза не в будущем
            if min_date > max_date:
                min_date = max_date - timedelta(days=365)

            anamnesis_date = fake.date_between_dates(
                date_start=min_date,
                date_end=max_date
            )

            anamnesis = PatientAnamnesisModel(
                patient_id=patient.id,
                anamnesis_description=anamnes_df.at[random_number, 'anamnesis'],
                date_anamnesis=anamnesis_date
            )
            session.add(anamnesis)

        # 5. Генерация результатов диагностики
        for patient in patients:
            # Выбираем случайный результат с заданными вероятностями
            rand = random.random()
            if rand <= 0.2:
                result = "normal spine"
            elif rand <= 0.6:
                result = "light scoliosis spine"
            elif rand <= 0.8:
                result = "mid scoliosis spine"
            else:
                result = "serious scoliosis spine"

            # Рассчитываем минимальную дату исследования:
            # Максимум из (текущая дата - 2 года) и (дата рождения + 5 лет)
            min_date_candidates = [
                date.today() - timedelta(days=365 * 2),  # 2 года назад от сегодня
                patient.date_of_birth + timedelta(days=365 * 5)  # 5 лет после рождения
            ]
            min_date = max(min_date_candidates)
            max_date = date.today()  # Сегодняшняя дата

            # Если минимальная дата получилась больше максимальной (например, для очень молодых пациентов)
            # то используем дату рождения + 5 лет
            if min_date > max_date:
                min_date = patient.date_of_birth + timedelta(days=365 * 5)

            study_date = fake.date_between_dates(
                date_start=min_date,
                date_end=max_date
            )

            # Создаем запись о результате
            result_record = PatientResultsModel(
                patient_id=patient.id,
                mkb_id=mkb_codes[0].id if result != "normal spine" else None,
                study_date=study_date,
                result_inference=result,
                final_diagnosis=DIAGNOSIS_DICT[result],
                procedure_id=procedures[0].id,
                cost=random.randint(1000, 5000)  # Случайная стоимость процедуры
            )
            session.add(result_record)

        await session.commit()
        print(f"База данных заполнена: {population} пациентов")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(setup_database())
        loop.run_until_complete(fake_database(1000))
    finally:
        loop.close()
