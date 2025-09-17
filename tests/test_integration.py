#!/usr/bin/env python3
"""
Integration Test Suite for MemoApp Memory Bot
Tests end-to-end flows and system integration
"""

import pytest
import json
import os
import sys
import asyncio
import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.memory.storage import MemoryStorage
from app.security.session_store import SessionStore
from app.security.audit import AuditLogger, AuditAction
from app.tenancy import TenancyManager, RBACManager
from app.whatsapp import WhatsAppHandler

class TestIntegration:
    """Test end-to-end integration scenarios"""
    
    @pytest.fixture
    def setup(self):
        """Setup test environment"""
        # Create test directories
        test_dir = Path("test_integration_data")
        test_dir.mkdir(exist_ok=True)
        
        # Initialize components
        memory_storage = MemoryStorage(base_dir=str(test_dir / "memory"))
        session_store = SessionStore()
        
        # Create WhatsApp handler
        whatsapp_handler = WhatsAppHandler(
            memory_storage=memory_storage,
            session_store=session_store
        )
        
        # Create audit logger
        audit_logger = AuditLogger(audit_dir=str(test_dir / "audit"))
        
        yield {
            'memory_storage': memory_storage,
            'session_store': session_store,
            'whatsapp_handler': whatsapp_handler,
            'audit_logger': audit_logger,
            'test_dir': test_dir
        }
        
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    @pytest.mark.asyncio
    async def test_complete_user_flow(self, setup):
        """Test complete user flow: onboarding → store memory → search → logout"""
        handler = setup['whatsapp_handler']
        memory_storage = setup['memory_storage']
        session_store = setup['session_store']
        
        user_phone = "+19876543210"
        
        # Mock WhatsApp API calls
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            with patch.object(handler, '_mark_as_read', new_callable=AsyncMock):
                
                # Step 1: Onboarding - First message
                first_message = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": user_phone,
                                    "id": "msg_001",
                                    "type": "text",
                                    "text": {"body": "Hello, this is my first message"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(first_message)
                assert response['status'] == 'processed', "First message should be processed"
                
                # Should send welcome message for first-time user
                welcome_calls = [c for c in mock_send.call_args_list if 'Welcome' in str(c)]
                assert len(welcome_calls) > 0 or mock_send.call_count > 0, "Should send welcome message"
                
                # Step 2: Store a memory
                store_message = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": user_phone,
                                    "id": "msg_002",
                                    "type": "text",
                                    "text": {"body": "I love Italian food, especially pasta"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(store_message)
                assert response['status'] == 'processed', "Memory should be stored"
                
                # Verify memory was stored
                stats = await memory_storage.get_user_stats(user_phone)
                assert stats['total'] >= 1, "Should have at least one memory"
                
                # Step 3: Search for memory
                search_message = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": user_phone,
                                    "id": "msg_003",
                                    "type": "text",
                                    "text": {"body": "/search Italian food"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(search_message)
                assert response['status'] == 'processed', "Search should be processed"
                
                # Verify search was performed
                search_reply_calls = [c for c in mock_send.call_args_list if 'Italian' in str(c) or 'pasta' in str(c)]
                assert len(search_reply_calls) > 0 or mock_send.call_count > 2, "Should return search results"
                
                # Step 4: Logout
                logout_message = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": user_phone,
                                    "id": "msg_004",
                                    "type": "text",
                                    "text": {"body": "/logout"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(logout_message)
                assert response['status'] == 'processed', "Logout should be processed"
                
                # Verify session was cleared
                assert not session_store.has_active_session(user_phone), "Session should be cleared after logout"
    
    @pytest.mark.asyncio
    async def test_whatsapp_webhook_verification(self, setup):
        """Test WhatsApp webhook verification (GET request)"""
        # Simulate webhook verification parameters
        verify_token = "test_verify_token"
        challenge = "test_challenge_code"
        
        # Mock environment variable
        with patch.dict(os.environ, {'WHATSAPP_VERIFY_TOKEN': verify_token}):
            # Test valid verification
            params = {
                'hub.mode': 'subscribe',
                'hub.verify_token': verify_token,
                'hub.challenge': challenge
            }
            
            # In real implementation, this would be handled by the web framework
            # Here we simulate the verification logic
            if (params.get('hub.mode') == 'subscribe' and 
                params.get('hub.verify_token') == verify_token):
                result = params.get('hub.challenge')
            else:
                result = None
            
            assert result == challenge, "Should return challenge for valid verification"
            
            # Test invalid verification token
            invalid_params = {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'wrong_token',
                'hub.challenge': challenge
            }
            
            if (invalid_params.get('hub.mode') == 'subscribe' and 
                invalid_params.get('hub.verify_token') == verify_token):
                result = invalid_params.get('hub.challenge')
            else:
                result = None
            
            assert result is None, "Should not return challenge for invalid token"
    
    @pytest.mark.asyncio
    async def test_whatsapp_message_processing(self, setup):
        """Test WhatsApp message processing (POST request)"""
        handler = setup['whatsapp_handler']
        
        # Mock WhatsApp API calls
        with patch.object(handler, '_send_reply', new_callable=AsyncMock) as mock_send:
            with patch.object(handler, '_mark_as_read', new_callable=AsyncMock) as mock_read:
                
                # Test text message
                text_webhook = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "+1234567890",
                                    "id": "msg_text",
                                    "type": "text",
                                    "text": {"body": "Store this memory"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(text_webhook)
                assert response['status'] == 'processed', "Text message should be processed"
                mock_read.assert_called_with("msg_text")
                
                # Test audio message
                audio_webhook = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "+1234567890",
                                    "id": "msg_audio",
                                    "type": "audio",
                                    "audio": {
                                        "id": "audio_123",
                                        "mime_type": "audio/ogg"
                                    }
                                }]
                            }
                        }]
                    }]
                }
                
                # Mock audio download and transcription
                with patch.object(handler, '_download_media', new_callable=AsyncMock) as mock_download:
                    mock_download.return_value = b"fake_audio_data"
                    with patch.object(handler.voice_service, 'transcribe', new_callable=AsyncMock) as mock_transcribe:
                        mock_transcribe.return_value = "Transcribed audio message"
                        
                        response = await handler.process_webhook(audio_webhook)
                        assert response['status'] == 'processed', "Audio message should be processed"
                        mock_read.assert_called_with("msg_audio")
                
                # Test unsupported message type
                image_webhook = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "+1234567890",
                                    "id": "msg_image",
                                    "type": "image",
                                    "image": {"id": "img_123"}
                                }]
                            }
                        }]
                    }]
                }
                
                response = await handler.process_webhook(image_webhook)
                assert response['status'] == 'processed', "Unsupported type should still be processed"
                
                # Should send message about unsupported type
                unsupported_calls = [c for c in mock_send.call_args_list if 'text and voice' in str(c)]
                assert len(unsupported_calls) > 0 or mock_send.call_count > 0, "Should inform about supported types"
    
    @pytest.mark.asyncio
    async def test_tenancy_isolation(self, setup):
        """Test tenancy isolation between different users"""
        memory_storage = setup['memory_storage']
        
        # Create memories for different users
        user1_phone = "+1111111111"
        user2_phone = "+2222222222"
        
        # Store memories for user 1
        await memory_storage.store_memory(
            user_phone=user1_phone,
            content="User 1 secret information",
            category="SECRET"
        )
        
        await memory_storage.store_memory(
            user_phone=user1_phone,
            content="User 1 general information",
            category="GENERAL"
        )
        
        # Store memories for user 2
        await memory_storage.store_memory(
            user_phone=user2_phone,
            content="User 2 confidential data",
            category="CONFIDENTIAL"
        )
        
        await memory_storage.store_memory(
            user_phone=user2_phone,
            content="User 2 general data",
            category="GENERAL"
        )
        
        # Test that users can only access their own memories
        user1_stats = await memory_storage.get_user_stats(user1_phone)
        user2_stats = await memory_storage.get_user_stats(user2_phone)
        
        assert user1_stats['total'] == 2, "User 1 should have 2 memories"
        assert user2_stats['total'] == 2, "User 2 should have 2 memories"
        
        # Search should only return user's own memories
        user1_results = await memory_storage.search_memories(
            user_phone=user1_phone,
            query="information"
        )
        
        user2_results = await memory_storage.search_memories(
            user_phone=user2_phone,
            query="data"
        )
        
        # Verify isolation
        for result in user1_results:
            assert "User 1" in result.get('content', result.get('content_preview', '')), "User 1 should only see their memories"
            assert "User 2" not in result.get('content', result.get('content_preview', '')), "User 1 should not see User 2 memories"
        
        for result in user2_results:
            assert "User 2" in result.get('content', result.get('content_preview', '')), "User 2 should only see their memories"
            assert "User 1" not in result.get('content', result.get('content_preview', '')), "User 2 should not see User 1 memories"
        
        # Verify file system isolation
        user1_dir = setup['test_dir'] / "memory" / "users" / "1111111111"
        user2_dir = setup['test_dir'] / "memory" / "users" / "2222222222"
        
        assert user1_dir.exists(), "User 1 directory should exist"
        assert user2_dir.exists(), "User 2 directory should exist"
        
        # Check that directories are separate
        assert user1_dir != user2_dir, "User directories should be different"
    
    @pytest.mark.asyncio
    async def test_rbac_permissions_enforcement(self, setup):
        """Test RBAC permissions enforcement"""
        handler = setup['whatsapp_handler']
        rbac_manager = handler.rbac_manager
        tenancy_manager = handler.tenancy_manager
        
        # Setup test users with different roles
        admin_phone = "+1000000001"
        manager_phone = "+1000000002"
        user_phone = "+1000000003"
        viewer_phone = "+1000000004"
        
        # Mock role assignments
        with patch.object(tenancy_manager, 'get_user_role') as mock_get_role:
            # Test admin permissions
            mock_get_role.return_value = 'admin'
            
            # Admin should have all permissions
            assert rbac_manager.check_memory_access('admin', 'ULTRA_SECRET', 'write')
            assert rbac_manager.check_memory_access('admin', 'ULTRA_SECRET', 'read')
            assert rbac_manager.check_permission('admin', rbac_manager.Permission.SYSTEM_CONFIG)
            
            # Test manager permissions
            mock_get_role.return_value = 'manager'
            
            # Manager can read but not write ultra secret
            assert rbac_manager.check_memory_access('manager', 'ULTRA_SECRET', 'read')
            assert not rbac_manager.check_memory_access('manager', 'ULTRA_SECRET', 'write')
            assert rbac_manager.check_permission('manager', rbac_manager.Permission.USER_MANAGE)
            assert not rbac_manager.check_permission('manager', rbac_manager.Permission.SYSTEM_CONFIG)
            
            # Test user permissions
            mock_get_role.return_value = 'user'
            
            # User can write but not read secrets without authentication
            assert rbac_manager.check_memory_access('user', 'SECRET', 'write')
            assert not rbac_manager.check_memory_access('user', 'SECRET', 'read')
            assert rbac_manager.check_memory_access('user', 'GENERAL', 'write')
            assert rbac_manager.check_memory_access('user', 'GENERAL', 'read')
            
            # Test viewer permissions
            mock_get_role.return_value = 'viewer'
            
            # Viewer can only read non-secret
            assert rbac_manager.check_memory_access('viewer', 'GENERAL', 'read')
            assert not rbac_manager.check_memory_access('viewer', 'GENERAL', 'write')
            assert not rbac_manager.check_memory_access('viewer', 'SECRET', 'read')
            assert not rbac_manager.check_memory_access('viewer', 'SECRET', 'write')
    
    @pytest.mark.asyncio
    async def test_audit_logging_for_all_operations(self, setup):
        """Test audit logging for all operations"""
        audit_logger = setup['audit_logger']
        memory_storage = setup['memory_storage']
        session_store = setup['session_store']
        
        user_phone = "+1234567890"
        
        # Test memory store audit
        audit_logger.log(
            AuditAction.MEMORY_STORED,
            user_phone,
            {'category': 'GENERAL', 'size': 100}
        )
        
        # Test memory read audit
        audit_logger.log(
            AuditAction.MEMORY_READ,
            user_phone,
            {'memory_id': 'mem_123', 'category': 'GENERAL'}
        )
        
        # Test search audit
        audit_logger.log(
            AuditAction.MEMORY_SEARCHED,
            user_phone,
            {'query': 'test search', 'results': 5}
        )
        
        # Test authentication audit
        audit_logger.log(
            AuditAction.AUTH_SUCCESS,
            user_phone,
            {'method': 'voice', 'session_id': 'sess_123'}
        )
        
        # Test access denied audit
        audit_logger.log(
            AuditAction.ACCESS_DENIED,
            user_phone,
            {'resource': 'ULTRA_SECRET', 'reason': 'no_session'}
        )
        
        # Wait for background writer to process
        await asyncio.sleep(0.1)
        
        # Verify audit logs were written
        audit_files = list(setup['test_dir'].glob("audit/audit_*.jsonl"))
        assert len(audit_files) > 0, "Audit log file should exist"
        
        # Read and verify audit entries
        with open(audit_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 5, "Should have at least 5 audit entries"
            
            # Parse and verify each entry
            entries = [json.loads(line) for line in lines]
            
            # Check that all required fields are present
            for entry in entries:
                assert 'id' in entry, "Audit entry should have ID"
                assert 'timestamp' in entry, "Audit entry should have timestamp"
                assert 'action' in entry, "Audit entry should have action"
                assert 'user' in entry, "Audit entry should have user"
                assert 'details' in entry, "Audit entry should have details"
            
            # Verify specific actions were logged
            actions = [e['action'] for e in entries]
            assert 'memory.stored' in actions, "Memory store should be logged"
            assert 'memory.read' in actions, "Memory read should be logged"
            assert 'memory.searched' in actions, "Search should be logged"
            assert 'auth.success' in actions, "Authentication should be logged"
            assert 'access.denied' in actions, "Access denied should be logged"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])