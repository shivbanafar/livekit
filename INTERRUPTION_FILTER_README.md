# LiveKit Interruption Filter Extension

## Overview

This extension layer for LiveKit Agents filters out configured "filler" words (e.g., 'uh', 'umm', 'hmm', 'haan') when the agent is speaking, while still allowing real interruptions to stop the agent immediately. The implementation does **not** modify LiveKit's VAD core—it operates as a middleware layer on transcription events.

## What Changed

This implementation adds the following modules:

- **`src/interruption_filter/`** - Core filtering logic
  - `filter.py` - Main `InterruptionFilter` class implementing the core algorithm
  - `tokenizer.py` - Text normalization and tokenization utilities
  - `commands.py` - Command detection logic
  - `config.py` - Configuration loader from environment variables
  - `types.py` - Action enum and Segment dataclass

- **`src/integration/`** - LiveKit integration layer
  - `livekit_adapter.py` - Adapter that hooks into LiveKit transcription events
  - `dynamic_update_server.py` - Optional HTTP server for runtime configuration updates

- **`metrics/`** - Prometheus metrics exporter
  - `prometheus_exporter.py` - Metrics counters and histograms

- **`tests/`** - Comprehensive test suite
  - `test_filter_unit.py` - Unit tests covering all spec scenarios
  - `test_integration_harness.py` - Integration tests with mock LiveKit agent
  - `test_performance.py` - Performance benchmarks

- **`examples/`** - Demo and example code
  - `demo_agent.py` - Example integration demonstrating all scenarios

## What Works

All core behaviors from the specification are implemented and tested:

✅ **Filler word filtering**: Configured filler words are ignored when agent is speaking  
✅ **Command detection**: Real commands (stop, wait, etc.) stop the agent immediately  
✅ **Mixed interruptions**: Filler + command combinations correctly stop the agent  
✅ **Agent state awareness**: Different behavior when agent is speaking vs. quiet  
✅ **Low confidence filtering**: Background murmur below threshold is ignored  
✅ **Case insensitivity**: Normalization handles case variations  
✅ **Multi-language support**: Language-agnostic token matching  
✅ **Dynamic updates**: Runtime configuration updates via HTTP API (optional)  
✅ **Structured logging**: JSON logs with all required fields  
✅ **Prometheus metrics**: Counters and latency histograms  
✅ **Performance**: Median latency < 10ms (verified in tests)

### Tested Scenarios

All scenarios from the specification are covered by unit tests:

1. ✅ User filler while agent speaks → "uh" → IGNORE
2. ✅ User real interruption while agent speaks → "wait one second" → STOP_AGENT
3. ✅ User filler while agent quiet → "umm" → REGISTER_SPEECH
4. ✅ Mixed filler + command "umm okay stop" with agent speaking → STOP_AGENT
5. ✅ Background murmur low confidence "hmm yeah" with confidence 0.2 → IGNORE
6. ✅ Noisy mixed case: "uh stop now" with high confidence → STOP_AGENT
7. ✅ Multi-token filler "uhm uhm" → IGNORE
8. ✅ Case sensitivity: "UMM" → IGNORE
9. ✅ Non-English filler words (e.g., "haan") → IGNORE

## Known Issues

- **NLU integration**: Currently uses rule-based command detection. Optional NLU model integration is not implemented (can be added via `contains_valid_command` function).
- **Language detection**: Language is passed through from ASR but not used for language-specific filler lists (can be extended).
- **False positives**: Rare edge cases with ambiguous text may be misclassified (mitigated by confidence threshold).
- **Latency**: Measured on test machine; actual latency may vary with system load (target: <10ms median).
- **Edge cases**: Very rapid speech with overlapping filler words may occasionally be misclassified, though this is rare in practice.

## Steps to Test

### Prerequisites

- Python 3.7 or higher
- pip

### Installation

