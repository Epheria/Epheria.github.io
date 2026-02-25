---
title: "AI in Game Development: Insights from 2,165 Messages - A Developer's 47-Day Log"
date: 2026-02-20 12:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, AI, Game Development, Unity, Productivity, LLM, Developer Tools]
lang: en
difficulty: intermediate
toc: true
toc_sticky: true
tldr:
  - "305 sessions, 2,165 messages over 47 days — Revealing real-world data of a game developer using AI coding agents in production."
  - "Using Claude Code as a 'Technical Analyst' rather than just a 'Pair Programmer' shows overwhelming efficiency in investigation and analysis tasks like memory leak research and Gap Analysis."
  - "Summarized the achievements and limitations of advanced workflows, including multi-agent team delegation and JetBrains MCP integration, with data."
---

## Introduction

On January 5, 2026, I fully integrated Claude Code into a Unity mobile game project. This isn't just another "AI writes code" marketing pitch; I'm sharing **quantitative data from 47 days of actual use in a production codebase**.

Most AI usage reports are limited to subjective impressions like "it was convenient" or "it was amazing." This article tells a story based on numbers, extracted from Claude Code Insights — a report analyzing actual session logs provided by Anthropic.

> All figures in this post are extracted directly from the Claude Code Insights reports (as of February 13 and February 20).

---

## 1. Summary of 47 Days in Numbers

### Overall Usage Trends

Comparing the insight reports from two points in time clearly shows a shift in usage patterns.

| Metric | Day 26 (Feb 13) | Day 33 (Feb 20) | Growth Rate |
|------|-------------|-------------|------|
| Total Messages | 1,246 | 2,165 | **+74%** |
| Total Sessions | 172 | 305 | **+77%** |
| Code Lines Added | +28,556 | +56,323 | **+97%** |
| Code Lines Deleted | -1,792 | -2,729 | +52% |
| Files Modified | 188 | 396 | **+111%** |
| Daily Avg Messages | 47.9 | 65.6 | +37% |

In just 7 days, the number of messages increased by 74%. It's not just "using it more"; what's important is that the **daily average messages rose from 47.9 to 65.6**. As I became more familiar with the tool, the density of use itself increased.

### Types of Tasks Requested

| Task Type | Feb 13 | Feb 20 |
|---------|------|------|
| Bug Fixes | 5 | **14** |
| Code Implementation | 10 | 11 |
| Debugging | 7 | 10 |
| Code Analysis | 7 | 10 |
| Feature Implementation | - | 9 |
| Code Investigation | 6 | 6 |

Initially, there were many requests for code implementation, but as time went on, the **proportion of bug fixes and debugging increased significantly**. This reflects the natural transition of the project from the development phase to the stabilization phase.

---

## 2. Where Was It Used Most?

### Session Distribution by Project

```
Unity Skill Studio Editor Tooling  ████████████████████████████████████ 35 sessions
Unity Runtime Bug Fixes & Debugging ████████████████████ 20 sessions
Unity Memory Leak & Crash Investigation ██████████████████ 18 sessions
Technical Documentation & Content Writing ███████████████ 15 sessions
iOS Build & Platform Issues         █████ 5 sessions
```

**Editor tooling development** is the overwhelming number one. While building the Skill Studio tool for the Unity Editor, I implemented various features such as a recipe system, drag-and-drop graph viewer, localization, CSV export, and a weapon comparison tool. I even **modified 22 files simultaneously** in a single session.

The second most frequent use was **runtime bug fixes**. I tracked down tricky bugs occurring in actual mobile games, such as Boss HP bar UI timing issues, cumulative onClick listeners in virtual scroll cells, object pool overflow strategies, and Galaxy A41 freezing issues.

### Top 6 Most Used Tools

| Tool | Calls | Use Case |
|------|---------|------|
| Read | 1,716 | File reading and code analysis |
| Bash | 1,206 | Command execution, git history investigation |
| JetBrains get_file_text | 1,153 | IDE-integrated file reading |
| JetBrains replace_text | 897 | IDE-integrated code modification |
| Edit | 888 | Direct file editing |
| JetBrains search_in_files | 870 | Project-wide search |

