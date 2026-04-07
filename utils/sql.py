import uuid
import pyodbc
from datetime import datetime
from config.database import get_pyodbc_string

def serialize(row: dict) -> dict:
    result = {}
    for k, v in row.items():
        if v is None:
            result[k] = None
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            result[k] = str(v)
        elif not isinstance(v, (str, int, float, bool)):
            result[k] = str(v)
        else:
            result[k] = v
    return result

def execute_all(sql: str, params: tuple = None):
    """SELECT → list[dict] | DML → rowcount"""
    conn = pyodbc.connect(get_pyodbc_string())
    cursor = conn.cursor()
    cursor.execute(sql, params) if params else cursor.execute(sql)
    if cursor.description:
        cols = [c[0] for c in cursor.description]
        result = [serialize(dict(zip(cols, r))) for r in cursor.fetchall()]
    else:
        conn.commit()
        result = cursor.rowcount
    conn.close()
    return result

def execute_one(sql: str, params: tuple = None) -> dict:
    """SELECT first row → dict"""
    conn = pyodbc.connect(get_pyodbc_string())
    cursor = conn.cursor()
    cursor.execute(sql, params) if params else cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    row = cursor.fetchone()
    conn.close()
    return serialize(dict(zip(cols, row))) if row else {}