```bash
# Clone the repository
git clone <your-fork-url>
cd SALECODEAI
git checkout feature/livekit-interrupt-handler-<yourname>

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
IGNORED_WORDS=uh,umm,hmm,haan
CONFIDENCE_THRESHOLD=0.45
DYNAMIC_UPDATE_ENABLED=false
LOG_LEVEL=info
```

### Run Unit Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_filter_unit.py -v

# Run performance tests
pytest tests/test_performance.py -v
```

### Run Integration Tests

```bash
pytest tests/test_integration_harness.py -v
```

### Run Demo

```bash
# Set environment variables
export IGNORED_WORDS=uh,umm,hmm,haan
export CONFIDENCE_THRESHOLD=0.45

# Run demo
python examples/demo_agent.py
```

### Manual Testing Steps

1. **Test filler word ignoring**:
   - Start agent TTS
   - Send transcription: "uh" (confidence: 0.9, agent_speaking: true)
   - Expected: Agent continues, interruption ignored

2. **Test command detection**:
   - Start agent TTS
   - Send transcription: "wait one second" (confidence: 0.9, agent_speaking: true)
   - Expected: Agent stops immediately

3. **Test mixed interruption**:
   - Start agent TTS
   - Send transcription: "umm okay stop" (confidence: 0.9, agent_speaking: true)
   - Expected: Agent stops (command detected despite filler)

4. **Test filler while quiet**:
   - Agent quiet (agent_speaking: false)
   - Send transcription: "umm" (confidence: 0.9)
   - Expected: Registered as user speech

5. **Test low confidence**:
   - Start agent TTS
   - Send transcription: "hmm yeah" (confidence: 0.2, agent_speaking: true)
   - Expected: Ignored (below threshold)

## Environment Details

- **Python**: 3.7+
- **Key packages**:
  - `aiohttp>=3.9.0` - HTTP server for dynamic updates
  - `prometheus-client>=0.19.0` - Metrics export
  - `pytest>=7.4.0` - Testing framework
  - `pytest-asyncio>=0.21.0` - Async test support
  - `python-dotenv>=1.0.0` - Environment variable loading

### Dynamic Update Endpoint

If `DYNAMIC_UPDATE_ENABLED=true`, an HTTP server starts on port `DYNAMIC_UPDATE_PORT` (default: 9090).

**Endpoints**:
- `GET /ignored-words` - Get current ignored words list
- `POST /ignored-words` - Update ignored words (body: `{"ignored_words": ["uh", "umm"]}`)
- `GET /command-words` - Get current command words list
- `POST /command-words` - Update command words (body: `{"command_words": ["stop", "wait"]}`)
- `GET /health` - Health check

**Authentication**: If `DYNAMIC_UPDATE_TOKEN` is set, include it in `Authorization: Bearer <token>` header or `?token=<token>` query parameter.

**Example**:
```bash
# Update ignored words
curl -X POST http://localhost:9090/ignored-words \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"ignored_words": ["uh", "umm", "hmm", "haan", "new-filler"]}'
```

## How to Evaluate

### Correctness

Check test output for all passing scenarios:
```bash
pytest tests/ -v
```

All tests should pass. Review logs for:
- Correct action taken (IGNORE, REGISTER_SPEECH, STOP_AGENT)
- Proper categorization (ignored_interruption, valid_interruption, etc.)
- Matched words/commands logged correctly

### Performance

Run performance tests:
```bash
pytest tests/test_performance.py -v -s
```

Expected results:
- **Median latency**: < 10ms
- **P95 latency**: < 20ms
- **Throughput**: > 1000 events/second

### Logs

Example log output (JSON format):

```json
{
  "level": "INFO",
  "event": "interruption_filter",
  "ts": "2025-01-18T12:34:56.789Z",
  "session_id": "abc123",
  "user_id": "user1",
  "action": "IGNORED",
  "category": "ignored_interruption",
  "text": "uh",
  "confidence": 0.78,
  "agent_speaking": true,
  "matched_ignored": ["uh"],
  "matched_commands": [],
  "processing_latency_ms": 3.2,
  "language": "en"
}
```

### Metrics

If Prometheus is configured, metrics are available at `/metrics` endpoint:
- `interrupt_ignored_total` - Counter of ignored interruptions
- `interrupt_stopped_total` - Counter of interruptions that stopped agent
- `interrupt_registered_total` - Counter of registered speech
- `interruption_filter_processing_latency_seconds` - Processing latency histogram

## Integration with LiveKit Agent

### Basic Integration

```python
from src.integration import LiveKitInterruptionAdapter
from src.interruption_filter.config import load_config_from_env

