#!/usr/bin/env python3
"""
Main Application - Memory System Phase 2
Integrates and runs all components of the advanced memory system
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=\'%(asctime)s - %(name)s - %(levelname)s - %(message)s\',
    handlers=[
        logging.FileHandler("memory_system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import system components
from memory-system.md_file_manager import MDFileManager
from memory-system.conversation_classifier import ConversationClassifier
from memory-system.enhanced_user_onboarding import EnhancedUserOnboarding
from memory-system.daily_memory_manager import DailyMemoryManager
from memory-system.confidential_manager import ConfidentialManager

# Import communication bots (placeholders)
# from communication.whatsapp_bot import WhatsAppBot
# from communication.telegram_bot import TelegramBot

class MemorySystem:
    """Main class for the Memory System"""
    
    def __init__(self):
        """Initialize the complete memory system"""
        logger.info("🚀 Initializing Memory System Phase 2...")
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found. AI features will be limited.")
        
        # Initialize components
        self.md_file_manager = MDFileManager()
        self.conversation_classifier = ConversationClassifier(openai_api_key=openai_api_key)
        self.confidential_manager = ConfidentialManager()
        
        # Initialize communication bots (placeholders)
        # self.whatsapp_bot = WhatsAppBot()
        # self.telegram_bot = TelegramBot()
        
        # Initialize user-facing components
        self.user_onboarding = EnhancedUserOnboarding(
            # whatsapp_bot=self.whatsapp_bot,
            # telegram_bot=self.telegram_bot,
            md_file_manager=self.md_file_manager,
            conversation_classifier=self.conversation_classifier
        )
        
        self.daily_memory_manager = DailyMemoryManager(
            md_file_manager=self.md_file_manager,
            conversation_classifier=self.conversation_classifier,
            # whatsapp_bot=self.whatsapp_bot,
            # telegram_bot=self.telegram_bot,
            openai_api_key=openai_api_key
        )
        
        logger.info("✅ Memory System components initialized successfully")
    
    async def start(self):
        """Start all system services"""
        logger.info("Starting all Memory System services...")
        
        # Start daily memory manager scheduler
        self.daily_memory_manager.start_scheduler()
        
        # Start communication bots (placeholders)
        # await self.whatsapp_bot.start()
        # await self.telegram_bot.start()
        
        logger.info("🔥 Memory System is now running")
        
        # Keep the system running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour
        except asyncio.CancelledError:
            logger.info("Memory System is shutting down...")
            self.stop()
    
    def stop(self):
        """Stop all system services"""
        logger.info("Stopping all Memory System services...")
        
        # Stop daily memory manager scheduler
        self.daily_memory_manager.stop_scheduler()
        
        # Stop communication bots (placeholders)
        # self.whatsapp_bot.stop()
        # self.telegram_bot.stop()
        
        logger.info("🛑 Memory System has been stopped")

async def main():
    """Main entry point for the application"""
    system = MemorySystem()
    
    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping system...")
    finally:
        system.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Memory System shut down.")


