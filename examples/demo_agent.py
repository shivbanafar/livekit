"""
Demo script showing how to integrate interruption filter with a LiveKit agent.

This is a simplified example demonstrating the integration pattern.
"""

import asyncio
import os
from src.integration import LiveKitInterruptionAdapter, DynamicUpdateServer
from src.interruption_filter.config import load_config_from_env


class DemoAgentControl:
    """Demo agent control that simulates TTS control."""
    
    def __init__(self):
        self.is_speaking = False
    
    async def start_tts(self, text: str):
        """Simulate starting TTS."""
        print(f"[Agent] Starting TTS: {text[:50]}...")
        self.is_speaking = True
    
    async def stop_tts(self, session_id: str):
        """Simulate stopping TTS."""
        print(f"[Agent] Stopping TTS for session {session_id}")
        self.is_speaking = False
    
    async def on_user_speech(self, session_id: str, text: str):
        """Handle user speech."""
        print(f"[Agent] Received user speech: {text}")


async def simulate_transcription_events(adapter: LiveKitInterruptionAdapter):
    """Simulate a sequence of transcription events."""
    session_id = "demo_session"
    
    print("\n=== Demo: Interruption Filter ===\n")
    
    # 1. Agent starts speaking
    print("1. Agent begins TTS...")
    adapter.set_agent_speaking(True)
    await asyncio.sleep(0.1)
    
    # 2. User says "uh" -> should be ignored
    print("\n2. User: 'uh'")
    await adapter.on_transcription_result(
        session_id=session_id,
        text="uh",
        confidence=0.9
    )
    print("   Expected: Agent continues (ignored)")
    await asyncio.sleep(0.1)
    
    # 3. User says "umm okay stop" -> should stop agent
    print("\n3. User: 'umm okay stop'")
    await adapter.on_transcription_result(
        session_id=session_id,
        text="umm okay stop",
        confidence=0.9
    )
    print("   Expected: Agent stops (command detected)")
    adapter.set_agent_speaking(False)
    await asyncio.sleep(0.1)
    
    # 4. Agent quiet, user says "umm" -> should register
    print("\n4. Agent quiet, User: 'umm'")
    await adapter.on_transcription_result(
        session_id=session_id,
        text="umm",
        confidence=0.9
    )
    print("   Expected: Registered as user speech")
    await asyncio.sleep(0.1)
    
    # 5. Low confidence background noise while agent speaking
    print("\n5. Agent speaking, User: low confidence 'hmm yeah'")
    adapter.set_agent_speaking(True)
    await adapter.on_transcription_result(
        session_id=session_id,
        text="hmm yeah",
        confidence=0.2  # Below threshold
    )
    print("   Expected: Ignored (low confidence)")
    
    print("\n=== Demo Complete ===\n")


async def main():
    """Main demo function."""
    # Load configuration from environment
    config = load_config_from_env()
    
    # Create demo agent control
    agent_control = DemoAgentControl()
    
    # Create adapter
    adapter = LiveKitInterruptionAdapter(config=config, agent_control=agent_control)
    
    # Set up user speech callback
    async def on_user_speech(session_id, segment):
        await agent_control.on_user_speech(session_id, segment.text)
    
    adapter.set_user_speech_callback(on_user_speech)
    
    # Start dynamic update server if enabled
    update_server = None
    if config.dynamic_update_enabled:
        update_server = DynamicUpdateServer(
            filter_instance=adapter.filter,
            port=config.dynamic_update_port,
            token=config.dynamic_update_token
        )
        await update_server.start()
        print(f"Dynamic update server started on port {config.dynamic_update_port}")
    
    try:
        # Run demo
        await simulate_transcription_events(adapter)
        
        # Keep server running if enabled
        if update_server:
            print("Dynamic update server running. Press Ctrl+C to stop.")
            await asyncio.sleep(3600)  # Run for 1 hour
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if update_server:
            await update_server.stop()


if __name__ == "__main__":
    asyncio.run(main())

