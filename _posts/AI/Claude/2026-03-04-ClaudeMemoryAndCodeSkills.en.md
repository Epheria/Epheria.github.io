---
title: "Claude Memory Goes Free, /simplify & /batch — and the Hidden Cost of CLAUDE.md"
lang: en
date: 2026-03-04 14:00:00 +0900
categories: [AI, Claude]
tags: [Claude, Claude Code, Memory, AI, LLM, simplify, batch, CLAUDE.md, Token Optimization, Developer Tools]

difficulty: intermediate
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
  - /posts/EvaluatingAgentsMd/
tldr:
  - "Anthropic opened Claude Memory to the free plan and launched a ChatGPT/Gemini memory import tool — an aggressive move right after hitting #1 free app on the App Store"
  - "/simplify spawns 3 parallel review agents (code reuse, quality, efficiency) that auto-fix 3–5 issues per PR, while /batch decomposes an entire codebase into 5–30 units for parallel migration"
  - "Excessive CLAUDE.md nesting can waste up to 55K+ tokens per session; Skill-based progressive loading can save up to 82% of context"
---

## Introduction

In the first week of March 2026, three notable developments emerged in the Claude ecosystem:

1. **Claude Memory opened to the free plan**, along with a competitor memory import tool
2. **`/simplify` and `/batch`** skills were bundled into Claude Code
3. The **token cost issues caused by CLAUDE.md nesting patterns** began to be seriously discussed in the community

This article covers each topic in depth. For the third topic in particular, we extend the context file paradox discussed in a previous post ([Is AGENTS.md Really Helpful?](/posts/EvaluatingAgentsMd/)) with actual token figures.

---

## 1. Claude Memory — Free Plan Launch and Memory Import

### 1-1. Timeline

| Date | Event |
|------|-------|
| August 2025 | Claude Memory first introduced (paid plans only) |
| October 2025 | Expanded to all paid plans: Pro, Max, Team, Enterprise |
| March 2, 2026 | **Free plan launch** + Memory import tool released |

A phased rollout spanning about 8 months was completed. The timing is significant — it came right after Claude reached **#1 on the App Store free app chart**, and during a period when **ChatGPT uninstalls surged by 295%** following the ChatGPT DoD (U.S. Department of Defense) contract.

### 1-2. How Memory Works

Claude's memory consists of summaries automatically generated during conversations.

```
User conversation → Claude infers preferences/projects/context → Saved as text file
```

Key features:
- **Auto-inference**: Automatically identifies user preferences, ongoing projects, and work context during conversations
- **Editable**: Users can directly view and modify saved memories
- **Control options**: Can be paused (preserves memory, deactivated) or fully deleted
- **Work-focused**: Designed to focus on work-related context; non-work personal information may not be preserved

### 1-3. Memory Import Tool

A tool was simultaneously released for users switching from competing chatbots like ChatGPT and Gemini to Claude.

**Migration process:**

1. Paste Claude's export prompt into ChatGPT/Gemini
2. The chatbot outputs saved memories as a code block
3. Paste this text into Claude and click "Add to memory"
4. Claude extracts key information and saves it as individual memory items

**Notes:**
- This is still an experimental feature, so not all memories may transfer perfectly
- Work-related context is prioritized; unrelated personal information may be omitted

### 1-4. What This Means

Opening memory to the free plan is not just a feature expansion. It's a strategic move to **lower switching costs** in the AI chatbot market. Context accumulated in other chatbots creates a lock-in effect that "keeps you using the AI you're already familiar with," and the import tool directly breaks down this barrier.

From a game developer's perspective, it's similar to providing asset migration tools when transitioning from Unity Editor to Unreal Engine.

---

## 2. /simplify — 3 Parallel Review Agents

### 2-1. Overview

`/simplify` is a **bundled skill** introduced in Claude Code v2.1.63. After implementing a feature and verifying it works, run it before committing to automatically improve code quality.

From the official documentation:

> `/simplify`: reviews your recently changed files for code reuse, quality, and efficiency issues, then fixes them.

### 2-2. The 3 Parallel Review Agents

