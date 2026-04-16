# Deploying with Supabase Database

## Quick Setup

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Sign up/login
3. Click "New Project"
4. Fill in:
   - **Name:** `email-reader`
   - **Database Password:** (generate strong password - save it!)
   - **Region:** Choose closest to you
   - **Plan:** Free
5. Click "Create new project"
6. Wait ~2 minutes for provisioning

### 2. Get Database Connection String

1. In Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **Connection string** section
3. Select **URI** tab
4. Copy the connection string (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with the password you set in step 1

### 3. Initialize Database Tables

**Option A: Using Supabase SQL Editor (Recommended)**

1. In Supabase dashboard, go to **SQL Editor**
2. Click "New query"
3. Paste this SQL:

```sql
-- Emails table
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    sender TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMP NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis table
CREATE TABLE IF NOT EXISTS analysis (
    email_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK(priority >= 0 AND priority <= 10),
    deadlines TEXT,
    should_trash BOOLEAN DEFAULT FALSE,
    reasoning TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id)
);

-- Trash log table
CREATE TABLE IF NOT EXISTS trash_log (
    email_id TEXT PRIMARY KEY,
    trashed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    priority INTEGER,
    can_undo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (email_id) REFERENCES emails(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails(received_at);
CREATE INDEX IF NOT EXISTS idx_analysis_priority ON analysis(priority);
CREATE INDEX IF NOT EXISTS idx_trash_log_email_id ON trash_log(email_id);
```

4. Click "Run" (or press Ctrl+Enter)
5. Verify tables created: Go to **Table Editor** and see `emails`, `analysis`, `trash_log`

**Option B: Auto-initialize on first run**

The app will create tables automatically when it starts (if they don't exist).

### 4. Deploy to Render

1. Push code to GitHub (see main README)
2. Go to https://dashboard.render.com
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Configure:
   - **Name:** `email-dashboard`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements-render.txt`
   - **Start Command:** `gunicorn src.dashboard_render:app`
   - **Plan:** Free

6. **Add Environment Variables:**
   - `DATABASE_URL` = `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres`
   - `DASHBOARD_USER` = `your_username` (choose any)
   - `DASHBOARD_PASSWORD` = `your_password` (choose strong password)

7. Click "Create Web Service"
8. Wait for deployment (~3-5 minutes)

### 5. Populate Database from Local

**Option A: Modify local scripts to write to Supabase**

Set environment variable locally:
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"
cd /home/bhuvan/Documents/Projects/autoEmailReader
python3 src/fetch_emails.py --minutes 10080  # Last 7 days
python3 src/analyze_emails.py
```

This will fetch and analyze emails directly into Supabase.

**Option B: Keep dual databases**

- Local scripts write to local SQLite
- Periodically sync to Supabase (manual export/import)

**Recommended: Option A** - Set `DATABASE_URL` locally so all scripts write directly to Supabase.

### 6. Access Dashboard

1. Open your Render URL: `https://email-dashboard-xxxx.onrender.com`
2. Enter username/password you set
3. View your emails!

## Supabase Benefits

✅ **500 MB free storage** (vs Render's 256 MB)
✅ **Unlimited paused hours** (Render has 97 hours/month limit)
✅ **Better PostgreSQL dashboard** (Table Editor, SQL Editor)
✅ **Real-time subscriptions** (if you want live updates later)
✅ **Built-in auth** (if you want to add user accounts later)

## Monitoring

**Supabase Dashboard:**
- View tables: **Table Editor**
- Run queries: **SQL Editor**
- Check usage: **Settings** → **Usage**

**Render Dashboard:**
- View logs: Click on service → **Logs** tab
- Check status: Service overview page

## Troubleshooting

**Connection refused:**
- Check `DATABASE_URL` is correct
- Verify Supabase project is running
- Check password has no special characters that need escaping

**Tables not created:**
- Run SQL manually in Supabase SQL Editor
- Check Render logs for errors

**Empty dashboard:**
- Database is empty - run local scripts with `DATABASE_URL` set
- Or manually insert test data in Supabase Table Editor

## Cost

- **Supabase Free:** 500 MB database, 2 GB bandwidth/month
- **Render Free:** 750 hours/month, sleeps after 15 min inactivity
- **Total:** $0/month (both free tiers)

## Security Notes

- Dashboard is password-protected
- Supabase connection uses SSL by default
- Don't commit `DATABASE_URL` to git
- Use strong passwords for both dashboard and database
