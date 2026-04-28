---
title: "CS Roadmap Part 9 — Scheduling: Whom Does the OS Give the CPU To?"
lang: en
date: 2026-04-27 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, scheduler, cfs, eevdf, qos, frame-budget, game-engine]
toc: true
toc_sticky: true
math: true
difficulty: intermediate
prerequisites:
  - /posts/OSArchitecture/
  - /posts/ProcessAndThread/
tldr:
  - The scheduler makes two decisions — "whom to give the CPU" and "for how long" — evaluated against Throughput, Latency, Fairness, and Response time
  - Linux evolved O(n) → O(1) → CFS (2007) → EEVDF (2024). CFS always picks the thread with the smallest vruntime from an RB-tree; EEVDF adds eligibility and deadline axes to handle latency-sensitive work better
  - Windows boosts responsiveness with 32 priority levels plus dynamic boost (foreground window, I/O completion, GUI input). macOS uses 5 QoS classes that simultaneously decide priority, P/E core placement, and power management
  - 60fps gives 16.67ms and 120fps gives 8.33ms to finish input → logic → physics → render → present. A single priority inversion is enough to drop a frame
  - Unity Job priority, Unreal TaskGraph named threads, and SetThreadPriority / pthread / dispatch_qos are different abstractions sitting on the same OS scheduler
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: The Question of "Who, and How Much"

The [previous post](/posts/ProcessAndThread/) showed what processes and threads are and how the OS abstracts them. A natural follow-up question arises.

> **If 100 threads are ready and there are only 8 cores, whom does the OS give the CPU to? And for how long?**

Answering these two questions is the job of the **scheduler**. The answer determines two things:

- **Perceived responsiveness**: does the click react within 0.1 seconds, or take a full second?
- **Frame stability**: does the game hold 60fps, or occasionally exceed 17ms?

This post covers:

- **Scheduling basics**: Preemptive vs Cooperative, the trade-offs between Throughput, Latency, Fairness, Response
- **Classic algorithms**: FCFS, SJF, RR, Priority, MLFQ
- **Linux**: the evolution from O(n) → O(1) → **CFS** → **EEVDF**
- **Windows**: 32 priority levels, dynamic boost, foreground quantum stretch
- **macOS**: **QoS**-based scheduling and Apple Silicon P/E core placement
- **Game frame budget**: what fills 16.67ms and how priority inversion ruins it
- **How game engines use priority and affinity**: Unity, Unreal, and the OS API level

The core question for Stage 2 — *"Why does a program with two threads writing to the same variable only crash sometimes?"* — hinges on the word "**sometimes**", and that word ultimately comes out of how the scheduler operates. The order and timing of execution mixing is being decided in a place you cannot see.

---

## Part 1: Why Scheduling Is Necessary

### The Illusion of Multitasking

A desktop has a browser, IDE, Slack, Spotify, and Discord open at once. There are 8 cores, while processes and threads typically number in the hundreds. Yet they all appear to run "simultaneously."

In reality, the OS is swapping threads in and out very rapidly. One thread holds a core for a few milliseconds, then yields to another, then to another. Swap faster than the human perception threshold (~50ms) and it feels concurrent.

The **scheduler** decides this swapping and answers two questions:

1. **Whom to give it to** — among threads in the Ready state, which one should be placed on a core?
2. **For how long** — once placed, when can it be taken back, or can it be?

### Preemptive vs Cooperative

**Preemptive**: the scheduler can forcibly take a thread off the CPU. Periodic timer interrupts wake the kernel, which decides "who is next." Almost every modern OS — Linux, Windows, macOS — uses this approach.

**Cooperative**: a thread runs until it voluntarily yields (`yield`). 80s Macs, pre-95 Windows, and some current coroutine/Fiber systems work this way. A single thread stuck in an infinite loop freezes the system — one cause of the old "Mac bomb icon."

> **Hold on, let's clarify this.** Are goroutines and async/await cooperative?
>
> Go's goroutines are **partially cooperative**. Yield points exist only at function calls, channel operations, and GC safe points. Without a function call inside an infinite loop, other goroutines could starve, which is why Go 1.14 introduced async preemption. async/await is similar — yield points only at `await`. But the underlying threads still run on the OS's preemptive scheduler, so the two layers are stacked.

### Scheduler Evaluation Criteria

A scheduler design must consider several metrics, and they conflict with each other.

| Metric | Meaning | Who likes it |
|--------|---------|--------------|
| Throughput | Tasks completed per unit time | Batch processing, build servers |
| Turnaround time | Total elapsed time per job | Compilers, data processing |
| Waiting time | Time spent in the Ready queue | All jobs |
| Response time | Input → first reaction | Desktops, games |
| Fairness | Even resource distribution | Multi-user systems |
| Predictability | Predictable latency | Real-time systems, games |
| Energy | Power efficiency | Mobile, laptops |

Desktop and mobile typically prioritize **Response time + Energy**. Servers prioritize **Throughput + Fairness**. Real-time and games prioritize **Predictability**. This is why no single algorithm is optimal for every environment.

---

## Part 2: Classic Scheduling Algorithms

Before looking at full-fledged OS schedulers, here are five textbook algorithms. Modern schedulers are all combinations or evolutions of these ideas.

### FCFS (First-Come, First-Served)

The simplest. Run jobs in arrival order, and once a job starts, never preempt it (non-preemptive).

The problem is the **convoy effect**. If a 100-second job arrives first, all the 0.1-second jobs behind it wait 100 seconds. Average waiting time explodes.

### SJF / SRTF (Shortest Job First / Shortest Remaining Time First)

Run the shortest job first. Mathematically proven to be **optimal in average waiting time**.

Problem 1: **You must know the job length in advance.** In practice you can't, so you estimate from past execution history.
Problem 2: **starvation** — if short jobs keep arriving, long ones may never start.

### Round Robin (RR)

Cycle through the ready queue and give each thread a **time quantum** of CPU. When the quantum expires, send it to the back of the queue and move on.

The quantum size is the key parameter.

- **Too large**: behaves like FCFS, responsiveness drops
- **Too small**: context-switch overhead eats up actual work time

Typical values are 10~100ms. Linux decides dynamically (CFS); Windows uses about 6ms (12ms+ on servers).

The diagram below compares FCFS and RR for the same workload (A=8ms, B=4ms, C=2ms) arriving simultaneously.

<div class="sk-tl">
  <div class="sk-tl-title">FCFS vs Round Robin (quantum 2ms)</div>

  <div class="sk-tl-row">
    <div class="sk-tl-label">FCFS</div>
    <div class="sk-tl-track">
      <div class="sk-tl-blk sk-tl-a" style="flex: 8">A (8ms)</div>
      <div class="sk-tl-blk sk-tl-b" style="flex: 4">B (4ms)</div>
      <div class="sk-tl-blk sk-tl-c" style="flex: 2">C (2ms)</div>
    </div>
    <div class="sk-tl-axis">
      <span>0</span><span>8</span><span>12</span><span>14</span>
    </div>
    <div class="sk-tl-meta">avg turnaround = (8 + 12 + 14) / 3 = 11.33ms · C response 12ms</div>
  </div>

  <div class="sk-tl-divider"></div>

  <div class="sk-tl-row">
    <div class="sk-tl-label">RR (q=2)</div>
    <div class="sk-tl-track">
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-b" style="flex: 2">B</div>
      <div class="sk-tl-blk sk-tl-c sk-tl-done" style="flex: 2">C ✓</div>
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-b sk-tl-done" style="flex: 2">B ✓</div>
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-a sk-tl-done" style="flex: 2">A ✓</div>
    </div>
    <div class="sk-tl-axis">
      <span>0</span><span>2</span><span>4</span><span>6</span><span>8</span><span>10</span><span>12</span><span>14</span>
    </div>
    <div class="sk-tl-meta">C response 4ms (1/3 of FCFS) · avg turnaround = (14 + 8 + 6) / 3 = 9.33ms</div>
  </div>

  <div class="sk-tl-legend">
    <span class="sk-tl-lg sk-tl-a"></span>A (8ms)
    <span class="sk-tl-lg sk-tl-b"></span>B (4ms)
    <span class="sk-tl-lg sk-tl-c"></span>C (2ms)
    <span class="sk-tl-note">✓ job completion</span>
  </div>

  <div class="sk-tl-foot">RR is not always better in turnaround, but it dominates in responsiveness for short jobs and in fairness.</div>

