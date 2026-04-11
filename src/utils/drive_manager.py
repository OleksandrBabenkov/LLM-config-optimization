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
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts.
        initial_backoff: Starting delay in seconds.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff
            
            while True:
                try:
                    return func(*args, **kwargs)
                except (HttpError, ConnectionError, TimeoutError, IOError) as e:
                    # Check if it's a retryable error (e.g., 403 rate limit, 429, 500, 503, 504)
                    if isinstance(e, HttpError):
                        if e.resp.status not in [403, 429, 500, 502, 503, 504]:
                            logger.error(f"Non-retryable HTTP error in {func.__name__}: {e}")
                            raise

                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}. Last error: {e}")
                        raise
                    
                    wait_time = backoff + random.uniform(0, 0.1 * backoff)
                    logger.warning(
                        f"Retryable error in {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s (Attempt {retries + 1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                    retries += 1
                    backoff *= 2
                except Exception as e:
                    logger.error(f"Unexpected non-retryable error in {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator

class GoogleDriveManager:
    """Handles Google Drive I/O operations and authentication with Service Account."""

    SCOPES: List[str] = ['https://www.googleapis.com/auth/drive']

    def __init__(self, credentials_path: str = "credentials.json") -> None:
        """
        Initialize the Drive Manager.
        
        Args:
            credentials_path: Path to the Google Service Account JSON credentials.
        """
        self.credentials_path: str = credentials_path
        self.service: Optional[Any] = None
        self.authenticate()

    def authenticate(self) -> None:
        """
        Authenticates using service account credentials.
        Handles missing credentials gracefully by logging a warning.
        """
        if not os.path.exists(self.credentials_path):
            logger.warning(
                "Credentials file not found at %s. "
                "Google Drive operations will be unavailable.",
                self.credentials_path
            )
            return

        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive API.")
        except Exception as e:
            logger.error("Failed to authenticate with Google Drive: %s", e)
            self.service = None

    def is_ready(self) -> bool:
        """Checks if the service is authenticated and ready."""
        return self.service is not None

    @retry_on_network_error()
    def find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """
        Finds a folder ID by its name.
        
        Args:
            folder_name: The name of the folder to search for.
            
        Returns:
            The folder ID if found, None otherwise.
        """
        if not self.is_ready():
            return None

        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        if not files:
            logger.warning(f"Folder '{folder_name}' not found.")
            return None
        return files[0]['id']

    @retry_on_network_error()
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Creates a new folder on Google Drive.
        
        Args:
            folder_name: The name of the folder to create.
            parent_id: Optional ID of the parent folder.
            
        Returns:
            The ID of the created folder, or None if failed.
        """
        if not self.is_ready():
            return None

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        file = self.service.files().create(body=file_metadata, fields='id').execute()
        logger.info(f"Created folder '{folder_name}' with ID: {file.get('id')}")
        return file.get('id')

    @retry_on_network_error()
    def list_files(self, folder_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Lists files in a specific folder or root.
        
        Args:
            folder_id: Optional ID of the folder to list files from.
            
        Returns:
            List of dictionaries containing file 'id', 'name', and 'mimeType'.
        """
        if not self.is_ready():
            return []

        query: str = f"'{folder_id}' in parents and trashed = false" if folder_id else "trashed = false"
        results = self.service.files().list(
            q=query, 
            fields="files(id, name, mimeType)",
            spaces='drive'
        ).execute()
        return results.get('files', [])

    @retry_on_network_error()
    def download_file(self, file_id: str, destination: str) -> bool:
        """
        Downloads a file from Drive by ID.
        
        Args:
            file_id: The ID of the file on Google Drive.
            destination: Local path where the file should be saved.
            
        Returns:
            True if download succeeded, False otherwise.
        """
        if not self.is_ready():
            return False

        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(destination, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done: bool = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug("Download progress: %d%%", int(status.progress() * 100))
        return True

    @retry_on_network_error()
    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        Uploads a file to a specific Drive folder.
        
        Args:
            file_path: Local path of the file to upload.
            folder_id: Optional ID of the folder to upload to.
            
        Returns:
            The ID of the uploaded file, or None if failed.
        """
        if not self.is_ready():
            return None

        if not os.path.exists(file_path):
            logger.error("Upload failed: Local file %s does not exist.", file_path)
            return None

        file_name: str = os.path.basename(file_path)
        file_metadata: Dict[str, Any] = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        return file.get('id')
