import base64
import json
import os
from datetime import datetime

import flet as ft
import requests
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import new_session, PatientResultsModel, PatientModel
from app.utils.utils_format_detection_results import format_detection_results
from app.utils.yandex_drive import YandexDiskAPI
from app.utils_query_db import find_patient, save_results_inference_to_db, find_anamnesis_patients
from yandexConfig.settings_yandex_api import Settings

# Конфигурация Yandex Disk
settings = Settings()
YANDEX_TOKEN = settings.YANDEX_OAUTH_TOKEN
yandex = YandexDiskAPI(YANDEX_TOKEN)

# Глобальные переменные для хранения состояния
current_patient = None
current_image_path = None

PORT_CLASSIFICATION = 8001
PORT_XrayDETECTION = 8002
PORT_CTDETECTION = 8003

YANDEX_DISK_PATH = "/DiplomaApp/XrayPictures"
BASE_URL_CLASSIFICATION = f"http://localhost:{PORT_CLASSIFICATION}"
BASE_URL_XrayDETECTION = f"http://localhost:{PORT_XrayDETECTION}"
BASE_URL_CTDETECTION = f"http://localhost:{PORT_CTDETECTION}"


def main(page: ft.Page):
    page.title = "Medical Analysis App"
    page.theme_mode = ft.ThemeMode.LIGHT

    differential_diagnostic_button = ft.ElevatedButton("Запустить процесс дифференциальной диагностики",
                                                       style=ft.ButtonStyle(
                                                           bgcolor=ft.colors.GREEN_100,
                                                           color=ft.colors.GREEN_900),
                                                       on_click=lambda e: page.go("/inference"))
    differential_diagnostic_button.disabled = True

    async def select_patient(e):
        global current_patient
        # Получаем данные из полей ввода
        surname = surname_field.value
        name = name_field.value
        birthdate = birthdate_field.value
        uuid = uuid_field.value

        # Пытаемся найти пациента в базе данных
        async with new_session() as session:
            patient = await find_patient(session, surname, name, birthdate, uuid)

            if patient:
                current_patient = patient  # Сохраняем выбранного пациента

                # Тянем анамнез пациента по его ID
                anamnesis = await find_anamnesis_patients(session, patient.id)

                # Подставляем анамнез в поле
                anamnesis_field.value = anamnesis

                # Если пациент найден, выводим информацию и показываем кнопку загрузки изображения
                patient_info.value = f"Пациент найден: {patient.surname} {patient.name}, {patient.date_of_birth.strftime('%d.%m.%Y')}, UUID: {patient.patient_uuid}"

                differential_diagnostic_button.disabled = False
                upload_button.visible = True
                patient_info.visible = True
            else:
                # Если пациента не нашли
                patient_info.value = "Пациент не найден!"
                patient_info.visible = True
                upload_button.visible = False  # Скрываем кнопку загрузки изображения
                select_button.disabled = False  # Снова включаем кнопку "Выбрать пациента"
            page.update()

    async def check_and_prepare_diagnosis(e):
        global current_patient, current_image_path

        if not current_patient:
            diagnosis_result.value = "Сначала выберите пациента"
            page.update()
            return

        if not current_image_path:
            diagnosis_result.value = "Сначала загрузите изображение"
            page.update()
            return

        try:
            if isinstance(current_image_path, str):
                # 1. Проверяем существование файла на Яндекс.Диске
                file_name = os.path.basename(current_image_path)
                remote_path = f"{YANDEX_DISK_PATH}/{file_name}"

                # 1. Проверка файла на Яндекс.Диске
                try:
                    file_meta = yandex.check_file_exists(remote_path)
                    diagnosis_result.value = f"Файл найден: {file_meta['name']} ({file_meta['size']} bytes)"
                except FileNotFoundError:
                    diagnosis_result.value = "Файл не найден на Яндекс.Диске"
                    page.update()
                    return
                except Exception as e:
                    diagnosis_result.value = f"Ошибка Яндекс.Диска: {str(e)}"
                    page.update()
                    return

                # 2. Проверяем наличие записи в PatientResults
                if isinstance(current_patient, PatientResultsModel):
                    async with new_session() as session:
                        result = await session.execute(
                            select(PatientResultsModel)
                            .where(PatientResultsModel.patient_id == current_patient.id)
                            .where(PatientResultsModel.image_path.contains(file_name))
                        )
                        db_result = result.scalars().first()

                        if not db_result:
                            diagnosis_result.value = "Сначала выполните инференс для этого снимка"
                            page.update()
                            return

                        # 3. Если все проверки пройдены - показываем поле для диагноза
                        diagnosis_field.value = db_result.final_diagnosis or "Диагноз не введен"
                        diagnosis_field.visible = True
                        save_diagnosis_button.visible = True
                        diagnosis_result.value = "Можно ввести диагноз"

        except Exception as e:
            diagnosis_result.value = f"Ошибка проверки: {str(e)}"

        page.update()

    async def save_final_diagnosis(e):
        global current_patient, current_image_path

        # Сбросим предыдущий результат
        diagnosis_result.value = ""
        page.update()

        # Проверка введенного диагноза
        if not diagnosis_field.value or not diagnosis_field.value.strip():
            diagnosis_result.value = "Введите текст диагноза"
            page.update()
            return

        # Проверка наличия пациента и изображения
        if not current_patient or not hasattr(current_patient, 'id'):
            diagnosis_result.value = "Пациент не выбран"
            page.update()
            return

        if not current_image_path or not isinstance(current_image_path, str):
            diagnosis_result.value = "Изображение не загружено"
            page.update()
            return

        try:
            file_name = os.path.basename(current_image_path)
            diagnosis_text = diagnosis_field.value.strip()

            if isinstance(current_patient, PatientResultsModel):
                async with new_session() as session:

                    # Ищем запись в базе данных
                    result = await session.execute(
                        select(PatientResultsModel)
                        .where(PatientResultsModel.patient_id == current_patient.id)
                        .where(PatientResultsModel.image_path.contains(file_name))
                    )
                    db_result = result.scalars().first()

                    if not db_result:
                        diagnosis_result.value = "Не найдены результаты анализа для этого снимка"
                        page.update()
                        return

                    # Обновляем диагноз
                    db_result.final_diagnosis = diagnosis_text
                    await session.commit()

                    diagnosis_result.value = "Диагноз успешно сохранен!"
                    diagnosis_result.color = "green"

        except ValueError as ve:
            diagnosis_result.value = f"Ошибка данных: {str(ve)}"
            diagnosis_result.color = "red"
        except SQLAlchemyError as sae:
            diagnosis_result.value = f"Ошибка базы данных: {str(sae)}"
            diagnosis_result.color = "red"
            # Откатываем транзакцию в случае ошибки
            await session.rollback()
        except Exception as ex:
            diagnosis_result.value = f"Неожиданная ошибка: {str(ex)}"
            diagnosis_result.color = "red"
        finally:
            page.update()

    # Добавляем новые элементы в интерфейс
    diagnosis_field = ft.TextField(label="Окончательный диагноз", multiline=True)
    save_diagnosis_button = ft.ElevatedButton("Сохранить диагноз", on_click=save_final_diagnosis)
    diagnosis_result = ft.Text()

    # Добавляем новую функцию для вызова API инференса
    async def run_inference(e):
        global current_patient, current_image_path

        if not current_patient:
            inference_result.value = "Сначала выберите пациента"
            page.update()
            return

        if not image.src:
            inference_result.value = "Сначала загрузите изображение"
            page.update()
            return

        inference_result.value = "Идет анализ изображения..."
        progress_ring.visible = True
        page.update()

        try:
            # 1. Загрузка на Yandex Disk
            current_image_path = image.src
            if isinstance(current_patient, PatientModel):
                remote_folder = f"/DiplomaApp/XrayPictures"
                image_url = yandex.upload_file(current_image_path, remote_folder)
                # Отправка изображения на сервер
                with open(current_image_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post(
                        f"{BASE_URL_CLASSIFICATION}/predict",
                        files=files
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Формируем основную информацию
                        output = [
                            f"Топовый класс: {result['top_class_name']}",
                            f"Вероятность: {result['top_confidence'] * 100:.2f}%",
                            "\nВсе классы с вероятностями:"
                        ]

                        # Добавляем информацию по всем классам
                        for class_info in result['all_classes']:
                            output.append(
                                f"- {class_info['class_name']}: {class_info['confidence'] * 100:.2f}%"
                            )

                        # Объединяем все строки
                        inference_result.value = "\n".join(output)

                        async with new_session() as session:
                            # 3. Сохранение в БД
                            await save_results_inference_to_db(session=session,
                                                               patient_id=current_patient.id,
                                                               image_url=image_url,
                                                               result=result
                                                               )

                        # Показываем поле для диагноза после успешного инференса
                        diagnosis_field.visible = True
                        save_diagnosis_button.visible = True

                    else:
                        inference_result.value = f"Ошибка API: {response.text}"

        except Exception as e:
            inference_result.value = f"Ошибка соединения: {str(e)}"
        finally:
            progress_ring.visible = False
            page.update()


    def toggle_middlename(e):
        middlename_field.visible = not middlename_check.value
        #middlename_field.disabled = not middlename_check.value
        if not middlename_check.value:
            middlename_field.value = ""
        validate_fields()
        page.update()

    def clear_fields(e):
        surname_field.value = ""
        name_field.value = ""

        middlename_check.value = False
        middlename_field.value = ""
        middlename_field.visible = True

        birthdate_field.value = ""
        uuid_field.value = ""
        patient_info.visible = False
        error_text.value = ""
        error_text.visible = False

        upload_button.visible = False
        image.src = None
        image.visible = False  # Скрываем изображение
        select_button.disabled = True

        global current_patient
        global current_image_path
        current_patient = None
        current_image_path = None

        diagnosis_field.value = ""
        diagnosis_field.visible = False
        save_diagnosis_button.visible = False
        diagnosis_result.value = ""

        anamnesis_field.value = ""

        differential_diagnostic_button.disabled = True

        page.update()

    # Поля для данных
    surname_field = ft.TextField(label="Фамилия пациента", autofocus=True)
    name_field = ft.TextField(label="Имя пациента")
    middlename_check = ft.Checkbox(label="Нет отчества", value=False)
    middlename_field = ft.TextField(label="Отчество пациента", visible=True)
    birthdate_field = ft.TextField(label="Дата рождения (DD.MM.YYYY)")
    uuid_field = ft.TextField(label="UUID пациента")
    select_button = ft.ElevatedButton("Выбрать пациента", disabled=True)

    clear_button = ft.ElevatedButton("Очистить")

    # Для отображения информации о пациенте
    patient_info = ft.Text(visible=False)
    error_text = ft.Text(color="red", visible=False)
    progress_ring = ft.ProgressRing(visible=False)

    # Элементы для работы с изображением
    upload_button = ft.ElevatedButton(
        "Загрузить изображение",
        visible=False
    )
    image = ft.Image(visible=False)
    classification_file_picker = ft.FilePicker()
    page.overlay.append(classification_file_picker)

    # Детекция рентген снимка
    detection_image = ft.Image(visible=False, width=800, height=800)
    detection_result_text = ft.Text("Здесь будет результат детекции", size=20)
    detection_file_picker = ft.FilePicker()
    page.overlay.append(detection_file_picker)

    #Детекция КТ снимка
    ct_detection_image = ft.Image(visible=False, width=800, height=800)
    ct_detection_result_text = ft.Text("Здесь будет результат детекции", size=20)
    ct_detection_file_picker = ft.FilePicker()
    page.overlay.append(ct_detection_file_picker)

    def upload_detection_image(e: ft.FilePickerResultEvent):
        if e.files:
            # Очистка предыдущего результата
            detection_image.src_base64 = None
            detection_image.src = e.files[0].path
            detection_image.visible = True

            detection_result_text.value = "Здесь будет результат детекции"
            #scale_slider.visible = False  # сбрасываем слайдер
            page.update()

    def upload_ct_detection_image(e: ft.FilePickerResultEvent):
        if e.files:
            # Очистка предыдущего результата
            ct_detection_image.src_base64 = None
            ct_detection_image.src = e.files[0].path
            ct_detection_image.visible = True

            detection_result_text.value = "Здесь будет результат детекции"

            page.update()

    def run_detection(e):

        if not detection_image.src:
            detection_result_text.value = "Пожалуйста, выберите изображение"
            page.update()
            return

        detection_result_text.value = "Идет обработка изображения..."
        page.update()

        try:

            with open(detection_image.src, "rb") as f:
                files = {"file": f}

                response = requests.post(
                    f"{BASE_URL_XrayDETECTION}/detect",
                    files=files
                )

                if response.status_code == 200:
                    img_bytes = response.content
                    detection_image.src_base64 = base64.b64encode(img_bytes).decode("utf-8")

                    detection_image.visible = True

                    # Проверка содержимого заголовка
                    detection_results_header = response.headers.get("X-Detection-Results", "")
                    print(f"Detection Results Header: {detection_results_header}")

                    # Обновляем результаты
                    detections = json.loads(detection_results_header)

                    detection_result_text.value = format_detection_results(detections)



        except Exception as ex:
            detection_result_text.value = f"Ошибка: {str(ex)}"

        page.update()

    def run_ct_detection(e):

        if not ct_detection_image.src:
            ct_detection_result_text.value = "Пожалуйста, выберите изображение"
            page.update()
            return

        ct_detection_result_text.value = "Идет обработка изображения..."
        page.update()

        try:

            with open(ct_detection_image.src, "rb") as f:
                files = {"file": f}

                response = requests.post(
                    f"{BASE_URL_CTDETECTION}/detect",
                    files=files
                )

                if response.status_code == 200:
                    img_bytes = response.content
                    ct_detection_image.src_base64 = base64.b64encode(img_bytes).decode("utf-8")

                    ct_detection_image.visible = True

                    # Проверка содержимого заголовка
                    ct_detection_results_header = response.headers.get("X-Detection-Results", "")
                    print(f"Detection Results Header: {ct_detection_results_header}")

                    # Обновляем результаты
                    detections = json.loads(ct_detection_results_header)

                    ct_detection_result_text.value = format_detection_results(detections)



        except Exception as ex:
            ct_detection_result_text.value = f"Ошибка: {str(ex)}"

        page.update()

    def validate_fields(e=None):
        required_fields_filled = all([
            surname_field.value,
            name_field.value,
            birthdate_field.value,
            uuid_field.value
        ])

        # Проверяем отчество (если чекбокс "Нет отчества" не выбран)
        middlename_ok = middlename_check.value or bool(middlename_field.value)

        # Проверка формата даты
        date_valid = False
        if birthdate_field.value:
            try:
                datetime.strptime(birthdate_field.value, "%d.%m.%Y")
                date_valid = True
            except ValueError:
                date_valid = False

        select_button.disabled = not (required_fields_filled and middlename_ok and date_valid)
        page.update()




    birthdate_field.on_change = validate_fields

    def upload_image(e: ft.FilePickerResultEvent):
        if e.files:
            image.src = e.files[0].path
            image.visible = True
            page.update()

    # Поле для вывода результатов инференса
    inference_result = ft.Text("Результат инференса будет здесь", size=20)

    # Поле для анамнеза
    anamnesis_field = ft.TextField(label="Анамнез пациента", multiline=True)



    def clear_results_inference(e):
        image.src = None
        image.visible = False
        inference_result.value = "Результат инференса будет здесь"

        page.update()

    def clear_results_xray_detection(e):
        detection_image.src = None
        detection_image.src_base64 = None
        detection_image.visible = False

        detection_result_text.value = "Здесь будет результат детекции"

        detection_image.width = 800
        detection_image.height = 800

        page.update()

    def clear_results_ct_detection(e):
        ct_detection_image.src = None
        ct_detection_image.src_base64 = None
        ct_detection_image.visible = False

        ct_detection_result_text.value = "Здесь будет результат детекции"

        ct_detection_image.width = 800
        ct_detection_image.height = 800

        page.update()

    # Привязка обработчиков
    classification_file_picker.on_result = upload_image
    upload_button.on_click = lambda _: classification_file_picker.pick_files(
        allow_multiple=False,
        allowed_extensions=["jpg", "jpeg", "png"]
    )

    detection_file_picker.on_result = upload_detection_image
    ct_detection_file_picker.on_result = upload_ct_detection_image

    # Назначаем обработчики изменений
    surname_field.on_change = validate_fields
    name_field.on_change = validate_fields
    middlename_check.on_change = toggle_middlename
    middlename_field.on_change = validate_fields
    birthdate_field.on_change = validate_fields
    uuid_field.on_change = validate_fields
    select_button.on_click = select_patient
    clear_button.on_click = clear_fields

    # Главная страница
    def home_view():
        return ft.View(
            "/",
            controls=[
                ft.Column([
                    ft.Text("Выбор пациента", size=20, weight=ft.FontWeight.BOLD),
                    surname_field,
                    name_field,
                    middlename_check,
                    middlename_field,
                    birthdate_field,
                    uuid_field,
                    ft.Row([select_button, clear_button], spacing=10),
                    progress_ring,
                    patient_info,
                    error_text,
                    upload_button,
                    image,
                    ft.Divider(),
                    ft.Divider(),
                    ft.ElevatedButton("Анамнез", on_click=lambda e: page.go("/anamnesis")),
                    differential_diagnostic_button,
                    ft.ElevatedButton("Детекция рентген снимка", style=ft.ButtonStyle(
                        bgcolor=ft.colors.PURPLE_500,
                        color=ft.colors.WHITE
                    ), on_click=lambda e: page.go("/xray_detection")),
                    ft.ElevatedButton("Детекция (Сегментация) КТ снимка", style=ft.ButtonStyle(
                        bgcolor=ft.colors.YELLOW_400,  # насыщенный жёлтый фон
                        color=ft.colors.PURPLE_700  # тёмно-фиолетовый текст
                    ), on_click=lambda e: page.go("/ct_detection")),
                ], spacing=10)
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    # Страницы
    # Страница с анамнезом
    def anamnesis_view():
        return ft.View(
            "/anamnesis",
            controls=[ft.ElevatedButton("Назад", on_click=lambda e: page.go("/")), anamnesis_field],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    # Страница с дифференциальной диагностикой сколиоза
    def inference_view():
        return ft.View(
            "/inference",
            controls=[
                ft.ElevatedButton("Назад", on_click=lambda e: page.go("/")),
                image,
                inference_result,
                ft.ElevatedButton("Запустить дифференциальную диагностику сколиоза", on_click=run_inference),
                ft.ElevatedButton("Анамнез пациента", on_click=lambda e: page.go("/anamnesis")),
                ft.ElevatedButton("Очистить результат диагностики", style=ft.ButtonStyle(
                    bgcolor=ft.colors.RED_600,
                    color=ft.colors.WHITE
                ), on_click=clear_results_inference)
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    # страница с детектированием сколиоза
    def xray_detection_view():
        return ft.View(
            "/xray_detection",
            controls=[
                ft.ElevatedButton("Назад", on_click=lambda e: page.go("/")),
                ft.ElevatedButton("Загрузить снимок", style=ft.ButtonStyle(
                    bgcolor=ft.colors.ORANGE, color=ft.colors.PURPLE
                ), on_click=lambda _: detection_file_picker.pick_files(
                    allowed_extensions=["jpg", "jpeg", "png"])),
                detection_image,
                ft.ElevatedButton("Запустить детекцию", style=ft.ButtonStyle(
                    bgcolor=ft.colors.YELLOW_400,
                ), on_click=run_detection),
                detection_result_text,
                ft.ElevatedButton("Очистить результат детекции", style=ft.ButtonStyle(
                    bgcolor=ft.colors.RED_600,
                    color=ft.colors.WHITE
                ), on_click=clear_results_xray_detection)
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    # Страница с сегментацией позвоночника
    def ct_detection_view():
        return ft.View(
            "/ct_detection",
            controls=[
                ft.ElevatedButton("Назад", on_click=lambda e: page.go("/")),
                ft.ElevatedButton("Загрузить снимок", style=ft.ButtonStyle(
                    bgcolor=ft.colors.ORANGE, color=ft.colors.PURPLE
                ), on_click=lambda _: ct_detection_file_picker.pick_files(
                    allowed_extensions=["jpg", "jpeg", "png"])),
                ct_detection_image,
                ft.ElevatedButton("Запустить детекцию", style=ft.ButtonStyle(
                    bgcolor=ft.colors.YELLOW_400,
                ), on_click=run_ct_detection),
                ct_detection_result_text,
                ft.ElevatedButton("Очистить результат детекции", style=ft.ButtonStyle(
                    bgcolor=ft.colors.RED_600,
                    color=ft.colors.WHITE
                ), on_click=clear_results_ct_detection)
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    # Навигация
    def route_change(route):
        page.views.clear()
        if route.route == "/":
            page.views.append(home_view())
        elif route.route == "/anamnesis":
            page.views.append(anamnesis_view())
        elif route.route == "/inference":
            page.views.append(inference_view())
        elif route.route == "/xray_detection":
            page.views.append(xray_detection_view())
        elif route.route == "/ct_detection":
            page.views.append(ct_detection_view())
        page.update()

    page.on_route_change = route_change
    page.go("/")


ft.app(target=main, view=ft.WEB_BROWSER, port=8550)
