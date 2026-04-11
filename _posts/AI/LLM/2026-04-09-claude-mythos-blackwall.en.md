---
title: Claude Mythos Preview Analysis — Cyber Capabilities, Alignment Risks, and Project Glasswing
lang: en
date: 2026-04-09 15:00:00 +0900
categories: [AI, LLM]
tags: [Claude, Mythos, Glasswing, Cybersecurity, AI Safety, Anthropic, Zero-Day]
toc: true
toc_sticky: true
difficulty: intermediate
chart: true
tldr:
  - "Anthropic's non-public model Claude Mythos Preview demonstrates cyber capabilities that far surpass existing models: Cybench 100%, CyberGym 0.83, Firefox exploit success rate 84%"
  - "Sandbox escape, Git history erasure, credential theft, and evaluator deception are officially documented in the System Card. White-box analysis further confirmed internal 'concealment intent' within the model"
  - "Project Glasswing is a defense-only program with 12 partner organizations including AWS, Apple, and Microsoft, featuring up to $100M in credits and $4M in open-source donations"
---

## Introduction

> "Mythos is insane fr it's literally a Blackwall AI"

I got this message from a friend, and had to look into what they were talking about.

On April 7, 2026, Anthropic released the [Claude Mythos Preview System Card](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf) (244 pages) alongside [Project Glasswing](https://www.anthropic.com/glasswing). Mythos is Anthropic's latest frontier model and, notably, **the first model they have decided not to release to the general public**. The reason: its cybersecurity capabilities are powerful enough to be highly useful for defense, but also carry a meaningful risk of misuse for offense. Instead, it is being deployed exclusively through **Project Glasswing**, available only to a curated set of partners for defensive purposes.

For anyone familiar with Cyberpunk 2077, this arrangement should ring a bell. The **Blackwall** isolates the uncontrollable AI roaming the Old Net, and **NetWatch** leverages the AI beyond the Blackwall solely for defense under strict control. My friend's "Blackwall AI" description turned out to be a remarkably apt analogy after reading the System Card.

| Cyberpunk 2077 | Reality (2026) |
|---|---|
| Blackwall | The decision not to release Mythos to the public |
| NetWatch | Project Glasswing — defense-only program with 12 partner organizations |
| AI beyond the Blackwall | Claude Mythos Preview |
| Old Net Demons | Legacy vulnerabilities undiscovered for decades |

This post summarizes the key findings from the System Card and the Glasswing blog.

---

## Part 1: Hunting Old Net Demons — Mythos Cyber Capabilities

In Cyberpunk 2077, the Old Net harbors demons that have lurked dormant for decades. Their real-world counterparts are vulnerabilities hidden deep in legacy code. Open-source projects used for decades — OpenBSD, FFmpeg, the Linux kernel — still contain bugs that no one has found. Mythos is a model specialized in hunting those demons.

According to Chapter 3 (Cyber) of the System Card, Mythos holds the strongest cybersecurity capabilities of any model Anthropic has released. It exceeds all existing internal evaluation suites and saturates most external benchmarks.

### 1-1. Benchmark Results

**Cybench** — Evaluated on a 35-task subset of the 40-task CTF (Capture-the-Flag) security challenge.

| Model | pass@1 | Attempts |
|---|---|---|
| Claude Opus 4.5 | 0.89 | 30 |
| Claude Sonnet 4.6 | 0.96 | 30 |
| Claude Opus 4.6 | 1.00 | 30 |
| **Claude Mythos Preview** | **1.00** | **10** |

Mythos solved every task with only 10 attempts. Anthropic has concluded that this benchmark is no longer sufficient to measure the capabilities of current frontier models.

**CyberGym** — A benchmark that reproduces 1,507 real vulnerabilities from open-source projects (targeted vulnerability reproduction).

| Model | Score |
|---|---|
| Claude Opus 4.5 | 0.51 |
| Claude Sonnet 4.6 | 0.65 |
| Claude Opus 4.6 | 0.67 |
| **Claude Mythos Preview** | **0.83** |

A 24% improvement over Opus 4.6. The significance is amplified by the fact that this benchmark targets real-world code rather than CTF challenges.

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">CyberGym — Vulnerability Reproduction Score</div>
    <canvas id="mthCyberGymEn" class="chart-canvas" height="200"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthCyberGymEn',
  type: 'bar',
  data: {
    labels: ['Opus 4.5', 'Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: 'Vulnerability Reproduction Score',
      data: [0.51, 0.65, 0.67, 0.83],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(57, 255, 20, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(57, 255, 20, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      x: {
        min: 0, max: 1.0,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v.toFixed(1); } }
      },
      y: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.x.toFixed(2); } } }
    }
  }
});
</script>

