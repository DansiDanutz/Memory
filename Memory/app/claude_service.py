"""
Claude AI Service Integration for Memory App
Provides AI-powered text processing, analysis, and generation capabilities
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
import logging

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service class for Claude AI integration"""
    
    def __init__(self):
        """Initialize Claude service with API key from environment"""
        self.api_key = os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            logger.warning("CLAUDE_API_KEY not found in environment variables")
            self.client = None
        else:
            self.client = Anthropic(api_key=self.api_key)
    
    def is_available(self) -> bool:
        """Check if Claude service is available"""
        return self.client is not None
    
    async def analyze_message(self, message: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a message for sentiment, intent, and key information
        
        Args:
            message: The message to analyze
            context: Optional context about the conversation
            
        Returns:
            Dictionary with analysis results
        """
        if not self.is_available():
            return {"error": "Claude service not available", "available": False}
        
        try:
            prompt = f"""
            Analyze the following message for:
            1. Sentiment (positive, negative, neutral)
            2. Intent (question, request, information, complaint, etc.)
            3. Key topics or entities mentioned
            4. Urgency level (low, medium, high)
            5. Suggested response type
            
            Message: "{message}"
            {f"Context: {context}" if context else ""}
            
            Provide your analysis in JSON format.
            """
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "analysis": response.content[0].text,
                "available": True,
                "model": "claude-3-haiku-20240307"
            }
            
        except Exception as e:
            logger.error(f"Claude analysis error: {str(e)}")
            return {"error": str(e), "available": True}
    
    async def generate_response(self, message: str, context: Optional[str] = None, 
                              tone: str = "helpful") -> Dict[str, Any]:
        """
        Generate a response to a message
        
        Args:
            message: The message to respond to
            context: Optional conversation context
            tone: Response tone (helpful, professional, casual, etc.)
            
        Returns:
            Dictionary with generated response
        """
        if not self.is_available():
            return {"error": "Claude service not available", "available": False}
        
        try:
            prompt = f"""
            Generate a {tone} response to the following message. 
            Keep it concise and appropriate for a WhatsApp conversation.
            
            Message: "{message}"
            {f"Context: {context}" if context else ""}
            
            Response:
            """
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "response": response.content[0].text.strip(),
                "available": True,
                "model": "claude-3-haiku-20240307"
            }
            
        except Exception as e:
            logger.error(f"Claude response generation error: {str(e)}")
            return {"error": str(e), "available": True}
    
    async def summarize_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Summarize a conversation thread
        
        Args:
            messages: List of message dictionaries with 'sender' and 'content' keys
            
        Returns:
            Dictionary with conversation summary
        """
        if not self.is_available():
            return {"error": "Claude service not available", "available": False}
        
        try:
            conversation = "\n".join([
                f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}" 
                for msg in messages
            ])
            
            prompt = f"""
            Summarize the following conversation, highlighting:
            1. Main topics discussed
            2. Key decisions or outcomes
            3. Action items or follow-ups needed
            4. Overall sentiment
            
            Conversation:
            {conversation}
            
            Summary:
            """
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "summary": response.content[0].text.strip(),
                "available": True,
                "model": "claude-3-haiku-20240307"
            }
            
        except Exception as e:
            logger.error(f"Claude summarization error: {str(e)}")
            return {"error": str(e), "available": True}
    
    async def extract_memory_items(self, text: str) -> Dict[str, Any]:
        """
        Extract important information that should be remembered
        
        Args:
            text: Text to analyze for memorable information
            
        Returns:
            Dictionary with extracted memory items
        """
        if not self.is_available():
            return {"error": "Claude service not available", "available": False}
        
        try:
            prompt = f"""
            Analyze the following text and extract information that should be remembered:
            1. Important facts or data points
            2. Personal preferences mentioned
            3. Dates, appointments, or deadlines
            4. Contact information
            5. Decisions made
            6. Goals or objectives stated
            
            Text: "{text}"
            
            Extract memorable items in JSON format with categories.
            """
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "memory_items": response.content[0].text.strip(),
                "available": True,
                "model": "claude-3-haiku-20240307"
            }
            
        except Exception as e:
            logger.error(f"Claude memory extraction error: {str(e)}")
            return {"error": str(e), "available": True}

# Global Claude service instance
claude_service = ClaudeService()

# Convenience functions for easy access
async def analyze_message(message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for message analysis"""
    return await claude_service.analyze_message(message, context)

async def generate_response(message: str, context: Optional[str] = None, 
                          tone: str = "helpful") -> Dict[str, Any]:
    """Convenience function for response generation"""
    return await claude_service.generate_response(message, context, tone)

async def summarize_conversation(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Convenience function for conversation summarization"""
    return await claude_service.summarize_conversation(messages)

async def extract_memory_items(text: str) -> Dict[str, Any]:
    """Convenience function for memory extraction"""
    return await claude_service.extract_memory_items(text)
