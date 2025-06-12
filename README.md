# Master app

## Запуск приложения

### uv

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
Для запуска модели,например классификации, выполните команду.
```
python -m uvicorn src.app.inferenceApi.yoloClassificationModelUltralytics:app --port 8001 --reload
```
Проверку работу моделей можно провести через интерфейс UI самого FastApi.
Для полной проверки работы самого приложения нужно получение отладочного токена YandexApi.

## Запуск БД с данными пациентов
В папке src/app/postgres-docker запустите docker-compose
```
docker compose build
```
```
docker compose up -d
```

## Airflow
В папке находятся скрипты, используемые в airflow. В Airflow была задана вся сетевая конфигурация для соединений с базой пациентов и разработанным хранилищем