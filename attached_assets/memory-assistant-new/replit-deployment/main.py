"""
Memory Harvester Agent - Replit Entry Point
Main application entry point for running the Memory Harvester Agent on Replit.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from memory_system.config.settings import Settings
from memory_system.agents.memory_harvester import MemoryHarvesterAgent, RawMemoryInput, SourceType
from memory_system.utils.logger import setup_logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

async def main():
    """Main application entry point"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Display welcome message
    welcome_text = Text("Memory Harvester Agent", style="bold blue")
    welcome_panel = Panel(
        welcome_text,
        subtitle="🧠 Advanced Personal Memory Processing System",
        border_style="blue"
    )
    console.print(welcome_panel)
    
    try:
        # Load configuration
        settings = Settings()
        logger.info("Configuration loaded successfully")
        
        # Initialize Memory Harvester Agent
        console.print("🔍 Initializing Memory Harvester Agent...", style="yellow")
        agent = MemoryHarvesterAgent(config=settings.dict())
        await agent.initialize()
        console.print("✅ Memory Harvester Agent initialized successfully!", style="green")
        
        # Run interactive demo
        await run_interactive_demo(agent)
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        console.print(f"❌ Error: {e}", style="red")
        return 1
    
    finally:
        if 'agent' in locals():
            await agent.shutdown()
            console.print("🛑 Memory Harvester Agent shutdown complete", style="blue")
    
    return 0

async def run_interactive_demo(agent: MemoryHarvesterAgent):
    """Run interactive demo of the Memory Harvester Agent"""
    
    console.print("\n🎯 Memory Harvester Agent Demo", style="bold green")
    console.print("Enter memories to process, or type 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            user_input = console.input("[bold cyan]Enter a memory: [/bold cyan]")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input.strip():
                continue
            
            # Create raw memory input
            raw_input = RawMemoryInput(
                content=user_input,
                source_type=SourceType.MANUAL_ENTRY,
                source_metadata={'platform': 'replit_demo'},
                user_id='demo_user',
                timestamp=None  # Will use current time
            )
            
            # Process memory
            console.print("🔄 Processing memory...", style="yellow")
            processed_memory = await agent.process_memory(raw_input)
            
            # Display results
            display_processed_memory(processed_memory)
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!", style="blue")
            break
        except Exception as e:
            console.print(f"❌ Processing error: {e}", style="red")

def display_processed_memory(memory):
    """Display processed memory results"""
    
    # Create result panel
    result_text = f"""
📝 Content: {memory.content[:100]}{'...' if len(memory.content) > 100 else ''}
🏷️  Tags: {', '.join(memory.tags[:5])}
😊 Sentiment: {memory.sentiment.get('label', 'unknown')} ({memory.sentiment.get('score', 0):.2f})
⭐ Quality: {memory.quality_level.value} ({memory.quality_score:.2f})
🌍 Language: {memory.language}
👥 Participants: {', '.join(memory.participants[:3])}
🆔 ID: {memory.id}
    """.strip()
    
    result_panel = Panel(
        result_text,
        title="✅ Memory Processed Successfully",
        border_style="green"
    )
    console.print(result_panel)

async def run_batch_test():
    """Run batch processing test"""
    
    console.print("\n🧪 Running Batch Processing Test...", style="bold yellow")
    
    # Load configuration
    settings = Settings()
    
    # Initialize agent
    agent = MemoryHarvesterAgent(config=settings.dict())
    await agent.initialize()
    
    # Test data
    test_memories = [
        "Had coffee with John this morning at Starbucks",
        "Meeting with the team at 2 PM about the new project",
        "Mom called to check in, she's doing well",
        "Finished reading 'The Great Gatsby' - amazing book!",
        "Went for a run in Central Park, beautiful weather"
    ]
    
    # Create raw inputs
    raw_inputs = []
    for i, content in enumerate(test_memories):
        raw_input = RawMemoryInput(
            content=content,
            source_type=SourceType.MANUAL_ENTRY,
            source_metadata={'platform': 'batch_test'},
            user_id=f'test_user_{i}',
            timestamp=None
        )
        raw_inputs.append(raw_input)
    
    # Process batch
    processed_memories = await agent.process_batch(raw_inputs)
    
    # Display results
    console.print(f"✅ Processed {len(processed_memories)} memories", style="green")
    
    # Show statistics
    stats = await agent.get_processing_stats()
    stats_text = f"""
Total Processed: {stats['total_processed']}
Average Processing Time: {stats.get('avg_processing_time', 0):.3f}s
Quality Distribution: {stats['quality_distribution']}
    """.strip()
    
    stats_panel = Panel(
        stats_text,
        title="📊 Processing Statistics",
        border_style="blue"
    )
    console.print(stats_panel)
    
    await agent.shutdown()

if __name__ == "__main__":
    # Check if running batch test
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        asyncio.run(run_batch_test())
    else:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)

