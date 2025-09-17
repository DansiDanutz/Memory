# Memory App — Full System Architecture (v1.1)

## 0) Vision & Principles
- Privacy-first, local-first, zero-knowledge sync.
- Explicit consent, region-aware compliance.
- Modular capabilities, user-controlled.
- Smart Limits Engine (SLE) governs **what to say, to whom, and why**.

## 1) High-Level Components
1. **Mobile App (iOS/Android; React Native → Bare)**
   - Capture: Share-to-Memory, Voice Notes, optional Keyboard Toggle (never in secure fields), Screenshot/Clipboard (manual confirm).
   - Call/VoIP via **Memory Number** (virtual) and WebRTC avatar room.
   - On-device ML: Whisper/Whisper-cpp, small NER (ONNX), embeddings (int8).
   - Local encrypted DB: SQLCipher/Libsodium + CRDT (Yjs/Automerge) for conflict-free drafts.
2. **Voice/Video Edge**
   - **Telephony**: Twilio Programmable Voice + Media Streams (consent IVR, call control).
   - **Video**: LiveKit/Jitsi SFU; avatar render with HOLOGRAM + LEGACY watermark.
3. **Backend (Zero-Knowledge Cloud)**
   - Gateway API (stateless, auth+routing only; stores ciphertext blobs).
   - Job Workers: heavy STT batches, diarization, avatar rendering, vector backups.
   - Object Storage (S3-compatible): encrypted blobs only.
   - Event Bus: encrypted audit, usage counters, subscription/credit ledger.
4. **Governance Brain**
   - **SLE**: orchestrates policy (MPL), trust (BLTS), mutual-knowledge (CEMG), provenance truth (KPE), and planning (IPSG).
   - **CRG**: Confidential Reply Guard with risk ladder (S0–S4).
5. **Legacy Subsystem**
   - Legacy Circle (≤5 slots), Shamir secret-sharing, dead-man timer, M-of-N verification, cooling-off period, read-only Legacy Portal.
6. **Billing & Credits**
   - $5/month Pass-Away plan (mandatory for Legacy), credit overlay (1 credit = 1 minute), loyalty boosts, rollover.

## 2) Data Model
### 2.1 Core Entities
- **Person** {id, names[], relation, contacts[], trustProfile, policyScopes}
- **Event** {id, ts, channel, participants[], mediaRefs, transcriptSegments, extractedFacts[], policyLabel, sourceType: 'human'|'avatar'}
- **MDC (Memory Data Card)** per entity/topic
  - header {id, version, labels[General|Secret|Ultra|C2|C3], cryptoContext}
  - profiles {aliases, relation}
  - ledgers[] (e.g., payments, commitments) → link(eventId)
  - threads[] (conversation refs) → link(eventId)
  - tags[]
- **Disclosure Tree** (Domain ▸ Category ▸ Topic) with inheritance and overrides
- **Belief/Knowledge Graph (BKG)**: what each person likely knows (+provenance, confidence)

### 2.2 Security Labels / Compartments
- General, Secret, Ultra-Secret, C2 (User+1), C3 (User+2). Each encrypted with a **Compartment Key**.

### 2.3 Indexes
- Local Vector Index per compartment; optional cloud vector backups (ciphertext).

## 3) Cryptography & Keys
- Master Key derived from passphrase + secure enclave.
- Compartment Keys (GK-General, GK-Secret, GK-Ultra, GK-C2, GK-C3).
- Session Keys per event; audio/transcripts sealed to session key then wrapped to relevant compartment key(s).
- Legacy Keys (`LK_*`) per slot (Spouse, Child1..3, BestFriend) + `LK_FamilyRoom`.

## 4) Ingestion → Understanding → Assignment Pipeline
1. Ingest (share/call/voice note)
2. Transcribe & diarize
3. NER & resolution
4. Extract facts (SVO, amounts, entities)
5. Policy classification (choose compartment)
6. **MDC Updater** (write ledgers/threads to affected MDCs; cross-link event)
7. Embedding & index update

## 5) Smart Limits Engine (SLE)
- **Inputs:** {callerId, utterance, domain, scope, strictTruth?, sensitive?}
- **Order of checks:** MPL (policy) → CEMG (MKE score) → BLTS (trust thresholds by domain) → KPE (Truth-of-Faith) → IPSG (utility/risk) → Outcome.
- **Outcomes:** disclose | partial | redact | probe | verify | divert | decline | throttle | inconclusive.
- **Reason Codes:** MPL_DENY, MKE_LOW, TRUST_RED/AMBER, TRUTH_MISSING, RISK_HIGH, OK.

## 6) Policy Layer (MPL)
- YAML rules + Disclosure Tree inheritance (Domain > Category > Topic; closest wins).
- Redaction fields, verify-before-disclose flags, region constraints.
- Never share Ultra-Secret beyond Self; health defaults Secret unless explicitly raised with verify.

## 7) Trust Scoring (BLTS)
- Beta(α,β) per **member×domain**; recency decay (λ≈0.98/day).
- Evidence: identity pass/fail, knowledge alignment, fishing attempts, weekly approvals/denials, post-hoc redactions.
- Bands: Green≥0.80, Amber 0.55–0.79, Red<0.55. Domain thresholds τ: Finance/Health 0.75; Family 0.6; Memories 0.55; Ultra 0.95.

## 8) Conversational Epistemics (CEMG)
- BKG tracks who knows what, when, and who told whom.
- MKE ∈ [0,1] from features: direct refs, recent conversation, third-party confirmation, utterance specificity, conflict signals.
- Decision Ladder: DL-0 divert → DL-1 probe → DL-2 partial → DL-3 disclose → DL-4 verify then disclose.

