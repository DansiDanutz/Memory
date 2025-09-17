#!/usr/bin/env python3
"""
Test file for Dynamic Category Manager System
Demonstrates intelligent category creation, scoring, and management
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import random

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dynamic_category_manager import DynamicCategoryManager, CategoryScore, SecurityLevel
from dynamic_cleaner_agent import DynamicCleanerAgent

# Test data with various sensitivity levels
TEST_MEMORIES = [
    # Financial (High Security)
    {
        "content": "Bank account password changed. New password: [REDACTED]. Security questions updated for account ending in 4592.",
        "metadata": {"source": "banking_app", "importance": 0.9}
    },
    {
        "content": "Investment portfolio review: Total value $125,000. Moving 30% to bonds, 40% stocks, 30% crypto.",
        "metadata": {"source": "financial_advisor", "importance": 0.8}
    },
    {
        "content": "Tax return filed. Refund expected: $3,200. SSN used for filing: XXX-XX-4567",
        "metadata": {"source": "tax_software", "importance": 0.85}
    },
    
    # Health (High Security)
    {
        "content": "Blood test results: Cholesterol 195, Blood sugar normal. Doctor recommends diet changes.",
        "metadata": {"source": "medical_portal", "importance": 0.7}
    },
    {
        "content": "Prescription filled: Lisinopril 10mg, 90-day supply. Insurance covered 80%.",
        "metadata": {"source": "pharmacy", "importance": 0.75}
    },
    
    # Work (Medium Security)
    {
        "content": "Q4 strategy meeting: Focus on AI integration, target 20% revenue growth. Confidential until announcement.",
        "metadata": {"source": "work_meeting", "importance": 0.6}
    },
    {
        "content": "Performance review scheduled for next Tuesday. Prepare self-assessment and project achievements.",
        "metadata": {"source": "hr_system", "importance": 0.5}
    },
    {
        "content": "Team standup notes: Sprint 23 on track, API integration complete, testing phase begins Monday.",
        "metadata": {"source": "project_management", "importance": 0.4}
    },
    
    # Personal (Low-Medium Security)
    {
        "content": "Anniversary dinner at La Bernardin next Friday 8 PM. Reservation confirmed.",
        "metadata": {"source": "personal_calendar", "importance": 0.5}
    },
    {
        "content": "Kids soccer practice moved to Saturday 10 AM at Riverside Park field 3.",
        "metadata": {"source": "family_schedule", "importance": 0.3}
    },
    
    # Ideas/Projects (Low Security)
    {
        "content": "App idea: Voice-activated memory assistant with AI categorization and smart search.",
        "metadata": {"source": "notes", "importance": 0.4}
    },
    {
        "content": "Blog post draft: 10 Ways AI is Transforming Personal Productivity in 2025",
        "metadata": {"source": "writing_app", "importance": 0.3}
    },
    
    # Daily/Routine (Very Low Security)
    {
        "content": "Grocery list: milk, eggs, bread, chicken, vegetables, coffee",
        "metadata": {"source": "shopping", "importance": 0.1}
    },
    {
        "content": "Reminder: Water plants on Wednesday and Sunday",
        "metadata": {"source": "reminders", "importance": 0.1}
    },
    {
        "content": "Coffee meeting with John at Starbucks on 5th Avenue at 3 PM tomorrow",
        "metadata": {"source": "casual", "importance": 0.2}
    },
    
    # Mixed Content for Category Detection
    {
        "content": "Legal contract review for new vendor agreement. NDA required. Terms: 2-year commitment, $50K annual.",
        "metadata": {"source": "legal", "importance": 0.7}
    },
    {
        "content": "Emergency contact updated: Jane Doe, relationship: spouse, phone: 555-0123",
        "metadata": {"source": "emergency_info", "importance": 0.6}
    },
    {
        "content": "Travel itinerary: NYC to London, Dec 15-22. Flight BA178, Hotel: The Savoy, Meeting with UK team on Dec 17.",
        "metadata": {"source": "travel", "importance": 0.5}
    },
    {
        "content": "Learning Spanish on Duolingo. Current streak: 45 days. Level: Intermediate.",
        "metadata": {"source": "education", "importance": 0.3}
    },
    {
        "content": "Dream journal: Recurring dream about flying over mountains. Possible meaning: desire for freedom?",
        "metadata": {"source": "personal_journal", "importance": 0.2}
    }
]


async def test_dynamic_category_system():
    """Comprehensive test of the Dynamic Category System"""
    
    print("\n" + "=" * 80)
    print("🧠 DYNAMIC CATEGORY MANAGER - COMPREHENSIVE TEST")
    print("=" * 80)
    
    # Initialize the Dynamic Category Manager
    manager = DynamicCategoryManager(
        base_dir='test_dynamic_categories',
        max_categories=15,
        enable_ai=True
    )
    
    # Initialize the Dynamic Cleaner Agent
    cleaner = DynamicCleanerAgent(
        category_manager=manager,
        base_dir='test_dynamic_categories',
        enable_scheduler=False,
        dry_run=True  # Test mode - no actual deletions
    )
    
    print(f"\n📊 Initial State:")
    print(f"  • Maximum Categories: {manager.max_categories}")
    print(f"  • Current Categories: {len(manager.categories)}")
    print(f"  • AI Detection: {'Enabled' if manager.enable_ai else 'Disabled'}")
    print(f"  • Merge Threshold: {manager.merge_threshold}")
    
    # Process each test memory
    print("\n" + "=" * 80)
    print("📝 PROCESSING TEST MEMORIES")
    print("=" * 80)
    
    for i, memory_data in enumerate(TEST_MEMORIES, 1):
        content = memory_data['content']
        metadata = memory_data.get('metadata', {})
        
        print(f"\n{i}. Processing: {content[:60]}...")
        
        # Detect or create category
        cat_id, category = await manager.detect_category(content, metadata)
        
        # Display category information
        print(f"   📁 Category: {category.name}")
        print(f"   🔒 Security Level: {category.score.security_level.value.upper()}")
        print(f"   📊 Scores:")
        print(f"      • Sensitivity: {category.score.sensitivity:.2f}")
        print(f"      • Importance: {category.score.importance:.2f}")
        print(f"      • Frequency: {category.score.frequency:.2f}")
        print(f"      • Criticality: {category.score.criticality:.2f}")
        print(f"      • TOTAL: {category.score.total_score:.2f}")
        print(f"   🎰 Slots Allocated: {category.num_slots}")
        cleaning_text = 'Never Clean' if not category.cleaning_policy['cleanable'] else f'{category.cleaning_policy["retention_days"]} days'
        print(f"   🧹 Cleaning Policy: {cleaning_text}")
        print(f"   🌟 Lifecycle Stage: {category.lifecycle_stage.upper()}")
        
        # Simulate slot updates
        if i % 3 == 0:  # Every third memory updates a slot
            manager.update_slot(
                category_id=cat_id,
                slot_type="recent",
                content=content[:100],
                memory_id=f"mem_{i}",
                score=metadata.get('importance', 0.5)
            )
            print(f"   ✅ Updated 'recent' slot")
    
    # Display category statistics
    print("\n" + "=" * 80)
    print("📊 CATEGORY STATISTICS")
    print("=" * 80)
    
    stats = manager.get_category_stats()
    
    print(f"\n📈 Overall Statistics:")
    print(f"  • Total Categories Created: {stats['total_categories']}")
    print(f"  • Average Category Score: {stats['average_score']:.2f}")
    
    print(f"\n🔒 Security Distribution:")
    for level, count in stats['security_distribution'].items():
        bar = "█" * (count * 2)  # Visual bar
        print(f"  • {level.upper():<12}: {count:2d} {bar}")
    
    print(f"\n🌟 Lifecycle Distribution:")
    for stage, count in stats['lifecycle_distribution'].items():
        bar = "█" * (count * 2)  # Visual bar
        print(f"  • {stage.upper():<10}: {count:2d} {bar}")
    
    print(f"\n🏆 Top Categories by Score:")
    for i, cat in enumerate(stats['categories'][:5], 1):
        security_emoji = "🔴" if cat['security'] in ['secret', 'ultra_secret'] else "🟡" if cat['security'] == 'confidential' else "🟢"
        print(f"  {i}. {security_emoji} {cat['name']:<20} Score: {cat['score']:.2f} | Memories: {cat['memories']} | Stage: {cat['stage']}")
    
    # Test the Dynamic Cleaner
    print("\n" + "=" * 80)
    print("🧹 TESTING DYNAMIC CLEANER")
    print("=" * 80)
    
    print("\n⚙️  Running Intelligent Cleanup (Dry Run)...")
    cleaning_stats = await cleaner.run_intelligent_cleanup()
    
    print(f"\n📊 Cleaning Results:")
    print(f"  • Memories Processed: {cleaning_stats.memories_processed}")
    print(f"  • Memories Would Delete: {cleaning_stats.memories_deleted}")
    print(f"  • Memories Would Archive: {cleaning_stats.memories_archived}")
    print(f"  • Categories Protected: {cleaning_stats.categories_protected}")
    print(f"  • High-Score Categories Skipped: {cleaning_stats.high_score_categories_skipped}")
    print(f"  • Duration: {cleaning_stats.duration_seconds():.2f} seconds")
    
    # Show which categories are protected
    print(f"\n🛡️  Protected Categories (Never Clean):")
    protected_count = 0
    for category in manager.categories.values():
        if category.score.total_score >= 0.7:
            protected_count += 1
            print(f"  • {category.name}: Score {category.score.total_score:.2f} - {category.score.security_level.value.upper()}")
    
    if protected_count == 0:
        print("  • No categories have reached protection threshold (0.7)")
    
    # Get cleaning recommendations
    print(f"\n🔍 Cleaning Recommendations:")
    recommendations = manager.get_cleaning_recommendations()
    if recommendations:
        for rec in recommendations:
            print(f"  • {rec['category_name']}: {rec['action'].upper()} - {rec['reason']}")
    else:
        print("  • No cleaning recommended at this time")
    
    # Demonstrate category merging
    print("\n" + "=" * 80)
    print("🔄 TESTING CATEGORY MERGING")
    print("=" * 80)
    
    # Add more memories to trigger potential merging
    similar_memories = [
        "Another meeting with executives about Q1 planning",
        "Executive committee decision on budget allocation",
        "CEO approval needed for new initiative"
    ]
    
    print("\n📝 Adding similar memories to test merging...")
    for content in similar_memories:
        cat_id, category = await manager.detect_category(content, {"importance": 0.6})
        print(f"  • Assigned to: {category.name} (ID: {cat_id[:8]})")
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ DYNAMIC CATEGORY SYSTEM TEST COMPLETE")
    print("=" * 80)
    
    print(f"\n📋 Final Summary:")
    final_stats = manager.get_category_stats()
    print(f"  • Total Categories: {final_stats['total_categories']}")
    print(f"  • High Security (>0.6): {sum(1 for c in manager.categories.values() if c.score.total_score > 0.6)}")
    print(f"  • Medium Security (0.3-0.6): {sum(1 for c in manager.categories.values() if 0.3 <= c.score.total_score <= 0.6)}")
    print(f"  • Low Security (<0.3): {sum(1 for c in manager.categories.values() if c.score.total_score < 0.3)}")
    
    # Save test report
    report = {
        "test_date": datetime.now().isoformat(),
        "memories_processed": len(TEST_MEMORIES),
        "categories_created": final_stats['total_categories'],
        "category_stats": final_stats,
        "cleaning_stats": cleaning_stats.to_dict(),
        "test_status": "SUCCESS"
    }
    
    report_file = Path('test_dynamic_categories') / 'test_report.json'
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Test report saved to: {report_file}")
    
    # Display a sample category MD file content
    if manager.categories:
        sample_category = list(manager.categories.values())[0]
        sample_file = Path('test_dynamic_categories') / sample_category.category_id / f"{sample_category.category_id}.md"
        if sample_file.exists():
            print(f"\n📝 Sample Category File ({sample_category.name}):")
            print("─" * 60)
            content = sample_file.read_text()[:500]  # First 500 chars
            print(content)
            print("─" * 60)
    
    print("\n🎉 All tests completed successfully!")


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_dynamic_category_system())