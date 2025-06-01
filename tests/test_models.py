from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from src.app.models import (
    GenderModel,
    PatientModel,
    PatientAnamnesisModel,
    MKBCodeModel,
    ProcedureModel,
    PatientResultsModel,
    Base
)

# Строка подключения для временной базы данных (SQLite в памяти)
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"


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
async def gender_and_patient(session: AsyncSession):
    # Создаем пол
    gender = GenderModel(gender_name="Male")
    session.add(gender)
    await session.flush()  # чтобы gender.id уже был доступен без коммита

    # Создаем пациента
    patient = PatientModel(
        patient_uuid="some-uuid",  # тут можно вставить любой uuid
        gender_id=gender.id,
        date_of_birth=date(1990, 1, 1),
        surname="Doe",
        name="John",
        middle_name="Smith"
    )
    session.add(patient)
    await session.commit()

    return patient, gender


# Тестирование создания записи о поле
@pytest.mark.asyncio
async def test_create_gender(session: AsyncSession):
    gender = GenderModel(gender_name="Female")
    session.add(gender)
    await session.commit()

    result = await session.execute(select(GenderModel).filter_by(gender_name="Female"))
    db_gender = result.scalar_one()

    assert db_gender.gender_name == "Female"


# Тестирование создания пациента и проверки связи с полом
@pytest.mark.asyncio
async def test_create_patient_and_gender(gender_and_patient, session: AsyncSession):
    patient, gender = gender_and_patient

    # Проверим, что пациент добавлен
    result = await session.execute(select(PatientModel).filter_by(id=patient.id))
    db_patient = result.scalar_one()

    assert db_patient.surname == "Doe"
    assert db_patient.gender_id == gender.id

    # Проверим, что связь работает
    assert db_patient.gender.gender_name == "Male"


# Тестирование создания анамнеза для пациента
@pytest.mark.asyncio
async def test_create_patient_anamnesis(gender_and_patient, session: AsyncSession):
    patient, _ = gender_and_patient

    anamnesis = PatientAnamnesisModel(
        patient_id=patient.id,
        anamnesis_description="Anamnesis description",
        date_anamnesis=date(2020, 5, 15)
    )
    session.add(anamnesis)
    await session.commit()

    # Проверяем, что анамнез добавлен
    result = await session.execute(select(PatientAnamnesisModel).filter_by(patient_id=patient.id))
    db_anamnesis = result.scalar_one()

    assert db_anamnesis.anamnesis_description == "Anamnesis description"
    assert db_anamnesis.patient_id == patient.id


# Тестирование создания и извлечения записи о результате пациента
@pytest.mark.asyncio
async def test_create_patient_result(gender_and_patient, session: AsyncSession):
    patient, _ = gender_and_patient
    procedure = ProcedureModel(procedure_name="Blood Test")
    session.add(procedure)
    await session.commit()

    result = PatientResultsModel(
        patient_id=patient.id,
        study_date=date(2022, 6, 1),
        result_inference="Positive",
        procedure_id=procedure.id
    )
    session.add(result)
    await session.commit()

    # Проверяем, что результат добавлен
    result_query = await session.execute(select(PatientResultsModel).filter_by(patient_id=patient.id))
    db_result = result_query.scalar_one()

    assert db_result.result_inference == "Positive"
    assert db_result.study_date == date(2022, 6, 1)
    assert db_result.procedure.procedure_name == "Blood Test"


# Тестирование удаления пациента
@pytest.mark.asyncio
async def test_delete_patient(gender_and_patient, session: AsyncSession):
    patient, _ = gender_and_patient

    # Удаляем пациента
    await session.delete(patient)
    await session.commit()

    # Проверяем, что пациент удален
    result = await session.execute(select(PatientModel).filter_by(id=patient.id))
    db_patient = result.scalar_one_or_none()

    assert db_patient is None


@pytest.mark.asyncio
async def test_create_procedure(session: AsyncSession):
    procedure = ProcedureModel(procedure_name="X-Ray")
    session.add(procedure)
    await session.commit()

    result = await session.execute(select(ProcedureModel).filter_by(procedure_name="X-Ray"))
    db_procedure = result.scalar_one()

    assert db_procedure.procedure_name == "X-Ray"


# Тестирование создания записи о МКБ-коде
@pytest.mark.asyncio
async def test_create_mkb_code(session: AsyncSession):
    mkb_code = MKBCodeModel(mkb_code="A00", diagnosis_name="Cholera")
    session.add(mkb_code)
    await session.commit()

    result = await session.execute(select(MKBCodeModel).filter_by(mkb_code="A00"))
    db_mkb_code = result.scalar_one()

    assert db_mkb_code.mkb_code == "A00"
    assert db_mkb_code.diagnosis_name == "Cholera"
