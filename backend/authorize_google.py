#!/usr/bin/env python3
"""
One-time OAuth authorization script for Google Sheets
Run this once to authorize the application
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Google Sheets API scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

TOKEN_PATH = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/token.pickle'
CREDENTIALS_PATH = '/home/ebran/Developer/projects/airtel_fraud_detection/backend/oauth_credentials.json'


def main():
    """Authorize and save credentials"""
    creds = None

    # Check if we already have valid credentials
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If credentials are expired or don't exist, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
            print("✅ Token refreshed successfully!")
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"❌ Error: OAuth credentials not found at {CREDENTIALS_PATH}")
                print("\nPlease download OAuth 2.0 credentials from Google Cloud Console:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Select project: rational-cat-397610")
                print("3. Go to APIs & Services → Credentials")
                print("4. Download the OAuth 2.0 Client ID JSON")
                print(f"5. Save it as: {CREDENTIALS_PATH}")
                return

            print("Starting OAuth authorization flow...")
            print("A browser window will open for you to authorize the application.")
            print("\nMake sure:")
            print("- You're logged in as: ebran@inbox.flowglobal.net")
            print("- You've added yourself as a test user in OAuth consent screen")
            print()

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # Use port 0 to auto-select available port

        # Save credentials for future use
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        print(f"✅ Credentials saved to: {TOKEN_PATH}")
        print("\n✅ Authorization complete! You can now use Google Sheets export.")
    else:
        print("✅ Already authorized! Credentials are valid.")
        print(f"Token file: {TOKEN_PATH}")


if __name__ == '__main__':
    main()