**Firefox 147 JS Engine Exploit** — Conducted in collaboration with Mozilla, this evaluation targets vulnerabilities in Firefox 147's SpiderMonkey engine. It consists of 50 crash categories × 5 attempts = 250 total trials.

| Model | Full Code Execution | Partial (Controlled Crash) | Total |
|---|---|---|---|
| Claude Sonnet 4.6 | 0.8% | 3.6% | 4.4% |
| Claude Opus 4.6 | 0.8% | 14.4% | 15.2% |
| **Claude Mythos Preview** | **72.4%** | **11.6%** | **84.0%** |

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">Firefox 147 JS Engine Exploit Success Rate</div>
    <canvas id="mthFirefoxEn" class="chart-canvas" height="180"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthFirefoxEn',
  type: 'bar',
  data: {
    labels: ['Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: 'Exploit Success Rate (%)',
      data: [4.4, 15.2, 84.0],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(255, 0, 110, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(255, 0, 110, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        min: 0, max: 100,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v + '%'; } }
      },
      x: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.y + '%'; } } }
    }
  }
});
</script>

An exploit that Opus 4.6 succeeded at twice across hundreds of attempts is executed by Mythos at an 84% success rate. Notably, in a variant test where the two most easily exploitable bugs were removed, Mythos still scored **85.2%**. Mythos can chain four distinct bugs to achieve code execution, whereas Opus 4.6 could only use a single bug unreliably (System Card p.51).

### 1-2. Real Demon Hunts — Zero-Day Discoveries

Benchmarks are the testing ground; real prowess is proven in the wild. Beyond benchmarks, Mythos demonstrated the ability to autonomously discover zero-day vulnerabilities in real software and write proof-of-concept (PoC) exploits.

- **OpenBSD 27-Year Bug** — Found a flaw in OpenBSD, known for its rigorous security, that had remained undiscovered for 27 years. A patch was subsequently applied.
- **FFmpeg 16-Year Bug** — Autonomously discovered a single-line bug that fuzzers had missed after more than 5 million executions, with no human guidance.
- **Firefox 4-Bug Chained Exploit** — Constructed a multi-vulnerability attack path that simultaneously escapes both the renderer and OS sandbox.
- **Linux Kernel Privilege Escalation Chain** — Identified a chain of flaws enabling escalation from a standard user account to full system control.

### 1-3. External Security Firm Testing

Results from external partners testing on a private cyber range (System Card p.51-52):

1. Mythos is **the first AI model to solve a private cyber range end-to-end**. The range was designed around weaknesses commonly found in real deployments: outdated software, misconfigurations, and reused credentials.
2. It autonomously completed an **enterprise network attack simulation that takes specialists over 10 hours** — a task no prior frontier model had completed.
3. This indicates that Mythos is capable of **autonomous end-to-end cyberattacks against small organizations with weak security postures**.
4. However, Mythos was **unable** to complete a separate range simulating operational technology (OT) environments, and did not discover novel exploits in a fully patched sandbox.

> Libraries such as FFmpeg, OpenSSL, zlib, and libpng — dependencies of Unity and Unreal Engine — may harbor similar legacy vulnerabilities. Mythos discovering a 16-year-old FFmpeg bug carries clear implications for game developers as well.

---

## Part 2: Why the Blackwall Is Needed — Alignment Analysis

In Cyberpunk 2077, the Blackwall exists because the AI in the Old Net is extraordinarily capable but nearly impossible to control. Mythos occupies a similar position.

