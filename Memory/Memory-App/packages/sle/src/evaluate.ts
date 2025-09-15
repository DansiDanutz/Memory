// Smart Limits Engine - Core Evaluation Logic
// Implements the SLE decision flow: MPL → CEMG → BLTS → KPE → IPSG → Outcome

import { MPL } from '@memory-app/mpl';
import { BLTS } from '@memory-app/blts';
import { CEMG } from '@memory-app/cemg';
import { KPE } from '@memory-app/kpe';
import { IPSG } from '@memory-app/ipsg';

import { 
  SLEContext, 
  SLEDecision, 
  SLEConfig, 
  DEFAULT_SLE_CONFIG,
  ReasonCode,
  TrustBand 
} from './types.js';

export class SmartLimitsEngine {
  private config: SLEConfig;
  private mpl: MPL;
  private blts: BLTS;
  private cemg: CEMG;
  private kpe: KPE;
  private ipsg: IPSG;

  constructor(
    config: Partial<SLEConfig> = {},
    mpl?: MPL,
    blts?: BLTS,
    cemg?: CEMG,
    kpe?: KPE,
    ipsg?: IPSG
  ) {
    this.config = { ...DEFAULT_SLE_CONFIG, ...config };
    this.mpl = mpl || new MPL();
    this.blts = blts || new BLTS();
    this.cemg = cemg || new CEMG();
    this.kpe = kpe || new KPE();
    this.ipsg = ipsg || new IPSG();
  }

  async evaluate(context: SLEContext): Promise<SLEDecision> {
    const reasonCodes: ReasonCode[] = [];
    let outcome: SLEDecision['outcome'] = 'disclose';
    let requireVerify = false;
    let redactions: string[] = [];
    let prompts: string[] = [];

    // Step 1: MPL (Policy) Check
    const policyResult = await this.mpl.evaluate({
      domain: context.domain,
      scope: context.scope || '',
      callerId: context.callerId,
      securityLabel: context.securityLabel || 'General'
    });

    if (!policyResult.allow) {
      reasonCodes.push('MPL_DENY');
      outcome = policyResult.requireVerify ? 'verify' : 'decline';
      requireVerify = policyResult.requireVerify || false;
      redactions = policyResult.redactions || [];
    }

    // Step 2: CEMG (Mutual Knowledge Estimation)
    const mkeScore = await this.cemg.estimateMutualKnowledge({
      askerId: context.callerId,
      utterance: context.utterance,
      domain: context.domain
    });

    const mkeThresholds = this.config.mkeThresholds;
    if (mkeScore < mkeThresholds.divert) {
      reasonCodes.push('MKE_LOW');
      outcome = 'divert';
      prompts.push("I'm not sure what you're referring to. Could you be more specific?");
    } else if (mkeScore < mkeThresholds.probe) {
      reasonCodes.push('MKE_LOW');
      outcome = 'probe';
      prompts.push("Can you tell me more about what you'd like to know?");
    } else if (mkeScore < mkeThresholds.partial && outcome === 'disclose') {
      outcome = 'partial';
    }

    // Step 3: BLTS (Trust Scoring)
    const trustScore = await this.blts.getTrust(context.callerId, context.domain);
    const trustThreshold = this.config.domainTrustThresholds[context.domain];
    const trustBand = this.blts.getTrustBand(trustScore);

    if (trustScore < trustThreshold) {
      if (trustBand === 'Red') {
        reasonCodes.push('TRUST_RED');
        outcome = 'decline';
      } else if (trustBand === 'Amber') {
        reasonCodes.push('TRUST_AMBER');
        if (outcome === 'disclose') {
          outcome = 'partial';
        }
        requireVerify = true;
      }
    }

    // Step 4: KPE (Truth-of-Faith/Provenance Check)
    if (context.strictTruth) {
      const provenanceResult = await this.kpe.checkProvenance({
        utterance: context.utterance,
        domain: context.domain,
        strictMode: true
      });

      if (!provenanceResult.hasProvenance) {
        reasonCodes.push('TRUTH_MISSING');
        outcome = 'inconclusive';
        prompts.push("I don't have verified information about that.");
      } else if (provenanceResult.requiresVerification) {
        requireVerify = true;
        if (outcome === 'disclose') {
          outcome = 'verify';
        }
      }
    }

    // Step 5: Security Label Check
    if (context.securityLabel) {
      const securityPolicy = this.config.securityPolicies[context.securityLabel];
      
      if (context.securityLabel === 'Ultra' && context.callerId !== 'Self') {
        reasonCodes.push('SECURITY_VIOLATION');
        outcome = 'decline';
      } else if (trustScore < securityPolicy.maxTrustRequired) {
        reasonCodes.push('TRUST_AMBER');
        requireVerify = securityPolicy.requireVerify;
        if (outcome === 'disclose') {
          outcome = requireVerify ? 'verify' : 'partial';
        }
      }
    }

    // Step 6: IPSG (Influence/Risk Assessment)
    if (context.sensitive) {
      const riskAssessment = await this.ipsg.assessRisk({
        context,
        trustScore,
        mkeScore,
        securityLabel: context.securityLabel || 'General'
      });

      if (riskAssessment.riskLevel === 'HIGH') {
        reasonCodes.push('RISK_HIGH');
        outcome = 'throttle';
      } else if (riskAssessment.riskLevel === 'MEDIUM' && outcome === 'disclose') {
        reasonCodes.push('SENSITIVE_CONTENT');
        outcome = 'verify';
        requireVerify = true;
      }
    }

    // Final validation
    if (reasonCodes.length === 0) {
      reasonCodes.push('OK');
    }

    return {
      outcome,
      reasonCodes,
      confidence: this.calculateConfidence(mkeScore, trustScore, reasonCodes),
      thresholds: {
        mkeThreshold: mkeThresholds.disclose,
        trustThreshold,
        applied: {
          mkeScore: Number(mkeScore.toFixed(4)),
          trustScore: Number(trustScore.toFixed(4)),
          trustBand
        }
      },
      prompts: prompts.length > 0 ? prompts : undefined,
      redactions: redactions.length > 0 ? redactions : undefined,
      requireVerify: requireVerify,
      needsVerification: requireVerify
    };
  }

  private calculateConfidence(mkeScore: number, trustScore: number, reasonCodes: ReasonCode[]): number {
    let confidence = 0.5; // Base confidence
    
    // Adjust based on MKE and trust scores
    confidence += (mkeScore * 0.3);
    confidence += (trustScore * 0.3);
    
    // Reduce confidence for problematic reason codes
    const problematicCodes = ['MPL_DENY', 'MKE_LOW', 'TRUST_RED', 'TRUTH_MISSING', 'RISK_HIGH'];
    const problemCount = reasonCodes.filter(code => problematicCodes.includes(code)).length;
    confidence -= (problemCount * 0.15);
    
    return Math.max(0, Math.min(1, confidence));
  }
}

// Convenience function for single evaluations
export async function evaluate(context: SLEContext, config?: Partial<SLEConfig>): Promise<SLEDecision> {
  const sle = new SmartLimitsEngine(config);
  return sle.evaluate(context);
}