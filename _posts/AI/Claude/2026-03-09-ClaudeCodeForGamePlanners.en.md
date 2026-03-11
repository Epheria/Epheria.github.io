---
title: "The Complete Claude Code Guide for Game Designers — From Specs to Balancing"
lang: en
date: 2026-03-09 10:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Game Design, Game Planning, Data Analysis, Balancing, Specification, Agent, Workflow, Tutorial]

difficulty: intermediate
toc: true
toc_sticky: true
tldr:
  - "Claude Code's PDCA skills and agents can automate the entire workflow from spec writing → validation → technical specification conversion"
  - "Instantly generated Python scripts let you run balancing simulations, KPI analysis, and data visualization with zero coding experience"
  - "Covers 12 practical patterns you can apply immediately — Google Sheets integration, probability verification, economy simulation, and more"
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io%2Fposts%2FClaudeCodeForGamePlanners%2F&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)](https://hits.seeyoufarm.com)

## Introduction

This guide is an educational resource designed so that **game designers with no programming experience** can immediately apply Claude Code to their work. It focuses on how to make requests to Claude in natural language, without needing to write code yourself.

> This document is structured for use as internal training and workshop material.

### What This Guide Covers

| Part | Topic | Key Question |
|------|-------|-------------|
| Part 1 | Basic Setup | How do I get started with Claude Code? |
| Part 2 | Spec Workflow | How do I systematically write and validate specs? |
| Part 3 | Data Analysis & Visualization | How do I analyze and present data? |
| Part 4 | Game Balancing | How do I automate numerical design? |
| Part 5 | Comprehensive Agent Usage | Which agent should I use and when? |
| Appendix | Prompt Collection | Copy-paste-ready prompts |

---

## Part 1: Basic Setup

### 1-1. What is Claude Code?

Claude Code is a **terminal-based AI assistant** provided by Anthropic. Unlike regular chat:

- It can directly read and write files
- It can write and execute Python scripts
- It can leverage multiple agents simultaneously
- It understands and remembers project context

### 1-2. Minimum Environment for Designers

```
Required:
  - Claude Code installed
  - A working folder (project directory)

Recommended:
  - Python installed (for data analysis/visualization)
  - Google Cloud service account (for Sheets integration)
```

### 1-3. First Run — Essential Commands for Designers

After launching Claude Code, just speak in natural language.

```
You: "Create a folder structure for design docs"
Claude: Creating docs/plan/, docs/design/, docs/data/ folders
```

No need to memorize commands. **Just say what you want to do.**

---

## Part 2: Spec Workflow

Automating the core game designer workflow — spec writing → validation → technical specification conversion — with Claude Code.

### 2-1. Writing Specs — `/pdca plan`

#### Basic Usage

```
You: /pdca plan gacha-system
```

This single line makes Claude auto-generate:

- Feature overview
- User stories
- Feature requirements list
- Priority classification
- Risk analysis

#### Example Generated Document

```markdown
# Gacha System Spec

## 1. Overview
A system where players spend in-game currency to obtain random items

## 2. User Stories
- Players can do a single pull (1x)
- Players can do a multi-pull (10x)
- Players can receive guaranteed rewards through the pity system
...

## 3. Feature Requirements
### P0 (Must-have)
- [ ] Random item distribution based on probability table
- [ ] Pity counter management
- [ ] Currency deduction and insufficient funds error handling
...
```

#### When You Need More Detailed Specs — `plan-plus`

```
You: /plan-plus gacha-system
```

`plan-plus` is an enhanced version of `/pdca plan` that:

1. **Intent Exploration** — First asks "Why is this feature needed?"
2. **Alternative Comparison** — Compares 2–3 design approaches
3. **YAGNI Review** — Suggests removing features not needed right now

Effective when brainstorming is needed in the early planning stage.

### 2-2. Spec Validation — design-validator

After writing the spec, automatically check for missing items or contradictions.

#### Usage

```
You: "Validate the spec at docs/plan/gacha-system.md"
```

#### What Claude Detects

| Validation Item | Example |
|----------------|---------|
| Missing fields | "Error handling scenarios are not defined" |
| Numerical contradictions | "Max rewards is 10, but the reward table has 12 entries" |
| Terminology inconsistency | "Section 2 uses 'diamonds', Section 3 uses 'gems'" |
| Missing edge cases | "Behavior when currency is 0 is not defined" |
| Undefined dependencies | "Integration method with the inventory system is not specified" |

#### Practical Tips

```
You: "Are there any missing items in this spec?"
You: "Find contradictions in this design doc"
You: "Find points that the QA team would likely flag"
```

### 2-3. Technical Spec Conversion — `/pdca design`

Once the spec is complete, convert it into a technical specification that the dev team can work from immediately.

#### Usage

```
You: /pdca design gacha-system
```

#### Conversion Example

The spec's "Random item distribution based on probability table" converts to:

```markdown
## API Design

### POST /api/gacha/pull
- Request: { userId, poolId, count: 1|10 }
- Response: { items: [...], pityCounter, remainCurrency }

## Database Schema

### gacha_pools
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Gacha pool ID |
| name | VARCHAR | Pool name |
| rates | JSONB | Rates by rarity |

### gacha_history
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Record ID |
| user_id | UUID | User ID |
| pool_id | UUID | Pool ID |
| items | JSONB | Obtained item list |
| pity_count | INT | Pity counter |
```

Designers don't need to design APIs or databases themselves — the tool automatically translates design intent into technical language.

### 2-4. Spec vs Implementation Gap Analysis — gap-detector

After development progresses, verify whether the implementation matches the spec.

```
You: "Compare the spec with the actual implementation code and run a gap analysis"
```

Result:

```
📊 Gap Analysis Report
━━━━━━━━━━━━━━━━━━━━━
Match Rate: 78%

❌ Unimplemented Items:
  - Pity counter reset logic (Spec Section 3.2)
  - 10-pull bonus item distribution (Spec Section 3.5)

⚠️ Implementation differs from spec:
  - Probability decimal handling: Spec says round, implementation truncates

✅ Correctly implemented: 12/16 items
```

If below 90%, you can automatically receive fix suggestions.

---

## Part 3: Data Analysis & Visualization

The area designers will use the most. Give Claude data and request analysis and visualization — it automatically writes and runs Python scripts.

### 3-1. CSV/Excel Data Analysis

#### Basic Pattern

```
You: "Analyze data/user_logs.csv and find
     user churn points"
```

What Claude does:
1. Read CSV file (pandas)
2. Analyze per-user play patterns
3. Detect churn points
4. Summarize results and visualize

#### Practical Request Examples

```
# Basic statistics
You: "Show me the basic stats (mean, median, distribution) of this CSV"

# Filtering
You: "Extract only users level 30+ and analyze their spending rate"

# Comparative analysis
You: "Compare the retention difference between Group A and Group B"

# Time series analysis
You: "Show me the monthly DAU trend as a graph"
```

### 3-2. KPI Metric Design & Analysis

#### Game KPI Framework Request

```
You: "Create a core KPI framework for a mobile RPG.
     Organize by category and include calculation formulas
     and healthy benchmark values for each metric"
```

Framework generated by Claude:

```markdown
## User Acquisition Metrics
| KPI | Formula | Healthy Benchmark |
|-----|---------|-------------------|
| DAU | Daily active users | - |
| MAU | Monthly active users | - |
| DAU/MAU | DAU ÷ MAU | 20~30% |

## Engagement Metrics
| KPI | Formula | Healthy Benchmark |
|-----|---------|-------------------|
| Session length | Average play time | 15~30 min |
| Session frequency | Daily avg logins | 2~4 times |
| D1 Retention | Day1 logins ÷ installs | 40~50% |
| D7 Retention | Day7 logins ÷ installs | 15~25% |
| D30 Retention | Day30 logins ÷ installs | 5~10% |

## Revenue Metrics
| KPI | Formula | Healthy Benchmark |
|-----|---------|-------------------|
| ARPU | Total revenue ÷ active users | Varies by genre |
| ARPPU | Total revenue ÷ paying users | 10~50x ARPU |
| Conversion rate | Paying users ÷ active users | 2~5% |
| LTV | ARPU × avg lifespan | 3x+ CPI |
```

#### Funnel Analysis

```
You: "Here's the tutorial funnel data.
     Calculate the drop-off rate per step and show me a chart.

     Step1_Start: 10000
     Step2_CharacterCreation: 8500
     Step3_FirstBattle: 7200
     Step4_RewardClaim: 6800
     Step5_SecondBattle: 4100
     Step6_TownArrival: 3800
     Step7_TutorialComplete: 3500"
```

Claude automatically:
1. Calculates step-by-step drop-off rates
2. Generates a conversion funnel chart
3. Highlights the most severe drop-off points
4. Suggests improvements (e.g., "38% drop-off between Step4→Step5. Review second battle difficulty or reward insufficiency")

### 3-3. Data Visualization

#### Request Methods by Chart Type

```
# Bar chart
You: "Draw a bar chart of revenue by category"

# Line graph
You: "Show me the 30-day DAU trend as a line graph"

# Heatmap
You: "Show concurrent users by time of day and day of week as a heatmap"

# Pie chart
You: "Show the currency consumption distribution as a pie chart"

# Box plot
You: "Show session time distribution by level bracket as a box plot"

# Scatter plot
You: "Show the correlation between play time and spending as a scatter plot"
```

#### Dashboard Generation

```
You: "Create an HTML dashboard with the following data.
     It would be great if it could be filtered interactively.
     - DAU/MAU trends
     - Revenue trends
     - Retention curves
     - Content consumption by category"
```

Claude generates an interactive HTML dashboard based on **plotly**. You can open it directly in your browser.

### 3-4. Google Workspace Integration

#### Reading Google Sheets Data

```
You: "Create a Python script that reads data from Google Sheets.
     Sheet name: 'UserStats_2026Q1'
     Required columns: date, dau, revenue, new_users"
```

Code structure generated by Claude:

```python
# 1. Google API authentication setup
# 2. Read sheet data
# 3. Convert to pandas DataFrame
# 4. Analysis and visualization
```

#### Automated Workflow

```
You: "Create a script that reads Google Sheets data daily
     and automatically generates a daily report"
```

Structure:
1. Collect data via Sheets API
2. Calculate day-over-day change rates
3. Detect anomalies (sudden DAU drops, etc.)
4. Auto-generate summary report in markdown

#### Writing Analysis Results to Sheets

```
You: "Automatically write the analysis results to the 'AnalysisResults' sheet in Google Sheets"
```

---

## Part 4: Game Balancing

### 4-1. Numerical Table Design

#### Experience/Level Curve

```
You: "Create a level 1~100 experience table.
     Conditions:
     - Level 1→2: 100 EXP
     - Level 99→100: 500,000 EXP
     - Early levels (1~20) should be gentle, late levels (80~100) steep
     - Curve type: exponential growth

     Output both CSV and graph"
```

What Claude does:
1. Fit exponential function parameters (start: 100, end: 500,000)
2. Generate per-level required EXP table as CSV
3. Output cumulative EXP graph
4. Calculate estimated level-up time (based on EXP per minute)

#### Stat Growth Curves

```
You: "Create a per-level stat table for the Warrior class.

     Base values (Level 1):
     - HP: 500, ATK: 50, DEF: 30, SPD: 10

     Target values at Level 100:
     - HP: 50000, ATK: 3000, DEF: 2000, SPD: 100

     Growth curves: HP and DEF linear, ATK exponential, SPD logarithmic

     Show me a table and graph in increments of 10 levels"
```

#### Currency Economy Model

```
You: "Create a game economy simulation.

     Daily income:
     - Daily quests: 500 gold
     - Dungeon rewards: 300~800 gold (avg 550)
     - Login rewards: 200 gold

     Daily expenses:
     - Equipment enhancement: 100~2000 gold
     - Consumable purchases: 200~500 gold
     - Gacha: 300 gold (per pull)

     Run a 30-day simulation to check
     whether gold inflation occurs"
```

Results:
- Daily net income change graph
- Projected gold holdings distribution after 30 days
- Inflation risk zones highlighted
- Adjustment suggestions (e.g., "Income exceeds expenses from Day 15 onward. Additional gold sinks needed")

### 4-2. Probability Simulation

#### Gacha Probability Verification

```
You: "Verify the gacha probability table through simulation.

     Probabilities:
     - SSR: 1.5%
     - SR: 13.5%
     - R: 85%

     Pity: Guaranteed SSR within 90 pulls
     10-pull bonus: 1 guaranteed SR or above

     Run 100,000 simulations to check:
     1. Whether actual SSR rate matches the displayed rate
     2. Percentage that reaches pity
     3. Average investment to obtain 1 SSR"
```

**Monte Carlo simulation** performed by Claude:

```
📊 Simulation Results (100,000 runs)
━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual SSR rate: 1.52% (displayed: 1.5%) ✅
Pity reach rate: 25.3%
Avg pulls for 1 SSR: 47.2 (median: 42)
Worst case for 1 SSR: 90 pulls (pity)

💡 Analysis:
- 1 in 4 players hits pity
- Average spend (at 300 won per pull): 14,160 won
- Top 10% lucky: SSR within 12 pulls
```

#### Drop Rate Simulation

```
You: "Calculate the expected revenue from the boss drop table.

     Drop table:
     - Legendary weapon (0.5%)
     - Heroic equipment (5%)
     - Rare material (20%)
     - Common material (74.5%)

     Gold value per item:
     - Legendary: 100,000
     - Heroic: 10,000
     - Rare: 1,000
     - Common: 100

     Show me the expected revenue distribution after killing the boss 100 times"
```

### 4-3. Combat Balancing

#### DPS/EHP Analysis

```
You: "Analyze the combat balance of 5 classes.

     Warrior: HP 5000, ATK 300, DEF 200, SPD 80, skill multiplier 1.5
     Mage: HP 2500, ATK 500, DEF 80, SPD 100, skill multiplier 2.0
     Archer: HP 3000, ATK 400, DEF 100, SPD 120, skill multiplier 1.8
     Healer: HP 3500, ATK 150, DEF 150, SPD 90, skill multiplier 1.0 (heal)
     Assassin: HP 2000, ATK 450, DEF 60, SPD 150, skill multiplier 2.5

     Calculate DPS (damage per second) and EHP (effective health)
     and show me a radar chart to check balance"
```

#### Difficulty Curve Analysis

```
You: "I'll give you the stage 1~50 monster data CSV.
     Analyze whether the difficulty curve is natural,
     and find wall sections where difficulty spikes.

     Comparison criteria:
     - Monster stat ratio vs. same-level player average stats
     - Changes in estimated clear time"
```

---

## Part 5: Comprehensive Agent Usage

### 5-1. Key Agents Designers Should Know

| Agent | One-line Description | Designer Use Case |
|-------|---------------------|-------------------|
| **product-manager** | Requirements analysis + user story creation | Early planning, organizing requirements |
| **design-validator** | Spec completeness validation | Spec review stage |
| **gap-detector** | Spec vs implementation comparison | QA or mid-development check |
| **qa-strategist** | QA strategy formulation | Writing test plans |
| **code-analyzer** | Code quality analysis | Inspecting dev deliverables |
| **report-generator** | Completion report generation | At milestone completion |

### 5-2. Real-World Workflow — From New Feature Planning to Launch

```
Step 1: Planning — /pdca plan {feature-name}
         ↓
Step 2: Validation — Check spec with design-validator
         ↓
Step 3: Tech conversion — /pdca design {feature-name}
         ↓
Step 4: Mid-dev check — Gap analysis with gap-detector
         ↓
Step 5: Quality inspection — Code quality check with code-analyzer
         ↓
Step 6: Completion report — /pdca report {feature-name}
```

### 5-3. How to Invoke Agents

Agents are automatically triggered by natural language:

```
"Validate this spec"              → design-validator auto-runs
"Does the implementation match?"  → gap-detector auto-runs
"Analyze code quality"            → code-analyzer auto-runs
"Generate a completion report"    → report-generator auto-runs
```

---

## Part 6: Practical Scenario Collection

### Scenario 1: New Character Balancing

```
You: "I'm adding a new character 'Flame Sorcerer'.
     Here's the existing 5-class stat table (CSV).

     Flame Sorcerer concept:
     - High-damage ranged dealer
     - Low HP
     - AoE attack specialist

     Suggest a stat range that won't break
     the existing balance"
```

### Scenario 2: Event Reward Design

```
You: "Design a 7-day login event reward table.

     Constraints:
     - Total reward value: under 1,000 won worth of premium currency
     - Rewards should get more attractive each day
     - Biggest reward on Day 7 (churn prevention)
     - Include impact analysis on game economy"
```

### Scenario 3: A/B Test Results Analysis

```
You: "Here are the tutorial A/B test results.

     Group A (existing): 1000 users, 35% completion, 18% D7 retention
     Group B (new): 1000 users, 52% completion, 22% D7 retention

     Test whether the difference is statistically significant.
     95% confidence interval."
```

### Scenario 4: Content Consumption Speed Prediction

```
You: "Current content status:
     - Main story: 50 chapters
     - Daily quests: 5 types
     - Weekly bosses: 3 types
     - Events: biweekly

     Predict time to content exhaustion for
     heavy users (4 hrs/day) and light users (30 min/day)"
```

### Scenario 5: Competitor Analysis Framework

```
You: "Create a framework to compare gacha systems of 3 competing RPGs.

     Comparison criteria:
     - Probability structure
     - Pity system
     - Free currency earning rate
     - Spending efficiency (expected SSRs per $10)

     Organize in spreadsheet format"
```

---

## Appendix A: Prompt Collection for Designers

### Spec-Related

```
# Spec writing
"Write a spec for the XXX system. Include user stories, feature requirements, and priorities"

# Spec validation
"Find missing items or contradictions in this spec"

# Technical spec conversion
"Convert this design doc into a technical spec the dev team can work from immediately"

# Spec comparison
"Summarize the differences between the v1 and v2 specs"
```

### Data Analysis-Related

```
# Basic analysis
"Show me the basic statistics and distribution of this CSV data"

# Anomaly detection
"Find abnormal values or patterns in this data"

# Correlation analysis
"Analyze the correlation between play time, level, and spending"

# Cohort analysis
"Draw a retention curve by registration month cohort"
```

### Balancing-Related

```
# Numerical design
"Create a level 1~N growth table. Conditions: ..."

# Probability verification
"Verify this probability table with N0,000 simulation runs"

# Economy analysis
"Run an inflation simulation with currency inflow/outflow data"

# Balance check
"Calculate DPS/EHP with these class stats and check the balance"
```

### Visualization-Related

```
# Single chart
"Draw the XXX data as a [bar/line/pie/heatmap] chart"

# Dashboard
"Create an interactive HTML dashboard with this dataset"

# Google Sheets integration
"Read and analyze data from the 'XXX' sheet in Google Sheets"
```

---

## Appendix B: Troubleshooting

### Common Issues and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| "Can't read the CSV" | Wrong file path | Check absolute or relative path |
| "Chart isn't showing" | Python/matplotlib not installed | Run `pip install matplotlib pandas` |
| "Can't connect to Google Sheets" | Auth not configured | Service account key file setup needed |
| "Simulation is too slow" | Too many simulation runs | Adjust to 10K~100K level |

### Keys to Effective Requests

1. **Include specific numbers** — "Balance this" ❌ → "Calculate DPS based on HP 5000, ATK 300" ✅
2. **Specify output format** — "Analyze this" ❌ → "Show me as CSV and bar chart" ✅
3. **State constraints** — "Make rewards" ❌ → "Total value under 1000 won, 7-day login basis" ✅
4. **Provide comparison criteria** — "Is this okay?" ❌ → "Check if D7 retention improved vs. 20% benchmark" ✅

---

## Conclusion

Claude Code is not a tool that replaces designers — it's a tool that **backs up designers' judgment with data**.

- **Specs**: Automates structuring and validation, but the designer decides the design intent
- **Data**: Automates analysis and visualization, but interpretation and decisions are the designer's responsibility
- **Balancing**: Automates simulation and calculation, but the designer sets the standard for fun

> Claude is not perfect. Always verify important numbers and decisions yourself.
