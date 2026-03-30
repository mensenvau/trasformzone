from urllib.parse import quote_plus
from config.settings import get_settings

def get_connection_string() -> str:
    settings = get_settings()
    
    if settings.DATABASE_USER and settings.DATABASE_PASSWORD:
        password = quote_plus(settings.DATABASE_PASSWORD)
        conn_str = (
            f"mssql+pyodbc://{settings.DATABASE_USER}:{password}"
            f"@{settings.DATABASE_SERVER}/{settings.DATABASE_NAME}"
            f"?driver={quote_plus(settings.DATABASE_DRIVER)}"
            f"&TrustServerCertificate=yes"
        )
    else:
        conn_str = (
            f"mssql+pyodbc://@{settings.DATABASE_SERVER}/{settings.DATABASE_NAME}"
            f"?driver={quote_plus(settings.DATABASE_DRIVER)}"
            f"&Authentication=ActiveDirectoryMsi"
        )
    
    return conn_str