What stands out here is that **Read (1,716) is almost double Edit (888)**. Much more time is spent reading code than writing it. This directly relates to the core pattern of how I utilize Claude Code.

---

## 3. Key Discovery: "Technical Analyst," Not "Pair Programmer"

The core of my usage pattern, as analyzed by Claude Code Insights, is this:

> **"You operate as a technical team lead who assigns Claude structured investigation and implementation tasks with formal reporting, intervening decisively when approaches diverge from your specific expectations."**

I don't use Claude as a "peer to code with." I act as a **team lead who delegates structured investigation and analysis tasks and receives reports**. In 305 sessions, there were only 9 commits. Most of the time is spent with Claude reading dozens of files, analyzing them, and creating structured reports.

### Why This Pattern is Effective

**1. Memory Leak Investigation is a Prime Example**

I systematically investigated DOTween sequence leaks, UniRx subscription cleanup, Addressable asset disposal, and delegate/closure retention patterns. Claude traversed dozens of files, tracked leak paths, and produced structured reports prioritized by severity.

If a human did this? It would take half a day just to track the lifecycle of a single `GameResultLayer`. Claude read all relevant files and **caught critical issues**, such as missing `.AddTo()` calls and insufficient `OnDestroy` cleanup, in a single session.

**2. Gap Analysis as a Quality Gate**

I repeatedly performed Gap Analysis to compare the completeness of actual implementation against Plan documents. In at least 7 sessions using the same pattern:

1. Read the Plan document.
2. Read all commit/implementation files.
3. Classify requirements as Completed / Partial / Missing.
4. Output a structured report.

This workflow allowed me to catch implementation omissions early.

**3. Multi-agent Team Orchestration**

I utilized Claude Code's agent team feature to handle complex multi-file tasks in parallel. I simultaneously modified 22 files across 4 task areas or delegated DOTween/UniRx/memory leak investigations to multiple agents at once.

| Metric | Feb 13 | Feb 20 |
|------|------|------|
| Parallel Session Overlap Events | 57 | 92 |
| Involved Sessions | 56 | 111 |
| Share of Total Messages | 15% | 15% |

---

## 4. Performance: What the Numbers Say

### Success Rate Trends

| Outcome | Feb 13 (50 sessions) | Feb 20 (98 sessions) |
|------|-------------|-------------|
| Fully Achieved | 32 (64%) | 58 (59%) |
| Mostly Achieved | 7 (14%) | 19 (19%) |
| Partially Achieved | 7 (14%) | 15 (15%) |
| Not Achieved | 2 (4%) | 5 (5%) |

The **Full Achievement rate is about 60%**, and including "Mostly Achieved," it's **about 78%**. This is a sufficiently productive figure compared to hiring almost any programmer.

### What Claude Does Best

| Capability | Count |
|------|------|
| Multi-file Simultaneous Changes | 36 |
| High-quality Explanation/Analysis | 21 |
| Debugging | 20 |
| Fast and Accurate Search | 10 |
| Accurate Code Modification | 4 |

**Multi-file changes are the overwhelming number one**. This is a task where humans are prone to mistakes. Claude shines in tasks like changing enum values across 10 files, refactoring namespaces, or batch-replacing localization keys.

---

## 5. Limitations: The Honest Truth

The data doesn't just show the strengths. The "Where Things Go Wrong" section of Claude Code Insights is quite frank.

### Friction Type Analysis

| Friction Type | Feb 13 | Feb 20 |
|---------|------|------|
| Wrong Approach | 11 | **21** |
| Buggy Code | - | 9 |
| User Rejected | 6 | 7 |
| Excessive Changes | 2 | 6 |
| Misunderstood | 3 | 5 |
| Unresponsive | 3 | 3 |

**"Wrong Approach" is the top cause of friction with 21 cases**. Specifically:

**Case 1: Claude Siding with a Critic**

I asked Claude to evaluate a code reviewer's comment about an object pool overflow strategy. Claude sided with the reviewer, saying my fallback logic was problematic. However, that design was intentional, and I had to explain to Claude, "I wrote that code that way on purpose."

