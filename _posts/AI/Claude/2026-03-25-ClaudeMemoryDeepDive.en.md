---
title: "Deep Dive into Claude's Memory System — Auto Memory, Auto Dream, and Sleep-time Compute"
lang: en
date: 2026-03-25 11:00:00 +0900
categories: [AI, Claude]
tags: [Claude, Claude Code, Memory, Auto Memory, Auto Dream, Sleep-time Compute, LLM, AI Agent, CLAUDE.md, Memory Architecture]

difficulty: advanced
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeMemoryAndCodeSkills/
  - /posts/ClaudeCodeInsights/
tldr:
  - "Claude Code's memory has evolved into three stages — CLAUDE.md (explicit rules) + Auto Memory (automatic learning) + Auto Dream (sleep consolidation) — mimicking the human 'write → sleep → organize → remember' cycle"
  - "Auto Dream is built on the theoretical foundation of the Sleep-time Compute paper (2025) — pre-computing before user queries can reduce test-time computation by approximately 5x"
  - "Recent research (2025–2026) classifies agent memory into Factual, Experiential, and Working memory, managed through a Formation → Evolution → Retrieval lifecycle"
---

## Introduction

The ability of AI agents to **learn and remember long-term** beyond a single conversation is a central topic of AI research in 2025–2026. Claude Code is one of the most aggressively experimenting products in this space, and the recently discovered unreleased feature **Auto Dream** clearly shows this direction.

This article dissects Claude's memory system along three axes:

1. **Product level**: Claude Code's memory architecture (CLAUDE.md → Auto Memory → Auto Dream)
2. **Theoretical level**: The "pre-computation during sleep" paradigm from the Sleep-time Compute paper
3. **Research level**: Agent memory taxonomies and latest survey papers from 2025–2026

---

## 1. The Complete Picture of Claude Code's Memory Architecture

### 1-1. Three-Layer Memory System

Claude Code's memory is divided into three layers based on **who writes it** and **when it loads**.

| Layer | Author | Content | Loading | Scope |
|-------|--------|---------|---------|-------|
| **CLAUDE.md** | User | Explicit rules & conventions | Every session start (full) | Project/User/Org |
| **Auto Memory** | Claude | Learned patterns & preferences | Every session start (200 lines) | Per git repository |
| **Auto Dream** | Claude (background) | Consolidated memories | When conditions are met | Per git repository |

#### CLAUDE.md — Declarative Rule Hierarchy

CLAUDE.md is a project-level instruction file. Narrower scope (project) takes precedence over broader scope (organization).

```
Priority (high → low):
1. Managed Policy — /Library/Application Support/ClaudeCode/CLAUDE.md (IT admin)
2. Project       — ./CLAUDE.md or ./.claude/CLAUDE.md (team shared)
3. User          — ~/.claude/CLAUDE.md (personal global)
```

**Requirements for effective CLAUDE.md:**
- Rule compliance rate is **92%+ under 200 lines**, dropping to 71% beyond 400 lines
- Verifiable instructions ("use 2-space indentation") work better than vague ones ("format code nicely")
- Modularize with `.claude/rules/` directory for conditional loading via glob patterns

#### Auto Memory — Notes Claude Writes for Itself

Auto Memory automatically records patterns Claude discovers during sessions, without the user writing anything.

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Index (200 lines loaded per session)
├── debugging.md       # Debugging patterns
├── api-conventions.md # API design decisions
└── ...                # Claude creates freely
```

**How it works:**
1. First 200 lines of `MEMORY.md` are injected into context at session start
2. Detects user corrections, preferences, and recurring patterns during conversation
3. Selectively saves based on "Will this be useful in a future conversation?"
4. Detailed content goes to topic files, `MEMORY.md` stays as an index only

### 1-2. The Fundamental Problem with Auto Memory

Auto Memory is powerful, but **descends into chaos over time.**

After 20+ sessions:
- **Contradictory entries** accumulate ("use pnpm" vs "use npm")
- **Relative dates** lose meaning ("bug fixed yesterday" from 3 months ago)
- **Transient notes and essential learnings** are stored at the same level
- **Priority competition** within the 200-line limit

This isn't a simple implementation bug — it's the structural limitation of a **write-only system that never consolidates**.

---

## 2. Auto Dream — AI That "Organizes Memories While Sleeping"

### 2-1. How It Was Discovered

Auto Dream was discovered in March 2026 by Japanese developer Akari on Zenn, found in Claude Code's `/memory` command. It appears in the UI but cannot be activated — controlled by a server-side feature flag.

```
Codename: tengu_onyx_plover
Default settings:
  enabled: false
  minHours: 24        # Minimum 24-hour interval
  minSessions: 5      # Runs after 5 sessions accumulated
