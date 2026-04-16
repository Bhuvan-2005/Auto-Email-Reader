#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Startup notification for unread important emails."""

import subprocess
import sys
from pathlib import Path
import configparser

sys.path.insert(0, str(Path(__file__).parent))
from database import get_connection

# Load config
config = configparser.ConfigParser()
config.read(Path(__file__).parent.parent / 'config.ini')
PORT = config['DASHBOARD']['port']


def get_unread_important_count():
    """Get count of unread emails with priority >= 6."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*), MAX(a.priority)
        FROM emails e
        INNER JOIN analysis a ON e.id = a.email_id
        LEFT JOIN trash_log t ON e.id = t.email_id
        WHERE e.is_read = 0 
        AND a.priority >= 6
        AND t.email_id IS NULL
    ''')
    
    count, max_priority = cursor.fetchone()
    conn.close()
    return count or 0, max_priority or 0


def send_notification():
    """Send desktop notification."""
    count, max_priority = get_unread_important_count()
    
    if count == 0:
        print("No important unread emails")
        return
    
    # Determine urgency
    if max_priority >= 9:
        urgency = "critical"
        icon = "🔴"
    elif max_priority >= 7:
        urgency = "normal"
        icon = "🟠"
    else:
        urgency = "low"
        icon = "🔵"
    
    title = f"{icon} {count} Important Email{'s' if count > 1 else ''}"
    message = f"You have {count} unread important email{'s' if count > 1 else ''} (Priority {max_priority})"
    
    # Send notification with action
    try:
        subprocess.run([
            'notify-send',
            title,
            message,
            f'--urgency={urgency}',
            '--app-name=Email Reader',
            f'--action=view=View Dashboard'
        ], check=True)
        
        print(f"✓ Notification sent: {count} emails")
        
    except subprocess.CalledProcessError:
        # Fallback without action
        subprocess.run([
            'notify-send',
            title,
            message,
            f'--urgency={urgency}',
            '--app-name=Email Reader'
        ])
        print(f"✓ Notification sent (no action): {count} emails")


if __name__ == '__main__':
    send_notification()
