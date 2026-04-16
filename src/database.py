#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Database initialization and helper functions."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import configparser

# Load config
config = configparser.ConfigParser()
config.read(Path(__file__).parent.parent / 'config.ini')
DB_PATH = Path(__file__).parent.parent / config['DATABASE']['path']


def init_database():
    """Initialize the database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Emails table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            received_at TIMESTAMP NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Analysis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis (
            email_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            priority INTEGER NOT NULL CHECK(priority >= 0 AND priority <= 10),
            deadlines TEXT,
            should_trash BOOLEAN DEFAULT 0,
            reasoning TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(id)
        )
    ''')
    
    # Trash log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trash_log (
            email_id TEXT PRIMARY KEY,
            trashed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            priority INTEGER,
            can_undo BOOLEAN DEFAULT 1,
            FOREIGN KEY (email_id) REFERENCES emails(id)
        )
    ''')
    
    # Config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized at {DB_PATH}")


def get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def store_email(email_id, sender, subject, body, received_at):
    """Store an email in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO emails (id, sender, subject, body, received_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (email_id, sender, subject, body, received_at))
    
    conn.commit()
    conn.close()


def store_analysis(email_id, summary, priority, deadlines, should_trash, reasoning):
    """Store email analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    
    deadlines_json = json.dumps(deadlines) if deadlines else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO analysis 
        (email_id, summary, priority, deadlines, should_trash, reasoning)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (email_id, summary, priority, deadlines_json, should_trash, reasoning))
    
    conn.commit()
    conn.close()


def get_unanalyzed_emails():
    """Get emails that haven't been analyzed yet."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.id, e.sender, e.subject, e.body, e.received_at
        FROM emails e
        LEFT JOIN analysis a ON e.id = a.email_id
        WHERE a.email_id IS NULL
        ORDER BY e.received_at DESC
    ''')
    
    emails = cursor.fetchall()
    conn.close()
    return emails


def get_emails_for_dashboard():
    """Get analyzed emails for dashboard display."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            e.id, e.sender, e.subject, e.received_at, e.is_read,
            a.summary, a.priority, a.deadlines
        FROM emails e
        INNER JOIN analysis a ON e.id = a.email_id
        LEFT JOIN trash_log t ON e.id = t.email_id
        WHERE t.email_id IS NULL AND a.priority >= 3
        ORDER BY a.priority DESC, e.received_at DESC
        LIMIT 100
    ''')
    
    emails = []
    for row in cursor.fetchall():
        emails.append({
            'id': row[0],
            'sender': row[1],
            'subject': row[2],
            'received_at': row[3],
            'is_read': row[4],
            'summary': row[5],
            'priority': row[6],
            'deadlines': json.loads(row[7]) if row[7] else []
        })
    
    conn.close()
    return emails


def get_low_priority_emails():
    """Get low priority emails (priority <= 2) for review."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            e.id, e.sender, e.subject, e.received_at, e.is_read,
            a.summary, a.priority, a.reasoning
        FROM emails e
        INNER JOIN analysis a ON e.id = a.email_id
        LEFT JOIN trash_log t ON e.id = t.email_id
        WHERE t.email_id IS NULL AND a.priority <= 2
        ORDER BY a.priority ASC, e.received_at DESC
        LIMIT 50
    ''')
    
    emails = []
    for row in cursor.fetchall():
        emails.append({
            'id': row[0],
            'sender': row[1],
            'subject': row[2],
            'received_at': row[3],
            'is_read': row[4],
            'summary': row[5],
            'priority': row[6],
            'reasoning': row[7]
        })
    
    conn.close()
    return emails


def mark_as_read(email_id):
    """Mark an email as read."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE emails SET is_read = 1 WHERE id = ?', (email_id,))
    
    conn.commit()
    conn.close()


def log_trash(email_id, reason, priority):
    """Log a trashed email."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO trash_log (email_id, reason, priority)
        VALUES (?, ?, ?)
    ''', (email_id, reason, priority))
    
    conn.commit()
    conn.close()


def get_upcoming_deadlines(hours_before=24):
    """Get emails with deadlines in the next N hours."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            e.id, e.subject, e.sender,
            a.deadlines, a.summary
        FROM emails e
        INNER JOIN analysis a ON e.id = a.email_id
        LEFT JOIN trash_log t ON e.id = t.email_id
        WHERE t.email_id IS NULL
        AND a.deadlines IS NOT NULL
        AND a.deadlines != '[]'
    ''')
    
    emails = []
    for row in cursor.fetchall():
        deadlines = json.loads(row[3]) if row[3] else []
        if deadlines:
            emails.append({
                'id': row[0],
                'subject': row[1],
                'sender': row[2],
                'deadlines': deadlines,
                'summary': row[4]
            })
    
    conn.close()
    return emails


if __name__ == '__main__':
    init_database()
