// Smart Limits Engine Types aligned with Memory App Architecture

export type SecurityLabel = 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3';
export type Domain = 'Finance' | 'Health' | 'Family' | 'Work' | 'Memories' | 'Legal';
export type TrustBand = 'Green' | 'Amber' | 'Red';
export type SourceType = 'human' | 'avatar';

export interface SLEContext {
  callerId: string;
  utterance: string;
  domain: Domain;
  scope?: string;
  strictTruth?: boolean;
  sensitive?: boolean;
  securityLabel?: SecurityLabel;
  sourceType?: SourceType;
}

export type SLEOutcome = 
  | 'disclose' 
  | 'partial' 
  | 'redact' 
  | 'probe' 
  | 'verify' 
  | 'divert' 
  | 'decline' 
  | 'throttle' 
  | 'inconclusive';

export type ReasonCode = 
  | 'MPL_DENY'
  | 'MKE_LOW' 
  | 'TRUST_RED'
  | 'TRUST_AMBER'
  | 'TRUTH_MISSING'
  | 'RISK_HIGH'
  | 'SENSITIVE_CONTENT'
  | 'SECURITY_VIOLATION'
  | 'OK';

export interface SLEDecision {
  outcome: SLEOutcome;
  reasonCodes: ReasonCode[];
  confidence: number;
  thresholds: {
    mkeThreshold: number;
    trustThreshold: number;
    applied: {
      mkeScore: number;
      trustScore: number;
      trustBand: TrustBand;
    };
  };
  prompts?: string[];
  redactions?: string[];
  requireVerify: boolean;
  needsVerification: boolean;
}

export interface SLEConfig {
  // Domain-specific trust thresholds (τ values from architecture)
  domainTrustThresholds: Record<Domain, number>;
  // MKE decision ladder thresholds
  mkeThresholds: {
    divert: number;    // DL-0
    probe: number;     // DL-1  
    partial: number;   // DL-2
    disclose: number;  // DL-3
    verify: number;    // DL-4
  };
  // Security label restrictions
  securityPolicies: Record<SecurityLabel, {
    maxTrustRequired: number;
    requireVerify: boolean;
    allowExternal: boolean;
  }>;
}

// Default configuration aligned with architecture document
export const DEFAULT_SLE_CONFIG: SLEConfig = {
  domainTrustThresholds: {
    'Finance': 0.75,
    'Health': 0.75, 
    'Family': 0.6,
    'Work': 0.65,
    'Memories': 0.55,
    'Legal': 0.8
  },
  mkeThresholds: {
    divert: 0.2,
    probe: 0.4,
    partial: 0.6,
    disclose: 0.7,
    verify: 0.9
  },
  securityPolicies: {
    'General': { maxTrustRequired: 0.5, requireVerify: false, allowExternal: true },
    'Secret': { maxTrustRequired: 0.75, requireVerify: true, allowExternal: true },
    'Ultra': { maxTrustRequired: 0.95, requireVerify: true, allowExternal: false },
    'C2': { maxTrustRequired: 0.8, requireVerify: true, allowExternal: true },
    'C3': { maxTrustRequired: 0.85, requireVerify: true, allowExternal: true }
  }
};