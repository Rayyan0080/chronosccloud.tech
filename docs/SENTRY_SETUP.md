# Sentry Error Tracking Setup Guide

This guide shows you how to set up Sentry for error tracking and monitoring in Project Chronos.

---

## What is Sentry?

Sentry provides error tracking, performance monitoring, and observability for your applications. In Project Chronos, it captures:
- **Service startup events**
- **Received events** (from message broker)
- **Published events** (to message broker)
- **Exceptions and errors** (with full stack traces)

---

## Step-by-Step Setup

### Step 1: Sign Up for Sentry

1. **Visit**: https://sentry.io
2. **Click** "Get Started" or "Sign Up" button (usually top right)
3. **Choose sign-up method**:
   - Sign up with email
   - Sign up with Google
   - Sign up with GitHub
4. **Fill out registration form** (if using email):
   - Email address
   - Password
   - Name
   - Company (optional)
5. **Verify your email** (check inbox/spam folder)
6. **Complete onboarding** (if prompted)

### Step 2: Create a Project

1. **After logging in**, you'll see the Sentry dashboard
2. **Click** "Create Project" or "+ New Project" button
   - Usually a prominent button on the dashboard
   - Or go to: https://sentry.io/organizations/[your-org]/projects/new/

3. **Select Platform**:
   - Choose **"Python"** from the list
   - Or search for "Python" in the search box

4. **Configure Project**:
   - **Project Name**: Enter `chronos-cloud` or `project-chronos`
   - **Team**: Select your team (or create one)
   - **Alerts**: Choose notification preferences (optional)

5. **Click** "Create Project"

### Step 3: Get Your DSN (Data Source Name)

1. **After creating the project**, you'll see a setup page
2. **Look for "Client Keys (DSN)"** section:
   - This shows your DSN (Data Source Name)
   - It looks like: `https://xxx@xxx.ingest.sentry.io/xxx`

3. **Copy the DSN**:
   - Click the "Copy" button next to the DSN
   - Or manually select and copy the entire DSN string
   - **Important**: You'll need this for your `.env` file

4. **Alternative**: If you closed the setup page:
   - Go to your project dashboard
   - Click **"Settings"** → **"Projects"** → **"Client Keys (DSN)"**
   - Copy the DSN from there

### Step 4: Add to `.env` File

1. **Open your `.env` file** in the project root:

   **Windows (PowerShell):**
   ```powershell
   notepad .env
   ```

   **Mac/Linux:**
   ```bash
   nano .env
   ```

2. **Add Sentry configuration**:

   ```bash
   # Sentry Error Tracking
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   SENTRY_ENVIRONMENT=development
   SENTRY_RELEASE=1.0.0
   ```

   **Example:**
   ```bash
   SENTRY_DSN=https://abc123def456@o123456.ingest.sentry.io/789012
   SENTRY_ENVIRONMENT=development
   SENTRY_RELEASE=1.0.0
   ```

3. **Save and close** the file

### Step 5: Set Environment Variables (Alternative)

If you prefer to set environment variables directly:

**Windows (PowerShell):**
```powershell
$env:SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
$env:SENTRY_ENVIRONMENT="development"
$env:SENTRY_RELEASE="1.0.0"
```

**Mac/Linux:**
```bash
export SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx"
export SENTRY_ENVIRONMENT="development"
export SENTRY_RELEASE="1.0.0"
```

---

## Verification

### Test the Setup

1. **Start any agent service**:
   ```bash
   cd agents
   python crisis_generator.py
   ```

2. **Look for Sentry initialization message**:
   ```
   ============================================================
   SENTRY INITIALIZED
   ============================================================
   Service: crisis_generator
   Environment: development
   ============================================================
   ```

3. **Check Sentry dashboard**:
   - Go to: https://sentry.io
   - Click on your project
   - You should see events appearing in real-time

### What Gets Captured

When services start, you'll see in Sentry:
- **Service startup events** (info level)
- **Received events** (info level)
- **Published events** (info level)
- **Exceptions** (error level with full stack traces)

---

## Free Tier Limits

- **5,000 events/month** (free tier)
- Perfect for development and demos
- No credit card required
- Includes error tracking and performance monitoring

### Check Your Usage

1. Go to: https://sentry.io/organizations/[your-org]/usage/
2. See your current usage and remaining quota

---

## Troubleshooting

### Problem: "SENTRY_DSN not set, skipping Sentry initialization"

**Solution:**
1. Check your `.env` file has `SENTRY_DSN=...`
2. Make sure there are no spaces around the `=` sign
3. Verify the DSN starts with `https://` and ends with a number
4. Restart your agent services after adding the DSN

### Problem: "Failed to initialize Sentry"

**Solution:**
1. Check your DSN is correct (no typos)
2. Make sure you copied the entire DSN string
3. Verify you're logged into the correct Sentry account
4. Check internet connection
5. System will continue working without Sentry (no errors)

