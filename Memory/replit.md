# MemoApp - Your Personal Memory Guardian

## Overview

MemoApp is a production-ready WhatsApp memory application that serves as your personal AI-powered memory assistant. Built with FastAPI and enterprise features, it provides secure voice-authenticated memory storage and retrieval through WhatsApp.

**Key Features:**
- 🔐 Voice-authenticated memory access with 10-minute session management
- 📊 5-tier security classification (general, chronological, confidential, secret, ultra_secret)
- 🏢 Multi-tenant support with department-based organization
- 👥 Role-Based Access Control (RBAC) with 5 roles
- 📝 Comprehensive audit logging for compliance
- 🔒 Fernet encryption for sensitive memories
- 💬 14 WhatsApp commands for complete memory management
- 📈 Prometheus metrics for monitoring

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Monorepo Structure
The application uses a TypeScript monorepo architecture organized into specialized packages and applications:

**Core Governance Packages:**
- `packages/sle` - Smart Limits Engine: Core orchestration layer that coordinates all other components
- `packages/mpl` - Memory Policy Layer: Implements disclosure tree policies with domain-based inheritance
- `packages/blts` - Bayesian Learning Trust System: Beta distribution-based trust scoring per member and domain
- `packages/cemg` - Conversational Epistemics & Mutual Knowledge Graph: Tracks who knows what information
- `packages/kpe` - Knowledge Provenance Engine: Verifies information sources with "Truth-of-Faith" mode
- `packages/ipsg` - Influence Planning & Strategy Generation: Risk assessment and response planning

**Additional Components:**
- `packages/conversation` - MCP-style conversation protocol with OpenAI integration
- `apps/dev-runner` - Demo application for testing SLE evaluations and conversation flows

### Smart Limits Engine (SLE) Decision Flow
The SLE implements a five-stage evaluation pipeline:

1. **MPL (Policy) Check**: Evaluates disclosure policies by domain, with security label enforcement
2. **CEMG (Mutual Knowledge)**: Estimates what the caller likely already knows
3. **BLTS (Trust Scoring)**: Calculates trust score using Bayesian learning with recency decay
4. **KPE (Provenance)**: Verifies information sources and timestamps in strict-truth mode
5. **IPSG (Risk Assessment)**: Analyzes potential risks and generates response strategies

**Decision Outcomes**: disclose, partial, redact, probe, verify, divert, decline, throttle, inconclusive

### Security Architecture
The system implements a compartmentalized security model with five security labels:
- General: Basic information sharing
- Secret: Elevated protection requiring verification
- Ultra: Highest protection, restricted to self-access only
- C2: User+1 person clearance
- C3: User+2 person clearance

### Data Model
Key entities include Person profiles with trust scores, Events with transcripts and provenance, Memory Data Cards (MDCs) with compartmentalized storage, and a Belief/Knowledge Graph tracking mutual awareness.

## Voice Authentication System (Python Implementation)

### Current Status: ✅ PRODUCTION-READY (September 2025)

**Complete Features:**
- **WhatsApp Cloud API Integration**: Full webhook support with META verification
- **5-Level Security Classification**: AI-powered categorization with automatic encryption for secret tiers
- **Voice Authentication**: Secure voice passphrase verification with challenge questions
- **Enterprise Features**: Multi-tenancy, RBAC, audit logging, department isolation
- **Memory Management**: Store, search, export, backup/restore capabilities
- **Security**: Fernet encryption, session management, permission-based access
- **Monitoring**: Health checks, metrics endpoint, audit trails

**WhatsApp Commands:**
- `/help` - Show available commands
- `/search <query>` - Search memories (supports dept: and tenant: prefixes)
- `/recent [count]` - Show recent memories
- `/stats` - Display memory statistics
- `/delete <id>` - Delete a memory
- `/clear` - Clear session
- `/voice` - Voice enrollment instructions
- `/login` - Login with voice
- `/logout` - Logout
- `/export` - Export memories
- `/backup` - Create backup
- `/restore` - Restore from backup
- `/category <name>` - List memories by category
- `/settings` - View/update settings
- `/profile` - View user profile
- `/whoami` - Show tenant, department, role
- `/audit` - View audit logs (admin only)

**Business Features:**
- **Multi-Tenancy**: Support for multiple organizations with isolated data
- **RBAC**: 5 roles (admin, manager, user, viewer, guest) with 17 permissions
- **Department Isolation**: Memory isolation by department within tenants
- **Audit Logging**: Complete audit trail for compliance and security
- **Cross-Tenant Search**: Admins can search across tenants (with audit trail)
- **Backup & Restore**: Automated backup with 7-day retention

**Architecture:**
- **Framework**: FastAPI with async/await support
- **Storage**: File-based with JSON index for fast retrieval
- **Encryption**: Fernet for secret tiers (secret, ultra_secret)
- **Session**: In-memory store with 10-minute TTL
- **Audit**: JSON Lines format with automatic rotation
- **Deployment**: Docker-ready with health checks and monitoring

### Testing Strategy
Comprehensive test suite with:
- **Acceptance Tests**: Validate all ship gate criteria
- **Integration Tests**: End-to-end user flows
- **Command Tests**: All 17 WhatsApp commands
- **Unit Tests**: Core functionality coverage
- **Test Runner**: Automated testing with coverage reporting

## External Dependencies

### Core Dependencies
- **TypeScript**: Primary development language with strict typing
- **Vitest**: Testing framework for unit and integration tests
- **OpenAI**: Language model integration for conversation capabilities (requires API key)

### Package Management
- **npm workspaces**: Monorepo dependency management
- **Local file dependencies**: Inter-package references using `file:` protocol

### Development Tools
- **TypeScript compiler**: Build system with project references
- **Node.js**: Runtime environment (>=18.0.0 required)
- **npm**: Package manager (>=9.0.0 required)

### Optional Integrations
The architecture supports future integration with:
- Telephony services (Twilio for voice/video)
- Encrypted storage systems (SQLCipher/Libsodium)
- Vector databases for semantic search
- WebRTC for real-time communication
- Cloud object storage for encrypted backups