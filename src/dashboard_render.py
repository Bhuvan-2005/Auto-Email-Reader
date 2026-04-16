#!/usr/bin/env python3
"""Flask dashboard for email viewer (Render-compatible)."""

import os
from flask import Flask, render_template, jsonify, request, Response
from functools import wraps
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from database_adapter import get_emails_for_dashboard, get_low_priority_emails, mark_as_read, log_trash, init_database

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent.parent / 'templates'),
            static_folder=str(Path(__file__).parent.parent / 'static'))

# Basic auth
DASHBOARD_USER = os.environ.get('DASHBOARD_USER', 'admin')
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'changeme')

def check_auth(username, password):
    """Check if username/password is valid."""
    return username == DASHBOARD_USER and password == DASHBOARD_PASSWORD

def authenticate():
    """Send 401 response."""
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Email Dashboard"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
@requires_auth
def index():
    """Main dashboard page."""
    emails = get_emails_for_dashboard()
    low_priority = get_low_priority_emails()
    return render_template('index.html', emails=emails, low_priority=low_priority)


@app.route('/api/emails')
@requires_auth
def api_emails():
    """API endpoint for emails."""
    emails = get_emails_for_dashboard()
    return jsonify(emails)


@app.route('/api/mark_read/<email_id>', methods=['POST'])
@requires_auth
def api_mark_read(email_id):
    """Mark email as read."""
    try:
        mark_as_read(email_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trash/<email_id>', methods=['POST'])
@requires_auth
def api_trash(email_id):
    """Move email to trash."""
    try:
        log_trash(email_id, "Manually trashed from dashboard", 0)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


def keep_alive():
    """Background thread to ping self every 10 minutes."""
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not render_url:
        return  # Only run on Render
    
    time.sleep(300)  # Wait 5 min after startup
    
    while True:
        try:
            requests.get(f"{render_url}/health", timeout=10)
            print(f"Self-ping successful at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Self-ping failed: {e}")
        
        time.sleep(600)  # Ping every 10 minutes


if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    # Start keep-alive thread if on Render
    if os.environ.get('RENDER_EXTERNAL_URL'):
        ping_thread = threading.Thread(target=keep_alive, daemon=True)
        ping_thread.start()
        print("Self-ping thread started")
    
    PORT = int(os.environ.get('PORT', 8472))
    app.run(host='0.0.0.0', port=PORT, debug=False)