The core of `/simplify` is its architecture of **spawning three sub-agents in parallel**.

```
/simplify execution
    ├── 🔄 Code Reuse Agent
    │    └── Checks for duplicate logic, extractable patterns
    ├── 📐 Code Quality Agent
    │    └── Checks readability, naming, structure
    └── ⚡ Efficiency Agent
         └── Checks unnecessary complexity, redundant operations

    → Aggregates results from 3 agents
    → Auto-applies fixes
```

**Role of each agent:**

| Agent | Inspection Target | Commonly Caught in Practice |
|-------|-------------------|---------------------------|
| Code Reuse | Duplicate logic, extractable patterns | Similar functions copied across files |
| Code Quality | Readability, naming, structure | Unclear variable names, excessive nesting |
| Efficiency | Unnecessary complexity, missed optimizations | Unnecessary loops, missed concurrency opportunities |

Based on real-world reports, it consistently catches **3–5 issues per feature branch**, with the Efficiency agent being particularly strong at identifying unnecessary loops and missed concurrency opportunities.

### 2-3. Usage

```bash
# Basic usage — review all changed files
/simplify

# Focus on specific concerns
/simplify focus on memory efficiency

# Focus on specific patterns
/simplify focus on null safety and error handling
```

**Recommended workflow:**

```
Implement feature → Verify behavior → /simplify → Commit → PR
```

Making it a habit to run `/simplify` before every PR can preemptively eliminate issues that would be flagged during code review.

---

## 3. /batch — Large-Scale Parallel Code Migration

### 3-1. Overview

`/batch` is a skill that performs large-scale changes across an entire codebase **in parallel**. It's not simple search-and-replace — it orchestrates the full pipeline from research → decomposition → execution → PR creation.

### 3-2. How It Works

```
/batch "migrate src/ from Solid to React"
    │
    ├── 1. Codebase Research
    │    └── Analyze target files and patterns
    │
    ├── 2. Task Decomposition (5–30 units)
    │    └── Split into independently processable units
    │
    ├── 3. User Approval
    │    └── Present decomposed plan and request approval
    │
    └── 4. Parallel Execution
         ├── Worker 1 (isolated git worktree)
         │    ├── Implementation
         │    ├── Testing
         │    ├── /simplify (automatic)
         │    └── PR creation
         ├── Worker 2 (isolated git worktree)
         │    └── ...
         └── Worker N
              └── ...
```

Key points:
- **Isolated git worktrees**: Each worker operates in an independent working tree, so there are no conflicts
- **Automatic /simplify**: Each worker automatically runs `/simplify` before committing. No manual chaining needed
- **Git repository required**: Uses worktree functionality, so it only works in git repositories

### 3-3. Usage Examples

```bash
# Framework migration
/batch migrate src/ from Solid to React

# API version upgrade
/batch update all API calls from v2 to v3 endpoints

# Test framework change
/batch convert all Jest tests in tests/ to Vitest

# Coding convention batch application
/batch rename all React components from PascalCase files to kebab-case files
```

### 3-4. /simplify vs /batch Comparison

| | /simplify | /batch |
|---|----------|--------|
| **Purpose** | Clean up changed code | Large-scale codebase changes |
| **When to run** | After implementation, before PR | During migration/refactoring |
| **Parallel units** | 3 review agents | 5–30 worker agents |
| **Isolation** | Runs on current branch | Individual git worktrees |
| **Output** | Modifies current code | Individual PR per worker |
| **/simplify included** | Is /simplify itself | Each worker runs it automatically |

---

## 4. The Hidden Cost of CLAUDE.md Nesting

### 4-1. Background

In a [previous post](/posts/EvaluatingAgentsMd/), we confirmed the **information duplication** and **cost increases** caused by context files using research data. This time, we analyze the **token costs** that occur when CLAUDE.md is excessively configured in actual Claude Code environments with concrete figures.

### 4-2. CLAUDE.md Loading Mechanism

Claude Code automatically loads the following at session start:

```
Session start
    ├── CLAUDE.md (project root)
    ├── ~/.claude/CLAUDE.md (user level)
    ├── CLAUDE.md in parent directories (recursive search)
    ├── MCP server tool definitions
    └── Activated Skill descriptions
```

