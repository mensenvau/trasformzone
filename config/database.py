from urllib.parse import quote_plus
from config.settings import get_settings

def get_connection_string() -> str:
    """SQLAlchemy-compatible connection string for registry/data_writer."""
    s = get_settings()
    if s.DATABASE_USER and s.DATABASE_PASSWORD:
        return (
            f"mssql+pyodbc://{s.DATABASE_USER}:{quote_plus(s.DATABASE_PASSWORD)}"
            f"@{s.DATABASE_SERVER}/{s.DATABASE_NAME}"
            f"?driver={quote_plus(s.DATABASE_DRIVER)}&TrustServerCertificate=yes"
        )
    return (
        f"mssql+pyodbc://@{s.DATABASE_SERVER}/{s.DATABASE_NAME}"
        f"?driver={quote_plus(s.DATABASE_DRIVER)}&Authentication=ActiveDirectoryMsi"
    )

def get_pyodbc_string() -> str:
    """Raw pyodbc connection string for direct cursor-based queries."""
    s = get_settings()
    conn = f"DRIVER={{{s.DATABASE_DRIVER}}};SERVER={s.DATABASE_SERVER};DATABASE={s.DATABASE_NAME};"
    conn += f"UID={s.DATABASE_USER};PWD={s.DATABASE_PASSWORD};" if s.DATABASE_USER else "Trusted_Connection=yes;"
    return conn
