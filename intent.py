import re
from typing import Dict, List, Any

# Local keyword triggers for rule-based matching
ADD_WORDS = [
    "add", "adding", "put", "include", "create", "note", "remember",
    "koodu", "seer", "ezhudu", "podu",           # Tamil
    "jodo", "daalo", "likhna", "likhlo", "yaad"  # Hindi
]

DONE_WORDS = [
    "done", "complete", "finished", "check", "tick", "mark",
    "achu", "mudinjuchu", "cross", "pannitu"      # Tamil
]

DELETE_WORDS = [
    "delete", "remove", "erase", "cancel",
    "thodu", "azhichu", "edutha",                # Tamil
    "hatao", "mitao", "hata do"                  # Hindi
]

CLEAR_WORDS = [
    "clear", "reset", "wipe", "all done", "empty",
    "ellam", "azhichu", "purify",                # Tamil
    "sab", "saaf", "poora"                       # Hindi
]

SHOW_WORDS = [
    "show", "list", "display", "kaata", "paaru", # Tamil
    "dikha", "batao", "kya hai"                  # Hindi
]


def _contains(text: str, words: List[str]) -> bool:
    """Helper to check if any of the given keywords are present in the text."""
    t = text.lower()
    return any(w in t for w in words)


def _extract_numbers(text: str) -> List[int]:
    """Helper to extract all numbers from text (e.g. for indicating task indexes)."""
    return [int(n) for n in re.findall(r'\d+', text)]


def _extract_tasks(text: str) -> List[str]:
    """Helper to extract clean task descriptions from casual natural language."""
    split_pattern = r'\band\b|\balso\b|\bthen\b|\bum\b|\benna\b|\baur\b|[,;]'
    parts = re.split(split_pattern, text, flags=re.IGNORECASE)
    
    # Common conversational fillers to clean up
    filler = r'\b(i need to|i want to|please|just|ok|okay|da|na|yaar|bhai|re|uh|ah)\b'
    cleaned = []
    
    for p in parts:
        p = re.sub(filler, '', p, flags=re.IGNORECASE).strip(" .,")
        if len(p) > 2:
            cleaned.append(p.capitalize())
            
    return cleaned


def parse_intent(transcript: str) -> Dict[str, Any]:
    """Fallback rule-based intent parser that extracts actions and params from speech.
    
    Args:
        transcript: The text transcription of the user's speech.
        
    Returns:
        A dictionary containing "action", "tasks", and "positions" keys.
    """
    t = transcript.lower()

    # Clear Action
    if _contains(t, CLEAR_WORDS) and _contains(t, ["all", "ellam", "sab", "poora", "everything"]):
        return {
            "action": "clear",
            "tasks": [],
            "positions": []
        }

    # Done Action
    if _contains(t, DONE_WORDS):
        nums = _extract_numbers(t)
        return {
            "action": "done",
            "tasks": [],
            "positions": nums
        }

    # Delete Action
    if _contains(t, DELETE_WORDS):
        nums = _extract_numbers(t)
        return {
            "action": "delete",
            "tasks": [],
            "positions": nums
        }

    # Show Action
    if _contains(t, SHOW_WORDS):
        return {
            "action": "show",
            "tasks": [],
            "positions": []
        }

    # Add Action (Explicit keywords)
    if _contains(t, ADD_WORDS):
        tasks = _extract_tasks(transcript)
        return {
            "action": "add",
            "tasks": tasks,
            "positions": []
        }

    # Implicit Add Fallback (if tasks are found but no explicit keyword)
    tasks = _extract_tasks(transcript)
    if tasks:
        return {
            "action": "add",
            "tasks": tasks,
            "positions": []
        }

    # Default Fallback
    return {
        "action": "unknown",
        "tasks": [],
        "positions": []
    }