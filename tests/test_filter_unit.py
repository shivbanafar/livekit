"""
Unit tests for InterruptionFilter covering all spec scenarios.
"""

import pytest
import asyncio
from src.interruption_filter import (
    InterruptionFilter,
    Action,
    Segment,
    InterruptionFilterConfig
)


@pytest.fixture
def default_config():
    """Create default test configuration."""
    return InterruptionFilterConfig(
        ignored_words={'uh', 'umm', 'hmm', 'haan'},
        command_words={'stop', 'wait', 'hold', 'pause', 'no', 'not that', "that's enough", "don't"},
        confidence_threshold=0.45
    )


@pytest.fixture
def filter_instance(default_config):
    """Create InterruptionFilter instance for testing."""
    return InterruptionFilter(config=default_config)


@pytest.mark.asyncio
async def test_filler_while_agent_speaking_ignored(filter_instance):
    """User filler while agent speaks → text "uh" → IGNORE."""
    segment = Segment(
        text="uh",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_real_interruption_while_agent_speaks_stops(filter_instance):
    """User real interruption while agent speaks → "wait one second" → STOP_AGENT."""
    segment = Segment(
        text="wait one second",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_filler_while_agent_quiet_registers(filter_instance):
    """User filler while agent quiet → "umm" with agent_speaking=False → REGISTER_SPEECH."""
    segment = Segment(
        text="umm",
        confidence=0.9,
        agent_speaking=False,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.REGISTER_SPEECH


@pytest.mark.asyncio
async def test_mixed_filler_command_stops_agent(filter_instance):
    """Mixed filler + command "umm okay stop" with agent speaking → STOP_AGENT."""
    segment = Segment(
        text="umm okay stop",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_low_confidence_background_murmur_ignored(filter_instance):
    """Background murmur low confidence "hmm yeah" with confidence 0.2 (< threshold) and agent speaking → IGNORE."""
    segment = Segment(
        text="hmm yeah",
        confidence=0.2,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_noisy_mixed_case_stops_agent(filter_instance):
    """Slightly noisy mixed case: "uh stop now" with confidence high → STOP_AGENT."""
    segment = Segment(
        text="uh stop now",
        confidence=0.85,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_multi_token_filler_ignored(filter_instance):
    """Multi-token filler "umm umm" should be normalized and ignored."""
    segment = Segment(
        text="umm umm",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_case_insensitive_filler(filter_instance):
    """Case sensitivity checks: "UMM" -> ignore."""
    segment = Segment(
        text="UMM",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_non_english_filler_words():
    """Non-English filler words included in the list."""
    config = InterruptionFilterConfig(
        ignored_words={'uh', 'umm', 'hmm', 'haan', 'अच्छा', 'हाँ'},
        command_words={'stop', 'wait'},
        confidence_threshold=0.45
    )
    filter_instance = InterruptionFilter(config=config)
    
    segment = Segment(
        text="haan",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_phrase_command_detection(filter_instance):
    """Test phrase command detection like "not that"."""
    segment = Segment(
        text="umm not that one",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_high_confidence_non_filler_registers(filter_instance):
    """High confidence non-filler text while agent speaking should register."""
    segment = Segment(
        text="I need help",
        confidence=0.95,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.REGISTER_SPEECH


@pytest.mark.asyncio
async def test_low_confidence_when_agent_quiet_registers(filter_instance):
    """Low confidence when agent is quiet should still register (not ignore)."""
    segment = Segment(
        text="something",
        confidence=0.2,
        agent_speaking=False,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.REGISTER_SPEECH


@pytest.mark.asyncio
async def test_empty_text_handling(filter_instance):
    """Empty text should be handled gracefully."""
    segment = Segment(
        text="",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    # Empty text with agent speaking should be ignored
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_dynamic_update_ignored_words(filter_instance):
    """Test dynamic update of ignored words."""
    # Initially "test" should register
    segment = Segment(
        text="test",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.REGISTER_SPEECH
    
    # Update ignored words to include "test"
    await filter_instance.update_ignored_words(['uh', 'umm', 'hmm', 'haan', 'test'])
    
    # Now "test" should be ignored
    segment = Segment(
        text="test",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_dynamic_update_command_words(filter_instance):
    """Test dynamic update of command words."""
    # Initially "halt" should register (not in default commands)
    segment = Segment(
        text="halt",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.REGISTER_SPEECH
    
    # Update command words to include "halt"
    await filter_instance.update_command_words(['stop', 'wait', 'halt'])
    
    # Now "halt" should stop agent
    segment = Segment(
        text="halt",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_multiple_commands_in_text(filter_instance):
    """Test text with multiple commands."""
    segment = Segment(
        text="stop wait pause",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.STOP_AGENT


@pytest.mark.asyncio
async def test_punctuation_handling(filter_instance):
    """Test that punctuation is handled correctly."""
    segment = Segment(
        text="uh, umm...",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE


@pytest.mark.asyncio
async def test_whitespace_normalization(filter_instance):
    """Test that extra whitespace is normalized."""
    segment = Segment(
        text="  uh   umm  ",
        confidence=0.9,
        agent_speaking=True,
        session_id="test_session"
    )
    action = await filter_instance.handle(segment)
    assert action == Action.IGNORE