<style>
.sk-tl { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-tl-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-tl-row { margin: 14px 0; }
.sk-tl-label { font-weight: 700; color: #2d3748; font-size: 12px; margin-bottom: 6px; }
.sk-tl-track { display: flex; height: 38px; border: 1px solid #cbd5e0; border-radius: 4px; overflow: hidden; }
.sk-tl-blk { display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.1); }
.sk-tl-blk:last-child { border-right: 0; }
.sk-tl-a { background: #fed7d7; }
.sk-tl-b { background: #c6f6d5; }
.sk-tl-c { background: #bee3f8; }
.sk-tl-done { box-shadow: inset 0 0 0 2px #2d3748; }
.sk-tl-axis { display: flex; justify-content: space-between; margin-top: 4px; padding: 0 2px; font-family: monospace; font-size: 10px; color: #718096; }
.sk-tl-meta { margin-top: 6px; font-size: 11px; color: #2b6cb0; font-weight: 600; }
.sk-tl-divider { height: 1px; background: #cbd5e0; margin: 18px 0; border-top: 1px dashed #cbd5e0; background: none; }
.sk-tl-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 14px; font-size: 11px; color: #4a5568; }
.sk-tl-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid #cbd5e0; vertical-align: middle; margin-right: 4px; }
.sk-tl-note { margin-left: auto; color: #718096; }
.sk-tl-foot { margin-top: 12px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-tl { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-tl-title { color: #e2e8f0; }
[data-mode="dark"] .sk-tl-label { color: #e2e8f0; }
[data-mode="dark"] .sk-tl-track { border-color: #4a5568; }
[data-mode="dark"] .sk-tl-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.08); }
[data-mode="dark"] .sk-tl-a { background: #742a2a; }
[data-mode="dark"] .sk-tl-b { background: #22543d; }
[data-mode="dark"] .sk-tl-c { background: #2a4365; }
[data-mode="dark"] .sk-tl-done { box-shadow: inset 0 0 0 2px #f7fafc; }
[data-mode="dark"] .sk-tl-axis { color: #a0aec0; }
[data-mode="dark"] .sk-tl-meta { color: #63b3ed; }
[data-mode="dark"] .sk-tl-divider { border-top-color: #4a5568; }
[data-mode="dark"] .sk-tl-legend { color: #cbd5e0; }
[data-mode="dark"] .sk-tl-lg { border-color: #4a5568; }
[data-mode="dark"] .sk-tl-note { color: #a0aec0; }
[data-mode="dark"] .sk-tl-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-tl { padding: 14px 12px 12px; }
  .sk-tl-title { font-size: 13px; }
  .sk-tl-blk { font-size: 9.5px; }
  .sk-tl-axis { font-size: 9px; }
  .sk-tl-meta { font-size: 10px; }
  .sk-tl-legend { font-size: 10px; gap: 6px; }
  .sk-tl-foot { font-size: 10px; }
}
</style>
</div>

### Priority Scheduling

Assign each thread a **priority** and run the highest-priority one first. Within the same priority, use RR.

The problem is again **starvation**. Low-priority threads may never run. One remedy is **aging**, gradually raising the priority of threads that have waited a long time.

Another deeper problem is **priority inversion**. If a low-priority thread holds a lock that a high-priority thread is waiting on, while a medium-priority thread keeps preempting the low one, the result is a paradox — **the high one is blocked by the medium one.** The next post (synchronization) takes this on directly.

### MLFQ (Multi-Level Feedback Queue)

Several queues are arranged by priority, and threads **move between queues based on observed behavior**.

The basic rules are:

1. New threads enter the highest queue
2. Using up the time quantum drops them down one level
3. Yielding to I/O before quantum expiry keeps them at the same level or moves them up

The interesting consequence:

- I/O-bound work (interactive GUI, game input): short bursts then yield → stays in higher queue → fast response
- CPU-bound work (compilers, encoders): long bursts → drops to lower queues → does not interfere with responsive work

The core idea is **classifying jobs by behavior** even when the algorithm has no idea what kind of work they are. Windows' dynamic boost, macOS' QoS adjustments, and Linux's sleeper bonus are all variants of the same idea.

> MLFQ was used directly by Solaris, classic Mac OS, and Windows NT. Modern OSes ostensibly use different algorithms (e.g., CFS), but their internal heuristics resemble MLFQ.

---

## Part 3: The Linux Scheduler — O(n) → O(1) → CFS → EEVDF

The evolution of the Linux scheduler is unbeatable as a study material. The same problem has been re-solved four times, and **what was wrong and how it was fixed** is fully public.

### O(n) Scheduler — Pre-2.4

The early Linux scheduler **walked the entire ready queue** for each decision. In an era of few cores and few processes, this was fine. But once servers began running thousands of processes, the scheduler itself became the bottleneck. Adding cores didn't help due to lock contention.

### O(1) Scheduler — 2.6 (Ingo Molnár, 2003)

Introduced by **Ingo Molnár** in late 2002.

Core ideas:

- **140 priority queues** (real-time 0–99, normal 100–139)
- A pair of active and expired queues per priority
- The next thread is chosen in **constant time** — just find the highest set bit in a bitmap

It also added an **interactive task bonus** as a heuristic. Longer sleep raised priority slightly, improving desktop responsiveness. But the heuristic grew increasingly complex, and workloads were found that gamed the bonus calculation, leaving the code a patchwork.

### CFS — Completely Fair Scheduler (2.6.23, 2007)

Built **again by Ingo Molnár**. He credited inspiration to **Con Kolivas's** RSDL (Rotating Staircase Deadline) patch.

The core idea was to define "fairness" not as simple rotation but as **balancing accumulated execution time**. Every thread has a virtual CPU time it should have received — `vruntime` — and the scheduler always picks **the thread with the smallest vruntime**.

Virtual runtime (`vruntime`) is the actual runtime (`runtime`) corrected by weight.

$$
\Delta \text{vruntime} = \Delta \text{runtime} \times \frac{w_0}{w}
$$

Here $w$ is the thread's weight (set by nice), and $w_0$ is the reference weight for nice 0 (1024). Lower nice (higher priority) means larger weight, so vruntime grows slower and the thread gets picked more often.

The **data structure** is a Red-Black Tree keyed on vruntime. The leftmost node (smallest vruntime) is the next runner, and insert / remove / select are all $O(\log n)$. Asymptotically slower than O(1), but in practice n is small enough that it doesn't matter, and removing the heuristics made the code far cleaner.

The diagram below shows CFS's core cycle. Pick the thread with the smallest vruntime from the RB-tree, run it, then re-insert it with the updated vruntime.

<div class="sk-cfs">
  <div class="sk-cfs-title">CFS — vruntime ordering and the run cycle</div>

  <div class="sk-cfs-rq-label">runqueue (key = vruntime, leftmost runs next)</div>
  <div class="sk-cfs-rq">
    <div class="sk-cfs-node sk-cfs-pick">
      <div class="sk-cfs-tname">T0</div>
      <div class="sk-cfs-tvrun">v=18</div>
      <div class="sk-cfs-pickmark">leftmost ← next</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T1</div>
      <div class="sk-cfs-tvrun">v=30</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T2</div>
      <div class="sk-cfs-tvrun">v=35</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T3</div>
      <div class="sk-cfs-tvrun">v=42</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T4</div>
      <div class="sk-cfs-tvrun">v=50</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T5</div>
      <div class="sk-cfs-tvrun">v=58</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T6</div>
      <div class="sk-cfs-tvrun">v=72</div>
    </div>
  </div>

  <div class="sk-cfs-flow">
    <div class="sk-cfs-step sk-cfs-step-pick">pick_next_task<br><span>(leftmost = T0)</span></div>
    <div class="sk-cfs-arrow">→</div>
    <div class="sk-cfs-step sk-cfs-step-run">run on CPU<br><span>vruntime += Δ × w₀ / w_T0</span></div>
    <div class="sk-cfs-arrow">→</div>
    <div class="sk-cfs-step sk-cfs-step-back">enqueue_task<br><span>re-insert in RB-tree with new v</span></div>
  </div>

  <div class="sk-cfs-formula">
    Δvruntime = Δruntime × (w₀ / w) &nbsp;·&nbsp; w₀ = 1024 (nice 0) &nbsp;·&nbsp; nice ↓ → w ↑ → Δv ↓ → picked more often
  </div>
  <div class="sk-cfs-foot">The result: every thread's vruntime self-balances toward roughly the same value — that is what "Completely Fair" means.</div>

<style>
.sk-cfs { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-cfs-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-cfs-rq-label { font-size: 12px; font-weight: 700; color: #4a5568; margin-bottom: 8px; }
.sk-cfs-rq { display: flex; gap: 6px; flex-wrap: wrap; padding: 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sk-cfs-node { flex: 1; min-width: 70px; padding: 10px 8px; border: 1.5px solid #4a5568; border-radius: 6px; background: #edf2f7; text-align: center; position: relative; }
.sk-cfs-pick { background: #38a169; border-color: #276749; color: #fff; }
.sk-cfs-tname { font-weight: 700; font-size: 13px; }
.sk-cfs-tvrun { font-family: monospace; font-size: 11px; opacity: 0.85; }
.sk-cfs-pick .sk-cfs-tvrun { color: #fff; opacity: 1; }
.sk-cfs-pickmark { position: absolute; top: 100%; left: 50%; transform: translateX(-50%); margin-top: 4px; font-size: 10px; font-weight: 700; color: #38a169; white-space: nowrap; }
.sk-cfs-flow { display: flex; align-items: stretch; gap: 8px; margin: 32px 0 14px; flex-wrap: wrap; }
.sk-cfs-step { flex: 1; min-width: 130px; padding: 10px 12px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 12px; }
.sk-cfs-step span { display: block; margin-top: 4px; font-weight: 400; font-size: 10.5px; font-family: monospace; opacity: 0.8; }
.sk-cfs-step-pick { background: #ebf8ff; color: #2c5282; border: 1px solid #3182ce; }
.sk-cfs-step-run { background: #faf5ff; color: #553c9a; border: 1px solid #805ad5; }
.sk-cfs-step-back { background: #fefcbf; color: #744210; border: 1px solid #d69e2e; }
.sk-cfs-arrow { display: flex; align-items: center; justify-content: center; font-size: 18px; color: #4a5568; font-weight: 700; }
.sk-cfs-formula { padding: 10px 14px; background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 6px; font-family: monospace; font-size: 12px; color: #2d3748; text-align: center; font-weight: 600; }
.sk-cfs-foot { margin-top: 8px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-cfs { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-cfs-title { color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-rq-label { color: #cbd5e0; }
[data-mode="dark"] .sk-cfs-rq { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-cfs-node { background: #2d3748; border-color: #718096; color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-pick { background: #38a169; border-color: #2f855a; color: #fff; }
[data-mode="dark"] .sk-cfs-pickmark { color: #68d391; }
[data-mode="dark"] .sk-cfs-step-pick { background: #2a4365; color: #bee3f8; border-color: #63b3ed; }
[data-mode="dark"] .sk-cfs-step-run { background: #322659; color: #d6bcfa; border-color: #b794f4; }
[data-mode="dark"] .sk-cfs-step-back { background: #744210; color: #fefcbf; border-color: #ecc94b; }
[data-mode="dark"] .sk-cfs-arrow { color: #a0aec0; }
[data-mode="dark"] .sk-cfs-formula { background: #2d3748; border-color: #4a5568; color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-cfs { padding: 14px 12px 12px; }
  .sk-cfs-title { font-size: 13px; }
  .sk-cfs-node { min-width: 56px; padding: 6px 4px; }
  .sk-cfs-tname { font-size: 11px; }
  .sk-cfs-tvrun { font-size: 9.5px; }
  .sk-cfs-pickmark { font-size: 9px; }
  .sk-cfs-step { font-size: 11px; min-width: 100px; padding: 8px; }
  .sk-cfs-step span { font-size: 9.5px; }
  .sk-cfs-arrow { font-size: 14px; }
  .sk-cfs-formula { font-size: 10.5px; padding: 8px 10px; }
  .sk-cfs-foot { font-size: 10px; }
}
</style>
</div>

CFS's key parameters are:

- `sched_latency_ns` — the target time to run every ready thread once per cycle (default 6ms × number of cores)
- `sched_min_granularity_ns` — minimum runtime per slice for one thread (default 0.75ms)
- `sched_wakeup_granularity_ns` — vruntime difference threshold required for a waking thread to preempt the current one

You can inspect them via `sysctl -a | grep sched`, and they auto-adjust based on core count.

```c
/* Simplified CFS pick logic */
struct task_struct *pick_next_task_fair(struct rq *rq) {
    struct cfs_rq *cfs_rq = &rq->cfs;
    struct sched_entity *se = __pick_first_entity(cfs_rq);  /* RB-tree leftmost */
    return container_of(se, struct task_struct, se);
}

/* Called every tick — update vruntime and rebalance */
void update_curr(struct cfs_rq *cfs_rq) {
    struct sched_entity *curr = cfs_rq->curr;
    u64 delta_exec = now - curr->exec_start;
    curr->vruntime += calc_delta_fair(delta_exec, curr);
    /* If preemption is warranted, resched_curr() */
}
```

### EEVDF — Earliest Eligible Virtual Deadline First (6.6, 2023~2024)

CFS served well for 16 years, but one structural issue remained: **expressing latency-sensitive work was hard.**

CFS could control *how often* a thread runs through nice, but not *how quickly* it must respond. The two concepts were collapsed onto the same axis.

**Peter Zijlstra** brought EEVDF into mainline starting in 2023, and it became the default scheduler in the 6.6 LTS kernel. The academic background is the 1996 paper by **Stoica, Abdel-Wahab, Jeffay, Baruah**.

EEVDF's two axes are:

1. **Eligibility** — has this thread already run its share? If not, it's eligible
2. **Virtual Deadline** — among eligible threads, pick the one whose deadline comes soonest

Deadline is computed as:

$$
\text{deadline} = \text{eligible time} + \frac{\text{request size}}{\text{weight}}
$$

A smaller request size (a new parameter called latency-nice) yields an earlier deadline, leading to more frequent preemption. In other words, work like a game's main thread that "**doesn't run that often, but must respond instantly when it does**" can finally be expressed exactly.

```c
/* Linux 6.6+ : set latency-nice independently from nice */
struct sched_attr attr = {
    .sched_policy   = SCHED_NORMAL,
    .sched_nice     = 0,
    .sched_runtime  = 1   * 1000 * 1000,   /* 1ms */
    .sched_deadline = 16  * 1000 * 1000,   /* 16.67ms */
    .sched_period   = 16  * 1000 * 1000,
};
sched_setattr(pid, &attr, 0);
```

> Even with EEVDF, vruntime-based fairness remains. EEVDF is less a replacement for CFS than a **refinement of the selection policy**, and external interfaces (`nice`, `cgroup cpu.weight`) are mostly unchanged.

### Linux's Other Scheduling Classes

Linux uses not a single algorithm but a layered set of **classes**. Each class has a priority, and lower classes don't run while higher ones have work.

| Class | Policy | Use |
|-------|--------|-----|
| stop | (kernel only) | CPU hotplug, RCU, etc. |
| dl | SCHED_DEADLINE | Real-time (period + runtime + deadline guaranteed) |
| rt | SCHED_FIFO, SCHED_RR | Real-time priorities 1–99 |
| fair | SCHED_NORMAL/BATCH/IDLE | General, CFS/EEVDF |
| idle | (when all idle) | swapper |

**Why you should not use SCHED_FIFO/RR carelessly in games**: misuse can freeze the whole system — a single priority-99 infinite loop renders that core unresponsive forever after. Even genuinely RT audio threads are safer accessed via OS-provided **higher abstractions** like `dispatch_qos` / `AVAudioSession.realtime` rather than direct `SCHED_FIFO`.

---

## Part 4: The Windows Scheduler — Priority + Boost

The Windows NT scheduler is a 32-level priority system designed by **Dave Cutler** based on his VMS experience. The core skeleton has been essentially unchanged since NT 3.1 (1993); over time, only heuristics and hardware-adaptive code have been layered on top.

### 32 Priority Levels

| Level | Meaning |
|-------|---------|
| 0 | Zero page thread (for zeroing memory) |
| 1~15 | Variable priority (regular processes, subject to dynamic adjustment) |
| 16~31 | Real-time priority (admin needed, no dynamic adjustment) |

Each process has a **Priority Class**, and within it threads are fine-tuned via **Thread Priority**.

```c
/* Windows priority = Process Class + Thread Priority offset */
SetPriorityClass(hProcess, NORMAL_PRIORITY_CLASS);    /* base 8 */
SetThreadPriority(hThread, THREAD_PRIORITY_NORMAL);   /* offset 0 */

/* HIGH_PRIORITY_CLASS = 13, THREAD_PRIORITY_HIGHEST = +2 → effective 15 */
/* REALTIME_PRIORITY_CLASS = 24, ... */
```

### Quantum

Windows' time quantum is measured as a multiple of **clock interval**. The clock interval is typically about 15ms (HPET-based) or 1ms (when the multimedia timer is enabled).

- **Workstation**: 2 clock intervals (default ~30ms but typically shorter after post-boot adjustments)
- **Server**: 12 clock intervals (long quantum favors throughput)

Furthermore, the **quantum is stretched for foreground processes**. The thread of the window the user is currently looking at gets longer time, improving responsiveness (Control Panel → System → Advanced → Performance Options → Advanced has a "Programs" / "Background services" toggle that turns this on and off).

### Priority Boost — Windows' Core Heuristic

Threads in the variable priority range (1~15) get **temporarily boosted** by various events. The boost decreases by 1 each quantum until it returns to the base.

| Event | Boost amount |
|-------|-------------|
| Disk I/O complete | +1 |
| Network / Mailslot | +2 |
| Mouse / Keyboard input | +6 |
| Sound card | +8 |
| GUI thread receives a message | +2 (foreground extra) |
| Semaphore wait release | +1 |
| Mutex/Event/Timer wait release | +1 |

This heuristic is **the mechanism behind Windows' responsiveness**. Move the mouse and the GUI thread gets +6; key input gets +6 too. Even when CPU-bound work is running, input remains responsive.

> **Hold on, let's clarify this.** If GUI thread boost is +6, how does priority get distributed across multiple windows?
>
> Only the **focused window's thread** receives the additional foreground boost. The moment Alt-Tab changes the active window, the boost distribution changes too. Turn on the priority column in Process Explorer and click another window — you'll see the priority of that window's thread briefly tick up.

### The Realtime Priority Trap

Levels 16~31 have **no dynamic boost** — they always run at that priority. In theory this means "never yields." Audio, video capture, and some game threads use 16~22.

But using **REALTIME_PRIORITY_CLASS (24~31)** in regular code is dangerous. A single infinite loop at 24 or above can freeze even the mouse cursor — mouse handling is also just a thread.

### NUMA, SMT, Heterogeneous

The modern Windows scheduler considers NUMA nodes, SMT (hyperthreading), and Intel Thread Director (P/E core hints) all together. **Hardware Threaded Scheduling**, introduced in Windows 11, takes Thread Director hints to adjust P/E core placement — what Apple Silicon does at the OS level, Intel solves through OS·CPU collaboration.

```cpp
/* Windows: thread priority adjustment + affinity */
HANDLE h = GetCurrentThread();
SetThreadPriority(h, THREAD_PRIORITY_TIME_CRITICAL);  /* +15 */

/* Pin to cores 0 and 1 */
DWORD_PTR mask = 0x3;
SetThreadAffinityMask(h, mask);

/* Windows 10+ : E-core preference hint */
THREAD_POWER_THROTTLING_STATE state = {};
state.Version = THREAD_POWER_THROTTLING_CURRENT_VERSION;
state.ControlMask = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
state.StateMask   = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
SetThreadInformation(h, ThreadPowerThrottling, &state, sizeof(state));
```

The final `THREAD_POWER_THROTTLING_EXECUTION_SPEED` is an API that hints to the OS, "this thread is fine running slowly on an E-core." Apply it to background work and the P-cores stay free for the game's main thread.

---

## Part 5: The macOS Scheduler — QoS + P/E Cores

macOS appears Mach-based on the surface, but its scheduler is a BSD-based priority system topped with the higher-level **QoS (Quality of Service)** abstraction. Developers almost always express priority through QoS, and the kernel translates it into priority + core placement + power management.

### 5 QoS Classes

| QoS Class | Meaning | Examples | Mapped priority |
|-----------|---------|----------|-----------------|
| User Interactive | Immediate response, what the user is directly seeing | Main thread, animation, input | 47 |
| User Initiated | User-started work the user is waiting for | File open, search | 37 |
| Default | Unspecified | General work | 31 |
| Utility | User doesn't need the result immediately (progress shown) | Downloads, imports | 20 |
| Background | Invisible to the user | Indexing, backup | 5 |

This QoS value determines:

1. **CPU priority** — the number above
2. **CPU scheduling latency** — User Interactive wakes fast, Background batches work
3. **I/O priority** — disk queue priority
4. **CPU core placement** (Apple Silicon) — User Interactive/Initiated prefer P-cores, Utility/Background prefer E-cores
5. **Timer coalescing** — Background batches timer firings
6. **GPU priority** — affects some graphics workloads

A single line of QoS decides **all six at once**.

### QoS API

```c
/* C/Objective-C — set the current thread's QoS */
pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);

/* When creating a GCD queue */
dispatch_queue_t q = dispatch_queue_create_with_target(
    "com.example.render",
    DISPATCH_QUEUE_SERIAL,
    dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE, 0));

/* Attach QoS to a dispatch_async */
dispatch_async(q, ^{
    /* Runs at User Interactive */
});
```

```swift
// Swift
DispatchQueue.global(qos: .userInteractive).async {
    // Quick work to relieve the main thread
}

// Operation API
let op = BlockOperation { /* ... */ }
op.qualityOfService = .userInitiated
queue.addOperation(op)
```

### QoS Inheritance — Priority Inversion Prevention

QoS **propagates automatically**. If work dispatched on a User Interactive queue does dispatch_sync on another queue, the target queue's QoS is temporarily boosted to User Interactive. This mechanism is at the heart of macOS's priority inversion mitigation.

The same applies to locks. `os_unfair_lock` raises the lock holder's QoS to the QoS of any waiter — POSIX's `PTHREAD_PRIO_INHERIT` done automatically at the OS level.

### QoS → priority → P/E core mapping

The diagram below shows how a single line of QoS translates into Mach priority and Apple Silicon's P/E core placement.

<div class="sk-qos">
  <div class="sk-qos-title">macOS QoS — six things decided in one line</div>

  <div class="sk-qos-grid">
    <div class="sk-qos-h">QoS Class</div>
    <div class="sk-qos-h sk-qos-h-prio">Mach priority</div>
    <div class="sk-qos-h">Apple Silicon core placement</div>

    <div class="sk-qos-cell sk-qos-ui">
      <div class="sk-qos-name">USER_INTERACTIVE</div>
      <div class="sk-qos-sub">Main thread / animation</div>
    </div>
    <div class="sk-qos-prio">47</div>
    <div class="sk-qos-cell sk-qos-pcore-strong">
      <div class="sk-qos-name">P-core only</div>
      <div class="sk-qos-sub">Maximum performance / max power</div>
    </div>

    <div class="sk-qos-cell sk-qos-uin">
      <div class="sk-qos-name">USER_INITIATED</div>
      <div class="sk-qos-sub">File open / search</div>
    </div>
    <div class="sk-qos-prio">37</div>
    <div class="sk-qos-cell sk-qos-pcore-pref">
      <div class="sk-qos-name">P-core preferred</div>
      <div class="sk-qos-sub">May use E-core if needed</div>
    </div>

    <div class="sk-qos-cell sk-qos-def">
      <div class="sk-qos-name">DEFAULT</div>
      <div class="sk-qos-sub">Unspecified</div>
    </div>
    <div class="sk-qos-prio">31</div>
    <div class="sk-qos-cell sk-qos-mixed">
      <div class="sk-qos-name">P/E mixed</div>
      <div class="sk-qos-sub">OS decides by load</div>
    </div>

    <div class="sk-qos-cell sk-qos-ut">
      <div class="sk-qos-name">UTILITY</div>
      <div class="sk-qos-sub">Progress-bar work</div>
    </div>
    <div class="sk-qos-prio">20</div>
    <div class="sk-qos-cell sk-qos-ecore-pref">
      <div class="sk-qos-name">E-core preferred</div>
      <div class="sk-qos-sub">Power efficiency first</div>
    </div>

    <div class="sk-qos-cell sk-qos-bg">
      <div class="sk-qos-name">BACKGROUND</div>
      <div class="sk-qos-sub">Indexing / backup</div>
    </div>
    <div class="sk-qos-prio">5</div>
    <div class="sk-qos-cell sk-qos-ecore-strong">
      <div class="sk-qos-name">E-core only + batched</div>
      <div class="sk-qos-sub">timer coalescing, low power</div>
    </div>
  </div>

  <div class="sk-qos-foot">
    <div class="sk-qos-foot-title">What one line of QoS decides simultaneously</div>
    <div class="sk-qos-foot-grid">
      <span>① CPU priority</span>
      <span>② scheduling latency</span>
      <span>③ I/O priority</span>
      <span>④ P/E core placement</span>
      <span>⑤ timer coalescing</span>
      <span>⑥ GPU priority</span>
    </div>
    <div class="sk-qos-foot-note">QoS auto-propagates (inheritance) up dispatch chains and to lock holders, so priority inversion is mitigated automatically.</div>
  </div>

<style>
.sk-qos { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-qos-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-qos-grid { display: grid; grid-template-columns: 1.2fr 0.5fr 1.2fr; gap: 8px; align-items: stretch; }
.sk-qos-h { font-size: 12px; font-weight: 700; color: #4a5568; text-align: center; padding-bottom: 4px; border-bottom: 1px solid #cbd5e0; }
.sk-qos-h-prio { text-align: center; }
.sk-qos-cell { padding: 10px 12px; border-radius: 6px; border: 1.5px solid; text-align: center; }
.sk-qos-name { font-family: monospace; font-weight: 700; font-size: 12px; color: #1a202c; }
.sk-qos-sub { font-size: 10.5px; color: #4a5568; margin-top: 2px; }
.sk-qos-prio { display: flex; align-items: center; justify-content: center; font-family: monospace; font-size: 18px; font-weight: 700; color: #2b6cb0; position: relative; }
.sk-qos-prio::before, .sk-qos-prio::after { content: ""; position: absolute; top: 50%; height: 1px; background: #a0aec0; }
.sk-qos-prio::before { left: 0; right: calc(50% + 16px); }
.sk-qos-prio::after { right: 0; left: calc(50% + 16px); }
.sk-qos-ui  { background: #fed7d7; border-color: #c53030; }
.sk-qos-uin { background: #feebc8; border-color: #d69e2e; }
.sk-qos-def { background: #fefcbf; border-color: #b7791f; }
.sk-qos-ut  { background: #c6f6d5; border-color: #38a169; }
.sk-qos-bg  { background: #bee3f8; border-color: #3182ce; }
.sk-qos-pcore-strong { background: #fed7d7; border-color: #c53030; }
.sk-qos-pcore-pref   { background: #feebc8; border-color: #d69e2e; }
.sk-qos-mixed        { background: #e9d8fd; border-color: #805ad5; }
.sk-qos-ecore-pref   { background: #c6f6d5; border-color: #38a169; }
.sk-qos-ecore-strong { background: #bee3f8; border-color: #3182ce; }

.sk-qos-foot { margin-top: 16px; padding: 12px 14px; background: #f7fafc; border: 1px solid #cbd5e0; border-radius: 6px; }
.sk-qos-foot-title { font-size: 12px; font-weight: 700; color: #2d3748; margin-bottom: 8px; }
.sk-qos-foot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px 12px; font-family: monospace; font-size: 11.5px; color: #2d3748; }
.sk-qos-foot-note { margin-top: 8px; font-size: 11px; color: #4a5568; font-style: italic; }

[data-mode="dark"] .sk-qos { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-qos-title { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-h { color: #cbd5e0; border-bottom-color: #4a5568; }
[data-mode="dark"] .sk-qos-name { color: #f7fafc; }
[data-mode="dark"] .sk-qos-sub { color: #cbd5e0; }
[data-mode="dark"] .sk-qos-prio { color: #63b3ed; }
[data-mode="dark"] .sk-qos-prio::before, [data-mode="dark"] .sk-qos-prio::after { background: #4a5568; }
[data-mode="dark"] .sk-qos-ui  { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sk-qos-uin { background: #744210; border-color: #ecc94b; }
[data-mode="dark"] .sk-qos-def { background: #5a4017; border-color: #d69e2e; }
[data-mode="dark"] .sk-qos-ut  { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-qos-bg  { background: #2a4365; border-color: #63b3ed; }
[data-mode="dark"] .sk-qos-pcore-strong { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sk-qos-pcore-pref   { background: #744210; border-color: #ecc94b; }
[data-mode="dark"] .sk-qos-mixed        { background: #322659; border-color: #b794f4; }
[data-mode="dark"] .sk-qos-ecore-pref   { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-qos-ecore-strong { background: #2a4365; border-color: #63b3ed; }
[data-mode="dark"] .sk-qos-foot { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-qos-foot-title { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-foot-grid { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-foot-note { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-qos { padding: 14px 12px 12px; }
  .sk-qos-title { font-size: 13px; }
  .sk-qos-grid { grid-template-columns: 1fr 0.4fr 1fr; gap: 5px; }
  .sk-qos-cell { padding: 6px 6px; }
  .sk-qos-name { font-size: 10px; }
  .sk-qos-sub { font-size: 8.5px; }
  .sk-qos-prio { font-size: 14px; }
  .sk-qos-foot-grid { grid-template-columns: 1fr 1fr; font-size: 10px; }
  .sk-qos-foot-title { font-size: 11px; }
  .sk-qos-foot-note { font-size: 10px; }
}
</style>
</div>

### Game Mode (macOS 14+)

**Game Mode**, added in macOS Sonoma, is a mode the OS auto-enables when a game is fullscreen. Effects:

- More aggressive QoS suppression for background work (Spotlight indexing, Time Machine, etc.)
- Stronger P-core priority for the game process
- Doubled audio·input polling rates for AirPods / PS5 controllers

The idea is similar to iOS's Sustained Performance API — telling the OS, "this app cannot afford to miss 16.67ms right now," so system-wide resource allocation adjusts.

---

## Part 6: Game Frame Budget — 16.67ms

Now let's transfer the OS theory above into a game context. For game developers, scheduling is ultimately about the **frame budget**.

### The Math of the Frame Budget

$$
\text{frame budget} = \frac{1000\,\text{ms}}{\text{target FPS}}
$$

| Target FPS | Frame budget | Who uses it |
|------------|--------------|-------------|
| 30 | 33.33ms | Console cinematics, some mobile |
| 60 | 16.67ms | Standard games |
| 90 | 11.11ms | VR minimum |
| 120 | 8.33ms | High-FPS PC, PS5 Performance |
| 144 | 6.94ms | High-refresh monitors |
| 240 | 4.17ms | Competitive FPS, e-sports |

All of the following must finish within this time:

1. **Input handling** — keyboard, mouse, gamepad, touch
2. **Game Logic** — AI, behavior, state updates
3. **Physics / Collision** — one step of discrete simulation
4. **Animation** — bone matrix computation, blending
5. **Particle / VFX** — particle updates
6. **Render command build** — draw call sorting, culling
7. **GPU submit** — command buffer queueing
8. **Present** — back buffer → screen (including VSync wait)

Game engines distribute this across **multiple threads**. Drawn on a timeline, what happens in one frame looks like this.

<div class="sk-fr">
  <div class="sk-fr-title">60fps frame budget 16.67ms — who does what when</div>
  <div class="sk-fr-budget">Hard deadline: failing to finish within 16.67ms causes a frame drop</div>

  <div class="sk-fr-grid">
    <div class="sk-fr-trackname">Main</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-input"   style="left: 0%;    width: 6%;">Input</div>
      <div class="sk-fr-blk sk-fr-logic"   style="left: 6%;    width: 14%;">Logic / AI</div>
      <div class="sk-fr-blk sk-fr-physics" style="left: 20%;   width: 12%;">Physics</div>
      <div class="sk-fr-blk sk-fr-anim"    style="left: 32%;   width: 10%;">Animation</div>
      <div class="sk-fr-blk sk-fr-cmd"     style="left: 42%;   width: 12%;">Cull / Sort</div>
    </div>

    <div class="sk-fr-trackname">Render</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-cmd"     style="left: 20%;   width: 30%;">CommandBuffer build (frame N-1)</div>
      <div class="sk-fr-blk sk-fr-submit"  style="left: 50%;   width: 22%;">GPU submit + sync</div>
    </div>

    <div class="sk-fr-trackname">Workers</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-job"     style="left: 6%;    width: 13%;">AI Job</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 19%;   width: 13%;">Particle</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 32%;   width: 10%;">Skinning</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 42%;   width: 14%;">Frustum Cull</div>
    </div>

    <div class="sk-fr-trackname">GPU</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-gpu"     style="left: 52%;   width: 44%;">GPU rendering (shadow → opaque → transparent → post)</div>
    </div>

    <div class="sk-fr-trackname sk-fr-vbname">VBlank</div>
    <div class="sk-fr-track sk-fr-vbtrack">
      <div class="sk-fr-vb">VBlank → Present</div>
    </div>
  </div>

  <div class="sk-fr-axis">
    <span style="left: 0%;">0</span>
    <span style="left: 25%;">4.2</span>
    <span style="left: 50%;">8.3</span>
    <span style="left: 75%;">12.5</span>
    <span style="left: 100%;">16.67ms</span>
  </div>

  <div class="sk-fr-legend">
    <span class="sk-fr-lg sk-fr-input"></span>Input
    <span class="sk-fr-lg sk-fr-logic"></span>Logic/AI
    <span class="sk-fr-lg sk-fr-physics"></span>Physics
    <span class="sk-fr-lg sk-fr-anim"></span>Animation
    <span class="sk-fr-lg sk-fr-cmd"></span>CommandBuffer/Cull
    <span class="sk-fr-lg sk-fr-job"></span>Worker Job
    <span class="sk-fr-lg sk-fr-gpu"></span>GPU
  </div>

  <div class="sk-fr-foot">CPU main thread runs one frame ahead of Render — what Render sees is Main's frame N-1 output.</div>

<style>
.sk-fr { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-fr-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 8px; text-align: center; }
.sk-fr-budget { font-size: 11px; color: #2b6cb0; font-weight: 700; text-align: center; margin-bottom: 14px; padding: 4px 8px; border: 1px dashed #2b6cb0; border-radius: 4px; }
.sk-fr-grid { display: grid; grid-template-columns: 80px 1fr; gap: 6px 10px; align-items: center; }
.sk-fr-trackname { font-size: 12px; font-weight: 700; color: #2d3748; text-align: right; }
.sk-fr-track { position: relative; height: 32px; background: #fff; border: 1px solid #cbd5e0; border-radius: 4px; overflow: hidden; }
.sk-fr-blk { position: absolute; top: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 10.5px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.1); padding: 0 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sk-fr-input    { background: #fefcbf; }
.sk-fr-logic    { background: #fed7d7; }
.sk-fr-physics  { background: #e9d8fd; }
.sk-fr-anim     { background: #c6f6d5; }
.sk-fr-cmd      { background: #bee3f8; }
.sk-fr-submit   { background: #feebc8; }
.sk-fr-job      { background: #c6f6d5; border: 1px solid #38a169; }
.sk-fr-gpu      { background: #fbb6ce; }
.sk-fr-vbtrack { background: transparent; border: 0; position: relative; }
.sk-fr-vbname { color: #c53030; }
.sk-fr-vb { position: absolute; right: 0; top: 50%; transform: translateY(-50%) translateX(50%); font-size: 11px; color: #c53030; font-weight: 700; padding: 4px 8px; background: #fff5f5; border: 1px dashed #c53030; border-radius: 4px; white-space: nowrap; }
.sk-fr-axis { position: relative; height: 18px; margin-top: 6px; margin-left: 90px; font-family: monospace; font-size: 10px; color: #718096; }
.sk-fr-axis span { position: absolute; transform: translateX(-50%); }
.sk-fr-axis span:last-child { transform: translateX(-100%); }
.sk-fr-legend { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 14px; font-size: 11px; color: #4a5568; }
.sk-fr-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid #cbd5e0; vertical-align: middle; margin-right: 4px; }
.sk-fr-foot { margin-top: 12px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-fr { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-fr-title { color: #e2e8f0; }
[data-mode="dark"] .sk-fr-budget { color: #63b3ed; border-color: #63b3ed; }
[data-mode="dark"] .sk-fr-trackname { color: #e2e8f0; }
[data-mode="dark"] .sk-fr-track { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-fr-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.08); }
[data-mode="dark"] .sk-fr-input    { background: #5a4017; }
[data-mode="dark"] .sk-fr-logic    { background: #742a2a; }
[data-mode="dark"] .sk-fr-physics  { background: #322659; }
[data-mode="dark"] .sk-fr-anim     { background: #22543d; }
[data-mode="dark"] .sk-fr-cmd      { background: #2a4365; }
[data-mode="dark"] .sk-fr-submit   { background: #744210; }
[data-mode="dark"] .sk-fr-job      { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-fr-gpu      { background: #702459; }
[data-mode="dark"] .sk-fr-vbname { color: #fc8181; }
[data-mode="dark"] .sk-fr-vb { color: #fc8181; background: #2d3748; border-color: #fc8181; }
[data-mode="dark"] .sk-fr-axis { color: #a0aec0; }
[data-mode="dark"] .sk-fr-legend { color: #cbd5e0; }
[data-mode="dark"] .sk-fr-lg { border-color: #4a5568; }
[data-mode="dark"] .sk-fr-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-fr { padding: 14px 12px 12px; }
  .sk-fr-title { font-size: 13px; }
  .sk-fr-grid { grid-template-columns: 60px 1fr; gap: 4px 6px; }
  .sk-fr-trackname { font-size: 10px; }
  .sk-fr-track { height: 26px; }
  .sk-fr-blk { font-size: 8.5px; }
  .sk-fr-vb { font-size: 9px; padding: 3px 5px; }
  .sk-fr-axis { margin-left: 66px; font-size: 9px; }
  .sk-fr-legend { font-size: 9.5px; gap: 4px 8px; }
  .sk-fr-foot { font-size: 10px; }
}
</style>
</div>

### One-Frame Pipeline

Most engines **stagger Main and Render by one frame**. While Main builds the game state for frame N, Render is dispatching GPU work for the state of frame N-1. The two threads don't touch the same data simultaneously, reducing locks, but **input lag increases by one frame**.

VR and e-sports titles are extremely sensitive to this trade-off. Features like NVIDIA Reflex and AMD Anti-Lag try to reduce this pipeline depth.

### Frame Spike Causes — A Scheduling View

When average frametime is 11ms but occasionally spikes to 23ms (a "frame spike"), the cause is often **OS scheduling** itself, in addition to GC, disk I/O, and syscalls.

- **Context switch storm**: more threads than cores → frequent swaps, cache pollution slows the main thread
- **Priority inversion**: main thread waits for a worker's lock while an unrelated thread keeps preempting the worker
- **NUMA miss**: a thread migrates to a different NUMA node, exploding cache·memory latency
- **P/E core demotion**: when macOS Game Mode isn't applied, the game's main thread can briefly land on an E-core, doubling frametime

Mitigations:

1. Pin the main and render threads to **fixed cores (affinity)**
2. Cap workers at about `core count - 2` to keep cores free for main and render
3. macOS: use `QOS_CLASS_USER_INTERACTIVE`; Windows: `THREAD_PRIORITY_HIGHEST` (avoid TIME_CRITICAL when possible)
4. Mark background threads explicitly with BACKGROUND / lower priority — the OS will route them appropriately on P/E setups

### A Priority Inversion Scenario

A common shape in games:

```
time      Main (qos=USER_INTERACTIVE)         Worker (qos=UTILITY)         Other (qos=DEFAULT)
0ms       enqueue logic                        idle                          running
1ms       AI result needed → mutex_lock(M) wait holds M                       -
2ms       (waiting)                            preempted by Other            running ← problem
... 6ms   (waiting)                            preempted by Other            running
7ms       (waiting)                            releases M                    -
7.1ms     unblocked → resumes                                                 -
```

Main is stuck from 1ms to 7ms while Worker can't run either; only Other runs. **macOS automatically boosts the M holder (Worker)'s QoS to USER_INTERACTIVE** in this case, so Other can no longer preempt Worker. POSIX's `PTHREAD_PRIO_INHERIT` and Windows' ALPC auto-boost are similar solutions. The next post (synchronization) covers this in depth.

---

## Part 7: How Game Engines Use Priority and Affinity

### Unity — Job System Priority

Unity's C# Job System manages an internal worker thread pool (default `worker count = ProcessorCount - 1`), and is scheduled via `JobHandle`.

```csharp
// Unity 2022+
using Unity.Jobs;
using Unity.Collections;

[Unity.Burst.BurstCompile]
struct PhysicsStepJob : IJobParallelFor {
    public NativeArray<float3> positions;
    public NativeArray<float3> velocities;
    public float dt;

    public void Execute(int i) {
        positions[i] += velocities[i] * dt;
    }
}

void Update() {
    var job = new PhysicsStepJob {
        positions = positionsArray,
        velocities = velocitiesArray,
        dt = Time.deltaTime
    };
    JobHandle h = job.Schedule(positionsArray.Length, 64);
    h.Complete();  /* Sync with main thread — must finish in this frame */
}
```

Counts can be controlled via `ScheduleBatchedJobs()` and `JobsUtility.JobWorkerMaximumCount`. **Player Settings → Other Settings → Use job worker count** also lets you set this explicitly — on an 8 P-core + 4 E-core machine, lowering workers to 8 lets Main hold a P-core more reliably.

### Unity — Application.targetFrameRate, vSyncCount

```csharp
// Mobile, locked 60fps
QualitySettings.vSyncCount = 0;
Application.targetFrameRate = 60;

// Desktop, follow monitor refresh rate
QualitySettings.vSyncCount = 1;
Application.targetFrameRate = -1;
```

### Unreal — TaskGraph and Named Threads

```cpp
// Unreal: dispatch work onto a specific thread
ENamedThreads::Type Target = ENamedThreads::GameThread;  /* or RenderThread, AnyThread */
FFunctionGraphTask::CreateAndDispatchWhenReady(
    [](){ /* runs on GameThread */ },
    TStatId(),
    nullptr,
    Target);

// Parallel worker pool
ParallelFor(NumElements, [&](int32 i) {
    Process(i);
}, EParallelForFlags::None);
```

Unreal forces explicit serialization through **named threads** like GameThread, RenderThread, RHIThread. Tasks queued to the WorkerPool go into a priority queue, and the Insights tool visualizes where each task ran.

### Calling OS APIs Directly

Sometimes you need to set priority directly via OS APIs, bypassing the engine.

```cpp
// Cross-platform thread priority — common in game engine cores
void SetThreadHighPriority(std::thread& t) {
#if defined(_WIN32)
    SetThreadPriority(t.native_handle(), THREAD_PRIORITY_HIGHEST);
#elif defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
    /* or thread_policy_set + thread_extended_policy_data_t */
#elif defined(__linux__)
    struct sched_param p;
    p.sched_priority = 0;  /* Within SCHED_NORMAL, adjust via nice */
    pthread_setschedparam(t.native_handle(), SCHED_NORMAL, &p);
    setpriority(PRIO_PROCESS, gettid_via_syscall(), -5);
#endif
}
```

### Thread Affinity — Pinning to Cores

```cpp
// Linux
cpu_set_t set;
CPU_ZERO(&set);
CPU_SET(0, &set);  /* core 0 */
CPU_SET(1, &set);
pthread_setaffinity_np(pthread_self(), sizeof(set), &set);

// Windows
SetThreadAffinityMask(GetCurrentThread(), 0x3);

// macOS — affinity API is deprecated, only hints possible
thread_affinity_policy_data_t policy = { 1 /* tag */ };
thread_policy_set(pthread_mach_thread_np(pthread_self()),
                  THREAD_AFFINITY_POLICY,
                  (thread_policy_t)&policy, 1);
```

> **Hold on, let's clarify this.** Why doesn't macOS have hard affinity?
>
> Apple's stance is consistent — "**developers don't know better than the OS**." The OS factors in heterogeneous P/E cores, power states, thermal limits, and core parking, so an app forcibly pinning a core often loses more than it gains. Instead, `THREAD_AFFINITY_POLICY` lets you hint **"keep these in the same cache group"**, and QoS lets you express P/E preference.

### Naughty Dog's Fiber Approach (Revisited)

Part 8 (Processes and Threads) briefly introduced Naughty Dog's Fiber model. From a scheduling viewpoint, **Naughty Dog hardly uses the OS scheduler at all**.

- One worker thread per core, pinned with affinity
- Every thread pulls the next fiber from a fiber pool and runs it (cooperative)
- Fiber switching takes tens of nanoseconds (1/100 of an OS context switch's few microseconds)
- From the OS's view, it's effectively "7 threads pinned to 7 cores — don't wake them"

This is the heart of Christian Gyrling's GDC 2015 talk. For ordinary games, this is overkill, but for AAA console titles where razor-sharp frame consistency is required, the choice is to bypass the OS and control the schedule directly.

---

## Part 8: Hands-On Observation — Which Threads Run Where

### Linux — chrt, nice, perf sched

```bash
# Change current shell's nice (smaller value = higher priority)
$ nice -n -5 ./mygame

# Inspect a running process's policy/priority
$ chrt -p $(pidof mygame)
pid 12345's current scheduling policy: SCHED_OTHER
pid 12345's current scheduling priority: 0

# Switch to SCHED_RR (root needed)
$ sudo chrt -r -p 50 $(pidof mygame)

# Trace scheduling events
$ sudo perf sched record -a sleep 10
$ sudo perf sched latency
# Task                       | Runtime ms | Switches | Avg delay ms | Max delay ms |
# mygame:12345               |   2543.123 |     8421 |        0.045 |        2.103 |
```

If `Max delay` exceeds 16ms, that frame likely had a frame spike.

### macOS — Activity Monitor, Instruments, sample

The Instruments **System Trace** template is the most accurate. What it measures:

- Which thread runs on each core (P0~P7, E0~E3)
- Color coded by QoS class
- Context switch events and their reason (preemption, voluntary block, etc.)
- Thread state transitions (run / runnable / waiting / stopped)

```bash
# CPU usage per thread
$ top -F -R -o cpu -stats pid,command,cpu,th,state

# Sample call stacks of all threads in a process, 5 times at 1-second intervals
$ sample <pid> 5 1 -mayDie

# powermetrics for per-core utilization (P/E split)
$ sudo powermetrics --samplers cpu_power -i 1000
```

### Windows — Process Explorer, WPA, Xperf

What the **Threads tab** in Process Explorer shows:
- Each thread's base/dynamic priority columns
- "Stack" button for call stack
- "I/O Priority", "Memory Priority" columns (Win10+)

**Xperf / Windows Performance Recorder**:

```powershell
# 1: Start profile
wpr -start GeneralProfile -filemode

# 2: Run the game, exercise the workload

# 3: Stop → collect ETL
wpr -stop trace.etl

# 4: Analyze with WPA (CPU usage by Thread, Generic Events, etc.)
wpa.exe trace.etl
```

The two graphs in WPA, "CPU Usage (Sampled)" and "CPU Usage (Precise)", differ importantly. Sampled is averaged; Precise is based on context-switch events and accurate for frame spike analysis.

### The Habit of Measuring

Forming the habit of **measuring** what the scheduler does instead of guessing is essential. Tracy Profiler embeds in your engine and visualizes every thread's frame-by-frame activity at nanosecond granularity — both Unity and Unreal have integrated plugins.

```cpp
// Tracy usage example
#include "Tracy.hpp"

void GameLoop() {
    ZoneScoped;  /* Auto-instrumented per function */
    {
        ZoneScopedN("AI Update");
        UpdateAI();
    }
    {
        ZoneScopedN("Physics Step");
        StepPhysics();
    }
}
```

Tracy also offers macros like LockableBase and FrameMark for synchronization·frame-boundary markers, which makes priority inversion easier to spot visually.

---

## Wrap-Up

This post covered:

**Scheduling basics**:
- Two decisions: "whom to" + "for how long"
- Preemptive vs Cooperative
- Evaluation criteria: Throughput, Latency, Fairness, Response, Energy

**Classic algorithms**:
- FCFS — convoy effect
- SJF — optimal average wait time, starvation
- RR — quantum trade-off
- Priority — starvation, foreshadows priority inversion
- MLFQ — automatic priority adjustment by observed behavior

**Linux**:
- O(n) → O(1) (Ingo Molnár, 2003)
- CFS (2007) — vruntime, RB-tree, completely fair
- EEVDF (2024) — eligibility + virtual deadline, latency-nice added
- Class hierarchy: stop > dl > rt > fair > idle

**Windows**:
- 32 priority levels (Variable 1–15, Realtime 16–31)
- Foreground quantum stretch
- Dynamic boost: I/O complete +1, Mouse/Keyboard +6, Sound +8
- Realtime has no dynamic boost — dangerous territory

**macOS**:
- 5 QoS classes (User Interactive ↔ Background)
- A single line decides priority + scheduling latency + I/O priority + P/E core + timer coalescing + GPU priority simultaneously
- QoS inheritance auto-mitigates priority inversion
- Game Mode (macOS 14+)

**Game frame budget**:
- 60fps = 16.67ms, 120fps = 8.33ms, VR 90fps = 11.11ms
- One frame: input → logic → physics → animation → render build → submit → present
- One-frame pipeline: parallelism via Main/Render lag, +1 frame input lag trade-off
- Scheduling causes of frame spike: context-switch storm, priority inversion, NUMA miss, P/E demotion

**Game engine usage**:
- Unity Job System, Unreal TaskGraph + Named Threads
- OS APIs: SetThreadPriority / pthread_setschedparam / pthread_set_qos_class_self_np
- Affinity: hard on Linux/Windows, hint-only on macOS
- Naughty Dog Fiber — bypasses the OS scheduler

**Observation tools**:
- Linux: chrt, nice, perf sched
- macOS: Instruments System Trace, sample, powermetrics
- Windows: Process Explorer, WPA / Xperf
- Cross-platform: Tracy Profiler

The next post is **Part 10: Synchronization Primitives**. We brushed up against priority inversion this time, and answering it requires looking at the essence of the **lock** first. What's the difference between Mutex, Semaphore, and SpinLock, and why does the OS bring its own primitives — futex / SRWLock / os_unfair_lock — to the table? With those answered, we finally get close to a head-on response to Stage 2's core question — *"Why does a program with two threads writing to the same variable only crash sometimes?"*

---

## References

### Textbooks
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.5 (CPU Scheduling), Ch.6 (Synchronization)
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.4 (Process Scheduling)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Ch.7 (Process Scheduling, O(1) era)
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — Ch.2 (Process Management and Scheduling, post-CFS)
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.4 (Thread Scheduling)
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.7 (Processes), Mach scheduler
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 (Multiprocessor Game Loops)

### Papers
- Stoica, Abdel-Wahab, Jeffay, Baruah, Plaxton, Tan — "A Proportional Share Resource Allocation Algorithm for Real-Time, Time-Shared Systems", RTSS 1996 — theoretical origin of EEVDF — [DOI](https://doi.org/10.1109/REAL.1996.563725)
- Pabla — "Completely Fair Scheduler", *Linux Journal*, 2009 — CFS introduction — [linuxjournal.com](https://www.linuxjournal.com/magazine/completely-fair-scheduler)
- Molnár, Ingo — "Modular Scheduler Core and Completely Fair Scheduler [CFS]", LKML patch series, 2007 — CFS introduction announcement
- Zijlstra, Peter — "EEVDF Scheduler", LWN articles, 2023 — [lwn.net/Articles/925371](https://lwn.net/Articles/925371/)
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:N model (revisited from a scheduling angle)
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — frame spike fundamentals

### Official Documentation
- Linux man pages — `sched(7)`, `chrt(1)`, `sched_setattr(2)`, `nice(1)` — [man7.org](https://man7.org/linux/man-pages/man7/sched.7.html)
- Linux Kernel Documentation — `Documentation/scheduler/sched-design-CFS.rst`, `sched-eevdf.rst`
- Microsoft Docs — *Scheduling Priorities* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)
- Microsoft Docs — *Priority Boosts* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts)
- Apple Developer — *Energy Efficiency Guide for Mac Apps — Prioritize Work with Quality of Service Classes* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-Mac/PrioritizeWorkAtTheTaskLevel.html)
- Apple Developer — *Tuning Your Code's Performance for Apple Silicon* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/tuning-your-code-s-performance-for-apple-silicon)
- Apple Developer — *Game Mode* (macOS 14+) — WWDC23 "Bring your game to Mac" session

### Game Development / GDC
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Acton, M. — *Data-Oriented Design and C++*, CppCon 2014 — Insomniac Games' cache·schedule mindset
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungie's threading model
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICE's Job system
- Unity Technologies — *C# Job System*, *Burst Compiler* manual — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Epic Games — *Task Graph System*, *Async Tasks in Unreal* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Tracy Profiler — [github.com/wolfpld/tracy](https://github.com/wolfpld/tracy)

### Blogs / Articles
- Brendan Gregg — *Linux Performance, perf sched* — [brendangregg.com](https://www.brendangregg.com/perf.html)
- Howard Oakley — *The Eclectic Light Company* — macOS QoS / P-E core observation series
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Raymond Chen — *The Old New Thing* — Windows priority boost reminiscences
- LWN.net — *EEVDF*, *CFS group scheduling*, *sched_ext* series
- Dmitry Vyukov — *1024cores.net* — go scheduler internals

### Tools
- Linux: `chrt`, `nice`, `taskset`, `perf sched`, `ftrace`, `bpftrace`
- macOS: Instruments (System Trace, Time Profiler, CPU Counters), `sample`, `powermetrics`, `dispatch_introspection`
- Windows: Process Explorer, Windows Performance Recorder + Analyzer, ETW, PerfView
- Cross-platform: Tracy Profiler, Optick, Superluminal
