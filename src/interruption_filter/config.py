"""
Configuration loader for interruption filter.
"""

import os
from typing import List, Set, Optional
from dataclasses import dataclass


@dataclass
class InterruptionFilterConfig:
    """Configuration for InterruptionFilter."""
    ignored_words: Set[str]
    command_words: Set[str]
    confidence_threshold: float
    dynamic_update_enabled: bool = False
    dynamic_update_port: int = 9090
    dynamic_update_token: Optional[str] = None
    log_level: str = "info"
    
    def __post_init__(self):
        """Normalize sets to lowercase."""
        self.ignored_words = {w.lower().strip() for w in self.ignored_words if w}
        self.command_words = {w.lower().strip() for w in self.command_words if w}


def load_config_from_env() -> InterruptionFilterConfig:
    """
    Load configuration from environment variables.
    
    Environment variables:
        IGNORED_WORDS: Comma-separated list of filler words (default: "uh,umm,hmm,haan")
        COMMAND_WORDS: Comma-separated list of command words (default: built-in list)
        CONFIDENCE_THRESHOLD: Float threshold for low-confidence filtering (default: 0.45)
        DYNAMIC_UPDATE_ENABLED: Enable dynamic update endpoint (default: false)
        DYNAMIC_UPDATE_PORT: Port for dynamic update server (default: 9090)
        DYNAMIC_UPDATE_TOKEN: Token for protecting update endpoint (optional)
        LOG_LEVEL: Logging level (default: info)
    
    Returns:
        InterruptionFilterConfig instance
    """
    # Load ignored words
    ignored_words_str = os.getenv("IGNORED_WORDS", "uh,umm,hmm,haan")
    ignored_words = [w.strip() for w in ignored_words_str.split(",") if w.strip()]
    
    # Load command words (use default if not specified)
    command_words_str = os.getenv("COMMAND_WORDS", "")
    if command_words_str:
        command_words = [w.strip() for w in command_words_str.split(",") if w.strip()]
    else:
        # Use default commands
        from .commands import get_default_commands
        command_words = get_default_commands()
    
    # Load confidence threshold
    confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
    
    # Load dynamic update settings
    dynamic_update_enabled = os.getenv("DYNAMIC_UPDATE_ENABLED", "false").lower() == "true"
    dynamic_update_port = int(os.getenv("DYNAMIC_UPDATE_PORT", "9090"))
    dynamic_update_token = os.getenv("DYNAMIC_UPDATE_TOKEN")
    
    # Load log level
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    return InterruptionFilterConfig(
        ignored_words=set(ignored_words),
        command_words=set(command_words),
        confidence_threshold=confidence_threshold,
        dynamic_update_enabled=dynamic_update_enabled,
        dynamic_update_port=dynamic_update_port,
        dynamic_update_token=dynamic_update_token,
        log_level=log_level,
    )

