"""
Performance tests to measure latency introduced by InterruptionFilter.
"""

import pytest
import asyncio
import time
import statistics
from src.interruption_filter import InterruptionFilter, Segment, InterruptionFilterConfig


@pytest.fixture
def filter_instance():
    """Create filter instance for performance testing."""
    config = InterruptionFilterConfig(
        ignored_words={'uh', 'umm', 'hmm', 'haan'},
        command_words={'stop', 'wait', 'hold'},
        confidence_threshold=0.45
    )
    return InterruptionFilter(config=config)


@pytest.mark.asyncio
async def test_single_event_latency(filter_instance):
    """Test latency for a single event (should be < 10ms)."""
    segment = Segment(
        text="uh",
        confidence=0.9,
        agent_speaking=True,
        session_id="perf_test"
    )
    
    start = time.perf_counter()
    action = await filter_instance.handle(segment)
    latency_ms = (time.perf_counter() - start) * 1000
    
    assert latency_ms < 10.0, f"Latency {latency_ms}ms exceeds 10ms threshold"
    assert action is not None


@pytest.mark.asyncio
async def test_batch_processing_latency(filter_instance):
    """Test median latency for processing 1000 events."""
    segments = [
        Segment(
            text="uh",
            confidence=0.9,
            agent_speaking=True,
            session_id="perf_test"
        )
        for _ in range(1000)
    ]
    
    latencies = []
    for segment in segments:
        start = time.perf_counter()
        await filter_instance.handle(segment)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)
    
    median_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    
    print(f"\nPerformance Results:")
    print(f"  Median latency: {median_latency:.2f}ms")
    print(f"  P95 latency: {p95_latency:.2f}ms")
    print(f"  Min latency: {min(latencies):.2f}ms")
    print(f"  Max latency: {max(latencies):.2f}ms")
    
    assert median_latency < 10.0, f"Median latency {median_latency}ms exceeds 10ms threshold"
    assert p95_latency < 20.0, f"P95 latency {p95_latency}ms exceeds 20ms threshold"


@pytest.mark.asyncio
async def test_throughput(filter_instance):
    """Test throughput: events per second."""
    segment = Segment(
        text="test",
        confidence=0.9,
        agent_speaking=True,
        session_id="perf_test"
    )
    
    num_events = 1000
    start = time.perf_counter()
    
    for _ in range(num_events):
        await filter_instance.handle(segment)
    
    total_time = time.perf_counter() - start
    events_per_second = num_events / total_time
    
    print(f"\nThroughput: {events_per_second:.0f} events/second")
    
    # Should handle at least 1000 events/second
    assert events_per_second > 1000, f"Throughput {events_per_second} events/s below 1000 threshold"


@pytest.mark.asyncio
async def test_different_text_lengths(filter_instance):
    """Test latency with different text lengths."""
    test_cases = [
        ("uh", "short"),
        ("uh umm hmm haan", "medium"),
        ("this is a much longer sentence with many words to test performance", "long"),
    ]
    
    results = {}
    for text, label in test_cases:
        segment = Segment(
            text=text,
            confidence=0.9,
            agent_speaking=True,
            session_id="perf_test"
        )
        
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            await filter_instance.handle(segment)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
        
        median = statistics.median(latencies)
        results[label] = median
        print(f"{label} text ({len(text)} chars): {median:.2f}ms median")
    
    # All should be under 10ms
    for label, latency in results.items():
        assert latency < 10.0, f"{label} text latency {latency}ms exceeds threshold"

