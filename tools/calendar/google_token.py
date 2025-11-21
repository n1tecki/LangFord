from google.oauth2 import service_account
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import os

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_TOKEN_PATH")
CALENDAR_ID = os.getenv("GOOGLE_MAIL")


def _get_access_token() -> str:
    """Get a fresh OAuth2 access token from the service account."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds.token, CALENDAR_ID