**The problem is that all of this is loaded into context for every session, every message.**

### 4-3. The Waste in Numbers

Combining figures reported by the community and official documentation:

#### MCP Server Token Overhead

| MCP Servers | Token Consumption Before Conversation Starts |
|-------------|---------------------------------------------|
| 0 | ~0 tokens |
| 5 | **~55,000 tokens** |
| 10+ | **100,000+ tokens** |

With just 5 MCP servers connected, **55K tokens are already consumed** before the conversation even begins. Adding servers with large tool definitions like Jira easily reaches 100K.

> Claude Code's Tool Search feature mitigates this problem by 46.9% (51K → 8.5K tokens). When tool descriptions exceed 10% of the context window, it automatically switches to on-demand loading.

#### CLAUDE.md Context Efficiency

Context utilization per session from actual measurements:

| Session Type | Tokens Loaded | Tokens Actually Used | Utilization |
|-------------|---------------|---------------------|-------------|
| README typo fix | 2,100 | ~300 | **14%** |
| Add API endpoint | 2,100 | ~600 | **28%** |
| Write tests | 2,100 | ~500 | **24%** |

**Average utilization is around 22%**. In other words, **78% of what's written in CLAUDE.md consumes unnecessary tokens** for that session.

#### The Multiplier Effect of Agent Teams

| Mode | Token Usage Multiplier | Reason |
|------|----------------------|--------|
| Single session | 1x (baseline) | — |
| Sub-agents | 1.5–3x | Each maintains its own context window |
| Agent Teams (plan mode) | **~7x** | Independent Claude instance per team member |

When team members operate in plan mode with Agent Teams, they use **approximately 7x the tokens of a single session**. If an excessive CLAUDE.md is loaded for each team member, the waste is multiplied by the number of team members.

#### Auto-Compaction Overhead

The auto-compact feature also consumes part of the context window. According to some reports, **the autocompact buffer pre-occupies 45K tokens — 22.5% of the context window**.

### 4-4. Cost Analysis by Nesting Pattern

Many developers use nesting patterns to systematically manage CLAUDE.md. However, token costs vary significantly depending on the pattern.

#### Pattern 1: Monolithic CLAUDE.md (Not Recommended)

```markdown
# CLAUDE.md (2,000+ lines)
## Project Overview ...
## Build Commands ...
## Coding Conventions ...
## API Documentation ...
## Database Schema ...
## Deployment Guide ...
## Test Strategy ...
```

- **Problem**: Loads entire content for every session
- **Token cost**: ~8,000–15,000 tokens per session
- **Utilization**: 14–28% (mostly unnecessary)

#### Pattern 2: Directory-Based Distribution (Partial Improvement)

```
project/
├── CLAUDE.md              # Project-wide rules
├── src/
│   └── CLAUDE.md          # src-related rules
├── tests/
│   └── CLAUDE.md          # Test-related rules
└── docs/
    └── CLAUDE.md          # Documentation-related rules
```

- **Improvement**: Additional rules loaded based on working directory
- **Remaining issue**: Root CLAUDE.md is still always loaded
- **Token cost**: 3,000–8,000 tokens (varies by directory)

#### Pattern 3: Skill-Based Progressive Loading (Recommended)

```
project/
├── CLAUDE.md              # Only essential minimum info (~500 lines or less)
└── .claude/skills/
    ├── deploy/SKILL.md    # Loaded only during deployment
    ├── api-guide/SKILL.md # Loaded only during API work
    └── db-schema/SKILL.md # Loaded only during DB work
```

- **Key**: Skills only load their **full content when invoked**
- **Normally**: Only the Skill description is included in context
- **Token savings**: **Up to 82% savings** (~15,000 tokens/session)

### 4-5. Before and After Optimization Comparison

Optimization effects combining official documentation and community reports:

| Strategy | Savings | Method |
|----------|---------|--------|
| CLAUDE.md → Skill migration | **82%** | Separate specialized instructions into Skills |
| Enable MCP Tool Search | **46.9%** | On-demand loading of tool definitions |
| Use Plan mode | **40–60%** | Reduce exploration costs for complex tasks |
| Keep CLAUDE.md under 500 lines | **62%** | Save ~1,300 tokens per session |
| Full optimization applied | **55–70%** | Combination of above strategies |

