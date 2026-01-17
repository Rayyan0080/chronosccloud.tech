# Solace Cloud Sign-Up and Messaging Service Creation Guide

This is a **detailed, step-by-step guide** for creating a Solace Cloud account and setting up a messaging service.

---

## Part 1: Sign Up for Solace Cloud

### Step 1: Go to Solace Cloud

1. Open your web browser
2. Navigate to: **https://console.solace.cloud**
3. You'll see the Solace Cloud login page

### Step 2: Create Account

1. Click the **"Sign Up"** or **"Get Started"** button (usually in the top right corner)
2. You'll be taken to the registration page

### Step 3: Fill Out Registration Form

You'll need to provide:
- **Email address** (required)
- **Password** (required, must meet security requirements)
- **First Name** (required)
- **Last Name** (required)
- **Company/Organization** (optional)
- **Country** (required)

### Step 4: Verify Email

1. After submitting the form, check your email inbox
2. Look for an email from Solace (check spam folder if needed)
3. Click the verification link in the email
4. You'll be redirected back to Solace Cloud

### Step 5: Complete Onboarding (if prompted)

Some accounts may see an onboarding wizard:
- Choose your use case (select "Event-Driven Architecture" or "Messaging")
- Select your industry (optional)
- Click "Continue" or "Skip" to proceed

---

## Part 2: Create a Messaging Service

### Step 1: Navigate to Cluster Manager

After logging in, you'll see the Solace Cloud dashboard:

1. Look for **"Cluster Manager"** in the left sidebar menu
   - Icon: Globe with circular arrow around it
   - Description: "Control the lifecycle of your Solace Event Broker Services"
2. Click on **"Cluster Manager"**
3. You'll see a page to manage your messaging services

### Step 2: Create New Service

1. Click the **"+ Create"** or **"Create Messaging Service"** button
   - This is usually a prominent button at the top of the page
   - May be labeled as "New Messaging Service" or have a "+" icon

### Step 3: Choose a Plan

You'll see different plan options:

1. **Free Tier** (Recommended for development):
   - Usually labeled as "Developer" or "Free"
   - 10,000 messages/day
   - Perfect for testing and demos
   - Click **"Select"** or **"Choose Plan"**

2. **Paid Plans** (for production):
   - Higher message limits
   - More features
   - Only choose if you need production-level service

**For Project Chronos, the Free tier is perfect!**

### Step 4: Configure Service Details

You'll need to fill out a form with:

1. **Service Name**:
   - Enter a name like: `chronos-messaging` or `my-chronos-service`
   - This is just for your reference

2. **Data Center Region**:
   - Select the region closest to you
   - Examples: `US East`, `US West`, `Europe`, `Asia Pacific`
   - Choose based on your location for best performance

3. **Message VPN Name** (optional):
   - Usually defaults to `default`
   - You can leave this as-is for most cases

4. **Service Type** (if prompted):
   - Usually defaults to "Cloud" or "Standard"
   - Leave as default unless you have specific requirements

### Step 5: Review and Create

1. Review your selections
2. Check the terms of service (if shown)
3. Click **"Create"** or **"Create Service"** button
4. Wait 2-3 minutes for provisioning

**Important**: Don't close the browser tab while provisioning!

### Step 6: Service Provisioning

You'll see a status page showing:
- "Provisioning..." or "Creating Service..."
- Progress indicators
- This usually takes 2-3 minutes

**Wait until you see "Active" or "Ready" status**

---

## Part 3: Get Connection Details

### Step 1: Open Your Service

1. Once provisioning is complete, click on your service name
2. You'll be taken to the service details page

### Step 2: Navigate to Connect Tab

1. Look for tabs at the top: **"Overview"**, **"Connect"**, **"Monitor"**, etc.
2. Click on the **"Connect"** tab
3. This shows all connection information

### Step 3: Find Connection Details

You'll see several sections. Look for:

#### **Messaging Service Connection Information**

You'll find:

1. **Host** (also called "Service URL" or "SMF Host"):
   - Format: `xxx.messaging.solace.cloud`
   - Example: `mr2j0v0i0u0.messaging.solace.cloud`
   - **Copy this entire hostname**

2. **Port**:
   - Usually `55555` for SMF (Simple Messaging Format)
   - May also show `443` for HTTPS
   - **Use port 55555 for Project Chronos**

3. **Message VPN**:
   - Usually `default` or the name you specified
   - **Copy this value**

4. **Username**:
   - Usually your Solace Cloud username
   - Or a service-specific username
   - **Copy this value**

5. **Password**:
   - Click **"Show"** or **"Reveal"** to see the password
   - Or click **"Generate New Password"** if needed
   - **Copy this value**

#### **Alternative: Connection Strings**

Some dashboards show connection strings like:
```
smf://xxx.messaging.solace.cloud:55555
```

