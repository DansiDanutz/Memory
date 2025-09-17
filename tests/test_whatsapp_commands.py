#!/usr/bin/env python3
"""
WhatsApp Commands Test Suite for MemoApp Memory Bot
Tests all WhatsApp commands and their functionality
"""

import pytest
import json
import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.memory.storage import MemoryStorage
from app.security.session_store import SessionStore
from app.whatsapp import WhatsAppHandler

class TestWhatsAppCommands:
    """Test all WhatsApp commands"""
    
    @pytest.fixture
    def setup(self):
        """Setup test environment"""
        # Create test directories
        test_dir = Path("test_commands_data")
        test_dir.mkdir(exist_ok=True)
        
        # Initialize components
        memory_storage = MemoryStorage(base_dir=str(test_dir / "memory"))
        session_store = SessionStore()
        
        # Create WhatsApp handler
        whatsapp_handler = WhatsAppHandler(
            memory_storage=memory_storage,
            session_store=session_store
        )
        
        # Pre-populate some test data
        test_phone = "+1234567890"
        import asyncio
        asyncio.run(memory_storage.store_memory(
            user_phone=test_phone,
            content="I love pizza",
            category="GENERAL"
        ))
        
        asyncio.run(memory_storage.store_memory(
            user_phone=test_phone,
            content="Meeting tomorrow at 3pm",
            category="CHRONOLOGICAL"
        ))
        
        asyncio.run(memory_storage.store_memory(
            user_phone=test_phone,
            content="My password is secret123",
            category="CONFIDENTIAL"
        ))
        
        yield {
            'memory_storage': memory_storage,
            'session_store': session_store,
            'whatsapp_handler': whatsapp_handler,
            'test_dir': test_dir,
            'test_phone': test_phone
        }
        
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    @pytest.mark.asyncio
    async def test_help_command(self, setup):
        """Test /help command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/help")
            
            # Should send help message
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert test_phone in args
            
            help_text = args[1]
            assert "Available commands" in help_text or "Commands" in help_text
            assert "/search" in help_text
            assert "/recent" in help_text
            assert "/stats" in help_text
    
    @pytest.mark.asyncio
    async def test_search_command(self, setup):
        """Test /search command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test search with query
            response = await handler._handle_command(test_phone, "/search pizza")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            search_results = args[1]
            
            assert "pizza" in search_results.lower() or "I love pizza" in search_results
            assert "Found" in search_results or "match" in search_results.lower()
            
            # Test search without query
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/search")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            error_msg = args[1]
            assert "Usage" in error_msg or "provide a search term" in error_msg
    
    @pytest.mark.asyncio
    async def test_recent_command(self, setup):
        """Test /recent command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/recent")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            recent_text = args[1]
            
            # Should show recent memories
            assert "Recent" in recent_text or "recent" in recent_text
            assert "password" in recent_text or "Meeting" in recent_text or "pizza" in recent_text
    
    @pytest.mark.asyncio
    async def test_stats_command(self, setup):
        """Test /stats command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/stats")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            stats_text = args[1]
            
            # Should show statistics
            assert "Total" in stats_text or "total" in stats_text
            assert "3" in stats_text  # We stored 3 memories
            assert "GENERAL" in stats_text or "CHRONOLOGICAL" in stats_text or "CONFIDENTIAL" in stats_text
    
    @pytest.mark.asyncio
    async def test_delete_command(self, setup):
        """Test /delete command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        memory_storage = setup['memory_storage']
        
        # Get a memory ID first
        recent = await memory_storage.get_recent_memories(test_phone, limit=1)
        if recent:
            memory_id = recent[0]['id']
            
            with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
                # Test delete with valid ID
                response = await handler._handle_command(test_phone, f"/delete {memory_id}")
                
                mock_send.assert_called()
                args = mock_send.call_args[0]
                delete_msg = args[1]
                
                assert "deleted" in delete_msg.lower() or "removed" in delete_msg.lower()
                
                # Test delete without ID
                mock_send.reset_mock()
                response = await handler._handle_command(test_phone, "/delete")
                
                mock_send.assert_called()
                args = mock_send.call_args[0]
                error_msg = args[1]
                assert "Usage" in error_msg or "provide" in error_msg or "ID" in error_msg
    
    @pytest.mark.asyncio
    async def test_clear_command(self, setup):
        """Test /clear command (requires confirmation)"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # First attempt should ask for confirmation
            response = await handler._handle_command(test_phone, "/clear")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            confirm_msg = args[1]
            
            assert "confirm" in confirm_msg.lower() or "sure" in confirm_msg.lower()
            assert "/clear CONFIRM" in confirm_msg or "YES" in confirm_msg
            
            # Test with confirmation
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/clear CONFIRM")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            clear_msg = args[1]
            
            assert "cleared" in clear_msg.lower() or "deleted" in clear_msg.lower()
    
    @pytest.mark.asyncio
    async def test_voice_command(self, setup):
        """Test /voice command for voice authentication"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/voice")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            voice_msg = args[1]
            
            # Should ask for voice sample
            assert "voice" in voice_msg.lower()
            assert "sample" in voice_msg or "audio" in voice_msg or "record" in voice_msg
    
    @pytest.mark.asyncio
    async def test_login_logout_commands(self, setup):
        """Test /login and /logout commands"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        session_store = setup['session_store']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test login
            response = await handler._handle_command(test_phone, "/login")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            login_msg = args[1]
            
            assert "voice" in login_msg.lower() or "authenticate" in login_msg.lower()
            
            # Simulate successful login
            session_id = session_store.create_session(test_phone)
            assert session_store.has_active_session(test_phone)
            
            # Test logout
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/logout")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            logout_msg = args[1]
            
            assert "logged out" in logout_msg.lower() or "session" in logout_msg.lower()
            assert not session_store.has_active_session(test_phone)
    
    @pytest.mark.asyncio
    async def test_export_command(self, setup):
        """Test /export command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            with patch.object(handler, '_send_document', new_callable=AsyncMock) as mock_doc:
                response = await handler._handle_command(test_phone, "/export")
                
                # Should send export file or message
                assert mock_send.called or mock_doc.called
                
                if mock_send.called:
                    args = mock_send.call_args[0]
                    export_msg = args[1]
                    assert "export" in export_msg.lower()
    
    @pytest.mark.asyncio
    async def test_backup_restore_commands(self, setup):
        """Test /backup and /restore commands"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test backup
            response = await handler._handle_command(test_phone, "/backup")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            backup_msg = args[1]
            
            assert "backup" in backup_msg.lower()
            assert "created" in backup_msg or "saved" in backup_msg or "complete" in backup_msg
            
            # Test restore
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/restore")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            restore_msg = args[1]
            
            assert "restore" in restore_msg.lower()
    
    @pytest.mark.asyncio
    async def test_category_command(self, setup):
        """Test /category command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test listing by category
            response = await handler._handle_command(test_phone, "/category GENERAL")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            category_msg = args[1]
            
            assert "pizza" in category_msg or "GENERAL" in category_msg
            
            # Test without category
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/category")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            list_msg = args[1]
            
            assert "GENERAL" in list_msg
            assert "CHRONOLOGICAL" in list_msg
            assert "CONFIDENTIAL" in list_msg
    
    @pytest.mark.asyncio
    async def test_settings_command(self, setup):
        """Test /settings command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/settings")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            settings_msg = args[1]
            
            # Should show current settings
            assert "Settings" in settings_msg or "settings" in settings_msg
            assert "notification" in settings_msg.lower() or "privacy" in settings_msg.lower()
    
    @pytest.mark.asyncio
    async def test_profile_command(self, setup):
        """Test /profile command"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            with patch.object(handler.tenancy_manager, 'get_user_role', return_value='user'):
                with patch.object(handler.tenancy_manager, 'get_user_tenant', return_value=Mock(name='Default')):
                    response = await handler._handle_command(test_phone, "/profile")
                    
                    mock_send.assert_called()
                    args = mock_send.call_args[0]
                    profile_msg = args[1]
                    
                    # Should show user profile
                    assert "Profile" in profile_msg or "profile" in profile_msg
                    assert test_phone in profile_msg or "user" in profile_msg
    
    @pytest.mark.asyncio
    async def test_invalid_command(self, setup):
        """Test invalid command handling"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            response = await handler._handle_command(test_phone, "/invalidcommand")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            error_msg = args[1]
            
            assert "Unknown" in error_msg or "Invalid" in error_msg or "not recognized" in error_msg
            assert "/help" in error_msg  # Should suggest help command
    
    @pytest.mark.asyncio
    async def test_multi_word_command_parsing(self, setup):
        """Test multi-word command parsing"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test search with multiple words
            response = await handler._handle_command(test_phone, "/search pizza and pasta")
            
            mock_send.assert_called()
            args = mock_send.call_args[0]
            search_msg = args[1]
            
            # Should handle multi-word query
            assert "pizza" in search_msg.lower() or "Found" in search_msg or "match" in search_msg.lower()
            
            # Test category with space
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/category ULTRA SECRET")
            
            mock_send.assert_called()
            # Should handle category with space
    
    @pytest.mark.asyncio
    async def test_command_permissions(self, setup):
        """Test command permissions based on user role"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test admin-only commands as regular user
            with patch.object(handler.tenancy_manager, 'get_user_role', return_value='user'):
                with patch.object(handler.rbac_manager, 'check_permission', return_value=False):
                    # Try to access system backup (admin only)
                    response = await handler._handle_command(test_phone, "/system-backup")
                    
                    if mock_send.called:
                        args = mock_send.call_args[0]
                        msg = args[1]
                        # Should show permission denied or similar
                        assert "permission" in msg.lower() or "denied" in msg.lower() or "authorized" in msg.lower()
            
            # Test as admin
            mock_send.reset_mock()
            with patch.object(handler.tenancy_manager, 'get_user_role', return_value='admin'):
                with patch.object(handler.rbac_manager, 'check_permission', return_value=True):
                    response = await handler._handle_command(test_phone, "/backup")
                    
                    if mock_send.called:
                        args = mock_send.call_args[0]
                        msg = args[1]
                        # Should allow backup
                        assert "backup" in msg.lower()
    
    @pytest.mark.asyncio
    async def test_command_case_insensitivity(self, setup):
        """Test that commands are case-insensitive"""
        handler = setup['whatsapp_handler']
        test_phone = setup['test_phone']
        
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            # Test uppercase
            response = await handler._handle_command(test_phone, "/HELP")
            mock_send.assert_called()
            args1 = mock_send.call_args[0][1]
            
            # Test lowercase
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/help")
            mock_send.assert_called()
            args2 = mock_send.call_args[0][1]
            
            # Should produce same result
            assert "commands" in args1.lower() or "Commands" in args1
            assert "commands" in args2.lower() or "Commands" in args2
            
            # Test mixed case
            mock_send.reset_mock()
            response = await handler._handle_command(test_phone, "/HeLp")
            mock_send.assert_called()
            args3 = mock_send.call_args[0][1]
            
            assert "commands" in args3.lower() or "Commands" in args3


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])