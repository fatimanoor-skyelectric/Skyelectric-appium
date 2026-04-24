import os
import re
import time
import base64
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

BASE_DIR         = os.path.dirname(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE       = os.path.join(BASE_DIR, 'token.json')


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def get_otp_from_gmail(sender_filter='skyelectric', subject_filter='OTP',
                        wait_seconds=90, poll_interval=5,
                        since_timestamp=None):
    """
    Poll Gmail for an OTP email.

    since_timestamp: unix timestamp (float). Only emails received AFTER
                     this point are considered. Pass time.time() captured
                     just before tapping Login so stale emails are ignored.
    """
    service       = get_gmail_service()
    start_time    = time.time()
    since_ts      = since_timestamp or (start_time - 30)  # default: last 30s

    print(f"\n⏳ Waiting for OTP email (max {wait_seconds}s)...")
    print(f"   Ignoring any email older than: "
          f"{datetime.fromtimestamp(since_ts).strftime('%H:%M:%S')}")

    while time.time() - start_time < wait_seconds:
        try:
            # newer_than:3m gives a safe window; we double-check the date below
            query = (f'from:{sender_filter} subject:{subject_filter} '
                     f'is:unread newer_than:3m')
            results = service.users().messages().list(
                userId='me', q=query, maxResults=5       # fetch a few in case
            ).execute()
            messages = results.get('messages', [])

            for msg_stub in messages:
                msg = service.users().messages().get(
                    userId='me', id=msg_stub['id'], format='full'
                ).execute()

                # Gmail internalDate is milliseconds since epoch
                internal_date_ms = int(msg.get('internalDate', 0))
                email_ts         = internal_date_ms / 1000.0

                if email_ts < since_ts:
                    print(f"   ⏭️  Skipping stale email "
                          f"(arrived {datetime.fromtimestamp(email_ts).strftime('%H:%M:%S')})")
                    continue

                body = extract_email_body(msg)
                print(f"📧 New OTP email received "
                      f"({datetime.fromtimestamp(email_ts).strftime('%H:%M:%S')}) — extracting…")
                otp = extract_otp_from_text(body)
                if otp:
                    print(f"✅ OTP found: {otp}")
                    # Mark as read so future polls don't pick it up
                    _mark_as_read(service, msg_stub['id'])
                    return otp
                else:
                    print("⚠️  Email matched but no OTP pattern found in body")

        except Exception as e:
            print(f"⚠️  Gmail check error: {e}")

        remaining = wait_seconds - (time.time() - start_time)
        if remaining > 0:
            print(f"   No valid OTP yet — retrying in {poll_interval}s "
                  f"({int(remaining)}s remaining)…")
            time.sleep(poll_interval)

    print("❌ OTP not received within timeout")
    return None


def _mark_as_read(service, msg_id):
    """Mark the OTP email as read so it isn't reused in later test runs."""
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    except Exception:
        pass  # non-critical


def extract_email_body(msg):
    """Walk the MIME tree and return the first text/plain body found."""
    payload = msg.get('payload', {})

    # Flat (non-multipart) message
    data = payload.get('body', {}).get('data', '')
    if data:
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    # Multipart — walk parts & sub-parts
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        for sub in part.get('parts', []):
            if sub.get('mimeType') == 'text/plain':
                data = sub.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    return ""


def extract_otp_from_text(text):
    """
    Extract OTP from email body. Tries most-specific patterns first.
    Returns the first match as a string, or None.
    """
    patterns = [
        r'OTP[:\s]+(\d{6})',            # "OTP: 123456"
        r'code[:\s]+(\d{6})',           # "code: 123456"
        r'is[:\s]+(\d{6})',             # "is 123456"
        r'\b(\d{6})\b',                 # any standalone 6-digit number
        r'OTP[:\s]+(\d{4})',            # 4-digit fallbacks
        r'code[:\s]+(\d{4})',
        r'\b(\d{4})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None