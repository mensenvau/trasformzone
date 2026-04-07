from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    RAW_PATH: str = "raw"
    PARSERS_DIR: str = "parsers"

    DATABASE_NAME: str = ""
    DATABASE_SERVER: str = ""
    DATABASE_USER: Optional[str] = None
    DATABASE_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DATABASE_PASSWORD: Optional[str] = None
    
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    
    STORAGE_CONTAINER_NAME: str = "transformzone-test"
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
