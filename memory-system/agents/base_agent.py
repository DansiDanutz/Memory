"""
Base Agent Framework for Memory System
Provides core functionality for all specialized agents
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """States an agent can be in"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    TERMINATED = "terminated"

class AgentCapability(Enum):
    """Capabilities that agents can have"""
    MEMORY_PROCESSING = "memory_processing"
    PATTERN_DETECTION = "pattern_detection"
    DATA_HARVESTING = "data_harvesting"
    CONTENT_ANALYSIS = "content_analysis"
    METADATA_EXTRACTION = "metadata_extraction"
    QUALITY_VALIDATION = "quality_validation"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    PREDICTIVE_MODELING = "predictive_modeling"
    NATURAL_LANGUAGE = "natural_language"
    VOICE_PROCESSING = "voice_processing"
    IMAGE_PROCESSING = "image_processing"

@dataclass
class AgentMessage:
    """Message structure for inter-agent communication"""
    sender_id: str
    recipient_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'message_type': self.message_type,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to
        }

class BaseAgent(ABC):
    """
    Abstract base class for all memory system agents
    """
    
    def __init__(self, agent_id: str, capabilities: List[AgentCapability], config: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.config = config or {}
        self.state = AgentState.IDLE
        self.is_initialized = False
        self.message_queue = asyncio.Queue()
        self.statistics = {
            'messages_processed': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'last_activity': datetime.now()
        }
        
        # Agent-specific metrics
        self.metrics = {}
        
        logger.info(f"Agent {agent_id} created with capabilities: {[c.value for c in capabilities]}")
    
    async def initialize(self):
        """Initialize the agent"""
        try:
            self.state = AgentState.INITIALIZING
            logger.info(f"Initializing agent {self.agent_id}...")
            
            # Perform agent-specific initialization
            await self._initialize_components()
            
            self.is_initialized = True
            self.state = AgentState.IDLE
            logger.info(f"Agent {self.agent_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self.state = AgentState.ERROR
            raise
    
    @abstractmethod
    async def _initialize_components(self):
        """Initialize agent-specific components (override in subclasses)"""
        pass
    
    async def send_message(self, recipient_id: str, message_type: str, content: Dict[str, Any]) -> AgentMessage:
        """Send a message to another agent"""
        message = AgentMessage(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.now()
        )
        
        # In a real implementation, this would send to a message broker
        logger.debug(f"Agent {self.agent_id} sending message to {recipient_id}: {message_type}")
        return message
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive a message from the queue"""
        try:
            if not self.message_queue.empty():
                message = await self.message_queue.get()
                self.statistics['messages_processed'] += 1
                self.statistics['last_activity'] = datetime.now()
                return message
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            self.statistics['errors'] += 1
            return None
    
    async def process_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Process an incoming message"""
        self.state = AgentState.PROCESSING
        
        try:
            result = await self._handle_message(message)
            self.state = AgentState.IDLE
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.state = AgentState.ERROR
            self.statistics['errors'] += 1
            raise
    
    @abstractmethod
    async def _handle_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Handle incoming message (override in subclasses)"""
        pass
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        uptime = datetime.now() - self.statistics['start_time']
        return {
            'agent_id': self.agent_id,
            'state': self.state.value,
            'capabilities': [c.value for c in self.capabilities],
            'messages_processed': self.statistics['messages_processed'],
            'errors': self.statistics['errors'],
            'uptime_seconds': uptime.total_seconds(),
            'last_activity': self.statistics['last_activity'].isoformat(),
            'metrics': self.metrics
        }
    
    async def shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info(f"Shutting down agent {self.agent_id}")
        self.state = AgentState.TERMINATED
        
        # Perform cleanup
        await self._cleanup()
        
        logger.info(f"Agent {self.agent_id} shutdown complete")
    
    async def _cleanup(self):
        """Perform cleanup operations (override in subclasses if needed)"""
        pass

# Helper classes for missing dependencies in agent files

class DuplicateDetector:
    """Duplicate detection for memory content"""
    
    def __init__(self):
        self.hashes = set()
    
    async def initialize(self):
        """Initialize the duplicate detector"""
        pass
    
    async def check_duplicate(self, raw_input) -> Any:
        """Check if content is duplicate"""
        class DuplicateResult:
            is_duplicate = False
        return DuplicateResult()

class AdaptiveLearner:
    """Adaptive learning component for agents"""
    
    async def initialize(self):
        """Initialize the learner"""
        pass
    
    async def learn_from_processing(self, raw_input, processed_memory):
        """Learn from processing results"""
        pass