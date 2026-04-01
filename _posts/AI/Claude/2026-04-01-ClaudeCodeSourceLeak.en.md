---
title: "Deep Dive into Claude Code Architecture — Inferring the Design Principles of an AI Coding Agent"
lang: en
date: 2026-04-01 12:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Architecture, Agent Design, Tool System, Security, Prompt Cache, Compaction, TypeScript, Bun, Ink, React]
difficulty: advanced
toc: true
toc_sticky: true
math: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "We infer and analyze the internal architecture design principles based on observed behavior while using Claude Code, official documentation, and publicly available tech stack information"
  - "The core design axes are Generator-based streaming query loops, a Fail-Closed security model, and structured context compaction — these patterns can be used as general design principles for building large-scale AI agents"
  - "Power user tips based on official documentation — CLAUDE.md loading priority, Hook event usage, environment variable tuning, and more"
---

## Introduction

Claude Code is a CLI-based AI coding agent developed by Anthropic. It's an agentic tool that directly reads, modifies, builds, and tests code from the terminal, and has evolved rapidly since 2025.

In this post, we **infer and analyze** the internal architecture's design principles based on **behavioral patterns observed during extensive use of Claude Code**, official documentation, and characteristics of the publicly known tech stack (TypeScript, Bun, Ink, etc.).

Basis for analysis:
- Official documentation and blog posts
- Behavioral patterns observable during CLI usage
- Public npm package metadata and dependency trees
- Observable structures in system prompts
- General patterns and best practices in AI agent design

> **Note**: This post is based on inference from public information and usage experience, and may differ from the actual internal implementation.

---

## 1. Project Overview — Tech Stack and Scale

### 1-1. Public Tech Stack

| Item | Technology |
|------|-----------|
| Language | TypeScript |
| Runtime | Bun |
| UI Framework | React + Ink (Terminal TUI) |
| Package Manager | npm (@anthropic-ai/claude-code) |
| Built-in Tools | 42+ (Read, Write, Edit, Bash, Glob, Grep, Agent, etc.) |
| Extension | MCP (Model Context Protocol) server integration |

Based on observed behavior during use, it can be inferred that the codebase is quite substantial. Patterns typically seen in large-scale projects — startup time optimization, lazy loading, conditional tool activation — are observable.

### 1-2. Startup Time Optimization

As a CLI tool, the perceived startup time is very fast. Simple flags like `--version` respond in nearly 0ms.

This suggests the use of a **lazy loading pattern via dynamic imports**:
- Heavy modules are not loaded during simple flag processing
- Initialization tasks like authentication and configuration reading are performed in parallel
- Leverages Bun runtime's fast startup time

---

## 2. Architecture — The Path from Request to Tool Execution

Observing Claude Code's behavior, the following pipeline structure can be inferred:

```
User Input
    ↓
[1] CLI Bootstrap — Authentication, model selection, permission mode setup
    ↓
[2] TUI (Terminal UI) — React/Ink-based interactive interface
    ↓
[3] Query Engine — System prompt assembly, message normalization
    ↓
[4] API Call + Tool Execution Loop
    │   ├→ Anthropic API (SSE streaming)
    │   ├→ Tool Execution (42+ built-in tools + MCP tools)
    │   ├→ Automatic Context Management (compaction)
    │   └→ Memory System
    ↓
[5] Render results to user
```

### 2-1. Build-Time Feature Gating

It appears that **build-time Dead Code Elimination** using Bun's bundling capabilities is applied. Certain features are enabled/disabled at build time, and the related code is completely removed from the final bundle.

Benefits of this approach:
- Code size optimization without runtime conditional branching
- Clean separation of internal-only and externally-released features
- Bundle size minimization

---

## 3. Tool System — Tool Type Design

### 3-1. Tool Interface Pattern

Each of Claude Code's tools (Read, Write, Edit, Bash, etc.) appears to follow a common interface. Referencing typical AI agent tool design, the following contract is needed:

```
Tool Interface (inferred):
├── name: Tool name
├── call(): Execute tool + return result
├── checkPermissions(): Permission check
├── description(): Generate tool description
│
├── isReadOnly(): Whether read-only
├── isConcurrencySafe(): Whether concurrent execution is safe
├── isDestructive(): Whether destructive operation
│
├── renderToolUseMessage(): UI display during tool use
├── renderToolResultMessage(): Result UI display
│
└── maxResultSizeChars: Result size limit
```

### 3-2. Fail-Closed Defaults

