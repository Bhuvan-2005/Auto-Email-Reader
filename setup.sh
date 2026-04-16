#!/bin/bash
# Setup script for cron jobs and systemd services

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PYTHON=$(which python3)

echo "=== Email Reader Setup ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$PROJECT_DIR/requirements.txt"
echo ""

# Create systemd user service for dashboard
echo "Creating systemd user service for dashboard..."
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/email-dashboard.service << EOF
[Unit]
Description=Email Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON $PROJECT_DIR/src/dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

echo "✓ Created email-dashboard.service"
echo ""

# Create desktop autostart entry for startup notification
echo "Creating autostart entry for startup notification..."
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/email-notify.desktop << EOF
[Desktop Entry]
Type=Application
Name=Email Notification
Comment=Show notification for important emails
Exec=$PYTHON $PROJECT_DIR/src/notify_startup.py
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "✓ Created autostart entry"
echo ""

# Display cron job instructions
echo "=== Cron Job Setup ==="
echo "Add these lines to your crontab (run: crontab -e)"
echo ""
echo "# Email Reader - Fetch, analyze, and trash every 30 minutes"
echo "*/30 * * * * cd $PROJECT_DIR && $PYTHON src/fetch_emails.py && $PYTHON src/analyze_emails.py && $PYTHON src/auto_trash.py >> $PROJECT_DIR/data/cron.log 2>&1"
echo ""
echo "# Email Reader - Check deadlines daily at 9 AM"
echo "0 9 * * * $PYTHON $PROJECT_DIR/src/notify_deadlines.py"
echo ""
echo "=== Systemd Service Setup ==="
echo "Enable and start the dashboard service:"
echo "  systemctl --user enable email-dashboard.service"
echo "  systemctl --user start email-dashboard.service"
echo ""
echo "Check service status:"
echo "  systemctl --user status email-dashboard.service"
echo ""
echo "=== Manual Testing ==="
echo "Test email fetching:"
echo "  cd $PROJECT_DIR && python3 src/fetch_emails.py --minutes 1440"
echo ""
echo "Test analysis:"
echo "  cd $PROJECT_DIR && python3 src/analyze_emails.py"
echo ""
echo "Test dashboard:"
echo "  cd $PROJECT_DIR && python3 src/dashboard.py"
echo "  Then open: http://localhost:8472"
echo ""
echo "Test notifications:"
echo "  python3 $PROJECT_DIR/src/notify_startup.py"
echo ""
