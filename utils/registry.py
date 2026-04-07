import fnmatch
import importlib
import pandas as pd
from pathlib import Path
from typing import Optional
from utils.logger import get_logger
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, text
from config.database import get_connection_string

logger = get_logger(__name__)

class ParserNotFoundError(Exception):
    pass

class ParserRegistry:
    def __init__(self, parsers_dir: str = "parsers"):
        self.parsers_dir = Path(parsers_dir)
        self.parsers = {}
        self.engine_instance: Optional[Engine] = None
        self.discover_parsers()

    @property
    def engine(self) -> Engine:
        if self.engine_instance is None:
            self.engine_instance = create_engine(get_connection_string())
        return self.engine_instance

    def discover_parsers(self) -> None:
        if not self.parsers_dir.exists():
            return
        for d_dir in self.parsers_dir.iterdir():
            if not d_dir.is_dir() or d_dir.name.startswith(('_', '.')):
                continue
            for r_dir in d_dir.iterdir():
                if not r_dir.is_dir() or r_dir.name.startswith(('_', '.')):
                    continue
                if (r_dir / "current" / "parser.py").exists():
                    self.load_parser(d_dir.name, r_dir.name, f"{d_dir.name}/{r_dir.name}")
        logger.info(f"Discovered {len(self.parsers)} parsers")

    def load_parser(self, domain: str, report_type: str, key: str) -> None:
        try:
            module = importlib.import_module(f"parsers.{domain}.{report_type}.current.parser")
            if hasattr(module, 'parse'):
                self.parsers[key] = module.parse
        except Exception as e:
            logger.error(f"Failed to load parser {key}: {e}")

    def lookup_file_wildcard(self, guid: str, filename: str) -> Optional[dict]:
        query = text("SELECT file_wildcard, domain, report_type, target_table, insert_mode, key_columns FROM config.file_registry WHERE guid = :guid AND is_active = 1")
        try:
            df = pd.read_sql(query, self.engine, params={"guid": guid})
            for _, row in df.iterrows():
                if fnmatch.fnmatch(filename, row['file_wildcard']):
                    return row.to_dict()
        except Exception as e:
            logger.error(f"Registry lookup failed: {e}")
        return None

    def get_parser(self, domain: str, report_type: str):
        parse_fn = self.parsers.get(f"{domain}/{report_type}")
        if not parse_fn:
            raise ParserNotFoundError(f"No parser for: {domain}/{report_type}")
        return parse_fn

    def close(self) -> None:
        if self.engine_instance:
            self.engine_instance.dispose()
            self.engine_instance = None
