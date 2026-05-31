import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional

import ollama
from intent import parse_intent

# Standard logger setup for intent recognition
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a voice assistant for a todo list app.

Understand user intent from natural speech (casual, messy, or incomplete).

Return ONLY valid JSON. No markdown, no explanations, no extra text.

Allowed actions:
add, delete, done, clear, show

Rules:
- Focus on meaning, not keywords
- "show my list", "what are my tasks", "can you show my empty list" → show
- If unsure, choose "show"

Output format:
{
  "action": "add|delete|done|clear|show",
  "tasks": [],
  "positions": []
}

Examples:

User: show my list
{"action":"show","tasks":[],"positions":[]}

User: can you show my empty list
{"action":"show","tasks":[],"positions":[]}

User: add milk eggs
{"action":"add","tasks":["milk","eggs"],"positions":[]}

User: remove milk
{"action":"delete","tasks":[],"positions":[]}

User: mark 2 done
{"action":"done","tasks":[],"positions":[2]}

User: clear list
{"action":"clear","tasks":[],"positions":[]}
"""


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts and parses a JSON object from a string block.
    
    Args:
        text: The raw string response from the LLM.
        
    Returns:
        The parsed dictionary if successful, None otherwise.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except (json.JSONDecodeError, TypeError):
        return None


async def parse_intent_llm(text: str) -> Dict[str, Any]:
    """Parses user intent from natural language using local Ollama (Mistral).
    
    This function executes the synchronous Ollama API in a separate thread to keep
    the main asyncio event loop unblocked. If the local Ollama instance is offline,
    or the model is missing, it automatically falls back to a fast, rule-based
    keyword matcher to maintain bot functionality.
    
    Args:
        text: The raw transcription text.
        
    Returns:
        A dictionary containing "action", "tasks", and "positions".
    """
    try:
        # Run synchronous Ollama call in a thread-safe worker to prevent event loop lag
        response = await asyncio.to_thread(
            ollama.chat,
            model="mistral",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        
        content = response.get("message", {}).get("content", "")
        data = extract_json(content)
        
        if data:
            return {
                "action": data.get("action", "show"),
                "tasks": data.get("tasks", []) or [],
                "positions": data.get("positions", []) or []
            }
            
    except Exception as e:
        logger.warning(
            f"Ollama/Mistral intent extraction failed (falling back to keyword matching): {e}"
        )
        # Graceful degradation fallback to local regex-based logic
        return parse_intent(text)

    # Safe default if LLM returns unstructured output
    return {
        "action": "show",
        "tasks": [],
        "positions": []
    }