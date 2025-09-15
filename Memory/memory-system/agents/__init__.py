"""
Memory System Agents Module
Advanced AI agents for memory processing and pattern analysis
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import base agent framework
from .base_agent import (
    BaseAgent,
    AgentMessage,
    AgentCapability,
    AgentState
)

# Import specialized agents with error handling
try:
    from .memory_harvester import (
        MemoryHarvesterAgent,
        SourceType,
        ContentType,
        QualityLevel,
        RawMemoryInput,
        ProcessedMemory,
        ValidationResult
    )
    MEMORY_HARVESTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Memory Harvester Agent not available: {e}")
    MEMORY_HARVESTER_AVAILABLE = False
    MemoryHarvesterAgent = None

try:
    from .pattern_analyzer import (
        PatternAnalyzerAgent,
        PatternType,
        PatternStrength,
        HabitType,
        DetectedPattern
    )
    PATTERN_ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Pattern Analyzer Agent not available: {e}")
    PATTERN_ANALYZER_AVAILABLE = False
    PatternAnalyzerAgent = None

# Agent factory for easy instantiation
class AgentFactory:
    """Factory class for creating agent instances"""
    
    @staticmethod
    def create_memory_harvester(config: dict = None) -> Optional[MemoryHarvesterAgent]:
        """Create a Memory Harvester Agent instance"""
        if not MEMORY_HARVESTER_AVAILABLE:
            logger.error("Memory Harvester Agent not available")
            return None
        return MemoryHarvesterAgent(config)
    
    @staticmethod
    def create_pattern_analyzer(config: dict = None) -> Optional[PatternAnalyzerAgent]:
        """Create a Pattern Analyzer Agent instance"""
        if not PATTERN_ANALYZER_AVAILABLE:
            logger.error("Pattern Analyzer Agent not available")
            return None
        return PatternAnalyzerAgent(config)

# Export all public components
__all__ = [
    # Base framework
    'BaseAgent',
    'AgentMessage',
    'AgentCapability',
    'AgentState',
    
    # Memory Harvester
    'MemoryHarvesterAgent',
    'SourceType',
    'ContentType',
    'QualityLevel',
    'RawMemoryInput',
    'ProcessedMemory',
    'ValidationResult',
    'MEMORY_HARVESTER_AVAILABLE',
    
    # Pattern Analyzer
    'PatternAnalyzerAgent',
    'PatternType',
    'PatternStrength',
    'HabitType',
    'DetectedPattern',
    'PATTERN_ANALYZER_AVAILABLE',
    
    # Factory
    'AgentFactory'
]

# Version info
__version__ = '1.0.0'
__author__ = 'Memory System Team'