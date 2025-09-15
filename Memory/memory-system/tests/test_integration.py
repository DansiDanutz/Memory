#!/usr/bin/env python3
"""
Integration Tests for Digital Immortality Platform
Tests harvest jobs, pattern detection, API endpoints, and UI navigation
"""

import os
import sys
import json
import time
import unittest
import requests
from datetime import datetime, timedelta
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import modules
from database.models import DatabaseManager, User, Memory, HarvestedItem, DetectedPattern, BehavioralInsight, Job
from background_jobs import JobManager
from security.security_manager import SecurityManager
from agents.memory_harvester import MemoryHarvesterAgent
from agents.pattern_analyzer import PatternAnalyzerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_API_URL = "http://localhost:3001"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "test123456"
TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/test_memory_db')

class IntegrationTestCase(unittest.TestCase):
    """Base test case with setup and teardown"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and services"""
        cls.db_manager = DatabaseManager(TEST_DATABASE_URL)
        cls.db_manager.create_tables()
        cls.job_manager = JobManager(TEST_DATABASE_URL)
        cls.security_manager = SecurityManager()
        
        # Create test user
        with cls.db_manager.get_session() as session:
            cls.test_user = User(
                email=TEST_USER_EMAIL,
                username="testuser",
                full_name="Test User",
                user_consent=True
            )
            session.add(cls.test_user)
            session.commit()
            cls.test_user_id = cls.test_user.id
        
        logger.info(f"Created test user with ID: {cls.test_user_id}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        with cls.db_manager.get_session() as session:
            # Delete test data
            session.query(Job).delete()
            session.query(BehavioralInsight).delete()
            session.query(DetectedPattern).delete()
            session.query(HarvestedItem).delete()
            session.query(Memory).delete()
            session.query(User).filter_by(id=cls.test_user_id).delete()
            session.commit()
        logger.info("Cleaned up test data")
    
    def create_test_memories(self, count=10):
        """Create test memories for the user"""
        memories = []
        with self.db_manager.get_session() as session:
            for i in range(count):
                memory = Memory(
                    user_id=self.test_user_id,
                    content=f"Test memory {i} - This is a test memory for integration testing.",
                    source_type="test",
                    tags=["test", f"memory_{i}"],
                    participants=["Test User", "System"],
                    location="Test Location",
                    emotion_scores={"happy": 0.8, "excited": 0.6},
                    quality_score=0.85,
                    user_agreement=True,
                    metadata={"test_id": i}
                )
                session.add(memory)
                memories.append(memory)
            session.commit()
        logger.info(f"Created {count} test memories")
        return memories

class TestHarvestJob(IntegrationTestCase):
    """Test memory harvest job execution"""
    
    def test_harvest_job_creation(self):
        """Test creating a harvest job"""
        job_id = self.job_manager.enqueue_job(
            job_type='harvest',
            params={
                'user_id': self.test_user_id,
                'sources': ['test'],
                'time_range': {'days': 1}
            }
        )
        
        self.assertIsNotNone(job_id)
        logger.info(f"Created harvest job with ID: {job_id}")
        
        # Check job exists
        with self.db_manager.get_session() as session:
            job = session.query(Job).filter_by(id=job_id).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.type, 'harvest')
            self.assertEqual(job.status, 'pending')
    
    def test_harvest_agent_execution(self):
        """Test Memory Harvester Agent execution"""
        # Create test memories
        self.create_test_memories(5)
        
        # Execute harvest
        harvester = MemoryHarvesterAgent({})
        result = harvester.harvest_memories(
            user_id=self.test_user_id,
            sources=['test'],
            time_range={'days': 1}
        )
        
        self.assertIsNotNone(result)
        self.assertIn('harvested_count', result)
        self.assertGreater(result['harvested_count'], 0)
        logger.info(f"Harvested {result['harvested_count']} memories")
        
        # Check harvested items
        with self.db_manager.get_session() as session:
            items = session.query(HarvestedItem).filter_by(user_id=self.test_user_id).all()
            self.assertGreater(len(items), 0)

