#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Check for upcoming deadlines and send notifications."""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import configparser

sys.path.insert(0, str(Path(__file__).parent))
from database import get_upcoming_deadlines

# Load config
config = configparser.ConfigParser()
config.read(Path(__file__).parent.parent / 'config.ini')
HOURS_BEFORE = int(config['NOTIFICATIONS']['deadline_hours_before'])


def check_deadlines():
    """Check for upcoming deadlines and notify."""
    emails = get_upcoming_deadlines(HOURS_BEFORE)
    
    if not emails:
        print("No upcoming deadlines")
        return
    
    now = datetime.now()
    cutoff = now + timedelta(hours=HOURS_BEFORE)
    
    notifications_sent = 0
    
    for email in emails:
        for deadline in email['deadlines']:
            try:
                # Parse deadline date
                deadline_date = datetime.fromisoformat(deadline['date'])
                
                # Check if within notification window
                if now <= deadline_date <= cutoff:
                    hours_until = (deadline_date - now).total_seconds() / 3600
                    
                    if hours_until < 1:
                        time_str = "in less than 1 hour"
                        urgency = "critical"
                    elif hours_until < 24:
                        time_str = f"in {int(hours_until)} hours"
                        urgency = "critical"
                    else:
                        days = int(hours_until / 24)
                        time_str = f"in {days} day{'s' if days > 1 else ''}"
                        urgency = "normal"
                    
                    title = f"⏰ Deadline Reminder"
                    message = f"{deadline['description']} {time_str}\n\nFrom: {email['sender']}\nSubject: {email['subject']}"
                    
                    subprocess.run([
                        'notify-send',
                        title,
                        message,
                        f'--urgency={urgency}',
                        '--app-name=Email Reader'
                    ])
                    
                    notifications_sent += 1
                    print(f"✓ Notified: {deadline['description']} ({time_str})")
                    
            except (ValueError, KeyError) as e:
                print(f"Error parsing deadline: {e}")
                continue
    
    if notifications_sent > 0:
        print(f"\n✓ Sent {notifications_sent} deadline notification{'s' if notifications_sent > 1 else ''}")
    else:
        print("No deadlines within notification window")


if __name__ == '__main__':
    check_deadlines()