> **There are moments when the AI mistakenly thinks it knows the code better than the person who wrote it.**

**Case 2: Boss HP Bar Null Return Value Change**

While fixing the boss HP bar, Claude changed a null return from `0f` to `1f`. If this had gone out, it would have caused a regression where the boss appears with full HP when it dies. Fortunately, I caught it during code review, but **Claude's first modification often contains logical errors**.

**Case 3: Investigating the Server When Only the Client is Needed**

When I requested an analysis of the game resume feature, Claude started investigating server-side code as well. I had to redirect it twice with "Only look at the client." Without explicit scope constraints, it **wastes time on unnecessary exploration**.

### The Reality of Multi-agent Teams

This is the most disappointing part of the data:

- Agents falling into idle loops and becoming unresponsive → had to create a new replacement agent.
- Missing namespace imports in code generated by agents → had to manually report compiler errors and request fixes.
- Agents not responding to status report requests as a team lead → required repeated escalation.

Compared to the success rate of single-agent sessions (32 out of 40 fully achieved), multi-agent sessions were noticeably unstable. **Currently, splitting large tasks into sequential subtasks is more stable than parallel agent teams**.

### Satisfaction Trends

| Satisfaction | Feb 13 | Feb 20 |
|------|------|------|
| Frustrated | 2 | 2 |
| Dissatisfied | 11 | 19 |
| Likely Satisfied | 56 | 95 |
| Satisfied | 5 | 9 |

**"Likely Satisfied" or higher accounts for 83%**. However, "Dissatisfied" is not insignificant with 19 cases. This is the reality of AI tools — they work incredibly well when they work, but the cost of cleaning up when they fail is substantial.

---

## 6. Deep Dive into Usage Patterns

### Usage by Time of Day

```
Morning  (06-12)  ████████████████████ 564
Afternoon(12-18)  █████████████████████████████████████████████ 1,268
Evening  (18-24)  ████████████ 333
Night    (00-06)  0
```

Usage is concentrated in the afternoon. No late-night coding — the pattern is to set the direction in the morning and work intensively with Claude in the afternoon.

### Response Time Distribution

| Range | Count | Note |
|------|------|------|
| 2-10s | 102 | Quick confirmation/approval |
| 10-30s | 181 | Short instructions |
| 30s-1m | 163 | Feedback after reviewing results |
| 1-2m | 157 | Detailed review |
| 2-5m | 160 | Reviewing deep analysis results |
| 5-15m | 162 | Multitasking |
| 15m+ | 91 | Waiting for long analysis |

**Median response time 81.2s, average 292.6s**. The fact that 1-5 minute responses are the most common, rather than under 10 seconds, shows a pattern of **carefully reviewing Claude's output and providing feedback**. This is evidence that I'm not blindly accepting it.

### Task Distribution by Language

| Language | Files | Note |
|------|--------|------|
| Markdown | 897 | Documentation, Plans, Blogs |
| HTML | 136 | Jekyll Templates |
| JSON | 61 | Config files |
| YAML | 33 | Front matter, CI/CD |
| Python | 18 | Scripts |
| Shell | 9 | Automation |

The reason Markdown is overwhelming is due to **technical documentation, Plan documents, and Gap Analysis reports**. Actual Unity C# code modification is done directly within the IDE via JetBrains MCP, so it isn't captured in separate language counts.

---

## 7. My Workflow: How to Use It Effectively

I summarize the patterns established through 47 days of trial and error.

### Pattern 1: Investigate → Report → Execute (3-Step Separation)

```
Session 1: Investigation and Analysis (Claude reads the entire codebase and writes a report)
   └─ Output: Structured report (list of issues by priority)

Session 2: Implementation Based on Report (fixing specific issues)
   └─ Input: Report from Session 1
   └─ Output: Code changes + compilation check

Session 3: Gap Analysis (Verifying implementation completeness against Plan)
   └─ Input: Plan document + latest commits
   └─ Output: Completed/Partial/Missing report
```

If you try to do everything from investigation to implementation in one session, Claude is prone to losing its way. **Clearly separating roles** is key.

### Pattern 2: Explicit Scope Constraints

