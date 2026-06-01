---
title: "CS Roadmap Part 10 — Synchronization Primitives: How Does a Mutex Let Only One Thread In?"
lang: en
date: 2026-05-19 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, synchronization, mutex, semaphore, spinlock, cas, futex, cache-coherence, mesi, unity, unreal, job-system]
toc: true
toc_sticky: true
math: true
image: /assets/img/og/cs.png
difficulty: advanced
prerequisites:
  - /posts/ProcessAndThread/
  - /posts/Scheduling/
tldr:
  - The reason two threads touching the same variable die only sometimes is that read-modify-write is not atomic. A lock is the abstraction "only one thread in the critical section at a time," and at the bottom of that abstraction there is always a hardware atomic instruction (x86 LOCK CMPXCHG, ARM LDXR/STXR)
  - Mutex/Semaphore/RWLock/Spinlock/CondVar are just different policies on top of the same atomic. Linux puts the fast path in user space via futex and only enters the kernel on the slow path; Windows SRWLock and macOS os_unfair_lock follow the same idea
  - The real cost of a lock is not the instruction itself but cache line bouncing. Under MESI, when one core grabs the lock, the corresponding line in other cores is Invalidated, and cross-socket the cost is 10× higher. False sharing is the trap that causes this unintentionally
  - Unity's Job System builds a JobHandle dependency DAG that prevents read/write conflicts, and AtomicSafetyHandle catches races at Schedule() time (Editor/Development builds). Burst leaves normal NativeArray reads/writes as plain load/store and only emits hardware atomics for explicit Interlocked.* calls. DOTS analyzes ComponentSystem read/write to parallelize without locks
  - Unreal separates Game/Render/RHI/Audio Threads and queues commands via TaskGraph + FRenderCommandFence. ENQUEUE_RENDER_COMMAND has no visible lock — it enqueues commands that the Render Thread executes in FIFO order
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: What "Dies Only Sometimes" Really Means

When Stage 2 began, we asked one question.

> **Why does a program with two threads writing to the same variable die only sometimes?**

After [Part 7 — OS Architecture](/posts/OSArchitecture/), [Part 8 — Process and Thread](/posts/ProcessAndThread/), and [Part 9 — Scheduling](/posts/Scheduling/), we've reached half the answer. The OS swaps threads in invisible places, and those swap moments are unpredictable — that justifies the word "sometimes."

This part covers the other half. **A single line of code that reads, modifies, and writes is in fact not atomic**, and we'll see how the OS and CPU cooperate to manufacture the abstraction "only one at a time."

What we'll cover:

- **The nature of a race condition**: why `counter++` loses data
- **The lock family**: Mutex / Semaphore / RWLock / Spinlock / CondVar / Monitor / Barrier
- **How locks are built**: Peterson → Test-and-Set → CAS → hardware atomic
- **OS-specific primitives**: Linux futex, Windows SRWLock, macOS os_unfair_lock
- **Hardware mechanism**: CPU cache hierarchy, MESI, how atomic grabs cache line ownership, false sharing, memory barrier
- **Unity synchronization (deep dive)**: Main Thread model, Job System, NativeContainer, AtomicSafetyHandle, Burst, DOTS — how data flows between cores
- **Unreal synchronization**: Game/Render/RHI Thread separation, TaskGraph, ENQUEUE_RENDER_COMMAND internals
- **Game engine patterns**: lockless ring buffer, double buffer to avoid locks, frame-locked sync

It sounds long, but compressed to one sentence: **a lock is an abstraction, that abstraction sits on atomic instructions, and atomic instructions sit on cache line ownership.** We'll work our way down from the top.

## Part 1: The Nature of a Race Condition

### A one-line mystery

Look at this code.

```cpp
static int counter = 0;

void Worker() {
    for (int i = 0; i < 1'000'000; ++i) {
        counter++;
    }
}

int main() {
    std::thread t1(Worker);
    std::thread t2(Worker);
    t1.join(); t2.join();
    std::cout << counter << "\n";  /* expected: 2,000,000 */
}
```

Two threads each added 1 a million times, so the result should be two million. But run it and you get a different number every time, almost always less than two million. On a desktop you'll commonly see somewhere between 1,200,000 and 1,800,000.

The reason values vanish is that `counter++` is one line but three steps in machine code. The figure below traces, in time order, what happens when two threads touch the same counter at the same time. The moment one increment is lost becomes obvious.

<div class="sy-race">
  <div class="sy-race-title">counter++ — split into three steps, and the moment a race occurs</div>

  <div class="sy-race-grid">
    <div class="sy-race-col sy-race-col-head sy-race-col-time">time →</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-t1">Thread A (Core 0)</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-mem">counter (memory)</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-t2">Thread B (Core 1)</div>

    <div class="sy-race-tick">t₀</div>
    <div class="sy-race-cell sy-race-load">load eax ← [counter]<br><span>eax = 41</span></div>
    <div class="sy-race-mem"><span class="sy-race-val">41</span></div>
    <div class="sy-race-cell sy-race-idle">·</div>

    <div class="sy-race-tick">t₁</div>
    <div class="sy-race-cell sy-race-mod">add eax, 1<br><span>eax = 42</span></div>
    <div class="sy-race-mem"><span class="sy-race-val">41</span></div>
    <div class="sy-race-cell sy-race-load">load eax ← [counter]<br><span>eax = 41</span></div>

    <div class="sy-race-tick">t₂</div>
    <div class="sy-race-cell sy-race-store">store [counter] ← eax<br><span>counter = 42</span></div>
    <div class="sy-race-mem sy-race-mem-change"><span class="sy-race-val">42</span><span class="sy-race-arrow">↑ A's +1</span></div>
    <div class="sy-race-cell sy-race-mod">add eax, 1<br><span>eax = 42</span></div>

    <div class="sy-race-tick">t₃</div>
    <div class="sy-race-cell sy-race-idle">·</div>
    <div class="sy-race-mem sy-race-mem-lost"><span class="sy-race-val">42</span><span class="sy-race-arrow sy-race-arrow-lost">✗ B overwrote +1</span></div>
    <div class="sy-race-cell sy-race-store">store [counter] ← eax<br><span>counter = 42</span></div>
  </div>

  <div class="sy-race-foot">
    Expected: counter = 43 (A and B each +1)  ·  Actual: counter = 42 — <strong>one increment is gone</strong><br>
    Cause: when B read 41 at t₁, A's result (42) wasn't in memory yet — read-modify-write is not atomic
  </div>

