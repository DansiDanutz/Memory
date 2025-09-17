# Memory App - TypeScript Monorepo

Privacy-first AI memory system with Smart Limits Engine (SLE) that governs what to say, to whom, and why.

## 🏗️ Architecture

This monorepo implements the core governance brain for the Memory App with MCP-style conversation capabilities:

### Packages

- **`packages/sle`** - Smart Limits Engine core evaluation logic
- **`packages/mpl`** - Memory Policy Layer (Disclosure Tree)  
- **`packages/blts`** - Bayesian Learning Trust System
- **`packages/cemg`** - Conversational Epistemics & Mutual Knowledge Graph
- **`packages/kpe`** - Knowledge Provenance Engine
- **`packages/ipsg`** - Influence Planning & Strategy Generation
- **`packages/conversation`** - MCP-style conversation protocol with OpenAI integration

### Apps

- **`apps/dev-runner`** - Demo runner to test SLE evaluations and conversation interactions

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Build all packages
npm run build

# Run tests
npm run test

# Run demo
npm run dev
```

## 🔑 Configuration

For full conversation features, set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 🧪 Demo Scenarios

The demo runner tests various scenarios:

1. **Grandmother asking about family finances** - Tests trust scoring and domain policies
2. **Spouse discussing family memories** - Tests mutual knowledge estimation
3. **Stranger requesting sensitive health info** - Tests security boundaries
4. **Ultra-Secret information requests** - Tests security label enforcement
5. **Truth-of-Faith strict mode** - Tests provenance verification

## 🧠 Smart Limits Engine Flow

The SLE evaluation follows this decision flow:

1. **MPL** (Policy) → Check disclosure permissions
2. **CEMG** (Mutual Knowledge) → Estimate what caller knows  
3. **BLTS** (Trust) → Evaluate relationship trust
4. **KPE** (Provenance) → Verify information sources
5. **IPSG** (Risk) → Assess disclosure risks

### Outcomes

- `disclose` - Share information freely
- `partial` - Share limited information
- `redact` - Remove sensitive parts
- `probe` - Ask clarifying questions
- `verify` - Require additional confirmation
- `divert` - Redirect conversation
- `decline` - Refuse to answer
- `throttle` - Limit response detail
- `inconclusive` - Cannot verify information

## 🗣️ Conversation Engine

The conversation system provides:

- **MCP-style protocol** for language interactions
- **SLE-integrated responses** respecting privacy boundaries
- **Voice interaction support** for Memory Number calls
- **Legacy mode** for bereaved family members
- **Multi-session management** with conversation history

## 🧪 Testing

```bash
# Run all tests
npm run test

# Watch mode
npm run test:watch
```

Tests cover:
- SLE decision logic for various scenarios
- Trust scoring with different caller relationships
- Policy enforcement across security labels
- Mutual knowledge estimation accuracy

## 📦 Development

Each package can be built independently:

```bash
# Build specific package
cd packages/sle && npm run build

# Watch mode for development
cd packages/sle && npm run dev
```

## 🔒 Security & Privacy

- **Zero-knowledge architecture** - No plaintext storage
- **Compartmentalized encryption** by security labels
- **Trust-based disclosure** with Beta distribution scoring
- **Provenance tracking** for Truth-of-Faith verification
- **Explicit consent** required for sensitive operations

## 🔧 Integration

This monorepo is designed to integrate with:

- **Mobile App** (React Native) for data capture
- **Backend API** (Node.js) for zero-knowledge cloud storage  
- **Voice/Video Edge** (Twilio, LiveKit) for Memory Number calls
- **Legacy Portal** for bereaved family access

## 📝 Configuration

Customize SLE behavior via configuration objects:

```typescript
import { SmartLimitsEngine } from '@memory-app/sle';

const sle = new SmartLimitsEngine({
  domainTrustThresholds: {
    'Finance': 0.8,  // Higher threshold for finance
    'Family': 0.6,   // Lower threshold for family
    // ...
  },
  mkeThresholds: {
    probe: 0.4,      // When to ask clarifying questions
    disclose: 0.7,   // When to share information
    // ...
  }
});
```

## 🤝 Contributing

1. Follow TypeScript strict mode
2. Add tests for new functionality
3. Update type definitions
4. Run full test suite before submitting

## 📄 License

Private - Memory App Project