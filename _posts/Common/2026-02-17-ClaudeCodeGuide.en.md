---
title: The Complete Claude Code Guide - From Installation to Advanced Usage Strategies
date: 2026-02-17 14:00:00 +0900
categories: [Tool, Claude Code]
tags: [claude code, ai, llm, vibe coding, claude, anthropic, cli]
difficulty: intermediate
lang: en
toc: true
toc_sticky: true
---

<br>

## What Is Claude Code?

**Claude Code** is an **agentic coding tool** developed by Anthropic. It runs directly in the terminal (CLI) and can handle almost every development task through natural language, including writing code, refactoring, debugging, and git operations.

Its biggest difference from existing AI coding assistants (Copilot, Cursor, etc.) is that it **understands the entire project as context** and works as an **agent** that can directly read and write the file system.

<br>

---

## I. Installation (macOS)

### Method 1: Install via Homebrew (Recommended)

| Step | Command | Description |
|:---:|:---|:---|
| **1** | `brew install --cask claude-code` | Install Claude Code with Homebrew |
| **2** | `claude --version` | Verify installation and check version |

### Method 2: Install via npm

| Step | Command | Description |
|:---:|:---|:---|
| **1** | `node --version` | Verify Node.js 18.0+ |
| **2** | `npm install -g @anthropic-ai/claude-code` | Global install via npm |
| **3** | `claude --version` | Verify installation |

