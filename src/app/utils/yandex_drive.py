import os
from typing import Any
from urllib.parse import quote

import requests


class YandexDiskAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.headers = {
            "Authorization": f"OAuth {self.token}",
            "Content-type": "application/json"
        }

    def upload_file(self, local_file_path, remote_folder=""):
        """
        Загружает файл на Яндекс.Диск и возвращает публичную ссылку на него.

        :param local_file_path: Путь к локальному файлу (например, 'file.txt').
        :param remote_folder: Папка на Яндекс.Диске, куда будет загружен файл (опционально). На конце пути / не ставим
        :return: Публичная ссылка на загруженный файл.
        """
        # 1. Получаем URL для загрузки файла

        # Извлекаем имя файла из пути
        file_name = os.path.basename(local_file_path)

        # Формируем путь на Яндекс.Диске
        remote_path = f"{remote_folder}/{file_name}" if remote_folder else file_name
        remote_path = remote_path.replace("//", "/")  # Убираем дублирующие слеши

        # Кодируем путь перед отправкой
        encoded_path = quote(str(remote_path))

        # 2. Получение URL для загрузки
        upload_link = self._get_upload_link(encoded_path)



        # 3. Загрузка файла
        self._upload_file_to_link(local_file_path, upload_link)



        # 4. Публикация файла и получение ссылки

        res_url = self._publish_and_get_public_url(encoded_path)



        return res_url

    def _get_upload_link(self, remote_path):
        """Получает URL для загрузки файла."""
        response = requests.get(
            f"{self.base_url}/resources/upload",
            headers=self.headers,
            params={"path": remote_path, "overwrite": "true"}
        )
        if response.status_code != 200:
            error = response.json().get("message", "Unknown error")
            raise Exception(f"Ошибка при получении ссылки для загрузки: {error}")

        data = response.json()
        if data.get("templated", False):
            # Обработка шаблонизированного URL (если потребуется)
            raise Exception("Получен шаблонизированный URL, требуется дополнительная обработка")

        return data["href"]

    def _upload_file_to_link(self, local_file_path, upload_link):
        """Загружает файл по полученной ссылке."""
        with open(local_file_path, "rb") as file:
            response = requests.put(upload_link, data=file)
            if response.status_code not in (201, 202):
                raise Exception(f"Ошибка при загрузке файла: {response.text}")

    def _publish_and_get_public_url(self, remote_path):
        """Публикует файл и возвращает публичную ссылку."""
        # Согласно документации тут должен быть такой заголовок
        # Публикация файла
        response = requests.put(
            f"{self.base_url}/resources/publish",
            headers=self.headers,
            params={"path": remote_path}
        )
        if response.status_code != 200:
            raise Exception(f"Ошибка при публикации файла: {response.json()}")

        # Получение публичной ссылки
        response = requests.get(
            f"{self.base_url}/resources",
            headers=self.headers,
            params={"path": remote_path}
        )
        if response.status_code != 200:
            raise Exception(f"Ошибка при получении метаданных файла: {response.json()}")

        return response.json().get("public_url")

    def create_folder(self, remote_folder):
        """Создаёт папку на Яндекс.Диске."""
        url = f"{self.base_url}/resources"

        # Кодируем путь перед отправкой
        encoded_path = quote(remote_folder)

        params = {"path": encoded_path}

        response = requests.put(url, headers=self.headers, params=params)
        if response.status_code not in (200, 201):
            raise Exception(f"Ошибка при создании папки: {response.json()}")

    def check_file_exists(self, remote_path: str) -> Any | None:
        """
        Проверяет существование файла на Яндекс.Диске и возвращает его метаданные.

        :param remote_path: Путь к файлу на Яндекс.Диске (например, '/folder/file.jpg')
        :return: Словарь с метаданными файла или None если файл не найден
        :raises Exception: При ошибке запроса к API
        """
        encoded_path = quote(remote_path)
        response = requests.get(
            f"{self.base_url}/resources",
            headers=self.headers,
            params={"path": encoded_path, "fields": "size,modified,name,path"}
        )

        # Все успешные статусы
        if response.ok:
            return response.json()

        # Анализ ошибки
        error_data = response.json()
        error_message = error_data.get("message", "Неизвестная ошибка")
        error_description = error_data.get("description", "")

        if response.status_code == 404:
            raise FileNotFoundError(f"Файл не найден: {error_message} ({error_description})")
        else:
            raise Exception(f"Ошибка API Яндекс.Диска [{response.status_code}]: {error_message} - {error_description}")
