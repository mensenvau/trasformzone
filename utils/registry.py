import fnmatch
import importlib
import pandas as pd
from pathlib import Path
from typing import Optional, List
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
        self.connection_string = get_connection_string()
        self.engine_instance: Optional[Engine] = None
        self.discover_parsers()
    
    @property
    def engine(self) -> Engine:
        if self.engine_instance is None:
            self.engine_instance = create_engine(self.connection_string)
        return self.engine_instance
    
    def discover_parsers(self) -> None:
        if not self.parsers_dir.exists():
            logger.warning(f"Parsers directory not found: {self.parsers_dir}")
            return
        
        for domain_dir in self.parsers_dir.iterdir():
            if not domain_dir.is_dir() or domain_dir.name.startswith(('_', '.')):
                continue
            for report_dir in domain_dir.iterdir():
                if not report_dir.is_dir() or report_dir.name.startswith(('_', '.')):
                    continue
                if (report_dir / "current" / "parser.py").exists():
                    key = f"{domain_dir.name}/{report_dir.name}"
                    self.load_parser(domain_dir.name, report_dir.name, key)
        
        logger.info(f"Discovered {len(self.parsers)} parsers")
    
    def load_parser(self, domain: str, report_type: str, key: str) -> None:
        try:
            module_path = f"parsers.{domain}.{report_type}.current.parser"
            module = importlib.import_module(module_path)
            if hasattr(module, 'parse'):
                self.parsers[key] = module.parse
            else:
                logger.warning(f"No parse() function found in {module_path}")
        except Exception as e:
            logger.error(f"Failed to load parser {key}: {e}")
    
    def lookup_file_wildcard(self, guid: str, filename: str) -> Optional[dict]:
        query = text("SELECT file_wildcard, domain, report_type, target_table, insert_mode, key_columns FROM dbo.file_registry WHERE guid = :guid AND is_active = 1")
        try:
            df = pd.read_sql(query, self.engine, params={"guid": guid})
            for _, row in df.iterrows():
                if fnmatch.fnmatch(filename, row['file_wildcard']):
                    return row.to_dict()
        except Exception as e:
            logger.error(f"File registry lookup failed: {e}")
        return None
    
    def get_parser(self, domain: str, report_type: str):
        key = f"{domain}/{report_type}"
        parse_fn = self.parsers.get(key)
        if not parse_fn:
            raise ParserNotFoundError(f"No parser found for: {key}")
        return parse_fn
    
    def close(self) -> None:
        if self.engine_instance:
            self.engine_instance.dispose()
            self.engine_instance = None