### 4-6. Practical Guide: CLAUDE.md Diet

**What to keep in CLAUDE.md:**

```markdown
# Build/run commands (project-specific)
bundle exec jekyll serve

# Project-specific non-standard rules
- Translation files: use .en.md, .ja.md suffixes
- Images: under assets/img/post/{category}/

# Special tool requirements
- Requires Ruby 3.2
- Don't commit Gemfile.lock
```

**What to move to Skills:**

```yaml
# .claude/skills/post-guide/SKILL.md
---
name: post-guide
description: Blog post writing guide. Use when writing posts.
---
## Front Matter Format
...detailed front matter guide...

## Category List
...full category listing...

## Post Statistics
...statistical data...
```

This way, `/post-guide` is only loaded when writing posts, and during other tasks, only the one-line description "Blog post writing guide. Use when writing posts." is included in context.

---

## 5. The Intersection of Three Changes

This week's three changes are interconnected:

```
Memory free launch         /simplify + /batch         CLAUDE.md optimization
      │                         │                          │
      ▼                         ▼                          ▼
  User growth  ──→  More agent usage  ──→  Token cost management critical
      │                         │                          │
      └─────────────── Ultimately a cost efficiency problem ────────────────┘
```

As memory going free increases users and multi-agent skills like `/simplify` and `/batch` become routine, **token cost management becomes a necessity, not a choice**. The "context file paradox" discussed in the previous post has now escalated into a real cost issue.

---

## Conclusion

The direction of Claude ecosystem evolution is clear:

1. **Expanding accessibility**: Free memory launch, competitor migration tools
2. **Deepening automation**: `/simplify`'s 3-agent review, `/batch`'s parallel migration
3. **Mandatory cost optimization**: Skill-based progressive loading, Tool Search, Plan mode

In particular, the pattern of using CLAUDE.md as an "encyclopedia containing everything about the project" now needs to be reconsidered. The official documentation also recommends keeping it under 500 lines, and separating specialized instructions into Skills is overwhelmingly advantageous in terms of token efficiency.

Next time you modify CLAUDE.md, ask yourself: **"Is this content worth loading in every session, every message?"**

---

## References

- Anthropic. (2026). *Claude Memory - Free Plan*. [Engadget](https://www.engadget.com/ai/anthropic-brings-memory-to-claudes-free-plan-220729070.html)
- Anthropic. (2026). *Import and export your memory from Claude*. [Claude Help Center](https://support.claude.com/en/articles/12123587-import-and-export-your-memory-from-claude)
- Anthropic. (2026). *Extend Claude with skills*. [Claude Code Docs](https://code.claude.com/docs/en/skills)
- Anthropic. (2026). *Manage costs effectively*. [Claude Code Docs](https://code.claude.com/docs/en/costs)
- Boris Cherny. (2026). */simplify and /batch announcement*. [Threads](https://www.threads.com/@boris_cherny/post/DVR-HzBkqRd/)
- Joe Njenga. (2026). *Claude Code Just Cut MCP Context Bloat by 46.9%*. [Medium](https://medium.com/@joe.njenga/claude-code-just-cut-mcp-context-bloat-by-46-9-51k-tokens-down-to-8-5k-with-new-tool-search-ddf9e905f734)
- MacRumors. (2026). *Anthropic Adds Free Memory Feature and Import Tool*. [MacRumors](https://www.macrumors.com/2026/03/02/anthropic-memory-import-tool/)
- TechCrunch. (2026). *ChatGPT uninstalls surged by 295% after DoD deal*. [TechCrunch](https://techcrunch.com/2026/03/02/chatgpt-uninstalls-surged-by-295-after-dod-deal/)
- The Verge. (2026). *Anthropic upgrades Claude's memory to attract AI switchers*. [The Verge](https://www.theverge.com/ai-artificial-intelligence/887885/anthropic-claude-memory-upgrades-importing)
