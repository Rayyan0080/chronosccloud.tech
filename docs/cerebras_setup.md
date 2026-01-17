# Cerebras LLM Setup Guide

Cerebras provides a free LLM API that works great with Project Chronos. This guide shows you how to set it up.

## Why Cerebras?

- ✅ **Free tier**: 1M tokens/day (no credit card required)
- ✅ **Fast**: Low latency API
- ✅ **OpenAI-compatible**: Easy integration
- ✅ **No setup complexity**: Just API key needed

## Quick Setup (5 minutes)

### Step 1: Sign Up for Cerebras

1. Visit: https://cloud.cerebras.ai
2. Click "Sign Up" or "Get Started"
3. Create your account (email verification may be required)

### Step 2: Create API Key

1. After signing in, go to your dashboard
2. Navigate to API Keys section
3. Click "Create API Key"
4. Copy the API key (you won't see it again!)

### Step 3: Configure Environment Variables

Add these to your `.env` file:

```bash
# Cerebras LLM Configuration
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_api_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

**Important**: Use the model names exactly as shown. The `openai/` prefix and model IDs are specific to Cerebras's API.

### Step 4: Test the Setup

1. Start your recovery planner:
   ```bash
   python ai/recovery_planner.py
   ```

2. Trigger a power failure:
   ```bash
   python agents/crisis_generator.py
   # Press 'f' to trigger
   ```

3. Check logs for:
   ```
   Calling Cerebras API (openai/zai-glm-4.7) to generate recovery plan...
   Recovery plan generated successfully using Cerebras
   ```

## Model Options

### Default Model (Recommended)
```bash
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```
- **Speed**: Fast
- **Capability**: Good for most use cases
- **Tokens**: Efficient

### Larger Model (More Capable)
```bash
LLM_SERVICE_PLANNING_MODEL_NAME=openai/qwen-3-235b-a22b-instruct-2507
LLM_SERVICE_GENERAL_MODEL_NAME=openai/qwen-3-235b-a22b-instruct-2507
```
- **Speed**: Slower
- **Capability**: More advanced reasoning
- **Tokens**: Higher usage

## How It Works

1. **Power failure event** is received
2. **Recovery planner** calls `get_recovery_plan()`
3. **LLM client** checks for Cerebras API key first
4. **Cerebras API** is called with OpenAI-compatible format
5. **Response** is parsed and validated
6. **Recovery plan** is published to message broker

## Priority Order

The system tries LLM providers in this order:

1. **Cerebras** (if `LLM_SERVICE_API_KEY` is set)
2. **Gemini** (if `GEMINI_API_KEY` is set)
3. **Fallback plans** (deterministic, no API needed)

## Free Tier Limits

- **1M tokens/day** (generous for development/demo)
- **No credit card required**
- **No expiration** (as long as account is active)

## Troubleshooting

### "Cerebras API error: 401"

**Solution**: Check your API key is correct
```bash
echo $LLM_SERVICE_API_KEY
```

### "Cerebras API error: 404"

**Solution**: Check model name is correct
- Must include `openai/` prefix
- Use exact model IDs: `zai-glm-4.7` or `qwen-3-235b-a22b-instruct-2507`

### "Failed to parse JSON from Cerebras response"

**Solution**: 
- Check API response in logs
- System will automatically fall back to Gemini or fallback plans
- This is normal if the model returns unexpected format

### "No LLM API keys configured"

**Solution**: 
- System uses fallback plans (still works!)
- Or set up Cerebras/Gemini API key

## Integration with Solace

Cerebras works seamlessly with Solace PubSub+:

1. **Set up Solace** (see README.md for Solace setup)
2. **Set up Cerebras** (this guide)
3. **System automatically uses both**:
   - Solace for message broker
   - Cerebras for LLM calls

No additional configuration needed!

## Example Configuration

Complete `.env` setup with Solace + Cerebras:

```bash
# Solace PubSub+ (Message Broker)
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# Cerebras LLM (AI Recovery Plans)
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_cerebras_api_key
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

## References

- **Cerebras Cloud**: https://cloud.cerebras.ai
- **Solace Agent Mesh Quickstart**: https://github.com/SolaceDev/solace-agent-mesh-hackathon-quickstart
- **LLM Setup Guide**: https://github.com/SolaceDev/solace-agent-mesh-hackathon-quickstart/blob/main/docs/llm-setup.md

---

**Happy coding! 🚀**