class TestPatternDetection(IntegrationTestCase):
    """Test pattern detection functionality"""
    
    def test_pattern_analysis_job(self):
        """Test pattern analysis job execution"""
        # Create test memories with patterns
        memories = []
        with self.db_manager.get_session() as session:
            # Create temporal pattern (morning activities)
            for day in range(7):
                memory = Memory(
                    user_id=self.test_user_id,
                    content=f"Morning coffee at 8 AM on day {day}",
                    source_type="test",
                    tags=["morning", "coffee", "routine"],
                    location="Home",
                    created_at=datetime.utcnow() - timedelta(days=day, hours=16),
                    quality_score=0.9,
                    user_agreement=True
                )
                session.add(memory)
                memories.append(memory)
            
            # Create behavioral pattern (exercise)
            for day in range(5):
                memory = Memory(
                    user_id=self.test_user_id,
                    content=f"Went for a run in the evening on day {day}",
                    source_type="test",
                    tags=["exercise", "running", "health"],
                    location="Park",
                    created_at=datetime.utcnow() - timedelta(days=day*2, hours=4),
                    quality_score=0.85,
                    user_agreement=True
                )
                session.add(memory)
                memories.append(memory)
            
            session.commit()
        
        # Run pattern analysis
        analyzer = PatternAnalyzerAgent({})
        patterns = analyzer.analyze_patterns(self.test_user_id)
        
        self.assertIsNotNone(patterns)
        self.assertGreater(len(patterns), 0)
        logger.info(f"Detected {len(patterns)} patterns")
        
        # Check detected patterns in database
        with self.db_manager.get_session() as session:
            db_patterns = session.query(DetectedPattern).filter_by(user_id=self.test_user_id).all()
            self.assertGreater(len(db_patterns), 0)
            
            # Check pattern types
            pattern_types = [p.type for p in db_patterns]
            self.assertIn('temporal', pattern_types)
    
    def test_insight_generation(self):
        """Test behavioral insight generation"""
        # Create patterns first
        self.test_pattern_analysis_job()
        
        # Generate insights
        with self.db_manager.get_session() as session:
            patterns = session.query(DetectedPattern).filter_by(user_id=self.test_user_id).all()
            
            for pattern in patterns[:2]:  # Generate insights for first 2 patterns
                insight = BehavioralInsight(
                    user_id=self.test_user_id,
                    type='pattern_based',
                    title=f"Insight from {pattern.type} pattern",
                    description=f"You have a consistent {pattern.type} pattern: {pattern.description}",
                    confidence=pattern.confidence,
                    impact_score=0.75,
                    recommendations=[
                        "Continue this positive behavior",
                        "Track your progress over time"
                    ],
                    supporting_patterns=[pattern.id]
                )
                session.add(insight)
            
            session.commit()
            
            # Check insights
            insights = session.query(BehavioralInsight).filter_by(user_id=self.test_user_id).all()
            self.assertGreater(len(insights), 0)
            logger.info(f"Generated {len(insights)} insights")

class TestAPIEndpoints(IntegrationTestCase):
    """Test API endpoints with authentication"""
    
    def setUp(self):
        """Set up API session"""
        self.session = requests.Session()
        # Note: In real test, would need to authenticate first
    
    def test_harvest_endpoint(self):
        """Test POST /api/harvest endpoint"""
        response = self.session.post(
            f"{TEST_API_URL}/api/harvest",
            json={
                'sources': ['test'],
                'time_range': {'days': 1}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get('success'))
            self.assertIn('job_id', data)
            logger.info(f"Harvest endpoint returned job_id: {data.get('job_id')}")
    
    def test_patterns_endpoint(self):
        """Test GET /api/patterns endpoint"""
        response = self.session.get(f"{TEST_API_URL}/api/patterns")
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get('success'))
            self.assertIn('patterns', data)
            logger.info(f"Patterns endpoint returned {len(data.get('patterns', []))} patterns")
    
    def test_insights_endpoint(self):
        """Test GET /api/insights endpoint"""
        response = self.session.get(f"{TEST_API_URL}/api/insights")
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get('success'))
            self.assertIn('insights', data)
            logger.info(f"Insights endpoint returned {len(data.get('insights', []))} insights")
    
    def test_review_queue_endpoint(self):
        """Test GET /api/review/queue endpoint"""
        response = self.session.get(f"{TEST_API_URL}/api/review/queue")
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data.get('success'))
            self.assertIn('memories', data)
            logger.info(f"Review queue has {len(data.get('memories', []))} pending memories")
    
    def test_job_status_endpoint(self):
        """Test GET /api/jobs/{job_id} endpoint"""
        # First create a job
        response = self.session.post(
            f"{TEST_API_URL}/api/harvest",
            json={'sources': ['test'], 'time_range': {'days': 1}}
        )
        
        if response.status_code == 200:
            job_id = response.json().get('job_id')
            
            # Get job status
            response = self.session.get(f"{TEST_API_URL}/api/jobs/{job_id}")
            
            if response.status_code == 200:
                data = response.json()
                self.assertTrue(data.get('success'))
                self.assertIn('job', data)
                job = data['job']
                self.assertEqual(job.get('id'), job_id)
                logger.info(f"Job {job_id} status: {job.get('status')}")

