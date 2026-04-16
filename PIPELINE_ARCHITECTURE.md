# Email Reader Pipeline Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOCAL MACHINE (Your Computer)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐    │
│  │   Gmail      │         │  kiro-cli    │         │   Systemd    │    │
│  │   IMAP       │         │  AI Engine   │         │   Timers     │    │
│  │   Server     │         │              │         │              │    │
│  └──────┬───────┘         └──────┬───────┘         └──────┬───────┘    │
│         │                        │                        │             │
│         │                        │                        │             │
│         ▼                        ▼                        ▼             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Python Scripts (src/)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │fetch_emails  │  │analyze_emails│  │  dashboard   │          │   │
│  │  │    .py       │─▶│    .py       │  │    .py       │          │   │
│  │  └──────────────┘  └──────────────┘  └──────┬───────┘          │   │
│  │         │                  │                 │                   │   │
│  └─────────┼──────────────────┼─────────────────┼───────────────────┘   │
│            │                  │                 │                       │
│            ▼                  ▼                 ▼                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              database_adapter.py (Dual DB Support)               │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  Detects DATABASE_URL environment variable               │   │   │
│  │  │  • If set → PostgreSQL (Supabase)                        │   │   │
│  │  │  • If not set → SQLite (local file)                      │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│            │                                                            │
└────────────┼────────────────────────────────────────────────────────────┘
             │
             │ DATABASE_URL set
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLOUD (Supabase)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    PostgreSQL Database                           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │    │
│  │  │  emails  │  │ analysis │  │trash_log │                      │    │
│  │  │  table   │  │  table   │  │  table   │                      │    │
│  │  └──────────┘  └──────────┘  └──────────┘                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ▲                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
                               │ Reads data
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│                         CLOUD (Render.com)                               │
├──────────────────────────────┼───────────────────────────────────────────┤
│                              │                                            │
│  ┌───────────────────────────┴──────────────────────────────────────┐   │
│  │              Flask Web App (dashboard_render.py)                  │   │
│  │  • HTTP Basic Auth (username/password)                           │   │
│  │  • Reads from Supabase PostgreSQL                                │   │
│  │  • Serves web dashboard                                          │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              ▼                                            │
│                    https://your-app.onrender.com                         │
│                    (Accessible from anywhere)                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Pipeline Flow

### 1. EMAIL FETCHING (Every 30 minutes)

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Systemd Timer Triggers                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ email-fetch.timer (runs every 30 min)                       │ │
│ │   └─▶ email-fetch.service                                   │ │
│ │         └─▶ fetch_emails.py --minutes 30                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Connect to Gmail via IMAP                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • Server: imap.gmail.com:993 (SSL)                          │ │
│ │ • Auth: App Password (from config.ini)                      │ │
│ │ • Search: Emails from last 30 minutes                       │ │
│ │ • Extract: ID, sender, subject, body, received_at           │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Store in Database                                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ database_adapter.store_email()                              │ │
│ │   └─▶ INSERT INTO emails (id, sender, subject, body, ...)  │ │
│ │       ON CONFLICT DO NOTHING (skip duplicates)              │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. AI ANALYSIS (Every 30 minutes, after fetching)

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Get Unanalyzed Emails                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ SELECT emails WHERE NOT IN analysis table                   │ │
│ │ Returns: List of emails needing analysis                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Parallel AI Analysis (5 concurrent workers)             │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ThreadPoolExecutor (max_workers=5)                          │ │
│ │                                                             │ │
│ │  Email 1 ──┐                                                │ │
│ │  Email 2 ──┼──▶ kiro-cli chat --no-interactive \           │ │
│ │  Email 3 ──┤      --trust-all-tools <prompt>               │ │
│ │  Email 4 ──┤                                                │ │
│ │  Email 5 ──┘                                                │ │
│ │                                                             │ │
│ │  Each worker:                                               │ │
│ │  1. Formats prompt with email content                       │ │
│ │  2. Calls kiro-cli subprocess                               │ │
│ │  3. Parses JSON response                                    │ │
│ │  4. Stores analysis in database                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: AI Prompt Template                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Input: Email (sender, subject, body)                        │ │
│ │                                                             │ │
│ │ Tasks:                                                      │ │
│ │ 1. Summarize in 3 sentences                                 │ │
│ │ 2. Assign priority (0-10)                                   │ │
│ │    • 9-10: Job offers, interviews, internships              │ │
│ │    • 6-8: Networking, career events, deadlines              │ │
│ │    • 3-5: Newsletters, course updates                       │ │
│ │    • 1-2: Marketing, promotional                            │ │
│ │    • 0: Spam                                                │ │
│ │ 3. Extract deadlines (dates + descriptions)                 │ │
│ │ 4. Recommend trash (if priority ≤ 2)                        │ │
│ │                                                             │ │
│ │ Output: JSON                                                │ │
│ │ {                                                           │ │
│ │   "summary": "3 sentence summary",                          │ │
│ │   "priority": 7,                                            │ │
│ │   "deadlines": [{date, description}],                       │ │
│ │   "should_trash": false,                                    │ │
│ │   "reasoning": "Why this priority"                          │ │
│ │ }                                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Store Analysis                                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ database_adapter.store_analysis()                           │ │
│ │   └─▶ INSERT INTO analysis (email_id, summary, priority,   │ │
│ │       deadlines, should_trash, reasoning)                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. DASHBOARD (Always Running)