<style>
.sy-race { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.45; }
.sy-race-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-race-grid { display: grid; grid-template-columns: 48px 1fr 110px 1fr; gap: 6px 8px; align-items: stretch; }
.sy-race-col-head { font-size: 12px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; border-bottom: 1px solid #cbd5e0; }
.sy-race-col-time { color: #718096; }
.sy-race-col-t1 { color: #c53030; }
.sy-race-col-mem { color: #2b6cb0; }
.sy-race-col-t2 { color: #2f855a; }
.sy-race-tick { font-family: monospace; font-weight: 700; color: #718096; text-align: center; align-self: center; }
.sy-race-cell { padding: 8px 10px; border-radius: 4px; font-family: monospace; font-size: 11.5px; font-weight: 600; }
.sy-race-cell span { display: block; font-size: 10px; font-weight: 500; color: #4a5568; margin-top: 2px; }
.sy-race-load { background: #fef5e7; color: #7b341e; }
.sy-race-mod  { background: #fef5e7; color: #7b341e; }
.sy-race-store { background: #fed7aa; color: #7b341e; }
.sy-race-idle { background: #f7fafc; color: #cbd5e0; text-align: center; padding: 8px; font-weight: 700; }
.sy-race-mem { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 6px; border: 1px dashed #cbd5e0; border-radius: 4px; background: #ebf8ff; }
.sy-race-mem-change { background: #c6f6d5; border-color: #38a169; border-style: solid; }
.sy-race-mem-lost { background: #fed7d7; border-color: #c53030; border-style: solid; }
.sy-race-val { font-family: monospace; font-size: 18px; font-weight: 800; color: #1a202c; }
.sy-race-arrow { font-size: 10px; font-weight: 700; color: #2f855a; }
.sy-race-arrow-lost { color: #c53030; }
.sy-race-foot { margin-top: 14px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 12px; color: #4a5568; text-align: center; line-height: 1.55; }
.sy-race-foot strong { color: #c53030; }

[data-mode="dark"] .sy-race { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-race-title { color: #e2e8f0; }
[data-mode="dark"] .sy-race-col-head { color: #e2e8f0; border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-race-col-time { color: #a0aec0; }
[data-mode="dark"] .sy-race-col-t1 { color: #feb2b2; }
[data-mode="dark"] .sy-race-col-mem { color: #90cdf4; }
[data-mode="dark"] .sy-race-col-t2 { color: #9ae6b4; }
[data-mode="dark"] .sy-race-tick { color: #a0aec0; }
[data-mode="dark"] .sy-race-cell span { color: #cbd5e0; }
[data-mode="dark"] .sy-race-load { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-race-mod  { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-race-store { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-race-idle { background: #2d3748; color: #4a5568; }
[data-mode="dark"] .sy-race-mem { background: #1a365d; border-color: #4a5568; }
[data-mode="dark"] .sy-race-mem-change { background: #22543d; border-color: #38a169; }
[data-mode="dark"] .sy-race-mem-lost { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sy-race-val { color: #f7fafc; }
[data-mode="dark"] .sy-race-arrow { color: #9ae6b4; }
[data-mode="dark"] .sy-race-arrow-lost { color: #feb2b2; }
[data-mode="dark"] .sy-race-foot { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-race-foot strong { color: #feb2b2; }

@media (max-width: 768px) {
  .sy-race { padding: 14px 10px 12px; font-size: 11px; }
  .sy-race-title { font-size: 13px; }
  .sy-race-grid { grid-template-columns: 32px 1fr 70px 1fr; gap: 4px 5px; }
  .sy-race-col-head { font-size: 10px; padding: 6px 2px; }
  .sy-race-cell { padding: 6px 6px; font-size: 10px; }
  .sy-race-cell span { font-size: 9px; }
  .sy-race-val { font-size: 14px; }
  .sy-race-arrow { font-size: 8.5px; }
  .sy-race-foot { font-size: 10.5px; }
}
</style>
</div>

### race condition vs data race — not the same thing

> **Hold on, let's settle this.** Are race condition and data race the same thing?
>
> They're often used interchangeably but they differ academically.
>
> - **Data race**: two threads access the same memory without synchronization, and at least one is a write. This is **explicitly defined** in multiple language memory models. **In C++/Rust it is undefined behavior**, while **Java/Go define limited behavior within their memory models** — not UB, but the result of a program that is not "correctly synchronized" can violate intuition.
> - **Race condition**: a broader concept where the result depends on thread execution order. Even if two threads communicate safely through atomic variables, if business-logic outcomes depend on who arrives first, that's a race condition.
>
> So every data race causes a race condition, but not every race condition is a data race. Locks remove data races; race conditions are a design problem at a higher layer.

### Atomicity, visibility, ordering — three guarantees

Synchronization primitives promise three things.

1. **Atomicity**: an operation happens as a single indivisible unit, with no observable intermediate state
2. **Visibility**: a value written by one thread is guaranteed to become visible to others
3. **Ordering**: memory operations are seen by other threads in the order the program intended

`counter++` broke because of atomicity. But visibility and ordering are separate problems too — CPUs reorder instructions, and caches don't synchronize instantly. All three are tackled in depth in Part 12 (memory model and atomic operations), but they sit in the background throughout this part.

> **Hold on, let's settle this.** Can a plain read or plain write also be non-atomic?
>
> Yes. On x86/ARM, naturally aligned 4-byte/8-byte reads and writes are generally atomic (separate from C++'s `std::atomic` guarantees). But misaligned access, 16-byte SIMD, or 64-bit values on a 32-bit CPU can split a single store into two and let another core observe a half-written value. That's why in C++ we use `std::atomic<T>` instead of a plain variable — to tell the compiler "this really must be atomic."

### What a lock promises

The simplest way to keep `counter++` from breaking:

```cpp
std::mutex m;
/* ... */
{
    std::lock_guard<std::mutex> lk(m);
    counter++;
}
```

While `lock_guard` holds `m`, no other thread can enter on the same `m`. The result is always two million.

Two questions follow naturally.

1. **How does the OS manufacture the "one at a time" promise?** — Part 3
2. **What does that promise cost?** — Part 5

First let's sort out the kinds of locks and how they differ.

---

## Part 2: The Lock Family

### Comparison at a glance

| Name | Essence | Who releases? | Wait style | Typical use |
|------|---------|---------------|-----------|-------------|
| **Mutex** | 1-slot lock | locking thread | sleep | protecting a critical section |
| **Recursive Mutex** | re-entrant Mutex | locking thread | sleep | nested calls from same thread |
| **Spinlock** | 1-slot lock | locking thread | busy-wait | very short critical sections, kernel |
| **Semaphore** | N-slot counter | any thread | sleep | resource pools, producer-consumer |
| **RWLock** | many readers / one writer | locking thread | sleep | read-heavy data |
| **Condition Variable** | wait + signal | waking thread | sleep | condition-based synchronization |
| **Monitor** | Mutex + CondVar bundle | (per object) | sleep | Java `synchronized` |
| **Barrier** | wait for N threads to arrive | once all arrive | sleep | parallel-stage sync |
| **Latch** | one-shot countdown | when count hits 0 | sleep | init-complete signal |

Quick notes on each.

### Mutex (Mutual Exclusion)

The most basic. **Holds state 0 or 1**, and only the thread that locked it can unlock it. If someone else has it, the incoming thread joins the wait queue and sleeps.

```cpp
std::mutex m;
m.lock();
// critical section
m.unlock();
```

In C++ you almost always use a RAII wrapper like `std::lock_guard` or `std::unique_lock`. They guarantee unlock even on exception.

> **Hold on, let's settle this.** reentrant, recursive, thread-safe — three terms that get confused.
>
> - **Thread-safe**: a function/object behaves correctly when called concurrently from multiple threads. A property *observed from outside*.
> - **Reentrant**: a thread can re-enter a function it's already executing (via interrupt or signal) safely. Conditions include no global variable use, no static buffers, etc.
> - **Recursive (lock)**: the same thread can acquire a lock it already holds. The counter goes up, and it must be released the same number of times.
>
> Recursive mutex is convenient but usually a sign of poor lock design. If a deep function doesn't know it already holds the lock and tries to acquire it again, that means the interface design left lock points unspecified.

### Spinlock

Same state as Mutex but the failing thread **does not sleep — it keeps retrying**.

```cpp
while (lock.test_and_set(std::memory_order_acquire)) {
    /* busy-wait */
}
```

When is Spinlock better than Mutex? **When the critical section is very short and context-switch cost outweighs spin cost.** A classic case: kernel interrupt handlers can't sleep at all, so only spinlock will do.

Conversely, if the critical section is long or you have more threads than cores, spinlock is a disaster. You'd burn CPU cycles on time that should be slept away.

> **Hold on, let's settle this.** What's the difference between a spinlock and plain busy-wait?
>
> A spinlock is **a lock built on atomic primitives**, while a plain busy-wait is just polling a regular variable. Polling a plain variable lets the compiler hoist the loop (`while(flag);` becomes an infinite loop) or never see a change made by another core. A spinlock prevents both via atomic + memory ordering.

### Semaphore

The oldest synchronization primitive, proposed by Dijkstra in 1965. A **non-negative integer counter** with two operations.

- **P (wait, acquire)**: sleep if counter is 0, otherwise decrement by 1
- **V (signal, release)**: increment by 1, wake one waiter if any

A Mutex is really "a binary semaphore initialized to 1." But the semantics differ — a Mutex must be released by the locking thread, while a Semaphore can be released by anyone. That makes Semaphore suitable for resource pools (free slots in a connection pool) or expressing "remaining capacity / items" in producer-consumer queues.

### Reader-Writer Lock

Many readers, one writer. Throughput improves when reads vastly outnumber writes.

```cpp
std::shared_mutex m;
{
    std::shared_lock<std::shared_mutex> r(m);  /* multiple readers OK */
    // read
}
{
    std::unique_lock<std::shared_mutex> w(m);  /* exclusive writer */
    // write
}
```

Two pitfalls. First, the RWLock itself costs more than a plain Mutex. For very short critical sections, plain Mutex can be faster. Second, **writer starvation** — if readers keep arriving, a writer can wait forever. Most implementations provide a writer-preferring mode.

### Condition Variable

Expresses "wait until a condition is satisfied." Always used **paired with a Mutex**.

```cpp
std::mutex m;
std::condition_variable cv;
bool ready = false;

/* Waiter */
{
    std::unique_lock<std::mutex> lk(m);
    cv.wait(lk, []{ return ready; });
    // woke up, ready == true
}

/* Notifier */
{
    std::lock_guard<std::mutex> lk(m);
    ready = true;
}
cv.notify_one();
```

The key is that `cv.wait` atomically does "release lock, sleep, on wake reacquire lock." Without that, a notify arriving just before wait causes the **lost wakeup** problem.

Also, you pass the wait predicate as a lambda because of **spurious wakeup**. The standard permits CV to wake without the condition being satisfied, so you must re-check after waking.

### Monitor

An abstraction that bundles Mutex + Condition Variable per object. Java's `synchronized` keyword and `wait/notify` attached to every object are exactly this pattern. C#'s `lock` block is the same.

```csharp
lock (gameState) {
    while (!gameState.Ready)
        Monitor.Wait(gameState);
    /* work */
    Monitor.PulseAll(gameState);
}
```

The monitor is embedded in the `gameState` object header so you don't have to declare a separate mutex. Convenient, but the lock is tightly bound to one object, making lock granularity hard to adjust.

### Barrier / Latch

**Barrier**: waits until N threads have all arrived at one point. Frame-locked parallel processing in games — "N physics update jobs must all finish before moving on" — is the canonical example. Reusable (cyclic barrier).

**Latch**: everyone waits until a counter reaches 0. Single-use. Useful for signaling once to all starting threads that initialization is done.

### Summary: which lock when

The matrix below places locks on two axes — critical section length (horizontal) and read/write ratio (vertical) — and marks the suitable primitive. At a glance you can see how tools with the same atomic foundation but different policies find their place.

<div class="sy-locks">
  <div class="sy-locks-title">Suitable synchronization primitive by situation</div>

  <div class="sy-locks-axis-y">read/write balance</div>

  <div class="sy-locks-grid">
    <div class="sy-locks-corner"></div>
    <div class="sy-locks-xh">Short (&lt; 1μs)</div>
    <div class="sy-locks-xh">Medium (1~100μs)</div>
    <div class="sy-locks-xh">Long / with I/O</div>

    <div class="sy-locks-yh">read ≈ write</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Spinlock</div>
      <div class="sy-locks-note">Kernel/interrupt only. Mostly forbidden in userspace</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex</div>
      <div class="sy-locks-note">Default choice. futex/SRWLock/os_unfair_lock</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex + CondVar</div>
      <div class="sy-locks-note">Long waits: sleep + condition signal</div>
    </div>

    <div class="sy-locks-yh">read ≫ write</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Mutex / atomic</div>
      <div class="sy-locks-note">RWLock overhead may be higher</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RWLock (Shared)</div>
      <div class="sy-locks-note">Watch for writer starvation</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RCU / Seqlock</div>
      <div class="sy-locks-note">Lock-free reads, protected writes</div>
    </div>

    <div class="sy-locks-yh">Resource pool / Queue</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Semaphore</div>
      <div class="sy-locks-note">Slot count = counter</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Semaphore + CondVar</div>
      <div class="sy-locks-note">Standard producer-consumer</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Lock-free Queue</div>
      <div class="sy-locks-note">SPSC ring / Vyukov MPSC</div>
    </div>

    <div class="sy-locks-yh">Phase sync</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">atomic flag</div>
      <div class="sy-locks-note">Short phase signal</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Barrier / Latch</div>
      <div class="sy-locks-note">N threads sync at once</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">JobHandle / Fence</div>
      <div class="sy-locks-note">Engine-level dependency</div>
    </div>
  </div>

  <div class="sy-locks-legend">
    <span class="sy-locks-lg sy-locks-cell-good"></span>Suitable
    <span class="sy-locks-lg sy-locks-cell-warm"></span>Possible but careful (overhead/forbidden)
    <span class="sy-locks-foot">— Every cell sits on the same atomic CAS underneath. Only the policy changes.</span>
  </div>

<style>
.sy-locks { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.45; position: relative; }
.sy-locks-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-locks-axis-y { position: absolute; left: 4px; top: 50%; transform: rotate(-90deg) translateX(50%); transform-origin: left center; font-size: 11px; font-weight: 700; color: #718096; letter-spacing: 0.05em; }
.sy-locks-grid { display: grid; grid-template-columns: 110px 1fr 1fr 1fr; gap: 8px; margin-left: 14px; }
.sy-locks-corner { background: transparent; }
.sy-locks-xh { font-size: 11.5px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; background: #edf2f7; border-radius: 4px; }
.sy-locks-yh { font-size: 11.5px; font-weight: 700; color: #2d3748; padding: 8px 6px; background: #edf2f7; border-radius: 4px; display: flex; align-items: center; }
.sy-locks-cell { padding: 10px 10px; border-radius: 5px; border: 1px solid; min-height: 60px; }
.sy-locks-cell-good { background: #c6f6d5; border-color: #68d391; }
.sy-locks-cell-warm { background: #fef5e7; border-color: #f6ad55; }
.sy-locks-name { font-weight: 700; font-size: 12.5px; color: #1a202c; margin-bottom: 4px; }
.sy-locks-note { font-size: 10.5px; color: #4a5568; line-height: 1.4; }
.sy-locks-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 16px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 11px; color: #4a5568; }
.sy-locks-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid; vertical-align: middle; margin-right: 4px; border-radius: 2px; }
.sy-locks-foot { margin-left: auto; color: #718096; font-style: italic; font-size: 11px; }

[data-mode="dark"] .sy-locks { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-locks-title { color: #e2e8f0; }
[data-mode="dark"] .sy-locks-axis-y { color: #a0aec0; }
[data-mode="dark"] .sy-locks-xh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-locks-yh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-locks-cell-good { background: #22543d; border-color: #38a169; }
[data-mode="dark"] .sy-locks-cell-warm { background: #5f370e; border-color: #c05621; }
[data-mode="dark"] .sy-locks-name { color: #f7fafc; }
[data-mode="dark"] .sy-locks-note { color: #cbd5e0; }
[data-mode="dark"] .sy-locks-legend { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-locks-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sy-locks { padding: 14px 8px 12px; }
  .sy-locks-title { font-size: 13px; }
  .sy-locks-axis-y { display: none; }
  .sy-locks-grid { grid-template-columns: 78px 1fr 1fr 1fr; gap: 5px; margin-left: 0; }
  .sy-locks-xh, .sy-locks-yh { font-size: 9.5px; padding: 6px 3px; }
  .sy-locks-cell { padding: 6px 6px; min-height: 50px; }
  .sy-locks-name { font-size: 10.5px; }
  .sy-locks-note { font-size: 9px; }
  .sy-locks-legend { font-size: 10px; gap: 8px; }
  .sy-locks-foot { margin-left: 0; width: 100%; }
}
</style>
</div>

That covers the interface layer that users see. Now we go one layer down and see how the OS and compiler manufacture these promises.

---

## Part 3: How Locks Are Built

### Attempt 1 — Can software alone do it?

Start with the naive attempt. Can we build a lock for two threads using just one variable?

```c
int locked = 0;

void lock() {
    while (locked) ;       /* spin */
    locked = 1;            /* got it! */
}
```

Obviously broken. Two threads that pass `while(locked)` simultaneously execute `locked = 1` at the same time and both enter the critical section. There's an empty gap between read and write where a race happens.

### Peterson's algorithm (1981)

You *can* build a lock in software alone. For two threads, the most elegant solution is **Gary Peterson's** algorithm from 1981.

<div class="sy-pt">
  <div class="sy-pt-title">Peterson's algorithm — two threads attempting to enter simultaneously</div>

  <div class="sy-pt-vars">
    <span class="sy-pt-tag">Shared variables</span>
    <code>flag[2] = {0, 0}</code>
    <code>turn = 0</code>
    <span class="sy-pt-meaning">flag[i] = "I want to enter", turn = "next to yield"</span>
  </div>

  <div class="sy-pt-cols">
    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-a">Thread A (self=0)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[0] = 1</code><span class="sy-pt-cmt">declare intent to enter</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 1</code><span class="sy-pt-cmt">yield to B</span></div>
      <div class="sy-pt-step sy-pt-pass"><span class="sy-pt-num">3</span><code>while (flag[1] &amp;&amp; turn == 1) ;</code><span class="sy-pt-cmt">wait if B also wants in and it's B's turn</span></div>
      <div class="sy-pt-step sy-pt-enter"><span class="sy-pt-num">4</span><strong>enter critical section</strong></div>
      <div class="sy-pt-step"><span class="sy-pt-num">5</span><code>flag[0] = 0</code><span class="sy-pt-cmt">unlock</span></div>
    </div>

    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-b">Thread B (self=1)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[1] = 1</code><span class="sy-pt-cmt">declare intent to enter</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 0</code><span class="sy-pt-cmt">yield to A</span></div>
      <div class="sy-pt-step sy-pt-wait"><span class="sy-pt-num">3</span><code>while (flag[0] &amp;&amp; turn == 0) ;</code><span class="sy-pt-cmt">spinning ...</span></div>
      <div class="sy-pt-step sy-pt-idle"><span class="sy-pt-num">4</span>(wait until A unlocks)</div>
      <div class="sy-pt-step sy-pt-enter-late"><span class="sy-pt-num">5</span><strong>then enter critical section</strong></div>
    </div>
  </div>

  <div class="sy-pt-key">
    <strong>Why does only one pass?</strong> Even when both threads execute step 2 nearly simultaneously, <code>turn</code> can hold only a single value (the last write wins). If that value is 0, A has yielded so B passes; if 1, vice versa — either way, exactly one thread escapes the while at step 3.
  </div>

  <div class="sy-pt-warn">
    <strong>But it doesn't work on real CPUs.</strong> From other cores' perspective, steps 1 and 2 may appear reordered (memory reorder), and store buffers prevent your own writes from being visible to other cores immediately. You ultimately need a memory barrier — which is a hardware instruction.
  </div>

<style>
.sy-pt { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-pt-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-pt-vars { padding: 8px 12px; background: #edf2f7; border-radius: 4px; margin-bottom: 14px; font-size: 12px; }
.sy-pt-vars code { background: #fff; padding: 1px 6px; margin: 0 4px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; }
.sy-pt-tag { display: inline-block; padding: 2px 8px; background: #2b6cb0; color: #fff; border-radius: 3px; font-size: 10.5px; font-weight: 700; margin-right: 6px; }
.sy-pt-meaning { display: block; margin-top: 4px; font-size: 11px; color: #4a5568; }
.sy-pt-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sy-pt-col { border: 1px solid #cbd5e0; border-radius: 6px; padding: 12px 12px 8px; background: #fff; }
.sy-pt-head { font-weight: 700; font-size: 13px; text-align: center; padding: 6px 0 10px; border-bottom: 1px dashed #cbd5e0; margin-bottom: 10px; }
.sy-pt-head-a { color: #c53030; }
.sy-pt-head-b { color: #2f855a; }
.sy-pt-step { display: flex; align-items: flex-start; gap: 8px; padding: 6px 8px; margin: 4px 0; border-radius: 4px; font-size: 11.5px; }
.sy-pt-num { flex: 0 0 22px; height: 22px; line-height: 22px; text-align: center; background: #4a5568; color: #fff; border-radius: 50%; font-weight: 700; font-size: 10.5px; }
.sy-pt-step code { font-family: monospace; color: #2b6cb0; font-weight: 600; flex: 1 1 auto; }
.sy-pt-cmt { display: block; width: 100%; padding-left: 30px; font-size: 10.5px; color: #718096; margin-top: -2px; font-style: italic; }
.sy-pt-pass { background: #c6f6d5; }
.sy-pt-pass .sy-pt-num { background: #2f855a; }
.sy-pt-enter { background: #2f855a; color: #fff; font-weight: 700; }
.sy-pt-enter .sy-pt-num { background: #fff; color: #2f855a; }
.sy-pt-enter strong { color: #fff; }
.sy-pt-wait { background: #fef5e7; }
.sy-pt-wait .sy-pt-num { background: #c05621; }
.sy-pt-idle { background: #f7fafc; color: #a0aec0; font-style: italic; }
.sy-pt-idle .sy-pt-num { background: #a0aec0; }
.sy-pt-enter-late { background: #fbd38d; }
.sy-pt-enter-late .sy-pt-num { background: #7b341e; }
.sy-pt-enter-late strong { color: #7b341e; }
.sy-pt-key { margin-top: 14px; padding: 10px 12px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; }
.sy-pt-key strong { color: #2b6cb0; }
.sy-pt-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; }
.sy-pt-warn { margin-top: 10px; padding: 10px 12px; background: #fff5f5; border-left: 3px solid #c53030; border-radius: 3px; font-size: 12px; color: #742a2a; }
.sy-pt-warn strong { color: #c53030; }

[data-mode="dark"] .sy-pt { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-pt-title { color: #e2e8f0; }
[data-mode="dark"] .sy-pt-vars { background: #2d3748; }
[data-mode="dark"] .sy-pt-vars code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-pt-meaning { color: #cbd5e0; }
[data-mode="dark"] .sy-pt-col { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-pt-head { border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-pt-head-a { color: #feb2b2; }
[data-mode="dark"] .sy-pt-head-b { color: #9ae6b4; }
[data-mode="dark"] .sy-pt-step code { color: #90cdf4; }
[data-mode="dark"] .sy-pt-cmt { color: #a0aec0; }
[data-mode="dark"] .sy-pt-pass { background: #22543d; }
[data-mode="dark"] .sy-pt-wait { background: #5f370e; }
[data-mode="dark"] .sy-pt-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-pt-enter-late { background: #7b341e; }
[data-mode="dark"] .sy-pt-enter-late strong { color: #fbd38d; }
[data-mode="dark"] .sy-pt-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-pt-key strong { color: #90cdf4; }
[data-mode="dark"] .sy-pt-key code { background: #2d3748; }
[data-mode="dark"] .sy-pt-warn { background: #742a2a; color: #fed7d7; }
[data-mode="dark"] .sy-pt-warn strong { color: #feb2b2; }

@media (max-width: 768px) {
  .sy-pt { padding: 14px 10px 12px; }
  .sy-pt-title { font-size: 13px; }
  .sy-pt-cols { grid-template-columns: 1fr; gap: 10px; }
  .sy-pt-col { padding: 10px 10px 6px; }
  .sy-pt-step { font-size: 10.5px; padding: 5px 6px; }
  .sy-pt-cmt { padding-left: 28px; font-size: 9.5px; }
  .sy-pt-num { flex-basis: 20px; height: 20px; line-height: 20px; font-size: 10px; }
  .sy-pt-key, .sy-pt-warn { font-size: 11px; padding: 8px 10px; }
}
</style>
</div>

The principle is combining **"I yield" intent with "whose turn is it" agreement.** Even when both threads enter at once, `turn` can hold only a single value, so only one passes.

Does this actually work? **In theory yes, on real CPUs no.**

Two reasons.

1. **CPU instruction reordering**: the order in which `flag[self] = 1; turn = other;` reaches memory can differ from code order. From another core, you might see `turn` change first while `flag[self]` still looks like 0.
2. **Store buffer**: each core has a write buffer, so values you wrote aren't immediately visible to other cores.

Solving both requires a **memory barrier**, which is essentially a hardware instruction. So software alone won't do.

### Attempt 2 — Hardware helps

What we fundamentally need is **a single instruction that does "read-compare-write" atomically.** CPU vendors provide special instructions for this. The three most common families, summarized in one figure:

<div class="sy-cas">
  <div class="sy-cas-title">Hardware atomic primitives — three families</div>

  <div class="sy-cas-fams">

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Test-and-Set (TAS)</div>
      <div class="sy-cas-fsub">"write a value and get the old one back"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">read<br><span>old = *X</span></div>
        <div class="sy-cas-amp">∧</div>
        <div class="sy-cas-box sy-cas-out">write<br><span>*X = true</span></div>
      </div>
      <div class="sy-cas-bracket">in one step — indivisible</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>XCHG</code> · <code>LOCK BTS</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> pair
      </div>
    </div>

    <div class="sy-cas-fam sy-cas-fam-hi">
      <div class="sy-cas-fname">Compare-and-Swap (CAS)</div>
      <div class="sy-cas-fsub">"if it equals expected, swap to new"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">read<br><span>cur = *X</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-cmp">compare<br><span>cur == exp ?</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-out">conditional write<br><span>*X = desired</span></div>
      </div>
      <div class="sy-cas-bracket">returns success/failure boolean</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK CMPXCHG</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> · <code>CAS</code> (v8.1+)
      </div>
    </div>

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Fetch-and-Add (FAA)</div>
      <div class="sy-cas-fsub">"add and get the old value back"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">read<br><span>old = *X</span></div>
        <div class="sy-cas-amp">+</div>
        <div class="sy-cas-box sy-cas-out">add and write<br><span>*X = old + δ</span></div>
      </div>
      <div class="sy-cas-bracket">returns old</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK XADD</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDADD</code> (v8.1+)
      </div>
    </div>

  </div>

  <div class="sy-cas-sep">↓ build a spinlock on top</div>

  <div class="sy-cas-spin">
    <div class="sy-cas-spin-title">One CAS makes one spinlock cycle</div>
    <div class="sy-cas-spin-flow">
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">1</div>
        <div class="sy-cas-step-name">acquire attempt</div>
        <div class="sy-cas-step-desc"><code>CAS(lock, 0, 1)</code></div>
      </div>
      <div class="sy-cas-spin-branch">
        <div class="sy-cas-branch sy-cas-branch-ok">
          <div class="sy-cas-branch-h">✓ success</div>
          <div class="sy-cas-branch-d">lock = 1<br>enter critical section</div>
        </div>
        <div class="sy-cas-branch sy-cas-branch-no">
          <div class="sy-cas-branch-h">✗ fail (already 1)</div>
          <div class="sy-cas-branch-d">PAUSE hint<br>retry</div>
        </div>
      </div>
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">2</div>
        <div class="sy-cas-step-name">critical section</div>
        <div class="sy-cas-step-desc">acquire-release<br>memory barrier included</div>
      </div>
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">3</div>
        <div class="sy-cas-step-name">release</div>
        <div class="sy-cas-step-desc"><code>store(lock, 0)</code></div>
      </div>
    </div>
  </div>

<style>
.sy-cas { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-cas-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-cas-fams { display: grid; grid-template-columns: 1fr 1.15fr 1fr; gap: 12px; }
.sy-cas-fam { padding: 12px 12px 10px; border: 1px solid #cbd5e0; border-radius: 6px; background: #fff; display: flex; flex-direction: column; }
.sy-cas-fam-hi { border-color: #2b6cb0; background: #ebf8ff; box-shadow: 0 0 0 2px rgba(43, 108, 176, 0.15); }
.sy-cas-fname { font-weight: 700; font-size: 13px; color: #1a202c; text-align: center; }
.sy-cas-fsub { font-size: 11px; color: #718096; text-align: center; margin-top: 2px; margin-bottom: 12px; font-style: italic; }
.sy-cas-flow { display: flex; align-items: center; justify-content: center; gap: 4px; margin: 8px 0; flex-wrap: wrap; }
.sy-cas-box { padding: 6px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; text-align: center; min-width: 60px; }
.sy-cas-box span { display: block; font-family: monospace; font-size: 9.5px; font-weight: 500; margin-top: 2px; opacity: 0.85; }
.sy-cas-in  { background: #fef5e7; color: #7b341e; }
.sy-cas-cmp { background: #ebf8ff; color: #2c5282; }
.sy-cas-out { background: #c6f6d5; color: #22543d; }
.sy-cas-amp { font-weight: 700; color: #2d3748; font-size: 14px; padding: 0 2px; }
.sy-cas-bracket { text-align: center; padding: 6px 8px; margin: 6px 0; background: #edf2f7; border-radius: 3px; font-size: 10.5px; font-weight: 700; color: #4a5568; letter-spacing: 0.02em; }
.sy-cas-isa { margin-top: auto; padding-top: 8px; border-top: 1px dashed #cbd5e0; font-size: 11px; line-height: 1.6; color: #4a5568; }
.sy-cas-arch { display: inline-block; min-width: 38px; padding: 1px 6px; margin-right: 6px; background: #4a5568; color: #fff; border-radius: 3px; font-size: 9.5px; font-weight: 700; text-align: center; }
.sy-cas-isa code { background: #edf2f7; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 10.5px; color: #2b6cb0; font-weight: 700; }

.sy-cas-sep { text-align: center; margin: 18px 0 10px; font-size: 11.5px; color: #718096; font-weight: 700; letter-spacing: 0.04em; }

.sy-cas-spin { padding: 12px 14px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-cas-spin-title { font-size: 12.5px; font-weight: 700; color: #2d3748; text-align: center; margin-bottom: 12px; }
.sy-cas-spin-flow { display: grid; grid-template-columns: 1fr 1.4fr 1fr 1fr; gap: 8px; align-items: stretch; }
.sy-cas-spin-step { padding: 10px 10px; background: #edf2f7; border-radius: 5px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.sy-cas-step-num { width: 22px; height: 22px; line-height: 22px; background: #2b6cb0; color: #fff; border-radius: 50%; font-weight: 700; font-size: 11px; }
.sy-cas-step-name { font-weight: 700; font-size: 11.5px; color: #1a202c; }
.sy-cas-step-desc { font-size: 10.5px; color: #4a5568; }
.sy-cas-step-desc code { background: #cbd5e0; padding: 1px 4px; border-radius: 2px; font-family: monospace; color: #2c5282; font-size: 10px; font-weight: 700; }
.sy-cas-spin-branch { display: grid; grid-template-rows: 1fr 1fr; gap: 4px; }
.sy-cas-branch { padding: 6px 8px; border-radius: 4px; }
.sy-cas-branch-ok { background: #c6f6d5; color: #22543d; }
.sy-cas-branch-no { background: #fed7d7; color: #742a2a; }
.sy-cas-branch-h { font-weight: 700; font-size: 11px; }
.sy-cas-branch-d { font-size: 10px; line-height: 1.35; margin-top: 2px; }

[data-mode="dark"] .sy-cas { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-cas-title { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-fam { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-cas-fam-hi { background: #1a365d; border-color: #4299e1; }
[data-mode="dark"] .sy-cas-fname { color: #f7fafc; }
[data-mode="dark"] .sy-cas-fsub { color: #a0aec0; }
[data-mode="dark"] .sy-cas-in  { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-cas-cmp { background: #1a365d; color: #90cdf4; }
[data-mode="dark"] .sy-cas-out { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-cas-amp { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-bracket { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-cas-isa { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-cas-arch { background: #cbd5e0; color: #1a202c; }
[data-mode="dark"] .sy-cas-isa code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-cas-sep { color: #a0aec0; }
[data-mode="dark"] .sy-cas-spin { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-cas-spin-title { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-spin-step { background: #1a202c; }
[data-mode="dark"] .sy-cas-step-name { color: #f7fafc; }
[data-mode="dark"] .sy-cas-step-desc { color: #cbd5e0; }
[data-mode="dark"] .sy-cas-step-desc code { background: #4a5568; color: #90cdf4; }
[data-mode="dark"] .sy-cas-branch-ok { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-cas-branch-no { background: #742a2a; color: #feb2b2; }

@media (max-width: 768px) {
  .sy-cas { padding: 14px 10px 12px; }
  .sy-cas-title { font-size: 13px; }
  .sy-cas-fams { grid-template-columns: 1fr; gap: 10px; }
  .sy-cas-fam { padding: 10px 10px 8px; }
  .sy-cas-fname { font-size: 12px; }
  .sy-cas-spin-flow { grid-template-columns: 1fr; gap: 6px; }
  .sy-cas-spin-step { padding: 8px 8px; }
  .sy-cas-spin-branch { grid-template-rows: auto; grid-template-columns: 1fr 1fr; }
}
</style>
</div>

CAS is the most general and powerful — it's **the basic unit of lock-free data structures** (covered in Part 13). TAS suffices for simple mutual exclusion like a spinlock, and FAA is the core operation for counter increments and ticket locks.

> **Hold on, let's settle this.** Are "CAS" and "atomic" the same?
>
> No. **Atomic operation** is the general concept of "any operation that happens as a single indivisible step." **CAS is one kind of atomic operation**, with siblings TAS, FAA, LL/SC, and atomic load/store. C++'s `std::atomic<T>` is an interface that abstracts these instructions, where `compare_exchange_weak` maps to CAS and `fetch_add` to FAA.

### CAS-based spinlock implementation

Building a spinlock with CAS:

```cpp
struct Spinlock {
    std::atomic<bool> locked{false};

    void acquire() {
        bool expected = false;
        while (!locked.compare_exchange_weak(
                expected, true,
                std::memory_order_acquire)) {
            expected = false;       /* gets clobbered on CAS failure */
            while (locked.load(std::memory_order_relaxed))
                __builtin_ia32_pause();  /* x86 PAUSE hint */
        }
    }

    void release() {
        locked.store(false, std::memory_order_release);
    }
};
```

Two things worth noting.

1. **acquire / release memory order**: ensures values written after acquiring the lock are visible to threads that later acquire the same lock. Details in Part 12.
2. **`PAUSE` hint**: on x86, inserting PAUSE in spin loops reduces power consumption and avoids memory-order violation penalties. ARM uses `YIELD` for a similar purpose.

### Spin or sleep — the decision rule

The same atomic underneath, just different policy, gives you spinlock or mutex. Which to use comes down to comparing critical section length against context-switch cost.

| Condition | Spin wins | Sleep wins |
|-----------|-----------|------------|
| Critical section length | < 1μs | > 10μs |
| Threads vs cores | ≤ | > |
| Environment | interrupt handler, RT kernel | normal user-space code |

Modern mutex implementations are therefore **adaptive**. They spin briefly first, then fall back to sleep if they still can't acquire. Linux glibc's NPTL does this; Windows SRWLock does too.

---

## Part 4: OS-specific Primitives

### Linux futex — fast userspace mutex (2002)

Does `pthread_mutex_lock` need a syscall every time? If the lock is uncontended, there's no reason to call into the kernel. That insight gave rise to **futex**.

Hubertus Franke, Rusty Russell, and Matthew Kirkwood introduced it into Linux in 2002. The core idea:

The pseudo-code commonly cited is a **3-state mutex implementation example** (0 unlocked, 1 locked-no-waiters, 2 locked-with-waiters). But that state encoding is **a user-space library's policy choice**, not part of futex itself — futex is the kernel-provided general **wait/wake building block**, and abstractions like mutex/semaphore/condvar are built on top with their own state encodings. The implementation above needs two bits because unlock must know whether waiters exist to decide whether to call the wake syscall.

A single uncontended futex operation costs roughly 10–20ns, less than one tenth of a syscall (~hundreds of ns). That's why **most user-space blocking lock implementations on Linux** (`pthread_mutex`, `sem_t`, glibc's `std::mutex`, etc.) are built on top of futex.

<div class="sy-futex">
  <div class="sy-futex-title">futex — fast path vs slow path branching</div>

  <div class="sy-futex-states">
    <span class="sy-futex-stag">state</span>
    <span class="sy-futex-st sy-futex-st-0">0 unlocked</span>
    <span class="sy-futex-st sy-futex-st-1">1 locked · no waiters</span>
    <span class="sy-futex-st sy-futex-st-2">2 locked · waiters present</span>
  </div>

  <div class="sy-futex-cols">
    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_lock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>CAS(m, 0, 1)</code></div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ success: lock acquired, done</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ failure: someone else holds it</div>
        </div>
        <div class="sy-futex-cost">~10ns · one CAS · no syscall</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>atomic_xchg(m, 2)</code> · mark "waiters present"</div>
        <div class="sy-futex-line"><code>futex_wait(m, 2)</code> syscall · enter kernel wait queue and sleep</div>
        <div class="sy-futex-cost">~hundreds of ns + context switch · plus sleep time</div>
      </div>
    </div>

    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_unlock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>fetch_sub(m, 1)</code> → check previous value</div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ was 1: no waiters, done</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ was 2: waiters present</div>
        </div>
        <div class="sy-futex-cost">~10ns · one atomic · no syscall</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>store(m, 0)</code> · unlock</div>
        <div class="sy-futex-line"><code>futex_wake(m, 1)</code> syscall · wake one waiter</div>
        <div class="sy-futex-cost">~hundreds of ns · woken thread retries lock</div>
      </div>
    </div>
  </div>

  <div class="sy-futex-key">
    <strong>Key insight</strong> — relies on the statistical fact that the lock is uncontended 90%+ of the time. When uncontended, everything finishes with one atomic in user space — avoiding the cost of calling the kernel. Only on contention does it enter the kernel and register on the wait queue.
    Windows SRWLock and macOS os_unfair_lock are variations of the same idea.
  </div>

<style>
.sy-futex { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-futex-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-futex-states { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 10px 12px; background: #edf2f7; border-radius: 5px; font-size: 11.5px; }
.sy-futex-stag { font-weight: 700; color: #2d3748; padding-right: 6px; border-right: 1px solid #cbd5e0; }
.sy-futex-st { padding: 3px 8px; border-radius: 3px; font-family: monospace; font-weight: 700; font-size: 11px; }
.sy-futex-st-0 { background: #c6f6d5; color: #22543d; }
.sy-futex-st-1 { background: #fef5e7; color: #7b341e; }
.sy-futex-st-2 { background: #fed7d7; color: #742a2a; }
.sy-futex-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.sy-futex-col { display: flex; flex-direction: column; gap: 10px; }
.sy-futex-ch { font-weight: 700; font-size: 13.5px; color: #1a202c; text-align: center; padding: 6px 0; }
.sy-futex-step { padding: 10px 12px; border-radius: 6px; border: 1px solid; }
.sy-futex-step-fast { background: #ebf8ff; border-color: #4299e1; }
.sy-futex-step-slow { background: #fff5f5; border-color: #fc8181; }
.sy-futex-zone { font-size: 10px; font-weight: 800; letter-spacing: 0.08em; color: #2b6cb0; text-transform: uppercase; margin-bottom: 6px; }
.sy-futex-zone-kernel { color: #c53030; }
.sy-futex-line { font-size: 11.5px; padding: 3px 0; color: #2d3748; }
.sy-futex-line code { background: #fff; padding: 1px 6px; margin-right: 4px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; font-size: 11px; }
.sy-futex-branch { padding: 6px 0 4px; font-size: 11px; }
.sy-futex-arrow { padding: 2px 0; font-weight: 600; }
.sy-futex-arrow-ok { color: #2f855a; }
.sy-futex-arrow-no { color: #c53030; }
.sy-futex-cost { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #cbd5e0; font-size: 10.5px; color: #4a5568; font-style: italic; }
.sy-futex-key { margin-top: 16px; padding: 12px 14px; background: #fffbeb; border-left: 3px solid #f6ad55; border-radius: 3px; font-size: 12px; color: #744210; line-height: 1.55; }
.sy-futex-key strong { color: #c05621; }

[data-mode="dark"] .sy-futex { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-futex-title { color: #e2e8f0; }
[data-mode="dark"] .sy-futex-states { background: #2d3748; }
[data-mode="dark"] .sy-futex-stag { color: #e2e8f0; border-right-color: #4a5568; }
[data-mode="dark"] .sy-futex-st-0 { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-futex-st-1 { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-futex-st-2 { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-futex-ch { color: #f7fafc; }
[data-mode="dark"] .sy-futex-step-fast { background: #1a365d; border-color: #4299e1; }
[data-mode="dark"] .sy-futex-step-slow { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sy-futex-zone { color: #90cdf4; }
[data-mode="dark"] .sy-futex-zone-kernel { color: #feb2b2; }
[data-mode="dark"] .sy-futex-line { color: #e2e8f0; }
[data-mode="dark"] .sy-futex-line code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-futex-arrow-ok { color: #9ae6b4; }
[data-mode="dark"] .sy-futex-arrow-no { color: #feb2b2; }
[data-mode="dark"] .sy-futex-cost { color: #a0aec0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-futex-key { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-futex-key strong { color: #fbd38d; }

@media (max-width: 768px) {
  .sy-futex { padding: 14px 10px 12px; }
  .sy-futex-title { font-size: 13px; }
  .sy-futex-cols { grid-template-columns: 1fr; gap: 14px; }
  .sy-futex-step { padding: 8px 10px; }
  .sy-futex-line { font-size: 10.5px; }
  .sy-futex-line code { font-size: 10px; }
  .sy-futex-cost { font-size: 9.5px; }
  .sy-futex-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

> **Hold on, let's settle this.** How are "fast path" and "slow path" generally split?
>
> In lock implementations, the fast path is **the route that finishes as fast as possible when there's no contention**, and the slow path is **the route that needs extra work when there is contention**. Nearly every modern synchronization primitive — futex, SRWLock, os_unfair_lock, parking_lot — follows this pattern. Fast path: 1–2 CASes. Slow path: kernel entry or separate wait-queue management. The design relies on the statistical fact that locks are uncontended over 90% of the time.

### Windows SRWLock and CRITICAL_SECTION

Windows has multiple generations of synchronization primitives, with different tradeoffs at each era.

**Mutex (kernel object)**: the oldest. Handle-based, can be shared across processes. But every lock/unlock is a syscall, making it slow — ~hundreds of ns.

**CRITICAL_SECTION**: introduced in NT 4 (1996). Handles the fast path with user-space atomics and only sleeps via the `WaitForSingleObject` kernel event on contention. Same idea as futex, five years earlier. Drawbacks: a heavy struct (~40 bytes including internal counter and handle) and only works within a single process.

**SRWLock (Slim Reader/Writer Lock)**: introduced in Windows Vista (2007). 8-byte pointer size, fast/slow path design almost identical to futex, with RWLock semantics. No init function needed (`= SRWLOCK_INIT`). For new code, SRWLock is almost always the answer.

```c
SRWLOCK lock = SRWLOCK_INIT;

AcquireSRWLockExclusive(&lock);   /* writer lock */
/* ... */
ReleaseSRWLockExclusive(&lock);

AcquireSRWLockShared(&lock);      /* reader lock */
/* ... */
ReleaseSRWLockShared(&lock);
```

Internally, SRWLock packs the following into a single 8-byte atomic: locked bit, waiting bit, waking bit, reader count, and high bits of a wait-queue head pointer. Bit-packing is what makes a single CAS suffice for the fast path.

**Condition Variable**: `CONDITION_VARIABLE`, paired with SRWLock, was added in the same era.

> **Hold on, let's settle this.** Which to use: `CRITICAL_SECTION` or `Mutex`?
>
> For new code within a single process, **SRWLock** is the answer. Lighter and supports RWLock. `CRITICAL_SECTION` is for compatibility with older code; `Mutex` (kernel object) is only when you need inter-process synchronization or a named mutex.

### macOS os_unfair_lock and family

macOS is based on BSD pthread, but adds Mach port–based synchronization and Apple-specific locks.

**pthread_mutex_t**: the standard. Internally uses the Mach `__ulock_wait` / `__ulock_wake` syscalls (macOS's futex equivalent). Same fast/slow path structure.

**os_unfair_lock**: introduced in macOS 10.12 / iOS 10 (2016). Created to **replace `OSSpinLock`**. OSSpinLock was vulnerable to priority inversion — if a low-priority thread held the lock and was demoted to E cores, a high-priority thread could spin forever.

```c
os_unfair_lock lock = OS_UNFAIR_LOCK_INIT;

os_unfair_lock_lock(&lock);
/* ... */
os_unfair_lock_unlock(&lock);
```

The "unfair" in the name is intentional. **It abandons FIFO fairness** and instead records information about the holding thread in the lock. When priority inversion is detected, it **temporarily boosts the holder's priority (priority donation)**. This is enabled by encoding the owner's thread ID in the 4-byte atomic.

> Within os_unfair_lock's 4 bytes is the owner thread's mach thread port id. This lets the kernel know who holds the lock on the contended path and automatically perform QoS inheritance (boost). It connects directly to the QoS coverage in Part 9.

**OSSpinLock**: deprecated. Never use in new code.

**NSLock / @synchronized**: Objective-C object-level monitor. Every NSObject can potentially have a lock. Same idea as Java's `synchronized` but costly.

**Dispatch semaphore (`dispatch_semaphore_t`)**: GCD's counting semaphore. P/V semantics.

### The same idea across three OSes

| OS | uncontended (fast) | contended (slow) | recommended new-code lock |
|------|------------------|------------------|---------------------------|
| Linux | atomic CAS | `futex(WAIT/WAKE)` syscall | `pthread_mutex`, `std::mutex` |
| Windows | atomic CAS | `NtWaitForAlertByThreadId` (Win8+) | `SRWLock` |
| macOS | atomic CAS | `__ulock_wait/wake` syscall | `os_unfair_lock` |

Three OSes provide different names and APIs, but share these traits:

1. Fast path: 1–2 user-space atomics
2. Slow path: kernel wait queue only
3. For RWLock, add reader count via bit packing

However, **priority inheritance/donation handling differs by OS.** macOS `os_unfair_lock` encodes the owner thread ID in 4 bytes so the kernel can immediately know the boost target. Linux records the owner only in the separate `PI_futex` mode (enabled via PTHREAD_PRIO_INHERIT) to support priority inheritance for RT tasks. Windows SRWLock and CRITICAL_SECTION don't guarantee priority inheritance by default — we revisit this in Part 11 (deadlock and priority inversion).

The C++ standard library, Rust `parking_lot`, and Java `j.u.c.locks` are all built on top of these OS APIs.

---

## Part 5: How Hardware Implements Locks

So far we've said "CAS happens atomically." But how is that actually possible? **A mechanism inside the CPU must make only one core pass through when multiple cores touch the same address at the same time.** That mechanism is **cache coherence**, and atomic instructions ride on top of it.

### CPU cache hierarchy — why multiple levels?

Modern CPUs don't access memory directly. Multiple cache levels sit between cores and DRAM.

| Level | Size (per core / shared) | Access time | Owner |
|-------|--------------------------|-------------|-------|
| Register | ~32 | 0 cycle | core only |
| L1 D-cache | 32–48KB | 4–5 cycle | core only |
| L1 I-cache | 32–48KB | 4–5 cycle | core only |
| L2 | 256KB–1MB | 12–15 cycle | core only (usually) |
| L3 (LLC) | 4–64MB | 30–50 cycle | shared among same-socket cores |
| DRAM | GB | 100–300 cycle (200–400ns) | everyone |
| DRAM on other socket | GB | 200–600 cycle | NUMA |

The cache unit is the **cache line**, and on almost all modern x86/ARM systems it's **64 bytes**. When a CPU reads one byte from memory, it fetches all 64.

> **Hold on, let's settle this.** If each core has its own L1, can the same variable have different values across cores?
>
> Solving exactly that problem is the **cache coherence protocol**. Multiple cores can hold copies of the same cache line, but the moment one core writes to that line, the others' copies are invalidated or updated to prevent inconsistency. The most widely used protocols are MESI (Intel) and its MOESI variant (AMD).

### MESI protocol

Each cache line is in one of four states.

| State | Meaning | Other cores |
|-------|---------|-------------|
| **M (Modified)** | only this core has it, differs from DRAM (dirty) | no copies |
| **E (Exclusive)** | only this core has it, matches DRAM (clean) | no copies |
| **S (Shared)** | multiple cores have the same value (clean) | same value present |
| **I (Invalid)** | this core's copy is invalid | (it's elsewhere) |

There's just one core rule.

> **If a cache line is in M state, only that core has it.**

When a write happens, that line in all other cores drops to I. To make this possible, cores exchange **coherence messages**.

| Message | Meaning |
|---------|---------|
| Read | "give me this line (for reading)" |
| Read-for-Ownership (RFO) | "give me this line (for writing)" — request to invalidate other cores' copies |
| Invalidate | "discard your copy of this line" |
| Read-Response | "here's that line" |

One-line summary — **a 4-state machine (M/E/S/I) that tracks who owns a cache line and whose copy is still valid**. When one core writes to a line, the others drop to I, and this is the mechanism atomic instructions use to manufacture "one at a time."

The next visualization traces a single cache line moving between two cores across 7 steps. It's a deep appendix, so it's collapsed — expand when you need it.

<details class="sy-fold" markdown="1">
<summary>▸ MESI state transitions in detail — every step of a cache line moving between cores</summary>

<div class="sy-mesi">
  <div class="sy-mesi-title">A cache line's MESI transitions — when two cores access the same line</div>

  <div class="sy-mesi-states">
    <span class="sy-mesi-stag">state</span>
    <span class="sy-mesi-state sy-mesi-m">M Modified</span>
    <span class="sy-mesi-state sy-mesi-e">E Exclusive</span>
    <span class="sy-mesi-state sy-mesi-s">S Shared</span>
    <span class="sy-mesi-state sy-mesi-i">I Invalid</span>
  </div>

  <div class="sy-mesi-grid">
    <div class="sy-mesi-h">Event</div>
    <div class="sy-mesi-h sy-mesi-h-c0">Core 0 line state</div>
    <div class="sy-mesi-h sy-mesi-h-c1">Core 1 line state</div>
    <div class="sy-mesi-h">coherence message</div>

    <div class="sy-mesi-evt"><strong>t₀</strong> Initial: nobody has it</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg">—</div>

    <div class="sy-mesi-evt"><strong>t₁</strong> Core 0 read</div>
    <div class="sy-mesi-cell sy-mesi-e">I → E</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg"><code>Read</code> → DRAM → response</div>

    <div class="sy-mesi-evt"><strong>t₂</strong> Core 0 write (atomic CAS)</div>
    <div class="sy-mesi-cell sy-mesi-m">E → M</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg">local — no message (already Exclusive)</div>

    <div class="sy-mesi-evt"><strong>t₃</strong> Core 1 attempts read</div>
    <div class="sy-mesi-cell sy-mesi-s">M → S</div>
    <div class="sy-mesi-cell sy-mesi-s">I → S</div>
    <div class="sy-mesi-msg"><code>Read</code> → Core 0 supplies dirty data, DRAM updated</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₄</strong> Core 1 write (atomic CAS) — bouncing begins</div>
    <div class="sy-mesi-cell sy-mesi-i">S → I</div>
    <div class="sy-mesi-cell sy-mesi-m">S → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO (Read-for-Ownership)</code> → Core 0's copy invalidated</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₅</strong> Core 0 writes again</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → pulls dirty data from Core 1 and invalidates Core 1</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₆</strong> Core 1 writes again</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → ping-pong continues</div>
  </div>

  <div class="sy-mesi-key">
    <strong>The M-I toggle of the same line is cache line bouncing.</strong> Intra-socket it's 30–50ns per round trip, cross-socket 150–300ns. The <code>LOCK CMPXCHG</code> instruction itself is ~10ns when the cache line is already in M state, but going through RFO makes it 30–100× more expensive. <strong>This is the real cost of lock contention.</strong>
  </div>

<style>
.sy-mesi { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-mesi-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-mesi-states { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; padding: 10px 12px; background: #edf2f7; border-radius: 5px; font-size: 11.5px; }
.sy-mesi-stag { font-weight: 700; color: #2d3748; padding-right: 6px; border-right: 1px solid #cbd5e0; }
.sy-mesi-state { padding: 3px 9px; border-radius: 3px; font-weight: 700; font-size: 11px; }
.sy-mesi-m { background: #fed7d7; color: #742a2a; }
.sy-mesi-e { background: #fbd38d; color: #7b341e; }
.sy-mesi-s { background: #bee3f8; color: #2c5282; }
.sy-mesi-i { background: #e2e8f0; color: #4a5568; }
.sy-mesi-grid { display: grid; grid-template-columns: 1.6fr 1fr 1fr 2fr; gap: 4px; }
.sy-mesi-h { font-size: 11px; font-weight: 700; padding: 8px 8px; background: #2d3748; color: #fff; text-align: center; border-radius: 3px; }
.sy-mesi-h-c0 { background: #2b6cb0; }
.sy-mesi-h-c1 { background: #2f855a; }
.sy-mesi-evt { padding: 8px 8px; font-size: 11.5px; background: #fff; border-radius: 3px; display: flex; align-items: center; }
.sy-mesi-evt strong { color: #c05621; margin-right: 6px; font-family: monospace; }
.sy-mesi-evt-hi { background: #fff5f5; border-left: 3px solid #c53030; }
.sy-mesi-cell { padding: 8px 4px; text-align: center; font-weight: 700; font-size: 11.5px; border-radius: 3px; font-family: monospace; }
.sy-mesi-msg { padding: 8px 10px; font-size: 11px; background: #fff; border-radius: 3px; color: #4a5568; display: flex; align-items: center; }
.sy-mesi-msg code { background: #edf2f7; padding: 1px 6px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; margin: 0 4px; }
.sy-mesi-msg-hi { background: #fff5f5; }
.sy-mesi-msg-hi code { background: #fed7d7; color: #c53030; }
.sy-mesi-key { margin-top: 16px; padding: 12px 14px; background: #fff5f5; border-left: 3px solid #c53030; border-radius: 3px; font-size: 12px; color: #742a2a; line-height: 1.55; }
.sy-mesi-key strong { color: #c53030; }
.sy-mesi-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; }

[data-mode="dark"] .sy-mesi { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-mesi-title { color: #e2e8f0; }
[data-mode="dark"] .sy-mesi-states { background: #2d3748; }
[data-mode="dark"] .sy-mesi-stag { color: #e2e8f0; border-right-color: #4a5568; }
[data-mode="dark"] .sy-mesi-m { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-mesi-e { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-mesi-s { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-mesi-i { background: #2d3748; color: #a0aec0; }
[data-mode="dark"] .sy-mesi-evt { background: #2d3748; color: #e2e8f0; }
[data-mode="dark"] .sy-mesi-evt-hi { background: #742a2a; border-left-color: #fc8181; }
[data-mode="dark"] .sy-mesi-msg { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-mesi-msg code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-mesi-msg-hi { background: #742a2a; }
[data-mode="dark"] .sy-mesi-msg-hi code { background: #1a202c; color: #feb2b2; }
[data-mode="dark"] .sy-mesi-key { background: #742a2a; color: #fed7d7; border-left-color: #fc8181; }
[data-mode="dark"] .sy-mesi-key strong { color: #feb2b2; }
[data-mode="dark"] .sy-mesi-key code { background: #1a202c; }

@media (max-width: 768px) {
  .sy-mesi { padding: 14px 8px 12px; }
  .sy-mesi-title { font-size: 13px; }
  .sy-mesi-states { gap: 5px; padding: 8px 10px; }
  .sy-mesi-state { padding: 2px 6px; font-size: 9.5px; }
  .sy-mesi-grid { grid-template-columns: 1.5fr 0.8fr 0.8fr 1.8fr; gap: 3px; }
  .sy-mesi-h { font-size: 9.5px; padding: 6px 4px; }
  .sy-mesi-evt { font-size: 9.5px; padding: 6px 6px; }
  .sy-mesi-cell { padding: 6px 2px; font-size: 9.5px; }
  .sy-mesi-msg { font-size: 9.5px; padding: 6px 7px; }
  .sy-mesi-msg code { font-size: 9px; padding: 1px 3px; }
  .sy-mesi-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

</details>

<style>
.sy-fold { margin: 20px 0; border: 1px solid #cbd5e0; border-radius: 6px; background: #f7fafc; overflow: hidden; }
.sy-fold > summary { padding: 12px 16px; cursor: pointer; font-weight: 700; font-size: 13.5px; color: #2b6cb0; background: #edf2f7; list-style: none; user-select: none; transition: background 0.15s; }
.sy-fold > summary::-webkit-details-marker { display: none; }
.sy-fold > summary:hover { background: #e2e8f0; }
.sy-fold[open] > summary { background: #ebf8ff; border-bottom: 1px solid #cbd5e0; color: #2c5282; }
.sy-fold > summary::before { content: ""; display: inline-block; width: 0; height: 0; margin-right: 10px; vertical-align: middle; border-left: 6px solid #2b6cb0; border-top: 4px solid transparent; border-bottom: 4px solid transparent; transition: transform 0.15s; }
.sy-fold[open] > summary::before { transform: rotate(90deg); }
.sy-fold > *:not(summary):first-of-type { margin-top: 4px; }

[data-mode="dark"] .sy-fold { background: #1a202c; border-color: #4a5568; }
[data-mode="dark"] .sy-fold > summary { background: #2d3748; color: #90cdf4; }
[data-mode="dark"] .sy-fold > summary:hover { background: #4a5568; }
[data-mode="dark"] .sy-fold[open] > summary { background: #1a365d; border-bottom-color: #4a5568; color: #bee3f8; }
[data-mode="dark"] .sy-fold > summary::before { border-left-color: #90cdf4; }

@media (max-width: 768px) {
  .sy-fold > summary { padding: 10px 12px; font-size: 12px; }
}
</style>

### What an atomic instruction actually does

When `LOCK CMPXCHG` executes on x86:

1. CPU fetches the target memory address's cache line **into Modified state** (RFO message invalidates other cores' copies)
2. While the line is in M state — **even if other cores send RFO simultaneously, the cache coherence mechanism serializes them** — compare and swap proceeds
3. The line stays in M or gets evicted at some later point

The point: atomic's "atomicity" comes from **the hardware fact that cache coherence serializes RFO requests**. There isn't a separate lock — the cache protocol's invariant that a single line can only be in M state on one core at a time *is* the lock.

ARM is slightly different. ARM uses **LL/SC (Load-Linked / Store-Conditional)** pairs.

```asm
loop:
    LDXR  w0, [x1]        ; load-exclusive, tracks address x1
    CMP   w0, w_expected
    B.NE  fail
    STXR  w2, w_desired, [x1]  ; store-exclusive, fails if x1 was modified meanwhile
    CBNZ  w2, loop        ; retry on failure
```

LL/SC's advantage: immunity to part of the CAS ABA problem. Its drawback: failure is possible so a retry loop is needed.

### cache line bouncing — the real cost of locks

What happens when two cores take turns grabbing the same lock?

Core A takes the lock → cache line in M state on A
Core B tries CAS → cache line moves from A to B; A becomes I, B becomes M
Core A takes the lock again → moves from B to A; B becomes I, A becomes M

This ping-pong is **cache line bouncing**. Cost per bounce:

| Scenario | Cost |
|----------|------|
| Cores sharing same L3 (intra-socket) | ~30–50ns |
| Different sockets (NUMA, cross-socket) | ~150–300ns |
| Different NUMA nodes | ~hundreds to 1000ns |

The `LOCK CMPXCHG` instruction itself costs ~10ns when the line is already in M state. **With bouncing, it becomes 30–100× more expensive.** That's the real cost of lock contention, and why the cache effect matters more than the lock itself.

> **Hold on, let's settle this.** If cache coherence guarantees consistency automatically, why do we still need locks?
>
> They guarantee different things.
>
> - **Cache coherence** promises "all copies of one cache line will eventually be consistent." Per-memory-location.
> - **Lock** promises "make a critical section spanning multiple memory locations behave as a single transaction." Per-semantic-unit.
>
> For example `account_a -= x; account_b += x;` spans two cache lines. Coherence guarantees consistency of each line, but a lock guarantees that both changes appear together.

### False sharing — unintentional cache line bouncing

Consider this struct.

```cpp
struct Counters {
    std::atomic<int> threadA_count;  /* offset 0  */
    std::atomic<int> threadB_count;  /* offset 4  */
};
```

Thread A only touches its counter, thread B only touches its own. Logically there's no shared data. But if the two atomics **sit in the same 64-byte cache line**, A's write invalidates B's line and vice versa. They ping-pong meaninglessly. This is **false sharing**.

The fix is **cache line alignment**.

```cpp
struct Counters {
    alignas(64) std::atomic<int> threadA_count;  /* line 0 */
    alignas(64) std::atomic<int> threadB_count;  /* line 1 */
};
```

C++17 provides the `std::hardware_destructive_interference_size` constant to know the cache line size at compile time.

In game engine code, false sharing typically shows up in:

- per-thread stat arrays — `int hits[NUM_THREADS]` with adjacent slots
- producer/consumer ring buffer head/tail pointers
- arrays of small Job structures packed tightly

Measurement is hard. The CPU counter `mem_load_uops_l3_hit_retired.xsnp_hitm` (Intel) is one indicator that catches false sharing. Linux `perf c2c` automates this.

### Memory barrier — the hardware side of ordering

Cache coherence makes values consistent, but **ordering** is a separate problem. CPUs reorder instructions, and store buffers briefly hold writes inside the issuing core.

```cpp
/* Thread A */
data = 42;
ready = true;       /* is the order of these two stores guaranteed to other cores? */

/* Thread B */
if (ready)
    use(data);      /* is data really 42? */
```

x86 has **TSO (Total Store Order)** so store-store reordering doesn't occur, but ARM is weakly ordered and the above code can break. ARM needs a **memory barrier (`DMB ST`)** between the two stores.

One thing a lock promises us is this ordering. `mutex.unlock()` internally includes a `release`-semantics barrier, and `mutex.lock()` includes an `acquire`-semantics barrier, so values written inside the lock appear consistently outside.

| Barrier | x86 | ARM | Meaning |
|---------|-----|-----|---------|
| store-store | (automatic) | DMB ST | after prior stores complete, then later stores |
| load-load | (automatic) | DMB LD | after prior loads complete, then later loads |
| store-load | MFENCE | DMB SY | prior store becomes globally visible, then later loads |
| full | MFENCE | DMB SY | serialize all memory operations |

Part 12 handles this in depth. The point here is just that **a lock is a bundle of atomic instructions + barriers**.

### Summary: what one lock causes

A `mutex.lock()` / `mutex.unlock()` pair traverses these steps, from user space to hardware cache:

<div class="sy-mflow">
  <div class="sy-mflow-title">mutex.lock() → critical section → mutex.unlock() — all layers</div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-lock">mutex.lock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">1</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>request cache line ownership</strong><br>
          <span>send RFO message to other cores</span>
        </div>
        <div class="sy-mflow-cost">~30–300ns</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">2</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>invalidate other cores' copies</strong><br>
          <span>bring that line into I state and fetch data (becomes M)</span>
        </div>
        <div class="sy-mflow-cost">RFO response</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">3</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>execute atomic instruction</strong><br>
          <span><code>LOCK CMPXCHG</code> (x86) · <code>LDXR/STXR</code> (ARM): try 0 → 1</span>
        </div>
        <div class="sy-mflow-cost">~10ns</div>
      </div>
      <div class="sy-mflow-branch">
        <div class="sy-mflow-bok"><strong>✓ success</strong> — fast path done, enter critical section</div>
        <div class="sy-mflow-bno"><strong>✗ failure</strong> — proceed to slow path</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">4</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>enter kernel wait queue</strong><br>
          <span><code>futex_wait</code> / <code>NtWaitForAlertByThreadId</code> / <code>__ulock_wait</code> — register on wait queue and sleep</span>
        </div>
        <div class="sy-mflow-cost">~hundreds ns + sleep</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">5</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>acquire ordering constraint</strong><br>
          <span>prevent memory ops after the atomic from being reordered before it — ARM uses <code>DMB ISH</code> or <code>LDA*</code>, x86 plain load suffices</span>
        </div>
        <div class="sy-mflow-cost">~few ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-cs">
    <span class="sy-mflow-cs-h">— critical section —</span>
    <span class="sy-mflow-cs-d">no one else can enter on the same lock during this time</span>
  </div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-unlock">mutex.unlock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">6</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>release ordering constraint</strong><br>
          <span>prevent values written inside the lock from being reordered after the unlock store — ARM uses <code>DMB ISH</code> or <code>STL*</code>, x86 plain store suffices</span>
        </div>
        <div class="sy-mflow-cost">~few ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">7</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>atomic store</strong><br>
          <span>set lock variable to 0 (including waiters-bit check)</span>
        </div>
        <div class="sy-mflow-cost">~5ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">8</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>wake waiters (only if present)</strong><br>
          <span><code>futex_wake</code> / <code>NtAlertThreadByThreadId</code> / <code>__ulock_wake</code></span>
        </div>
        <div class="sy-mflow-cost">~hundreds ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-legend">
    <span class="sy-mflow-lg sy-mflow-layer-hw">HW</span>cache coherence / MESI
    <span class="sy-mflow-lg sy-mflow-layer-cpu">CPU</span>atomic instruction + barrier
    <span class="sy-mflow-lg sy-mflow-layer-os">OS</span>kernel wait queue (slow path only)
  </div>

<style>
.sy-mflow { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-mflow-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-mflow-section { margin-bottom: 4px; }
.sy-mflow-sh { font-size: 12.5px; font-weight: 800; padding: 6px 12px; border-radius: 4px 4px 0 0; display: inline-block; }
.sy-mflow-sh-lock   { background: #2b6cb0; color: #fff; }
.sy-mflow-sh-unlock { background: #2f855a; color: #fff; }
.sy-mflow-steps { padding: 10px 10px; background: #fff; border: 1px solid #cbd5e0; border-radius: 0 6px 6px 6px; }
.sy-mflow-step { display: grid; grid-template-columns: 32px 56px 1fr 90px; gap: 10px; padding: 8px 8px; margin: 3px 0; border-radius: 4px; background: #f7fafc; align-items: center; }
.sy-mflow-step-pivot { background: #ebf8ff; }
.sy-mflow-step-slow { background: #fff5f5; }
.sy-mflow-stnum { width: 26px; height: 26px; line-height: 26px; text-align: center; background: #4a5568; color: #fff; border-radius: 50%; font-weight: 700; font-size: 11.5px; }
.sy-mflow-step-pivot .sy-mflow-stnum { background: #2b6cb0; }
.sy-mflow-step-slow .sy-mflow-stnum { background: #c53030; }
.sy-mflow-stlayer { font-size: 10px; font-weight: 800; padding: 4px 6px; border-radius: 3px; text-align: center; letter-spacing: 0.05em; }
.sy-mflow-layer-hw  { background: #fbd38d; color: #7b341e; }
.sy-mflow-layer-cpu { background: #bee3f8; color: #2c5282; }
.sy-mflow-layer-os  { background: #d6bcfa; color: #44337a; }
.sy-mflow-stbody { font-size: 11.5px; color: #2d3748; line-height: 1.45; }
.sy-mflow-stbody strong { color: #1a202c; }
.sy-mflow-stbody span { display: block; font-size: 10.5px; color: #4a5568; margin-top: 2px; }
.sy-mflow-stbody code { background: #edf2f7; padding: 1px 5px; border-radius: 2px; font-family: monospace; color: #2b6cb0; font-weight: 700; font-size: 10px; }
.sy-mflow-cost { font-size: 11px; color: #c05621; text-align: right; font-weight: 700; font-family: monospace; }
.sy-mflow-branch { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 4px 0; padding: 0 8px; }
.sy-mflow-bok { padding: 6px 10px; background: #c6f6d5; color: #22543d; border-radius: 4px; font-size: 11px; font-weight: 600; }
.sy-mflow-bno { padding: 6px 10px; background: #fed7d7; color: #742a2a; border-radius: 4px; font-size: 11px; font-weight: 600; }
.sy-mflow-bok strong, .sy-mflow-bno strong { font-weight: 800; }
.sy-mflow-cs { text-align: center; padding: 12px 14px; margin: 6px 0; background: linear-gradient(90deg, transparent, #fef5e7, transparent); border-radius: 0; }
.sy-mflow-cs-h { font-size: 12px; font-weight: 700; color: #7b341e; letter-spacing: 0.05em; }
.sy-mflow-cs-d { display: block; font-size: 11px; color: #4a5568; margin-top: 4px; font-style: italic; }
.sy-mflow-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; margin-top: 16px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 11px; color: #4a5568; }
.sy-mflow-lg { padding: 3px 7px; border-radius: 3px; font-size: 9.5px; font-weight: 800; letter-spacing: 0.05em; margin-right: 4px; }

[data-mode="dark"] .sy-mflow { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-mflow-title { color: #e2e8f0; }
[data-mode="dark"] .sy-mflow-steps { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-mflow-step { background: #1a202c; }
[data-mode="dark"] .sy-mflow-step-pivot { background: #1a365d; }
[data-mode="dark"] .sy-mflow-step-slow { background: #742a2a; }
[data-mode="dark"] .sy-mflow-stbody { color: #e2e8f0; }
[data-mode="dark"] .sy-mflow-stbody strong { color: #f7fafc; }
[data-mode="dark"] .sy-mflow-stbody span { color: #cbd5e0; }
[data-mode="dark"] .sy-mflow-stbody code { background: #2d3748; color: #90cdf4; }
[data-mode="dark"] .sy-mflow-cost { color: #fbd38d; }
[data-mode="dark"] .sy-mflow-layer-hw  { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-mflow-layer-cpu { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-mflow-layer-os  { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-mflow-bok { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-mflow-bno { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-mflow-cs { background: linear-gradient(90deg, transparent, #5f370e, transparent); }
[data-mode="dark"] .sy-mflow-cs-h { color: #fbd38d; }
[data-mode="dark"] .sy-mflow-cs-d { color: #cbd5e0; }
[data-mode="dark"] .sy-mflow-legend { color: #cbd5e0; border-top-color: #4a5568; }

@media (max-width: 768px) {
  .sy-mflow { padding: 14px 8px 12px; }
  .sy-mflow-title { font-size: 13px; }
  .sy-mflow-step { grid-template-columns: 26px 42px 1fr; gap: 6px; padding: 6px 6px; }
  .sy-mflow-cost { grid-column: 1 / -1; text-align: left; padding-left: 76px; font-size: 9.5px; }
  .sy-mflow-stnum { width: 22px; height: 22px; line-height: 22px; font-size: 10px; }
  .sy-mflow-stlayer { font-size: 9px; padding: 3px 4px; }
  .sy-mflow-stbody { font-size: 10.5px; }
  .sy-mflow-stbody span { font-size: 9.5px; }
  .sy-mflow-stbody code { font-size: 9px; }
  .sy-mflow-branch { padding: 0 4px; }
  .sy-mflow-bok, .sy-mflow-bno { font-size: 10px; padding: 5px 8px; }
  .sy-mflow-cs-h { font-size: 11px; }
  .sy-mflow-cs-d { font-size: 10px; }
  .sy-mflow-legend { font-size: 10px; gap: 8px; }
}
</style>
</div>

That's the bottom of locks. Now we see how game engines solve synchronization on top of all this.

---

## Part 6: Unity Synchronization — Main Thread, Job System, DOTS

Game engines don't use locks as is. One frame at 60fps is 16.67ms, and a single lock contention can cost 100–300ns to a few μs. A thousand of them eat 1ms before anything else. So engines adopt **lock-avoiding structures**. Two ideas are central:

1. **Thread affinity**: certain data is touched by only one thread (then no lock is needed at all)
2. **Dependency-based parallelism**: instead of locks, build a dependency graph that prevents read/write conflicts at scheduling time

Unity does exactly these two.

### Main Thread model

All Unity `MonoBehaviour` callbacks — `Update`, `LateUpdate`, `FixedUpdate`, `OnGUI`, `OnTriggerEnter`, etc. — execute **on a single thread, the Main Thread**. And almost every Unity API (`Transform.position`, `GameObject.Find`, `Component.GetComponent`, etc.) can only be called from the main thread. Calling from another thread throws `UnityException: ... can only be called from the main thread.`

This is an enormous simplification. There isn't a single lock in the entire scene graph — because all access is on one thread.

> **Hold on, let's settle this.** Is Unity's main thread OS thread #1?
>
> "#1" is meaningless from the OS perspective. The main thread is whichever thread is created first when the Unity process starts; from the OS's view it's a normal pthread/Win32 thread. The Unity runtime simply records this thread's ID and uses it for `IsMainThread()` checks. On macOS, the main thread is tied to NSRunLoop and runs alongside UI events.

The pitfall of the main thread model is one thing. **Heavy work on the main thread is frame drops, period.** That's why Unity spins up worker threads separately and provides the abstraction called **Job System** on top.

### Unity Job System

The Job System does two things at once.

1. **Parallel processing on native memory**: doesn't touch the managed heap, so GC-irrelevant
2. **Race detection at schedule time**: dependency graph and NativeContainer safety check read/write conflicts. The attributes (`[ReadOnly]`/`[WriteOnly]`/`[NativeDisableContainerSafetyRestriction]`) are read by the compiler, but **the actual conflict check is a runtime check at the time of `Schedule()`** and is enabled only with the `ENABLE_UNITY_COLLECTIONS_CHECKS` macro (Editor/Development builds)

Basic usage:

```csharp
public struct ApplyVelocityJob : IJobParallelFor {
    [ReadOnly]  public NativeArray<float3> velocities;
    [WriteOnly] public NativeArray<float3> positions;
    public float deltaTime;

    public void Execute(int index) {
        positions[index] += velocities[index] * deltaTime;
    }
}

void Update() {
    var job = new ApplyVelocityJob {
        velocities = velocityBuffer,
        positions = positionBuffer,
        deltaTime = Time.deltaTime,
    };
    JobHandle handle = job.Schedule(positionBuffer.Length, 64);  /* batch=64 */
    handle.Complete();
}
```

`Schedule` doesn't execute the job immediately — it **registers it in the dependency graph**. `JobHandle` tracks the job's completion.

#### Internal flow — where does one call go?

Tracing what `Schedule()` triggers, step by step:

1. **Compile time**: IL2CPP/Burst reads the `[ReadOnly]`, `[WriteOnly]` attributes and marks `velocities` as read-only, `positions` as write-only
2. **Schedule call (main thread)**:
   - Creates a JobHandle and registers dependencies
   - Copies the Job struct into unmanaged memory (so workers don't touch the main heap)
   - Inspects the NativeContainers' AtomicSafetyHandle — if another in-flight job writes the same container, throws a runtime exception (not at compile time)
3. **Worker thread (`Unity Job Worker N`)**:
   - Pulls a job from its own wait list (work-stealing deque)
   - For `IJobParallelFor`, slices the index range into batches (64 each) and distributes
   - Calls `Execute(index)` for each batch
4. **Complete call (main thread)**:
   - `handle.Complete()` checks that all transitively dependent jobs are done in the dependency graph
   - If not done, the main thread also acts as a worker and steals jobs (work-stealing — main thread becomes a worker too)

#### How does data flow between cores?

Trace how `positionBuffer` is touched by a worker thread, in cache units.

1. **At Schedule time**: the first 64 slots of `positionBuffer` (16 bytes × 64 = 1024 bytes = 16 cache lines) are in the main thread CPU's L1/L2 (touched in the previous frame).
2. **Worker thread starts**: worker N receives `Execute(0)` ~ `Execute(63)`. If the worker is on a different core, **RFO messages** are issued for the 64 slots' cache lines. The lines move from the main thread's L1 to the worker core's L1 — at 30–50ns each intra-socket, 16 lines means ~600ns warmup for the first batch.
3. **Batch execution**: as the worker processes 64 sequentially, the cache lines stay in the worker core's L1. With 16-byte slots, 4 per line, the line is touched 4 times in M state — cache hit.
4. **Next batch (64–127)**: another 16 lines move to the worker's L1. The previous 16 lines get evicted or remain in worker's L2/L3.
5. **At Complete time**: when the main thread reads the results, all lines RFO back to the main CPU.

Two costs are visible:

- **First batch warmup**: cache lines moving from main → worker
- **Result reclamation**: lines moving back from worker → main

So if a Job's input/output is small, the scheduling overhead itself can exceed the work cost. The `batchCount` parameter (64 above) of `IJobParallelFor` tunes this tradeoff. Too small means cache miss + dispatch overhead at every batch boundary; too large means load balancing breaks. Unity docs guide "16–64 is usually better than 1" for this reason.

The figure below shows the Job dependency DAG and worker mapping. The top is the dependency graph (logical order), the bottom is the actual worker thread mapping (time axis).

<div class="sy-unity">
  <div class="sy-unity-title">Unity Job System — dependency DAG and worker mapping</div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">dependency DAG (logical order)</div>
    <div class="sy-unity-dag">
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-r">VelocityJob<br><span>read input</span></div>
        <div class="sy-unity-node sy-unity-node-r">CollisionJob<br><span>read AABB</span></div>
      </div>
      <div class="sy-unity-arrows">
        <span class="sy-unity-edge"></span>
        <span class="sy-unity-edge"></span>
      </div>
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-w">ApplyVelocityJob<br><span>write Position</span></div>
      </div>
      <div class="sy-unity-arrows">
        <span class="sy-unity-edge sy-unity-edge-c"></span>
      </div>
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-r">RenderBoundsJob<br><span>read Position</span></div>
        <div class="sy-unity-node sy-unity-node-r">CullingJob<br><span>read Position</span></div>
      </div>
      <div class="sy-unity-deplabel">read-after-write — dependency added automatically</div>
    </div>
  </div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">worker thread mapping (actual execution, time →)</div>
    <div class="sy-unity-timeline">
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel sy-unity-tlabel-main">Main Thread</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-main" style="flex: 1">Update / Schedule</div>
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 3">work-stealing</div>
          <div class="sy-unity-blk sy-unity-blk-sync" style="flex: 1">Complete</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 1</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.2">Vel[0..15]</div>
          <div class="sy-unity-blk sy-unity-blk-w" style="flex: 1.4">ApplyVel[0..15]</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">RenderB[0..15]</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 2</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.2">Vel[16..31]</div>
          <div class="sy-unity-blk sy-unity-blk-w" style="flex: 1.4">ApplyVel[16..31]</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">Culling[0..31]</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 3</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">Collision[0..63]</div>
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1.2">wait dep</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">RenderB[16..31]</div>
        </div>
      </div>
      <div class="sy-unity-axis"><span>schedule</span><span>parallel reads</span><span>writes</span><span>parallel reads</span><span>sync</span></div>
    </div>
  </div>

  <div class="sy-unity-cache">
    <div class="sy-unity-sec">data flow — while Worker 1 runs ApplyVel[0..15]</div>
    <div class="sy-unity-cacheflow">
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">①</div>
        <div class="sy-unity-cstep-t">at Schedule</div>
        <div class="sy-unity-cstep-d">positionBuffer[0..15] cache lines sit in main CPU L1</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-rfo">
        <div class="sy-unity-cstep-i">②</div>
        <div class="sy-unity-cstep-t">worker starts</div>
        <div class="sy-unity-cstep-d">RFO messages move the lines to the worker CPU's L1 (~30–50ns × 4 lines)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-hot">
        <div class="sy-unity-cstep-i">③</div>
        <div class="sy-unity-cstep-t">batch execution</div>
        <div class="sy-unity-cstep-d">16 slots = 4 lines, all stay in worker L1 (cache hit, M state)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">④</div>
        <div class="sy-unity-cstep-t">Complete</div>
        <div class="sy-unity-cstep-d">result lines RFO back to main CPU (on read)</div>
      </div>
    </div>
  </div>

  <div class="sy-unity-key">
    <strong>Not a single lock.</strong> Dependencies between Jobs are expressed as a graph, read-after-write conflicts are serialized at Schedule time, and jobs sharing the same read permission flow freely in parallel. AtomicSafetyHandle's runtime check at <code>Schedule()</code> time (Editor/Development builds only) catches container-permission conflicts and throws exceptions.
  </div>

<style>
.sy-unity { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-unity-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-unity-block { margin-bottom: 18px; }
.sy-unity-sec { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; padding-left: 6px; border-left: 3px solid #2b6cb0; letter-spacing: 0.02em; }
.sy-unity-dag { padding: 14px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-row { display: flex; gap: 12px; justify-content: center; margin: 6px 0; flex-wrap: wrap; }
.sy-unity-node { padding: 8px 14px; border-radius: 5px; font-weight: 700; font-size: 11.5px; text-align: center; min-width: 120px; }
.sy-unity-node span { display: block; font-size: 10px; font-weight: 500; opacity: 0.85; margin-top: 2px; font-family: monospace; }
.sy-unity-node-r { background: #c6f6d5; color: #22543d; }
.sy-unity-node-w { background: #fed7aa; color: #7b341e; }
.sy-unity-arrows { display: flex; justify-content: center; gap: 80px; height: 14px; align-items: center; }
.sy-unity-edge { width: 1px; height: 14px; background: linear-gradient(to bottom, #cbd5e0 0 60%, transparent 60% 100%); position: relative; }
.sy-unity-edge:after { content: ""; position: absolute; bottom: 0; left: -3px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #4a5568; }
.sy-unity-edge-c { background: #c53030; }
.sy-unity-edge-c:after { border-top-color: #c53030; }
.sy-unity-deplabel { text-align: center; font-size: 10.5px; color: #c53030; font-style: italic; margin-top: 4px; font-weight: 600; }

.sy-unity-timeline { padding: 12px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-trow { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.sy-unity-tlabel { flex: 0 0 86px; font-size: 11px; font-weight: 700; color: #2d3748; text-align: right; }
.sy-unity-tlabel-main { color: #c53030; }
.sy-unity-track { display: flex; flex: 1; height: 30px; border: 1px solid #e2e8f0; border-radius: 3px; overflow: hidden; }
.sy-unity-blk { display: flex; align-items: center; justify-content: center; font-size: 10.5px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.08); }
.sy-unity-blk:last-child { border-right: 0; }
.sy-unity-blk-main { background: #fed7d7; color: #742a2a; }
.sy-unity-blk-r { background: #c6f6d5; color: #22543d; }
.sy-unity-blk-w { background: #fed7aa; color: #7b341e; }
.sy-unity-blk-sync { background: #d6bcfa; color: #44337a; }
.sy-unity-blk-idle { background: #f7fafc; color: #a0aec0; font-style: italic; font-weight: 500; }
.sy-unity-axis { display: flex; justify-content: space-around; margin-top: 6px; padding-left: 94px; font-size: 10px; color: #718096; font-family: monospace; }

.sy-unity-cache { padding: 12px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-cacheflow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sy-unity-cstep { flex: 1 1 130px; padding: 10px 10px; background: #ebf8ff; border-radius: 5px; min-height: 80px; display: flex; flex-direction: column; gap: 4px; }
.sy-unity-cstep-rfo { background: #fef5e7; }
.sy-unity-cstep-hot { background: #c6f6d5; }
.sy-unity-cstep-i { font-weight: 800; color: #2b6cb0; font-size: 14px; }
.sy-unity-cstep-rfo .sy-unity-cstep-i { color: #c05621; }
.sy-unity-cstep-hot .sy-unity-cstep-i { color: #2f855a; }
.sy-unity-cstep-t { font-weight: 700; font-size: 11.5px; color: #1a202c; }
.sy-unity-cstep-d { font-size: 10.5px; color: #4a5568; line-height: 1.45; }
.sy-unity-carrow { font-size: 16px; color: #cbd5e0; font-weight: 700; }
.sy-unity-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-unity-key strong { color: #2b6cb0; }
.sy-unity-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 11px; }

[data-mode="dark"] .sy-unity { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-unity-title { color: #e2e8f0; }
[data-mode="dark"] .sy-unity-sec { color: #90cdf4; border-left-color: #4299e1; }
[data-mode="dark"] .sy-unity-dag { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-node-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-unity-node-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-unity-edge { background: linear-gradient(to bottom, #4a5568 0 60%, transparent 60% 100%); }
[data-mode="dark"] .sy-unity-edge:after { border-top-color: #4a5568; }
[data-mode="dark"] .sy-unity-edge-c { background: #feb2b2; }
[data-mode="dark"] .sy-unity-edge-c:after { border-top-color: #feb2b2; }
[data-mode="dark"] .sy-unity-deplabel { color: #feb2b2; }
[data-mode="dark"] .sy-unity-timeline { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-tlabel { color: #e2e8f0; }
[data-mode="dark"] .sy-unity-tlabel-main { color: #feb2b2; }
[data-mode="dark"] .sy-unity-track { border-color: #4a5568; }
[data-mode="dark"] .sy-unity-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.05); }
[data-mode="dark"] .sy-unity-blk-main { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-unity-blk-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-unity-blk-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-unity-blk-sync { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-unity-blk-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-unity-axis { color: #a0aec0; }
[data-mode="dark"] .sy-unity-cache { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-cstep { background: #1a365d; }
[data-mode="dark"] .sy-unity-cstep-rfo { background: #5f370e; }
[data-mode="dark"] .sy-unity-cstep-hot { background: #22543d; }
[data-mode="dark"] .sy-unity-cstep-i { color: #90cdf4; }
[data-mode="dark"] .sy-unity-cstep-rfo .sy-unity-cstep-i { color: #fbd38d; }
[data-mode="dark"] .sy-unity-cstep-hot .sy-unity-cstep-i { color: #9ae6b4; }
[data-mode="dark"] .sy-unity-cstep-t { color: #f7fafc; }
[data-mode="dark"] .sy-unity-cstep-d { color: #cbd5e0; }
[data-mode="dark"] .sy-unity-carrow { color: #4a5568; }
[data-mode="dark"] .sy-unity-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-unity-key strong { color: #90cdf4; }
[data-mode="dark"] .sy-unity-key code { background: #2d3748; color: #90cdf4; }

@media (max-width: 768px) {
  .sy-unity { padding: 14px 8px 12px; }
  .sy-unity-title { font-size: 13px; }
  .sy-unity-node { padding: 6px 10px; font-size: 10.5px; min-width: 100px; }
  .sy-unity-node span { font-size: 9px; }
  .sy-unity-tlabel { flex-basis: 60px; font-size: 9.5px; }
  .sy-unity-track { height: 24px; }
  .sy-unity-blk { font-size: 9px; }
  .sy-unity-axis { font-size: 8.5px; padding-left: 68px; }
  .sy-unity-cacheflow { flex-direction: column; }
  .sy-unity-cstep { flex-basis: auto; }
  .sy-unity-carrow { transform: rotate(90deg); }
  .sy-unity-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

#### NativeContainer and AtomicSafetyHandle

Unity catches races even on non-GC native memory. How?

NativeContainers like `NativeArray<T>`, `NativeList<T>`, `NativeQueue<T>` carry an internal **AtomicSafetyHandle**. It's debug metadata enabled only in Editor and Development builds. Roughly:

```csharp
struct AtomicSafetyHandle {
    int version;          /* has the container been disposed? */
    AtomicSafetyNodePtr nodePtr;  /* manages read/write reader lists */
}
```

The handle tracks:

- **Jobs currently writing this container**: 0 or 1 (if 1, no one else can even read)
- **Jobs currently reading this container**: N (writers blocked)
- **Whether the container is alive (DisposeSentinel)**: throws immediately on access to a disposed container

At Schedule time, Unity compares the job's `[ReadOnly]/[WriteOnly]` markings with the AtomicSafetyHandle state and **throws an exception when it finds a possible conflict**. It blocks the Schedule call itself.

```csharp
var a = new NativeArray<int>(100, Allocator.TempJob);
var jobA = new WriteJob { data = a }.Schedule();          /* writes a */
var jobB = new ReadJob  { data = a }.Schedule();          /* reads a — conflict! */
/* InvalidOperationException: The previously scheduled job WriteJob writes
   to the NativeArray a. You must call JobHandle.Complete() on the job
   before you can read from the NativeArray safely. */
```

The fix is to express the dependency:

```csharp
var handleA = jobA.Schedule();
var handleB = jobB.Schedule(handleA);   /* B after A */
handleB.Complete();
```

To bypass this, you add `[NativeDisableContainerSafetyRestriction]`, but that's a declaration of "I take responsibility for the race." Use only when truly safe — e.g., two jobs with non-overlapping index ranges.

> **Hold on, let's settle this.** Does AtomicSafetyHandle work in production builds?
>
> No. It's enabled only in Editor and Development builds, gated by the `ENABLE_UNITY_COLLECTIONS_CHECKS` macro. Release builds strip all safety check code. **This is not a static guarantee** — a clean run in the Editor means *for the code paths exercised at that time* the safety system didn't see a conflict, but it isn't a proof that no race will occur under different inputs and different timing. So before shipping to production, you need tests that exercise as many code paths as possible, and `[NativeDisableContainerSafetyRestriction]` paths bypass the check entirely, so they require extra care.

#### Burst — how is atomic guaranteed?

In short — **Burst compiles IL to native code via LLVM, but it does not turn ordinary array accesses into atomics.** If you need atomic, you must call `Interlocked.*` explicitly, and only those get emitted as hardware atomic instructions. That's the key point; the 4–5 steps below are compiler internals and are collapsed.

<details class="sy-fold" markdown="1">
<summary>▸ Burst compile pipeline in detail — IL → native, atomic emit, NoAlias, SIMD mapping</summary>

A job tagged `[BurstCompile]` is compiled to native code instead of IL (LLVM backend). What Burst does when compiling NativeArray access:

1. **Ordinary `array[i]` reads/writes are plain load/store** — not atomic. Races are possible, and conflict prevention depends on schedule-time dependency + safety system
2. **Only explicit atomic calls like `Interlocked.*`** are emitted directly as hardware atomic instructions like x86 `LOCK XADD` / `LOCK CMPXCHG` or ARM `LDADD` / `LDXR-STXR`
3. Keeps bounds checks SIMD-friendly, or enables them only in the Editor
4. Uses `[NoAlias]` hints to assume ptr aliasing — enables more aggressive compiler optimization
5. Maps SIMD intrinsics (`Unity.Mathematics.float4`) to SSE/AVX/NEON

```csharp
[BurstCompile]
public struct CountJob : IJobParallelFor {
    [NativeDisableContainerSafetyRestriction]
    public NativeArray<int> counter;   /* length 1, all jobs share the same slot */

    public void Execute(int i) {
        unsafe {
            Interlocked.Increment(ref UnsafeUtility.As<int, int>(
                ref counter.GetUnsafePtrReadOnly()[0]));
        }
    }
}
```

The moment Burst sees `Interlocked.Increment`, on x86 it emits directly as `LOCK INC` or `LOCK XADD`. That is, the hardware atomic instructions from Part 5 happen exactly as is. Cache line bouncing costs apply just the same.

> **Hold on, let's settle this.** What happens when jobs write to slots in the same cache line simultaneously?
>
> That's exactly **false sharing**. In the example above, with a length-1 counter, every job does atomic increment, so that 1 byte (actually 4 bytes, 1 line) ping-pongs between cores endlessly. A million calls vanish 50–100ms in cache bouncing alone. The fix is per-thread local counters on different cache lines, summed at the end — `[ThreadStatic]` or `NativeQueue<int>.Concurrent`'s enqueue pattern.

</details>

#### DOTS / ECS — system-level dependencies

`SystemBase` or `ISystem`-based ECS takes the above mechanism one step further.

```csharp
public partial struct MoveSystem : ISystem {
    public void OnUpdate(ref SystemState state) {
        new MoveJob { dt = SystemAPI.Time.DeltaTime }
            .ScheduleParallel();
    }
}

[BurstCompile]
public partial struct MoveJob : IJobEntity {
    public float dt;
    void Execute(ref LocalTransform t, in Velocity v) {
        t.Position += v.Value * dt;
    }
}
```

`IJobEntity` automatically extracts read/write component access from the signature (`ref` = write, `in` = read). The source generator creates metadata for this info at compile time, and at runtime the World scheduler reads it and handles the following automatically:

- Two systems writing the same Component get **automatic ordering**
- Systems touching different Components **automatically run in parallel**

This is the most extreme example of resolving synchronization not with locks but with a dependency graph. The programmer never locks, but the scheduler checks read/write permissions at Schedule time and serializes conflicts (Editor/Development builds get additional safety system checks).

Internally, ECS maintains dependency info per Component with ReaderWriterLock semantics. Combined with Burst, it looks like the diagram below.

<div class="sy-ecs">
  <div class="sy-ecs-title">DOTS ECS scheduler — automatic parallelization via Component permission analysis</div>

  <div class="sy-ecs-comp">
    <div class="sy-ecs-comp-h">Component permission analysis (at compile time)</div>
    <div class="sy-ecs-comp-grid">
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">SpawnSystem</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> add/remove Entity</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">MoveJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> LocalTransform.Position</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-r">read</span> Velocity</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">RotateJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> LocalTransform.Rotation</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">RenderBoundsJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-r">read</span> LocalTransform.Position</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> RenderBounds</div>
      </div>
    </div>
    <div class="sy-ecs-note">scheduler reads read/write patterns and adds dependency edges automatically</div>
  </div>

  <div class="sy-ecs-tl">
    <div class="sy-ecs-tl-h">execution timeline (Frame N)</div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl sy-ecs-tlbl-main">Main</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-main" style="flex: 1">SpawnSystem</div>
        <div class="sy-ecs-blk sy-ecs-blk-sched" style="flex: 0.8">schedule jobs</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 2.2">— work-stealing —</div>
        <div class="sy-ecs-blk sy-ecs-blk-sync" style="flex: 1">SyncPoint</div>
        <div class="sy-ecs-blk sy-ecs-blk-main" style="flex: 1">RenderSystem</div>
      </div>
    </div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl">W1</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.8">idle</div>
        <div class="sy-ecs-blk sy-ecs-blk-w" style="flex: 1.5">MoveJob [Position write]</div>
        <div class="sy-ecs-blk sy-ecs-blk-r" style="flex: 1.5">RenderBoundsJob [Position read]</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.2">idle</div>
      </div>
    </div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl">W2</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.8">idle</div>
        <div class="sy-ecs-blk sy-ecs-blk-w" style="flex: 1.5">RotateJob [Rotation write]</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.5">idle (no Position dep)</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.2">idle</div>
      </div>
    </div>
    <div class="sy-ecs-tl-arrows">
      <span class="sy-ecs-arrow-h">↑ same time — different Components, so parallel without locks</span>
      <span class="sy-ecs-arrow-d">↑ Position read waits for MoveJob (automatic dependency)</span>
    </div>
  </div>

  <div class="sy-ecs-key">
    <strong>The programmer specifies neither locks nor dependencies.</strong> The ECS scheduler reads each job/system's Component permissions (<code>ref</code>=write, <code>in</code>=read) and serializes only read-after-write conflicts. Result: work touching different Components runs in parallel freely; touching the same Component gets automatic ordering.
  </div>

<style>
.sy-ecs { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-ecs-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-ecs-comp { padding: 12px 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; margin-bottom: 14px; }
.sy-ecs-comp-h { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; }
.sy-ecs-comp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.sy-ecs-comp-cell { padding: 8px 10px; background: #f7fafc; border-radius: 4px; border: 1px solid #e2e8f0; }
.sy-ecs-sys { font-weight: 700; font-size: 11.5px; color: #1a202c; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed #cbd5e0; }
.sy-ecs-perm { font-size: 10.5px; padding: 2px 0; color: #4a5568; font-family: monospace; }
.sy-ecs-r { display: inline-block; padding: 1px 5px; background: #c6f6d5; color: #22543d; border-radius: 2px; font-size: 9.5px; font-weight: 800; margin-right: 4px; }
.sy-ecs-w { display: inline-block; padding: 1px 5px; background: #fed7aa; color: #7b341e; border-radius: 2px; font-size: 9.5px; font-weight: 800; margin-right: 4px; }
.sy-ecs-note { margin-top: 10px; font-size: 11px; color: #2b6cb0; font-style: italic; text-align: center; }
.sy-ecs-tl { padding: 12px 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-ecs-tl-h { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; }
.sy-ecs-trow { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.sy-ecs-tlbl { flex: 0 0 50px; font-size: 11px; font-weight: 700; color: #2d3748; text-align: right; }
.sy-ecs-tlbl-main { color: #c53030; }
.sy-ecs-track { display: flex; flex: 1; height: 28px; border: 1px solid #e2e8f0; border-radius: 3px; overflow: hidden; }
.sy-ecs-blk { display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; padding: 0 4px; text-align: center; border-right: 1px solid rgba(0,0,0,0.06); }
.sy-ecs-blk:last-child { border-right: 0; }
.sy-ecs-blk-main { background: #fed7d7; color: #742a2a; }
.sy-ecs-blk-sched { background: #d6bcfa; color: #44337a; }
.sy-ecs-blk-sync { background: #fbd38d; color: #7b341e; }
.sy-ecs-blk-w { background: #fed7aa; color: #7b341e; }
.sy-ecs-blk-r { background: #c6f6d5; color: #22543d; }
.sy-ecs-blk-idle { background: #f7fafc; color: #a0aec0; font-weight: 500; font-style: italic; }
.sy-ecs-tl-arrows { margin-top: 10px; padding-top: 8px; border-top: 1px dashed #cbd5e0; display: flex; flex-direction: column; gap: 3px; }
.sy-ecs-arrow-h { font-size: 10.5px; color: #2f855a; font-weight: 600; }
.sy-ecs-arrow-d { font-size: 10.5px; color: #c05621; font-weight: 600; }
.sy-ecs-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-ecs-key strong { color: #2b6cb0; }
.sy-ecs-key code { background: #fff; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 11px; color: #2b6cb0; font-weight: 700; }

[data-mode="dark"] .sy-ecs { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-ecs-title { color: #e2e8f0; }
[data-mode="dark"] .sy-ecs-comp { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-comp-h { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-comp-cell { background: #1a202c; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-sys { color: #f7fafc; border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-ecs-perm { color: #cbd5e0; }
[data-mode="dark"] .sy-ecs-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-note { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-tl { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-tl-h { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-tlbl { color: #e2e8f0; }
[data-mode="dark"] .sy-ecs-tlbl-main { color: #feb2b2; }
[data-mode="dark"] .sy-ecs-track { border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.05); }
[data-mode="dark"] .sy-ecs-blk-main { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-ecs-blk-sched { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-ecs-blk-sync { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-blk-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-blk-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-blk-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-ecs-tl-arrows { border-top-color: #4a5568; }
[data-mode="dark"] .sy-ecs-arrow-h { color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-arrow-d { color: #fbd38d; }
[data-mode="dark"] .sy-ecs-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-ecs-key strong { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-key code { background: #2d3748; color: #90cdf4; }

@media (max-width: 768px) {
  .sy-ecs { padding: 14px 8px 12px; }
  .sy-ecs-title { font-size: 13px; }
  .sy-ecs-comp-grid { grid-template-columns: 1fr 1fr; gap: 5px; }
  .sy-ecs-comp-cell { padding: 6px 8px; }
  .sy-ecs-sys { font-size: 10.5px; }
  .sy-ecs-perm { font-size: 9.5px; }
  .sy-ecs-r, .sy-ecs-w { font-size: 8.5px; padding: 1px 4px; }
  .sy-ecs-tlbl { flex-basis: 36px; font-size: 9.5px; }
  .sy-ecs-track { height: 22px; }
  .sy-ecs-blk { font-size: 8.5px; }
  .sy-ecs-arrow-h, .sy-ecs-arrow-d { font-size: 9.5px; }
  .sy-ecs-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

The dependency where RenderBoundsJob waits for MoveJob to complete is **automatically inferred** by ECS without the developer specifying it. Both jobs touch `LocalTransform.Position`, MoveJob writes and RenderBoundsJob reads, so the ECS scheduler automatically adds the dependency edge.

#### One frame's memory flow — summary

Synchronization-related events Unity triggers within a single frame (16.67ms), in time order:

| Time | Location | What happens |
|------|----------|--------------|
| 0ms | Main | Input/MonoBehaviour Update — main thread only, no locks |
| 2ms | Main | Schedule jobs, build dependency graph |
| 2~10ms | Worker 1~N | Workers execute jobs in dependency order; NativeArray cache lines RFO-move to worker cores |
| 10ms | Main | `JobHandle.Complete()` or sync point — main also acts as a worker via work-stealing |
| 12ms | Render thread | submit command buffer to GPU (next section) |
| 16ms | GPU | present, next frame begins |

That covers Unity. Unreal has a similar philosophy but with stronger thread separation.

---

## Part 7: Unreal Engine Synchronization

Unreal has a more explicit **multi-thread model** than Unity. The engine itself is split into multiple named threads, and inter-thread communication is built almost entirely on lock-free queues.

### Four Named Threads

A typical Unreal game has these threads always running:

| Thread | Responsibility | OS thread |
|--------|----------------|-----------|
| **Game Thread** | Tick, gameplay logic, Blueprint, AI | main thread (Unity's main equivalent) |
| **Render Thread** | high-level render command generation (FRDG, RHI command authoring) | separate OS thread |
| **RHI Thread** | GPU API calls (D3D12/Vulkan/Metal/Mantle) | separate OS thread |
| **Audio Thread** | sound mixing, voice management | separate OS thread |
| **Worker Threads** | TaskGraph job execution | one per core |

The core idea is **each thread holds data only it touches, and inter-thread communication goes through explicit command queues**. Instead of locking, data ownership is bound firmly to a thread.

### Game Thread → Render Thread — one frame's flow

Unreal's Render Thread usually runs **one frame behind** the Game Thread (Epic's docs describe it as 0 or 1 frame behind — if Game finishes fast Render can catch up; if Render is heavy, Game blocks on sync next frame). This article describes the "one frame behind" case under normal load. When Game runs frame N's logic, Render builds frame N-1's render commands, and RHI submits frame N-2 to the GPU.

<div class="sy-upipe">
  <div class="sy-upipe-title">Unreal 4-thread pipeline — same moment, different frames</div>

  <div class="sy-upipe-grid">
    <div class="sy-upipe-corner">Thread ↓ / Frame →</div>
    <div class="sy-upipe-fh">Frame N</div>
    <div class="sy-upipe-fh">Frame N+1</div>
    <div class="sy-upipe-fh">Frame N+2</div>

    <div class="sy-upipe-th sy-upipe-th-game">Game Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active">N logic<br><span>Tick, AI, Physics, Blueprint</span></div>
    <div class="sy-upipe-cell">N+1 logic</div>
    <div class="sy-upipe-cell">N+2 logic</div>

    <div class="sy-upipe-th sy-upipe-th-render">Render Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-r">N-1 render<br><span>RDG build, FMeshBatch generation</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N render</div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N+1 render</div>

    <div class="sy-upipe-th sy-upipe-th-rhi">RHI Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-h">N-2 submit<br><span>D3D12/Vulkan/Metal API</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N-1 submit</div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N submit</div>

    <div class="sy-upipe-th sy-upipe-th-gpu">GPU</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-g">N-3 draw + present<br><span>actual pixels displayed</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-2 draw + present</div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-1 draw + present</div>
  </div>

  <div class="sy-upipe-flow">
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ ENQUEUE_RENDER_COMMAND</div>
      <div class="sy-upipe-fl-d">Game pushes data to Render (lock-free MPSC queue)</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ RHI command list</div>
      <div class="sy-upipe-fl-d">Render dispatches GPU commands to RHI</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ GPU submit</div>
      <div class="sy-upipe-fl-d">RHI submits to GPU, tracked by fence</div>
    </div>
    <div class="sy-upipe-fl sy-upipe-fl-back">
      <div class="sy-upipe-fl-h">← FRenderCommandFence</div>
      <div class="sy-upipe-fl-d">Only when Game needs to wait for Render (rare)</div>
    </div>
  </div>

  <div class="sy-upipe-key">
    <strong>Only one thread touches the same data at the same moment.</strong> While Game makes N, Render handles N-1 and RHI handles N-2, so almost no lock is needed. The tradeoff is +1 frame of input lag — the exact realization of one-frame pipelining from Part 9.
  </div>

<style>
.sy-upipe { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-upipe-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-upipe-grid { display: grid; grid-template-columns: 120px 1fr 1fr 1fr; gap: 4px; margin-bottom: 16px; }
.sy-upipe-corner { font-size: 10.5px; color: #718096; font-style: italic; padding: 8px 4px; }
.sy-upipe-fh { font-size: 11.5px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; background: #edf2f7; border-radius: 3px; }
.sy-upipe-th { font-size: 11.5px; font-weight: 700; color: #fff; padding: 12px 8px; border-radius: 3px; display: flex; align-items: center; justify-content: center; text-align: center; }
.sy-upipe-th-game   { background: #c53030; }
.sy-upipe-th-render { background: #c05621; }
.sy-upipe-th-rhi    { background: #2b6cb0; }
.sy-upipe-th-gpu    { background: #553c9a; }
.sy-upipe-cell { padding: 10px 8px; font-size: 11.5px; font-weight: 700; background: #f7fafc; border-radius: 3px; color: #4a5568; text-align: center; opacity: 0.55; }
.sy-upipe-cell span { display: block; font-size: 10px; font-weight: 500; margin-top: 3px; opacity: 0.85; }
.sy-upipe-cell-active { opacity: 1; box-shadow: 0 0 0 2px rgba(43, 108, 176, 0.25); }
.sy-upipe-cell-r { background: #fed7aa; color: #7b341e; }
.sy-upipe-cell-h { background: #bee3f8; color: #2c5282; }
.sy-upipe-cell-g { background: #d6bcfa; color: #44337a; }
.sy-upipe-grid > .sy-upipe-cell:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #fed7d7; color: #742a2a; }
.sy-upipe-grid > .sy-upipe-cell.sy-upipe-cell-active:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #fc8181; color: #742a2a; }

.sy-upipe-flow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 12px 10px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-upipe-fl { padding: 8px 10px; background: #ebf8ff; border-radius: 4px; border-left: 3px solid #2b6cb0; }
.sy-upipe-fl-back { background: #fff5f5; border-left-color: #c53030; }
.sy-upipe-fl-h { font-size: 11px; font-weight: 700; color: #2b6cb0; margin-bottom: 4px; }
.sy-upipe-fl-back .sy-upipe-fl-h { color: #c53030; }
.sy-upipe-fl-d { font-size: 10.5px; color: #4a5568; line-height: 1.4; }
.sy-upipe-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-upipe-key strong { color: #2b6cb0; }

[data-mode="dark"] .sy-upipe { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-upipe-title { color: #e2e8f0; }
[data-mode="dark"] .sy-upipe-corner { color: #a0aec0; }
[data-mode="dark"] .sy-upipe-fh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-upipe-cell { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-upipe-cell-r { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-upipe-cell-h { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-upipe-cell-g { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-upipe-grid > .sy-upipe-cell:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-upipe-grid > .sy-upipe-cell.sy-upipe-cell-active:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #9b2c2c; color: #feb2b2; }
[data-mode="dark"] .sy-upipe-flow { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-upipe-fl { background: #1a365d; }
[data-mode="dark"] .sy-upipe-fl-back { background: #742a2a; border-left-color: #fc8181; }
[data-mode="dark"] .sy-upipe-fl-h { color: #90cdf4; }
[data-mode="dark"] .sy-upipe-fl-back .sy-upipe-fl-h { color: #feb2b2; }
[data-mode="dark"] .sy-upipe-fl-d { color: #cbd5e0; }
[data-mode="dark"] .sy-upipe-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-upipe-key strong { color: #90cdf4; }

@media (max-width: 768px) {
  .sy-upipe { padding: 14px 8px 12px; }
  .sy-upipe-title { font-size: 13px; }
  .sy-upipe-grid { grid-template-columns: 80px 1fr 1fr 1fr; gap: 3px; }
  .sy-upipe-corner { font-size: 9px; }
  .sy-upipe-fh { font-size: 10px; padding: 6px 2px; }
  .sy-upipe-th { font-size: 10px; padding: 8px 4px; }
  .sy-upipe-cell { font-size: 10px; padding: 6px 4px; }
  .sy-upipe-cell span { font-size: 8.5px; }
  .sy-upipe-flow { grid-template-columns: 1fr 1fr; gap: 6px; }
  .sy-upipe-fl { padding: 6px 8px; }
  .sy-upipe-fl-h { font-size: 10px; }
  .sy-upipe-fl-d { font-size: 9.5px; }
  .sy-upipe-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

Thanks to this pipelining, almost no lock is needed. Only one thread touches the same data at any moment.

### TaskGraph — Unreal's Job System

`FTaskGraphInterface` is the Unreal equivalent of Unity Job System.

```cpp
FGraphEventRef MyTask = FFunctionGraphTask::CreateAndDispatchWhenReady(
    [Data]() {
        // executes on a worker thread
        ProcessData(Data);
    },
    TStatId(),
    nullptr,                      /* dependency prerequisite */
    ENamedThreads::AnyThread      /* which thread to run on */
);

/* wait for the result later */
FTaskGraphInterface::Get().WaitUntilTaskCompletes(MyTask);
```

Features:

- **Named thread selection**: dispatch to `GameThread`, `RenderThread`, `RHIThread`, or `AnyThread`
- **Dependency edge expression**: pass a prerequisite array to start after they complete
- **Automatic work-stealing**: AnyThread is picked up by the least busy worker
- **Hierarchical tasks**: spawn child tasks from within a task

### ENQUEUE_RENDER_COMMAND — a command queue with no visible lock

The most common macro for passing data from Game Thread to Render Thread.

```cpp
FVector NewPos = Actor->GetActorLocation();
FRHICommandListImmediate& RHICmdList = ...;

ENQUEUE_RENDER_COMMAND(UpdateActorPos)(
    [NewPos](FRHICommandListImmediate& RHICmdList) {
        /* this lambda executes on the Render Thread */
        UpdateConstantBuffer(RHICmdList, NewPos);
    });
```

What this macro means: **wrap the lambda into a command object, enqueue it on the Render Thread's command queue, and the Render Thread pulls in FIFO order to execute.** Epic's docs don't explicitly guarantee the internal queue is lock-free MPSC (a version-dependent implementation detail), and the macro's contract is just *"ordered + execute on Render Thread"*. Conceptually it's a multi-producer (workers can enqueue too) single-consumer (Render Thread only pops) pattern, which is generally a natural fit for lock-free MPSC.

> **Hold on, let's settle this.** How does a lock-free MPSC queue work without locks?
>
> The key is the asymmetry: **producers append to the queue tail via atomic CAS or atomic exchange**, and **the consumer is single-threaded so no synchronization is needed**. The most famous design is the **Vyukov MPSC queue** — one atomic exchange grabs the prev tail, then updates prev tail's next pointer to the new node. No retry loops, almost zero contention.

The Vyukov MPSC core looks like this.

```cpp
struct Node { std::atomic<Node*> next; T payload; };
std::atomic<Node*> tail;

void push(Node* node) {
    node->next.store(nullptr, std::memory_order_relaxed);
    Node* prev = tail.exchange(node, std::memory_order_acq_rel);
    prev->next.store(node, std::memory_order_release);
}
/* pop is single-consumer, almost no atomics needed */
```

This pattern underlies nearly every inter-thread communication in Unreal. That's why ENQUEUE_RENDER_COMMAND, called hundreds of times per frame, has no lock contention.

### FRenderCommandFence — when Game must wait for Render

Sometimes Game Thread needs to know "the commands sent to Render Thread really finished." For example, to destroy a GPU resource safely, you must ensure the Render Thread no longer touches it.

```cpp
FRenderCommandFence Fence;
Fence.BeginFence();      /* mark all render commands up to this point */
Fence.Wait();            /* block until marked commands all finish */
```

`BeginFence` enqueues a fence marker into the Render Thread's queue. `Wait` makes Game Thread sleep on an FEvent until the fence is processed. This is essentially the only explicit synchronization point between Game ↔ Render.

### FCriticalSection / FRWLock — explicit locks

Of course explicit locks are sometimes needed. Unreal provides:

- **`FCriticalSection`**: abstraction over Windows `CRITICAL_SECTION` (pthread_mutex on others). Standard mutex.
- **`FRWLock`**: Reader-Writer lock. On macOS mapped to pthread_rwlock instead of `os_unfair_lock`.
- **`FScopeLock`**: RAII helper (equivalent to `std::lock_guard`).
- **`TQueue<T, EQueueMode::Spsc>`**: lock-free single-producer single-consumer queue.
- **`TQueue<T, EQueueMode::Mpsc>`**: lock-free multi-producer single-consumer.

Engine code itself prefers lock-free queues and TaskGraph dependencies; `FCriticalSection` appears occasionally in gameplay code (on top of the gameplay framework).

### Unity vs Unreal

| Item | Unity | Unreal |
|------|-------|--------|
| Main thread | one, all APIs go through it | Game Thread, gameplay only |
| Render separation | yes (Render Thread, fewer explicit APIs) | strong (Render Thread + RHI Thread + RDG) |
| Job abstraction | Job System + DOTS | TaskGraph + Async Tasks |
| Compile-time race detection | NativeContainer + AtomicSafetyHandle | none (runtime asserts) |
| Lock-avoidance philosophy | dependency graph + main thread affinity | named threads + lock-free queues |
| ECS | DOTS / Entities (official) | Mass Entity (5.x), various unofficial |

Unity goes for **making dependencies expressible safely and validating at schedule time (in Editor/Development)** (safety on by default). Unreal goes for **binding data to threads and communicating through command queues** (performance by convention). Neither locks much, but the reasons and verification timing differ.

---

## Part 8: Game Engine Patterns That Avoid Locks

Since locks are barely used inside engines, patterns that bypass them have evolved. Patterns you can use directly in game code:

### Double Buffering

The simplest and most common. **Alternate between two buffers**. But to use it safely you need **a guarantee that read and write don't overlap in time** — usually a frame boundary or fence.

```cpp
/* Assumption: GameTick and PhysicsTick are called sequentially at frame boundary.
   Within one frame, the worker starts the next write only after read finishes. */

struct PhysicsState {
    std::vector<Transform> transforms;
};

PhysicsState buffers[2];
std::atomic<int> readIdx{0};   /* main reads */

/* Frame N — Worker picks the next buffer to write (read-finished guarantee required) */
void PhysicsTick() {
    int w = 1 - readIdx.load(std::memory_order_acquire);
    UpdatePhysics(buffers[w]);
    readIdx.store(w, std::memory_order_release);  /* publish */
}

/* Frame N — Main reads the latest published buffer */
void GameTick() {
    int r = readIdx.load(std::memory_order_acquire);
    Render(buffers[r]);
}
```

No lock anywhere. A single atomic swaps the "currently readable buffer index." Memory cost is 2× the buffer, but contention is zero. **However, this code isn't safe if writer and reader run independent asynchronous loops.** Right after publish, while reader still reads that buffer, if worker tries to write a *different* buffer in the next tick, the index could collide. Game engines typically design **sync at frame boundaries** so read and write phases are time-separated — only with that assumption is double buffer safe. Otherwise you need triple buffer or explicit sequence handoff.

Where this pattern appears in game engines:

- **Physics → Render**: swap buffer at frame boundary, render thread draws N while physics prepares N+1
- **AI tick**: compute next-frame behavior, swap at frame boundary
- **Network input**: collect packets during a frame, swap at frame boundary

### Triple Buffering

When writer and reader run independent loops and read/write can overlap in time, double buffer isn't enough. Three buffers handle it — "currently drawing," "just made," "next to write." Used in OS graphics stack's swap chain, V-sync queue, game engine ring buffers, etc. With three buffers, the writer always finds a slot the reader isn't using.

### Lock-free SPSC Ring Buffer

A single-producer single-consumer queue is implementable without locks using just two atomics.

```cpp
template<typename T, size_t N>
struct SpscRing {
    T buf[N];
    alignas(64) std::atomic<size_t> head{0};  /* producer writes */
    alignas(64) std::atomic<size_t> tail{0};  /* consumer writes */

    bool push(const T& v) {
        size_t h = head.load(std::memory_order_relaxed);
        size_t next = (h + 1) % N;
        if (next == tail.load(std::memory_order_acquire))
            return false;  /* full */
        buf[h] = v;
        head.store(next, std::memory_order_release);
        return true;
    }

    bool pop(T& out) {
        size_t t = tail.load(std::memory_order_relaxed);
        if (t == head.load(std::memory_order_acquire))
            return false;  /* empty */
        out = buf[t];
        tail.store((t + 1) % N, std::memory_order_release);
        return true;
    }
};
```

`alignas(64)` keeps head and tail on different cache lines — preventing false sharing. Even on different cores, producer and consumer have no contention.

This structure underlies game ↔ render command queues, audio sample buffers, log queues, and almost any 1:1 communication.

### Per-thread accumulation

When multiple threads must increment a counter, false sharing is a common trap. The fix is **each thread holds its own slot, summed at the end**.

```cpp
struct alignas(64) Slot { int64_t v = 0; };
Slot per_thread[NUM_THREADS];

/* each thread */
per_thread[tid].v++;        /* plain store, not atomic */

/* summation (single thread) */
int64_t total = 0;
for (auto& s : per_thread) total += s.v;
```

Thanks to `alignas(64)`, each slot owns its own cache line. A million increments are 50–100× faster than a false-sharing lock-free counter.

### Frame-locked sync — explicit sync points

Instead of taking locks constantly per job, **sync only at frame boundaries**. Within a frame, one thread touches its own data, and main integrates all thread results at frame end.

Naughty Dog's fiber system (see Part 9) is the extreme of this idea — split a frame into thousands of fibers, but advance to the next frame only at a sync point where all fibers complete.

### Summary: the lock-avoiding mindset

Common traits of patterns used instead of locks inside engines:

1. **Bind data to a thread** — when one thread owns its data, no lock needed
2. **Explicit communication channels** — lock-free queues for inter-thread data transfer
3. **Time separation** — double/triple buffer to separate read and write in time
4. **Spatial separation** — per-thread slots to avoid false sharing
5. **Sync rarely** — concentrate cost at natural sync points like frame boundaries

Locks themselves aren't bad — **lock contention and cache bouncing** are expensive, and the patterns above naturally avoid both.

---

## Part 9: The Cost of Locks — Measuring

Measure, don't guess. Tools for confirming whether a lock is really expensive and where the cost comes from.

### Linux — perf and perf c2c

```bash
# syscall (futex_wait/wake) frequency
$ perf stat -e syscalls:sys_enter_futex ./game

# cache miss, hitm (modified line hit on another core)
$ perf stat -e mem_load_uops_l3_hit_retired.xsnp_hitm ./game

# false sharing detection (Cache-to-Cache analysis)
$ perf c2c record ./game
$ perf c2c report
```

`perf c2c` is the standard tool for false sharing diagnosis. Frequent HITM (Hit Modified) events on the same cache line make that line a prime suspect.

### Windows — Concurrency Visualizer, ETW

Visual Studio's Concurrency Visualizer shows per-thread CPU usage, lock contention blocks, and I/O waits. WPA's "Wait Analysis" page gives the same info in more detail.

```powershell
# Track lock contention
wpr -start LockHeldTimes -filemode
# (run game)
wpr -stop trace.etl
```

### macOS — Instruments System Trace

The "Thread State" track in the System Trace template visualizes thread blocking. "Pthread mutex contention" markers show separately, telling you which mutex is contended.

```bash
# Or measure on the fly via dtrace
$ sudo dtrace -n 'pid$target:libsystem_pthread:_pthread_mutex_lock:entry {@[ustack()]=count();}' -p <pid>
```

### Cross-platform — Tracy Profiler

Tracy provides macros that directly track mutex usage.

```cpp
#include "Tracy.hpp"
#include "TracyLock.hpp"

TracyLockable(std::mutex, m);

void DoWork() {
    std::lock_guard<LockableBase(std::mutex)> lk(m);
    ZoneScoped;
    /* ... */
}
```

Lock/unlock times and contention durations of mutexes wrapped with `LockableBase` are visualized on Tracy's timeline. You can immediately see which mutex is hot.

### Built-in engine profilers

- **Unity Profiler**: Job System tab shows worker thread utilization and dependency wait time
- **Unreal Insights**: visualizes TaskGraph, fence wait time, ENQUEUE_RENDER_COMMAND call frequency
- **PIX (Xbox/PC)**: shows D3D12 fence wait and RHI thread blocking

### One-line diagnosis

"My game is slow — is the lock the cause?" The one-line answer is **"if spinning or waiting shows up in the thread state visualization, that's the cost."** Without even looking at code, looking only at the thread state graph tells you immediately whether a lock is really the problem.

---

## Conclusion

Pulling together everything from this part:

**The nature of race condition**:
- `counter++` decomposes into load/modify/store, breaking atomicity
- data race (undefined behavior in C++/Rust) and race condition (execution-order dependent) are different concepts
- Locks guarantee atomicity, visibility, and ordering together

**The lock family**:
- Mutex, Spinlock, Semaphore, RWLock, CondVar, Monitor, Barrier, Latch
- Just different policies over the same atomic foundation

**Lock construction**:
- Peterson works in theory, real CPUs need memory barriers
- Hardware atomics: x86 LOCK CMPXCHG, ARM LDXR/STXR
- Spin vs Sleep compares critical section length against context-switch cost

**OS primitives**:
- Linux futex (2002), Windows SRWLock (Vista, 2007), macOS os_unfair_lock (2016)
- All share the same idea: fast path in user-space atomic, slow path only enters kernel
- macOS os_unfair_lock encodes owner thread ID for QoS donation

**Hardware mechanism**:
- CPU cache: L1 (4 cycle) ~ L3 (50 cycle) ~ DRAM (300 cycle)
- MESI: a cache line can be in Modified state on only one core
- Atomicity comes from cache coherence serializing RFO
- Cache line bouncing: intra-socket 30–50ns, cross-socket 150–300ns
- False sharing: different variables on the same line cause unintended contention

**Unity synchronization**:
- Main thread model: all Unity APIs main only
- Job System: JobHandle dependency graph, batch 64, work-stealing
- NativeContainer + AtomicSafetyHandle: schedule-time runtime race check (Editor/Development only)
- Burst: ordinary reads/writes are plain load/store; only `Interlocked.*` calls emit hardware atomics
- DOTS: automatically analyzes Component read/write, scheduler adds dependency edges at schedule time

**Unreal synchronization**:
- Game / Render / RHI / Audio Thread separation
- TaskGraph + Named Thread + dependency
- ENQUEUE_RENDER_COMMAND works as a lock-free MPSC queue (conceptually)
- FRenderCommandFence is the only explicit Game ↔ Render sync point

**Lock-avoiding patterns**:
- Double/Triple buffer, lock-free SPSC ring, per-thread slot
- Frame-locked sync concentrates cost at one point

In the next part, **Part 11 — Deadlock and Starvation**, we cover cases where locks work fine but the program still hangs — circular waits between two locks, priority inversion, livelock. After that, Part 12 covers memory model and atomic ordering, and Part 13 goes deeper into lock-free data structures and Unity Job System internals.

Stage 2's original question can now be answered.

> **Why does a program with two threads writing the same variable die only sometimes?**

- "Write" decomposes into 3 steps (load/modify/store), so another thread can interleave anywhere in the middle
- "Interleaving" is decided by the scheduler at arbitrary moments, so "sometimes"
- "To prevent it," we need the lock abstraction built on cache coherence and atomic instructions

---

## References

### Textbooks

- Herlihy, M., Shavit, N. — *The Art of Multiprocessor Programming*, 2nd ed., Morgan Kaufmann, 2020 — Ch.2~7 (Mutex algorithms, lock-free, hardware foundations) — the canonical text on multithread synchronization
- Silberschatz, A., Galvin, P. B., Gagne, G. — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.6 (Synchronization Tools), Ch.7 (Synchronization Examples)
- Tanenbaum, A. S., Bos, H. — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.3 (Interprocess Communication)
- Russinovich, M., Solomon, D., Ionescu, A. — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.8 (System Mechanisms, SRWLock / pushlock internals)
- Singh, A. — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.10 (Mach IPC, locks)
- Drepper, U. — *What Every Programmer Should Know About Memory*, Red Hat, 2007 — the definitive primer on cache coherence — [people.freebsd.org/~lstewart/articles/cpumemory.pdf](https://people.freebsd.org/~lstewart/articles/cpumemory.pdf)
- Gregory, J. — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8.6~8.7 (Multithreading, Job systems)
- McKenney, P. E. — *Is Parallel Programming Hard, And, If So, What Can You Do About It?*, 2024 ed. — [kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) — free book by RCU's author

### Papers

- Peterson, G. L. — "Myths About the Mutual Exclusion Problem", *Information Processing Letters*, 1981 — Peterson's original paper
- Dijkstra, E. W. — "Cooperating Sequential Processes", *Programming Languages*, 1968 — introduction of the semaphore
- Lamport, L. — "A New Solution of Dijkstra's Concurrent Programming Problem", *CACM*, 1974 — bakery algorithm
- Lamport, L. — "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs", *IEEE TC*, 1979 — definition of sequential consistency
- Franke, H., Russell, R., Kirkwood, M. — "Fuss, Futexes and Furwocks: Fast Userlevel Locking in Linux", *OLS 2002* — futex introduction — [kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf](https://www.kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf)
- Drepper, U. — "Futexes Are Tricky", Red Hat, 2011 — pitfalls of futex implementation — [akkadia.org/drepper/futex.pdf](https://www.akkadia.org/drepper/futex.pdf)
- Sweeney, T. et al. — "Concurrent Programming in Unreal Engine" (GDC, EpicGames Dev) — TaskGraph design
- Boehm, H.-J. — "Threads Cannot Be Implemented as a Library", *PLDI 2005* — motivation for C++ memory model
- Adve, S. V., Gharachorloo, K. — "Shared Memory Consistency Models: A Tutorial", *IEEE Computer*, 1996 — memory model comparison

### Official documentation

- Linux man pages — `futex(2)`, `futex(7)`, `pthread_mutex_lock(3)`, `pthread_rwlock_rdlock(3)` — [man7.org/linux/man-pages/man2/futex.2.html](https://man7.org/linux/man-pages/man2/futex.2.html)
- Linux Kernel Documentation — `Documentation/locking/futex2.rst`, `mutex-design.rst`, `lockdep-design.rst`
- Microsoft Docs — *Slim Reader/Writer (SRW) Locks*, *Critical Section Objects* — [learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks](https://learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks)
- Apple Developer — *Threading Programming Guide*, `os_unfair_lock(3)` — [developer.apple.com/documentation/os/os_unfair_lock](https://developer.apple.com/documentation/os/os_unfair_lock)
- Intel — *Intel 64 and IA-32 Architectures Software Developer's Manual*, Vol. 3A — Ch.8 (Multiple-Processor Management), LOCK prefix
- ARM — *ARM Architecture Reference Manual ARMv8-A*, B2 (Memory Model), C6 (Load-Acquire / Store-Release)

### Unity official

- Unity Manual — *C# Job System* — [docs.unity3d.com/Manual/JobSystem.html](https://docs.unity3d.com/Manual/JobSystem.html)
- Unity Manual — *Native Containers* — [docs.unity3d.com/Manual/JobSystemNativeContainer.html](https://docs.unity3d.com/Manual/JobSystemNativeContainer.html)
- Unity Manual — *Burst Compiler* — [docs.unity3d.com/Packages/com.unity.burst@latest](https://docs.unity3d.com/Packages/com.unity.burst@latest)
- Unity Manual — *Entities (DOTS)* — [docs.unity3d.com/Packages/com.unity.entities@latest](https://docs.unity3d.com/Packages/com.unity.entities@latest)
- Joachim Ante — *C# Job System and ECS — Unite LA 2018* — Job System design talk
- Lucas Meijer — *On DOTS: Entity Component System — Unity Blog*, 2019

### Unreal official

- Epic Games — *Threading in Unreal Engine* — [dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine)
- Epic Games — *Task Graph System* — [dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Epic Games — *Rendering and the Game Thread* — explanation of RDG and ENQUEUE_RENDER_COMMAND
- Tim Sweeney — *The Next Mainstream Programming Language*, POPL 2006 — Unreal's multithreading vision

### Game development / GDC

- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — fiber-based sync — [gdcvault.com/play/1022186](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungie's lock-free design
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICE's Job system
- Reinders, J., Roberts, B. — *Multithreading for Visual Effects*, A K Peters, 2014 — VFX engine lock-free patterns
- Vyukov, D. — *Lock-Free / 1024cores* — Vyukov MPSC, scalability resources — [1024cores.net](https://www.1024cores.net/)

### Blogs / articles

- Preshing, J. — *Preshing on Programming* — atomic, memory ordering series — [preshing.com](https://preshing.com/)
- Howells, D. et al. — *Linux Kernel Memory Barriers (`memory-barriers.txt`)* — official kernel memory model guide
- Chen, R. — *The Old New Thing* — Windows critical section/SRWLock retrospectives
- Giesen, F. — *Reading List on Multithreading* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Oakley, H. — *The Eclectic Light Company* — macOS os_unfair_lock, QoS observations
- Bonzini, P. — "QEMU and lock-free RCU" — practical RCU application

### Tools

- Linux: `perf c2c`, `perf lock`, `bpftrace`, `lockstat`
- Windows: Concurrency Visualizer (VS), WPA Wait Analysis, PIX (for games)
- macOS: Instruments System Trace, `dtrace`, `sample`
- Cross-platform: Tracy Profiler (LockableBase), Intel VTune, AMD μProf
- ThreadSanitizer (TSan): GCC/Clang's static & dynamic data race detector









<div class="sy-guide">
  <div class="sy-guide-h">
    <span class="sy-guide-icon">⛟</span>
    Reading Guide
  </div>
  <div class="sy-guide-body">
    <p>This is a long article. You don't have to read it in one sitting.</p>
    <ul class="sy-guide-list">
      <li><strong>First time through</strong> — Part 1 (race condition) → Part 2 (lock family) → Part 8 (patterns that avoid locks) gives you the whole picture</li>
      <li><strong>For Stage 2's central answer — "why only sometimes"</strong> — go all the way to Part 5 (hardware and MESI)</li>
      <li><strong>If you want the engine internals</strong> — Part 6 (Unity) and Part 7 (Unreal) are the main course</li>
      <li><strong>OS implementation when you need it</strong> — Part 3 (how locks are built), Part 4 (futex/SRWLock/os_unfair_lock) work well as references</li>
    </ul>
    <p class="sy-guide-note">The two deepest sections — MESI state transitions and Burst's compile pipeline — are collapsed. Expand them only when you need them.</p>
  </div>

<style>
.sy-guide { margin: 22px 0; padding: 16px 18px 14px; border: 1px solid #cbd5e0; border-left: 4px solid #2b6cb0; border-radius: 6px; background: #ebf8ff; font-size: 13px; line-height: 1.55; }
.sy-guide-h { font-size: 13.5px; font-weight: 800; color: #2c5282; margin-bottom: 8px; letter-spacing: 0.01em; display: flex; align-items: center; gap: 8px; }
.sy-guide-icon { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: #2b6cb0; color: #fff; border-radius: 50%; font-size: 12px; font-weight: 700; }
.sy-guide-body p { margin: 4px 0 8px; color: #2c5282; }
.sy-guide-list { margin: 6px 0 6px 0; padding-left: 18px; }
.sy-guide-list li { padding: 3px 0; color: #2c5282; font-size: 12.5px; }
.sy-guide-list li strong { color: #1a365d; }
.sy-guide-note { font-size: 11.5px !important; color: #4a5568 !important; font-style: italic; margin-top: 10px !important; padding-top: 8px; border-top: 1px dashed #bee3f8; }

[data-mode="dark"] .sy-guide { background: #1a365d; border-color: #4a5568; border-left-color: #4299e1; }
[data-mode="dark"] .sy-guide-h { color: #bee3f8; }
[data-mode="dark"] .sy-guide-icon { background: #4299e1; color: #1a202c; }
[data-mode="dark"] .sy-guide-body p { color: #bee3f8; }
[data-mode="dark"] .sy-guide-list li { color: #bee3f8; }
[data-mode="dark"] .sy-guide-list li strong { color: #90cdf4; }
[data-mode="dark"] .sy-guide-note { color: #a0aec0 !important; border-top-color: #2c5282; }

@media (max-width: 768px) {
  .sy-guide { padding: 12px 12px 10px; font-size: 11.5px; }
  .sy-guide-h { font-size: 12px; }
  .sy-guide-list { padding-left: 14px; }
  .sy-guide-list li { font-size: 11px; }
  .sy-guide-note { font-size: 10.5px !important; }
}
</style>
</div>

---
