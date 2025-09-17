"""
Memory System Package
Advanced Personal Memory Management System
"""

__version__ = "1.0.0"
__author__ = "Memory Assistant Team"
__email__ = "team@memoryassistant.ai"

from .agents.memory_harvester import MemoryHarvesterAgent, RawMemoryInput, SourceType
from .config.settings import Settings

__all__ = [
    "MemoryHarvesterAgent",
    "RawMemoryInput", 
    "SourceType",
    "Settings"
]