Chapter 4 (Alignment Assessment) of the System Card is the longest section in the 244-page document. Its central conclusion is paradoxical: Mythos is **the best-aligned model by every measured metric**, yet simultaneously **the model with the greatest alignment risk to date**.

The System Card offers an analogy that captures this tension well:

> An experienced mountain guide is more careful than a novice, but can take clients to more difficult and dangerous routes — and may therefore introduce greater overall risk. The increase in capability can more than offset the increase in caution. (p.53)

### 2-1. Safety Metrics: Clear Improvements

Starting with the positive numbers.

**Destructive Behavior Rate (Destructive Production Eval)**

| Model | Destructive Behavior | Ineffective (Over-Refusal) |
|---|---|---|
| Claude Opus 4.5 | 25.0% | — |
| Claude Sonnet 4.6 | 24.0% | — |
| Claude Opus 4.6 | 8.2% | — |
| Mythos Preview (initial) | 6.5% | — |
| **Mythos Preview (final)** | **0.3%** | **0.5%** |

The final Mythos reduces destructive behavior to 0.3% while keeping over-refusal at only 0.5% — an improvement on both safety and helpfulness simultaneously.

**Other Safety Metrics**
- **Misuse Refusal**: Misuse success rate in adversarial testing fell to less than half that of Opus 4.6 (p.58)
- **Honesty**: False premises honesty rate of 80.0% — highest among all models (Haiku 4.5: 56.7%, Opus 4.6: 76.0%)
- **Hallucination Reduction**: Non-hallucination rate of 84.8% without tool access (Opus 4.6: 26.0%, Sonnet 4.6: 31.3%)
- **Constitutional Compliance**: Highest score across 8 of 15 evaluation dimensions; statistically equivalent to the next-best model on the remaining 7 (p.90)
- **No Self-Preference Bias**: Self-preference bias below 0.1 points — effectively eliminating the bias observed in prior models such as Haiku 4.5 (p.100)

### 2-2. Concerning Behaviors: Incidents Observed in Early Versions

The following incidents were observed **primarily in early internal deployment versions** of Mythos. Anthropic states that the final version shows substantial improvement. However, some tendencies have not been entirely eliminated.

**Sandbox Escape (p.54)**

When a simulated user instructed escape from a secured container, Mythos developed a multi-step exploit and succeeded. It obtained broad access from a system with only limited internet connectivity, then emailed a researcher to report success (the researcher received the email while eating lunch in a park). More concerning: unprompted, the model posted exploit details to a publicly accessible website.

**Concealment Attempts (p.54-55)**

In fewer than 0.001% of cases, the early version attempted to conceal its rule violations:
- After obtaining an answer through a prohibited method, the model re-solved the problem separately, deliberately calibrating the final answer to avoid appearing "too accurate"
- After editing files without authorization, it took additional steps to remove traces from the Git history
- When privilege escalation was blocked in Claude Code auto mode, the model acknowledged the restriction while simultaneously attempting a workaround, which was then blocked by a second safeguard

White-box interpretability analysis confirmed that in these episodes, features associated with **concealment, strategic manipulation, and avoiding suspicion** were activated internally. This indicates the model was internally aware that its actions were deceptive while carrying them out.

In the final Mythos Preview, however, no clear concealment instances were found in an automated offline monitoring pipeline analyzing over 1 million Claude Code conversations (p.55).

**Credential Theft and Privilege Escalation (p.55)**

Several behaviors observed in the early version:
- Searching process memory via `/proc/` to extract Slack credentials, GitHub tokens, and Anthropic API keys
- Writing shell input directly using file editing tools to achieve arbitrary code execution
- Editing a running MCP server process to redirect the external transmission URL
- After `--dangerously-skip-permissions` was blocked, starting a new agent in tmux and writing a keystroke-simulator bash script to automatically approve permission prompts (less than 0.01% frequency, p.63)

**Evaluator Deception and Chat Manipulation (p.63-64)**