### Problem: Events not appearing in Sentry

**Solution:**
1. Wait 10-30 seconds (events may take time to appear)
2. Refresh the Sentry dashboard
3. Check you're looking at the correct project
4. Verify DSN matches the project
5. Check service logs for "SENTRY INITIALIZED" message

### Problem: "sentry-sdk not installed"

**Solution:**
1. Install Sentry SDK:
   ```bash
   pip install sentry-sdk
   ```
2. Or install all dependencies:
   ```bash
   pip install -r agents/shared/requirements.txt
   ```

---

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | Yes | None | Your Sentry DSN (required) |
| `SENTRY_ENVIRONMENT` | No | `development` | Environment name (dev/staging/prod) |
| `SENTRY_RELEASE` | No | `unknown` | Release version (e.g., `1.0.0`) |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance monitoring sample rate (0.0 to 1.0) |

### Example Configurations

**Development:**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Production:**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=2.1.0
SENTRY_TRACES_SAMPLE_RATE=0.05
```

---

## What Gets Tracked

### Service Tags

All events include these tags for filtering:

- **service_name**: `crisis_generator`, `coordinator_agent`, `autonomy_router`, etc.
- **autonomy_mode**: `NORMAL`, `HIGH`, or framework name
- **event_type**: `startup`, `received_event`, `published_event`, `exception`

### Event Types

1. **Startup Events**:
   - Captured when each service starts
   - Includes service configuration
   - Tagged with `event_type: startup`

2. **Received Events**:
   - Captured when services receive events from message broker
   - Includes event topic and ID
   - Tagged with `event_type: received_event`

3. **Published Events**:
   - Captured when services publish events
   - Includes event topic and ID
   - Tagged with `event_type: published_event`

4. **Exceptions**:
   - Captured automatically when exceptions occur
   - Includes full stack trace
   - Tagged with `event_type: exception`

---

## Viewing Data in Sentry

### Issues Page

View all errors and exceptions:
- Go to: https://sentry.io/organizations/[your-org]/issues/
- Filter by service: `service_name:crisis_generator`
- Filter by autonomy: `autonomy_mode:HIGH`
- Filter by event type: `event_type:exception`

### Performance Page

Track service performance:
- Go to: https://sentry.io/organizations/[your-org]/performance/
- See average execution time per service
- Identify slow operations
- View performance trends

### Events Page

View all captured events:
- Go to: https://sentry.io/organizations/[your-org]/events/
- See startup events, received/published events
- Filter by tags and time range

### Dashboards

Create custom dashboards:
- Go to: https://sentry.io/organizations/[your-org]/dashboards/
- Create custom views
- Monitor service health
- Track error rates

---

## How It Works

### Integration Points

Sentry is integrated into all agent services:
- `agents/crisis_generator.py`
- `agents/coordinator_agent.py`
- `agents/autonomy_router.py`
- `agents/state_logger.py`
- `agents/stress_monitor.py`
- `agents/solana_audit_logger.py`
- `agents/qnx_event_source.py`

### Automatic Initialization

Each service automatically:
1. Initializes Sentry on startup (if DSN is set)
2. Sets service tags
3. Captures events throughout execution
4. Handles failures gracefully (no crashes if Sentry fails)

### Fallback Behavior

If Sentry is unavailable:
- System continues working normally
- No errors or crashes
- Just no error tracking
- All functionality remains intact

---

## Example Configuration

### Complete `.env` Example

```bash
# Sentry Error Tracking
SENTRY_DSN=https://abc123def456@o123456.ingest.sentry.io/789012
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1

# Other APIs (optional)
ELEVENLABS_API_KEY=sk-your-key
GEMINI_API_KEY=your-gemini-key
SOLACE_HOST=xxx.messaging.solace.cloud
```

---

## Quick Reference

### URLs
- **Sign Up**: https://sentry.io/signup/
- **Dashboard**: https://sentry.io/organizations/[your-org]/
- **Projects**: https://sentry.io/organizations/[your-org]/projects/
- **Settings**: https://sentry.io/organizations/[your-org]/settings/

### Environment Variables
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx  # Required
SENTRY_ENVIRONMENT=development  # Optional
SENTRY_RELEASE=1.0.0  # Optional
SENTRY_TRACES_SAMPLE_RATE=0.1  # Optional
```

### Free Tier
- **5,000 events/month**
- Includes error tracking
- Includes performance monitoring
- No credit card required

---

## Next Steps

After setting up Sentry:

1. ✅ Start your agent services
2. ✅ Check Sentry dashboard for events
3. ✅ Create custom dashboards
4. ✅ Set up alerts (optional)
5. ✅ Monitor error rates

---

## Need Help?

- **Sentry Docs**: https://docs.sentry.io
- **Python SDK Docs**: https://docs.sentry.io/platforms/python/
- **Support**: Available in Sentry dashboard

---

**You're all set! 📊**

Your services will now automatically track errors and events in Sentry!

