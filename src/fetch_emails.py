#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Fetch emails from Gmail via IMAP."""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import configparser
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from database_adapter import store_email


def decode_mime_words(s):
    """Decode MIME encoded-word strings."""
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    return ''.join(
        str(fragment, encoding or 'utf-8') if isinstance(fragment, bytes) else str(fragment)
        for fragment, encoding in decoded_fragments
    )


def get_email_body(msg):
    """Extract email body from message."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode()
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except:
            body = str(msg.get_payload())
    
    return body.strip()


def fetch_recent_emails(minutes=30):
    """Fetch emails from the last N minutes."""
    # Load config
    config = configparser.ConfigParser()
    config.read(Path(__file__).parent.parent / 'config.ini')
    
    email_address = config['IMAP']['email']
    password = config['IMAP']['password']
    imap_server = config['IMAP']['server']
    imap_port = int(config['IMAP']['port'])
    
    print(f"Connecting to {imap_server}...")
    
    # Connect to IMAP server
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_address, password)
    mail.select('INBOX')
    
    # Calculate date for search
    since_date = (datetime.now() - timedelta(minutes=minutes)).strftime("%d-%b-%Y")
    
    # Search for emails
    print(f"Searching for emails since {since_date}...")
    status, messages = mail.search(None, f'(SINCE {since_date})')
    
    if status != 'OK':
        print("Error searching emails")
        mail.logout()
        return
    
    email_ids = messages[0].split()
    print(f"Found {len(email_ids)} emails")
    
    fetched_count = 0
    
    for email_id in email_ids:
        # Fetch email
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            continue
        
        # Parse email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Extract details
        subject = decode_mime_words(msg.get('Subject', ''))
        sender = decode_mime_words(msg.get('From', ''))
        date_str = msg.get('Date', '')
        
        # Parse date
        try:
            received_at = email.utils.parsedate_to_datetime(date_str)
        except:
            received_at = datetime.now()
        
        # Get body
        body = get_email_body(msg)
        
        # Generate unique ID
        message_id = msg.get('Message-ID', f"{sender}_{subject}_{date_str}")
        
        # Store in database
        try:
            store_email(message_id, sender, subject, body, received_at)
            fetched_count += 1
            print(f"  ✓ Stored: {subject[:50]}...")
        except Exception as e:
            print(f"  ✗ Error storing email: {e}")
    
    mail.logout()
    print(f"\n✓ Fetched {fetched_count} new emails")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch emails from Gmail via IMAP')
    parser.add_argument('--minutes', type=int, default=30, help='Fetch emails from last N minutes')
    args = parser.parse_args()
    
    fetch_recent_emails(args.minutes)
