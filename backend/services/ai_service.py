"""
AI Service — OpenRouter integration for the Data Analyst Copilot.
Uses nvidia/nemotron-3-ultra-550b-a55b:free via OpenRouter.
"""
import os
import json
import logging
import re
from typing import Optional
import httpx
from dotenv import load_dotenv

from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Default model
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_openrouter(prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
    """Call OpenRouter API and return text response."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set in environment!")
        return _mock_response(prompt)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",  # Replace with actual referer if available
        "X-Title": "Data Analyst Copilot",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                json=payload, 
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Optionally log reasoning tokens if present
            if "usage" in data and "completion_tokens_details" in data["usage"]:
                reasoning_tokens = data["usage"]["completion_tokens_details"].get("reasoning_tokens")
                if reasoning_tokens:
                    logger.debug(f"Reasoning tokens: {reasoning_tokens}")

            if "choices" not in data:
                error_info = data.get("error", data)
                raise ValueError(f"OpenRouter API returned an unexpected response: {error_info}")
                
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        raise


async def call_ai(
    prompt: str,
    system: Optional[str] = None,
    model: str = "openrouter",
    temperature: float = 0.2,
) -> str:
    """Unified AI call — routes to correct provider."""
    # We ignore the model parameter as we strictly use OpenRouter
    return await call_openrouter(prompt, system, temperature)


def extract_json(text: str) -> dict | list:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code blocks
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"\{[\s\S]*\}",
        r"\[[\s\S]*\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if "```" in pattern else match.group())
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


def _mock_response(prompt: str) -> str:
    """Mock response when no API key is configured."""
    if "intent" in prompt.lower():
        return json.dumps({
            "intent": "statistics",
            "confidence": 0.9,
            "suggested_approach": "Calculate basic statistics on numeric columns"
        })
    if "code" in prompt.lower() or "pandas" in prompt.lower():
        return json.dumps({
            "code": "result = df.describe()",
            "chart_requested": False,
            "result_type": "table",
            "explanation": "Basic statistical description of all numeric columns"
        })
    return "I need a valid API key to provide AI-powered analysis. Please configure OPENROUTER_API_KEY in your .env file."


async def generate_with_context(
    prompt: str,
    history: list[dict],
    system: Optional[str] = None,
    model: str = "openrouter",
) -> str:
    """Generate response with conversation history context."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set in environment!")
        return _mock_response(prompt)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})

    # Add history
    for msg in history[-10:]:  # Keep last 10 messages for context
        # Convert app roles to OpenRouter roles (user, assistant, system)
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({
            "role": role,
            "content": msg["content"]
        })

    # Add current prompt
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Data Analyst Copilot",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                json=payload, 
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            if "choices" not in data:
                error_info = data.get("error", data)
                raise ValueError(f"OpenRouter API returned an unexpected response: {error_info}")
                
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error generating with context: {e}")
        raise
