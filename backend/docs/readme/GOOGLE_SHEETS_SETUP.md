# Google Sheets Export Setup Guide

This guide explains how to set up Google Sheets export functionality for the Airtel Statement Fraud Detection app.

## Prerequisites

1. A Google Cloud Platform account
2. Python packages installed (automatically installed via requirements.txt)

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your Project ID

### 2. Enable Google Sheets and Drive APIs

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for and enable:
   - **Google Sheets API**
   - **Google Drive API**

### 3. Create Service Account Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in the service account details:
   - Name: `airtel-fraud-detection` (or any name you prefer)
   - Description: Service account for Airtel fraud detection app
4. Click **Create and Continue**
5. Skip the optional steps (Grant access and Grant users access)
6. Click **Done**

### 4. Generate and Download JSON Key

1. In the **Service Accounts** list, click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Select **JSON** format
5. Click **Create**
6. The JSON key file will be downloaded to your computer

### 5. Add Credentials to the App

1. Rename the downloaded JSON file to `google_credentials.json`
2. Place it in the `fraud_detection` folder:
   ```
   /home/ebran/Developer/projects/data_score_factors/fraud_detection/google_credentials.json
   ```

### 6. Install Required Packages

If not already installed, run:
```bash
pip install gspread google-auth google-auth-oauthlib google-auth-httplib2
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

## Usage

Once setup is complete:

1. Generate a running balance sheet in the app
2. Click the **📊 Export to Google Sheets** button
3. The app will create a new Google Sheet and provide a link
4. The sheet will be owned by the service account
5. You can access the sheet via the provided URL

## Important Notes

- **Sheet Ownership**: Sheets created by the service account are owned by that account
- **Sharing**: If you want to share sheets with others, you'll need to:
  1. Add sharing functionality to the app, OR
  2. Manually share from Google Sheets after creation
- **Permissions**: The service account needs the following scopes:
  - `https://www.googleapis.com/auth/spreadsheets` (create and edit sheets)
  - `https://www.googleapis.com/auth/drive` (manage files in Drive)

## Troubleshooting

### Error: "Google credentials file not found"
- Ensure `google_credentials.json` is in the `fraud_detection` folder
- Check the file name is exactly `google_credentials.json`

### Error: "Required packages not installed"
- Run: `pip install gspread google-auth google-auth-oauthlib google-auth-httplib2`

### Error: "API has not been used in project"
- Make sure you enabled both Google Sheets API and Google Drive API in your Google Cloud project

### Error: "Permission denied" or 403 errors
- Check that the service account has the correct permissions
- Ensure the APIs are enabled in your Google Cloud project

## Security Considerations

- **Keep credentials secure**: Never commit `google_credentials.json` to version control
- Add to `.gitignore`:
  ```
  fraud_detection/google_credentials.json
  ```
- The service account has limited permissions and can only create/edit sheets
- For production use, consider using more secure credential management (e.g., environment variables, secret managers)

## Alternative: User Authentication

If you prefer users to authenticate with their own Google accounts instead of using a service account:

1. Use OAuth 2.0 instead of service account authentication
2. Modify the `export_to_google_sheets` function to use user OAuth flow
3. This requires additional setup with OAuth consent screen

For most use cases, the service account approach is simpler and more suitable for automated exports.
