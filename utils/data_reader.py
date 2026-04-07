import io
import fnmatch
import tempfile
import pandas as pd
from typing import List
from pathlib import Path
from utils.logger import get_logger
from config.settings import get_settings
from azure.storage.blob import BlobServiceClient

logger = get_logger(__name__)


class DataReader:
    SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.tsv'}

    def __init__(self):
        self.settings = get_settings()
        self.blob_client = BlobServiceClient.from_connection_string(self.settings.AZURE_STORAGE_CONNECTION_STRING)
        self.container = self.blob_client.get_container_client(self.settings.STORAGE_CONTAINER_NAME)
        try:
            self.container.get_container_properties()
        except Exception as e:
            logger.error(f"Azure connection failed: {e}")
            raise

    def list_files(self, guid: str, sub_id: str, file_wildcard: str = None) -> List[str]:
        prefix = f"raw/{guid}/{sub_id}/"
        try:
            blobs = [b.name for b in self.container.list_blobs(name_starts_with=prefix)]
            return [b for b in blobs if fnmatch.fnmatch(Path(b).name, file_wildcard)] if file_wildcard else blobs
        except Exception as e:
            logger.error(f"Blob listing failed: {e}")
            return []

    def read_preview(self, blob_path: str, rows: int = 50) -> str:
        try:
            data = self.container.get_blob_client(blob_path).download_blob().readall()
            ext = Path(blob_path).suffix.lower()
            if ext in ('.xlsx', '.xls'):
                df = pd.read_excel(io.BytesIO(data), header=None, nrows=rows, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
            else:
                df = pd.read_csv(io.BytesIO(data), header=None, nrows=rows)
            return df.to_csv(index=False)
        except Exception as e:
            logger.error(f"Blob preview failed: {e}")
            return ""

    def get_blob_info(self, blob_path: str) -> dict:
        try:
            props = self.container.get_blob_client(blob_path).get_blob_properties()
            return {"name": blob_path, "size": props.size}
        except:
            return {"name": blob_path, "size": 0}

    def get_local_copy(self, blob_path: str) -> str:
        data = self.container.get_blob_client(blob_path).download_blob().readall()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(blob_path).suffix)
        tmp.write(data)
        tmp.close()
        return tmp.name

    def download_to_temp(self, blob_path: str) -> str:
        return self.get_local_copy(blob_path)
