# Master app

## Application Startup

Run as a desktop application:

```
uv run flet run
```

Run as a web application:

```
uv run flet run --web
```

For a more detailed review of the launch, see [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Building the app

### Windows

```
flet build windows -v
```

For more assembly details for Windows, see [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

## Installing dependencies
First, install the dependencies:

```
pip install -r requirements.txt
```

## Launching models
Classification, detection, and segmentation models work on ports 8001, 8002, and 8003
To run a model, such as classification, run the command:

```
python -m uvicorn src.app.inferenceApi.yoloClassificationModelUltralytics:app --port 8001 --reload
```
You can check the operation of the models through the UI interface of FastAPI itself.
To fully verify the operation of the application itself, you need to obtain a Yandex Api debugging token.

## Launching a database with patient data
In the src/app/postgres-docker folder, run docker-compose:

```
docker compose build
```
```
docker compose up -d
```

## Airflow
The src/airflow folder contains the SQL scripts and dags used in airflow. The entire network configuration for connections to the patient database and the developed storage was set in Airflow.

---
---

## Запуск приложения


Запустить как десктоп приложение:

```
uv run flet run
```

Запустить как веб приложение:

```
uv run flet run --web
```

Для более детального рассмотрения запуска, смотреть [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Сборка приложения

### Windows

```
flet build windows -v
```

Для больших деталей по сборке для Windows, смотреть [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

## Установка зависимостей
Для начала установите зависимости:

```
pip install -r requirements.txt
```

## Запуск моделей
Модели классификации, детекции и сегментации работают на портах 8001, 8002, 8003
Для запуска модели,например классификации, выполните команду:

```
python -m uvicorn src.app.inferenceApi.yoloClassificationModelUltralytics:app --port 8001 --reload
```
Проверку работу моделей можно провести через интерфейс UI самого FastApi.
Для полной проверки работы самого приложения нужно получение отладочного токена YandexApi.

## Запуск БД с данными пациентов
В папке src/app/postgres-docker запустите docker-compose:
```
docker compose build
```
```
docker compose up -d
```

## Airflow
В папке src/airflow находятся SQL скрипты и dags, используемые в airflow. В Airflow была задана вся сетевая конфигурация для соединений с базой пациентов и разработанным хранилищем