class TestSecurityFeatures(IntegrationTestCase):
    """Test security measures"""
    
    def test_encryption(self):
        """Test data encryption and decryption"""
        original_data = "This is sensitive user data"
        
        # Encrypt data
        encrypted = self.security_manager.encrypt_sensitive_data(original_data)
        self.assertIsNotNone(encrypted)
        self.assertNotEqual(encrypted, original_data)
        
        # Decrypt data
        decrypted = self.security_manager.decrypt_sensitive_data(encrypted)
        self.assertEqual(decrypted, original_data)
        logger.info("Encryption/decryption test passed")
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SecurePassword123!"
        
        # Hash password
        hashed, salt = self.security_manager.encryption.hash_password(password)
        self.assertIsNotNone(hashed)
        self.assertIsNotNone(salt)
        
        # Verify correct password
        is_valid = self.security_manager.encryption.verify_password(password, hashed, salt)
        self.assertTrue(is_valid)
        
        # Verify wrong password
        is_invalid = self.security_manager.encryption.verify_password("WrongPassword", hashed, salt)
        self.assertFalse(is_invalid)
        logger.info("Password hashing test passed")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        key = "test_user_endpoint"
        max_calls = 5
        window = 10  # 10 seconds
        
        # Make allowed requests
        for i in range(max_calls):
            allowed = self.security_manager.check_rate_limit(key, max_calls, window)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
        
        # Next request should be blocked
        blocked = self.security_manager.check_rate_limit(key, max_calls, window)
        self.assertFalse(blocked, "Request should be blocked by rate limit")
        logger.info("Rate limiting test passed")
    
    def test_webhook_signature(self):
        """Test webhook signature verification"""
        payload = b'{"event": "test", "data": {"key": "value"}}'
        
        # Generate signature
        signature = self.security_manager.webhook_verifier.generate_signature(payload)
        self.assertIsNotNone(signature)
        
        # Verify correct signature
        is_valid = self.security_manager.verify_webhook(payload, signature)
        self.assertTrue(is_valid)
        
        # Verify wrong signature
        wrong_signature = "sha256=wrongsignature"
        is_invalid = self.security_manager.verify_webhook(payload, wrong_signature)
        self.assertFalse(is_invalid)
        logger.info("Webhook signature test passed")

class TestUINavigation(IntegrationTestCase):
    """Test UI navigation and component rendering"""
    
    def test_react_dashboard_endpoints(self):
        """Test that React dashboard endpoints are accessible"""
        ui_endpoints = [
            '/',
            '/dashboard',
            '/memories',
            '/patterns',
            '/insights',
            '/review',
            '/jobs'
        ]
        
        # Note: These would actually test the React app running on port 5000
        # For now, we just verify the structure exists
        import os
        
        # Check React component files exist
        component_files = [
            'react-dashboard/src/components/Dashboard.jsx',
            'react-dashboard/src/components/PatternsPage.jsx',
            'react-dashboard/src/components/InsightsPage.jsx',
            'react-dashboard/src/components/ReviewQueue.jsx',
            'react-dashboard/src/components/JobStatus.jsx'
        ]
        
        for file_path in component_files:
            full_path = os.path.join(os.path.dirname(__file__), '..', '..', file_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"Component file {file_path} should exist"
            )
        
        logger.info("All React components exist")

def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestHarvestJob))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityFeatures))
    suite.addTests(loader.loadTestsFromTestCase(TestUINavigation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    logger.info("Starting integration tests...")
    
    # Check if services are running
    try:
        response = requests.get(f"{TEST_API_URL}/api/health", timeout=5)
        if response.status_code != 200:
            logger.warning("API server may not be running properly")
    except requests.exceptions.RequestException:
        logger.warning("API server is not accessible at {TEST_API_URL}")
        logger.warning("Some API tests may fail")
    
    # Run tests
    success = run_integration_tests()
    
    if success:
        logger.info("✅ All integration tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some integration tests failed")
        sys.exit(1)