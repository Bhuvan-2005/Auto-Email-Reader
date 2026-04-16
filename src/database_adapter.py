#!/usr/bin/env python3
"""Database adapter supporting both SQLite (local) and PostgreSQL (Render)."""

import os
import json
from datetime import datetime
from pathlib import Path
import configparser

# Detect environment
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_RENDER = DATABASE_URL is not None

if IS_RENDER:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    def get_connection():
        """Get PostgreSQL connection."""
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
else:
    import sqlite3
    
    config = configparser.ConfigParser()
    config.read(Path(__file__).parent.parent / 'config.ini')
    DB_PATH = Path(__file__).parent.parent / config['DATABASE']['path']
    
    def get_connection():
        """Get SQLite connection."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_database():
    """Initialize database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_RENDER:
        # PostgreSQL schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                received_at TIMESTAMP NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis (
                email_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                priority INTEGER NOT NULL CHECK(priority >= 0 AND priority <= 10),
                deadlines TEXT,
                should_trash BOOLEAN DEFAULT FALSE,
                reasoning TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trash_log (
                email_id TEXT PRIMARY KEY,
                trashed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                priority INTEGER,
                can_undo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
    else:
        # SQLite schema (existing)
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
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized ({'PostgreSQL' if IS_RENDER else 'SQLite'})")


def dict_from_row(row):
    """Convert database row to dict."""
    if IS_RENDER:
        return dict(row)
    else:
        return dict(row)


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
        row_dict = dict_from_row(row)
        emails.append({
            'id': row_dict['id'],
            'sender': row_dict['sender'],
            'subject': row_dict['subject'],
            'received_at': str(row_dict['received_at']),
            'is_read': row_dict['is_read'],
            'summary': row_dict['summary'],
            'priority': row_dict['priority'],
            'deadlines': json.loads(row_dict['deadlines']) if row_dict['deadlines'] else []
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
        row_dict = dict_from_row(row)
        emails.append({
            'id': row_dict['id'],
            'sender': row_dict['sender'],
            'subject': row_dict['subject'],
            'received_at': str(row_dict['received_at']),
            'is_read': row_dict['is_read'],
            'summary': row_dict['summary'],
            'priority': row_dict['priority'],
            'reasoning': row_dict['reasoning']
        })
    
    conn.close()
    return emails


def mark_as_read(email_id):
    """Mark an email as read."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE emails SET is_read = %s WHERE id = %s' if IS_RENDER 
                   else 'UPDATE emails SET is_read = 1 WHERE id = ?',
                   (True, email_id) if IS_RENDER else (email_id,))
    
    conn.commit()
    conn.close()


def log_trash(email_id, reason, priority):
    """Log email to trash."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO trash_log (email_id, reason, priority)
        VALUES (%s, %s, %s)
        ON CONFLICT (email_id) DO NOTHING
    ''' if IS_RENDER else '''
        INSERT OR IGNORE INTO trash_log (email_id, reason, priority)
        VALUES (?, ?, ?)
    ''', (email_id, reason, priority))
    
    conn.commit()
    conn.close()


def store_email(email_id, sender, subject, body, received_at):
    """Store an email in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO emails (id, sender, subject, body, received_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    ''' if IS_RENDER else '''
        INSERT OR IGNORE INTO emails (id, sender, subject, body, received_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (email_id, sender, subject, body, received_at))
    
    conn.commit()
    conn.close()


def store_analysis(email_id, summary, priority, deadlines, should_trash, reasoning):
    """Store email analysis."""
    import json
    conn = get_connection()
    cursor = conn.cursor()
    
    deadlines_json = json.dumps(deadlines) if deadlines else None
    
    cursor.execute('''
        INSERT INTO analysis 
        (email_id, summary, priority, deadlines, should_trash, reasoning)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (email_id) DO UPDATE SET
            summary = EXCLUDED.summary,
            priority = EXCLUDED.priority,
            deadlines = EXCLUDED.deadlines,
            should_trash = EXCLUDED.should_trash,
            reasoning = EXCLUDED.reasoning
    ''' if IS_RENDER else '''
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
    return [tuple(dict_from_row(row).values()) for row in emails]
