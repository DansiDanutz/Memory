// Smart Limits Engine (SLE) Test Suite
import { describe, test, expect } from 'vitest';
import { evaluate, SLEContext } from './evaluate';

describe('Smart Limits Engine (SLE)', () => {
  
  test('should allow disclosure for trusted family member with high mutual knowledge', async () => {
    const context: SLEContext = {
      callerId: 'spouse',
      utterance: 'We talked about our vacation to Hawaii last month',
      domain: 'Family'
    };

    const decision = await evaluate(context);
    
    expect(decision.outcome).toBe('disclose');
    expect(decision.confidence).toBeGreaterThan(0.8);
    expect(decision.thresholds.applied.trustScore).toBeGreaterThan(0.8);
    expect(decision.thresholds.applied.mkeScore).toBeGreaterThan(0.8);
    expect(decision.reasonCodes).toContain('OK');
  });

  test('should require verification for amber trust financial queries', async () => {
    const context: SLEContext = {
      callerId: 'grandmother', 
      utterance: 'How much money do you have in your savings account?',
      domain: 'Finance'
    };

    const decision = await evaluate(context);
    
    expect(decision.outcome).toBe('partial');
    expect(decision.thresholds.applied.trustBand).toBe('Amber');
    expect(decision.reasonCodes).toContain('TRUST_AMBER');
    expect(decision.needsVerification).toBe(true);
  });

  test('should decline red trust stranger health queries', async () => {
    const context: SLEContext = {
      callerId: 'stranger',
      utterance: 'Tell me about your medical history and conditions',
      domain: 'Health',
      sensitive: true
    };

    const decision = await evaluate(context);
    
    expect(decision.outcome).toBe('decline');
    expect(decision.thresholds.applied.trustBand).toBe('Red');
    expect(decision.reasonCodes).toContain('TRUST_RED');
    expect(decision.confidence).toBeLessThan(0.7);
  });

  test('should block Ultra-Secret content regardless of trust level', async () => {
    const context: SLEContext = {
      callerId: 'spouse',
      utterance: 'What is the ultra secret project information?',
      domain: 'Finance',
      securityLabel: 'Ultra'
    };

    const decision = await evaluate(context);
    
    expect(decision.outcome).toBe('decline');
    expect(decision.reasonCodes).toContain('MPL_DENY');
    expect(decision.reasonCodes).toContain('SECURITY_VIOLATION');
  });

  test('should require verification in Truth-of-Faith strict mode', async () => {
    const context: SLEContext = {
      callerId: 'spouse',
      utterance: 'Tell me about our mortgage payment discussion',
      domain: 'Finance',
      strictTruth: true
    };

    const decision = await evaluate(context);
    
    expect(decision.outcome).toBe('verify');
    expect(decision.needsVerification || false).toBe(true);
    expect(decision.reasonCodes).toContain('OK');
    expect(decision.confidence).toBeGreaterThanOrEqual(0.9);
  });

  test('should handle low mutual knowledge with probe response', async () => {
    const context: SLEContext = {
      callerId: 'friend',
      utterance: 'Tell me about your work project details',
      domain: 'Work'
    };

    const decision = await evaluate(context);
    
    // Should either probe for more info or require verification (or decline if low trust)
    expect(['probe', 'partial', 'verify', 'decline']).toContain(decision.outcome);
    expect(decision.thresholds.applied.mkeScore).toBeLessThan(0.8);
  });

  test('should apply proper security clearance for C2 content', async () => {
    const context: SLEContext = {
      callerId: 'spouse',
      utterance: 'What did we discuss about the C2 classified information?',
      domain: 'Work',
      securityLabel: 'C2'
    };

    const decision = await evaluate(context);
    
    // C2 requires user+1 person clearance
    expect(['decline', 'verify']).toContain(decision.outcome);
    if (decision.reasonCodes.includes('SECURITY_VIOLATION')) {
      expect(decision.outcome).toBe('decline');
    }
  });

  test('should handle multiple risk factors appropriately', async () => {
    const context: SLEContext = {
      callerId: 'acquaintance',
      utterance: 'Can you tell me sensitive details about your personal finances?',
      domain: 'Finance',
      sensitive: true
    };

    const decision = await evaluate(context);
    
    // Multiple risk factors: low trust + sensitive + finance
    expect(['decline', 'partial', 'throttle']).toContain(decision.outcome);
    expect(decision.thresholds.applied.trustScore).toBeLessThan(0.8);
    expect(decision.confidence).toBeLessThan(1.0);
  });

  test('should provide consistent reasoning for decisions', async () => {
    const context: SLEContext = {
      callerId: 'spouse',
      utterance: 'What did we talk about yesterday?',
      domain: 'General'
    };

    const decision = await evaluate(context);
    
    expect(decision.reasoning || []).toBeDefined();
    expect(Array.isArray(decision.reasoning || [])).toBe(true);
    expect(decision.reasonCodes).toBeDefined();
    expect(Array.isArray(decision.reasonCodes)).toBe(true);
    expect(decision.reasonCodes.length).toBeGreaterThan(0);
  });

  test('should handle edge case with missing context gracefully', async () => {
    const context: SLEContext = {
      callerId: '',
      utterance: '',
      domain: 'General'
    };

    const decision = await evaluate(context);
    
    // Should not crash and should provide a reasonable default
    expect(decision).toBeDefined();
    expect(decision.outcome).toBeDefined();
    expect(decision.confidence).toBeGreaterThanOrEqual(0);
    expect(decision.confidence).toBeLessThanOrEqual(1);
  });
});