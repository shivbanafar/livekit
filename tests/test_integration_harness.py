"""
Integration test harness with mock LiveKit agent.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.interruption_filter import Segment, Action
from src.integration import LiveKitInterruptionAdapter


class MockAgentControl:
    """Mock agent control for testing."""
    
    def __init__(self):
        self.stop_tts_called = False
        self.stop_tts_session_id = None
        self.stop_called = False
        self.pause_tts_called = False
    
    async def stop_tts(self, session_id: str):
        """Mock stop_tts method."""
        self.stop_tts_called = True
        self.stop_tts_session_id = session_id
    
    async def stop(self, session_id: str):
        """Mock stop method."""
        self.stop_called = True
    
    async def pause_tts(self, session_id: str):
        """Mock pause_tts method."""
        self.pause_tts_called = True


@pytest.fixture
def mock_agent_control():
    """Create mock agent control."""
    return MockAgentControl()


@pytest.fixture
def adapter(mock_agent_control):
    """Create adapter with mock agent control."""
    adapter = LiveKitInterruptionAdapter(agent_control=mock_agent_control)
    return adapter


@pytest.mark.asyncio
async def test_filler_ignored_agent_continues(adapter, mock_agent_control):
    """Test that filler words are ignored and agent continues speaking."""
    adapter.set_agent_speaking(True)
    
    user_speech_called = False
    
    async def on_user_speech(session_id, segment):
        nonlocal user_speech_called
        user_speech_called = True
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # Send filler word
    await adapter.on_transcription_result(
        session_id="test_session",
        text="uh",
        confidence=0.9
    )
    
    # Agent should continue (no stop called, no user speech registered)
    assert not mock_agent_control.stop_tts_called
    assert not user_speech_called


@pytest.mark.asyncio
async def test_command_stops_agent(adapter, mock_agent_control):
    """Test that commands stop the agent immediately."""
    adapter.set_agent_speaking(True)
    
    user_speech_called = False
    captured_segment = None
    
    async def on_user_speech(session_id, segment):
        nonlocal user_speech_called, captured_segment
        user_speech_called = True
        captured_segment = segment
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # Send command
    await adapter.on_transcription_result(
        session_id="test_session",
        text="stop",
        confidence=0.9
    )
    
    # Agent should be stopped
    assert mock_agent_control.stop_tts_called
    assert mock_agent_control.stop_tts_session_id == "test_session"
    # User speech should also be registered
    assert user_speech_called
    assert captured_segment.text == "stop"


@pytest.mark.asyncio
async def test_mixed_filler_command_stops_agent(adapter, mock_agent_control):
    """Test that mixed filler + command stops agent."""
    adapter.set_agent_speaking(True)
    
    await adapter.on_transcription_result(
        session_id="test_session",
        text="umm okay stop",
        confidence=0.9
    )
    
    assert mock_agent_control.stop_tts_called


@pytest.mark.asyncio
async def test_filler_while_agent_quiet_registers(adapter, mock_agent_control):
    """Test that filler words are registered when agent is quiet."""
    adapter.set_agent_speaking(False)
    
    user_speech_called = False
    captured_segment = None
    
    async def on_user_speech(session_id, segment):
        nonlocal user_speech_called, captured_segment
        user_speech_called = True
        captured_segment = segment
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # Send filler word while agent quiet
    await adapter.on_transcription_result(
        session_id="test_session",
        text="umm",
        confidence=0.9
    )
    
    # Should register as user speech
    assert user_speech_called
    assert captured_segment.text == "umm"
    # Should not stop agent (agent already quiet)
    assert not mock_agent_control.stop_tts_called


@pytest.mark.asyncio
async def test_low_confidence_ignored_when_agent_speaking(adapter, mock_agent_control):
    """Test that low confidence segments are ignored when agent is speaking."""
    adapter.set_agent_speaking(True)
    
    user_speech_called = False
    
    async def on_user_speech(session_id, segment):
        nonlocal user_speech_called
        user_speech_called = True
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # Send low confidence segment
    await adapter.on_transcription_result(
        session_id="test_session",
        text="something",
        confidence=0.2  # Below threshold
    )
    
    # Should be ignored
    assert not user_speech_called
    assert not mock_agent_control.stop_tts_called


@pytest.mark.asyncio
async def test_agent_speaking_state_tracking(adapter):
    """Test that agent speaking state is tracked correctly."""
    assert not adapter.is_agent_speaking()
    
    adapter.set_agent_speaking(True)
    assert adapter.is_agent_speaking()
    
    adapter.set_agent_speaking(False)
    assert not adapter.is_agent_speaking()


@pytest.mark.asyncio
async def test_sequence_simulation(adapter, mock_agent_control):
    """
    Simulate a realistic sequence:
    1. Agent starts speaking
    2. User says "uh" -> agent continues
    3. User says "umm okay stop" -> agent stops
    4. Agent quiet, user says "umm" -> registers
    """
    user_speech_events = []
    
    async def on_user_speech(session_id, segment):
        user_speech_events.append((session_id, segment.text))
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # 1. Agent starts speaking
    adapter.set_agent_speaking(True)
    
    # 2. User says "uh" -> should be ignored
    await adapter.on_transcription_result(
        session_id="session1",
        text="uh",
        confidence=0.9
    )
    assert not mock_agent_control.stop_tts_called
    assert len(user_speech_events) == 0
    
    # 3. User says "umm okay stop" -> should stop agent
    await adapter.on_transcription_result(
        session_id="session1",
        text="umm okay stop",
        confidence=0.9
    )
    assert mock_agent_control.stop_tts_called
    assert len(user_speech_events) == 1
    assert user_speech_events[0][1] == "umm okay stop"
    
    # Reset for next test
    mock_agent_control.stop_tts_called = False
    user_speech_events.clear()
    
    # 4. Agent quiet, user says "umm" -> should register
    adapter.set_agent_speaking(False)
    await adapter.on_transcription_result(
        session_id="session1",
        text="umm",
        confidence=0.9
    )
    assert not mock_agent_control.stop_tts_called
    assert len(user_speech_events) == 1
    assert user_speech_events[0][1] == "umm"


@pytest.mark.asyncio
async def test_agent_control_fallback_methods():
    """Test that adapter tries different methods if stop_tts doesn't exist."""
    # Test with agent that has stop() method (but not stop_tts)
    mock_control_stop = MagicMock(spec=[])  # Empty spec so no default attributes
    mock_control_stop.stop = AsyncMock()
    # Explicitly set stop_tts to None to ensure it's not used
    mock_control_stop.stop_tts = None
    
    adapter = LiveKitInterruptionAdapter(agent_control=mock_control_stop)
    adapter.set_agent_speaking(True)
    
    await adapter.on_transcription_result(
        session_id="test",
        text="stop",
        confidence=0.9
    )
    
    mock_control_stop.stop.assert_called_once_with("test")
    
    # Test with agent that has pause_tts() method (but not stop_tts or stop)
    mock_control_pause = MagicMock(spec=[])
    mock_control_pause.pause_tts = AsyncMock()
    mock_control_pause.stop_tts = None
    mock_control_pause.stop = None
    
    adapter2 = LiveKitInterruptionAdapter(agent_control=mock_control_pause)
    adapter2.set_agent_speaking(True)
    
    await adapter2.on_transcription_result(
        session_id="test",
        text="stop",
        confidence=0.9
    )
    
    mock_control_pause.pause_tts.assert_called_once_with("test")