You can extract:
- **Host**: `xxx.messaging.solace.cloud`
- **Port**: `55555`

---

## Part 4: Add to Your `.env` File

### Step 1: Open `.env` File

Create or edit `.env` in your project root:

**Windows (PowerShell):**
```powershell
notepad .env
```

**Mac/Linux:**
```bash
nano .env
```

### Step 2: Add Solace Configuration

Add these lines (replace with your actual values):

```bash
# Solace PubSub+ Configuration
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

**Example:**
```bash
SOLACE_HOST=mr2j0v0i0u0.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=myusername
SOLACE_PASSWORD=abc123xyz
```

### Step 3: Save and Close

Save the file and close the editor.

---

## Part 5: Verify Connection

### Step 1: Start an Agent Service

```bash
cd agents
python coordinator_agent.py
```

### Step 2: Look for Connection Message

You should see:

```
============================================================
Connected to Solace Cloud
Host: xxx.messaging.solace.cloud:55555
VPN: default
Username: your_username
============================================================
```

**If you see this, you're connected! ✅**

---

## Troubleshooting

### Problem: "Sign Up" button not visible

**Solution:**
- Try: https://console.solace.cloud/signup
- Or look for "Create Account" link

### Problem: Email verification not received

**Solution:**
1. Check spam/junk folder
2. Wait 5-10 minutes
3. Try resending verification email
4. Check email address is correct

### Problem: Can't find "Messaging Services" or "Cluster Manager" menu

**Solution:**
1. Make sure you're logged in
2. Look for **"Cluster Manager"** in the left sidebar
   - Icon: Globe with circular arrow
   - This is where you create messaging services
3. If you don't see it, try refreshing the page
4. Make sure your account is fully verified

### Problem: "Create" button is disabled

**Solution:**
1. Make sure you've filled all required fields
2. Check that you've selected a plan
3. Verify email is verified

### Problem: Service stuck in "Provisioning"

**Solution:**
1. Wait 5-10 minutes (can take longer)
2. Refresh the page
3. Check Solace Cloud status page
4. Contact Solace support if still stuck

### Problem: Can't find connection details

**Solution:**
1. Make sure service status is "Active"
2. Click on the service name to open details
3. Look for "Connect" tab (not "Overview")
4. Scroll down to see all connection info

### Problem: Connection fails with credentials

**Solution:**
1. Double-check all values are correct (no extra spaces)
2. Verify host includes `.messaging.solace.cloud`
3. Check port is `55555` (not `443`)
4. Try generating a new password
5. Verify VPN name is correct (usually `default`)

---

## Visual Guide (What to Look For)

### Dashboard Layout

```
┌─────────────────────────────────────┐
│  Solace Cloud                      │
│  [Messaging Services] [Other...]   │
├─────────────────────────────────────┤
│                                     │
│  [+ Create]  [Search...]            │
│                                     │
│  Your Services:                     │
│  (empty list)                       │
│                                     │
└─────────────────────────────────────┘
```

### Create Service Form

```
┌─────────────────────────────────────┐
│  Create Messaging Service            │
├─────────────────────────────────────┤
│  Service Name: [chronos-messaging]  │
│  Region: [US East ▼]                │
│  Plan: [Free] [Select]              │
│                                     │
│  [Cancel]  [Create]                 │
└─────────────────────────────────────┘
```

### Connect Tab

```
┌─────────────────────────────────────┐
│  Service: chronos-messaging          │
│  [Overview] [Connect] [Monitor]     │
├─────────────────────────────────────┤
│  Connection Information:            │
│                                     │
│  Host: xxx.messaging.solace.cloud  │
│  Port: 55555                        │
│  VPN: default                       │
│  Username: your_username            │
│  Password: [Show] [Generate New]    │
└─────────────────────────────────────┘
```

---

## Quick Reference

### URLs
- **Sign Up**: https://console.solace.cloud/signup
- **Login**: https://console.solace.cloud
- **Dashboard**: https://console.solace.cloud/dashboard

### Default Values
- **Port**: `55555`
- **VPN**: `default`
- **Protocol**: SMF (Simple Messaging Format)

### Free Tier Limits
- **Messages**: 10,000/day
- **Connections**: Limited
- **Perfect for**: Development, demos, testing

---

## Next Steps

After setting up Solace:

1. ✅ Add credentials to `.env` file
2. ✅ Test connection with an agent service
3. ✅ Set up Cerebras LLM (see `docs/cerebras_setup.md`)
4. ✅ Run the full system (see `docs/demo_script.md`)

---

## Need Help?

- **Solace Documentation**: https://docs.solace.com
- **Solace Support**: Available in the dashboard
- **Community Forum**: https://solace.community

---

**You're all set! 🎉**

Once you have your connection details, add them to `.env` and you're ready to use Solace PubSub+ with Project Chronos!

