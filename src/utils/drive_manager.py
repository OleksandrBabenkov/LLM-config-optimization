import os
import io
import logging
import time
import random
import functools
from typing import List, Optional, Any, Dict, Callable
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
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
    """Handles Google Drive I/O operations and authentication with OAuth 2.0."""

    SCOPES: List[str] = ['https://www.googleapis.com/auth/drive.file']
    
    # Folder names as class constants to avoid hardcoding
    ROOT_FOLDER_NAME = "LLM-config-optimization"
    CONFIG_IN_FOLDER_NAME = "LLM_Configs_In"
    RESULTS_OUT_FOLDER_NAME = "Python_Results_Out"

    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json") -> None:
        """
        Initialize the Drive Manager.
        
        Args:
            credentials_path: Path to the OAuth 2.0 client credentials JSON.
            token_path: Path to the saved token for persistent authentication.
        """
        self.credentials_path: str = credentials_path
        self.token_path: str = token_path
        self.service: Optional[Any] = None
        self.config_in_id: Optional[str] = None
        self.results_out_id: Optional[str] = None
        self.authenticate()
        if self.is_ready():
            self.initialize_folders()

    def authenticate(self) -> None:
        """
        Authenticates using OAuth 2.0 client credentials.
        Note: The first run requires user interaction (browser) to generate token.json.
        """
        if not os.path.exists(self.credentials_path) and not os.path.exists(self.token_path):
            logger.warning(
                "Credentials file not found at %s and no token at %s. "
                "Google Drive operations will be unavailable.",
                self.credentials_path, self.token_path
            )
            return

        creds = None
        # token.json stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error("Credentials file missing for initial OAuth flow.")
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    # Note: run_local_server will open a browser window for authentication
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                    
            except Exception as e:
                logger.error("Failed to complete OAuth 2.0 flow: %s", e)
                self.service = None
                return

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive API.")
        except Exception as e:
            logger.error("Failed to build Drive service: %s", e)
            self.service = None

    def is_ready(self) -> bool:
        """Checks if the service is authenticated and ready."""
        return self.service is not None

    def initialize_folders(self, force: bool = False) -> None:
        """
        Automatically initializes the folder structure on Google Drive.
        - Searches for or creates project root folder.
        - Searches for or creates input and output folders inside it.
        - Stores the IDs in instance attributes.
        
        Args:
            force: If True, re-searches Drive even if IDs are already set.
        """
        if not self.is_ready():
            return

        if not force and self.config_in_id and self.results_out_id:
            return

        logger.info("Initializing Drive folder structure...")
        
        root_id = self.find_folder_by_name(self.ROOT_FOLDER_NAME)
        if not root_id:
            logger.info(f"Project root folder '{self.ROOT_FOLDER_NAME}' not found. Creating...")
            root_id = self.create_folder(self.ROOT_FOLDER_NAME)
        
        if not root_id:
            logger.error(f"Failed to find or create project root folder '{self.ROOT_FOLDER_NAME}'.")
            return

        if not self.config_in_id or force:
            self.config_in_id = self.find_folder_by_name(self.CONFIG_IN_FOLDER_NAME, parent_id=root_id)
            if not self.config_in_id:
                logger.info(f"Folder '{self.CONFIG_IN_FOLDER_NAME}' not found. Creating...")
                self.config_in_id = self.create_folder(self.CONFIG_IN_FOLDER_NAME, parent_id=root_id)

        if not self.results_out_id or force:
            self.results_out_id = self.find_folder_by_name(self.RESULTS_OUT_FOLDER_NAME, parent_id=root_id)
            if not self.results_out_id:
                logger.info(f"Folder '{self.RESULTS_OUT_FOLDER_NAME}' not found. Creating...")
                self.results_out_id = self.create_folder(self.RESULTS_OUT_FOLDER_NAME, parent_id=root_id)
            
        logger.info(f"Drive folders initialized: In={self.config_in_id}, Out={self.results_out_id}")

    @retry_on_network_error()
    def find_folder_by_name(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Finds a folder by its name.
        
        Args:
            folder_name: The name of the folder to find.
            parent_id: Optional ID of the parent folder to search within.
            
        Returns:
            The ID of the folder if found, otherwise None.
        """
        if not self.is_ready():
            return None

        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name)",
            spaces='drive'
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0].get('id')
        return None

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

    @retry_on_network_error()
    def delete_file(self, file_id: str) -> bool:
        """
        Deletes a file from Google Drive by its ID.
        
        Args:
            file_id: The ID of the file to delete.
            
        Returns:
            True if deletion succeeded, False otherwise.
        """
        if not self.is_ready():
            return False

        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Successfully deleted file with ID: {file_id}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File with ID {file_id} not found for deletion.")
                return True # Consider it "deleted" if it's already gone
            raise