```
┌─────────────────────────────────────────────────────────────────┐
│ LOCAL DASHBOARD (localhost:8472)                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Flask App (dashboard.py)                                    │ │
│ │                                                             │ │
│ │ Routes:                                                     │ │
│ │ • GET  /           → Main page with tabs                   │ │
│ │ • GET  /api/emails → JSON list of emails                   │ │
│ │ • POST /api/mark_read/<id> → Mark email as read            │ │
│ │ • POST /api/trash/<id> → Move to trash                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE QUERIES                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Main Emails Tab (priority ≥ 3):                            │ │
│ │   SELECT emails JOIN analysis                               │ │
│ │   WHERE priority >= 3 AND NOT IN trash_log                  │ │
│ │   ORDER BY priority DESC, received_at DESC                  │ │
│ │                                                             │ │
│ │ Low Priority Tab (priority ≤ 2):                           │ │
│ │   SELECT emails JOIN analysis                               │ │
│ │   WHERE priority <= 2 AND NOT IN trash_log                  │ │
│ │   ORDER BY priority ASC, received_at DESC                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ UI FEATURES                                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • Tabbed interface (Main / Low Priority)                   │ │
│ │ • Sort controls (Priority / Date)                           │ │
│ │ • Color-coded priority badges                               │ │
│ │ • 3-sentence summaries                                      │ │
│ │ • Deadline indicators with dates                            │ │
│ │ • Mark as read button                                       │ │
│ │ • Trash/Keep buttons (low priority)                         │ │
│ │ • Auto-refresh every 2 minutes                              │ │
│ │ • Dark theme (GitHub colors)                                │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. RENDER DEPLOYMENT (Cloud Dashboard)

```
┌─────────────────────────────────────────────────────────────────┐
│ RENDER.COM WEB SERVICE                                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Flask App (dashboard_render.py)                             │ │
│ │                                                             │ │
│ │ Differences from local:                                     │ │
│ │ • HTTP Basic Auth (username/password)                       │ │
│ │ • Always uses PostgreSQL (DATABASE_URL)                     │ │
│ │ • Gunicorn WSGI server (production-ready)                   │ │
│ │ • Health check endpoint (/health)                           │ │
│ │ • Environment variables for config                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AUTHENTICATION FLOW                                              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. User visits https://your-app.onrender.com                │ │
│ │ 2. Browser prompts for username/password                    │ │
│ │ 3. Server checks against DASHBOARD_USER/PASSWORD env vars   │ │
│ │ 4. If valid → Show dashboard                                │ │
│ │    If invalid → 401 Unauthorized                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
┌─────────────────────────────────────────────────────────────────┐
│ TABLE: emails                                                    │
├─────────────────────────────────────────────────────────────────┤
│ id              TEXT PRIMARY KEY    (Gmail message ID)          │
│ sender          TEXT NOT NULL       (From address)              │
│ subject         TEXT                (Email subject)             │
│ body            TEXT                (Email content)             │
│ received_at     TIMESTAMP NOT NULL  (When email was received)   │
│ is_read         BOOLEAN DEFAULT 0   (Read status)               │
│ fetched_at      TIMESTAMP           (When we fetched it)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:1
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ TABLE: analysis                                                  │
├─────────────────────────────────────────────────────────────────┤
│ email_id        TEXT PRIMARY KEY    (FK → emails.id)           │
│ summary         TEXT NOT NULL       (3 sentence summary)        │
│ priority        INTEGER NOT NULL    (0-10 score)                │
│ deadlines       TEXT                (JSON array)                │
│ should_trash    BOOLEAN DEFAULT 0   (AI recommendation)         │
│ reasoning       TEXT                (Why this priority)         │
│ analyzed_at     TIMESTAMP           (When analyzed)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 0:1
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ TABLE: trash_log                                                 │
├─────────────────────────────────────────────────────────────────┤
│ email_id        TEXT PRIMARY KEY    (FK → emails.id)           │
│ trashed_at      TIMESTAMP           (When trashed)              │
│ reason          TEXT                (Why trashed)               │
│ priority        INTEGER             (Priority at trash time)    │
│ can_undo        BOOLEAN DEFAULT 1   (Can be restored)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

