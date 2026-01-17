# Solace + Cerebras Setup Guide

This guide shows you how to use **Solace PubSub+** (message broker) with **Cerebras LLM** (AI recovery plans) in Project Chronos.

## Overview

- **Solace PubSub+**: Production-grade message broker for event-driven architecture
- **Cerebras LLM**: Free-tier LLM API for AI recovery plan generation

Both work together seamlessly - Solace handles messaging, Cerebras handles AI.

---

## Step-by-Step Setup

### Part 1: Solace PubSub+ Setup

#### 1. Create Solace Cloud Account

1. Visit: https://console.solace.cloud
2. Click **"Sign Up"** or **"Get Started"** button
3. Fill out registration form (email, password, name, country)
4. Verify your email (check inbox/spam)
5. Complete onboarding if prompted

**See detailed guide**: `docs/SOLACE_SIGNUP_GUIDE.md`

#### 2. Create Messaging Service

1. After logging in, click **"Cluster Manager"** in left sidebar
   - Look for the globe icon with circular arrow
   - Description: "Control the lifecycle of your Solace Event Broker Services"
2. Click **"+ Create"** or **"Create"** or **"New Service"** button
3. Choose **Free tier** plan (perfect for development)
4. Enter service name (e.g., `chronos-messaging`)
5. Select region (choose closest to you)
6. Click **"Create"** and wait 2-3 minutes for provisioning

**See detailed guide**: `docs/SOLACE_SIGNUP_GUIDE.md`

#### 3. Get Connection Details

1. Once service is "Active", click on your service name
2. Click **"Connect"** tab (at the top)
3. Find **"Messaging Service Connection Information"** section
4. Copy these details:
   - **Host**: `xxx.messaging.solace.cloud` (click "Show" if hidden)
   - **Port**: `55555` (for SMF protocol)
   - **Message VPN**: Usually `default`
   - **Username**: Your Solace username
   - **Password**: Click "Show" to reveal, or "Generate New"

**See detailed guide**: `docs/SOLACE_SIGNUP_GUIDE.md` for screenshots and troubleshooting

#### 4. Add to `.env` File

```bash
# Solace PubSub+ Configuration
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

**Windows (PowerShell):**
```powershell
$env:SOLACE_HOST="xxx.messaging.solace.cloud"
$env:SOLACE_PORT="55555"
$env:SOLACE_VPN="default"
$env:SOLACE_USERNAME="your_username"
$env:SOLACE_PASSWORD="your_password"
```

---

### Part 2: Cerebras LLM Setup

#### 1. Create Cerebras Account

1. Visit: https://cloud.cerebras.ai
2. Click **"Sign Up"** or **"Get Started"**
3. Create your account
4. Verify your email if required

#### 2. Create API Key

1. After signing in, navigate to API Keys section
2. Click **"Create API Key"**
3. Copy the API key (you won't see it again!)

#### 3. Add to `.env` File

```bash
# Cerebras LLM Configuration
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_cerebras_api_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

**Windows (PowerShell):**
```powershell
$env:LLM_SERVICE_ENDPOINT="https://api.cerebras.ai/v1"
$env:LLM_SERVICE_API_KEY="your_cerebras_api_key_here"
$env:LLM_SERVICE_PLANNING_MODEL_NAME="openai/zai-glm-4.7"
$env:LLM_SERVICE_GENERAL_MODEL_NAME="openai/zai-glm-4.7"
```

---

## Complete `.env` Example

Here's a complete `.env` file with both Solace and Cerebras configured:

```bash
# ============================================
# Solace PubSub+ (Message Broker)
# ============================================
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# ============================================
# Cerebras LLM (AI Recovery Plans)
# ============================================
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_cerebras_api_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7

# ============================================
# MongoDB (Local - via Docker)
# ============================================
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=chronos
MONGO_PASS=chronos
MONGO_DB=chronos
```

---

## How It Works Together

### Event Flow with Solace + Cerebras

```
1. Crisis Generator
   └─> Publishes power.failure event
       └─> Sent via Solace PubSub+

2. Coordinator Agent
   └─> Receives event from Solace
       └─> Dispatches to frameworks

3. Recovery Planner
   └─> Receives event from Solace
       └─> Calls Cerebras API for recovery plan
       └─> Publishes plan via Solace

4. Autonomy Router
   └─> Receives plan from Solace
       └─> Routes based on autonomy level
```

### Priority Order

**Message Broker:**
1. **Solace** (if `SOLACE_HOST` is set)
2. **NATS** (default, if Solace not set)

**LLM Provider:**
1. **Cerebras** (if `LLM_SERVICE_API_KEY` is set)
2. **Gemini** (if `GEMINI_API_KEY` is set)
3. **Fallback plans** (if neither is set)

---

## Verification

### Check Solace Connection

When you start any agent service, you should see:

```
============================================================
SENTRY INITIALIZED
============================================================
Connected to Solace Cloud
Host: xxx.messaging.solace.cloud:55555
VPN: default
Username: your_username
============================================================
```

### Check Cerebras Connection

When recovery planner generates a plan, you should see:

```
Calling Cerebras API (openai/zai-glm-4.7) to generate recovery plan...
Recovery plan generated successfully using Cerebras
```

---

## Troubleshooting

### Solace Connection Failed

**Error**: `Failed to connect to Solace`

**Solutions**:
1. Check credentials are correct
2. Verify service is running in Solace Cloud dashboard
3. Check network/firewall settings
4. System will automatically fall back to NATS

### Cerebras API Failed

**Error**: `Cerebras API error: 401`

**Solutions**:
1. Check API key is correct
2. Verify you have tokens available (1M/day free)
3. Check model name is exact: `openai/zai-glm-4.7`
4. System will automatically fall back to Gemini or fallback plans

### Both Services Not Working

**Solution**: System automatically falls back:
- Solace → NATS (message broker)
- Cerebras → Gemini → Fallback plans (LLM)

Everything still works, just using fallbacks!

---

## Free Tier Limits

### Solace PubSub+
- **10,000 messages/day** (free tier)
- Perfect for development and demos

### Cerebras
- **1M tokens/day** (free tier)
- No credit card required
- Perfect for development and demos

---

## References

- **Solace Cloud**: https://console.solace.cloud
- **Cerebras Cloud**: https://cloud.cerebras.ai
- **Solace Agent Mesh Quickstart**: https://github.com/SolaceDev/solace-agent-mesh-hackathon-quickstart
- **Cerebras Setup Guide**: https://github.com/SolaceDev/solace-agent-mesh-hackathon-quickstart/blob/main/docs/llm-setup.md

---

## Quick Start Commands

```bash
# 1. Set Solace environment variables
export SOLACE_HOST=xxx.messaging.solace.cloud
export SOLACE_PORT=55555
export SOLACE_VPN=default
export SOLACE_USERNAME=your_username
export SOLACE_PASSWORD=your_password

# 2. Set Cerebras environment variables
export LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
export LLM_SERVICE_API_KEY=your_cerebras_api_key
export LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
export LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7

# 3. Start services
python agents/coordinator_agent.py
python ai/recovery_planner.py
```

**That's it!** The system will automatically use Solace for messaging and Cerebras for LLM calls.

---

**Happy coding! 🚀**

