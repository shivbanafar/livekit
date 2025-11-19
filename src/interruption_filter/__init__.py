"""
Interruption Filter Module for LiveKit Agents

This module provides filtering logic to ignore filler words during agent speech
while allowing real interruptions to stop the agent immediately.
"""

from .types import Action, Segment
from .filter import InterruptionFilter
from .config import InterruptionFilterConfig

__all__ = ['Action', 'Segment', 'InterruptionFilter', 'InterruptionFilterConfig']

