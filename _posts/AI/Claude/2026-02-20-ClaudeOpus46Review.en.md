---
title: "Claude Opus 4.5 → 4.6 Transition: Performance, Tokens, Workflow Changes Experienced by a Game Developer"
date: 2026-02-20 14:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, AI, Opus 4.6, Opus 4.5, Sonnet 4.6, LLM, Benchmark, Game Development]
lang: en
difficulty: intermediate
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "Opus 4.6 expands the context window 5x to 1M tokens, and ARC AGI 2 reasoning score jumps from 37.6% to 68.8%."
  - "Adaptive Thinking automatically adjusts depth of thought based on task complexity, but increases token consumption by ~2x."
  - "Separating roles—Opus 4.6 for Design/Analysis and Sonnet 4.6 for Implementation/Modification—yields optimal cost efficiency."
---

## Introduction

On February 5, 2026, Anthropic released Claude Opus 4.6. In my previous post ([AI Usage for Game Developers Based on Real Data](/posts/ClaudeCodeInsights/)), I shared 47 days of usage data. The first half of that period was with Opus 4.5, and the second half was with Opus 4.6.

This article covers both benchmark numbers and the tangible differences experienced in actual game development. I honestly summarize how the "groundbreaking performance improvements" in marketing materials translated into **actual differences in my Unity project**.

---

## 1. Opus 4.5 vs 4.6 by the Numbers

### Key Benchmark Comparison

| Benchmark | Opus 4.5 | Opus 4.6 | Change |
|---------|----------|----------|------|
| **ARC AGI 2** (New Type of Reasoning) | 37.6% | 68.8% | **+31.2pp** |
| **OSWorld** (Agentic Computer Use) | 66.3% | 72.7% | +6.4pp |
| **Terminal-Bench 2.0** (Terminal Tasks) | 59.8% | 65.4% | +5.6pp |
| **SWE-bench Verified** (Real Coding) | 80.9% | 80.8% | -0.1pp |
| **Long-Context Retrieval** (MRCR v2) | 18.5% | 76.0% | **+57.5pp** |

### Architecture Changes

| Specs | Opus 4.5 | Opus 4.6 |
|------|----------|----------|
| Context Window | 200K tokens | **1M tokens** |
| Max Output | 8K tokens | **128K tokens** |
| Adaptive Thinking | None | **Included** |
| Agent Teams | None | **Included** |
| Price (Input/Output) | $5 / $25 per M | $5 / $25 per M |

Two things stand out:

1. **Little difference in SWE-bench (Real Coding)** — Code writing capability itself is virtually the same between 4.5 and 4.6.
2. **Overwhelming improvement in Reasoning (ARC AGI 2) and Long Context** — It shines in complex analysis and navigating large codebases.

---

## 2. Actual Experience: What Insights Data Says

Comparing the two periods in my Claude Code Insights data reveals interesting patterns.

### Usage Comparison by Period

| Metric | First Half (1/5-2/12) | Second Half Delta (2/12-2/20) |
|------|------------------|----------------------|
| Duration | 38 days | 8 days |
| Messages | 1,246 | **919** |
| Sessions | 172 | **133** |
| Daily Avg Messages | 47.9 | **114.9** |
| Daily Avg Sessions | 4.5 | **16.6** |
| Lines of Code Added | +28,556 | **+27,767** |
| Modified Files | 188 | **208** |

**The daily average messages for the 8 days exploded to 2.4x compared to the first half.** Of course, this isn't solely due to the model upgrade. The project entered the implementation phase, and tool proficiency increased. However, the biggest experiential difference was the **1M Context Window**.

### Experiential Difference 1: Overwhelming Improvement in Long Context

With Opus 4.5's 200K context, Claude frequently **forgot previously discussed content** in the latter half of long sessions. Especially during tasks like memory leak investigations that involve reading dozens of files sequentially, it would inaccurately reference file contents read early in the session.

After switching to Opus 4.6's 1M context, **context loss decreased noticeably** in similar large-scale codebase investigations. The jump in MRCR v2 (Long-Context Retrieval) score from 18.5% to 76.0% is not an exaggeration.

