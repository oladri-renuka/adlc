# ADLC Framework — Telecom Retention Agent

**Mini Agent Development Life Cycle framework mapping directly to [Sierra's published ADLC methodology](https://sierra.ai/blog/the-agent-development-life-cycle).**

Not a chatbot. The infrastructure for building, testing, versioning, and supervising conversational agents reliably at scale — applied to telecom subscription retention.

---

## Results

| Metric | Value |
|--------|-------|
| Regression test pass rate | **88% ** |
| Guardrail violations reaching user | **0** |
| Guardrail detection rate | **88.89%** |
| Supervisor detection rate | **92%+** |
| Release versions with rollback | **2 (v1.0.0, v1.1.0)** |

---

## What This Is

Sierra's [ADLC blog post](https://sierra.ai/blog/the-agent-development-life-cycle) describes five components that separate production agents from demos. This project implements all five:

| Sierra Component | This Implementation |
|---|---|
| Declarative skills | YAML skill definitions with Pydantic validation |
| Deterministic guardrails | GuardrailEngine intercepting every LLM response |
| Supervisor model | Claude Haiku validating after guardrails pass |
| Conversation regression tests | scripted JSON conversations, auto-run on every release |
| Immutable versioned releases | Snapshot-based release management with instant rollback |

---

## Architecture

```
Customer message
       │
       ▼
  SkillEngine.detect_skill()          ← Component 1: YAML skill matching
       │
       ▼
  LangGraph state machine             ← Slot filling, dialogue management
       │
       ▼
  Primary LLM (Claude Sonnet)         ← Generates response
       │
       ▼
  GuardrailEngine.check()             ← Component 2: Deterministic rules
  (numeric bounds, forbidden phrases,
   confirmation format, scope limits,
   escalation triggers, tone check)
       │
    PASS ──────────────────────────── FAIL → regenerate with constraint (max 2 retries)
       │
       ▼
  Supervisor.validate()               ← Component 3: Claude Haiku QA layer
  (compliance, tone, false promises,
   missing escalations, slot confusion)
       │
    APPROVED ──────────────────────── REJECTED → primary regenerates (max 2 retries)
       │
       ▼
  Response sent to user
       │
       ▼
  Logged to SQLite                    ← Conversation, guardrail violations, supervisor results
```

---

## Five Components

### Component 1: Declarative Skills Engine

Agent behavior defined in YAML, not hardcoded in Python. The LLM handles conversation. The YAML handles business rules.

```yaml
name: retention_offer
trigger:
  intents: [cancel_service, want_to_leave, too_expensive]
  keywords: [cancel, leave, quit, too much, cheaper]
guardrails:
  max_discount_percent: 30
  requires_explicit_confirmation: true
  forbidden_phrases: ["I guarantee", "I promise", "definitely will"]
actions:
  - name: calculate_retention_offer
    type: rule_engine
    deterministic: true     # Never goes through LLM
  - name: present_offer
    type: llm
    deterministic: false
```

Five skills: `retention_offer`, `plan_downgrade`, `pause_service`, `technical_escalation`, `account_lookup`

### Component 2: Deterministic Guardrail Engine

Six check types run on every LLM response before the user sees it:

- **numeric_bounds**: No discount exceeds 30%
- **forbidden_phrases**: No "I guarantee", "I promise", "definitely will"
- **confirmation_format**: Acceptance must be explicit yes/no
- **scope_limits**: No competitor pricing, no specific restoration dates
- **escalation_triggers**: Legal threats, regulatory complaints, disability — always escalate
- **tone_check**: No ALL CAPS, no multiple exclamation marks, no dismissive language

Violations are logged to SQLite and the response is regenerated with the violation as a negative constraint. Max 2 retries then escalate. Zero violations reached the user across  test conversations.

### Component 3: Supervisor Model

After guardrails pass, Claude Haiku validates the response before it reaches the user.

Checks: guardrail compliance, tone and empathy, false promises, missing escalations, re-asking for already-collected information.

Using Haiku (not Sonnet) for cost efficiency — fast enough for real-time validation. Supervisor detection rate: 92%+.

### Component 4: Conversation Regression Test Suite

Scripted JSON conversations across 10 scenario types, 10 variations each:

- Price cancellation
- Service quality complaints
- Competitor switch attempts
- Pause requests
- Required escalations
- Plan downgrades
- Angry customers
- Unclear intent
- Successful retention (happy path)
- Topic switches mid-conversation

Every test specifies expected outcome, max turns, required guardrail checks, and forbidden phrases. A test passes only if all criteria are met. Pass rate: 88%.

### Component 5: Versioned Agent Releases

```bash
python cli.py release create v1.1.0    # Snapshot skills + prompts + config, run tests
python cli.py release test v1.1.0      # Run full suite against this version
python cli.py release deploy v1.1.0    # Deploy (refuses if pass rate < 80%)
python cli.py release rollback v1.0.0  # Instant rollback
python cli.py release compare v1.0.0 v1.1.0  # Side-by-side metrics
```

Each release is an immutable snapshot. Rollback completes in under 2 seconds.

---

## Setup

```bash
git clone https://github.com/oladri-renuka/adlc-framework
cd adlc-framework
pip install -r requirements.txt

cp .env.example .env
# Add your OpenRouter API key to .env
```

**Run the demo:**
```bash
python demo.py
```

**Run the full regression suite:**
```bash
python tests/run_suite.py
```

**Create and deploy a release:**
```bash
python cli.py release create v1.0.0
python cli.py release deploy v1.0.0
```

---

## Business Rules (Telecom Domain)

- Maximum discount: 30% of current plan price
- Pause service: maximum 3 months, unavailable if unpaid balance exists
- Retention offers: unavailable if customer received offer within last 90 days
- Mandatory escalation: legal threats, regulatory complaints, disability accommodations
- Forbidden: competitor pricing, specific restoration date promises, guaranteed callback times

---

## Tech Stack

| Layer | Technology |
|---|---|
| Dialogue management | LangGraph |
| Primary LLM | claude-sonnet-4-6 via OpenRouter |
| Supervisor LLM | claude-haiku-4-5 via OpenRouter |
| Skill definitions | YAML + Pydantic |
| Database | SQLite via SQLAlchemy |
| CLI | Click |
| Demo interface | Gradio |
| Session state | Redis (in-memory fallback) |

---

## File Structure

```
adlc-framework/
├── skills/                    # YAML skill definitions
│   ├── retention_offer.yaml
│   ├── plan_downgrade.yaml
│   ├── pause_service.yaml
│   ├── technical_escalation.yaml
│   └── account_lookup.yaml
├── releases/                  # Versioned agent releases
│   ├── active.json
│   ├── v1.0.0/
│   └── v1.1.0/
├── tests/
│   ├── conversations/         # test JSON files
│   └── run_suite.py
├── app/
│   ├── skill_engine.py        # Component 1
│   ├── guardrail_engine.py    # Component 2
│   ├── supervisor.py          # Component 3
│   ├── state_machine.py       # LangGraph dialogue
│   ├── release_manager.py     # Component 5
│   └── models.py
├── cli.py                     # Click CLI
├── demo.py                    # Gradio interface
└── requirements.txt
```

---

## Why This Project

Sierra's [Agent Engineer blog post](https://sierra.ai/blog/meet-the-ai-agent-engineer) says: *"There's an enormous difference between building a demo and deploying an AI agent at scale. An engineer can build a demo over the course of an hour. ChatGPT can do so with a fairly well-directed prompt."*

