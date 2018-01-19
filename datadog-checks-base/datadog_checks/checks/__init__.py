
try:
    # Agent5 compatibility layer
    from checks import AgentCheck
except ImportError:
    from .base import AgentCheck

__all__ = [
    'AgentCheck',
]
