"""
CLI for reading Gmail via the API instead of browser scraping.

Usage:
  python gmail_search.py search "<gmail search query>" [--max 25]
      Lists matching messages: id, date, from, subject, snippet.

  python gmail_search.py read <message_id>
      Prints the full plain-text body of one message.

Search query syntax is the same as Gmail's search bar
(from:, newer_than:, subject:, OR, quoted phrases, etc).
"""
import argparse
import base64
import sys

sys.stdout.reconfigure(encoding="utf-8")

from gmail_auth import get_credentials
from googleapiclient.discovery import build


def get_service():
    return build("gmail", "v1", credentials=get_credentials())


def cmd_search(query, max_results):
    service = get_service()
    resp = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = resp.get("messages", [])
    if not messages:
        print("No results.")
        return
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        print(f"id: {m['id']}")
        print(f"  date:    {headers.get('Date', '')}")
        print(f"  from:    {headers.get('From', '')}")
        print(f"  subject: {headers.get('Subject', '')}")
        print(f"  snippet: {msg.get('snippet', '')}")
        print()


def _extract_body(payload):
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


def cmd_read(message_id):
    service = get_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    print(f"From:    {headers.get('From', '')}")
    print(f"Date:    {headers.get('Date', '')}")
    print(f"Subject: {headers.get('Subject', '')}")
    print()
    print(_extract_body(msg["payload"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--max", type=int, default=25)

    p_read = sub.add_parser("read")
    p_read.add_argument("message_id")

    args = parser.parse_args()
    if args.cmd == "search":
        cmd_search(args.query, args.max)
    elif args.cmd == "read":
        cmd_read(args.message_id)