```
Opus 4.5 Era:
  "In GameResultLayer.cs analyzed earlier..." → (Already gone from context)
  → Re-request needed → Time wasted

Opus 4.6:
  Can reference specific lines of the first file even after analyzing 30 files
  → Complete the entire investigation in a single session
```

### Experiential Difference 2: Two Sides of Adaptive Thinking

Adaptive Thinking is a key new feature of Opus 4.6. It automatically adjusts thought depth based on prompt complexity:

| Effort Level | Behavior | Suitable Tasks |
|------------|------|---------|
| `low` | Skips thinking for simple queries | Quick checks, simple fixes |
| `medium` | Thinks at an appropriate level | General coding tasks |
| `high` (Default) | Always deep thinking | Complex analysis, design |
| `max` | Unlimited depth of thought | Extremely complex reasoning |

Experience in practice:

**Positives** — Output quality increased for complex tasks like memory leak analysis or architecture design. The ability to explain "why this approach is problematic" improved significantly. The reasoning capability jump in ARC AGI 2 score (37.6% → 68.8%) is felt in reality.

**Negatives** — **Token consumption increased noticeably.** According to Artificial Analysis, Opus 4.6 generates **about 58M output tokens in standard benchmarks, while Opus 4.5 was 29M**. That's a 2x difference. Claude Code usage is unlimited, but direct API calls directly impact costs.

### Experiential Difference 3: Agent Teams

Agent Teams, officially introduced in Opus 4.6, supports parallel agent tasks. As mentioned in the previous post, my multi-agent sessions amounted to **92 parallel overlap events and 111 sessions**.

Honest assessment: **The concept is innovative, but stability is still experimental.**

```
✅ Works Well:
   Modifying files in 4 areas simultaneously (22 files completed in one session)
   Executing independent investigation tasks in parallel

❌ Issues:
   Agents stuck in idle loops, unresponsive
   Agents not responding to Team Lead's status requests
   File conflicts between agents (Missing namespace imports during simultaneous edits)
```

While the completion rate for single-agent sessions is ~80%, multi-agent sessions feel around 50-60%. Anthropic's Insights report also advises that "Sequential subtask breakdown is currently more stable than multi-agents."

---

## 3. Opus 4.6 vs Sonnet 4.6: Role Division Strategy

Sonnet 4.6 was also released on February 17. I currently use the two models **separated by role**.

### Benchmark Comparison

| Benchmark | Opus 4.6 | Sonnet 4.6 | Difference |
|---------|----------|------------|------|
| SWE-bench Verified | 80.8% | 79.6% | 1.2pp |
| OSWorld | 72.7% | 72.5% | 0.2pp |
| GDPval-AA (Knowledge Work) | 1606 Elo | **1633 Elo** | Sonnet Wins |
| Agentic Financial Analysis | 60.1% | **63.3%** | Sonnet Wins |

Shocking Fact: **In coding benchmarks, Sonnet 4.6 has reached 97-99% of Opus 4.6's level.** Sonnet even outperforms Opus in some practical benchmarks.

### My Role Division Strategy

```
┌─────────────────────────────────────────────────┐
│            Plan / Design Phase (Opus 4.6)          │
│  • Architecture design and technical decisions         │
│  • Large-scale codebase analysis (Using 1M context)    │
│  • Gap Analysis and quality verification               │
│  • Memory leak investigation (Traversing dozens of files)│
│  • Complex multi-file refactoring design               │
└─────────────────┬───────────────────────────────┘
                  │ Deliver Analysis Results/Design Docs
                  ▼
┌─────────────────────────────────────────────────┐
│            Do Phase (Sonnet 4.6)                   │
│  • Concrete code implementation                        │
│  • Bug fixes (Clear scope)                             │
│  • Single/Few file modifications                       │
│  • Repetitive coding tasks (Localization, etc.)        │
│  • Debugging requiring fast iteration                  │
└─────────────────────────────────────────────────┘
```

### Why This Strategy Works

**1. Cost Efficiency**

