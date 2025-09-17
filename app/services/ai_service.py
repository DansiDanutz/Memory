"""
AI Service for Memory Management
Based on MEMORY_APP_COMPLETE_PACKAGE implementation
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """AI response data structure"""
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    sentiment: Optional[str] = None
    importance: Optional[int] = None
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AIService:
    """
    AI Service for memory processing and enhancement
    Integrates with OpenAI for advanced features
    """
    
    def __init__(self):
        """Initialize AI Service"""
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        if self.api_key:
            openai.api_key = self.api_key
            self.ai_enabled = True
        else:
            self.ai_enabled = False
            logger.warning("OpenAI API key not configured. AI features will be limited.")
        
        # Default prompts
        self.system_prompts = {
            'categorize': """You are a memory categorization assistant. Categorize the given text into one of these categories:
                GENERAL, CONFIDENTIAL, SECRET, ULTRA_SECRET, CHRONOLOGICAL.
                Also extract key topics and determine sentiment.""",
            
            'summarize': """You are a memory summarization assistant. Create a concise summary of the given memory,
                preserving key information and context.""",
            
            'enhance': """You are a memory enhancement assistant. Analyze the given memory and provide:
                1. Enhanced categorization
                2. Key topics and tags
                3. Sentiment analysis
                4. Importance score (1-10)
                5. Actionable insights if any""",
            
            'search': """You are a memory search assistant. Help find relevant memories based on the query."""
        }
    
    async def categorize_memory(self, content: str) -> AIResponse:
        """
        Categorize memory content using AI
        
        Args:
            content: Memory content to categorize
            
        Returns:
            AIResponse with categorization details
        """
        try:
            if not self.ai_enabled:
                # Fallback to basic categorization
                return self._basic_categorization(content)
            
            # Use OpenAI for categorization
            response = await self._call_openai(
                prompt=f"Categorize this memory: {content}",
                system_prompt=self.system_prompts['categorize']
            )
            
            # Parse response
            result = self._parse_categorization_response(response)
            
            return AIResponse(
                content=content,
                category=result.get('category', 'GENERAL'),
                tags=result.get('tags', []),
                sentiment=result.get('sentiment', 'neutral'),
                importance=result.get('importance', 5),
                metadata=result
            )
            
        except Exception as e:
            logger.error(f"Error in AI categorization: {e}")
            return self._basic_categorization(content)
    
    async def summarize_memory(self, content: str, max_length: int = 100) -> str:
        """
        Create a summary of memory content
        
        Args:
            content: Memory content to summarize
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        try:
            if not self.ai_enabled:
                # Basic summarization
                return content[:max_length] + "..." if len(content) > max_length else content
            
            # Use OpenAI for summarization
            response = await self._call_openai(
                prompt=f"Summarize this memory in {max_length} characters: {content}",
                system_prompt=self.system_prompts['summarize']
            )
            
            return response[:max_length]
            
        except Exception as e:
            logger.error(f"Error in AI summarization: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content
    
    async def enhance_memory(self, content: str) -> AIResponse:
        """
        Enhance memory with AI-generated metadata
        
        Args:
            content: Memory content to enhance
            
        Returns:
            Enhanced AIResponse
        """
        try:
            if not self.ai_enabled:
                return self._basic_categorization(content)
            
            # Use OpenAI for enhancement
            response = await self._call_openai(
                prompt=f"Enhance this memory with metadata: {content}",
                system_prompt=self.system_prompts['enhance']
            )
            
            # Parse enhanced response
            result = self._parse_enhancement_response(response)
            
            return AIResponse(
                content=content,
                category=result.get('category', 'GENERAL'),
                tags=result.get('tags', []),
                sentiment=result.get('sentiment', 'neutral'),
                importance=result.get('importance', 5),
                summary=result.get('summary', ''),
                metadata=result
            )
            
        except Exception as e:
            logger.error(f"Error in AI enhancement: {e}")
            return self._basic_categorization(content)
    
    async def search_memories(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        AI-powered memory search
        
        Args:
            query: Search query
            memories: List of memories to search
            limit: Maximum results
            
        Returns:
            Sorted list of relevant memories
        """
        try:
            if not self.ai_enabled:
                # Basic keyword search
                return self._basic_search(query, memories, limit)
            
            # Use AI for semantic search
            # This would typically use embeddings for better results
            scored_memories = []
            
            for memory in memories:
                score = await self._calculate_relevance(query, memory.get('content', ''))
                scored_memories.append({
                    **memory,
                    'relevance_score': score
                })
            
            # Sort by relevance
            scored_memories.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_memories[:limit]
            
        except Exception as e:
            logger.error(f"Error in AI search: {e}")
            return self._basic_search(query, memories, limit)
    
    async def generate_insights(
        self,
        user_id: str,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate insights from user memories
        
        Args:
            user_id: User identifier
            memories: User's memories
            
        Returns:
            Insights dictionary
        """
        try:
            if not memories:
                return {'insights': [], 'summary': 'No memories to analyze'}
            
            if not self.ai_enabled:
                # Basic insights
                return self._basic_insights(memories)
            
            # Prepare memory summary for analysis
            memory_summary = self._prepare_memory_summary(memories)
            
            # Generate insights using AI
            response = await self._call_openai(
                prompt=f"Generate insights from these memories: {memory_summary}",
                system_prompt="You are a memory analysis assistant. Provide insights, patterns, and recommendations."
            )
            
            return {
                'insights': self._parse_insights(response),
                'summary': response,
                'generated_at': datetime.now().isoformat(),
                'memory_count': len(memories)
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return self._basic_insights(memories)
    
    async def _call_openai(self, prompt: str, system_prompt: str) -> str:
        """
        Call OpenAI API
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            
        Returns:
            AI response
        """
        if not self.ai_enabled:
            return ""
        
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ""
    
    def _basic_categorization(self, content: str) -> AIResponse:
        """
        Basic categorization without AI
        
        Args:
            content: Content to categorize
            
        Returns:
            Basic AIResponse
        """
        # Simple keyword-based categorization
        content_lower = content.lower()
        
        category = 'GENERAL'
        if any(word in content_lower for word in ['confidential', 'private', 'secret']):
            category = 'CONFIDENTIAL'
        elif any(word in content_lower for word in ['password', 'key', 'token']):
            category = 'SECRET'
        
        # Extract basic tags
        tags = []
        if 'work' in content_lower:
            tags.append('work')
        if 'personal' in content_lower:
            tags.append('personal')
        if 'family' in content_lower:
            tags.append('family')
        
        # Basic sentiment
        sentiment = 'neutral'
        if any(word in content_lower for word in ['happy', 'great', 'excellent', 'good']):
            sentiment = 'positive'
        elif any(word in content_lower for word in ['sad', 'bad', 'terrible', 'awful']):
            sentiment = 'negative'
        
        return AIResponse(
            content=content,
            category=category,
            tags=tags,
            sentiment=sentiment,
            importance=5
        )
    
    def _basic_search(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Basic keyword search
        
        Args:
            query: Search query
            memories: Memories to search
            limit: Result limit
            
        Returns:
            Filtered memories
        """
        query_lower = query.lower()
        results = []
        
        for memory in memories:
            content = memory.get('content', '').lower()
            if query_lower in content:
                results.append(memory)
        
        return results[:limit]
    
    def _basic_insights(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate basic insights without AI
        
        Args:
            memories: User memories
            
        Returns:
            Basic insights
        """
        total = len(memories)
        categories = {}
        
        for memory in memories:
            cat = memory.get('category', 'GENERAL')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'insights': [
                f"Total memories: {total}",
                f"Most used category: {max(categories, key=categories.get) if categories else 'None'}",
                f"Categories distribution: {categories}"
            ],
            'summary': f"You have {total} memories across {len(categories)} categories",
            'generated_at': datetime.now().isoformat()
        }
    
    def _parse_categorization_response(self, response: str) -> Dict[str, Any]:
        """Parse AI categorization response"""
        try:
            # Try to parse as JSON
            return json.loads(response)
        except:
            # Fallback to text parsing
            result = {'category': 'GENERAL', 'tags': [], 'sentiment': 'neutral'}
            
            # Extract category
            for cat in ['GENERAL', 'CONFIDENTIAL', 'SECRET', 'ULTRA_SECRET']:
                if cat in response.upper():
                    result['category'] = cat
                    break
            
            return result
    
    def _parse_enhancement_response(self, response: str) -> Dict[str, Any]:
        """Parse AI enhancement response"""
        try:
            return json.loads(response)
        except:
            return {
                'category': 'GENERAL',
                'tags': [],
                'sentiment': 'neutral',
                'importance': 5,
                'summary': response[:100]
            }
    
    async def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        # Simple keyword matching for now
        # In production, use embeddings for semantic similarity
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        return overlap / len(query_words)
    
    def _prepare_memory_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Prepare memory summary for analysis"""
        summaries = []
        for memory in memories[:10]:  # Limit to prevent token overflow
            content = memory.get('content', '')[:100]
            category = memory.get('category', 'GENERAL')
            summaries.append(f"[{category}] {content}")
        
        return "\n".join(summaries)
    
    def _parse_insights(self, response: str) -> List[str]:
        """Parse insights from AI response"""
        # Split response into bullet points
        insights = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                insights.append(line.lstrip('-•1234567890. '))
        
        return insights if insights else [response]