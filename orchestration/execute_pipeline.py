import os
import sys
import argparse
from typing import Dict
from pathlib import Path
from datetime import datetime
from utils.data_reader import DataReader
from utils.data_writer import DataWriter
from utils.logger import get_logger, setup_logging
from utils.registry import ParserRegistry, ParserNotFoundError

logger = get_logger(__name__)

class PipelineExecutor:
    def __init__(self):
        self.registry = ParserRegistry()
        self.reader = DataReader()
        self.writer = DataWriter()
        self.stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

    def run(self, guid: str, sub_id: str) -> Dict[str, int]:
        logger.info(f"Starting pipeline: {guid}/{sub_id}")
        start = datetime.now()
        files = self.reader.list_files(guid, sub_id)
        if not files:
            logger.warning(f"No files found for {guid}/{sub_id}")
            return self.stats
        for blob_path in files:
            self.process_file(blob_path, guid, sub_id)
        logger.info(f"Pipeline done in {(datetime.now() - start).total_seconds():.2f}s — {self.stats}")
        return self.stats

    def process_file(self, blob_path: str, guid: str, sub_id: str) -> bool:
        self.stats["processed"] += 1
        filename = Path(blob_path).name
        info = self.registry.lookup_file_wildcard(guid, filename)
        if not info:
            logger.warning(f"No registry match: {filename}")
            self.writer.log_processing(guid=guid, sub_id=sub_id, file_wildcard="", filename=filename,
                                        domain="", report_type="", target_table="", status="skipped",
                                        error_message="No matching file_wildcard")
            self.stats["skipped"] += 1
            return False

        domain, report_type = info['domain'], info['report_type']
        target_table, insert_mode = info['target_table'], info['insert_mode']
        key_columns, file_wildcard = info.get('key_columns', ''), info['file_wildcard']
        local_path = None
        try:
            local_path = self.reader.download_to_temp(blob_path)
            df = self.registry.get_parser(domain, report_type)(local_path)
            df['_source_file'] = filename
            df['_guid'] = guid
            df['_sub_id'] = sub_id
            df['_file_wildcard'] = file_wildcard
            df['_parsed_at'] = datetime.now()
            rows = self.writer.write(df=df, target_table=target_table, insert_mode=insert_mode, key_columns=key_columns)
            self.writer.log_processing(guid=guid, sub_id=sub_id, file_wildcard=file_wildcard, filename=filename,
                                        domain=domain, report_type=report_type, target_table=target_table,
                                        status="success", rows_inserted=rows)
            self.stats["success"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed {filename}: {e}")
            self.writer.log_processing(guid=guid, sub_id=sub_id, file_wildcard=file_wildcard, filename=filename,
                                        domain=domain, report_type=report_type, target_table=target_table,
                                        status="failed", error_message=str(e))
            self.stats["failed"] += 1
            return False
        finally:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)

    def close(self) -> None:
        self.registry.close()
        self.writer.close()


def main():
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--guid", required=True)
    parser.add_argument("--sub-id", required=True)
    args = parser.parse_args()
    executor = PipelineExecutor()
    try:
        stats = executor.run(args.guid, args.sub_id)
        if stats["failed"] > 0:
            sys.exit(1)
    finally:
        executor.close()


if __name__ == "__main__":
    main()