## 9) Provenance & Truth (KPE)
- “Truth-of-Faith 100%” mode: only facts with full provenance (event ids, timestamps, diarized speakers); else respond **inconclusive**.
- Query API: whatDoesKnow(A, B, {domain?, asOf?, strictTruth?}).

## 10) Influence Planner (IPSG) — Later Phase
- Goal → beam search with guardrails EDR = MPL ∧ (Trust≥τ) ∧ (MKE≥θ).
- Strategy patterns: reciprocity, coordination, framing, no fabrication, always opt-out.
- Playbooks saved from successful plans.

## 11) CRG — Confidential Reply Guard
- Session Risk Score (identity, channel, sensitivity, context anomalies).
- Safety Ladder S0–S4: Open → Partial → Verify → Decline → Escalate.

## 12) Legacy Mode (CAP 5)
- Slots: Spouse, Child1..3, BestFriend (explicit selection preferred; default inference if unset).
- Pass-Away protocol: inactivity horizon, multi-channel pings, M-of-N verifiers, cooling-off, threshold decrypt → read-only portal.
- HOLOGRAM + LEGACY badges; consent evidence stored.
- Knowledge partition: indexes per recipient; no cross-compartment leakage.
- Subscription: $5/month required; credits = talk minutes; rollover; loyalty boosts; emergency allowance.

## 13) Weekly Consent Curation & Habit Loop
- Candidate Disclosures per transcript → weekly batch review (20–40) + daily micro-prompts (≤6/day, quiet-hour aware).
- Accept → write to MDC(s); Deny → discard and learn; Snooze → re-batch.
- Rules: user automation (e.g., “all groceries → Wife C2”).

## 14) Disclosure Tree & Policy Taxonomy
- Domains (Finance, Health, Family, Work, Memories, Legal).
- Categories inside domains; Topics inside categories.
- Inheritance + overrides; effective policy computed; conflicts flagged.
- Drag-and-drop CDs onto tree for bulk policy application.

## 15) APIs (Selected)
- **SLE**: evaluate(ctx: SLEContext): SLEDecision
- **KPE**: whatDoesKnow(askerId, targetId, {domain?, asOf?, strictTruth?}) => Fact[]
- **BLTS**: getTrust(memberId, domain); updateTrust(memberId, domain, s, f, ts); decayTrust()
- **MPL**: evaluate({domain, scope, callerId}) => {allow, redactions?, requireVerify?}
- **Disclosure Tree**: getEffectivePolicy(nodeId); bulkApply(nodeIds, policy); validate(nodeId)

## 16) OS Constraints & Legal
- iOS/Android: auto-answer/record limited; rely on **Memory Number** with consent IVR. For EU, device call recording not available; keep region flags.
- GDPR/biometrics: cloned voice → explicit consent; add AI disclosure watermarks & audible notices.

## 17) Telemetry & Audit
- Privacy-scrubbed crash logs; encrypted audit events with reason codes; local review UI.
- No third-party analytics for content; opt-in metrics only.

## 18) Deployment Topology
- Mobile client (RN) + native modules.
- Edge: Twilio webhooks (Node/Go), LiveKit SFU.
- API Gateway (stateless), Workers (STT/diarization/avatar), Object store (S3). All payloads ciphertext.
- Keys only on device; no server escrow by default (optional hardware key recovery).

## 19) Testing & Red-Team
- Unit tests per module; replay anonymized transcripts; fishing/contradiction sims.
- Grid search thresholds for MKE/Trust; evaluate FPR/FNR for leaks.

## 20) Product Phases & KPIs
- **Phase 1 (MVP):** DAU, weekly review completion %, disclosure accuracy, user-reported leak rate (target 0), retention.
- **Phase 2 (Legacy):** Legacy Circle activation rate, session minutes, NPS of bereaved users.
- **Phase 3 (Planner):** Goal success rate, credits per successful plan, opt-out rate (target low).

## 21) Build Plan (Condensed)
- RN app shell + local store + STT + MDC + SLE integration.
- Memory Number IVR + consent + transcripts.
- Weekly loop UI + Disclosure Tree Designer.
- Legacy subsystem + avatar + portal.
- Planner/Advice/KPE UIs.

## 22) Future Excellence Enhancements (Manus + Additional Upgrades)
### 22.1 Hybrid Hardware/Software Key Management + MFA
- Secure Enclave/TPM + optional HSM.
- MFA: passphrase + hardware key + biometrics.
- Argon2 KDF with salt.

### 22.2 Decentralized Identity (DID) + Verifiable Credentials (VCs)
- W3C DID per user; relationships as VCs.

### 22.3 Geo-Distributed, Fault-Tolerant Backend
- Multi-region deploy, CockroachDB/Spanner, chaos engineering.

### 22.4 Causal Inference in BLTS
- Bayesian causal networks; counterfactual reasoning; user feedback.

### 22.5 Continuous Adversarial Training for SLE
- RL adversaries probing; continuous updates.

### 22.6 Explainable AI (XAI)
- NL explanations; decision tree visualizations; counterfactuals.

### 22.7 Richer Legacy Mode
- Storytelling, Gifts, Collaboration.

### 22.8 Third-Party AI Marketplace
- SDK + dev portal; certified marketplace.

### 22.9 Memory App for Good Program
- NGO partnerships, research program, ethics council.

### 22.10 Additional User Satisfaction Upgrades
- Adaptive personalization (tone, humor, style).
- Privacy nudges when oversharing detected.
- Full offline mode with later sync.
- Seamless family UX (one-tap onboarding).
- Wellbeing features (grief-support, counselor escalation).
- Gamified Trust Dashboard (streaks, badges).
- Multi-language support.
- Accessibility (voice, screen readers, large fonts).
