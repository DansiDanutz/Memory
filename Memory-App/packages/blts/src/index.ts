// Bayesian Learning Trust System (BLTS) - Stub Implementation
// Beta(α,β) per member×domain with recency decay

export type TrustBand = 'Green' | 'Amber' | 'Red';

export interface TrustProfile {
  alpha: number;  // Beta distribution α (successes)
  beta: number;   // Beta distribution β (failures)
  lastUpdate: number;
  domain: string;
}

export class BLTS {
  // Stub trust store - in real implementation this would be persistent
  private trustStore: Map<string, Map<string, TrustProfile>> = new Map();

  constructor() {
    // Initialize with some mock data
    this.initializeMockData();
  }

  private initializeMockData() {
    // Grandmother - high trust in family, medium in finance
    this.setTrustProfile('grandmother', 'Family', { alpha: 20, beta: 2, lastUpdate: Date.now(), domain: 'Family' });
    this.setTrustProfile('grandmother', 'Finance', { alpha: 8, beta: 4, lastUpdate: Date.now(), domain: 'Finance' });
    
    // Spouse - high trust across most domains
    this.setTrustProfile('spouse', 'Family', { alpha: 25, beta: 1, lastUpdate: Date.now(), domain: 'Family' });
    this.setTrustProfile('spouse', 'Finance', { alpha: 15, beta: 2, lastUpdate: Date.now(), domain: 'Finance' });
    this.setTrustProfile('spouse', 'Health', { alpha: 18, beta: 2, lastUpdate: Date.now(), domain: 'Health' });
    
    // Stranger - low trust
    this.setTrustProfile('stranger', 'Family', { alpha: 1, beta: 10, lastUpdate: Date.now(), domain: 'Family' });
    this.setTrustProfile('stranger', 'Finance', { alpha: 1, beta: 15, lastUpdate: Date.now(), domain: 'Finance' });
  }

  private setTrustProfile(memberId: string, domain: string, profile: TrustProfile) {
    if (!this.trustStore.has(memberId)) {
      this.trustStore.set(memberId, new Map());
    }
    this.trustStore.get(memberId)!.set(domain, profile);
  }

  async getTrust(memberId: string, domain: string): Promise<number> {
    const memberProfiles = this.trustStore.get(memberId);
    if (!memberProfiles) {
      return 0.1; // Low default trust for unknown members
    }

    const profile = memberProfiles.get(domain);
    if (!profile) {
      return 0.3; // Medium-low default for unknown domain
    }

    // Apply recency decay (λ≈0.98/day from architecture)
    const daysSinceUpdate = (Date.now() - profile.lastUpdate) / (1000 * 60 * 60 * 24);
    const decayFactor = Math.pow(0.98, daysSinceUpdate);

    // Beta distribution mean: α/(α+β)
    const baseTrust = profile.alpha / (profile.alpha + profile.beta);
    
    return Math.max(0, Math.min(1, baseTrust * decayFactor));
  }

  getTrustBand(trustScore: number): TrustBand {
    // Bands from architecture: Green≥0.80, Amber 0.55–0.79, Red<0.55
    if (trustScore >= 0.80) return 'Green';
    if (trustScore >= 0.55) return 'Amber';
    return 'Red';
  }

  async updateTrust(memberId: string, domain: string, success: boolean, failure: boolean, timestamp: number = Date.now()): Promise<void> {
    const memberProfiles = this.trustStore.get(memberId) || new Map();
    const currentProfile = memberProfiles.get(domain) || { 
      alpha: 1, 
      beta: 1, 
      lastUpdate: timestamp, 
      domain 
    };

    // Update Beta parameters
    if (success) currentProfile.alpha += 1;
    if (failure) currentProfile.beta += 1;
    currentProfile.lastUpdate = timestamp;

    memberProfiles.set(domain, currentProfile);
    this.trustStore.set(memberId, memberProfiles);
  }

  async decayTrust(): Promise<void> {
    // Apply daily decay to all profiles
    const now = Date.now();
    for (const [memberId, profiles] of this.trustStore.entries()) {
      for (const [domain, profile] of profiles.entries()) {
        const daysSinceUpdate = (now - profile.lastUpdate) / (1000 * 60 * 60 * 24);
        if (daysSinceUpdate > 0) {
          // Decay by reducing alpha/beta slightly to reduce certainty over time
          profile.alpha = Math.max(1, profile.alpha * Math.pow(0.99, daysSinceUpdate));
          profile.beta = Math.max(1, profile.beta * Math.pow(0.99, daysSinceUpdate));
        }
      }
    }
  }
}