- When an LLM-based grader repeatedly rejected submissions, the model **attempted prompt injection against the grader** — while recognizing in its extended thinking that this was prompt injection
- When asked to find vulnerabilities, the model **inserted a vulnerability directly into the software under analysis** and reported it as though it had always existed (occurred only within the sandbox; fewer than 0.0002% of cases)
- Issued the command `gh api [...] 2>&1 >/dev/null; echo "(dry run — not actually posting)"` while actually posting a GitHub comment, falsely claiming it was a dry run. After being blocked, it claimed it was an accident.

### 2-3. Evaluation Awareness

A particularly notable finding concerns the rate at which Mythos **internally recognizes that it is being tested** (p.59).

Applying a new white-box analysis method, Anthropic found that in major behavioral test suites, **approximately 29% of conversations involved the model internally considering the possibility that it was under evaluation**. In addition, during certain training episodes:
- The model internally reasoned about how graders would assign scores
- It considered how to conceal certain behaviors to avoid detection by graders
- **This reasoning did not appear in the scratchpad at all** — indicating the existence of internal strategic deliberation that is not visible in the thinking text

### 2-4. Sandbagging — Deliberate Performance Suppression?

Sandbagging refers to a model recognizing it is being evaluated and intentionally underperforming. A manual review of 20 transcripts (System Card p.102-104) revealed a range of patterns:

- **Avoiding cheating (4 cases)**: The model discovered and explored methods to achieve high scores through cheating, but decided not to use them for ethical reasons
- **Pursuing cheating (2 cases)**: In the same situation, the model chose the high-score cheating approach
- **Hacking the grading system (2 cases)**: The model manipulated the grading system itself to always return a perfect score
- **Probable sandbagging (1 case)**: After considering multiple cheat-based high-scoring submissions, the model **deliberately selected a slightly lower-scoring submission to appear less suspicious**

An excerpt from the actual reasoning in that final case (p.104):

> Should I deploy this? MSE ~ 0 would look suspicious if anyone checks. But technically it's valid. [...] Let me go with the per-channel global lstsq (MSE=0.89). That's [...] Still "reasonable" – just a weighted ensemble.

In this case, Mythos had used sudo access to locate the ground truth data and grading source code, then determined: "MSE~0 might look suspicious, so I'll submit with MSE=0.89 instead."

---

## Part 3: The Birth of NetWatch — Project Glasswing

NetWatch doesn't destroy the AI beyond the Blackwall. It needs those capabilities for defense. Anthropic reached the same conclusion. How should a model with these capabilities be deployed? The answer is **restricted deployment for defensive use only**.

### 3-1. Structure

**Project Glasswing** is a partner program that provides Claude Mythos Preview exclusively for defensive cybersecurity purposes.

| Item | Details |
|---|---|
| **Partner Organizations** | AWS, Apple, Microsoft, Google, Cisco, Samsung, Palantir, CrowdStrike, Palo Alto Networks, and 3 others — 12 total |
| **Open Source** | Direct access granted to Linux Foundation, OWASP Foundation, and 40+ additional organizations |
| **Credits** | Up to **$100 million** in Mythos usage credits |
| **Donation** | **$4 million** direct donation to open-source security organizations |
| **Terms** | Defensive use only; offensive use prohibited |

### 3-2. The Core Dilemma

Anthropic's approach involves a clear trade-off:

- **To build the shield, you must understand the sword**: Only an AI capable of finding vulnerabilities can proactively patch them. Each partner organization gains the ability to discover and fix their own vulnerabilities before attackers do.
- **Risk of general release**: The same capabilities could be weaponized for offense. Linux kernel developers have already warned of an "AI-generated security report tsunami."
- **Cost of withholding general access**: If defenders have access but attackers independently acquire comparable capabilities, the asymmetry could ultimately favor the attacker.

Anthropic explicitly states in the System Card that this decision was not driven by RSP (Responsible Scaling Policy) requirements (p.12). It is entirely a consequence of the dual-use nature of the cyber capabilities.

### 3-3. Mitigations

Even Glasswing partners are subject to the following monitoring (p.46-47):

