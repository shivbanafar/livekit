"""
Prometheus metrics exporter for interruption filter.
"""

from prometheus_client import Counter, Gauge, Histogram
from typing import Optional


# Metrics
interrupt_ignored_total = Counter(
    'interrupt_ignored_total',
    'Total number of interruptions ignored',
    ['language', 'session']
)

interrupt_stopped_total = Counter(
    'interrupt_stopped_total',
    'Total number of interruptions that stopped the agent',
    ['language', 'session']
)

interrupt_registered_total = Counter(
    'interrupt_registered_total',
    'Total number of interruptions registered as speech',
    ['language', 'session']
)

processing_latency = Histogram(
    'interruption_filter_processing_latency_seconds',
    'Processing latency for interruption filter',
    buckets=[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
)


def record_action(action: str, language: str = "unknown", session: str = "unknown"):
    """
    Record an action metric.
    
    Args:
        action: Action taken (IGNORE, STOP_AGENT, REGISTER_SPEECH)
        language: Language code
        session: Session identifier
    """
    if action == "IGNORE":
        interrupt_ignored_total.labels(language=language, session=session).inc()
    elif action == "STOP_AGENT":
        interrupt_stopped_total.labels(language=language, session=session).inc()
    elif action == "REGISTER_SPEECH":
        interrupt_registered_total.labels(language=language, session=session).inc()


def record_latency(latency_seconds: float):
    """
    Record processing latency.
    
    Args:
        latency_seconds: Processing latency in seconds
    """
    processing_latency.observe(latency_seconds)