```

This dual-gate design is intentional — it doesn't trigger for light usage, only running periodic consolidation for active development projects.

### 2-2. Auto Dream's Four-Phase Process

Auto Dream is analogous to **human REM sleep**. Information collected while awake (sessions) is organized and consolidated while sleeping (background).

**Phase 1 — Orientation**

Scans the memory directory and assesses the current state — which topic files exist, the current size of `MEMORY.md`, and how much time has elapsed since the last consolidation.

**Phase 2 — Gather Signal**

Selectively extracts important information from session transcripts. Instead of reading all files, it performs **narrow grep searches**:
- User corrections ("No, not that...")
- Explicit save commands ("Remember this")
- Recurring topics and patterns
- Important technical decisions

**Phase 3 — Consolidation**

Merges new information into existing files while:
- Converting relative dates ("yesterday") to absolute dates ("2026-03-24")
- Keeping only the latest among contradictory facts
- Removing outdated, no longer valid memories
- Merging duplicate entries into one

**Phase 4 — Prune and Index**

Updates the `MEMORY.md` index to stay under 200 lines.

### 2-3. Auto Memory + Auto Dream = Complete Memory

```
  Auto Memory (While Awake)            Auto Dream (While Sleeping)
  ┌─────────────────────┐         ┌─────────────────────┐
  │  Collect experiences │         │  Extract signals     │
  │  Detect patterns     │  ───▶   │  Resolve conflicts   │
  │  Write notes         │         │  Consolidate/Organize│
  │  Split topic files   │         │  Update index        │
  └─────────────────────┘         └─────────────────────┘
           ↑                                │
           └────────────────────────────────┘
                  Reflected in next session