Opus 4.6: $5 / $25 (Input/Output per M tokens)
Sonnet 4.6: $3 / $15 (Input/Output per M tokens)

Sonnet provides 97-99% coding performance at 60% of Opus's cost. Using Opus for code implementation is akin to **burning money**.

**2. Speed Difference**

Sonnet's latency is significantly faster than Opus. In agentic workflows, dozens of API calls occur per session. Accumulating speed differences in each call creates a **huge difference in perceived productivity**.

**3. Opus's Real Strength lies in "Thinking"**

While equal in coding benchmarks like SWE-bench, **Opus 4.6 is overwhelmingly superior in ARC AGI 2 (Reasoning) at 68.8%**. Opus clearly wins in complex architectural decisions and design judgments after understanding the entire codebase.

---

## 4. Token Economics: What You Need to Know

### Increased Token Consumption of Opus 4.6

One of the most critical changes. With Adaptive Thinking defaulting to `high` level, **output tokens have increased by about 2x compared to Opus 4.5**.

| Model | Standard Benchmark Output Tokens | Relative Cost |
|------|---------------------|---------|
| Opus 4.5 | ~29M | 1x |
| Opus 4.6 (high) | ~58M | **~2x** |

Direct Impact on Claude Code Users:

- **Pro/Max Subscription**: Token quotas drain faster. If you could use it all day before, Opus 4.6 drains the quota faster for the same tasks.
- **API Users**: Incurs 2x output token costs for the same task.
- **Strategy**: You can adjust the effort level with the `/effort` command. Develop a habit of lowering it to `medium` or `low` for simple tasks.

### Practical Token Saving Guide

```bash
# Adjust effort level in Claude Code
/effort low     # Simple fixes, check tasks
/effort medium  # General coding
/effort high    # Complex analysis (Default)
/effort max     # Extremely difficult reasoning
```

Recommendations based on my usage pattern:

| Task Type | Recommended Model | Effort |
|---------|---------|--------|
| Architecture Design | Opus 4.6 | high/max |
| Memory Leak Investigation | Opus 4.6 | high |
| Gap Analysis | Opus 4.6 | high |
| General Code Implementation | Sonnet 4.6 | - |
| Simple Bug Fixes | Sonnet 4.6 | - |
| File Search/Check | Sonnet 4.6 | - |
| Localization Tasks | Sonnet 4.6 | - |

---

## 5. Practical Impact of 1M Context Window

### Before vs After

Expanding from 200K to 1M isn't just about "longer conversations possible." **It changes the way you work.**

**Workflow in Opus 4.5 (200K) Era:**

```
Session 1: Analyze GameResultLayer.cs → Output Report A
Session 2: Analyze 5 additional related files → Output Report B
Session 3: Synthesize Reports A+B → Final Analysis
```

It required 3 sessions. Lack of context prevented analyzing all files in one session, and information loss occurred during handoffs between sessions.

**Current Workflow in Opus 4.6 (1M):**

```
Single Session: Analyze all 30 related files → Output Comprehensive Report
```

This difference explains the jump in MRCR v2 score from 18.5% to 76.0%. The ability to **actually utilize** information within the context window has dramatically improved.

### Meaning of 128K Output

Previously, due to the 8K max token output limit, large reports couldn't be generated at once. I had to repeat "continue" or request section by section.

With the expansion to 128K output, I can **complete a memory leak analysis report for dozens of files in a single response**. File-by-file issue lists, priority classification, and fix recommendations are all contained in one response.

---

## 6. Moments Where Opus 4.6 Shines in Game Development

### Case 1: Full Inspection of DOTween Sequence Leaks

```
Request: "Find patterns across the entire project where DOTween Sequences are created
          but Kill() is not called, and classify them into P0/P1/P2."

Opus 4.5: Context limit after reading 15 files → Session split needed
Opus 4.6: Traverse all related files and output as a single report
```

This is the best example of the synergy between 1M context + improved reasoning capability.

### Case 2: Redesigning Node Combination System

