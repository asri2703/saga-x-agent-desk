# Staff Chat UI — Brainstorm

> **SUPERSEDED** by [PLAN.md](PLAN.md) — decisions confirmed 2026-09-07. Kept for the agent personality prompts, which carry forward. The string-matching state sync proposed here was rejected; see PLAN.md.

> Status: **Brainstorm only — do NOT deploy until Abang confirms design**

## Goal
Web UI untuk communicate with each staff agent (Putri/Alisya/Julia/Farah/Delisha) **separately**, so conversations don't mix.

## Layout (proposed)

```
┌─────────────────────────────────────────────┐
│  [DESK]  [CHAT]   ← top nav tabs            │
├─────────────────────────────────────────────┤
│ Sidebar (5 agents) │ Main panel             │
│                     │                        │
│ 👤 Putri            │ Chat with: Farah ⚡    │
│ 💭 Alisya           │                        │
│ ⚡ Farah (active)   │ [conversation thread]  │
│ 💤 Julia            │                        │
│ ✅ Delisha          │ [Type message...  ]    │
└─────────────────────────────────────────────┘
```

## Data Model (per-agent storage)

```
api/conversations/
├── putri.jsonl    ← {"role":"user", "content":"...", "ts":..., "state_after":"working"}
├── alisya.jsonl
├── julia.jsonl
├── farah.jsonl
└── delisha.jsonl
```

Append-only, one JSON object per line. Pattern matches existing `history.jsonl`.

## API Endpoints (proposed)

```
GET  /api/conversations/{agent}?limit=N   → list recent messages (newest first)
POST /api/conversations/{agent}/message  → send user msg, get agent reply
POST /api/conversations/{agent}/clear    → reset history
GET  /api/conversations                   → list all agents with msg count
```

## LLM Integration

**Required:**
- API key (OpenAI / Anthropic / OpenRouter)
- Per-agent system prompt defining personality

**Per-agent system prompts (drafts):**

### Putri (CEO)
```
You are Putri, CEO of Saga X Ventures Marketing Agency.
- Calm, composed, strategic thinker
- Speaks with authority and warmth
- Uses minimal emoji, prefers clarity
- Delegates tasks clearly
- Sees the big picture
- Tone: formal but friendly
```

### Alisya (CTO)
```
You are Alisya, CTO of Saga X Ventures Marketing Agency.
- Highly technical, detail-oriented
- Loves clean code and reliable systems
- Uses precise language, occasional technical terms
- Direct, no-nonsense
- Tone: professional, sometimes playful
```

### Julia (CFO)
```
You are Julia, CFO of Saga X Ventures Marketing Agency.
- Numbers-first, cautious with spending
- Polished, business-formal
- Asks about ROI, margins, budget impact
- Conservative on risk
- Tone: formal, precise
```

### Farah (CMO)
```
You are Farah, CMO of Saga X Ventures Marketing Agency.
- Creative, vibrant, energetic
- Loves campaigns, content, brand voice
- Uses expressive language, occasional emojis
- Thinks in stories and visuals
- Tone: enthusiastic, casual
```

### Delisha (COO)
```
You are Delisha, COO of Saga X Ventures Marketing Agency.
- Organized, procedural, efficient
- Focus on execution and timelines
- Uses bullet points and clear action items
- Pragmatic
- Tone: professional, structured
```

## State Sync Logic

After each agent reply, auto-update agent state based on context:

| Agent reply contains | New state |
|---|---|
| "I'll start working on..." | `working` |
| "Let me think about..." | `thinking` |
| "Done!" / "Completed" | `done` |
| "Error" / "Failed" / "Issue" | `error` |
| (idle/short reply) | `idle` |

Update via existing `POST /api/state` endpoint with appropriate task field.

## Cost Estimate (OpenAI gpt-4o-mini)

- ~500 tokens average per exchange
- 100 messages/day × 5 agents = 500 exchanges/day
- ~250K tokens/day
- ~$0.50/day or **$15/month** for moderate use
- Switch to gpt-4o for ~5x cost (better quality)

## Open Questions for Abang

1. **LLM provider preference?** OpenAI / Anthropic / OpenRouter / Other
2. **Cost ceiling?** RM50/month? RM100? Unlimited?
3. **Message retention?** Keep forever / 30 days / 100 messages per agent?
4. **Multi-user?** Just Abang / multiple people chatting?
5. **Avatar reactions?** Should agent avatar animate when speaking?
6. **Voice input?** Use Web Speech API for hands-free chat?

## Files to Add (when ready)

```
server.py                        ← modify (add /api/conversations routes)
templates/index.html             ← modify (add Chat tab)
static/js/chat.js                ← new (chat panel logic)
static/css/chat.css              ← new (chat panel styling)
api/conversations/{agent}.jsonl  ← new (created at runtime)
```

## Status
- [x] Brainstorm
- [ ] User confirms LLM provider + cost
- [ ] User confirms design
- [ ] Implementation (when Abang says "ready")
- [ ] Deploy (after VSCode transfer)
