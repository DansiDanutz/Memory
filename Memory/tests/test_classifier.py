#!/usr/bin/env python3
"""
Test Message Classifier
Tests classification of messages into 5 categories
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
import asyncio
from datetime import datetime
from memory.classifier import MessageClassifier

class TestMessageClassifier:
    """Test message classification into 5 categories"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance"""
        return MessageClassifier()
    
    @pytest.mark.asyncio
    async def test_chronological_classification(self, classifier):
        """Test CHRONOLOGICAL category classification"""
        test_messages = [
            "Meeting tomorrow at 3pm",
            "Doctor appointment on January 15th",
            "Birthday party next Saturday",
            "Deadline is 12/25/2024",
            "Conference scheduled for 10:30 AM",
            "Anniversary on March 21st"
        ]
        
        for message in test_messages:
            category = await classifier.classify(message)
            assert category == "CHRONOLOGICAL", f"Failed to classify '{message}' as CHRONOLOGICAL, got {category}"
    
    @pytest.mark.asyncio
    async def test_general_classification(self, classifier):
        """Test GENERAL category classification"""
        test_messages = [
            "I like pizza",
            "My favorite color is blue",
            "I prefer coffee over tea",
            "I love hiking on weekends",
            "My hobby is reading books"
        ]
        
        for message in test_messages:
            category = await classifier.classify(message)
            assert category == "GENERAL", f"Failed to classify '{message}' as GENERAL, got {category}"
    
    @pytest.mark.asyncio
    async def test_confidential_classification(self, classifier):
        """Test CONFIDENTIAL category classification"""
        test_messages = [
            "My password is abc123xyz",
            "PIN code: 4567",
            "Account number is 12345678",
            "Private information about my work",
            "Personal ID: 987-65-4321"
        ]
        
        for message in test_messages:
            category = await classifier.classify(message)
            assert category == "CONFIDENTIAL", f"Failed to classify '{message}' as CONFIDENTIAL, got {category}"
    
    @pytest.mark.asyncio
    async def test_secret_classification(self, classifier):
        """Test SECRET category classification"""
        test_messages = [
            "My bank account has $50,000",
            "Credit card number 4111 1111 1111 1111",
            "Medical diagnosis shows diabetes",
            "Taking medication for anxiety",
            "Financial records show debt",
            "This is a secret project"
        ]
        
        for message in test_messages:
            category = await classifier.classify(message)
            assert category == "SECRET", f"Failed to classify '{message}' as SECRET, got {category}"
    
    @pytest.mark.asyncio
    async def test_ultra_secret_classification(self, classifier):
        """Test ULTRA_SECRET category classification"""
        test_messages = [
            "Ultra secret government project",
            "Top secret classified information",
            "Legal case against the company",
            "My will and testament details",
            "Emergency contact for critical situations",
            "Highly confidential merger plans"
        ]
        
        for message in test_messages:
            category = await classifier.classify(message)
            assert category == "ULTRA_SECRET", f"Failed to classify '{message}' as ULTRA_SECRET, got {category}"
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, classifier):
        """Test edge cases and mixed signals"""
        # Empty message defaults to GENERAL
        category = await classifier.classify("")
        assert category == "GENERAL"
        
        # Mixed signals - should pick highest priority
        category = await classifier.classify("Meeting tomorrow about secret project")
        assert category in ["SECRET", "CHRONOLOGICAL"]
        
        # Explicit category mention overrides
        category = await classifier.classify("This is ultra secret information")
        assert category == "ULTRA_SECRET"
    
    @pytest.mark.asyncio
    async def test_user_patterns(self, classifier):
        """Test user-specific pattern addition"""
        user_phone = "+1234567890"
        
        # Add custom pattern
        classifier.add_user_pattern(user_phone, "SECRET", "project alpha")
        
        # Pattern should now be recognized (though not implemented in classify yet)
        assert user_phone in classifier.user_patterns
        assert "project alpha" in classifier.user_patterns[user_phone]["SECRET"]
    
    def test_category_descriptions(self, classifier):
        """Test category description retrieval"""
        categories = ["CHRONOLOGICAL", "GENERAL", "CONFIDENTIAL", "SECRET", "ULTRA_SECRET"]
        
        for category in categories:
            description = classifier.get_category_description(category)
            assert description is not None
            assert len(description) > 0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])