```

This cycle directly mimics the human **"experience → sleep → memory strengthening"** pattern. In neuroscience, the process where the hippocampus replays daytime experiences during sleep and transfers them to the neocortex is called **memory consolidation** — Auto Dream plays exactly this role.

### 2-4. Why Hasn't It Been Released Yet?

While technically ready for immediate release, three business decisions remain:

1. **Cost**: A sub-agent consumes tokens in the background without user request
2. **Transparency**: Trust issues around restructuring memory without user awareness
3. **Defaults**: opt-in vs opt-out — what's the right default behavior?

---

## 3. Theoretical Foundation — Sleep-time Compute

### 3-1. Paper Overview

The theoretical basis for Auto Dream is the **"Sleep-time Compute: Beyond Inference Scaling at Test-time"** paper published in April 2025.

> **Authors**: Kevin Lin, Charlie Snell, Yu Wang, Charles Packer, Sarah Wooders, Ion Stoica, Joseph E. Gonzalez
> **arXiv**: [2504.13171](https://arxiv.org/abs/2504.13171)
> **Core idea**: Pre-computing **before** the user asks questions can drastically reduce computation needed during actual inference.

![Sleep-time Compute Concept](/assets/img/post/AI/memory-deep-dive/sleep-time-concept.png)
_Figure 1: Sleep-time compute pre-processes the original context, performing additional computations that may be useful for future queries. (Lin et al., 2025)_

### 3-2. Key Results

The paper demonstrates impressive efficiency improvements on two modified reasoning tasks (Stateful GSM-Symbolic, Stateful AIME).

![Sleep-time vs Test-time accuracy tradeoff](/assets/img/post/AI/memory-deep-dive/sleep-time-accuracy.png)
_Figure 3: Test-time compute vs. accuracy tradeoff on Stateful GSM-Symbolic. The shaded area shows where sleep-time compute improves the Pareto frontier._

**Key figures:**
- **~5x reduction in test-time compute**: Reduces inference computation needed for the same accuracy to about 1/5
- **Up to 13% accuracy improvement**: Scaling sleep-time compute achieves up to 13 percentage points higher accuracy
- **2.5x reduction in average cost per query**: Sharing context across multiple queries reduces costs

![Cost reduction through query sharing](/assets/img/post/AI/memory-deep-dive/sleep-time-amortize.png)
_Figure 9: On Multi-Query GSM-Symbolic, the cost-accuracy Pareto improves as the number of questions per context increases._

### 3-3. Correlation Between Predictability and Effectiveness

A particularly interesting finding is that **the more predictable the user's question is from context, the greater the effect of sleep-time compute**.

![Predictability and sleep-time effect](/assets/img/post/AI/memory-deep-dive/sleep-time-predictability.png)
_Figure 10: As question predictability increases, the performance gap between sleep-time compute and standard inference widens._

The implications for Auto Dream are clear:

- Recurring patterns in development projects (build commands, coding style, architecture decisions) have **high predictability**
- Therefore, pre-organizing these patterns allows Claude to generate more accurate responses with fewer tokens in the next session
- Auto Dream is essentially **sleep-time compute specialized for development context**

### 3-4. Real-World Software Engineering Application

The paper also validated on SWE-Features, a real software engineering task.

![SWE-Features results](/assets/img/post/AI/memory-deep-dive/sleep-time-swe.png)
_Figure 11: On SWE-Features, sleep-time compute shows higher F1 scores than the standard approach at lower test-time budgets._

---

## 4. Academic Context — The Current State of Agent Memory Research

Claude's memory system sits within a broader academic research stream. Let's understand this context through key survey papers published in 2025–2026.

### 4-1. Mapping Human Memory → AI Memory

**"From Human Memory to AI Memory"** (Wu et al., 2025) proposed a framework mapping human memory taxonomies to AI memory systems.

![Parallels between human and AI memory](/assets/img/post/AI/memory-deep-dive/human-ai-memory.png)
_Figure 1: Correspondence between human memory (sensory, working, explicit/implicit) and LLM-based AI system memory. (Wu et al., 2025)_

This paper classifies memory using **3 dimensions (object, form, time) and 8 quadrants**:

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Object** | Whose memory is it? | Individual vs. collective |
| **Form** | How is it stored? | Text, vector, parameter |
| **Time** | How long does it persist? | Short-term vs. long-term |

Mapping to Claude Code:
- **CLAUDE.md** = Explicit long-term memory (user-declared rules)
- **Auto Memory** = Implicit long-term memory (auto-extracted from experience)
- **Context window** = Working memory (current session)
- **Auto Dream** = Memory consolidation (sleep-time organization)

### 4-2. Memory Taxonomy for the Age of AI Agents

**"Memory in the Age of AI Agents"** (Hu, Liu et al., 2025/2026) is a large-scale survey with 47 authors, proposing a new taxonomy that goes beyond simple "long-term/short-term memory" classification.

> **arXiv**: [2512.13564](https://arxiv.org/abs/2512.13564) (December 2025, v2: January 2026)

#### Agent Memory vs. Related Concepts

The paper first distinguishes agent memory from LLM memory, RAG, and context engineering.

![Agent memory concept comparison](/assets/img/post/AI/memory-deep-dive/agent-memory-concept.png)
_Figure 1: Conceptual comparison of Agent Memory with LLM memory, RAG, and context engineering. (Hu et al., 2025)_

#### Forms Dimension — Physical Structure of Memory

The physical forms of agent memory are classified into three types.

![Memory form comparison](/assets/img/post/AI/memory-deep-dive/agent-memory-forms.png)
_Figure 4: Comparison of three forms — token-level, parametric, and latent memory._

**Token-level memory** is the most intuitive form, storing information as text tokens. It's further subdivided by topological complexity:

![Topological classification of token-level memory](/assets/img/post/AI/memory-deep-dive/agent-memory-token-level.png)
_Figure 2: Topological classification of token-level memory — flat (1D), planar (2D graph/tree), hierarchical (3D multi-layer)._

| Form | Structure | Example | Claude Code Mapping |
|------|-----------|---------|-------------------|
| **Flat (1D)** | Linear sequence | Simple text log | `MEMORY.md` entry listing |
| **Planar (2D)** | Tree/Graph | Knowledge graph | Cross-references between topic files |
| **Hierarchical (3D)** | Multi-layer | Pyramid memory | `MEMORY.md` → topic file hierarchy |

**Parametric memory** encodes information in model weights themselves. Fine-tuning and LoRA are representative examples. Claude Code does not use this.

**Latent memory** stores information in hidden states or KV caches. Anthropic's prompt caching is close to this category.

#### Functions Dimension — Cognitive Roles of Memory

![Functional taxonomy](/assets/img/post/AI/memory-deep-dive/agent-memory-taxonomy.png)
_Figure 6: Functional taxonomy of agent memory — Factual, Experiential, and Working memory._

**Factual Memory**

The agent's declarative knowledge base, divided into two subtypes:
- **User Factual Memory**: Information for maintaining consistency in user interactions ("This project uses pnpm")
- **Environment Factual Memory**: Ensuring consistency with external world knowledge ("This API was deprecated in Node.js 20")

In Claude Code, **CLAUDE.md** is the primary store for factual memory.

**Experiential Memory**

Learnings extracted from past experience. Three subtypes:
- **Case-based**: Records of past episodes ("Last build error was resolved this way")
- **Strategy-based**: Learning of reasoning patterns ("In this project, always run type checks first")
- **Skill-based**: Procedural capabilities ("Test → Build → Deploy pipeline")

In Claude Code, **Auto Memory** handles experiential memory.

**Working Memory**

Capacity-limited active context that maintains the state of ongoing tasks in the current session.

In Claude Code, the **context window** itself is working memory, and the 200-line limit of `MEMORY.md` is reminiscent of the human working memory capacity limit (Miller's 7±2 law).

#### Dynamics Dimension — Memory Lifecycle

![Memory lifecycle](/assets/img/post/AI/memory-deep-dive/agent-memory-lifecycle.png)
_Figure 8: Agent memory lifecycle — Formation, Evolution, Retrieval._

| Stage | Description | Claude Code Mapping |
|-------|-------------|-------------------|
| **Formation** | Writing new information to memory | Auto Memory detects and saves patterns during sessions |
| **Evolution** | Updating, transforming, deleting existing memory | Auto Dream resolves contradictions, consolidates, refines |
| **Retrieval** | Accessing memory at the needed moment | 200 lines loaded at session start + on-demand topic file reading |

![Memory evolution process](/assets/img/post/AI/memory-deep-dive/agent-memory-evolution.png)
_Figure 7: Detailed mechanisms of memory evolution — update, reinforcement, forgetting, restructuring._

### 4-3. The Write–Manage–Read Loop

**"Memory for Autonomous LLM Agents"** (2026) formalized agent memory as a **Write–Manage–Read loop**.

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Write   │───▶│  Manage  │───▶│   Read   │
│ (Record) │    │ (Manage) │    │(Retrieve)│
└──────────┘    └──────────┘    └──────────┘
     ↑                                │
     └────────────────────────────────┘
              Feedback Loop
```

