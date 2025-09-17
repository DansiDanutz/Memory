#!/usr/bin/env python3
"""
Test Suite for Circleback-style MD Agent
Validates all components with sample conversations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Import our components
from .md_agent_upgraded import MDAgentUpgraded, get_upgraded_agent
from .schemas import (
    Utterance, Memory, Entity, ActionItem, Relation,
    EntityType, ActionPriority, ActionStatus, MemoryCategory
)
from .entity_extractor import EntityExtractor
from .action_extractor import ActionExtractor
from .context_enhancer import ContextEnhancer
from .circleback_orchestrator import CirclebackOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample conversations for testing
SAMPLE_CONVERSATIONS = {
    'meeting_standup': {
        'messages': [
            {
                'sender': 'John Smith',
                'text': "Good morning everyone, let's start our standup. I completed the API integration yesterday.",
                'timestamp': datetime.now() - timedelta(minutes=5)
            },
            {
                'sender': 'Sarah Johnson',
                'text': "Great work John! I'm currently working on the frontend dashboard, should be done by tomorrow.",
                'timestamp': datetime.now() - timedelta(minutes=4)
            },
            {
                'sender': 'Mike Chen',
                'text': "I need to discuss a blocker with Sarah about the API endpoints. Can we sync after this meeting?",
                'timestamp': datetime.now() - timedelta(minutes=3)
            },
            {
                'sender': 'John Smith',
                'text': "Sure, I'll also need to deploy the new version to staging by Friday. Sarah, can you review the PR #123?",
                'timestamp': datetime.now() - timedelta(minutes=2)
            },
            {
                'sender': 'Sarah Johnson',
                'text': "Will do! I'll review it today. Also, we have the client demo next Tuesday at 2 PM.",
                'timestamp': datetime.now() - timedelta(minutes=1)
            }
        ]
    },
    
    'action_heavy': {
        'messages': [
            {
                'sender': 'Project Manager',
                'text': "Team, we need to prioritize the following for this sprint:",
                'timestamp': datetime.now() - timedelta(hours=1)
            },
            {
                'sender': 'Project Manager',
                'text': "1. @john - Complete the payment integration by March 15th. This is critical.",
                'timestamp': datetime.now() - timedelta(minutes=59)
            },
            {
                'sender': 'Project Manager',
                'text': "2. @sarah - Update the documentation for the new API endpoints",
                'timestamp': datetime.now() - timedelta(minutes=58)
            },
            {
                'sender': 'Project Manager',
                'text': "3. Everyone - Review and provide feedback on the Q2 roadmap by end of week",
                'timestamp': datetime.now() - timedelta(minutes=57)
            },
            {
                'sender': 'John',
                'text': "I'll start on the payment integration today. Will need access to the Stripe test keys.",
                'timestamp': datetime.now() - timedelta(minutes=55)
            },
            {
                'sender': 'Sarah',
                'text': "Documentation update is already in progress. Should be done by tomorrow.",
                'timestamp': datetime.now() - timedelta(minutes=54)
            }
        ]
    },
    
    'entity_rich': {
        'text': """
        Meeting with Acme Corporation about Project Phoenix.
        
        Attendees: john.smith@acme.com, sarah@ourcompany.com, mike.chen@partner.org
        
        Discussion points:
        - Budget approved for $250,000
        - Timeline: Start April 1st, complete by September 30th
        - Main contact: Jennifer Davis (CEO of Acme) - phone: +1-555-0123
        - Next meeting scheduled for March 20th at 3 PM
        - Technical lead: Dr. Robert Johnson from MIT
        - Using AWS cloud infrastructure
        - Integration with Salesforce CRM required
        - Development in Python and React
        - Weekly status reports to stakeholders@acme.com
        
        Action items assigned during the meeting.
        """
    },
    
    'decision_making': {
        'messages': [
            {
                'sender': 'Tech Lead',
                'text': "We need to decide between MongoDB and PostgreSQL for our database.",
                'timestamp': datetime.now() - timedelta(hours=2)
            },
            {
                'sender': 'Developer 1',
                'text': "I think PostgreSQL would be better for our relational data structure.",
                'timestamp': datetime.now() - timedelta(minutes=115)
            },
            {
                'sender': 'Developer 2',
                'text': "Agreed, plus it has better support for complex queries and transactions.",
                'timestamp': datetime.now() - timedelta(minutes=110)
            },
            {
                'sender': 'Tech Lead',
                'text': "Let's go with PostgreSQL then. Decision made. I'll update the architecture docs.",
                'timestamp': datetime.now() - timedelta(minutes=105)
            },
            {
                'sender': 'Tech Lead',
                'text': "Also decided to use Redis for caching and Docker for containerization.",
                'timestamp': datetime.now() - timedelta(minutes=100)
            }
        ]
    }
}

class TestCirclebackSystem:
    """Test suite for the Circleback-style MD Agent"""
    
    def __init__(self):
        """Initialize test suite"""
        self.agent = get_upgraded_agent()
        self.test_dir = Path('test_output')
        self.test_dir.mkdir(exist_ok=True)
        self.results = []
        
    async def run_all_tests(self):
        """Run all test cases"""
        logger.info("🧪 Starting Circleback System Tests")
        
        # Test individual components
        await self.test_entity_extraction()
        await self.test_action_extraction()
        await self.test_context_enhancement()
        
        # Test full pipeline
        await self.test_full_pipeline()
        
        # Test specific scenarios
        await self.test_standup_meeting()
        await self.test_action_heavy_conversation()
        await self.test_entity_rich_content()
        await self.test_decision_making()
        
        # Generate report
        self.generate_report()
        
        logger.info("✅ All tests completed")
    
    async def test_entity_extraction(self):
        """Test entity extraction component"""
        logger.info("Testing Entity Extraction...")
        
        extractor = EntityExtractor()
        
        # Create test utterances
        utterances = [
            Utterance(
                speaker_id='test',
                text="Meeting with John Smith from Acme Corp on March 15th at john@acme.com",
                timestamp=datetime.now()
            ),
            Utterance(
                speaker_id='test',
                text="Budget approved for $50,000. Contact: +1-555-0123",
                timestamp=datetime.now()
            )
        ]
        
        entities, relations = await extractor.extract_entities(utterances)
        
        # Validate results
        assert len(entities) > 0, "No entities extracted"
        
        # Check for specific entity types
        entity_types = {e.type for e in entities}
        expected_types = {EntityType.PERSON, EntityType.ORGANIZATION, EntityType.DATE, EntityType.EMAIL, EntityType.MONEY, EntityType.PHONE}
        
        found_types = entity_types.intersection(expected_types)
        
        self.results.append({
            'test': 'entity_extraction',
            'status': 'PASS' if len(found_types) >= 3 else 'FAIL',
            'entities_found': len(entities),
            'types_found': [t.value for t in found_types],
            'confidence_avg': sum(e.confidence for e in entities) / len(entities) if entities else 0
        })
        
        logger.info(f"  ✓ Extracted {len(entities)} entities with {len(relations)} relations")
    
    async def test_action_extraction(self):
        """Test action item extraction"""
        logger.info("Testing Action Extraction...")
        
        extractor = ActionExtractor()
        
        # Create test utterances
        utterances = [
            Utterance(
                speaker_id='manager',
                text="John, please complete the report by Friday. This is urgent.",
                timestamp=datetime.now()
            ),
            Utterance(
                speaker_id='john',
                text="I'll finish the report today and send it for review.",
                timestamp=datetime.now()
            ),
            Utterance(
                speaker_id='manager',
                text="Also, we need to schedule a meeting with the client next week.",
                timestamp=datetime.now()
            )
        ]
        
        actions = await extractor.extract_actions(utterances)
        
        # Validate results
        assert len(actions) > 0, "No actions extracted"
        
        # Check for priorities and assignees
        has_assignee = any(a.assignee for a in actions)
        has_due_date = any(a.due_date for a in actions)
        has_priority = any(a.priority != ActionPriority.MEDIUM for a in actions)
        
        self.results.append({
            'test': 'action_extraction',
            'status': 'PASS' if len(actions) >= 2 else 'PARTIAL',
            'actions_found': len(actions),
            'has_assignee': has_assignee,
            'has_due_date': has_due_date,
            'has_priority': has_priority
        })
        
        logger.info(f"  ✓ Extracted {len(actions)} action items")
    
    async def test_context_enhancement(self):
        """Test context enhancement"""
        logger.info("Testing Context Enhancement...")
        
        enhancer = ContextEnhancer()
        
        # Create test data
        utterances = [
            Utterance(speaker_id='john', text="Let's discuss the project", timestamp=datetime.now()),
            Utterance(speaker_id='sarah', text="Sure, what about the timeline?", timestamp=datetime.now())
        ]
        
        entities = [
            Entity(type=EntityType.PERSON, value="John", canonical_name="John Smith", confidence=0.9),
            Entity(type=EntityType.PERSON, value="Sarah", canonical_name="Sarah Johnson", confidence=0.9)
        ]
        
        actions = []
        
        context = await enhancer.enhance_context(
            utterances, entities, actions, 'test_contact'
        )
        
        # Validate results
        assert context is not None, "No context created"
        
        self.results.append({
            'test': 'context_enhancement',
            'status': 'PASS',
            'participants': len(context.participants) if context.participants else 0,
            'has_metadata': bool(context.metadata),
            'confidence': context.metadata.get('confidence', 0)
        })
        
        logger.info(f"  ✓ Enhanced context with {len(context.participants) if context.participants else 0} participants")
    
    async def test_full_pipeline(self):
        """Test full processing pipeline"""
        logger.info("Testing Full Pipeline...")
        
        # Use orchestrator directly
        orchestrator = CirclebackOrchestrator()
        
        # Process sample conversation
        input_data = SAMPLE_CONVERSATIONS['meeting_standup']
        
        result = await orchestrator.process_conversation(
            input_data,
            'test_contact'
        )
        
        # Validate results
        assert result is not None, "No result from pipeline"
        assert len(result.memories) > 0, "No memories created"
        
        self.results.append({
            'test': 'full_pipeline',
            'status': 'PASS' if len(result.memories) > 0 else 'FAIL',
            'utterances': len(result.utterances),
            'memories': len(result.memories),
            'entities': len(result.entities),
            'actions': len(result.action_items),
            'processing_time': result.processing_time,
            'confidence': result.confidence_scores.get('overall', 0)
        })
        
        logger.info(f"  ✓ Pipeline processed {len(result.utterances)} utterances → {len(result.memories)} memories")
    
    async def test_standup_meeting(self):
        """Test standup meeting processing"""
        logger.info("Testing Standup Meeting...")
        
        result = await self.agent.process_conversation(
            SAMPLE_CONVERSATIONS['meeting_standup'],
            'standup_test'
        )
        
        # Validate standup-specific features
        has_updates = any('completed' in m.content.lower() or 'working on' in m.content.lower() 
                         for m in result.memories)
        has_blockers = any('blocker' in m.content.lower() for m in result.memories)
        
        self.results.append({
            'test': 'standup_meeting',
            'status': 'PASS' if has_updates else 'PARTIAL',
            'memories': len(result.memories),
            'has_updates': has_updates,
            'has_blockers': has_blockers,
            'meeting_type': result.context.meeting_type if result.context else None
        })
        
        logger.info(f"  ✓ Standup processed with {len(result.memories)} memories")
    
    async def test_action_heavy_conversation(self):
        """Test action-heavy conversation"""
        logger.info("Testing Action-Heavy Conversation...")
        
        result = await self.agent.process_conversation(
            SAMPLE_CONVERSATIONS['action_heavy'],
            'action_test'
        )
        
        # Check action extraction
        critical_actions = [a for a in result.action_items 
                          if a.priority in [ActionPriority.CRITICAL, ActionPriority.HIGH]]
        
        self.results.append({
            'test': 'action_heavy',
            'status': 'PASS' if len(result.action_items) >= 3 else 'FAIL',
            'total_actions': len(result.action_items),
            'critical_actions': len(critical_actions),
            'with_assignee': sum(1 for a in result.action_items if a.assignee),
            'with_due_date': sum(1 for a in result.action_items if a.due_date)
        })
        
        logger.info(f"  ✓ Extracted {len(result.action_items)} actions ({len(critical_actions)} critical)")
    
    async def test_entity_rich_content(self):
        """Test entity-rich content"""
        logger.info("Testing Entity-Rich Content...")
        
        result = await self.agent.process_conversation(
            SAMPLE_CONVERSATIONS['entity_rich'],
            'entity_test'
        )
        
        # Check entity diversity
        entity_types = set(e.type for e in result.entities)
        
        self.results.append({
            'test': 'entity_rich',
            'status': 'PASS' if len(entity_types) >= 5 else 'PARTIAL',
            'total_entities': len(result.entities),
            'unique_types': len(entity_types),
            'types': [t.value for t in entity_types],
            'high_confidence': sum(1 for e in result.entities if e.confidence > 0.8)
        })
        
        logger.info(f"  ✓ Extracted {len(result.entities)} entities of {len(entity_types)} types")
    
    async def test_decision_making(self):
        """Test decision-making conversation"""
        logger.info("Testing Decision-Making Conversation...")
        
        result = await self.agent.process_conversation(
            SAMPLE_CONVERSATIONS['decision_making'],
            'decision_test'
        )
        
        # Check for decision memories
        decision_memories = [m for m in result.memories 
                           if m.category == MemoryCategory.DECISIONS]
        
        self.results.append({
            'test': 'decision_making',
            'status': 'PASS' if len(decision_memories) > 0 else 'FAIL',
            'total_memories': len(result.memories),
            'decision_memories': len(decision_memories),
            'categories': list(set(m.category.value for m in result.memories))
        })
        
        logger.info(f"  ✓ Identified {len(decision_memories)} decision memories")
    
    def generate_report(self):
        """Generate test report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'passed': sum(1 for r in self.results if r['status'] == 'PASS'),
            'failed': sum(1 for r in self.results if r['status'] == 'FAIL'),
            'partial': sum(1 for r in self.results if r['status'] == 'PARTIAL'),
            'results': self.results,
            'statistics': self.agent.get_statistics()
        }
        
        # Save report
        report_file = self.test_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("TEST REPORT SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {report['total_tests']}")
        logger.info(f"✅ Passed: {report['passed']}")
        logger.info(f"❌ Failed: {report['failed']}")
        logger.info(f"⚠️  Partial: {report['partial']}")
        logger.info(f"Success Rate: {report['passed']/report['total_tests']*100:.1f}%")
        logger.info("="*60)
        
        # Print individual results
        for result in self.results:
            status_emoji = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            logger.info(f"{status_emoji} {result['test']}: {result['status']}")
        
        logger.info(f"\nReport saved to: {report_file}")
        
        return report


async def main():
    """Main test runner"""
    test_suite = TestCirclebackSystem()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())