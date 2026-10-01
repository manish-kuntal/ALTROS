# ============================================================
#  ALTROS Module: Gmail Integration
#  Read, Send, Delete, Search, Reply — multiple accounts
# ============================================================

import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from modules.base import BaseModule

CREDS_FILE  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
TOKEN_FILE  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory", "gmail_token.json")
SCOPES      = ['https://www.googleapis.com/auth/gmail.modify']

GMAIL_TRIGGERS = [
    "gmail", "email", "mail", "inbox",
    "mail bhej", "email bhej", "send email", "send mail",
    "mail padho", "inbox dekho", "mail dekho",
    "mail delete", "delete email", "reply karo",
    "mail search", "email search", "attachment",
    "unread", "new mail", "naya mail",
]


class GmailModule(BaseModule):
    name = "gmail"
    description = "Gmail — read, send, delete, search, reply"

    def __init__(self):
        self._ready = False
        self._service = None

    def on_enable(self):
        try:
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            creds = None

            # Load saved token
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            # Refresh or new login
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(CREDS_FILE):
                        print("     ⚠️  credentials.json nahi mila C:\\ALTROS\\ mein")
                        return
                    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save token
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, 'w') as f:
                    f.write(creds.to_json())

            self._service = build('gmail', 'v1', credentials=creds)
            self._ready = True
            print("     ✅ Gmail module ready")

        except ImportError:
            print("     ⚠️  Run: pip install google-auth-oauthlib google-api-python-client")
        except Exception as e:
            print(f"     ⚠️  Gmail error: {e}")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in GMAIL_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower()

        # ── READ INBOX ────────────────────────────────────────
        if any(w in q for w in ["inbox dekho", "mail dekho", "unread", "naya mail", "new mail"]):
            return self._read_inbox(unread_only="unread" in q or "naya" in q)

        # ── SEND EMAIL ────────────────────────────────────────
        if any(w in q for w in ["mail bhej", "email bhej", "send email", "send mail", "mail karo"]):
            return self._parse_and_send(query)

        # ── SEARCH EMAIL ──────────────────────────────────────
        if any(w in q for w in ["search", "dhundo", "find"]) and any(w in q for w in ["mail", "email", "gmail"]):
            import re
            search_match = re.search(r'(?:search|dhundo|find)\s+(?:mail|email)?\s*["\']?([^"\']+)["\']?', q)
            keyword = search_match.group(1).strip() if search_match else ""
            if not keyword:
                return "Gmail: Kya search karna hai? 'gmail search invoice'"
            return self._search_emails(keyword)

        # ── DELETE EMAIL ──────────────────────────────────────
        if any(w in q for w in ["delete", "trash", "hata do"]) and any(w in q for w in ["mail", "email"]):
            return self._delete_latest()

        # ── REPLY ─────────────────────────────────────────────
        if "reply" in q:
            return self._parse_and_reply(query)

        # ── READ SPECIFIC ─────────────────────────────────────
        if any(w in q for w in ["padho", "open", "read"]) and any(w in q for w in ["mail", "email"]):
            return self._read_latest()

        return ""

    # ── Gmail Operations ──────────────────────────────────────

    def _read_inbox(self, unread_only: bool = False, max_results: int = 5) -> str:
        try:
            query_str = "is:unread" if unread_only else "in:inbox"
            results = self._service.users().messages().list(
                userId='me', q=query_str, maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return "Gmail: Inbox empty hai." if not unread_only else "Gmail: Koi unread mail nahi."

            lines = [f"Gmail: {'Unread' if unread_only else 'Latest'} emails ({len(messages)}):"]
            for msg in messages:
                details = self._get_email_summary(msg['id'])
                lines.append(f"\n  📧 {details}")

            return "\n".join(lines)
        except Exception as e:
            return f"Gmail: ❌ Inbox error — {e}"

    def _get_email_summary(self, msg_id: str) -> str:
        try:
            msg = self._service.users().messages().get(
                userId='me', id=msg_id, format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            sender  = headers.get('From', 'Unknown')[:40]
            subject = headers.get('Subject', 'No Subject')[:50]
            date    = headers.get('Date', '')[:20]

            return f"From: {sender}\n     Subject: {subject}\n     Date: {date}"
        except Exception as e:
            return f"Error reading message: {e}"

    def _read_latest(self) -> str:
        try:
            results = self._service.users().messages().list(
                userId='me', q="in:inbox", maxResults=1
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return "Gmail: Inbox empty hai."

            msg = self._service.users().messages().get(
                userId='me', id=messages[0]['id'], format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            sender  = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            body    = self._extract_body(msg)

            return (
                f"Gmail: Latest email:\n"
                f"  From: {sender}\n"
                f"  Subject: {subject}\n"
                f"  Body: {body[:500]}"
            )
        except Exception as e:
            return f"Gmail: ❌ Read error — {e}"

    def _extract_body(self, msg) -> str:
        try:
            parts = msg['payload'].get('parts', [])
            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')[:500]
            else:
                data = msg['payload']['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')[:500]
        except Exception:
            pass
        return "[Body read nahi ho saka]"

    def _parse_and_send(self, query: str) -> str:
        import re

        to_match      = re.search(r'(?:to|ko)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', query)
        subject_match = re.search(r'subject\s+"([^"]+)"', query, re.I)
        body_match    = re.search(r'(?:body|content|likhna hai|message)\s+"([^"]+)"', query, re.I)

        if not to_match:
            return "Gmail: Email address batao — format: 'mail bhejo to xyz@gmail.com subject \"Topic\" body \"Message\"'"

        to      = to_match.group(1)
        subject = subject_match.group(1) if subject_match else "ALTROS se message"
        body    = body_match.group(1) if body_match else query

        return self._send_email(to, subject, body)

    def _send_email(self, to: str, subject: str, body: str) -> str:
        try:
            msg = MIMEMultipart()
            msg['To']      = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()

            return f"Gmail: ✅ Email bhej diya {to} ko!\n  Subject: {subject}"
        except Exception as e:
            return f"Gmail: ❌ Send error — {e}"

    def _search_emails(self, keyword: str) -> str:
        try:
            results = self._service.users().messages().list(
                userId='me', q=keyword, maxResults=5
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return f"Gmail: '{keyword}' se koi email nahi mili."

            lines = [f"Gmail: '{keyword}' search results ({len(messages)}):"]
            for msg in messages:
                details = self._get_email_summary(msg['id'])
                lines.append(f"\n  📧 {details}")

            return "\n".join(lines)
        except Exception as e:
            return f"Gmail: ❌ Search error — {e}"

    def _delete_latest(self) -> str:
        try:
            results = self._service.users().messages().list(
                userId='me', q="in:inbox", maxResults=1
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return "Gmail: Koi email nahi hai delete karne ke liye."

            self._service.users().messages().trash(
                userId='me', id=messages[0]['id']
            ).execute()

            return "Gmail: ✅ Latest email trash mein chali gayi."
        except Exception as e:
            return f"Gmail: ❌ Delete error — {e}"

    def _parse_and_reply(self, query: str) -> str:
        import re
        body_match = re.search(r'reply\s+"([^"]+)"', query, re.I)
        if not body_match:
            return "Gmail: Reply ka content batao — 'reply \"Theek hai, kal milte hain\"'"

        reply_body = body_match.group(1)

        try:
            results = self._service.users().messages().list(
                userId='me', q="in:inbox", maxResults=1
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return "Gmail: Koi email nahi hai reply karne ke liye."

            msg = self._service.users().messages().get(
                userId='me', id=messages[0]['id'], format='metadata',
                metadataHeaders=['From', 'Subject', 'Message-ID']
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            to      = headers.get('From', '')
            subject = "Re: " + headers.get('Subject', '')

            return self._send_email(to, subject, reply_body)
        except Exception as e:
            return f"Gmail: ❌ Reply error — {e}"