```
❌ "Analyze memory leaks in GameResultLayer"
✅ "Analyze only the client code in the GameResultLayer.cs file.
    Ignore server code. Focus on missing DOTween Kill()
    and missing UniRx AddTo() calls and classify them as P0/P1/P2."
```

This single line of difference **saves 30 minutes of unnecessary server code exploration**. Many of the 21 "Wrong Approach" cases in the Insights data originated from a lack of scope specification.

### Pattern 3: Utilizing JetBrains MCP Integration

Connecting Claude Code + JetBrains IDE via MCP (Model Context Protocol) provides:

- `replace_text_in_file` (897 times) — Modify code directly within the IDE.
- `get_file_problems` (671 times) — Check for compiler errors immediately after modification.
- `search_in_files` (870 times) — Index-based search of the entire project.

This is an experience on a completely different level compared to using `grep` in a terminal. Since Claude directly utilizes the IDE's code analysis engine, **compiler errors like missing namespaces or type mismatches can be caught in real-time**.

---

## 8. Future Direction: What Insights Suggests

Claude Code Insights goes beyond simple statistics and suggests directions for improvement.

### Autonomous Gap-Analysis-to-Implementation Pipeline

Currently, there is a manual hand-off: "Gap Analysis → Human reviews report → Start implementation session." This can be combined into a single autonomous workflow:

```
Analyze commits → Identify gaps → Generate priority task list
→ Agent auto-fixes → Compilation verification → Repeat
```

### Self-Healing Multi-agent Teams

Watchdog patterns to solve agent unresponsiveness:
- Monitor response timeouts for each agent.
- Automatically create replacement agents upon unresponsiveness.
- Use compilation verification as a gate.

### Continuous Memory Leak Scanning Agent

The patterns accumulated over 10+ memory leak investigation sessions (missing DOTween Kill, missing UniRx AddTo, missing OnDestroy cleanup) can be codified into an agent that **automatically scans every PR**.

---

## 9. Practical Advice for Game Developers

Practical advice extracted from 47 days of data.

### Areas Where Claude Code is Particularly Strong
- **Memory Leak/Crash Investigation** — Systematic investigation tasks tracing leak paths across dozens of files.
- **Multi-file Refactoring** — Changing enums, cleaning up namespaces, and batch-replacing localization keys.
- **Gap Analysis** — Systematically verifying implementation completeness against Plan documents.
- **Code Analysis/Explanation** — Understanding the behavior of complex legacy code and generating structured explanations.

### Areas Where Claude Code is Weak
- **Accuracy of the First Modification** — Logical errors, wrong execution order, and missing edge cases are frequent.
- **Multi-agent Stability** — Unresponsiveness, idle loops, and missing imports make it unstable.
- **Scope Judgment** — Wastes time exploring unnecessary areas without explicit constraints.
- **Domain Intent Understanding** — Mistaking intentional design decisions for "bugs."

### Pre-introduction Checklist
1. **Code Review is Essential** — Do not merge Claude's output without verification.
2. **Explicitly Define Scope** — Provide specific constraints like "client only," "this file only," or "focus on this pattern."
3. **Use It for Investigation and Analysis First** — ROI is higher in code analysis than in code writing.
4. **Utilize JetBrains MCP Integration** — Connecting the IDE's code analysis engine significantly boosts productivity.
5. **Separate Sessions by Role** — Do not cram investigation, implementation, and verification into a single session.

---

## Conclusion

2,165 messages, 305 sessions, 56,323 lines of code added. What these numbers say is simple — **AI coding agents already provide meaningful productivity in practice, but they are not "magic."**

A 60% full achievement rate and 21 cases of wrong approaches coexist. If you view Claude not as a "wizard who writes code" but as a **"capable junior analyst who needs systematic management,"** the gap between expectations and reality narrows.

The future of AI tools in game development is bright. However, that bright future depends not on "AI doing everything on its own," but on **"developers learning how to effectively command AI."**

I will share more insights in another 47 days.

---

> The data used in this post is based on reports generated by the [Claude Code](https://claude.ai/code) Insights feature. Claude Code is a CLI-based AI coding agent from Anthropic.
