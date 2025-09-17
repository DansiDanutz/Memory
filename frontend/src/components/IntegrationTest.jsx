import React, { useState, useEffect } from 'react';
import { memoryService, claudeService, wsService } from '../services';
import api from '../services/apiService';

const IntegrationTest = () => {
  const [testResults, setTestResults] = useState({
    healthCheck: null,
    backendStatus: null,
    claudeStatus: null,
    memoryCreate: null,
    memoryList: null,
    websocket: null
  });
  const [testing, setTesting] = useState(false);

  const runTests = async () => {
    setTesting(true);
    const results = {};
    const userId = 'test_user_' + Date.now();

    // Test 1: Health Check
    try {
      const health = await api.get('/health');
      results.healthCheck = { success: true, data: health };
    } catch (error) {
      results.healthCheck = { success: false, error: error.message };
    }

    // Test 2: Backend Status
    try {
      const status = await api.get('/health/backend-status');
      results.backendStatus = { success: true, data: status };
    } catch (error) {
      results.backendStatus = { success: false, error: error.message };
    }

    // Test 3: Claude Status
    try {
      const claude = await claudeService.getStatus();
      results.claudeStatus = { success: true, data: claude };
    } catch (error) {
      results.claudeStatus = { success: false, error: error.message };
    }

    // Test 4: Create Memory
    try {
      const memory = await memoryService.createMemory({
        user_id: userId,
        content: 'Test memory created at ' + new Date().toISOString(),
        category: 'GENERAL'
      });
      results.memoryCreate = { success: true, data: memory };
    } catch (error) {
      results.memoryCreate = { success: false, error: error.message };
    }

    // Test 5: List Memories
    try {
      const memories = await memoryService.retrieveMemories(userId);
      results.memoryList = { success: true, count: memories.length };
    } catch (error) {
      results.memoryList = { success: false, error: error.message };
    }

    // Test 6: WebSocket Connection
    try {
      wsService.connect(userId, 
        () => {
          results.websocket = { success: true, status: 'connected' };
          setTestResults({ ...results });
        },
        () => {
          results.websocket = { success: false, status: 'disconnected' };
          setTestResults({ ...results });
        }
      );
      
      // Give WebSocket time to connect
      setTimeout(() => {
        if (!results.websocket) {
          results.websocket = { success: false, status: 'timeout' };
          setTestResults({ ...results });
        }
      }, 3000);
    } catch (error) {
      results.websocket = { success: false, error: error.message };
    }

    setTestResults(results);
    setTesting(false);
  };

  useEffect(() => {
    runTests();
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>Frontend-Backend Integration Test</h2>
      <button onClick={runTests} disabled={testing}>
        {testing ? 'Testing...' : 'Run Tests'}
      </button>
      
      <div style={{ marginTop: '20px' }}>
        {Object.entries(testResults).map(([test, result]) => (
          <div key={test} style={{ marginBottom: '10px' }}>
            <strong>{test}:</strong> 
            {result ? (
              <span style={{ color: result.success ? 'green' : 'red', marginLeft: '10px' }}>
                {result.success ? '✅ PASS' : '❌ FAIL'}
                {result.error && <span> - {result.error}</span>}
                {result.data && <pre>{JSON.stringify(result.data, null, 2)}</pre>}
              </span>
            ) : (
              <span style={{ color: 'gray', marginLeft: '10px' }}>Pending...</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default IntegrationTest;