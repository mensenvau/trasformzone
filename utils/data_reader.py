import io
import tempfile
import pandas as pd
from pathlib import Path
from typing import List
from utils.logger import get_logger
from config.settings import get_settings
from azure.storage.blob import BlobServiceClient

logger = get_logger(__name__)

class UnsupportedFileTypeError(Exception):
    pass

class DataReader:
    SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.tsv'}
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_client = BlobServiceClient.from_connection_string(self.settings.AZURE_STORAGE_CONNECTION_STRING)
        self.container = self.blob_client.get_container_client(self.settings.STORAGE_CONTAINER_NAME)
    
    def list_files(self, guid: str, sub_id: str) -> List[str]:
        prefix = f"raw/{guid}/{sub_id}/"
        blobs = self.container.list_blobs(name_starts_with=prefix)
        return [b.name for b in blobs]
    
    def download_to_temp(self, blob_path: str) -> str:
        blob_data = self.container.get_blob_client(blob_path).download_blob().readall()
        ext = Path(blob_path).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(blob_data)
        tmp.close()
        return tmp.name
    
    def read_preview(self, blob_path: str, rows: int = 50) -> str:
        blob_data = self.container.get_blob_client(blob_path).download_blob().readall()
        ext = Path(blob_path).suffix.lower()
        
        if ext in ('.xlsx', '.xls'):
            engine = 'openpyxl' if ext == '.xlsx' else 'xlrd'
            df = pd.read_excel(io.BytesIO(blob_data), header=None, nrows=rows, engine=engine)
        elif ext in ('.csv', '.tsv'):
            delimiter = '\t' if ext == '.tsv' else ','
            df = pd.read_csv(io.BytesIO(blob_data), header=None, nrows=rows, delimiter=delimiter)
        else:
            return ""
        
        return df.to_csv(index=False)
    
    def get_blob_info(self, blob_path: str) -> dict:
        blob = self.container.get_blob_client(blob_path)
        props = blob.get_blob_properties()
        return {"name": blob_path, "size": props.size}
