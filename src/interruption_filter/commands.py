"""
Command detection logic for identifying valid interruption commands.
"""

from typing import List, Set
from .tokenizer import tokenize, contains_any_token


# Default command words/phrases that should stop the agent
DEFAULT_COMMAND_WORDS = [
    "stop",
    "wait",
    "hold",
    "pause",
    "no",
    "not that",
    "that's enough",
    "don't",
    "don't do that",
    "cancel",
    "abort",
    "enough",
    "back off",
    "backoff",
    "halt",
    "freeze",
    "quit",
    "end",
    "cease",
]


def contains_valid_command(text: str, command_words: Set[str]) -> bool:
    """
    Check if text contains any valid command phrase.
    
    Args:
        text: Transcription text to analyze
        command_words: Set of command words/phrases to detect
        
    Returns:
        True if a valid command is detected
    """
    if not text or not command_words:
        return False
    
    tokens = tokenize(text)
    return contains_any_token(tokens, command_words)


def get_default_commands() -> List[str]:
    """Get the default list of command words/phrases."""
    return DEFAULT_COMMAND_WORDS.copy()

