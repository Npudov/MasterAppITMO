import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    YANDEX_OAUTH_TOKEN: str

    model_config = SettingsConfigDict(env_file=f"{pathlib.Path(__file__).resolve().parent}/yandex.env")


settings_yandex = Settings()
