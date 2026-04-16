#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Auto-trash low-priority emails via IMAP."""

import imaplib
import configparser
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))
from database import get_connection, log_trash


def get_emails_to_trash(threshold=2):
    """Get emails that should be trashed based on priority."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.id, a.priority, a.reasoning
        FROM emails e
        INNER JOIN analysis a ON e.id = a.email_id
        LEFT JOIN trash_log t ON e.id = t.email_id
        WHERE a.priority <= ? AND t.email_id IS NULL
    ''', (threshold,))
    
    emails = cursor.fetchall()
    conn.close()
    return emails


def trash_email_via_imap(mail, message_id):
    """Move an email to trash folder via IMAP."""
    try:
        # Search for email by Message-ID
        status, messages = mail.search(None, f'HEADER Message-ID "{message_id}"')
        
        if status != 'OK' or not messages[0]:
            return False
        
        email_ids = messages[0].split()
        
        for email_id in email_ids:
            # Copy to Trash
            mail.copy(email_id, '[Gmail]/Trash')
            # Mark as deleted in INBOX
            mail.store(email_id, '+FLAGS', '\\Deleted')
        
        # Expunge to actually delete
        mail.expunge()
        return True
        
    except Exception as e:
        print(f"  Error trashing: {e}")
        return False


def auto_trash():
    """Auto-trash low-priority emails."""
    # Load config
    config = configparser.ConfigParser()
    config.read(Path(__file__).parent.parent / 'config.ini')
    
    threshold = int(config['TRASH']['priority_threshold'])
    email_address = config['IMAP']['email']
    password = config['IMAP']['password']
    imap_server = config['IMAP']['server']
    imap_port = int(config['IMAP']['port'])
    
    # Get emails to trash
    emails_to_trash = get_emails_to_trash(threshold)
    
    if not emails_to_trash:
        print("No emails to trash")
        return
    
    print(f"Found {len(emails_to_trash)} emails to trash (priority ≤ {threshold})")
    
    # Connect to IMAP
    print(f"Connecting to {imap_server}...")
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_address, password)
    mail.select('INBOX')
    
    trashed_count = 0
    
    for email_id, priority, reasoning in emails_to_trash:
        print(f"Trashing email (priority {priority})...")
        
        if trash_email_via_imap(mail, email_id):
            log_trash(email_id, reasoning, priority)
            trashed_count += 1
            print(f"  ✓ Trashed")
        else:
            print(f"  ✗ Failed to trash")
    
    mail.logout()
    print(f"\n✓ Trashed {trashed_count} emails")


if __name__ == '__main__':
    auto_trash()
