---
title: "CS Roadmap (0) — Why CS Knowledge Matters More Than Ever in the AI Era"
lang: en
date: 2026-03-10 10:00:00 +0900
categories: [AI, CS]
tags: [CS, Computer Science, AI, Vibe Coding, Software Engineering, Fundamentals]
difficulty: beginner
toc: true
image: /assets/img/og/cs.png
tldr:
  - "AI coding tools actually made experienced developers 19% slower (METR 2025), and junior developers using AI assistance scored 17% lower on comprehension (Anthropic 2026)"
  - "40-65% of AI-generated code contains security vulnerabilities, and iterative refinement paradoxically increases critical vulnerabilities by 37.6%"
  - "Karpathy himself revised 'vibe coding' to 'agentic engineering' after just one year — implying that oversight and expertise are prerequisites"
  - "Senior developer demand is at an all-time high while junior hiring has plummeted 60% — CS fundamentals are becoming a survival requirement for developers"
---

## Introduction

> This is Part 0 of the **CS Roadmap** series.

In February 2025, Andrej Karpathy — OpenAI co-founder and former Tesla AI director — posted a tweet:

> "There's a new kind of coding I call **'vibe coding'**, where you fully give in to the vibes, embrace exponentials, and forget that the code even exists."

![Karpathy's Vibe Coding Tweet (February 2, 2025)](/assets/img/post/cs/karpathy-vibe-coding-tweet.png)
_Andrej Karpathy's original tweet. It garnered 4.5 million views._

With 4.5 million views, this tweet sent shockwaves through the software industry. In an age where AI writes code for us, do we really no longer need CS knowledge? Can we truly "give in to the vibes and forget that code even exists"?

This article is an answer to that question, drawing on research papers, experimental data, industry reports, and insights from the great minds of computer science.

This series covers the core areas of CS systematically:

| Part | Topic | Key Question |
| --- | --- | --- |
| **Part 0 (this post)** | CS Knowledge in the AI Era | Why are CS fundamentals more important now? |
| **Part 1+** | Data Structures and Memory | Arrays, lists, hashes, trees — starting from memory layout |
| **Later** | OS, Math, Rendering, Networking | Progressive deep dives |

---

## Part 1: Vibe Coding — Revolution or Illusion?

### The Birth of Vibe Coding

In February 2025, Karpathy shared his experience using Cursor — giving voice instructions, not reading the generated code, and "moving on if it roughly works." He called this approach **Vibe Coding**.

The key characteristics:

- Give instructions to the LLM in natural language
- Don't read the generated code
- When errors occur, paste the error message and say "fix it"
- Forget that code exists

The idea spread rapidly. Demos poured in showing prototypes built in minutes and people with no programming experience creating websites. Cheers of "the democratization of coding" erupted.

### One Year Later, the Creator's Revision

But Karpathy himself revised his stance one year later (February 2026):

> "I think a better term might be **'agentic engineering'**. 'Agentic' because the new default is that you are orchestrating agents who do and acting as oversight — **'engineering' to emphasize that there is art & science and expertise to it.**"

**Agentic engineering**. Orchestrating agents while providing oversight. And emphasizing that it requires art, science, and expertise. The exact opposite of the "anyone can do it" vibe that the term "vibe coding" conveyed.

Why the revision? What happened in that year?

### Reality Emerges

Google Chrome Engineering Manager Addy Osmani directly challenged this phenomenon:

> "Vibe coding is not the same as AI-Assisted Engineering."

His key point: the way FAANG teams use AI is not vibe coding. There are technical design documents, rigorous code reviews, and test-driven development. AI is used as a tool to boost productivity **within that framework**.

> "AI is fundamentally an **inexperienced assistant**, and just as you wouldn't trust a first-year junior developer with your entire system architecture, it should not be trusted without supervision."

Stack Overflow's data backs this up. Within six months of ChatGPT's launch, weekly active users dropped from **60,000 to 30,000 — cut in half**. People started asking AI directly. But simultaneously, contributions to medium-sized open-source projects **declined by 35%** from January 2025 to January 2026. A signal that the population of people who read, understand, and contribute to code is shrinking.

---

## Part 2: What the Data Tells Us

Let's move past the intuitive arguments. Now for controlled experimental results.

### The METR Study (2025) — "AI That Slows Down Experts"

METR (Model Evaluation & Threat Research) conducted the most rigorous experiment in July 2025:

- **Subjects**: 16 experienced open-source developers
  - Average GitHub stars: 22,000+
  - Experience maintaining codebases of 1M+ lines
- **Method**: Randomized Controlled Trial (RCT)
- **Tools**: Cursor Pro (including Claude 3.5 Sonnet / GPT-4o)

Results:

![METR Study: Expert Forecasts vs Observed Results](/assets/img/post/cs/metr-study-forecasted-vs-observed.png)
_Key chart from the METR 2025 study. Economists, ML experts, and developers all predicted AI would speed things up, but in reality it was 19% slower (red dot). (Source: metr.org, CC-BY)_

| Metric | Value |
| --- | --- |
| Change in task completion time with AI | **19% increase** (slower) |
| Developers' prior prediction | "24% faster" |
| Developers' post-experiment perception | "20% faster" |
| AI-generated code acceptance rate | **Less than 44%** |

![METR Study: Predicted Time vs Actual Implementation Time](/assets/img/post/cs/metr-study-core-result.png)
_Left: developer predictions (AI would be faster), Right: actual observations (AI actually took longer). (Source: metr.org, CC-BY)_

Developers spent time reviewing, testing, and modifying AI-generated code, only to frequently reject it. The most striking finding: **even after the experiment, they believed they had been faster**. A disconnect between perception and reality.

![AI Code Review Flow](/assets/img/post/cs/excalidraw-04-ai-code-review-en.png)

The paper's conclusion is clear. **For developers who deeply understand their codebase, AI actually increases cognitive load.** AI-generated code is often "plausible but misses context," making verification costs exceed writing costs.

### The Anthropic Study (2026) — "AI Hinders Learning"

This time, the company that makes AI ran the experiment. Anthropic (the developer of Claude) conducted an RCT with 52 junior engineers in January 2026:

| Metric | AI-Assisted Group | Non-AI Group |
| --- | --- | --- |
| Comprehension test score | **50%** | **67%** |
| Debugging question gap | Widened further | — |

What's particularly interesting is the **difference based on how AI was used**:

- Developers who used AI for **conceptual questions**: 65%+ scores
- Developers who **delegated code generation** to AI: Below 40% scores

Same tool, different outcomes based on usage. The key insight: the moment you delegate "build this for me" to AI, learning stops. But when you ask "explain how this concept works," AI becomes an effective tutor.

> **Let's pause and address this**
>
> **Q. So is it better not to use AI at all?**
>
> No. The common message from both studies is **"you need fundamentals to use AI effectively."** The METR study found AI was effective for simple, independent tasks. Problems arose with complex system-level work. The Anthropic study showed that the group using AI as a questioning tool performed well. The difference is whether you wield AI like a hammer or use it like a scalpel.

### GitHub Copilot Productivity Studies

Combining GitHub's own research with external academic studies:

| Subject | Productivity Gain | Notes |
| --- | --- | --- |
| New developers | **35-39%** | Based on code writing speed |
| Senior developers | **8-16%** | Based on code writing speed |
| Overall average (PR-based) | **10.6% increase** | Pull Request merges |
| Overall task completion (experiment) | **55.8% faster** | Simple tasks only |

The numbers look impressive. But there's missing data: **bug rates**. Studies report significantly higher bug rates among Copilot users (arXiv 2302.06590). Faster writing, more frequent errors.

This aligns perfectly with an age-old software engineering lesson:

> **The time spent writing code is only a fraction of total development time.**

The rest goes to design, debugging, testing, code review, refactoring, and maintenance. Even if AI accelerates the "writing" phase, nothing in the remaining phases can be handled without knowledge.

---

## Part 3: Quality of AI-Generated Code — The Numbers

### Security Vulnerabilities

Research on the security quality of AI-generated code is well-established:

| Study | Finding |
| --- | --- |
| Multiple academic studies combined | **40-65%** of generated code contains CWE-classified security vulnerabilities |
| IEEE-ISTAS 2025 (400 samples) | Critical vulnerabilities **increased 37.6%** after 5 rounds of refinement |
| CrowdStrike (DeepSeek-R1) | Baseline vulnerable code rate: **~19%** |
| Escape.tech (5,600 apps analyzed) | **2,000+** vulnerabilities, **400+** exposed secrets, **175** PII exposures |

The IEEE-ISTAS 2025 paper is particularly noteworthy. It tested 400 code samples over 40 rounds of "asking AI to improve":

![The Paradox of Iterative Security](/assets/img/post/cs/excalidraw-05-security-iteration-en.png)

**The paradox of iterative refinement**: The more you ask AI to "make it more secure," the more complex the code becomes, and higher complexity means more vulnerabilities. Security-focused prompts achieved net security improvement only **27% of the time**, and only during the first 1-3 iterations.

### The Lovable Incident — The Real Cost of Vibe Coding

In 2025, a serious security incident occurred on the vibe coding platform Lovable (CVE-2025-48757):

- Of 1,645 apps tested, **170 apps** allowed unauthenticated database read/write access
- Exposed data: subscription info, names, phone numbers, API keys, payment info, Google Maps tokens

Apps built with vibe coding were deployed to production, and real user data was exposed. The advantage of "build and ship fast" turned into the risk of "deploy without anyone understanding the code."

### GitClear Code Quality Report (2024)

GitClear analyzed **211 million lines** of code changes from 2020 to 2024:

![GitClear: Surge in Duplicated Code Blocks After AI](/assets/img/post/cs/gitclear-code-duplication.png)
_After the spread of AI coding tools (2022~), the ratio of commits containing duplicated code blocks surged. (Source: GitClear 2025 Research)_

| Metric | 2020-2022 | 2023-2024 | Change |
| --- | --- | --- | --- |
| Code duplication rate | 8.3% | 12.3% | **4x increase** |
| Refactoring ratio | 25% | Below 10% | **60% decrease** |
| Code churn (modified within 2 weeks) | 3.1% | 5.7% | **84% increase** |

**Code churn** measures the rate at which newly written code is modified or deleted within two weeks. Nearly doubling means "write first, fix later" code has surged.

The steep decline in refactoring is even more concerning. Software is a living organism. Without continuous refactoring, technical debt accumulates and systems become unmaintainable. AI excels at "writing new code," but "reading existing code and improving its structure" remains a human domain.

---

## Part 4: The Essence of Abstraction — Insights from the Masters

Let's step back and ask a more fundamental question. **"What exactly is CS knowledge, and why can't it be replaced by AI?"**

### Dijkstra — Abstraction Is Not About Being Vague

![Edsger W. Dijkstra](/assets/img/post/cs/dijkstra-portrait.jpg){: width="300" }
_Edsger W. Dijkstra (1930-2002). Photo: Hamilton Richards, CC BY-SA 3.0_

Edsger W. Dijkstra (1930-2002). 1972 Turing Award recipient. Inventor of the shortest path algorithm, structured programming, semaphores, and more.

His most misunderstood quote:

> "Computer science is no more about computers than astronomy is about telescopes."

This means the essence of CS lies not in specific tools (computers, programming languages, or AI). CS is the study of **computation**, **abstraction**, and **complexity management**. Even as tools change, this essence remains constant.

Another key insight:

> "The purpose of abstracting is not to be vague, but to create a new semantic level in which one can be **absolutely precise**."

This is the difference between vibe coding and true engineering. Vibe coding uses abstraction as "vagueness" — you don't know what the code does, but it works, so it's fine. True abstraction is the opposite. **It hides the complexity of lower layers while enabling precise reasoning on top.**

In his 1972 Turing Award lecture "The Humble Programmer," Dijkstra said:

> "The competent programmer is fully aware of the strictly limited size of his own skull; therefore he approaches the programming task in full humility."

Human cognitive ability is limited. That's why abstraction is necessary, why structure is necessary, why CS is necessary. In the age of AI-generated code — no, **especially** in such an age — the ability to judge whether the abstraction level is appropriate and the structure is correct rests with humans.

### Knuth — Confident Nonsense

Donald Knuth. Author of **The Art of Computer Programming**. A living legend of computer science.

In 2023, Knuth posed 20 questions to ChatGPT and analyzed the results:

> "It's amazing how the confident tone lends credibility to all of that made-up nonsense."

This is the core risk of AI-generated code. AI **always responds confidently**. Whether the answer is correct or completely wrong. To tell the difference, you need domain knowledge.

There's an interesting follow-up. In 2026, Claude Opus solved a graph decomposition conjecture that Knuth had researched for weeks. Knuth's response:

> "It seems I'll have to revise my opinions about generative AI one of these days."

But is this evidence that "CS knowledge is unnecessary"? Quite the opposite. **Because Knuth was able to precisely define the problem he'd spent weeks researching**, AI could solve it. The ability to define problems — that is the core of CS knowledge.

### Brooks — No Silver Bullet

![Frederick Brooks](/assets/img/post/cs/fred-brooks-portrait.jpg){: width="300" }
_Frederick Brooks (1931-2022). 1999 Turing Award recipient._

Frederick Brooks. Author of **The Mythical Man-Month**. In his 1986 paper "No Silver Bullet":

> "There is no single development, in either technology or management technique, which by itself promises even one order of magnitude improvement within a decade in productivity."

Brooks divided software complexity into two types:

![Software Complexity — Brooks's Classification](/assets/img/post/cs/excalidraw-06-software-complexity-en.png)

AI excels at reducing **accidental complexity**. It generates boilerplate, catches syntax errors, and helps with environment configuration. But **essential complexity** — business logic design, concurrency handling, system trade-offs — is not something AI resolves. Forty years later, Brooks' analysis remains valid.

### The Law of Leaky Abstractions

Joel Spolsky formulated the **Law of Leaky Abstractions** in 2002:

> "All non-trivial abstractions, to some degree, are leaky."

TCP abstracts reliable transmission, but when the network is unstable, that abstraction "leaks." Garbage collectors abstract memory management, but when GC pauses occur, that abstraction leaks. AI abstracts coding, but when AI is wrong, that abstraction leaks.

When abstractions leak, **only those who understand what happens beneath the abstraction can solve the problem.** This is why CS knowledge exists.

---

## Part 5: The Polarization of the Job Market

Beyond theory and experiments, how is the market responding?

### Senior vs Junior — The Widening Gap

2025 tech hiring market data:

| Metric | Value | Source |
| --- | --- | --- |
| New tech positions | **371,000** | CompTIA 2025 |
| Software engineering positions | **156,000** | CompTIA 2025 |
| Big tech hiring (YoY) | **40% increase** | Pragmatic Engineer |
| Entry-level job postings (2022-2024) | **60% decrease** | Stack Overflow |
| Developer employment ages 22-25 (vs 2022) | **~20% decrease** | Stanford Digital Economy Lab |
| Entry-level share of total hiring | **7%** | Industry survey 2025 |

![Developer Job Market Polarization](/assets/img/post/cs/excalidraw-07-job-market-en.png)

The structure is clear. **As AI replaces the simple tasks juniors used to do, the value of seniors who can supervise and set direction is rising.** Google and Meta are hiring **50% fewer new graduates** compared to 2021.

### What Companies Want

Competencies hiring managers seek:

1. The ability to **reason** about bugs (not just copy-pasting error messages to AI)
2. The ability to explain **why** a query is slow
3. Understanding how the OS works
4. The ability to **design** systems that don't break at scale

These are all CS fundamentals. Data structures, operating systems, databases, networking, system design. In the age of AI writing code, this knowledge hasn't become **obsolete — it's become a filter**.

### The Changing Interview

2025 tech interview trends:

- **Over 70%** of interviews include algorithm/data structure questions
- Some companies allow AI tools in interviews but **pose higher-level problems**
- **45% of companies** plan to drop degree requirements — instead prioritizing demonstrated competency
- AI engineer roles have **increased 143%** since May 2024

Degrees matter less. But **knowledge matters more.** Understand the difference. "No degree required" is not synonymous with "no CS knowledge needed."

---

## Part 6: So What Should You Study?

Summarizing the discussion so far:

1. AI accelerates code **writing** but cannot replace **understanding and judgment**
2. Using AI effectively requires fundamentals — research proves this
3. Quality issues with AI-generated code are serious; without verification ability, it's dangerous
4. The job market is restructuring in favor of developers with strong fundamentals

So which areas of CS should you study? Here's the roadmap for this series.

### CS Roadmap

![CS Roadmap — 7 Levels for Game Programmers](/assets/img/post/cs/excalidraw-08-cs-roadmap-en.png)

Key questions for each level:

| Level | Key Question | Reference Texts |
| --- | --- | --- |
| **1. Data Structures & Memory** | Why does putting the same data in an array vs. a linked list create a 100x performance difference? | Cormen et al. *CLRS*, Knuth *TAOCP*, Bryant & O'Hallaron *CS:APP* |
| **2. OS & Concurrency** | Why does a program only sometimes crash when two threads write to the same variable? | Silberschatz *Operating System Concepts*, Herlihy & Shavit *The Art of Multiprocessor Programming* |
| **3. Math & Physics** | Why are quaternions better than Euler angles? | Strang *Linear Algebra*, Ericson *Real-Time Collision Detection* |
| **4. Engine Architecture** | How do you design systems under the constraint that a frame must finish within 16.67ms? | Gregory *Game Engine Architecture*, Nystrom *Game Programming Patterns* |
| **5. Rendering** | Why are frames slow when the GPU is idle? | Akenine-Moller *Real-Time Rendering*, RTR4 |
| **6. Networking** | How is synchronization possible for a 60fps action game at 100ms latency? | Fiedler *Gaffer on Games*, Bernier *Latency Compensating Methods* (Valve) |
| **7. Advanced Optimization** | Why is one cache miss more expensive than 200 arithmetic operations? | Hennessy & Patterson *Computer Architecture*, Drepper *What Every Programmer Should Know About Memory* |

### Principles of This Series

1. **Theory and intuition together**: We use formulas where needed, but first explain *why* the formula is needed
2. **Reference papers and textbooks**: We don't stop at blog posts — we guide you to primary sources
3. **Verify through implementation**: Core concepts are confirmed through code
4. **Depth first**: Not wide and shallow, but narrow and deep

---

## Conclusion: Tools and Craftsmen

In the 1980s, when spreadsheets appeared, people said "accountants will disappear." Accountants didn't disappear. Accountants who **used spreadsheets well** replaced those who didn't.

In the 2020s, AI started writing code. People say "programmers will disappear." Programmers won't disappear. Programmers who **effectively supervise AI** will replace those who don't.

And to supervise AI effectively, you need to understand what AI is doing. You need to know data structures to judge whether the data structure AI suggested is appropriate. You need to understand memory models to verify that AI-written concurrent code has no race conditions. You need to know the rendering pipeline to validate whether AI-optimized shaders are actually faster.

Let's return to Dijkstra's words:

> "The only mental tool by means of which a very finite piece of reasoning can cover a myriad of cases is called **abstraction**."

AI can generate countless lines of code. But **abstracting that code to understand it, judge it, and guide it in the right direction** remains — and will likely remain for a long time — a human responsibility.

In the next part, we'll begin with the first topic of this journey: **Data Structures and Memory** — starting with arrays and linked lists, examining how computers actually store and access data.

---

## References

**Research Papers and Reports**
- METR, "Measuring the Impact of Early 2025 AI on Experienced Open-Source Developer Productivity" (2025.07) — [arXiv 2507.09089](https://arxiv.org/abs/2507.09089)
- Anthropic, "The Impact of AI Assistance on Coding Skill Formation" (2026.01) — [anthropic.com/research](https://www.anthropic.com/research/AI-assistance-coding-skills)
- GitHub, "Research: Quantifying GitHub Copilot's Impact on Developer Productivity and Happiness" — [github.blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/)
- IEEE-ISTAS 2025, "The Paradox of Iterative Refinement in AI-Generated Code Security" — [arXiv 2506.11022](https://arxiv.org/abs/2506.11022)
- GitClear, "AI Assistant Code Quality 2025 Research" — [gitclear.com](https://www.gitclear.com/ai_assistant_code_quality_2025_research)
- Georgetown CSET, "Cybersecurity Risks of AI-Generated Code" (2024.11) — [cset.georgetown.edu](https://cset.georgetown.edu/publication/cybersecurity-risks-of-ai-generated-code/)
- ACM, "CS2023: ACM/IEEE-CS/AAAI Computer Science Curricula" — [doi.org/10.1145/3664191](https://dl.acm.org/doi/10.1145/3664191)
- CrowdStrike, "Hidden Vulnerabilities in AI-Coded Software" — [crowdstrike.com](https://www.crowdstrike.com/en-us/blog/crowdstrike-researchers-identify-hidden-vulnerabilities-ai-coded-software/)

**Expert Writings and Statements**
- Dijkstra, E.W., "The Humble Programmer" (1972 Turing Award Lecture) — [cs.utexas.edu](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD340.html)
- Knuth, D., "20 Questions for ChatGPT" (2023) — [cs.stanford.edu/~knuth](https://cs.stanford.edu/~knuth/chatGPT20.txt)
- Brooks, F., "No Silver Bullet — Essence and Accident in Software Engineering" (1986) — [Wikipedia](https://en.wikipedia.org/wiki/No_Silver_Bullet)
- Spolsky, J., "The Law of Leaky Abstractions" (2002)
- Osmani, A., "Vibe Coding Is Not the Same as AI-Assisted Engineering" — [addyo.substack.com](https://addyo.substack.com/p/vibe-coding-is-not-an-excuse-for)
- Karpathy, A., Original Vibe Coding Post (2025.02) — [x.com/karpathy](https://x.com/karpathy/status/1886192184808149383)

**Job Market and Industry Trends**
- Pragmatic Engineer, "State of the Tech Market in 2025" — [newsletter.pragmaticengineer.com](https://newsletter.pragmaticengineer.com/p/state-of-the-tech-market-in-2025)
- Stack Overflow Blog, "AI vs Gen Z: A New Worst Coder Has Entered the Chat" (2026.01) — [stackoverflow.blog](https://stackoverflow.blog/2026/01/02/a-new-worst-coder-has-entered-the-chat-vibe-coding-without-code-knowledge/)
- Stanford Digital Economy, Software Developer Employment Trends — [stackoverflow.blog](https://stackoverflow.blog/2025/12/26/ai-vs-gen-z/)
- MIT Technology Review, "From Vibe Coding to Context Engineering" (2025.11) — [technologyreview.com](https://www.technologyreview.com/2025/11/05/1127477/from-vibe-coding-to-context-engineering-2025-in-software-development/)
- Semafor, "Lovable Security Incident" (2025) — [semafor.com](https://www.semafor.com/article/05/29/2025/the-hottest-new-vibe-coding-startup-lovable-is-a-sitting-duck-for-hackers)

**Textbooks**
- Cormen, T.H. et al., *Introduction to Algorithms (CLRS)*, MIT Press
- Knuth, D., *The Art of Computer Programming (TAOCP)*, Addison-Wesley
- Bryant, R. & O'Hallaron, D., *Computer Systems: A Programmer's Perspective (CS:APP)*, Pearson
- Hennessy, J. & Patterson, D., *Computer Architecture: A Quantitative Approach*, Morgan Kaufmann
- Drepper, U., *What Every Programmer Should Know About Memory* (2007)