> If Node.js is not installed, use the LTS version from the [official site](https://nodejs.org/) or install it with `brew install node`.
{: .prompt-tip }

<br>

---

## II. Initial Setup

### 1. Sign In

After installation, sign in from the terminal.

```bash
claude login
```

When your browser opens, sign in with your Anthropic account and choose the CLI tool type.

### 2. Check Token Usage

You can check current usage at [https://claude.ai/settings/usage](https://claude.ai/settings/usage).

> **What is a token?** A token is the minimum unit an LLM processes. Roughly, English is about 1 word = 1.3 tokens, while Korean is about 1 character = 2-3 tokens. Claude Code consumes both **input tokens (prompt + context)** and **output tokens (response)**.
{: .prompt-info }

<br>

---

## III. IDE Integration (Recommended)

You can use it directly from terminal, but using it with an IDE is **strongly recommended**. You can inspect code changes in real time, which is much more efficient.

### VS Code (Recommended)

1. Install [VS Code](https://code.visualstudio.com/)
2. Open your project folder with **Open Folder**
3. Open **Terminal > New Terminal**
4. Run `claude` in that terminal

```bash
# Run from your project directory
cd /path/to/your/project
claude
```

> At startup, Claude Code automatically reads `CLAUDE.md` in your project root to understand architecture, coding conventions, and workflow. That context improves relevance and accuracy.
{: .prompt-tip }

### JetBrains (Rider, IntelliJ, etc.)

You can run `claude` from the built-in terminal in JetBrains IDEs as well. Personally, I found VS Code terminal UX better.

<br>

---

## IV. Complete Reference of Core Commands

### Session Management Commands

| Command | Function | Description |
|:---|:---|:---|
| `claude` | Start Claude Code | Start a new session in the current directory |
| `claude -c` / `claude --continue` | Continue latest session | Continue from the last conversation |
| `claude -r` / `claude --resume` | Resume previous conversation | Pick and resume from past sessions |
| `claude --verbose` | Verbose mode | Show detailed logs useful for debugging |
| `claude --dangerously-skip-permissions` | Skip permission checks | Auto-allow all file access and execution (caution) |

### Slash Commands Inside a Session

| Command | Function | Detailed Description |
|:---|:---|:---|
| `/clear` | **Reset context** | Start a new conversation. **Most important command.** Having enough context window reduces hallucination risk. Use `/clear` per task. |
| `/compact` | Compress conversation | Summarize/compact chat to free context. You can target specific content, e.g. `/compact core points`. |
| `/model` | Switch model | Choose Opus, Sonnet, etc. A practical pattern is Opus for planning, Sonnet for implementation. |
| `/resume` | Resume old conversation | Load past conversations. |
| `/config` | Manage settings | Adjust verbose, model, todo list, and more. |
| `/memory` | Edit CLAUDE.md | Edit project/global CLAUDE.md directly. |
| `/init` | Initialize project | Claude analyzes the project and generates CLAUDE.md automatically. |
| `/terminal-setup` | Configure terminal line breaks | Enable line breaks via `Shift+Enter`. |
| `/plugin` | Plugin management | Explore, install, and remove plugins. |
| `/agents` | Agent management | Inspect and manage custom agents. |
| `/mcp` | MCP server management | Configure Model Context Protocol servers. |
| `/statusline` | Status line settings | Configure terminal status line display. |
| `/todos` | View todo list | Check the current task list. |
| `/permissions` | Permission management | Configure pre-approval rules for bash commands, etc. |
| `/insights` | **Usage pattern analysis** | Analyze the last 30 days of sessions and generate an HTML report with patterns, bottlenecks, and workflow suggestions. |
| `/fast` | **Toggle Fast mode** | Switch fast output mode. Shows lightning icon (↯), persisted across sessions. |

### Update Commands

```bash
# Update Claude Code (npm install)
claude update

# If installed via Homebrew
brew upgrade claude-code
```

### Special Features

| Feature | How to Use | Description |
|:---|:---|:---|
| **File reference** | `@filename` | Add `@` to reference files directly, e.g. `@GameHandler.cs`. |
| **Image attach** | Drag & drop / `Cmd+Shift+4` then paste | Adding screenshots/UI designs gives visual context and significantly boosts efficiency. Official docs also recommend image usage. |
| **Rewind** | Tap `Esc` twice | Stop current conversation and roll back to a checkpoint. You can choose conversation/code/conversation+code. Very useful when hallucination appears. |
| **Mode switch** | `Shift+Tab` | Switch between Plan mode / Auto-accept mode / default mode. |
| **Thinking toggle** | `Tab` | Toggle Extended Thinking mode on/off. Setting persists across sessions. |
| **Add memory** | `#` key | Quickly add memory content to CLAUDE.md (e.g. “remember this rule”). |

<br>

---

## V. Latest Features (v2.1.x, as of February 2026)

Major additions in Claude Code v2.1.x:

### 1. `/insights` - Usage Pattern Analysis Report

`/insights` analyzes the last 30 days of session data and generates an **interactive HTML report**.

```bash
# Run inside a Claude Code session
/insights
```

**Data analyzed:**
- Session logs in `~/.claude/` (prompts + Claude responses)
- Tool usage patterns, error patterns, interaction patterns
- Source code itself is not analyzed (privacy preserved)

**Report contents:**

| Item | Description |
|:---|:---|
| **Usage stats** | Number of messages, sessions, and file edits |
| **Project breakdown** | What kind of work you did in each project |
| **Tool usage patterns** | Charts showing most-used tools |
| **Language usage** | Which programming languages you worked in |
| **Bottlenecks** | Patterns that reduce productivity |
| **Improvement suggestions** | Personalized suggestions, custom skill recommendations, and hook recommendations that can be copied into CLAUDE.md |

The report is saved to `~/.claude/usage-data/report.html` and opened automatically in your browser.

> Suggestions in `/insights` include a **Copy button**, so you can paste directly into CLAUDE.md. This is highly useful because the optimization guidance is personalized from your own usage patterns.
{: .prompt-tip }

### 2. Extended Thinking & Effort System

Claude Code supports **Extended Thinking**, where Claude performs deeper internal reasoning before replying, greatly improving accuracy on complex problems.

**How to toggle Thinking:**

| Method | Description |
|:---|:---|
| `Tab` key | Toggle Thinking mode on/off instantly in session |
| `/config` | Enable/disable Thinking from settings |
| Environment variable `MAX_THINKING_TOKENS=8000` | Set Thinking token budget directly (minimum 1,024) |

**Effort levels (Opus 4.6 only):**

You can set **Effort level** when choosing a model via `/model`. It controls how deeply Claude reasons.

| Effort | Use Case | Token Usage | Recommended For |
|:---:|:---|:---:|:---|
| **Low** | Fast response, simple tasks | Low | Simple classification, quick lookup, batch processing |
| **Medium** | Balanced performance | Medium | General coding tasks |
| **High** (default) | Best reasoning quality | High | Complex reasoning, difficult coding tasks |
| **Max** | Absolute best performance | Highest | Extremely complex architecture analysis, multi-step reasoning |

```bash
# Set Effort level via environment variable
CLAUDE_CODE_EFFORT_LEVEL=high claude

# Or change from /model in-session
/model
# -> choose model, then adjust Effort slider
```

> **Adaptive Thinking**: On Opus 4.6, **Adaptive Thinking** is recommended over manually setting `budget_tokens`. Claude adjusts reasoning depth **dynamically** based on prompt complexity. Effort level controls that range.
{: .prompt-info }

### 3. Fast Mode

**Fast mode** keeps the same model but can increase output token generation speed by up to **2.5x**. It is not a model switch; it uses a faster inference path on the same model.

```bash
# Toggle inside session
/fast

# Lightning icon (↯) appears when enabled
# Setting persists across sessions
```

> Fast mode uses **premium pricing** ($30/$150 per MTok). It is useful for rapid iteration in prototyping, but choose it selectively with cost in mind.
{: .prompt-warning }

### 4. Agent Teams (Research Preview)

**Agent Teams** lets multiple Claude Code instances **collaborate as a team**. One orchestrator coordinates the whole task while sub-agents process different parts in parallel.

```
┌─────────────────────────────┐
│      Orchestrator (Leader) │
│  Coordinates and dispatches │
└──────┬──────┬──────┬────────┘
       │      │      │
  ┌────▼──┐ ┌─▼───┐ ┌▼─────┐
  │Agent 1│ │Agent2│ │Agent3│
  │Backend│ │Front │ │Tests │
  └───────┘ └─────┘ └──────┘
```

- Each sub-agent runs in its own **tmux pane**
- Independent work runs **in parallel** to speed up large tasks
- Currently in **research preview** (subject to change)

### 5. Auto Memory

Claude Code can **automatically remember context across sessions**. It runs in the background without manual setup.

**How it works:**

| Indicator | Meaning |
|:---|:---|
| `Recalled X memories` | Loaded memories from previous sessions at startup |
| `Wrote X memories` | Saved snapshot of current work during session |

- Automatically stores project patterns, key commands, and user preferences
- Saved at `~/.claude/projects/<project-hash>/<session-id>/session-memory/summary.md`
- Press `#` to quickly add memory to CLAUDE.md

> Auto Memory is separate from CLAUDE.md. CLAUDE.md is explicit, user-managed rules; Auto Memory is implicit context extracted by Claude. Using both together is most effective.
{: .prompt-info }

### 6. Opus 4.6 & 1M Token Context (Beta)

The latest model, **Claude Opus 4.6**, supports a **1M-token context window** in beta.

| Feature | Description |
|:---|:---|
| **1M token context** | 5x larger than 200K. Enables full analysis of large codebases in one pass |
| **Adaptive Thinking** | Dynamically adjusts reasoning depth by task complexity |
| **Context Compaction** | Summarizes old context in long sessions to push past limits |
| **Agent Teams** | Supports multi-agent collaboration |

### 7. Model Comparison (as of February 2026)

| Model | Context | Speed | Reasoning | Cost | Recommended Use |
|:---|:---:|:---:|:---:|:---:|:---|
| **Opus 4.6** | 200K (1M beta) | Medium | Best | High | Architecture design, complex refactoring, Plan mode |
| **Opus 4.6 Fast** | 200K (1M beta) | Fast (2.5x) | Best | Very High | Rapid prototyping, iterative work |
| **Sonnet 4.5** | 200K | Fast | Strong | Medium | General implementation, coding, debugging |
| **Haiku 4.5** | 200K | Very Fast | Good | Low | Simple tasks, bulk processing |

> **Hybrid strategy**: Plan with Opus (`/model` -> Opus), implement with Sonnet (`/model` -> Sonnet). This **opusplan** pattern can reduce costs by **60-80%** versus using Opus for everything.
{: .prompt-tip }

<br>

---

## VI. Deep Dive: Context Window

To use Claude Code effectively, understanding the **context window** is essential.

### What Is the Context Window?

The context window is the **maximum token size** an LLM can process at once. For Claude models:

| Model | Context Window | Characteristics |
|:---|:---|:---|
| **Claude Opus 4.6** | 200K (1M beta) | Strongest reasoning, ideal for complex architecture analysis |
| **Claude Sonnet 4.5** | 200K tokens | Faster response, efficient for general coding |

> **How large is 200K tokens?** Roughly 150,000 English words, around 300 A4 pages. In practice, code and Korean are less token-efficient, so usable size is smaller. 1M tokens is about 5x that, roughly 1,500 A4 pages.
{: .prompt-info }

### Why Context Window Matters

LLMs are **stateless** per request. A new chat with Claude Code is like working with a **new teammate every time**. Earlier information is remembered only if it stays inside the current context window.

```
[System Prompt] + [CLAUDE.md] + [Chat History] + [Current Prompt] = Total token usage
                                                                ↕
                                                      Context window limit
```

When context fills up:
1. **Auto-compact** triggers and summarizes prior conversation
2. **Information loss/distortion** can occur during summarization
3. Existing plan context can disappear

### Structural Issues with Auto-Compact

Once auto-compact runs, it is **not reversible**. Original conversation is permanently compressed, which can cause:

| Issue | Description |
|:---|:---|
| **Context distortion** | Summarization can alter the original meaning |
| **Temporal context loss** | Sequential context like “Based on A earlier, do B now” can disappear |
| **Information fragmentation** | Related information gets split, reducing reasoning quality |

> Auto-compact often summarizes a “middle segment” of the session. Instead of summarizing all of Phase 1, it may compress around Phase 1.2-1.5.
{: .prompt-warning }

### Context Management Strategies

**1. Use manual `/compact` regularly**
- Do not rely only on auto-compact; run `/compact` at good checkpoints
- You can target key content, e.g. `/compact focused on current todo list and progress`

**2. Use `/clear` per task**
- Split large work into multiple sessions
- Start each session with `/clear` for clean context

**3. Use CLAUDE.md well**
- Put recurring project information into CLAUDE.md
- It auto-loads each session and saves context budget

**4. Reference external documents**
- Write complex plans in separate `.md` files and reference with `@filename`
- Usually more efficient than keeping full plans directly in context

<br>

---

## VII. Understanding the CLAUDE.md File

### What Is CLAUDE.md?

CLAUDE.md is your project’s **AI onboarding document**. Like a new teammate reading project docs, Claude Code reads this file every session to understand your project.

### What to Include in CLAUDE.md

```markdown
# CLAUDE.md

## Project Overview
- Project description, tech stack, architecture summary

## Build & Development Commands
- Build, test, and run commands

## Code Conventions
- Coding style, naming conventions, file structure

## Architecture
- Main directory structure, core module descriptions

## Common Patterns
- Frequently used patterns in this project
- “Do not do this” rules (prevent repeated Claude mistakes)
```

### Memory Nesting

CLAUDE.md can be [layered across multiple levels](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories):

| Location | Scope | Purpose |
|:---|:---|:---|
| `~/.claude/CLAUDE.md` | **Global (user-level)** | Rules shared across all projects |
| `./CLAUDE.md` | **Project root** | Applies to entire project |
| `./src/CLAUDE.md` | **Subdirectory** | Applies only to specific modules/directories |

> Do **not** use `/init` output as-is forever. Add your real code conventions, design direction, and recurring mistakes yourself, then keep improving it.
{: .prompt-warning }

<br>

---

## VIII. Plan & Execute Workflow

### Core Principle

The key to effective Claude Code usage is clearly separating **Plan** and **Execute** phases.

### Model Selection Strategy

| Phase | Recommended Model | Why |
|:---|:---|:---|
| **Planning** | Opus | Better for complex reasoning, architecture analysis, strategy |
| **Implementation** | Sonnet | Faster, cost-efficient, great for direct coding work |

```
1. /model -> select Opus
2. Press Shift+Tab twice -> enter Plan mode
3. Build plan and todo list
4. /model -> switch to Sonnet
5. Implement code step by step
```

### Plan-Mode Workflow

**Step 1: Explore and plan**

Start in Plan mode (Shift+Tab twice):

- Build implementation strategy
- Break work into **independently testable steps**
- Estimate effort/time
- Include UI/library decisions

> Detailed prompting matters. For example: “Break implementation into step-by-step tasks. Each step must be independently testable, and estimate time for each.”
{: .prompt-tip }

**Step 2: Finalize plan and execute**

Once the plan is satisfactory:
1. Press `Shift+Tab` to switch to **Auto-accept edits mode**
2. Let Claude execute **one-shot implementation** following the plan

**Advantages of Plan mode:**

| Advantage | Description |
|:---|:---|
| **Context continuity** | Plan-mode todo list persists even in long sessions, preserving task continuity |
| **Dynamic updates** | You can revise the plan immediately if gaps appear during implementation |
| **Lower hallucination risk** | Clear plan prevents drifting in wrong directions |

> When possible, maintain a checklist `.md` file for the current task and keep it updated continuously.
{: .prompt-tip }

### Using a PRD (Product Requirements Document)

A simple todo plan is fine, but for **large-scale work or refactoring**, a PRD is more effective.

Include in PRD:
- **Goal and background**: why this work is needed
- **Requirements**: functional and non-functional
- **Scope**: included/excluded items
- **Design direction**: architecture decisions
- **Success criteria**: completion conditions

<br>

---

## IX. Safety & Control

### Understanding Permission Modes

| Mode | Description | When to Use |
|:---|:---|:---|
| **Default mode** | Requires approval for file edits and command execution | Critical projects, learning phase |
| **Auto-accept** | File edits auto-approved | Execution phase after plan is finalized |
| **dangerously-skip-permissions** | Auto-approves all permissions | Recommended only in sandboxed environments |

### Fine-Grained Control with `/permissions`

Instead of `--dangerously-skip-permissions`, it is recommended to pre-allow only safe, frequently used commands via `/permissions`.

```bash
# Saved in .claude/settings.json and can be shared with team
# Example: pre-allow git, npm, and build commands
```

### Safe Usage Principles

1. Start in approval mode and review actions one by one
2. Switch to Auto-accept only after plan is finalized
3. If implementation diverges, roll back with `Esc` twice (Rewind)
4. If the plan is wrong, revise the plan itself

<br>

---

## X. 13 Advanced Usage Tips (Creator Workflow)

Practical tips directly shared by Claude Code’s creator.

### 1. Build a parallel execution environment

Run **five Claude sessions in parallel** in terminal. Label tabs 1-5, and use [system notifications](https://code.claude.com/docs/en/terminal-config#iterm-2-system-notifications) to know when input is needed.

### 2. Run web and local in parallel

- Run **5-10 additional Claude sessions** in parallel on `claude.ai/code`
- Handoff local sessions to web (`&`) or switch bidirectionally with `-teleport`
- Start sessions from iOS app and check later

### 3. Model choice: Opus with thinking

- Use **Opus 4 with thinking** for all work
- Bigger/slower than Sonnet, but requires less steering and has stronger tool use
- In practice, often reaches final outcomes **faster** than smaller models

### 4. Accumulate team knowledge with CLAUDE.md

- Maintain one shared **CLAUDE.md** for the whole team
- Check it into git; team contributes multiple times weekly
- Add guidance whenever Claude behaves incorrectly to prevent repeat mistakes

### 5. Update CLAUDE.md during code review

- In peer PR reviews, tag **@.claude** to add updates into CLAUDE.md
- Use **Claude Code GitHub Action** (`/install-github-action`)

### 6. Plan mode + auto-accept workflow

- Start most sessions in **Plan mode** (Shift+Tab twice)
- Iterate until plan quality is high
- Switch to **Auto-accept mode** to finish in **one shot**
- **Good planning is critical**

### 7. Automate repetitive loops with slash commands

- Use slash commands for each frequent inner-loop workflow
- Store them in `.claude/commands/` and check into git
- Example: use `/commit-push-pr` dozens of times daily
- Use [inline bash](https://code.claude.com/docs/en/slash-commands#bash-command-execution) to precompute `git status`, reducing unnecessary model round trips

### 8. Use sub-agents

Use several [sub-agents](https://code.claude.com/docs/en/sub-agents) regularly:
- **code-simplifier**: simplify code after implementation
- **verify-app**: detailed instructions for end-to-end testing

### 9. Auto-format with PostToolUse hooks

- Use **PostToolUse hooks** to automate formatting
- Claude usually produces well-formatted code already; hooks handle the remaining **10%**

### 10. Permission management style

- Do not use `--dangerously-skip-permissions`
- Instead, pre-allow safe bash commands via `/permissions`
- Check `.claude/settings.json` into git for team sharing

### 11. Integrate external tools

Let Claude Code operate external tools:
- Search and post to **Slack** (via MCP)
- Run **BigQuery** queries (`bq` CLI)
- Pull error logs from **Sentry**
- Check `.mcp.json` into git and share MCP setup across team

### 12. Handling long-running tasks

For very long jobs, choose one of these:
- **(a)** Prompt Claude to validate work using a **background agent** at completion
- **(b)** Use [agent Stop hooks](https://code.claude.com/docs/en/hooks-guide) for more deterministic validation
- **(c)** Use [ralph-wiggum plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum)

### 13. Most important tip: verification feedback loop

> The **single most important factor** for great Claude Code results: provide Claude with a **way to verify the work**.
{: .prompt-warning }

With this feedback loop, final output quality can improve by **2-3x**:
- Verify results via bash commands
- Run test suites
- Test app in browser/simulator
- Test UI with [Chrome extension](https://code.claude.com/docs/en/chrome)

**Investing in robust verification loops has the highest ROI.**

<br>

---

## XI. SDD (Spec-Driven Development)

### What Is SDD?

SDD (Spec-Driven Development) moves beyond “telling Claude what to do” and lets AI implement and test against **team-shared technical specs**.

**Core value of SDD:**
- Minimize context loss
- Reduce hallucinations
- Improve team collaboration efficiency

### Install and Use Spec Kit

[Spec Kit](https://github.com/github/spec-kit) is a tool for SDD.

```bash
# Initialize Spec Kit
specify init --here
# -> type 'y'
# -> select 'claude'
# -> select 'sh'
```

After setup, run `claude` in a new session to access additional commands.

### Spec Kit Workflow

| Command | Phase | Description |
|:---|:---|:---|
| `/speckit.constitution` | Rules | Standards based on CLAUDE.md, code rules, architecture |
| `/speckit.specify` | Requirements | **What/Why** focused, no tech stack |
| `/speckit.clarify` | Clarification | Fill missing spec details |
| `/speckit.plan` | Planning | Decide tech stack/architecture here |
| `/speckit.tasks` | Task breakdown | Split into implementable units |
| `/speckit.implement` | Implementation | Write actual code |
| `/speckit.analyze` | Analysis (optional) | Check consistency across documents |
| `/speckit.checklist` | Checklist (optional) | Quality checks |

### Guide for `/speckit.specify`

`specify` is for **What/Why**. Implementation details (How) belong in `/speckit.plan`.

**WHAT (requirements)**
- User actions that must be possible
- Rules the system must guarantee (validation/constraints/compatibility)
- Deliverables (assets, prefabs, registration, test environment)
- Success criteria (time constraints, legacy compatibility, etc.)

**WHY (necessity)**
- Existing problems (bottlenecks, duplication, inconsistency, context loss)
- Contribution to success metrics

**Do not write these in `specify` (save for `/plan`)**
- ~~“Inject a DI container into BaseWeapon...”~~
- ~~“Create BulletRecipe as a ScriptableObject...”~~
- ~~“Optimize with ECS...”~~

<br>

---

## XII. Using Plugins

### How to Install Plugins

```bash
# Start Claude Code
claude

# Download from marketplace
/plugin marketplace add wshobson/agents

# Install selected plugins
/plugin install game-development
/plugin install debugging-toolkit
/plugin install code-refactoring
```

The [wshobson/agents](https://github.com/wshobson/agents/tree/main) repository includes many optimized agents for orchestration workflows.

### How Plugins Work

Installed plugins are **used automatically by context**:

- **Automatic activation**: relevant agent runs based on task
  - After coding -> code-reviewer agent
  - On errors -> debugger agent
- **Explicit request**: “Please review this code” -> code-reviewer activated
- **Context judgment**: simple tasks may run without extra agents

<br>

---

## XIII. Notes and Cautions

### Unity Integration Limitations

Currently, there is no direct bridge between Claude Code and Unity Editor. Because of that, Claude may not always detect Unity editor error states precisely. Still, it performs strongly in **logic analysis and code intent understanding**.

> A tool named Unity-MCP exists, but it may have security vulnerabilities. Perform security review before using it.
{: .prompt-danger }

### Caution When Using MCP Servers

When using MCP (Model Context Protocol) servers:
- Verify the source is trustworthy
- Review for security vulnerabilities
- If used in team environments, manage with a whitelist

<br>

---

## References

- [Claude Code Official Docs](https://code.claude.com/docs)
- [Spec Kit (GitHub)](https://github.com/github/spec-kit)
- [wshobson/agents Plugin Collection](https://github.com/wshobson/agents/tree/main)
- [Claude Code Memory System](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands#bash-command-execution)
- [Claude Code Sub-Agents](https://code.claude.com/docs/en/sub-agents)
