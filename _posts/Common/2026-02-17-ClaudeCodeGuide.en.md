---
categories:
- Tool
- Claude Code
date: 2026-02-17 14:00:00 +0900
difficulty: intermediate
lang: en
tags:
- claude code
- ai
- llm
- vibe coding
- claude
- anthropic
- cli
title: The Complete Guide to Claude Code - From Installation to Advanced Usage Strategies
toc: true
toc_sticky: true
---

<br>

## What is Claude Code?

**Claude Code** is an Agentic Coding Tool** developed by Anthropic. It runs directly from the terminal (CLI) and allows you to perform almost all development tasks, including writing code in natural language, refactoring, debugging, and git management.

The biggest difference from existing AI coding assistants (Copilot, Cursor, etc.) is that it **understands the entire project as a context** and is in the form of an **Agent** that can directly read and write the file system.

<br>

---

## I. Installation (macOS environment)

### Method 1: Installation via Homebrew (recommended)

| steps | command | Description |
|:---:|:---|:---|
| **1** | `brew install --cask claude-code` | Install Claude Code with Homebrew |
| **2** | `claude --version` | Check installation and version |

### Method 2: Installation via npm

| steps | command | Description |
|:---:|:---|:---|
| **1** | `node --version` | Check Node.js 18.0 or higher |
| **2** | `npm install -g @anthropic-ai/claude-code` | npm global install |
| **3** | `claude --version` | Verify installation |

> If you don't have Node.js, you can install the LTS version from [official site](https://nodejs.org/), or install it with `brew install node`.
{: .prompt-tip }

<br>

---

## II. Initial settings

### 1. Login

After installation, log in to the terminal.

```bash
claude login
```

When the browser opens, log in to your Anthropic account and select the CLI tool type.

### 2. Check token usage

