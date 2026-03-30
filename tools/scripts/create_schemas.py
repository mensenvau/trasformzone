"""One-time script to create stg and bronze schemas in the database."""
import pyodbc
from config.settings import get_settings

settings = get_settings()
conn = pyodbc.connect(
    f"DRIVER={{{settings.DATABASE_DRIVER}}};"
    f"SERVER={settings.DATABASE_SERVER};"
    f"DATABASE={settings.DATABASE_NAME};"
    f"UID={settings.DATABASE_USER};"
    f"PWD={settings.DATABASE_PASSWORD};"
    f"TrustServerCertificate=yes"
)

cursor = conn.cursor()
for schema in ("stg", "bronze"):
    cursor.execute(f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')")
conn.commit()
print("Schemas created: stg, bronze")
conn.close()