Applying this framework to Claude Code:

| Stage | Implementation | Owner |
|-------|---------------|-------|
| **Write** | Recording to memory files during sessions | Auto Memory |
| **Manage** | Periodic consolidation and refinement | Auto Dream |
| **Read** | Loading 200 lines at session start + accessing topic files on demand | Claude Code Runtime |

---

## 5. Claude's Memory in a Broader Context

### 5-1. Chat Memory vs Claude Code Memory

Claude's memory system provides different layers depending on user type.

| Layer | Target | Mechanism | Consolidation Cycle |
|-------|--------|-----------|-------------------|
| **Chat Memory** | All Claude users | Auto-extraction from conversations (Memory Synthesis) | ~24 hours |
| **CLAUDE.md + Auto Memory** | Claude Code developers | Explicit rules + automatic learning | Manual / Auto Dream |
| **API Memory Tool** | App builders | Programmatic CRUD | Per app logic |

Chat Memory is the simplest form, using **extractive summarization** that extracts long-term useful information from conversations approximately every 24 hours. Claude Code's Auto Memory + Auto Dream combination is a far more sophisticated evolution of this.

### 5-2. Three Layers of Infrastructure Scheduling

Auto Dream's execution infrastructure is also evolving in three stages:

| Layer | Scope | Persistence | Example |
|-------|-------|-------------|---------|
| **CLI `/loop`** | Active session only | Dies on session end | `loop 10m /simplify` |
| **Desktop Scheduled Tasks** | Local machine persistent | Dies on machine shutdown | crontab-based |
| **Cloud Scheduled Tasks** | Anthropic infrastructure | Always running | Serverless execution |

