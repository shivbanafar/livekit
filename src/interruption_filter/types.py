"""
Type definitions for the interruption filter module.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class Action(Enum):
    """Action to take based on transcription event analysis."""
    IGNORE = "IGNORE"  # Ignore the interruption, agent continues speaking
    REGISTER_SPEECH = "REGISTER_SPEECH"  # Register as normal user speech
    STOP_AGENT = "STOP_AGENT"  # Stop agent TTS immediately


@dataclass
class Segment:
    """Represents a transcription segment from ASR."""
    text: str
    confidence: float  # 0.0 to 1.0
    agent_speaking: bool
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    language: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None