Observing Claude Code's behavior, the **Fail-Closed principle** is consistently applied:

- **New tools are assumed unsafe by default** — concurrent execution disabled, assumed writable
- Only tools explicitly declared as safe are allowed parallel execution
- Only tools explicitly declared as read-only are eligible for auto-approval

This principle is crucial for security design, because even if you forget to declare safety when adding a new tool, it **always defaults to the safe side**.

### 3-3. Tool Pool Assembly

Built-in tools and MCP external tools are combined into a single tool pool. **Name-sorted ordering** is important here because the Anthropic API's prompt cache key is affected by the order of the tool list. If the order changes, the cache breaks and costs increase.

### 3-4. Tool Lazy Loading

As can be confirmed from the system prompt, some tools operate using a **deferred (lazy loading)** approach. Since loading all tools from the start would make the system prompt too long, schemas are fetched on demand.

---

## 4. Detailed Analysis of Core Design Patterns

### 4-1. Bash Security — Multi-Layer Defense Model

Claude Code's Bash tool is both the most powerful and the most dangerous tool. Based on observed behavior, a **multi-layer security pipeline** is applied:

```
[1] Regex-based Dangerous Pattern Detection
    - Detect dangerous constructs like process substitution, command substitution
    - Unicode attack and control character filtering

[2] AST-based Structural Analysis
    - Parse Bash commands to generate Abstract Syntax Tree (AST)
    - Structures not on the allowlist → automatic rejection (Fail-Closed)
    - Only simple commands are eligible for automatic processing

[3] Permission Rule Matching
    - Match argv[0] against predefined patterns
    - Apply alwaysAllow / alwaysDeny rules from settings.json

[4] User Confirmation Dialog
    - If none of the above stages pass, directly confirm with the user
```

**Core Principle**: "Can trustworthy argv[] be extracted from this command?" → If possible, apply rule matching; if not, ask the user directly. Block what you don't understand.

### 4-2. Prompt Cache Optimization

Claude Code actively leverages prompt caching to optimize API call costs.

**Cache Key Components** (based on Anthropic API documentation):
- System prompt
- Tool list (including order)
- Model
- Message prefix

Observable optimizations for this:
- **Deterministic sorting** of tool lists (alphabetical, built-ins first)
- **Static/dynamic region separation** of system prompt (maximizing cacheable area)
- Keeping sub-agent system prompts identical to parent to share cache

### 4-3. Structured Context Compaction

It's observable that Claude Code automatically compresses context as conversations grow longer. Manual triggering is also possible with the `/compact` command.

**Observed Compaction Behavior:**

1. **Auto-trigger**: Automatically executes when exceeding a certain percentage of the context window
2. **Structured summary**: Not simple summarization, but structural compression divided into multiple sections
   - User requests and intent
   - Technical concepts
   - Files and code sections
   - Errors and solutions
   - Remaining tasks and current work status
3. **User message preservation**: User-provided feedback and instructions are preserved during compression
4. **Image processing**: Images are replaced with text markers before compression to optimize API calls

### 4-4. Token Overflow Recovery Strategy

When token limits are reached during API calls, a staged recovery strategy is applied:

| Situation | Recovery Strategy |
|-----------|-------------------|
| Token overflow (1st) | Reactive compaction — compress conversation history |
| Token overflow (2nd) | Gradually increase max output tokens |
| Token overflow (3rd) | Forced termination |
| Context window approaching | Proactive auto-compaction |
| API error | Exponential backoff retry |

### 4-5. Memory System Relevance Search

Claude Code's memory system (`~/.claude/projects/*/memory/`) appears to use **LLM-based relevance assessment** rather than traditional vector search.

Observed behavior:
- Relevance assessment based on memory file headers (name, description)
- Only a small number of memories selectively loaded per turn
- Prevents duplicate loading of reference documents for already-used tools
- Filters out memories already provided in previous turns

### 4-6. Large Tool Result Handling

When tool execution results are very large (file reading, search results, etc.), a pattern is observed where the **results are persisted to disk and only a preview is passed** rather than putting the entire result in context.

This is a rational design that saves the context window while still allowing access to full results when needed.

### 4-7. Selective Retry Strategy

Observing retry behavior during API overload (529) situations:

- **Main requests where the user is waiting**: Retry performed
- **Background tasks** (title generation, summarization, etc.): Fail immediately (no retry)

This design prevents unnecessary retries from worsening the situation during overload, based on the principle that "each retry in a capacity cascade causes 3-10x gateway amplification."