# Load configuration
config = load_config_from_env()

# Create adapter (pass your agent control object)
adapter = LiveKitInterruptionAdapter(config=config, agent_control=your_agent_control)

# Set agent speaking state when TTS starts/stops
adapter.set_agent_speaking(True)  # When agent starts speaking
adapter.set_agent_speaking(False)  # When agent stops

# Set callback for user speech
async def on_user_speech(session_id, segment):
    # Handle user speech in your agent
    await your_agent.handle_user_input(session_id, segment.text)

adapter.set_user_speech_callback(on_user_speech)

# In your LiveKit transcription handler:
async def on_transcription(session_id, text, confidence, **kwargs):
    await adapter.on_transcription_result(
        session_id=session_id,
        text=text,
        confidence=confidence,
        **kwargs
    )
```

### Agent Control Interface

Your agent control object should implement one of:
- `async def stop_tts(session_id: str)` (preferred)
- `async def stop(session_id: str)`
- `async def pause_tts(session_id: str)`

The adapter will try these methods in order.

## Architecture

### Core Algorithm

1. **Low confidence check**: If agent speaking and confidence < threshold → IGNORE
2. **Command detection**: If segment contains any command → STOP_AGENT
3. **Agent speaking**:
   - Pure filler → IGNORE
   - Mixed filler + command → STOP_AGENT
   - Otherwise → REGISTER_SPEECH
4. **Agent quiet**: Always → REGISTER_SPEECH

### Design Principles

- **No LiveKit SDK modifications**: All logic is in extension layer
- **Thread-safe**: Uses asyncio.Lock for dynamic updates
- **Minimal latency**: Optimized for <10ms processing time
- **Configurable**: Environment variables and runtime updates
- **Observable**: Structured logs and Prometheus metrics

## Example Logs

### Scenario 1: Filler Ignored
```json
{"level":"INFO","event":"interruption_filter","ts":"2025-01-18T12:34:56.789Z","session_id":"abc123","action":"IGNORE","category":"ignored_interruption","text":"uh","confidence":0.9,"agent_speaking":true,"matched_ignored":["uh"],"processing_latency_ms":2.1}
```

### Scenario 2: Command Stops Agent
```json
{"level":"INFO","event":"interruption_filter","ts":"2025-01-18T12:34:57.123Z","session_id":"abc123","action":"STOP_AGENT","category":"valid_interruption","text":"wait one second","confidence":0.9,"agent_speaking":true,"matched_commands":["wait"],"processing_latency_ms":2.5}
```

### Scenario 3: Mixed Interruption
```json
{"level":"INFO","event":"interruption_filter","ts":"2025-01-18T12:34:57.456Z","session_id":"abc123","action":"STOP_AGENT","category":"mixed_interruption","text":"umm okay stop","confidence":0.9,"agent_speaking":true,"matched_ignored":["umm"],"matched_commands":["stop"],"processing_latency_ms":2.8}
```

### Scenario 4: Low Confidence Ignored
```json
{"level":"INFO","event":"interruption_filter","ts":"2025-01-18T12:34:57.789Z","session_id":"abc123","action":"IGNORE","category":"low_confidence_ignored","text":"hmm yeah","confidence":0.2,"agent_speaking":true,"processing_latency_ms":1.9}
```

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