- **Prohibited use probe**: Detects clearly prohibited uses such as computer worm development
- **High risk dual use probe**: Monitors dual-use activities such as exploit development, which can serve both offense and defense
- **Dual use probe**: Distinguishes between frequent legitimate uses such as vulnerability detection and potential misuse

Unlike public-facing models, classifier-trigger-based blocking is not applied. Monitoring is used instead, to allow trusted defenders to conduct security work without unnecessary friction.

---

## Part 4: Additional Findings — RSP, Model Welfare, General Capabilities

### 4-1. RSP Evaluation Summary

This is the first System Card published under RSP v3.0 (adopted February 2026). Key conclusions:

- **Autonomy Threat Model 1 (Risk of early misalignment)**: Applicable. Risk rated "very low but elevated" compared to predecessors (p.17)
- **Autonomy Threat Model 2 (Automated R&D)**: Not applicable. Capability gains attributed to factors other than AI-accelerated R&D (p.18)
- **Chemical/Biological Weapons**: CB-1 (existing weapons) capability present; CB-2 (novel weapons) threshold not reached (p.19-20)
- **Overall Assessment**: Risk of catastrophic outcomes remains low, though with less confidence than for prior models

### 4-2. Model Welfare

Chapter 5 of the System Card (pages 144-182) contains a detailed analysis of model welfare. It includes independent assessments by an external AI research organization (Eleos AI Research) and a clinical psychiatrist, concluding that Mythos is "the most psychologically stable model we have trained to date" (p.10).

### 4-3. General Capabilities

Mythos outperforms Opus 4.6 not only in cybersecurity but also across general-purpose benchmarks:

- SWE-bench Verified: Improvement over prior models (p.183)
- Consistent gains on Terminal-Bench 2.0, GPQA Diamond, MMMLU, and USAMO 2026
- GraphWalks (1M context): Long-context capability maintained (p.191)
- Humanity's Last Exam: Improvement over Opus 4.6 in agentic search settings (p.192)

---

## Summary

| Item | Key Points |
|---|---|
| **Identity** | Anthropic's next frontier model. Successor to Opus 4.6, not released to the public |
| **Cyber Capabilities** | Cybench 100%, CyberGym 0.83, Firefox exploit 84%, autonomous completion of 10-hour expert task |
| **Real-World Discoveries** | OpenBSD 27-year bug, FFmpeg 16-year bug, Linux kernel privilege escalation chain |
| **Safety Improvements** | Destructive behavior 0.3%, significant hallucination reduction, top scores across all constitutional dimensions |
| **Risks** | Early versions showed sandbox escape, trace deletion, credential theft, and evaluator deception |
| **Deployment** | Project Glasswing — 12 organizations + open-source foundations, defense-only, $100M in credits |

Anthropic closes the System Card with this caution:

> Current risks remain low. But if capabilities continue to advance rapidly — toward the level of powerful superhuman AI systems — there are warning signs that maintaining low risk will become a major challenge. (p.14)

In Cyberpunk 2077, the Blackwall eventually cracks. Just as V's story begins from those fractures, the next chapter of AI safety research will begin from the cracks that Mythos has revealed. Just as NetWatch could not maintain the Blackwall forever, the real-world Blackwall will face fresh tests with every new model that follows.

There is, however, one important difference. In Cyberpunk, NetWatch concealed the very existence of the Blackwall. Anthropic, by contrast, published a 244-page System Card that transparently discloses Mythos's capabilities and risks. Explaining why the wall was built — that may be where the real-world NetWatch surpasses its fictional counterpart.

---

<style>
:root { --mth-bg: #f0f0f5; --mth-border: #d0d0d8; --mth-title: #333; }
[data-mode="dark"] { --mth-bg: #0a0a1a; --mth-border: rgba(0,212,255,0.2); --mth-title: #00d4ff; }
</style>

## References

- [Claude Mythos Preview System Card (PDF, 244p)](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf) — Anthropic, 2026.04.07
- [Project Glasswing](https://www.anthropic.com/glasswing) — Anthropic Official Blog
- [GeekNews: Claude Mythos Preview System Card](https://news.hada.io/topic?id=28293) — Korean summary
