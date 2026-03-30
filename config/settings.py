from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    RAW_PATH: str = "raw"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    STORAGE_CONTAINER_NAME: str = "transformzone-test"
    
    DATABASE_SERVER: str = ""
    DATABASE_NAME: str = ""
    DATABASE_USER: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_DRIVER: str = "ODBC Driver 17 for SQL Server"
    
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GOOGLE_API_KEY: str = ""
    
    PARSERS_DIR: str = "parsers"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
