"""Secure Gmail access for FRIDAY.

The first send opens Google's sign-in page. Passwords are never stored here.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = PROJECT_DIR / "credentials.json"
TOKEN_FILE = PROJECT_DIR / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailSetupError(RuntimeError):
    """Raised when Google OAuth has not been configured yet."""


def _get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as error:
        raise GmailSetupError("Gmail libraries are not installed yet.") from error

    if not CREDENTIALS_FILE.exists():
        raise GmailSetupError(
            "credentials.json is missing. Follow the Gmail setup instructions in README.md."
        )

    credentials = None
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=credentials)


def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an already user-confirmed message and return Gmail's message ID."""
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service = _get_service()
    result = service.users().messages().send(
        userId="me", body={"raw": encoded}
    ).execute()
    return result["id"]
