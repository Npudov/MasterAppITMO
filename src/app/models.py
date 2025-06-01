from datetime import date
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Integer, String, ForeignKey, Date, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config_database import settings

engine = create_async_engine(url=settings.DATABASE_URL_asyncpg, echo=False)  # строка подключения к БД

new_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with new_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    pass


class GenderModel(Base):
    __tablename__ = 'gender'

    id: Mapped[int] = mapped_column(primary_key=True)
    gender_name: Mapped[str] = mapped_column(unique=True, nullable=False)

    # Отношение один-ко-многим с таблицей Patients
    patients: Mapped[list["PatientModel"]] = relationship(back_populates="gender")


# Таблица Patients
class PatientModel(Base):
    __tablename__ = 'patients'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_uuid: Mapped[str] = mapped_column(String, nullable=False)
    gender_id: Mapped[int] = mapped_column(ForeignKey("gender.id"), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    surname: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)


    # Отношения с другими таблицами
    gender: Mapped["GenderModel"] = relationship(back_populates="patients")
    anamnesis: Mapped[list["PatientAnamnesisModel"]] = relationship(back_populates="patient")
    results: Mapped[list["PatientResultsModel"]] = relationship(back_populates="patient")

    @property
    def age(self) -> int:
        """Вычисляет возраст пациента на основе даты рождения."""
        today = date.today()
        age = today.year - self.date_of_birth.year
        # Корректировка, если день рождения еще не наступил в этом году
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age


# Таблица PatientAnamnesis
class PatientAnamnesisModel(Base):
    __tablename__ = 'patient_anamnesis'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    anamnesis_description: Mapped[str] = mapped_column(String, nullable=False)
    date_anamnesis: Mapped[date] = mapped_column(Date, nullable=False)
    #procedure_id: Mapped[int] = mapped_column(ForeignKey("procedure.id"), nullable=True)

    # Отношение многие-к-одному с таблицей Patients
    patient: Mapped["PatientModel"] = relationship(back_populates="anamnesis")


# Таблица MKB_code
class MKBCodeModel(Base):
    __tablename__ = 'mkb_code'

    id: Mapped[int] = mapped_column(primary_key=True)
    mkb_code: Mapped[str] = mapped_column(String, nullable=False)
    diagnosis_name: Mapped[str] = mapped_column(String, nullable=False)

    # Отношение один-ко-многим с таблицей Patient_results
    patient_results: Mapped[list["PatientResultsModel"]] = relationship(
        back_populates="mkb_code"
    )


# Таблица Procedure
class ProcedureModel(Base):
    __tablename__ = 'procedure'

    id: Mapped[int] = mapped_column(primary_key=True)
    procedure_name: Mapped[str] = mapped_column(String, nullable=False)

    #Отношение один-ко-многим с таблицей Patient_results
    patient_procedure_results: Mapped[list["PatientResultsModel"]] = relationship(back_populates="procedure")


# Таблица Patient_results
class PatientResultsModel(Base):
    __tablename__ = 'patient_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    mkb_id: Mapped[int] = mapped_column(ForeignKey("mkb_code.id"), nullable=True)
    image_path: Mapped[str] = mapped_column(String, nullable=True)
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    result_inference: Mapped[str] = mapped_column(String, nullable=True)
    final_diagnosis: Mapped[str] = mapped_column(String, nullable=True)
    procedure_id: Mapped[int] = mapped_column(ForeignKey("procedure.id"), nullable=True)
    cost: Mapped[int] = mapped_column(Integer, nullable=True)

    # Отношения с другими таблицами
    patient: Mapped["PatientModel"] = relationship(back_populates="results")
    mkb_code: Mapped["MKBCodeModel"] = relationship(back_populates="patient_results")
    # Отношение многие-к-одному с таблицей Procedure
    procedure: Mapped["ProcedureModel"] = relationship(back_populates="patient_procedure_results")


async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