```
Gmail IMAP
    │
    │ fetch_emails.py (every 30 min)
    ▼
┌─────────────┐
│   emails    │ (raw email data)
└──────┬──────┘
       │
       │ analyze_emails.py (every 30 min)
       │ ↓ kiro-cli AI analysis
       ▼
┌─────────────┐
│  analysis   │ (AI-generated metadata)
└──────┬──────┘
       │
       │ User action in dashboard
       ▼
┌─────────────┐
│  trash_log  │ (trashed emails)
└─────────────┘
       ▲
       │
       │ dashboard.py reads all tables
       │
   ┌───┴────┐
   │ LOCAL  │ (localhost:8472)
   └────────┘
       │
       │ Same database via DATABASE_URL
       │
   ┌───┴────┐
   │ RENDER │ (https://your-app.onrender.com)
   └────────┘
```

---

## Current Setup

### Local (Your Computer)
- **Fetch**: Systemd timer → fetch_emails.py → Supabase
- **Analyze**: Systemd timer → analyze_emails.py → Supabase
- **Dashboard**: Running on localhost:8472 → Reads from Supabase
- **Database**: Supabase PostgreSQL (cloud)

### Render (When Deployed)
- **Dashboard**: Web service → Reads from Supabase
- **Auth**: HTTP Basic Auth (username/password)
- **Database**: Same Supabase PostgreSQL
- **URL**: https://your-app.onrender.com

---

## Key Design Decisions

### 1. Dual Database Support
```python
if DATABASE_URL:
    # Use PostgreSQL (Supabase)
    conn = psycopg2.connect(DATABASE_URL)
else:
    # Use SQLite (local file)
    conn = sqlite3.connect('data/emails.db')
```

### 2. Parallel Analysis
- 5 concurrent kiro-cli processes
- 5x faster than sequential
- Thread-safe with locks

### 3. Priority-Based Filtering
- Main tab: priority ≥ 3 (important emails)
- Low priority tab: priority ≤ 2 (review before trash)
- Trash log: excluded from both tabs

### 4. Idempotent Operations
- `INSERT ... ON CONFLICT DO NOTHING` (no duplicates)
- Re-running fetch/analyze is safe
- Can re-analyze by deleting from analysis table

---

## Monitoring & Logs

### Local
```bash
# Check systemd timers
systemctl --user list-timers

# View fetch logs
journalctl --user -u email-fetch.service -f

# View dashboard logs
tail -f /tmp/dashboard.log
```

### Supabase
- Table Editor: View data
- SQL Editor: Run queries
- Logs: Database activity

### Render
- Dashboard → Logs tab
- Real-time deployment logs
- Application logs

---

## Security Layers

1. **IMAP**: App password (not main Gmail password)
2. **Supabase**: Connection string with password
3. **Render Dashboard**: HTTP Basic Auth
4. **Git**: .gitignore excludes config.ini and .env
5. **Environment Variables**: Secrets not in code
