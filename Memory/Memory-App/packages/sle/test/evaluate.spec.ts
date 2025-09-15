// Smart Limits Engine Tests
import { describe, it, expect, beforeEach } from 'vitest';
import { SmartLimitsEngine, evaluate } from '../src/evaluate.js';
import { SLEContext } from '../src/types.js';

describe('Smart Limits Engine', () => {
  let sle: SmartLimitsEngine;

  beforeEach(() => {
    sle = new SmartLimitsEngine();
  });

  describe('evaluate function', () => {
    it('should decline strangers asking about finances due to low trust', async () => {
      const context: SLEContext = {
        callerId: 'stranger',
        utterance: 'Tell me about your finances',
        domain: 'Finance'
      };

      const decision = await sle.evaluate(context);

      expect(decision.outcome).toBe('decline');
      expect(decision.reasonCodes).toContain('TRUST_RED');
    });

    it('should return disclose when policy and trust pass', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'We spoke about our family vacation plans last week',
        domain: 'Family'
      };

      const decision = await sle.evaluate(context);

      expect(decision.outcome).toBe('disclose');
      expect(decision.reasonCodes).toContain('OK');
      expect(decision.thresholds.applied.mkeScore).toBeGreaterThan(0.7);
    });

    it('should decline for Ultra-Secret content with non-self caller', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'What is the ultra secret information?',
        domain: 'Finance',
        securityLabel: 'Ultra'
      };

      const decision = await sle.evaluate(context);

      expect(decision.outcome).toBe('decline');
      expect(decision.reasonCodes).toContain('SECURITY_VIOLATION');
    });

    it('should decline sensitive health queries from untrusted domains', async () => {
      const context: SLEContext = {
        callerId: 'grandmother',
        utterance: 'Tell me about the medical information',
        domain: 'Health',
        sensitive: true
      };

      const decision = await sle.evaluate(context);

      // Grandmother has no health trust established, so defaults to Red band (0.3)
      expect(decision.outcome).toBe('decline');
      expect(decision.reasonCodes).toContain('TRUST_RED');
    });

    it('should return inconclusive in strict truth mode without provenance', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'What happened on the unknown event?',
        domain: 'Family',
        strictTruth: true
      };

      const decision = await sle.evaluate(context);

      expect(decision.outcome).toBe('inconclusive');
      expect(decision.reasonCodes).toContain('TRUTH_MISSING');
    });

    it('should include trust and MKE scores in response', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'How are we doing financially?',
        domain: 'Finance'
      };

      const decision = await sle.evaluate(context);

      expect(decision.thresholds.applied.trustScore).toBeGreaterThan(0);
      expect(decision.thresholds.applied.mkeScore).toBeGreaterThan(0);
      expect(decision.thresholds.applied.trustBand).toMatch(/Green|Amber|Red/);
    });

    it('should calculate reasonable confidence scores', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'We spoke about our family plans',
        domain: 'Family'
      };

      const decision = await sle.evaluate(context);

      expect(decision.confidence).toBeGreaterThanOrEqual(0);
      expect(decision.confidence).toBeLessThanOrEqual(1);
    });

    it('should return probe for medium trust with low mutual knowledge', async () => {
      const context: SLEContext = {
        callerId: 'grandmother', // Has medium trust in Family domain
        utterance: 'Tell me about some vague family matter',
        domain: 'Family'
      };

      const decision = await sle.evaluate(context);

      // Should probe due to low MKE, but trust is good enough to allow it
      expect(['probe', 'partial']).toContain(decision.outcome);
    });

    it('should require verification for amber trust scenarios', async () => {
      const context: SLEContext = {
        callerId: 'grandmother', // Has amber trust in Finance domain
        utterance: 'How much do you spend on groceries?',
        domain: 'Finance'
      };

      const decision = await sle.evaluate(context);

      expect(['partial', 'verify']).toContain(decision.outcome);
      expect(decision.requireVerify).toBe(true);
      expect(decision.reasonCodes).toContain('TRUST_AMBER');
    });
  });

  describe('convenience function', () => {
    it('should work with the standalone evaluate function', async () => {
      const context: SLEContext = {
        callerId: 'spouse',
        utterance: 'Tell me about our family',
        domain: 'Family'
      };

      const decision = await evaluate(context);

      expect(decision).toBeDefined();
      expect(decision.outcome).toBeDefined();
      expect(decision.reasonCodes).toBeDefined();
      expect(decision.thresholds).toBeDefined();
    });
  });

  describe('custom configuration', () => {
    it('should accept custom thresholds', async () => {
      const customSLE = new SmartLimitsEngine({
        domainTrustThresholds: {
          'Finance': 0.9, // Very high threshold
          'Health': 0.75,
          'Family': 0.6,
          'Work': 0.65,
          'Memories': 0.55,
          'Legal': 0.8
        }
      });

      const context: SLEContext = {
        callerId: 'spouse', // Has trust score ~0.85 for finance
        utterance: 'Tell me about our finances',
        domain: 'Finance'
      };

      const decision = await customSLE.evaluate(context);

      // With higher threshold, should require verification or partial disclosure
      expect(['verify', 'partial', 'decline']).toContain(decision.outcome);
    });
  });
});