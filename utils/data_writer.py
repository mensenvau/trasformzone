import pandas as pd
from typing import List, Optional
from utils.logger import get_logger
from sqlalchemy.engine import Engine
from config.database import get_connection_string
from sqlalchemy import create_engine, text, inspect

logger = get_logger(__name__)


class DataWriter:
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or get_connection_string()
        self.engine_instance: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        if self.engine_instance is None:
            self.engine_instance = create_engine(self.connection_string)
        return self.engine_instance

    def ensure_schema_exists(self, schema: str) -> None:
        with self.engine.connect() as conn:
            conn.execute(text(f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')"))
            conn.commit()

    def table_exists(self, table: str, schema: str) -> bool:
        return inspect(self.engine).has_table(table, schema=schema)

    def ensure_table_exists(self, df: pd.DataFrame, table: str, schema: str) -> None:
        self.ensure_schema_exists(schema)
        if not self.table_exists(table, schema):
            logger.info(f"Creating table {schema}.{table}")
            df.head(0).to_sql(table, self.engine, schema=schema, if_exists='fail', index=False)

    def write(self, df: pd.DataFrame, target_table: str, insert_mode: str = "append", key_columns: Optional[str] = None) -> int:
        if df.empty:
            return 0
        schema, table = target_table.split('.', 1) if '.' in target_table else ('dbo', target_table)
        self.ensure_table_exists(df, table, schema)
        m = insert_mode.lower()
        if m == "append":
            return self.append_data(df, table, schema)
        if m == "replace":
            return self.replace_data(df, table, schema)
        if m in ["upsert", "merge"]:
            keys = [k.strip() for k in key_columns.split(',')] if key_columns else []
            if not keys:
                raise ValueError("key_columns required for upsert/merge")
            return self.upsert_data(df, table, schema, keys)
        raise ValueError(f"Unknown insert_mode: {insert_mode}")

    def append_data(self, df: pd.DataFrame, table: str, schema: str) -> int:
        df.to_sql(table, self.engine, schema=schema, if_exists='append', index=False)
        return len(df)

    def replace_data(self, df: pd.DataFrame, table: str, schema: str) -> int:
        df.to_sql(table, self.engine, schema=schema, if_exists='replace', index=False)
        return len(df)

    def upsert_data(self, df: pd.DataFrame, table: str, schema: str, key_columns: List[str]) -> int:
        self.ensure_schema_exists('stg')
        stg = f"stg_{table}"
        cols = df.columns.tolist()
        col_list = ', '.join([f"[{c}]" for c in cols])
        df.to_sql(stg, self.engine, schema='stg', if_exists='replace', index=False)
        keys = ' AND '.join([f"t.[{k}] = s.[{k}]" for k in key_columns])
        with self.engine.connect() as conn:
            deleted = conn.execute(text(f"DELETE t FROM {schema}.{table} t INNER JOIN stg.{stg} s ON {keys}")).rowcount
            inserted = conn.execute(text(f"INSERT INTO {schema}.{table} ({col_list}) SELECT {col_list} FROM stg.{stg}")).rowcount
            conn.execute(text(f"DROP TABLE IF EXISTS stg.{stg}"))
            conn.commit()
        logger.info(f"Upsert {schema}.{table}: deleted={deleted}, inserted={inserted}")
        return inserted

    def log_processing(self, guid: str, sub_id: str, file_wildcard: str, filename: str,
                        domain: str, report_type: str, target_table: str, status: str,
                        rows_inserted: int = 0, error_message: str = None) -> None:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO config.processing_log
                        (guid, sub_id, file_wildcard, filename, domain, report_type, target_table, status, rows_inserted, error_message, processed_at)
                    VALUES (:guid, :sub_id, :file_wildcard, :filename, :domain, :report_type, :target_table, :status, :rows_inserted, :error_message, GETDATE())
                """), {"guid": guid, "sub_id": sub_id, "file_wildcard": file_wildcard, "filename": filename,
                       "domain": domain, "report_type": report_type, "target_table": target_table,
                       "status": status, "rows_inserted": rows_inserted, "error_message": error_message})
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log processing: {e}")

    def close(self) -> None:
        if self.engine_instance:
            self.engine_instance.dispose()
            self.engine_instance = None
