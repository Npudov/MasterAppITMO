import random

from sqlalchemy.future import select

from app.inferenceApi.config_сlass_inference import *
from app.models import *


async def find_patient(session: AsyncSession, surname: str, name: str, birthdate: str, uuid: str):
    # Преобразуем строку с датой в объект datetime.date
    try:
        birthdate = datetime.strptime(birthdate, "%d.%m.%Y").date()
    except ValueError:
        return None  # Если дата невалидна

    # Формируем запрос
    stmt = select(PatientModel).filter(
        PatientModel.patient_uuid == uuid,
        PatientModel.surname == surname,
        PatientModel.name == name,
        PatientModel.date_of_birth == birthdate
    )

    result = await session.execute(stmt)
    patient = result.scalars().first()  # Получаем первого найденного пациента

    return patient


async def save_results_inference_to_db(session: AsyncSession, patient_id, image_url, result):
    """Сохраняет результаты анализа в базу данных"""
    mkb_id = None

    top_class: str = result['top_class_name']

    diagnosis_keys = [key.lower() for key in DIAGNOSIS_DICT.keys()]

    if top_class.lower() in diagnosis_keys:
        mkb_id = await get_unspecified_scoliosis_id(session)

    db_result = PatientResultsModel(
        patient_id=patient_id,
        mkb_id=mkb_id,
        image_path=image_url,
        study_date=date.today(),
        result_inference=f"{top_class}",
        final_diagnosis=f"{DIAGNOSIS_DICT[top_class]}",
        cost=round(random.uniform(1000, 4000), 2)
    )
    session.add(db_result)
    await session.commit()


async def find_anamnesis_patients(session: AsyncSession, patient_id):
    # Формируем запрос
    stmt = select(PatientAnamnesisModel).filter(
        PatientAnamnesisModel.patient_id == patient_id
    )

    result = await session.execute(stmt)
    patient = result.scalars().first()  # Получаем первого найденного пациента

    return patient.anamnesis_description


async def get_unspecified_scoliosis_id(session: AsyncSession) -> int | None:
    '''stmt = select(MKBCodeModel).where(func.lower(MKBCodeModel.diagnosis_name) == "сколиоз неуточненный")
    result = await session.execute(stmt)
    record = result.scalars().first()
    return record.id if record else None'''
    stmt = select(MKBCodeModel)
    result = await session.execute(stmt)
    for record in result.scalars():
        if record.diagnosis_name.lower() == "сколиоз неуточненный":
            return record.id
    return None