You can check your current token usage at [https://claude.ai/settings/usage](https://claude.ai/settings/usage).

> **What is a Token?** It is the minimum unit by which LLM processes text. In English, approximately 1 word = 1.3 tokens, in Korean, 1 letter = approximately 2 to 3 tokens. Claude Code consumes both **input tokens (prompt + context)** and **output tokens (response)**.
{: .prompt-info }

<br>

---

## III. IDE integration (recommended environment)

You can use it directly from the terminal, but **we strongly recommend using it connected to an IDE**. It's much more efficient because you can see code changes in real time.

### VS Code (recommended)

1. Install [VS Code](https://code.visualstudio.com/)
2. Open the project folder with **Open Folder**
3. Open **Terminal > New Terminal** from the top menu.
4. Enter `claude` in the terminal and run it.

```bash
# 프로젝트 디렉토리에서 실행
cd /path/to/your/project
claude
```

> When Claude Code runs, it automatically reads the `CLAUDE.md` file in the project root to understand the project's architecture, coding rules, and work procedures. We then provide more accurate and relevant answers tailored to your needs.
{: .prompt-tip }

### JetBrains (Rider, IntelliJ, etc.)

It can also be executed using the `claude` command in JetBrains IDE's built-in terminal. However, I personally liked the terminal usability of VS Code better.

<br>

---

## IV. Complete summary of key commands

### Session management commands

| command | Features | Description |
|:---|:---|:---|
| `claude` | Welcome to Claude Code | Start a new session in the current directory |
| `claude -c` / `claude --continue` | Continue recent session | Continuing from the last conversation |
| `claude -r` / `claude --resume` | Recall previous conversation | Resume by selecting from a list of past sessions |
| `claude --verbose` | Detailed log mode | Detailed log output useful for debugging |
| `claude --dangerously-skip-permissions` | Skip permission check | Automatically allow access/execution of all files (Caution!) |

### Slash commands in session| command | Features | Detailed description |
|:---|:---|:---|
| `/clear` | **Context initialization** | Start a new conversation. **Most important command.** Make sure you have enough context windows to reduce the chance of hallucination. It is recommended to start with `/clear` on a task basis. |
| `/compact` | Conversation Compression | Summarize/condense the conversation to free up a context window. You can also compress it around specific content like `/compact 핵심 내용`. |
| `/model` | Change model | Select models such as Opus, Sonnet, etc. Opus for planning and Sonnet for implementation are efficient. |
| `/resume` | Resume previous conversation | You can recall past conversations. |
| `/config` | Settings Management | Adjust various settings such as verbose, model, todo list, etc. |
| `/memory` | Edit CLAUDE.md | Edit the project/global CLAUDE.md file directly |
| `/init` | Project initialization | Claude analyzes the entire project and automatically generates CLAUDE.md |
| `/terminal-setup` | Terminal line wrapping settings | Set line breaks to `Shift+Enter` |
| `/plugin` | Plugin Management | Explore, install, and uninstall plugins |
| `/agents` | Agent Management | Check and manage custom agents |
| `/mcp` | MCP Server Management | Model Context Protocol server settings |
| `/statusline` | Status line settings | Terminal status bar display settings |
| `/todos` | Check Todo list | Check your current task list |
| `/permissions` | Permission Management | Setting pre-allowance rules for bash commands, etc. |
| `/insights` | **Usage pattern analysis** | Generates an HTML report by analyzing sessions for the last 30 days. Provides usage patterns, bottlenecks, and workflow improvement suggestions. |
| `/fast` | **Toggle Fast Mode** | Fast output mode switching. A lightning bolt icon (↯) appears and persists between sessions. |

### update command

```bash
# Claude Code 업데이트 (npm 설치인 경우)
claude update

# Homebrew로 설치한 경우
brew upgrade claude-code
```

### Special features

| Features | How to use | Description |
|:---|:---|:---|
| **Refer to file** | `@파일명` | You can directly reference files within the project by adding `@`, like `@GameHandler.cs`. |
| **Image attached** | Drag and drop / `Cmd+Shift+4` and paste | Attaching a screenshot or UI design greatly increases efficiency by providing visual context. The use of images is also recommended in official documents. |
| **Rewind** | `Esc` Tap 2 | Stops the current conversation and reverts to a previous checkpoint. You can select from previous conversation/code/dialogue+code. This is very useful when hallucination is detected. |
| **Change Mode** | `Shift+Tab` | Switch between Plan mode / Auto-accept mode / Basic mode |
| **Thinking toggle** | `Tab` | Turn Extended Thinking mode on and off. Settings are retained between sessions. |
| **Add Memory** | `#` key | Quickly add reminders to CLAUDE.md. It's used for things like "Remember this rule." |

<br>

---

## V. Latest features (v2.1.x, as of February 2026)

These are the main features added in Claude Code v2.1.x.

### 1. `/insights` - Usage pattern analysis report

`/insights` is a command that analyzes session data for the last 30 days and generates an **interactive HTML report**.

```bash
# Claude Code 세션 내에서 실행
/insights
```

**Analyzed by:**
- Session history stored in `~/.claude/` (prompt + Claude response)
- Tool usage patterns, error patterns, interaction patterns
- The source code itself is not analyzed (privacy guaranteed)

**What the report includes:**| Item | Description |
|:---|:---|
| **Usage Statistics** | Number of messages, number of sessions, file modification history |
| **Analysis by project** | What projects did you mainly work on? |
| **Tool Usage Pattern** | Visualize with charts which tools you use the most |
| **Usage by language** | What programming language did you work in |
| **Bottleneck** | Identify patterns that reduce productivity |
| **Improvement Suggestions** | Custom suggestions, Custom Skill recommendations, Hook recommendations that can be copied to CLAUDE.md |

The report is saved to `~/.claude/usage-data/report.html` and automatically opens in your browser.

> The suggestion from `/insights` includes a **Copy button** so you can paste it directly into CLAUDE.md. This is very useful as it offers customized optimization suggestions based on your usage patterns.
{: .prompt-tip }

### 2. Extended Thinking & Effort System

Claude Code supports **Extended Thinking** functionality. This forces Claude to think deeply internally before responding, which greatly improves accuracy in complex problems.

**How to toggle Thinking:**

| method | Description |
|:---|:---|
| `Tab` key | Toggle Thinking Mode On/Off on the fly within a session |
| `/config` | Enable/Disable Thinking in Settings |
| Environment variable `MAX_THINKING_TOKENS=8000` | Specify your own Thinking token budget (minimum 1,024) |

**Effort level (Opus 4.6 only):**

You can adjust the **Effort level** when selecting a model in the `/model` command. This controls how deeply Claude will reason.

| Effort | Use | Token Consumption | Recommendation situation |
|:---:|:---|:---:|:---|
| **Low** | Fast response, simple operation | Less | Simple sorting, fast lookup, bulk processing |
| **Medium** | Balanced Performance | Normal | Common Coding Tasks |
| **High** (default) | Highest quality inference | many | Complex reasoning, difficult coding problems |
| **Max** | Absolute Best Performance | max | Extremely complex architecture analysis, multi-level reasoning |

```bash
# Effort 레벨 환경변수로 설정
CLAUDE_CODE_EFFORT_LEVEL=high claude

# 또는 세션 내에서 /model로 변경
/model
# → 모델 선택 후 Effort 슬라이더 조정
```

> **Adaptive Thinking**: In Opus 4.6, **Adaptive Thinking** is recommended instead of specifying `budget_tokens` directly. Claude **dynamically** adjusts his thinking depth based on the complexity of the question. You can control this range through the Effort level.
{: .prompt-info }

### 3. Fast mode

**Fast mode** uses the same model but **speeds up output token generation by up to 2.5x**. Rather than changing the model, it uses a fast inference path from the same model.

```bash
# 세션 내에서 토글
/fast

# 활성화되면 번개 아이콘(↯) 표시
# 설정은 세션 간 유지됨
```

> Fast mode is subject to **premium rate** ($30/$150 per MTok). This is useful in the prototyping phase where rapid iteration is required, but use it selectively due to cost.
{: .prompt-warning }

### 4. Agent Teams (Research Preview)

**Agent Teams** is a feature where multiple Claude Code instances **collaborate as teams**. A single orchestrator coordinates the entire operation, with each subagent processing different parts in parallel.

```
┌─────────────────────────────┐
│      Orchestrator (리더)      │
│    전체 작업 조율 및 분배       │
└──────┬──────┬──────┬────────┘
       │      │      │
  ┌────▼──┐ ┌─▼───┐ ┌▼─────┐
  │Agent 1│ │Agent2│ │Agent3│
  │백엔드  │ │프론트│ │테스트 │
  └───────┘ └─────┘ └──────┘
```

- Each subagent runs in its own **tmux pane**
- Speed up large-scale operations by processing independent tasks **in parallel**
- Currently in **Research Preview** phase (subject to change)

### 5. Auto Memory

A feature that allows Claude Code to **automatically remember context between sessions**. It operates in the background without manual settings.

**How it works:**

| display | meaning |
|:---|:---|
| `Recalled X memories` | When starting a session, load memories from previous sessions |
| `Wrote X memories` | Saves a snapshot of current work during a session |

- Automatically saves project patterns, main commands, and user preferences
- Save to `~/.claude/projects/<project-hash>/<session-id>/session-memory/summary.md`
- You can quickly add memory to CLAUDE.md with the `#` key.

> Auto Memory is separate from CLAUDE.md. CLAUDE.md is an explicit rule managed directly by the user, and Auto Memory is an implicit context automatically extracted by Claude. Using the two together is most effective.
{: .prompt-info }### 6. Opus 4.6 & 1M Token Context (Beta)

The latest model, **Claude Opus 4.6**, supports the **1M token context window** in beta.

| Features | Description |
|:---|:---|
| **1M Token Context** | 5 times the existing 200K. Able to analyze entire large code base at once |
| **Adaptive Thinking** | Dynamically adjust inference depth based on question complexity |
| **Context Compaction** | Overcoming limitations by automatically summarizing old context in long conversations |
| **Agent Teams** | Multi-agent collaboration support |

### 7. Comparison by model (as of February 2026)

| model | Context | speed | reasoning skills | cost | Recommended use |
|:---|:---:|:---:|:---:|:---:|:---|
| **Opus 4.6** | 200K (1M beta) | Normal | Strongest | High | Architecture Design, Complex Refactoring, Plan Mode |
| **Opus 4.6 Fast** | 200K (1M beta) | Fast (2.5x) | Strongest | very high | Rapid prototyping, iterative work |
| **Sonnet 4.5** | 200K | Fast | Excellent | Normal | General implementation, code writing, debugging |
| **Haiku 4.5** | 200K | Very fast | Good | low | Simple operation, high volume processing |

> **Hybrid Strategy**: By using the **opusplan** pattern, which involves planning with Opus (`/model` → Opus) and implementing with Sonnet (`/model` → Sonnet), **60-80% cost savings** are possible compared to using Opus alone.
{: .prompt-tip }

<br>

---

##VI. Deep understanding of the context window

To use Claude Code effectively, an understanding of the **Context Window** is essential.

### What is a context window?

The context window is the maximum size of tokens the LLM can process at one time. Based on Claude model:

| model | context window | Features |
|:---|:---|:---|
| **Claude Opus 4.6** | 200K (1M beta) | The most powerful inference, suitable for analyzing complex architectures |
| **Claude Sonnet 4.5** | 200K tokens | Fast response, efficient for general coding tasks |

> **Approximately how much is 200K tokens?** This is approximately 150,000 words in English and approximately 300 A4 pages. However, Code and Korean have lower token efficiency so there is actually less. 1M tokens are about 5 times the size of 1,500 A4 pages.
{: .prompt-info }

### Why the context window is important

For LLM, every request is **Stateless**. This means that each new chat with Claude Code is like collaborating with a new team member every time. Previous conversations are remembered only when they are within the context window.

```
[시스템 프롬프트] + [CLAUDE.md] + [대화 이력] + [현재 질문] = 총 토큰 사용량
                                                              ↕
                                                    컨텍스트 윈도우 한계
```

When the context window is full:
1. **Auto-compact** is triggered → Previous conversations are automatically summarized
2. **Information loss/distortion** occurs during the summarization process.
3. The context of existing plans may be lost.

### Structural problems with Auto-Compact

Once Auto-compact is run, it **cannot be undone**. When it does, existing conversations are lost forever, causing the following problems:

| problem | Description |
|:---|:---|
| **Context Distortion** | The meaning of the original may be altered during the summarization process. |
| **Loss of temporal context** | Sequential context such as “Let’s do B based on A previously mentioned” disappears |
| **Information Fragmentation** | Separation of related information reduces inference quality |

> Auto-compact tends to summarize the "midpoint" of a conversation, resulting in around Phase 1.2 to 1.5 rather than all of Phase 1.
{: .prompt-warning }

### Context management strategy

**1. Cyclic Manual `/compact`**
- Do not rely on Auto-compact, but execute `/compact` directly at the appropriate time.
- Key contents can be specified like `/compact 현재 Todo 리스트와 진행 상황을 중심으로`

**2. `/clear`** on a per-task basis
- Separate one large task into multiple sessions
- Each session starts in a clean context with `/clear`

**3. Using CLAUDE.md**
- Record project information that needs to be repeated every time in CLAUDE.md
- Automatically loaded for each new session, saving context**4. External documentation reference**
- Complex plans should be written in a separate `.md` file and referenced as `@파일명`
- More efficient than maintaining the plan directly within the context window

<br>

---

## VII. Understanding the CLAUDE.md file

### What is CLAUDE.md?

CLAUDE.md is the project's **"AI Onboarding Document"**. Just as new team members read the project wiki when they join the company, Claude Code reads this file every session to understand the project.

### What to include in CLAUDE.md

```markdown
# CLAUDE.md

## Project Overview
- 프로젝트 설명, 기술 스택, 아키텍처 개요

## Build & Development Commands
- 빌드, 테스트, 실행 명령어

## Code Conventions
- 코딩 스타일, 네이밍 규칙, 파일 구조

## Architecture
- 주요 디렉토리 구조, 핵심 모듈 설명

## Common Patterns
- 프로젝트에서 자주 사용하는 패턴
- "이렇게 하지 마라" 규칙 (Claude가 반복하는 실수 방지)
```

### Memory Nesting

CLAUDE.md can be [organized into multiple layers](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories):

| Location | range | Use |
|:---|:---|:---|
| `~/.claude/CLAUDE.md` | **Global (per user)** | Rules common to all projects |
| `./CLAUDE.md` | **Project Root** | Apply to the entire project |
| `./src/CLAUDE.md` | **Subdirectory** | Applies only to specific modules/directories |

> **Do not use the CLAUDE.md automatically generated by the `/init` command.** You must manually add the project's code rules, design direction, and common mistakes and continuously improve it.
{: .prompt-warning }

<br>

---

## VIII. Plan-Execute Workflow (Plan & Execute)

### Core Principles

The key to using Claude Code is to clearly separate the **Plan** and **Execute** steps.

### Model selection strategy

| steps | Recommended Model | Reason |
|:---|:---|:---|
| **Make a plan** | Opus | Strong in complex reasoning, architecture analysis, and strategy formulation |
| **Code Implementation** | Sonnet | Fast response, cost-effective, suitable for simple implementation tasks |

```
1. /model → Opus 선택
2. Shift+Tab 2번 → Plan 모드 진입
3. 계획 수립 및 Todo 리스트 작성
4. /model → Sonnet으로 변경
5. 단계별 코드 구현 진행
```

### Plan mode-based workflow

**Step 1: Explore & Plan**

Start in Plan mode (`Shift+Tab` number 2):

- Establishment of implementation strategy
- Decompose tasks into **independently testable steps**
- Estimate expected travel time
- Includes UI/library related matters

> Detailed prompting is key. Give specific instructions such as “Break down the work to implement this feature into steps. Each step must be independently testable, and provide an estimate of how long it will take.”
{: .prompt-tip }

**Step 2: Confirm and implement plan**

Once you are satisfied with your plan:
1. Switch to **Auto-accept edits mode** with `Shift+Tab`
2. Claude implements **1-shot** according to plan

**Benefits of Plan Mode:**

| Advantages | Description |
|:---|:---|
| **Context Continuation** | The Todo list in Plan mode is maintained even if the session is longer, ensuring work continuity. |
| **Dynamic Plan Modification** | If anything is missed during implementation, you can immediately revise the plan. |
| **Reduces hallucination** | Having a clear plan prevents Claude from going in the wrong direction. |

> If possible, it is recommended to create a checklist document of the tasks currently being worked on in the form of `.md` and encourage continuous updating.
{: .prompt-tip }

### Utilize PRD (Product Requirements Document)

Although it is good to simply create a Todo list in Plan mode, it is effective to use PRD for **large-scale work or refactoring**.

PRD includes:
- **Goals and Background**: Why do we need to do this?
- **Requirements**: Functional/non-functional requirements
- **Scope**: Included/excluded
- **Design Direction**: Architectural Decisions
- **Success Criteria**: Completion Conditions

<br>

---

## IX. Safety & Control

### Understanding permission modes

| mode | Description | When to use |
|:---|:---|:---|
| **Default Mode** | Requires approval every time you modify a file/execute a command | Critical Projects, Learning Steps |
| **Auto-accept** | File modifications are automatically approved | Implementation stage after the plan is confirmed |
| **dangerously-skip-permissions** | Automatically grant all permissions | Recommended for use only in sandbox environments |

### Fine-grained control with `/permissions`It is recommended to pre-allow only frequently used safe commands with `/permissions` instead of `--dangerously-skip-permissions`.

```bash
# .claude/settings.json에 저장되어 팀과 공유 가능
# 예: git, npm, build 명령은 사전 허용
```

### Safe use principles

1. **Initially proceed in approval mode**, checking one by one.
2. Switch to Auto-accept once the plan is confirmed
3. If the function implementation is different from expected, revert to `Esc 2번` (Rewind)
4. If the plan itself is wrong, modify the plan.

<br>

---

##

These are practical tips shared directly by developer Claude Code.

### 1. Configuring parallel execution environment

**Run 5 Claudes in parallel** in your terminal. Number the tabs 1 to 5, and use [System Notifications](https://code.claude.com/docs/en/terminal-config#iterm-2-system-notifications) to know when input is needed.

### 2. Parallel operation of web and local

- `claude.ai/code` **Run additional 5 to 10 Claudes in parallel on the web**
- Handoff the local session to the web (using `&`), or switch to both directions with `-teleport`
- You can also start a session from the iOS app and check it later

### 3. Model selection: Opus with thinking

- Use **Opus 4 with thinking** for everything
- Bigger and slower than Sonnet, but **requires less steering** and **has better toolability**
- This results in a final result that is **almost always** faster** than a smaller model.

### 4. Team-based knowledge accumulation through CLAUDE.md

- Maintain a **single CLAUDE.md file** shared across the team
- Check in to git, and the whole team contributes **multiple times a week**
- Add every time Claude does something wrong **Prevent the same mistake next time**

### 5. Update CLAUDE.md during code review

- When reviewing code, tag **@.claude** in your colleague's PR and add content to CLAUDE.md
- Utilize **Claude Code GitHub Action**(`/install-github-action`)

### 6. Plan mode and auto-acceptance workflow

- Start most sessions in **Plan mode** (`Shift+Tab` number 2)
- Repeat consultations until the plan is satisfactory.
- After confirmation, switch to **Auto-accept mode** and **complete in one shot (1-shot)**
- **Good planning is really important**

### 7. Automate repetitive tasks with slash commands

- Use the slash command for each frequently performed “inner loop” workflow.
- Saved in `.claude/commands/` directory and checked into git
- Example: `/commit-push-pr` Use the slash command dozens of times every day
- Prevent unnecessary model round trips by pre-calculating git status, etc. with [inline bash](https://code.claude.com/docs/en/slash-commands#bash-command-execution)

### 8. Use of subagents

Regular use of multiple [subagents](https://code.claude.com/docs/en/sub-agents):
- **code-simplifier**: Simplifies code after work is done.
- **verify-app**: Detailed instructions for end-to-end testing

### 9. Formatting code with PostToolUse hook

- Automatically handle code formatting using the **PostToolUse hook**
- Claude generates well-formatted code by default, and hooks **take care of the remaining 10%**

### 10. Permission management method

- `--dangerously-skip-permissions` Not used
- **Pre-allow** safe bash commands with `/permissions` instead
- Check in with `.claude/settings.json` and share with your team

### 11. Take advantage of tool integrations

Claude Code **uses an external tool instead**:
- **Slack** search and post (using MCP server)
- Run **BigQuery** query (bq CLI)
- Get error log from **Sentry**
- MCP settings are shared with the team by checking in to `.mcp.json`

### 12. How to handle tasks over long periods of timeFor very long tasks, choose between three methods:
- Prompt to verify task with **Background Agent** upon completion of **(a)**
- **(b)** Verify more deterministically using [Agent Stop hook](https://code.claude.com/docs/en/hooks-guide)
- **(c)** Use [ralph-wiggum plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum)

### 13. Top Tip: Validation Feedback Loop

> The **most important** to getting great results in Claude Code: Give Claude **a way to validate his work**.
{: .prompt-warning }

Having this feedback loop will result in a **2-3x improvement** in the quality of your final output:
- Check results by executing bash command
- Run test suite
- Test your app in a browser or simulator
- Test UI with [Chrome extension](https://code.claude.com/docs/en/chrome)

**Investing in building a robust validation process is the most worthwhile thing you can do.**

<br>

---

##XI. SDD (Spec-Driven Development)

### What is SDD?

SDD (Spec-Driven Development) is a development method that goes beyond “development by telling Claude to do it verbally,” and uses AI to implement and test based on tech specifications shared by the team.

**SDD Core Values:**
- Minimize context loss
- Reduce hallucination
- Efficient team collaboration

### Installing and using the Spec Kit

[Spec Kit](https://github.com/github/spec-kit) is a tool to realize SDD.

```bash
# Spec Kit 초기화
specify init --here
# → 'y' 입력
# → 'claude' 선택
# → 'sh' 선택
```

After installation, if you run claude in a new session, new commands will be added.

### Spec Kit Workflow

| command | steps | Description |
|:---|:---|:---|
| `/speckit.constitution` | Protocol settings | CLAUDE.md and project code rules, architecture-based conventions |
| `/speckit.specify` | Requirements Definition | Based on **What/Why**. No technology stack |
| `/speckit.clarify` | Detailing | Supplementing insufficient technical documents |
| `/speckit.plan` | Planning | Decide on technology stack/architecture at this stage |
| `/speckit.tasks` | Task decomposition | Breaking it down into implementable units |
| `/speckit.implement` | implementation | Write actual code |
| `/speckit.analyze` | Analysis (Optional) | Check consistency between documents |
| `/speckit.checklist` | Checklist (optional) | Quality check |

### `/speckit.specify` Writing Guide

`specify` is the step of writing **What/Why)**. How to implement is covered in `/speckit.plan`.

**WHAT (requirement)**
- What users should be able to do (actions)
- Rules that the system must guarantee (verification/constraints/compatibility)
- Deliverables (assets, prefabs, registration, test environment)
- Success criteria (time constraints, legacy compatibility, etc.)

**WHY**
- Existing issues (bottlenecks, duplication, inconsistency, loss of context)
- Contribution to success indicators

**Do not write (this is in `/plan`)**
- ~~"Put a DI container into BaseWeapon..."~~
- ~~"Make BulletRecipe a ScriptableObject..."~~
- ~~"Optimize with ECS..."~~

<br>

---

## XII. Utilize plugins

### How to install plugins

```bash
# Claude Code 실행 후
claude

# 마켓플레이스에서 플러그인 다운로드
/plugin marketplace add wshobson/agents

# 원하는 플러그인 선택적 설치
/plugin install game-development
/plugin install debugging-toolkit
/plugin install code-refactoring
```

The [wshobson/agents](https://github.com/wshobson/agents/tree/main) repository contains a variety of agents optimized through orchestration.

### How the plugin works

Installed plugins are **automatically used**:

- **Auto Utilization**: The agent automatically operates if it matches the task characteristics.
  - After writing code → code-reviewer agent
  - When an error occurs → debugger agent
- **Explicit request**: “Please review the code” → Activate code-reviewer
- **Situation judgment**: Handle simple tasks directly without a separate agent

<br>

---

## XIII. Precautions

### Unity integration limitationsThere is currently no direct connection between Claude Code and the Unity editor. Because of this, there are cases where the error code of the Unity editor is not accurately recognized. However, **performance for logic error analysis and code intent identification is excellent.**

> There is a tool called Unity-MCP, but it has security vulnerabilities, so be sure to review its security before using it.
{: .prompt-danger }

### Caution when using MCP server

When using a Model Context Protocol (MCP) server:
- Make sure it is a trustworthy source
- Review whether there are any security vulnerabilities
- Whitelist management recommended when used by a team

<br>

---

## References

- [Claude Code official document](https://code.claude.com/docs)
- [Spec Kit (GitHub)](https://github.com/github/spec-kit)
- [wshobson/agents plugin collection](https://github.com/wshobson/agents/tree/main)
- [Claude Code Memory System](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code slash command](https://code.claude.com/docs/en/slash-commands#bash-command-execution)
- [Claude Code Sub-Agent](https://code.claude.com/docs/en/sub-agents)