"""
Core interruption filter logic implementing the main algorithm.
"""

import asyncio
import time
from typing import Set, Optional, Dict, Any
from datetime import datetime, timezone

from .types import Action, Segment
from .config import InterruptionFilterConfig
from .tokenizer import normalize_text, tokenize, is_filler_only
from .commands import contains_valid_command

# Optional metrics import
try:
    import sys
    import os
    # Add project root to path for metrics import
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from metrics.prometheus_exporter import record_action, record_latency
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


class InterruptionFilter:
    """
    Filters transcription events to ignore filler words during agent speech
    while allowing real interruptions to stop the agent immediately.
    """
    
    def __init__(self, config: Optional[InterruptionFilterConfig] = None):
        """
        Initialize the interruption filter.
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        if config is None:
            from .config import load_config_from_env
            config = load_config_from_env()
        
        self.config = config
        self._ignored_words = config.ignored_words.copy()
        self._command_words = config.command_words.copy()
        self._lock = asyncio.Lock()
        self._logger = None  # Will be set by integration layer
        
    async def update_ignored_words(self, words: list) -> None:
        """
        Dynamically update the ignored words list (thread-safe).
        
        Args:
            words: List of new ignored words to add/replace
        """
        async with self._lock:
            self._ignored_words = {w.lower().strip() for w in words if w}
    
    async def update_command_words(self, words: list) -> None:
        """
        Dynamically update the command words list (thread-safe).
        
        Args:
            words: List of new command words to add/replace
        """
        async with self._lock:
            self._command_words = {w.lower().strip() for w in words if w}
    
    def set_logger(self, logger):
        """Set the logger instance for structured logging."""
        self._logger = logger
    
    async def handle(self, segment: Segment) -> Action:
        """
        Process a transcription segment and return the action to take.
        
        This implements the core algorithm:
        1. Low confidence background murmur when agent speaks -> IGNORE
        2. If segment contains any strong command -> STOP_AGENT
        3. If agent is speaking:
           - Pure filler -> IGNORE
           - Mixed filler + command -> STOP_AGENT
           - Otherwise -> REGISTER_SPEECH
        4. If agent quiet -> REGISTER_SPEECH (always)
        
        Args:
            segment: Transcription segment to analyze
            
        Returns:
            Action enum indicating what to do
        """
        start_time = time.perf_counter()
        
        # Normalize and tokenize
        normalized_text = normalize_text(segment.text)
        tokens = tokenize(normalized_text)
        
        # Get current config (thread-safe copy)
        async with self._lock:
            ignored_words = self._ignored_words.copy()
            command_words = self._command_words.copy()
            confidence_threshold = self.config.confidence_threshold
        
        processing_latency_ms = (time.perf_counter() - start_time) * 1000
        processing_latency_sec = processing_latency_ms / 1000.0
        
        # 1) Low confidence background murmur when agent speaks -> ignore
        if segment.agent_speaking and segment.confidence < confidence_threshold:
            action = Action.IGNORE
            log_data = self._create_log_data(
                segment=segment,
                action=action,
                category="low_confidence_ignored",
                matched_ignored=[],
                matched_commands=[],
                processing_latency_ms=processing_latency_ms
            )
            self._log(log_data)
            if METRICS_AVAILABLE:
                record_action(action.value, segment.language or "unknown", segment.session_id or "unknown")
                record_latency(processing_latency_sec)
            return action
        
        # 2) Check if segment contains any valid command
        has_command = contains_valid_command(normalized_text, command_words)
        matched_commands = []
        if has_command:
            # Find which commands matched
            for cmd in command_words:
                if cmd.lower() in normalized_text:
                    matched_commands.append(cmd)
        
        # 3) If agent is speaking
        if segment.agent_speaking:
            # Check if it's pure filler
            is_filler = is_filler_only(tokens, ignored_words)
            matched_ignored = []
            if is_filler:
                # Find which ignored words matched
                for word in ignored_words:
                    if word in tokens or word in normalized_text:
                        matched_ignored.append(word)
            
            # If contains command -> stop agent (even if mixed with filler)
            if has_command:
                action = Action.STOP_AGENT
                category = "mixed_interruption" if is_filler else "valid_interruption"
                log_data = self._create_log_data(
                    segment=segment,
                    action=action,
                    category=category,
                    matched_ignored=matched_ignored if is_filler else [],
                    matched_commands=matched_commands,
                    processing_latency_ms=processing_latency_ms
                )
                self._log(log_data)
                if METRICS_AVAILABLE:
                    record_action(action.value, segment.language or "unknown", segment.session_id or "unknown")
                    record_latency(processing_latency_sec)
                return action
            
            # If pure filler -> ignore
            if is_filler:
                action = Action.IGNORE
                log_data = self._create_log_data(
                    segment=segment,
                    action=action,
                    category="ignored_interruption",
                    matched_ignored=matched_ignored,
                    matched_commands=[],
                    processing_latency_ms=processing_latency_ms
                )
                self._log(log_data)
                if METRICS_AVAILABLE:
                    record_action(action.value, segment.language or "unknown", segment.session_id or "unknown")
                    record_latency(processing_latency_sec)
                return action
            
            # Otherwise -> register as speech
            action = Action.REGISTER_SPEECH
            log_data = self._create_log_data(
                segment=segment,
                action=action,
                category="registered_interruption",
                matched_ignored=[],
                matched_commands=[],
                processing_latency_ms=processing_latency_ms
            )
            self._log(log_data)
            if METRICS_AVAILABLE:
                record_action(action.value, segment.language or "unknown", segment.session_id or "unknown")
                record_latency(processing_latency_sec)
            return action
        
        # 4) Agent quiet: treat everything as normal user speech
        action = Action.REGISTER_SPEECH
        log_data = self._create_log_data(
            segment=segment,
            action=action,
            category="registered_while_quiet",
            matched_ignored=[],
            matched_commands=[],
            processing_latency_ms=processing_latency_ms
        )
        self._log(log_data)
        if METRICS_AVAILABLE:
            record_action(action.value, segment.language or "unknown", segment.session_id or "unknown")
            record_latency(processing_latency_sec)
        return action
    
    def _create_log_data(
        self,
        segment: Segment,
        action: Action,
        category: str,
        matched_ignored: list,
        matched_commands: list,
        processing_latency_ms: float
    ) -> Dict[str, Any]:
        """Create structured log data dictionary."""
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": segment.session_id or "unknown",
            "user_id": segment.user_id or "unknown",
            "action": action.value,
            "category": category,
            "text": segment.text,
            "confidence": segment.confidence,
            "agent_speaking": segment.agent_speaking,
            "matched_ignored": matched_ignored,
            "matched_commands": matched_commands,
            "processing_latency_ms": round(processing_latency_ms, 2),
            "language": segment.language or "unknown",
        }
    
    def _log(self, log_data: Dict[str, Any]) -> None:
        """Log the event using the configured logger."""
        if self._logger:
            self._logger.info("interruption_filter", **log_data)
        else:
            # Fallback to print if no logger configured
            import json
            print(json.dumps(log_data))