When redesigning the node combination system for Skill Studio, I had it read the entire existing code and propose a new architecture. With Opus 4.6's Adaptive Thinking at `high`, it provided an analysis including not just "change it like this" but **"why the current structure is problematic and what the trade-offs are."**

### Case 3: Editing 22 Files Simultaneously

Using Agent Teams, I had a session modifying 22 files across 4 task areas simultaneously. Such parallel work was virtually impossible in Opus 4.5. Although the result wasn't perfect (missing namespace imports, etc.), **attempting work of this scale in a single session is a paradigm shift in itself.**

---

## 7. Honest Assessment: Is It Worth Upgrading?

### Opus 4.5 → 4.6

| Perspective | Evaluation |
|------|------|
| Coding Capability | **Almost Identical** (SWE-bench 0.1pp diff) |
| Analysis/Reasoning | **Significantly Improved** (ARC AGI +31pp) |
| Long Context | **Revolutionary Improvement** (MRCR +57.5pp) |
| Token Efficiency | **Worsened** (Output ~2x) |
| Multi-Agent | **New Feature, but Unstable** |
| Overall | **Must-Upgrade for Analysis-Centric Workflows** |

If simply writing code, the experiential difference isn't huge. But for usage patterns like mine—**analyzing large codebases, generating structured reports, and making complex architectural decisions**—it is a definite upgrade.

### Who Should Use It

```
✅ Opus 4.6 is effective for:
   - Developers frequently analyzing large codebases (tens of thousands of lines)
   - Complex investigation tasks like memory leaks, crashes
   - Using AI for architecture design and technical decision-making
   - Systematic verification workflows like Gap Analysis, Code Review

⚠️ Sonnet 4.6 is better for:
   - Routine code implementation and bug fixing
   - Debugging where fast iteration is key
   - Cost-constrained environments
   - Single/Few file tasks
```

---

## 8. Future Outlook

It took **only 2 months** from Opus 4.5 to 4.6. At this rate, 4.7 or the next generation model isn't far off. Expectations based on current limitations:

**1. Improved Multi-Agent Stability**
Currently the biggest pain point. Solving agent unresponsiveness, idle loops, and missing imports will dramatically increase parallel work productivity.

**2. Optimized Token Efficiency**
If Adaptive Thinking's depth becomes more refined, unnecessary token consumption for simple tasks could decrease. Currently, `high` is the default, leading to excessive thinking even for simple tasks.

**3. Improved Accuracy of First Attempts**
In my Insights data, "Wrong Approach" was the top cause of friction with 21 cases. Reasoning capability (ARC AGI 68.8%) has greatly improved, but the **ability to grasp developer intent** still has much room for improvement.

---

## Conclusion

The transition from Opus 4.5 to 4.6 is a shift from **"Smarter AI" to "Broader-Seeing AI"**. Coding ability is nearly the same, but the ability to understand large codebases and provide structured analysis has changed distinctively.

As a game developer, the most valuable change is **being able to view the entire project in a single session**. Tasks like memory leak investigation, refactoring design, and Gap Analysis are completed without session splitting, making the workflow much smoother.

However, the 2x increase in token consumption is a change that cannot be ignored. **Opus for Design and Analysis, Sonnet for Implementation**—this role division is currently the most rational strategy.

---

> **References**
> - [Anthropic Official - Introducing Claude Opus 4.6](https://www.anthropic.com/news/claude-opus-4-6)
> - [Anthropic Official - Introducing Claude Sonnet 4.6](https://www.anthropic.com/news/claude-sonnet-4-6)
> - [What's new in Claude 4.6 - Claude API Docs](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6)
> - [Claude Opus 4.6 Benchmark Analysis - Vellum](https://www.vellum.ai/blog/claude-opus-4-6-benchmarks)
> - [Claude Opus 4.6 Performance Analysis - Artificial Analysis](https://artificialanalysis.ai/models/claude-opus-4-6-adaptive)
> - [Sonnet 4.6 vs Opus 4.6 Comparison - NxCode](https://www.nxcode.io/resources/news/claude-sonnet-4-6-vs-opus-4-6-which-model-to-choose-2026)
