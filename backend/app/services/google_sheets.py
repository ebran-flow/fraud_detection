"""
Google Sheets Integration using OAuth 2.0
Exports data to Google Sheets using user's personal Google account
"""
import logging
import os
import pickle
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Google Sheets API scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Path to store OAuth token
TOKEN_PATH = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/token.pickle'
CREDENTIALS_PATH = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/oauth_credentials.json'


def get_credentials():
    """Get OAuth credentials, prompting user if needed"""
    creds = None

    # Token file stores the user's access and refresh tokens
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired OAuth token")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"OAuth credentials not found at {CREDENTIALS_PATH}\n"
                    "Please download OAuth 2.0 credentials from Google Cloud Console"
                )
            logger.info("Starting OAuth flow - browser will open for authorization")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for next time
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        logger.info("OAuth credentials saved")

    return creds


def get_google_sheets_client():
    """Get authenticated Google Sheets client using OAuth"""
    creds = get_credentials()
    client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return client, drive_service


def get_or_create_folder(drive_service, folder_name: str, parent_folder_id: str = None) -> str:
    """
    Get existing folder or create new one in Google Drive

    Args:
        drive_service: Google Drive API service
        folder_name: Name of folder
        parent_folder_id: Parent folder ID (None for root)

    Returns:
        Folder ID
    """
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"

        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            logger.info(f"Found existing folder: {folder_name}")
            return files[0]['id']

        # Create new folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]

        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        logger.info(f"Created folder: {folder_name}")
        return folder['id']

    except Exception as e:
        logger.error(f"Error with folder {folder_name}: {e}")
        return None


def create_spreadsheet_from_csv_data(csv_data: str, title: str) -> str:
    """
    Create a Google Spreadsheet from CSV data in fraud_detection/airtel/processed folder

    Args:
        csv_data: CSV formatted string
        title: Title for the spreadsheet

    Returns:
        URL to the created spreadsheet
    """
    import csv
    import io

    try:
        client, drive_service = get_google_sheets_client()

        # Create folder structure: fraud_detection/airtel/processed
        fraud_detection_id = get_or_create_folder(drive_service, 'fraud_detection')
        airtel_id = get_or_create_folder(drive_service, 'airtel', fraud_detection_id) if fraud_detection_id else None
        processed_id = get_or_create_folder(drive_service, 'processed', airtel_id) if airtel_id else None

        # Parse CSV data
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)

        if not rows:
            raise ValueError("No data to export")

        logger.info(f"Creating spreadsheet '{title}' with {len(rows)} rows")

        # Create spreadsheet in folder
        spreadsheet = client.create(title, folder_id=processed_id)
        logger.info(f"Created spreadsheet: {title} (ID: {spreadsheet.id})")

        # Update worksheet with data
        worksheet = spreadsheet.sheet1
        worksheet.update(rows, value_input_option='USER_ENTERED')
        logger.info(f"Uploaded {len(rows)} rows")

        # Format header row (bold)
        worksheet.format('1:1', {'textFormat': {'bold': True}})

        # Share with anyone with link (view only)
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            drive_service.permissions().create(
                fileId=spreadsheet.id,
                body=permission
            ).execute()
            logger.info("Shared with anyone with link")
        except Exception as e:
            logger.warning(f"Could not share publicly: {e}")

        logger.info(f"Spreadsheet created: {spreadsheet.url}")
        return spreadsheet.url

    except Exception as e:
        logger.error(f"Error creating Google Spreadsheet: {e}")
        raise


def export_summary_to_google_sheets(csv_data: str, title: str = "Statement Summary") -> str:
    """
    Export summary data to Google Sheets

    Args:
        csv_data: CSV formatted string
        title: Title for the spreadsheet

    Returns:
        URL to the created Google Spreadsheet
    """
    return create_spreadsheet_from_csv_data(csv_data, title)