When Auto Dream moves to Cloud Scheduled Tasks, memory consolidation can proceed **even when the user's computer is off**. This aligns with Anthropic's $100M investment in the Claude Partner Network in March 2026.

### 5-3. Competitive Landscape

| Product | Memory Form | Consolidation | Developer Integration |
|---------|-------------|--------------|---------------------|
| **Claude Code** | File-based (CLAUDE.md + MEMORY.md) | Auto Dream (upcoming) | Per git repository |
| **ChatGPT** | Server-side key-value | Auto summary | Limited |
| **GitHub Copilot** | `.github/copilot-instructions.md` | None | Per repository |
| **Cursor** | `.cursorrules` | None | Per project |

Claude Code's differentiator is the **existence of the consolidation phase (Auto Dream)**. While other tools offer "write-only" memory, Claude Code aims to implement the complete cycle of "write, sleep, organize, and remember."

---

## 6. Practical: Effective Memory Management Strategies

### 6-1. CLAUDE.md Writing Principles

```markdown
# Good: Specific and verifiable
- Use 2-space indentation
- Run `npm test` before committing
- API handlers go in `src/api/handlers/`

# Bad: Vague and unverifiable
- Write clean code
- Test properly
- Keep files organized
```

### 6-2. Auto Memory Tips

1. **Check regularly with `/memory`**: Periodically review what Claude remembers
2. **Fix contradictions immediately**: Say "that's no longer correct" and Claude will update
3. **Encourage topic file splitting beyond 200 lines**: Request "please organize the memory"
4. **Watch for sensitive information**: Ensure API keys and passwords aren't stored

### 6-3. Preparing for Auto Dream

When Auto Dream officially launches, you can expect:

- **Automatic conflict resolution**: Contradictory records for the same setting consolidated to the latest
- **Relative date conversion**: "yesterday" automatically converted to absolute dates
- **Priority-based cleanup**: Recurring patterns weighted higher than transient notes
- **Manual trigger**: `/dream` command for immediate cleanup after major refactoring

---

## Conclusion — The Era of AI That Dreams

The evolution of Claude's memory system can be summarized in one line:

> **"Writing (Auto Memory) alone isn't enough. You need to sleep and organize (Auto Dream) for real memories to form."**

This isn't just a feature addition — it's a signal that LLM agents are beginning to mimic **fundamental mechanisms of human cognition**. The Sleep-time Compute paper provides the theory, agent memory surveys provide the taxonomy, and Claude Code's Auto Dream implements it as a product.

As a game developer analogy, it follows the same trajectory as NPC AI evolving from simple state machines (FSM) to behavior trees, and then to utility AI. Just as each step qualitatively changed the complexity of situations agents could handle, AI memory systems are preparing for a qualitative leap along the trajectory of "simple storage → automatic learning → sleep consolidation."

---

## References

### Papers
1. Kevin Lin et al., **"Sleep-time Compute: Beyond Inference Scaling at Test-time"**, arXiv:2504.13171, 2025.
2. Yuyang Hu, Shichun Liu et al., **"Memory in the Age of AI Agents: A Survey"**, arXiv:2512.13564, 2025/2026.
3. Yaxiong Wu et al., **"From Human Memory to AI Memory: A Survey on Memory Mechanisms in the Era of LLMs"**, arXiv:2504.15965, 2025.
4. **"Memory for Autonomous LLM Agents"**, arXiv:2603.07670, 2026.
5. **"A Survey on the Memory Mechanism of Large Language Model-based Agents"**, ACM TOIS, 2025.

### Articles and Documentation
6. Akari, **"The Day We Might Say 'Sweet Dreams' to Claude"**, Zenn, 2026-03-24.
7. Anthropic, **"How Claude remembers your project"**, [Claude Code Docs](https://code.claude.com/docs/en/memory).
8. **"Claude Memory Guide: Understanding the 3-Layer Architecture"**, [ShareUHack](https://www.shareuhack.com/en/posts/claude-memory-feature-guide-2026), 2026.
9. **"Claude Code Auto Dream: Memory Consolidation Feature Explained"**, [ClaudeFast](https://claudefa.st/blog/guide/mechanics/auto-dream).
