"""
LiveKit adapter that hooks into transcription events and applies interruption filtering.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Any
from datetime import datetime

from ..interruption_filter import InterruptionFilter, Action, Segment, InterruptionFilterConfig


# Configure structured logger
logger = logging.getLogger(__name__)


class StructuredLogger:
    """Simple structured logger that outputs JSON logs."""
    
    def __init__(self, log_level: str = "info"):
        self.log_level = log_level.upper()
        self.logger = logging.getLogger("interruption_filter")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, self.log_level, logging.INFO))
    
    def info(self, event_type: str, **kwargs):
        """Log an info-level event as JSON."""
        log_entry = {
            "level": "INFO",
            "event": event_type,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))


class LiveKitInterruptionAdapter:
    """
    Adapter that integrates interruption filtering with LiveKit Agents.
    
    This adapter:
    - Subscribes to LiveKit transcription events
    - Applies interruption filtering logic
    - Controls agent TTS based on filter decisions
    - Does NOT modify LiveKit SDK core
    """
    
    def __init__(
        self,
        filter_instance: Optional[InterruptionFilter] = None,
        config: Optional[InterruptionFilterConfig] = None,
        agent_control: Optional[Any] = None
    ):
        """
        Initialize the adapter.
        
        Args:
            filter_instance: Pre-configured InterruptionFilter instance (optional)
            config: Configuration for creating filter (optional)
            agent_control: Agent control object with stop_tts() method (optional)
        """
        if filter_instance:
            self.filter = filter_instance
        else:
            self.filter = InterruptionFilter(config)
        
        self.agent_control = agent_control
        self._agent_speaking = False
        self._speaking_lock = asyncio.Lock()
        
        # Set up structured logger
        log_level = self.filter.config.log_level
        structured_logger = StructuredLogger(log_level)
        self.filter.set_logger(structured_logger)
        
        # Callback for when user speech should be registered
        self.on_user_speech_callback: Optional[Callable] = None
    
    def set_agent_speaking(self, speaking: bool) -> None:
        """
        Update the agent speaking state.
        Call this when agent starts/stops TTS.
        
        Args:
            speaking: True if agent is currently speaking
        """
        self._agent_speaking = speaking
    
    async def set_agent_speaking_async(self, speaking: bool) -> None:
        """Async version of set_agent_speaking."""
        async with self._speaking_lock:
            self._agent_speaking = speaking
    
    def is_agent_speaking(self) -> bool:
        """Check if agent is currently speaking."""
        return self._agent_speaking
    
    def set_user_speech_callback(self, callback: Callable) -> None:
        """
        Set callback to be invoked when user speech should be registered.
        
        Args:
            callback: Async function(session_id, segment) -> None
        """
        self.on_user_speech_callback = callback
    
    async def on_transcription_result(
        self,
        session_id: str,
        text: str,
        confidence: float,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
        timestamp_start: Optional[float] = None,
        timestamp_end: Optional[float] = None
    ) -> None:
        """
        Handle a transcription result from LiveKit.
        
        This is the main entry point that should be called from LiveKit's
        transcription event handler.
        
        Args:
            session_id: Session identifier
            text: Transcribed text
            confidence: Confidence score (0.0 to 1.0)
            language: Language code (optional)
            user_id: User identifier (optional)
            timestamp_start: Start timestamp (optional)
            timestamp_end: End timestamp (optional)
        """
        # Create segment with current agent speaking state
        segment = Segment(
            text=text,
            confidence=confidence,
            agent_speaking=self._agent_speaking,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            language=language,
            session_id=session_id,
            user_id=user_id
        )
        
        # Get action from filter
        action = await self.filter.handle(segment)
        
        # Execute action
        if action == Action.IGNORE:
            # Do nothing - agent continues speaking
            return
        
        elif action == Action.STOP_AGENT:
            # Stop agent TTS immediately
            await self._stop_agent_tts(session_id)
            # Also register as user speech (user interrupted with command)
            if self.on_user_speech_callback:
                await self.on_user_speech_callback(session_id, segment)
        
        elif action == Action.REGISTER_SPEECH:
            # Register as normal user speech
            if self.on_user_speech_callback:
                await self.on_user_speech_callback(session_id, segment)
    
    async def _stop_agent_tts(self, session_id: str) -> None:
        """
        Stop agent TTS using the agent control API.
        
        Args:
            session_id: Session identifier
        """
        if self.agent_control:
            # Try to call stop_tts method if available
            # Check if method exists and is callable (not just a MagicMock default or None)
            stop_tts = getattr(self.agent_control, 'stop_tts', None)
            stop_method = getattr(self.agent_control, 'stop', None)
            pause_tts = getattr(self.agent_control, 'pause_tts', None)
            
            if stop_tts is not None and callable(stop_tts):
                try:
                    result = stop_tts(session_id)
                    if asyncio.iscoroutine(result):
                        await result
                    return
                except Exception as e:
                    logger.error(f"Error stopping TTS: {e}")
            
            if stop_method is not None and callable(stop_method):
                try:
                    result = stop_method(session_id)
                    if asyncio.iscoroutine(result):
                        await result
                    return
                except Exception as e:
                    logger.error(f"Error stopping agent: {e}")
            
            if pause_tts is not None and callable(pause_tts):
                try:
                    result = pause_tts(session_id)
                    if asyncio.iscoroutine(result):
                        await result
                    return
                except Exception as e:
                    logger.error(f"Error pausing TTS: {e}")
        else:
            # Log warning if no agent control available
            logger.warning(f"No agent control available to stop TTS for session {session_id}")


def create_adapter_from_env(agent_control: Optional[Any] = None) -> LiveKitInterruptionAdapter:
    """
    Create an adapter instance using environment variable configuration.
    
    Args:
        agent_control: Optional agent control object
        
    Returns:
        Configured LiveKitInterruptionAdapter instance
    """
    from ..interruption_filter.config import load_config_from_env
    config = load_config_from_env()
    return LiveKitInterruptionAdapter(config=config, agent_control=agent_control)

