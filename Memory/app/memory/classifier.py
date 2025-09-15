#!/usr/bin/env python3
"""
Message Classifier
Classifies messages into 5 memory categories using AI
"""

import os
import re
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageClassifier:
    """Classify messages into memory categories"""
    
    CATEGORIES = {
        "CHRONOLOGICAL": {
            "keywords": ["tomorrow", "yesterday", "today", "date", "time", "when", "meeting", 
                        "appointment", "schedule", "deadline", "event", "birthday", "anniversary"],
            "patterns": [
                r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # Date patterns
                r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b",  # Time patterns
                r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
                r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                r"\b(?:next|last|this)\s+(?:week|month|year)\b"
            ],
            "priority": 2
        },
        "GENERAL": {
            "keywords": ["like", "prefer", "favorite", "hate", "love", "think", "believe", 
                        "opinion", "fact", "info", "know", "learn", "hobby", "interest"],
            "patterns": [
                r"\b(?:I|my|me)\s+(?:like|love|hate|prefer)\b",
                r"\b(?:favorite|favourite)\s+\w+\b"
            ],
            "priority": 1
        },
        "CONFIDENTIAL": {
            "keywords": ["private", "personal", "confidential", "secret", "password", "pin",
                        "account", "number", "social", "ssn", "id", "license", "passport"],
            "patterns": [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
                r"\b(?:password|pin|code):\s*\S+\b",
                r"\b(?:account|acc)\s*(?:number|#|no)?\s*:?\s*\d+\b"
            ],
            "priority": 3
        },
        "SECRET": {
            "keywords": ["secret", "classified", "sensitive", "restricted", "medical", "health",
                        "diagnosis", "medication", "therapy", "financial", "bank", "credit"],
            "patterns": [
                r"\b(?:bank|credit\s*card|debit\s*card)\s*(?:number|#)?\s*:?\s*\d+\b",
                r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",  # Credit card pattern
                r"\b(?:diagnosed|prescription|medication)\b"
            ],
            "priority": 4
        },
        "ULTRA_SECRET": {
            "keywords": ["ultra secret", "top secret", "highly confidential", "critical",
                        "emergency", "urgent", "legal", "lawsuit", "contract", "will", "testament"],
            "patterns": [
                r"\b(?:legal|lawsuit|attorney|lawyer)\b",
                r"\b(?:will|testament|inheritance)\b",
                r"\b(?:critical|emergency|urgent)\s+(?:information|data|secret)\b"
            ],
            "priority": 5
        }
    }
    
    def __init__(self):
        """Initialize the classifier"""
        self.user_patterns = {}  # Store user-specific patterns
        logger.info("📊 Message classifier initialized")
    
    def classify(self, message: str, user_phone: Optional[str] = None) -> str:
        """
        Classify a message into one of the 5 categories
        Returns: Category name (CHRONOLOGICAL, GENERAL, CONFIDENTIAL, SECRET, ULTRA_SECRET)
        """
        if not message:
            return "GENERAL"
        
        message_lower = message.lower()
        scores = {}
        
        # Calculate scores for each category
        for category, config in self.CATEGORIES.items():
            score = 0
            
            # Check keywords
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    score += 2
            
            # Check patterns
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += 3
            
            # Apply priority weight
            score *= config["priority"]
            scores[category] = score
        
        # Check for explicit category mentions
        if "ultra secret" in message_lower or "ultrasecret" in message_lower:
            return "ULTRA_SECRET"
        elif "secret" in message_lower and "ultra" not in message_lower:
            return "SECRET"
        elif "confidential" in message_lower:
            return "CONFIDENTIAL"
        elif any(word in message_lower for word in ["tomorrow", "yesterday", "appointment", "meeting"]):
            return "CHRONOLOGICAL"
        
        # Return category with highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Default to GENERAL
        return "GENERAL"
    
    def add_user_pattern(self, user_phone: str, category: str, pattern: str):
        """Add a user-specific pattern for classification"""
        if user_phone not in self.user_patterns:
            self.user_patterns[user_phone] = {}
        
        if category not in self.user_patterns[user_phone]:
            self.user_patterns[user_phone][category] = []
        
        self.user_patterns[user_phone][category].append(pattern)
        logger.info(f"Added user pattern for {user_phone}: {category} -> {pattern}")
    
    def get_category_description(self, category: str) -> str:
        """Get a description of a category"""
        descriptions = {
            "CHRONOLOGICAL": "Timeline events, appointments, and date-related memories",
            "GENERAL": "General facts, preferences, and everyday information",
            "CONFIDENTIAL": "Private information requiring basic security",
            "SECRET": "Sensitive information requiring authentication",
            "ULTRA_SECRET": "Highly classified information with maximum security"
        }
        return descriptions.get(category, "Unknown category")