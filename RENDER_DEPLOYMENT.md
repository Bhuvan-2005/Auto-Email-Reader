# Deploying to Render

## Prerequisites

1. GitHub account
2. Render account (free tier works)
3. This repository pushed to GitHub

## Deployment Steps

### 1. Push to GitHub

```bash
cd /home/bhuvan/Documents/Projects/autoEmailReader

# Create new repo (if not exists)
git init
git add .
git commit -m "Initial commit for Render deployment"

# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/autoEmailReader.git
git branch -M main
git push -u origin main
```

**Important:** Make sure `.gitignore` excludes `config.ini` and `data/` directory.

### 2. Create PostgreSQL Database on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "PostgreSQL"
3. Name: `email-db`
4. Database: `emailreader`
5. User: `emailreader`
6. Region: Choose closest to you
7. Plan: **Free**
8. Click "Create Database"
9. Wait for database to provision (~2 minutes)

### 3. Deploy Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name:** `email-dashboard`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements-render.txt`
   - **Start Command:** `gunicorn src.dashboard_render:app`
   - **Plan:** Free

4. Add Environment Variables:
   - `DASHBOARD_USER` = `your_username` (choose a username)
   - `DASHBOARD_PASSWORD` = `your_secure_password` (choose a strong password)
   - `DATABASE_URL` = (Connect to `email-db` database - Render will auto-fill this)

5. Click "Create Web Service"

### 4. Wait for Deployment

- First deploy takes ~5 minutes
- Watch the logs for any errors
- Once deployed, you'll get a URL like: `https://email-dashboard-xxxx.onrender.com`

### 5. Access Dashboard

1. Open the Render URL in browser
2. Enter the username/password you set in environment variables
3. You should see the dashboard (empty initially)

## Important Notes

### Database Initialization

The database tables are created automatically on first startup. Check the logs to confirm:
```
✓ Database initialized (PostgreSQL)
```

### Email Fetching (Local Only)

**The Render deployment is READ-ONLY.** Email fetching and analysis still runs locally:

1. Keep your local systemd timers running
2. Local scripts will populate the local SQLite database
3. **You need to sync data from local to Render PostgreSQL**

### Data Sync Options

**Option A: Manual Export/Import (Simple)**

Export from local SQLite:
```bash
cd /home/bhuvan/Documents/Projects/autoEmailReader
sqlite3 data/emails.db .dump > backup.sql
```

Import to Render PostgreSQL (convert SQLite to PostgreSQL syntax first - complex).

**Option B: Dual Database Support (Recommended)**

Modify local scripts to write to BOTH SQLite and PostgreSQL:
- Set `DATABASE_URL` environment variable locally pointing to Render PostgreSQL
- Local scripts write to remote database
- Dashboard reads from same database

**Option C: API Sync (Advanced)**

Create an API endpoint on Render that accepts email data from local scripts.

### Security

- Dashboard is password-protected with HTTP Basic Auth
- Change default credentials immediately
- Don't commit `config.ini` with IMAP password
- Use Render environment variables for secrets

### Limitations

- **Free tier sleeps after 15 min inactivity** (30 sec cold start)
- **750 hours/month free** (enough for 24/7 if only one service)
- **PostgreSQL free tier:** 256 MB storage, 97 hours/month
- **No background workers on free tier** (email fetching must run locally)

### Troubleshooting

**Database connection errors:**
- Check `DATABASE_URL` is set correctly
- Verify PostgreSQL database is running
- Check Render logs for connection errors

**Authentication not working:**
- Verify `DASHBOARD_USER` and `DASHBOARD_PASSWORD` are set
- Clear browser cache/cookies
- Try incognito mode

**Empty dashboard:**
- Database is empty initially
- Need to populate data (see Data Sync Options above)
- Check if tables were created (see logs)

## Next Steps

After deployment, you need to decide how to populate the Render database:

1. **Keep it local** - Don't deploy, just use localhost:8472
2. **Sync manually** - Periodically export/import data
3. **Dual write** - Modify local scripts to write to Render PostgreSQL
4. **Full migration** - Move email fetching/analysis to Render (requires paid plan for background workers)

## Recommended Approach

For your use case, I recommend **keeping the system local** because:
- Email fetching requires local IMAP access
- kiro-cli analysis runs locally
- No need for remote access if you're always on your machine
- More secure (not exposed to internet)
- Simpler architecture

If you need remote access occasionally, use SSH tunnel:
```bash
ssh -L 8472:localhost:8472 your-server
```

Then access via `http://localhost:8472` from any device.
