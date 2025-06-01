import pytest
from datetime import date, datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.app.models import PatientModel, PatientAnamnesisModel, MKBCodeModel, Base, GenderModel
from src.app.utils_query_db import find_patient, save_results_inference_to_db, find_anamnesis_patients, \
    get_unspecified_scoliosis_id

# Строка подключения для временной базы данных (SQLite в памяти)
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:?charset=utf8"


@pytest_asyncio.fixture(scope="session")
async def engine():
    # Используем SQLite в памяти для тестов
    engine = create_async_engine(DATABASE_URL_TEST, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def setup_test_data(session):
    # Создаем гендеры для использования в тестах
    male_gender = GenderModel(gender_name="Male")
    female_gender = GenderModel(gender_name="Female")
    session.add(male_gender)
    session.add(female_gender)
    await session.commit()

    # Создаем тестовых пациентов
    patient1 = PatientModel(
        patient_uuid="test-uuid1",
        surname="Smith",
        name="John",
        date_of_birth=date(1990, 1, 1),
        gender_id=male_gender.id  # Привязываем к гендеру
    )

    patient2 = PatientModel(
        patient_uuid="test-uuid2",
        surname="Doe",
        name="Jane",
        date_of_birth=date(1985, 5, 20),
        gender_id=female_gender.id  # Привязываем к гендеру
    )

    patient3 = PatientModel(
        patient_uuid="test-uuid3",
        surname="White",
        name="Walter",
        date_of_birth=date(1970, 12, 10),
        gender_id=male_gender.id  # Привязываем к гендеру
    )

    session.add(patient1)
    session.add(patient2)
    session.add(patient3)
    await session.commit()

    # Добавляем диагнозы
    mkb_code = MKBCodeModel(
        mkb_code="М41.9",
        diagnosis_name="Сколиоз неуточненный"
    )
    session.add(mkb_code)
    await session.commit()

    # Добавляем анамнез для одного пациента
    anamnesis = PatientAnamnesisModel(
        patient_id=patient3.id,
        anamnesis_description="Previous fractures",
        date_anamnesis=datetime.now()
    )
    session.add(anamnesis)
    await session.commit()

    return {
        "patient1": patient1,
        "patient2": patient2,
        "patient3": patient3,
        "mkb_code": mkb_code,
        "anamnesis": anamnesis
    }


@pytest.mark.asyncio
async def test_find_patient(session: AsyncSession, setup_test_data):
    patient = setup_test_data["patient1"]

    found_patient = await find_patient(
        session, "Smith", "John", "01.01.1990", "test-uuid1"
    )

    assert found_patient is not None
    assert found_patient.surname == "Smith"
    assert found_patient.name == "John"


@pytest.mark.asyncio
async def test_save_results_inference_to_db(session: AsyncSession, setup_test_data):
    patient = setup_test_data["patient2"]
    mkb_code = setup_test_data["mkb_code"]

    # Добавляем тестовый диагноз
    inference_result = {
        "top_class_name": "normal spine"
    }
    await save_results_inference_to_db(session, patient.id, "http://example.com/image.jpg", inference_result)

    # Явно загружаем пациента с результатами
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(PatientModel)
        .filter_by(id=patient.id)
        .options(selectinload(PatientModel.results))  # Предзагрузка результатов
    )
    db_patient = result.scalar_one()

    assert db_patient.results
    assert db_patient.results[0].result_inference == "normal spine"
    assert db_patient.results[0].image_path == "http://example.com/image.jpg"


@pytest.mark.asyncio
async def test_find_anamnesis_patients(session: AsyncSession, setup_test_data):
    patient = setup_test_data["patient3"]
    anamnesis = setup_test_data["anamnesis"]

    found_anamnesis = await find_anamnesis_patients(session, patient.id)

    assert found_anamnesis == "Previous fractures"


@pytest.mark.asyncio
async def test_get_unspecified_scoliosis_id(session: AsyncSession, setup_test_data):
    mkb_code = setup_test_data["mkb_code"]

    mkb_id = await get_unspecified_scoliosis_id(session)

    assert mkb_id == mkb_code.id