---

## 5. System Prompt Structure

### 5-1. Static/Dynamic Boundary

Observing the system prompt reveals separation of **static areas** and **dynamic areas**:

```
[Static Area — Prompt Cache Eligible]
  ├── Tool descriptions
  ├── Base instructions (# System, # Doing tasks, # Using your tools)
  ├── Security instructions
  └── Code style instructions
──── (Boundary) ────
[Dynamic Area — Changes every turn]
  ├── CLAUDE.md contents
  ├── git status snapshot
  ├── Per-session guidance
  ├── Memory (MEMORY.md)
  └── Language settings, output style
```

Placing the static area at the front increases prompt cache hit rates. Even when dynamic area content changes, the static area cache is maintained.

### 5-2. CLAUDE.md Loading Priority

Loading order confirmed from official documentation:

```
1. /etc/claude-code/CLAUDE.md  — Admin settings (lowest priority)
2. ~/.claude/CLAUDE.md          — User global settings
3. {project}/CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md
4. {project}/CLAUDE.local.md  — Highest priority
```

Later-loaded content is placed closer to the model, receiving more attention.

---

## 6. Power User Tips for Practice

### 6-1. Environment Variable Tuning

Environment variables confirmed from official documentation and settings:

| Environment Variable | Function |
|---------------------|----------|
| `DISABLE_AUTO_COMPACT=1` | Disable auto-compact |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Set max output tokens |

> The environment variable list may change with versions, so it's recommended to refer to official documentation.

### 6-2. Hook Event Usage

Hook events confirmed from official documentation:

```
PreToolUse / PostToolUse
Notification
Stop
SubagentStop
```

Actions that hooks can return:
- `approve` / `deny` / `block` — Allow/deny/block tool execution
- `reason` — Reason for decision
- `updatedInput` — Modified input

Using hooks, you can automate tool execution or auto-approve/deny commands matching specific patterns.

### 6-3. Agent Usage Optimization

Agent types confirmed from system prompt:

| Agent | Purpose | Features |
|-------|---------|----------|
| `Explore` | Codebase exploration | Specify depth: `quick` / `medium` / `very thorough` |
| `Plan` | Design/planning | Specialized for implementation strategy design |
| `general-purpose` | Multi-step tasks | Includes CLAUDE.md, most versatile |

Specifying exploration depth for Explore changes the search scope, so it's efficient to use `quick` for simple searches and `very thorough` for deep analysis.

---

## 7. Security Design Principles

Principles consistently observed in Claude Code's security design:

### 7-1. Fail-Closed Strategy

- Bash commands not understood → Block and request user confirmation
- Default permissions for new tools → Not allowed (explicit permission required)
- Concurrency safety undeclared → Serial execution

### 7-2. Defense in Depth

To execute a single Bash command, multi-stage verification goes through regex filter → AST analysis → permission matching → user confirmation.

### 7-3. Filesystem Protection

Protection is observed for system configuration files like `.gitconfig`, `.bashrc`, `.zshrc` and important directories like `.git`, `.vscode`, `.claude`.

### 7-4. 5-Stage Permission Decision Flow

```
Tool Use Request
  ↓
① Static Rules (alwaysAllow/alwaysDeny in settings.json)
  ↓
② Hook Execution (when external process hooks are registered)
  ↓
③ Auto Classification (automatic safe command assessment)
  ↓
④ Multi-agent Delegation (for sub-agents)
  ↓
⑤ User Dialog (final confirmation)
```

---

## 8. Conclusion

The design philosophy observed through deep use of Claude Code can be summarized in three points:

1. **Fail-Closed Security**: Block what you don't understand. The entire Bash security and permission system is built on this principle.

2. **Cost Optimization**: Design to save every token is everywhere — prompt caching, selective retry, tool result disk persistence, image processing optimization.

3. **Gradual Feature Release**: Isolate features with feature flags and roll out gradually. There may be features included in the build that are not yet observable.

These design principles are not specific to Claude Code, but are **architectural patterns universally applicable when building large-scale AI agents**. In particular, the Fail-Closed security model and structured compaction are worth referencing in any AI agent project.

---

## References

- [Claude Code Insights](/posts/ClaudeCodeInsights/) — Basic usage of Claude Code
- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — Official tool use guide
- [Claude Code Official Documentation](https://docs.anthropic.com/en/docs/claude-code) — Official usage guide
- [Model Context Protocol](https://modelcontextprotocol.io/) — MCP official documentation
