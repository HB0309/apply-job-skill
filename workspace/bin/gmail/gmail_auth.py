"""
One-time (and auto-refresh) OAuth setup for Gmail API access.
Run this directly the first time: python gmail_auth.py
It opens a browser for you to approve access, then saves token.json here.
Subsequent runs just refresh the token silently if needed.

If the saved refresh token has been revoked or expired, this module parks the
dead token and re-runs the browser consent flow rather than crashing. Google
expires refresh tokens after 7 days while an OAuth app's publishing status is
still "Testing" -- set the app to "In production" in the Google Cloud console
to stop the weekly re-auth.
"""
import os
import time

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
HERE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(HERE, "credentials.json")
TOKEN_PATH = os.path.join(HERE, "token.json")

REAUTH_HINT = (
    "Gmail token is expired or revoked and no valid refresh token remains.\n"
    "Re-authorize by running, at a terminal you control:\n"
    "    cd <WORKSPACE>/bin/gmail && python gmail_auth.py\n"
    "A browser window will open for Google sign-in."
)


def _park_dead_token():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(TOKEN_PATH, TOKEN_PATH + ".expired-" + stamp)
    except OSError:
        pass


def _run_consent_flow():
    """Interactive browser consent. Requires a human at the keyboard."""
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    return flow.run_local_server(port=0)


def _save(creds):
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def get_credentials(interactive=True):
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save(creds)
            return creds
        except RefreshError:
            _park_dead_token()
            creds = None

    if not interactive:
        raise RuntimeError(REAUTH_HINT)

    creds = _run_consent_flow()
    _save(creds)
    return creds


if __name__ == "__main__":
    get_credentials()
    print("Auth OK. Token saved to", TOKEN_PATH)
