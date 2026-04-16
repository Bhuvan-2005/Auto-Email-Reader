# Email Auto-Reader with AI Analysis

Automatically fetch, analyze, and manage Gmail emails using IMAP and AI analysis. Features a web dashboard with priority-based filtering and cloud deployment support.

![Dashboard Preview](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 📧 **Auto-fetch emails** via IMAP (every 30 minutes)
- 🤖 **AI analysis** with kiro-cli (priority scoring, summaries, deadline extraction)
- 🗑️ **Manual review** of low-priority emails before deletion
- 📊 **Web dashboard** with tabbed interface (Main / Low Priority)
- 🔔 **Desktop notifications** for important emails and deadlines
- ☁️ **Cloud deployment** ready (Render + Supabase)
- 🔄 **Dual database** support (SQLite local / PostgreSQL cloud)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Gmail account with IMAP enabled
- Gmail app password (2FA required)
- kiro-cli installed

### Local Setup

1. **Clone repository**
```bash
git clone https://github.com/YOUR_USERNAME/autoEmailReader.git
cd autoEmailReader
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure**
```bash
cp config.ini.example config.ini
# Edit config.ini with your Gmail credentials
```

4. **Initialize database**
```bash
python3 src/database_adapter.py
```

5. **Fetch and analyze emails**
```bash
python3 src/fetch_emails.py --minutes 10080  # Last 7 days
python3 src/analyze_emails.py
```

6. **Start dashboard**
```bash
python3 src/dashboard.py
# Open http://localhost:8472
```

## ☁️ Cloud Deployment

### Deploy to Render + Supabase

See detailed guides:
- [Supabase Setup](SUPABASE_SETUP.md)
- [Render Deployment](RENDER_DEPLOYMENT.md)
- [Pipeline Architecture](PIPELINE_ARCHITECTURE.md)

**Quick steps:**

1. Create Supabase project → Get `DATABASE_URL`
2. Push to GitHub
3. Deploy to Render with environment variables:
   - `DATABASE_URL` (Supabase connection string)
   - `DASHBOARD_USER` (your choice)
   - `DASHBOARD_PASSWORD` (strong password)

## 📋 Priority Scoring

- **9-10 (Critical)**: Job offers, interview invitations, internship opportunities
- **6-8 (Important)**: Networking emails, career events, academic deadlines
- **3-5 (Medium)**: Tech newsletters, course updates, social notifications
- **1-2 (Low)**: Marketing emails, promotional spam (manual review)
- **0 (Spam)**: Obvious spam, phishing

## 🗂️ Project Structure

```
autoEmailReader/
├── src/
│   ├── database_adapter.py    # Dual DB support (SQLite/PostgreSQL)
│   ├── fetch_emails.py         # IMAP email fetcher
│   ├── analyze_emails.py       # AI analyzer (parallel)
│   ├── dashboard.py            # Local Flask dashboard
│   ├── dashboard_render.py     # Cloud dashboard (with auth)
│   ├── notify_startup.py       # Startup notifications
│   └── notify_deadlines.py     # Deadline checker
├── templates/
│   └── index.html              # Dashboard UI (tabbed)
├── static/
│   └── style.css               # Dark theme styling
├── config.ini.example          # Configuration template
├── requirements.txt            # Local dependencies
├── requirements-render.txt     # Cloud dependencies
├── render.yaml                 # Render deployment config
├── Procfile                    # Alternative deployment config
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables (Cloud)

```bash
DATABASE_URL=postgresql://user:pass@host:port/db
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=secure_password
```

### Local Config (config.ini)

```ini
[IMAP]
email = your.email@gmail.com
password = your_app_password

[DASHBOARD]
port = 8472
```

## 🛠️ Development

### Run locally with Supabase

```bash
export DATABASE_URL='postgresql://...'
python3 src/fetch_emails.py --minutes 1440
python3 src/analyze_emails.py
python3 src/dashboard.py
```

### Systemd timers (Linux)

```bash
# Enable automatic fetching/analysis
systemctl --user enable --now email-fetch.timer
systemctl --user enable --now email-deadlines.timer

# Check status
systemctl --user list-timers
```

## 📊 Database Schema

- **emails**: Raw email data (id, sender, subject, body, received_at)
- **analysis**: AI-generated metadata (summary, priority, deadlines, reasoning)
- **trash_log**: Trashed emails (email_id, trashed_at, reason)

## 🔒 Security

- ✅ IMAP credentials in config.ini (gitignored)
- ✅ HTTP Basic Auth on cloud dashboard
- ✅ Environment variables for secrets
- ✅ SSL/TLS for database connections
- ✅ No secrets in code or git history

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📚 Documentation

- [Pipeline Architecture](PIPELINE_ARCHITECTURE.md) - Detailed system flow
- [Supabase Setup](SUPABASE_SETUP.md) - Database configuration
- [Render Deployment](RENDER_DEPLOYMENT.md) - Cloud deployment guide

## 🐛 Troubleshooting

**IMAP connection fails:**
- Verify IMAP is enabled in Gmail settings
- Check app password is correct
- Ensure 2FA is enabled

**Dashboard shows no emails:**
- Run fetch and analyze scripts
- Check database has data
- Verify DATABASE_URL if using cloud

**Analysis fails:**
- Check kiro-cli is installed: `which kiro-cli`
- Test kiro-cli: `kiro-cli chat --prompt "test"`
- Check kiro-cli has credits/quota

## 📧 Support

For issues or questions, please open a GitHub issue.

---

Built with ❤️ using Flask, PostgreSQL, and AI
