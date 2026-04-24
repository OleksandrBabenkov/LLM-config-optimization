import os
import io
import logging
import time
import random
import functools
from typing import List, Optional, Any, Dict, Callable
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def retry_on_network_error(max_retries: int = 5, initial_backoff: float = 1.0):
    """Decorator for exponential backoff retry logic."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff
            while True:
                try:
                    return func(*args, **kwargs)
                except (HttpError, ConnectionError, TimeoutError, IOError) as e:
                    if isinstance(e, HttpError):
                        if e.resp.status not in [403, 429, 500, 502, 503, 504]:
                            logger.error(f"Non-retryable HTTP error in {func.__name__}: {e}")
                            raise
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) reached. Last error: {e}")
                        raise
                    wait_time = backoff + random.uniform(0, 0.1 * backoff)
                    logger.warning(f"Retryable error in {func.__name__}: {e}. Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    retries += 1
                    backoff *= 2
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator

class GoogleDriveManagerSA:
    """Handles Google Drive I/O operations and authentication with a Service Account."""

    SCOPES: List[str] = ['https://www.googleapis.com/auth/drive']
    
    ROOT_FOLDER_NAME = "LLM-config-optimization"
    CONFIG_IN_FOLDER_NAME = "LLM_Configs_In"
    RESULTS_OUT_FOLDER_NAME = "Python_Results_Out"

    def __init__(self, credentials_path: str = "service-account.json") -> None:
        """
        Initialize the Drive Manager using a Service Account.
        
        Args:
            credentials_path: Path to the Service Account JSON key.
        """
        self.credentials_path: str = credentials_path
        self.service: Optional[Any] = None
        self.config_in_id: Optional[str] = None
        self.results_out_id: Optional[str] = None
        self.authenticate()
        if self.is_ready():
            self.initialize_folders()

    def authenticate(self) -> None:
        """Authenticates using the Service Account JSON key."""
        if not os.path.exists(self.credentials_path):
            logger.warning("Service account key not found at %s. Please ensure 'service-account.json' is in the project root.", self.credentials_path)
            return

        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Service Account.")
        except Exception as e:
            logger.error("Failed to authenticate with Service Account: %s", e)
            self.service = None

    def is_ready(self) -> bool:
        return self.service is not None

    def initialize_folders(self) -> None:
        """Search for existing folders shared with this service account."""
        if not self.is_ready(): return
        
        logger.info("Connecting to Drive folders via Service Account...")
        
        root_id = self.find_folder_by_name(self.ROOT_FOLDER_NAME)
        if not root_id:
            logger.error(f"Could not find shared folder '{self.ROOT_FOLDER_NAME}'.")
            logger.info("ACTION REQUIRED: Go to Google Drive, right-click the '%s' folder, click 'Share', and paste your Service Account email.", self.ROOT_FOLDER_NAME)
            return

        self.config_in_id = self.find_folder_by_name(self.CONFIG_IN_FOLDER_NAME, parent_id=root_id)
        self.results_out_id = self.find_folder_by_name(self.RESULTS_OUT_FOLDER_NAME, parent_id=root_id)
        
        if self.config_in_id and self.results_out_id:
            logger.info(f"Drive folders connected: In={self.config_in_id}, Out={self.results_out_id}")
        else:
            logger.warning("Subfolders missing inside the shared root folder.")

    @retry_on_network_error()
    def find_folder_by_name(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        if not self.is_ready(): return None
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None

    @retry_on_network_error()
    def list_files(self, folder_id: Optional[str] = None) -> List[Dict[str, str]]:
        if not self.is_ready(): return []
        query = f"'{folder_id}' in parents and trashed = false" if folder_id else "trashed = false"
        results = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    @retry_on_network_error()
    def download_file(self, file_id: str, destination: str) -> bool:
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(destination, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return True

    @retry_on_network_error()
    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id: file_metadata['parents'] = [folder_id]
        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')

    @retry_on_network_error()
    def delete_file(self, file_id: str) -> bool:
        self.service.files().delete(fileId=file_id).execute()
        return True
