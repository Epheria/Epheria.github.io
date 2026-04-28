---
title: "CS Roadmap Part 8 — Processes and Threads: How the OS Abstracts Execution Units"
lang: en
date: 2026-04-26 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, process, thread, pcb, tcb, fork, pthreads, scheduling, game-engine]
toc: true
toc_sticky: true
math: true
difficulty: intermediate
prerequisites:
  - /posts/OSArchitecture/
  - /posts/MemoryManagement/
tldr:
  - A process is "an isolated address space plus a bundle of resources," and a thread is "a flow of execution inside a process." Threads share code, heap, and globals but keep the stack and registers private
  - Unix's fork() clones the process and is then overwritten by exec() in two steps, while Windows' CreateProcess() builds a new one in one shot. The clone looks expensive, but Copy-on-Write makes it actually fast
  - Thread models split into 1:1 (Linux NPTL, Windows), N:1 (green threads), M:N (Go goroutines, Erlang) — each trades performance against implementation complexity differently
  - A context switch doesn't just save/restore registers; it also causes TLB flushes and cache pollution. Modern game engines therefore move toward "break work into Jobs/TaskGraph/Fibers and distribute over cores" rather than "spawn more threads"
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: From the Map to the Body

The [previous post](/posts/OSArchitecture/) surveyed the lineage and skeleton of the three operating systems: Linux monolithic, Windows NT hybrid, macOS XNU a Mach + BSD dual structure. If that was the **map**, this post is the **body of the journey**.

Let's bring Stage 2's key question back.

> **"When two threads use the same variable, why does the program crash only sometimes?"**

To answer this, we first need to know **"what a thread is"** precisely. And to understand threads, we need to first understand their parent concept, the **process**. The distinction between processes and threads, how the two share and separate memory, and how the OS abstracts all of this — these are the starting points of every concurrency problem.

What we cover in this post:

- **Processes**: PCBs and address-space layouts. Linux's `task_struct`, Windows' `EPROCESS`, macOS's `proc`/`task`
- **Process creation**: Unix's two-step `fork()`+`exec()` model, Windows' single-call `CreateProcess()`, and Copy-on-Write
- **Threads**: why processes alone aren't enough, TCBs, shared vs. private regions, TLS
- **Thread mapping models**: 1:1, N:1, M:N — why Go's goroutines are so cheap
- **Context switching**: the real cost of registers, TLBs, and caches
- **Game engine execution models**: Unity's main thread, Unreal's TaskGraph, Naughty Dog's fibers

We keep the game-dev lens throughout, but this post carries more **foundational theory** than previous ones. The next post (scheduling) and the one after (synchronization) are built on top of it.

---

## Part 1: Processes — The Execution Unit the OS Sees

### What Is a Process?

Start with the textbook definition. A **process** is a **program in execution**. The `.exe` file on disk or the Mach-O binary is a **program**; the instance of it loaded into memory and running on the CPU is a **process**.

A process owns:

1. **A unique address space** — memory isolated from other processes
2. **Execution state** — CPU register values, program counter
3. **An open-files table** — the list of file descriptors currently in use
4. **Ownership info** — UID, GID, permissions
5. **Parent-child relationships** — who created whom (the process tree)

The OS manages all of this via a single **struct**. That's the **PCB (Process Control Block)**, also called the process descriptor.

### The PCB in Practice — Per-OS Structs

**Linux — `task_struct`**

In the Linux kernel, processes (and threads) are represented by `struct task_struct`. It's defined in `include/linux/sched.h` and is a huge struct with **hundreds of fields**.

```c
/* Linux kernel task_struct (kernel 6.x, heavily simplified) */
struct task_struct {
    /* State */
    unsigned int           __state;          /* TASK_RUNNING etc. */

    /* Identifiers */
    pid_t                  pid;              /* process id */
    pid_t                  tgid;             /* thread group id */
    struct task_struct    *parent;           /* parent process */
    struct list_head       children;         /* child list */

    /* Memory */
    struct mm_struct      *mm;               /* address space */

    /* Files */
    struct files_struct   *files;            /* open files table */

    /* Scheduling */
    int                    prio;
    struct sched_entity    se;               /* CFS scheduling entity */

    /* signals, resource limits, and hundreds more... */
};
```

The real struct is over 700 lines. Crucially, in Linux **a process and a thread share the same struct**. We come back to this peculiarity later.

**Windows — `EPROCESS`, `KPROCESS`**

Windows NT splits across two layers:
- `KPROCESS` (Kernel Process Block) — minimal scheduling-related info
- `EPROCESS` (Executive Process Block) — wraps `KPROCESS` and adds more

```c
/* Conceptual pseudocode — see WinDbg or leaked NT sources for the real thing */
typedef struct _EPROCESS {
    KPROCESS Pcb;                    /* kernel process block (inherited) */
    HANDLE UniqueProcessId;          /* PID */
    LIST_ENTRY ActiveProcessLinks;   /* global process list */
    PVOID SectionBaseAddress;        /* image load address */
    PVOID Token;                     /* security token */
    /* ... */
} EPROCESS;
```

**macOS — `proc` + `task`**

macOS's dual structure shows up here too. The **BSD layer** holds the classic Unix `struct proc`; the **Mach layer** holds `struct task`.

```c
/* BSD side — bsd/sys/proc_internal.h */
struct proc {
    pid_t                  p_pid;           /* POSIX process ID */
    struct proc           *p_pptr;          /* parent */
    struct task           *task;            /* link to Mach task */
    /* ... */
};

/* Mach side — osfmk/kern/task.h */
struct task {
    queue_head_t           threads;         /* threads belonging to this task */
    vm_map_t               map;             /* address space */
    ipc_space_t            itk_space;       /* Mach port space */
    /* ... */
};
```

So when `fork()` creates a process on macOS, **a BSD `proc` and a Mach `task` are created as a pair**. Unix tools (`ps`, `top`) look at the `proc`; Mach-based tools (`lldb`, `Instruments`) look at the `task`.

### Process Address-Space Layout

How is a process's memory **laid out**? Here's the classic Unix/Linux 32-bit layout.

<div class="pt-addr-container">
<svg viewBox="0 0 700 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process address space layout">
  <text x="350" y="28" text-anchor="middle" class="pa-title">Process address space (conceptual)</text>

  <g class="pa-layer pa-kernel">
    <rect x="180" y="55" width="340" height="50" rx="4"/>
    <text x="350" y="78" text-anchor="middle" class="pa-label">Kernel Space</text>
    <text x="350" y="95" text-anchor="middle" class="pa-sub">(no direct access from user processes)</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="130" x2="600" y2="105" class="pa-arrow"/>
    <text x="615" y="122" class="pa-addr">high address</text>
    <text x="615" y="138" class="pa-addr">0xFFFFFFFF</text>
  </g>

  <g class="pa-layer pa-stack">
    <rect x="180" y="120" width="340" height="70" rx="4"/>
    <text x="350" y="145" text-anchor="middle" class="pa-label">Stack</text>
    <text x="350" y="165" text-anchor="middle" class="pa-sub">call frames, locals</text>
    <text x="350" y="180" text-anchor="middle" class="pa-sub pa-emph">↓ grows downward</text>
  </g>

  <g class="pa-layer pa-gap">
    <rect x="180" y="200" width="340" height="120" rx="4"/>
    <text x="350" y="235" text-anchor="middle" class="pa-label pa-gray">Unused region</text>
    <text x="350" y="258" text-anchor="middle" class="pa-sub pa-gray">room for the stack to grow</text>
    <text x="350" y="280" text-anchor="middle" class="pa-sub pa-gray">mmap'd shared libraries sit here</text>
    <text x="350" y="300" text-anchor="middle" class="pa-sub pa-gray">(libc, libdl, heap extensions, etc.)</text>
  </g>

  <g class="pa-layer pa-heap">
    <rect x="180" y="330" width="340" height="70" rx="4"/>
    <text x="350" y="355" text-anchor="middle" class="pa-label">Heap</text>
    <text x="350" y="375" text-anchor="middle" class="pa-sub">allocations via malloc / new</text>
    <text x="350" y="390" text-anchor="middle" class="pa-sub pa-emph">↑ grows upward (brk / sbrk)</text>
  </g>

  <g class="pa-layer pa-bss">
    <rect x="180" y="410" width="340" height="40" rx="4"/>
    <text x="350" y="432" text-anchor="middle" class="pa-label">BSS (Uninitialized Data)</text>
    <text x="350" y="445" text-anchor="middle" class="pa-sub">int x; (zero-initialized)</text>
  </g>

  <g class="pa-layer pa-data">
    <rect x="180" y="460" width="340" height="40" rx="4"/>
    <text x="350" y="482" text-anchor="middle" class="pa-label">Data (Initialized)</text>
    <text x="350" y="495" text-anchor="middle" class="pa-sub">int x = 42;</text>
  </g>

  <g class="pa-layer pa-rodata">
    <rect x="180" y="510" width="340" height="30" rx="4"/>
    <text x="350" y="530" text-anchor="middle" class="pa-label">Read-only Data (.rodata)</text>
  </g>

  <g class="pa-layer pa-text">
    <rect x="180" y="548" width="340" height="40" rx="4"/>
    <text x="350" y="570" text-anchor="middle" class="pa-label">Text (Code)</text>
    <text x="350" y="583" text-anchor="middle" class="pa-sub">executable machine code</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="568" x2="600" y2="590" class="pa-arrow"/>
    <text x="615" y="583" class="pa-addr">low address</text>
    <text x="615" y="598" class="pa-addr">0x00400000</text>
  </g>

  <g class="pa-note">
    <text x="40" y="78" class="pa-sectlabel">Perm</text>
    <text x="40" y="145" class="pa-sectlabel">RW</text>
    <text x="40" y="355" class="pa-sectlabel">RW</text>
    <text x="40" y="432" class="pa-sectlabel">RW</text>
    <text x="40" y="482" class="pa-sectlabel">RW</text>
    <text x="40" y="525" class="pa-sectlabel">R</text>
    <text x="40" y="568" class="pa-sectlabel">RX</text>
  </g>
</svg>
</div>

<style>
.pt-addr-container { margin: 2rem 0; text-align: center; }
.pt-addr-container svg { max-width: 100%; height: auto; }
.pa-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.pa-layer rect { stroke-width: 1.5; }
.pa-label { font-size: 13px; font-weight: 700; fill: #1a202c; }
.pa-sub { font-size: 11px; fill: #4a5568; }
.pa-emph { fill: #2b6cb0; font-style: italic; }
.pa-gray { fill: #a0aec0; }
.pa-addr { font-size: 11px; fill: #718096; font-family: monospace; }
.pa-sectlabel { font-size: 12px; font-weight: 700; fill: #e53e3e; font-family: monospace; }
.pa-arrow { stroke: #718096; stroke-width: 1; }
.pa-kernel rect { fill: #fed7d7; stroke: #e53e3e; }
.pa-stack rect { fill: #bee3f8; stroke: #3182ce; }
.pa-gap rect { fill: #f7fafc; stroke: #cbd5e0; stroke-dasharray: 4 4; }
.pa-heap rect { fill: #c6f6d5; stroke: #38a169; }
.pa-bss rect { fill: #feebc8; stroke: #d69e2e; }
.pa-data rect { fill: #fefcbf; stroke: #d69e2e; }
.pa-rodata rect { fill: #e9d8fd; stroke: #805ad5; }
.pa-text rect { fill: #faf5ff; stroke: #553c9a; }

[data-mode="dark"] .pa-title { fill: #e2e8f0; }
[data-mode="dark"] .pa-label { fill: #e2e8f0; }
[data-mode="dark"] .pa-sub { fill: #cbd5e0; }
[data-mode="dark"] .pa-emph { fill: #63b3ed; }
[data-mode="dark"] .pa-gray { fill: #718096; }
[data-mode="dark"] .pa-addr { fill: #a0aec0; }
[data-mode="dark"] .pa-sectlabel { fill: #fc8181; }
[data-mode="dark"] .pa-arrow { stroke: #a0aec0; }
[data-mode="dark"] .pa-kernel rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .pa-stack rect { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pa-gap rect { fill: #1a202c; stroke: #4a5568; }
[data-mode="dark"] .pa-heap rect { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .pa-bss rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .pa-data rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .pa-rodata rect { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .pa-text rect { fill: #44337a; stroke: #b794f4; }

@media (max-width: 768px) {
  .pa-title { font-size: 14px; }
  .pa-label { font-size: 11px; }
  .pa-sub { font-size: 9.5px; }
  .pa-addr { font-size: 9px; }
  .pa-sectlabel { font-size: 10px; }
}
</style>

A tour of each region (from low address upward):

- **Text (`.text`)**: executable machine code. Allowed **read + execute** only; writes cause a segfault
- **Read-only data (`.rodata`)**: string literals (`"Hello"`), constant arrays. **Read-only**
- **Data (`.data`)**: initialized globals and statics (`int x = 42;`). The initial values sit in the file
- **BSS (Block Started by Symbol)**: zero-initialized globals (`int x;`, `static char buf[1024];`). The file only records the **size**; the OS zeroes out the memory at execution — a trick to shrink the binary on disk
- **Heap**: dynamic allocations (`malloc`, `new`). Grows upward via the `brk()` syscall
- **Shared library region (mmap)**: `libc.so`, `libstdc++.so` etc. are mapped here via `mmap()`
- **Stack**: call frames, locals, return addresses. Grows **downward**
- **Kernel space**: kernel code and data. User processes have no direct access. On 32-bit Linux it's the top 1 GB; on x86-64 it's the top half

**Windows uses different section names in PE but the structure is nearly the same** (`.text`, `.data`, `.rdata`, `.bss`).

### Process States

A process moves through **multiple states**. The standard model from Silberschatz:

<div class="ps-container">
<svg viewBox="0 0 900 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process state transition diagram">
  <defs>
    <marker id="ps-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" class="ps-arrowfill"/>
    </marker>
  </defs>

  <text x="450" y="22" text-anchor="middle" class="ps-title">Process State Transitions (Silberschatz model)</text>

  <rect x="60" y="40" width="140" height="50" rx="24" class="ps-new"/>
  <text x="130" y="72" text-anchor="middle" class="ps-state">New</text>

  <rect x="230" y="155" width="140" height="50" rx="24" class="ps-ready"/>
  <text x="300" y="187" text-anchor="middle" class="ps-state">Ready</text>

  <rect x="470" y="155" width="140" height="50" rx="24" class="ps-running"/>
  <text x="540" y="187" text-anchor="middle" class="ps-state">Running</text>

  <rect x="710" y="155" width="140" height="50" rx="24" class="ps-terminated"/>
  <text x="780" y="187" text-anchor="middle" class="ps-state">Terminated</text>

  <rect x="350" y="295" width="140" height="50" rx="24" class="ps-waiting"/>
  <text x="420" y="327" text-anchor="middle" class="ps-state">Waiting</text>

  <line x1="130" y1="90" x2="270" y2="155" class="ps-arrow" marker-end="url(#ps-arrowhead)"/>
  <text x="175" y="118" class="ps-label">admitted</text>

  <line x1="370" y1="180" x2="466" y2="180" class="ps-arrow" marker-end="url(#ps-arrowhead)"/>
  <text x="418" y="173" text-anchor="middle" class="ps-label">scheduler dispatch</text>

  <path d="M 540 155 Q 420 95 300 155" class="ps-arrow ps-arrow-curve" marker-end="url(#ps-arrowhead)"/>
  <text x="420" y="110" text-anchor="middle" class="ps-label">interrupt</text>

  <line x1="500" y1="205" x2="468" y2="295" class="ps-arrow" marker-end="url(#ps-arrowhead)"/>
  <text x="510" y="260" class="ps-label">I/O or event wait</text>

  <line x1="370" y1="295" x2="322" y2="205" class="ps-arrow" marker-end="url(#ps-arrowhead)"/>
  <text x="310" y="260" text-anchor="end" class="ps-label">I/O or event completion</text>

  <line x1="610" y1="180" x2="706" y2="180" class="ps-arrow" marker-end="url(#ps-arrowhead)"/>
  <text x="658" y="173" text-anchor="middle" class="ps-label">exit</text>
</svg>
</div>

<style>
.ps-container { margin: 2rem 0; text-align: center; }
.ps-container svg { max-width: 100%; height: auto; }
.ps-title { font-size: 15px; font-weight: 700; fill: #1a202c; }
.ps-new { fill: #e2e8f0; stroke: #4a5568; stroke-width: 1.5; }
.ps-ready { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.ps-running { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.ps-waiting { fill: #feebc8; stroke: #dd6b20; stroke-width: 1.5; }
.ps-terminated { fill: #edf2f7; stroke: #718096; stroke-width: 1.5; stroke-dasharray: 5 3; }
.ps-state { font-size: 14px; font-weight: 700; fill: #1a202c; }
.ps-arrow { stroke: #2d3748; stroke-width: 1.5; fill: none; }
.ps-arrow-curve { stroke: #2d3748; stroke-width: 1.5; fill: none; }
.ps-arrowfill { fill: #2d3748; }
.ps-label { font-size: 11px; fill: #2d3748; font-style: italic; }

[data-mode="dark"] .ps-title { fill: #e2e8f0; }
[data-mode="dark"] .ps-new { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .ps-ready { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .ps-running { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .ps-waiting { fill: #5c2f0c; stroke: #ed8936; }
[data-mode="dark"] .ps-terminated { fill: #1a202c; stroke: #a0aec0; stroke-dasharray: 5 3; }
[data-mode="dark"] .ps-state { fill: #e2e8f0; }
[data-mode="dark"] .ps-arrow { stroke: #cbd5e0; }
[data-mode="dark"] .ps-arrow-curve { stroke: #cbd5e0; }
[data-mode="dark"] .ps-arrowfill { fill: #cbd5e0; }
[data-mode="dark"] .ps-label { fill: #cbd5e0; }

@media (max-width: 768px) {
  .ps-title { font-size: 12px; }
  .ps-state { font-size: 11px; }
  .ps-label { font-size: 9.5px; }
}
</style>

- **New**: process just created
- **Ready**: runnable but waiting for a CPU
- **Running**: actually executing on a CPU
- **Waiting (or Blocked)**: waiting for I/O or an event
- **Terminated**: exited

Real OSes have **many more states**. Linux's `task_struct` has `TASK_RUNNING`, `TASK_INTERRUPTIBLE`, `TASK_UNINTERRUPTIBLE`, `TASK_STOPPED`, `TASK_TRACED`, `TASK_DEAD`, `TASK_WAKEKILL`, `TASK_WAKING`, `TASK_PARKED`, and more. The letters `S`, `R`, `D`, `Z` you see in `ps` are these states.

```bash
$ ps aux
USER  PID  %CPU %MEM  COMMAND
root   1   0.0  0.1   /sbin/init           <- S (sleeping)
www    1234 2.1  1.5   nginx: worker        <- R (running)
root   5678 0.0  0.0   [kworker/u8:2]       <- D (uninterruptible sleep)
```

**D state (uninterruptible sleep)** matters for game developers too — it means waiting on disk I/O or a driver request, and even `kill -9` doesn't work in this state. A lot of "unresponsive processes" are stuck in D.

---

## Part 2: Process Creation — fork, exec, CreateProcess

Now for **how** processes are created. This is where the philosophical differences among the three OSes become sharpest.

### Unix: fork() + exec() — The Two-Step Model

Unix's idea is **"duplicate the parent, then overwrite."**

```c
#include <unistd.h>
#include <sys/wait.h>

int main() {
    pid_t pid = fork();   /* step 1: clone yourself */

    if (pid == 0) {
        /* child */
        execl("/bin/ls", "ls", "-l", NULL);   /* step 2: overwrite with a new program */
        /* not reached if execl succeeds */
    } else if (pid > 0) {
        /* parent */
        int status;
        waitpid(pid, &status, 0);             /* wait for the child */
    } else {
        perror("fork failed");
    }
    return 0;
}
```

A single call to `fork()` **returns twice**. It returns the child's PID to the parent and 0 to the child. An odd API.

**What `fork()` does** (naive implementation):
1. Create a new PCB (`task_struct`)
2. **Copy the parent's entire address space** (text, data, heap, stack all)
3. Copy open file descriptors too
4. Assign a new PID to the child
5. Put the child on the ready queue

Step 2 is the problem. When a process's address space is hundreds of MB, **copying it every time is hugely expensive**. And if `exec()` is called right after `fork()`, the address space is overwritten anyway — you copied only to throw away.

### Copy-on-Write — "Actually Copy Only On Write"

The answer is **Copy-on-Write (COW)**. At `fork()` time, **only the page tables are copied**, and the actual memory pages are **shared** between parent and child — but marked **read-only**.

When either side **tries to write** to a page, the hardware raises a page fault, and only then does the OS copy **that one page**.

<div class="pt-fork-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="fork with COW">
  <text x="450" y="28" text-anchor="middle" class="pf-title">fork() + Copy-on-Write in practice</text>

  <g class="pf-step">
    <text x="150" y="65" text-anchor="middle" class="pf-step-label">1) Right after fork()</text>
    <rect x="30" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="80" y="105" text-anchor="middle" class="pf-proc-label">parent</text>
    <text x="80" y="125" text-anchor="middle" class="pf-proc-sub">page table</text>

    <rect x="170" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="220" y="105" text-anchor="middle" class="pf-proc-label">child</text>
    <text x="220" y="125" text-anchor="middle" class="pf-proc-sub">page table (copied)</text>

    <rect x="80" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="150" y="194" text-anchor="middle" class="pf-page-label">physical page (read-only)</text>

    <line x1="80" y1="140" x2="130" y2="170" class="pf-edge"/>
    <line x1="220" y1="140" x2="170" y2="170" class="pf-edge"/>

    <text x="150" y="235" text-anchor="middle" class="pf-note">Only the page table is copied — fast</text>
    <text x="150" y="252" text-anchor="middle" class="pf-note">Actual memory stays shared</text>
  </g>

  <g class="pf-step">
    <text x="450" y="65" text-anchor="middle" class="pf-step-label">2) Child tries to write</text>
    <rect x="330" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="380" y="105" text-anchor="middle" class="pf-proc-label">parent</text>
    <text x="380" y="125" text-anchor="middle" class="pf-proc-sub">page table</text>

    <rect x="470" y="80" width="100" height="60" rx="4" class="pf-proc pf-proc-active"/>
    <text x="520" y="105" text-anchor="middle" class="pf-proc-label">child</text>
    <text x="520" y="125" text-anchor="middle" class="pf-proc-sub">attempts write ✍️</text>

    <rect x="380" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="450" y="194" text-anchor="middle" class="pf-page-label">physical page (read-only)</text>

    <line x1="380" y1="140" x2="430" y2="170" class="pf-edge"/>
    <line x1="520" y1="140" x2="470" y2="170" class="pf-edge pf-edge-fault"/>

    <text x="450" y="235" text-anchor="middle" class="pf-note pf-fault">⚡ Page fault</text>
    <text x="450" y="252" text-anchor="middle" class="pf-note">CPU → OS takes over</text>
  </g>

  <g class="pf-step">
    <text x="750" y="65" text-anchor="middle" class="pf-step-label">3) OS copies the page</text>
    <rect x="630" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="680" y="105" text-anchor="middle" class="pf-proc-label">parent</text>

    <rect x="770" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="820" y="105" text-anchor="middle" class="pf-proc-label">child</text>

    <rect x="620" y="170" width="120" height="40" rx="4" class="pf-page pf-page-orig"/>
    <text x="680" y="194" text-anchor="middle" class="pf-page-label">original (RW restored)</text>

    <rect x="760" y="170" width="120" height="40" rx="4" class="pf-page pf-page-new"/>
    <text x="820" y="194" text-anchor="middle" class="pf-page-label">copy (child only)</text>

    <line x1="680" y1="140" x2="680" y2="170" class="pf-edge"/>
    <line x1="820" y1="140" x2="820" y2="170" class="pf-edge"/>

    <text x="750" y="235" text-anchor="middle" class="pf-note">Only the written page is copied</text>
    <text x="750" y="252" text-anchor="middle" class="pf-note">The rest stays shared</text>
  </g>

  <g class="pf-conclusion">
    <rect x="30" y="290" width="840" height="130" rx="8" class="pf-concl-box"/>
    <text x="450" y="315" text-anchor="middle" class="pf-concl-title">Result: fork() is not "copy" but "share + lazy copy"</text>
    <text x="450" y="343" text-anchor="middle" class="pf-concl-line">• fork() itself does only page-table-sized work — microseconds</text>
    <text x="450" y="363" text-anchor="middle" class="pf-concl-line">• If the child exec()s without writing most pages, copy cost is near zero</text>
    <text x="450" y="383" text-anchor="middle" class="pf-concl-line">• Granularity is one page (typically 4KB or 16KB) — one byte written copies the whole page</text>
    <text x="450" y="403" text-anchor="middle" class="pf-concl-line">• Linux makes this the default for task creation, so spawning processes is very fast</text>
  </g>
</svg>
</div>

<style>
.pt-fork-container { margin: 2rem 0; text-align: center; }
.pt-fork-container svg { max-width: 100%; height: auto; }
.pf-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.pf-step-label { font-size: 13px; font-weight: 600; fill: #2d3748; }
.pf-proc rect, .pf-proc { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.pf-proc-active { fill: #feebc8; stroke: #d69e2e; stroke-width: 2; }
.pf-proc-label { font-size: 12px; font-weight: 700; fill: #1a202c; }
.pf-proc-sub { font-size: 10px; fill: #4a5568; }
.pf-page { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.pf-page-orig { fill: #bee3f8; stroke: #3182ce; }
.pf-page-new { fill: #feebc8; stroke: #d69e2e; }
.pf-page-label { font-size: 11px; fill: #1a202c; }
.pf-edge { stroke: #4a5568; stroke-width: 1.5; fill: none; }
.pf-edge-fault { stroke: #e53e3e; stroke-width: 2; stroke-dasharray: 3 3; }
.pf-note { font-size: 11px; fill: #4a5568; }
.pf-fault { fill: #e53e3e; font-weight: 700; }
.pf-concl-box { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.5; }
.pf-concl-title { font-size: 13px; font-weight: 700; fill: #553c9a; }
.pf-concl-line { font-size: 11px; fill: #2d3748; }

[data-mode="dark"] .pf-title { fill: #e2e8f0; }
[data-mode="dark"] .pf-step-label { fill: #cbd5e0; }
[data-mode="dark"] .pf-proc { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pf-proc-active { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .pf-proc-label { fill: #e2e8f0; }
[data-mode="dark"] .pf-proc-sub { fill: #a0aec0; }
[data-mode="dark"] .pf-page { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .pf-page-orig { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pf-page-new { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .pf-page-label { fill: #e2e8f0; }
[data-mode="dark"] .pf-edge { stroke: #a0aec0; }
[data-mode="dark"] .pf-edge-fault { stroke: #fc8181; }
[data-mode="dark"] .pf-note { fill: #cbd5e0; }
[data-mode="dark"] .pf-fault { fill: #fc8181; }
[data-mode="dark"] .pf-concl-box { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .pf-concl-title { fill: #d6bcfa; }
[data-mode="dark"] .pf-concl-line { fill: #e2e8f0; }

@media (max-width: 768px) {
  .pf-title { font-size: 13px; }
  .pf-step-label { font-size: 11px; }
  .pf-concl-title { font-size: 11px; }
  .pf-concl-line { font-size: 9.5px; }
}
</style>

COW requires hardware support — the CPU's MMU (Memory Management Unit) must enforce per-page protection and raise page faults, otherwise the OS has no hook to intervene. **Page-level MMU** is the foundation for nearly every modern-OS trick (COW, swap, mmap, shared memory).

### Windows: CreateProcess() — A Single Call

Windows took a different path. There is no parent-cloning concept; it **builds a new process from scratch**.

```c
#include <windows.h>

int main() {
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    BOOL ok = CreateProcess(
        "C:\\Windows\\System32\\notepad.exe",  /* executable */
        NULL,                                   /* command line */
        NULL, NULL,                             /* process/thread security */
        FALSE,                                  /* inherit handles? */
        0,                                      /* creation flags */
        NULL, NULL,                             /* environment, working dir */
        &si, &pi);

    if (ok) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    return 0;
}
```

Unix's `fork()` takes no parameters; `CreateProcess()` takes **ten**. That's the Windows philosophy of "stuff every configurable option for process creation into one function."

**Trade-offs**:

| Aspect | Unix `fork()+exec()` | Windows `CreateProcess()` |
|--------|---------------------|---------------------------|
| **API complexity** | Two steps, each simple | One step, many parameters |
| **Process creation cost** | Very cheap via COW | Relatively expensive |
| **Shell implementation** | Natural (fork → set up redirections → exec) | Needs a separate API like ShellExecute |
| **Security** | Parent handles inherit automatically (error-prone) | Inheritance is explicit |
| **Flexibility** | Arbitrary code between fork and exec | Only at creation time |

### macOS — Unix Inheritance Plus a Few Twists

macOS comes from BSD, so naturally it supports `fork()` and `exec()`. But **XNU's internal implementation is slightly distinctive**.

When BSD's `fork()` is mapped down to Mach, what actually happens is:
1. Clone the current `proc` struct
2. Clone the current `task` at the Mach level (`task_create()`)
3. Create an initial thread (`thread_create()`)
4. Clone the address space too (Mach's vm_map, COW)

That is, **a single BSD `fork()` call decomposes into several Mach-level operations**. This is the practical face of the XNU dual structure.

Also interesting is macOS's **`posix_spawn()`**. A POSIX standard that Apple actively promotes, it **performs fork+exec in one call**.

```c
posix_spawn(&pid, "/bin/ls", NULL, NULL, argv, environ);
```

Why prefer it? **Because of iOS**. On iOS, `fork()` is forbidden for security reasons, and only `posix_spawn()` is allowed. The internal implementation can also be more efficient (it may even skip the COW page-table clone).

> ### Hold on, let's clarify this
>
> **"Why is fork() banned on iOS?"**
>
> Three reasons overlap.
>
> 1. **Sandbox-escape risk**: a forked child inherits its parent's privileges, and in iOS's strict app sandbox model this boundary becomes a potential avenue for vulnerabilities
> 2. **Objective-C runtime state duplication**: iOS apps are usually written in Objective-C or Swift, whose runtimes initialize lots of state at startup (threads, GCD queues, IOKit connections, etc.). Post-fork, this state easily falls out of consistency
> 3. **Memory efficiency**: iOS is memory-constrained, and even COW still needs page-table cloning. `posix_spawn()` can skip even that
>
> On macOS, `fork()` is still allowed, but Apple recommends `posix_spawn()` where possible.

---

## Part 3: Threads — Why Processes Alone Aren't Enough

### Limits of Process-Based Concurrency

In 1970s–80s Unix, **one process meant one execution flow**. To do multiple things at once, you `fork()`ed multiple processes. A web server would create one process per connection (classic Apache `prefork`).

Problems with this model:

1. **Process creation cost**: cheaper thanks to COW, but still microseconds to milliseconds for page-table cloning, PCB allocation, etc.
2. **Context switch cost**: switching between processes also changes the address space, so TLB flushes are required (details below)
3. **IPC cost**: since processes have separate address spaces, exchanging data requires heavy machinery like pipes, sockets, or shared memory
4. **Expressing shared state is hard**: when multiple flows need to share the same data structure, it gets complicated

By the 1990s a solution was needed, and that was the **thread**.

### Definition of a Thread

A **thread** is **an independent flow of execution within a process**. When multiple threads exist in one process, they all share the same address space but **can execute simultaneously on CPUs**.

What threads **share**:
- **Text (code)**: naturally, they execute the same code
- **Heap**: memory allocated with `malloc`
- **Data / BSS**: globals and statics
- **Open file descriptors**
- **Signal handlers**

What threads keep **private**:
- **Stack**: each thread has its own
- **CPU register state**: PC, SP, general-purpose regs
- **TLS (Thread-Local Storage)**: per-thread globals
- **Error state**: `errno` (in POSIX it's per-thread)

<div class="pt-share-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process vs thread memory sharing">
  <text x="450" y="28" text-anchor="middle" class="ps-title">Memory sharing — processes vs threads</text>

  <g class="ps-left">
    <text x="225" y="62" text-anchor="middle" class="ps-heading">Multiple processes — fully separated</text>

    <g class="ps-proc">
      <rect x="40" y="80" width="170" height="330" rx="8"/>
      <text x="125" y="103" text-anchor="middle" class="ps-proc-label">Process A</text>
      <rect x="55" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="125" y="137" text-anchor="middle" class="ps-sect-lab">Text (code)</text>
      <rect x="55" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="125" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="55" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="125" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="55" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="125" y="302" text-anchor="middle" class="ps-sect-lab">Stack (flow 1)</text>
      <rect x="55" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="55" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="55" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <g class="ps-proc">
      <rect x="240" y="80" width="170" height="330" rx="8"/>
      <text x="325" y="103" text-anchor="middle" class="ps-proc-label">Process B</text>
      <rect x="255" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="325" y="137" text-anchor="middle" class="ps-sect-lab">Text (separate)</text>
      <rect x="255" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="325" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="255" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="325" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="255" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="325" y="302" text-anchor="middle" class="ps-sect-lab">Stack (flow 1)</text>
      <rect x="255" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="255" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="255" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <text x="225" y="433" text-anchor="middle" class="ps-caption">No communication without IPC (pipes/sockets/shared memory)</text>
  </g>

  <g class="ps-right">
    <text x="675" y="62" text-anchor="middle" class="ps-heading">Multiple threads in one process — mostly shared</text>

    <g class="ps-proc ps-proc-big">
      <rect x="470" y="80" width="410" height="330" rx="8"/>
      <text x="675" y="103" text-anchor="middle" class="ps-proc-label">Process C (3 threads)</text>

      <rect x="485" y="118" width="380" height="28" rx="3" class="ps-sect ps-sect-text ps-sect-shared"/>
      <text x="675" y="137" text-anchor="middle" class="ps-sect-lab">Text (shared)</text>
      <rect x="485" y="152" width="380" height="28" rx="3" class="ps-sect ps-sect-data ps-sect-shared"/>
      <text x="675" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS (shared)</text>
      <rect x="485" y="186" width="380" height="60" rx="3" class="ps-sect ps-sect-heap ps-sect-shared"/>
      <text x="675" y="221" text-anchor="middle" class="ps-sect-lab">Heap (shared)</text>

      <g class="ps-thread">
        <rect x="485" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="545" y="272" text-anchor="middle" class="ps-sect-lab">Stack T1</text>
        <text x="545" y="290" text-anchor="middle" class="ps-sect-sub">private</text>
      </g>
      <g class="ps-thread">
        <rect x="615" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="675" y="272" text-anchor="middle" class="ps-sect-lab">Stack T2</text>
        <text x="675" y="290" text-anchor="middle" class="ps-sect-sub">private</text>
      </g>
      <g class="ps-thread">
        <rect x="745" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="805" y="272" text-anchor="middle" class="ps-sect-lab">Stack T3</text>
        <text x="805" y="290" text-anchor="middle" class="ps-sect-sub">private</text>
      </g>

      <g class="ps-thread">
        <rect x="485" y="308" width="120" height="28" rx="3" class="ps-sect ps-sect-misc ps-sect-private"/>
        <text x="545" y="327" text-anchor="middle" class="ps-sect-sub">Regs T1</text>
      </g>
      <g class="ps-thread">
        <rect x="615" y="308" width="120" height="28" rx="3" class="ps-sect ps-sect-misc ps-sect-private"/>
        <text x="675" y="327" text-anchor="middle" class="ps-sect-sub">Regs T2</text>
      </g>
      <g class="ps-thread">
        <rect x="745" y="308" width="120" height="28" rx="3" class="ps-sect ps-sect-misc ps-sect-private"/>
        <text x="805" y="327" text-anchor="middle" class="ps-sect-sub">Regs T3</text>
      </g>

      <rect x="485" y="342" width="380" height="28" rx="3" class="ps-sect ps-sect-misc ps-sect-shared"/>
      <text x="675" y="361" text-anchor="middle" class="ps-sect-lab">File descriptors (shared)</text>

      <g class="ps-thread">
        <rect x="485" y="376" width="120" height="22" rx="3" class="ps-sect ps-sect-tls"/>
        <text x="545" y="391" text-anchor="middle" class="ps-sect-sub">TLS T1</text>
      </g>
      <g class="ps-thread">
        <rect x="615" y="376" width="120" height="22" rx="3" class="ps-sect ps-sect-tls"/>
        <text x="675" y="391" text-anchor="middle" class="ps-sect-sub">TLS T2</text>
      </g>
      <g class="ps-thread">
        <rect x="745" y="376" width="120" height="22" rx="3" class="ps-sect ps-sect-tls"/>
        <text x="805" y="391" text-anchor="middle" class="ps-sect-sub">TLS T3</text>
      </g>
    </g>

    <text x="675" y="433" text-anchor="middle" class="ps-caption">Same heap/data read and written directly — the root of races</text>
  </g>
</svg>
</div>

<style>
.pt-share-container { margin: 2rem 0; text-align: center; }
.pt-share-container svg { max-width: 100%; height: auto; }
.ps-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.ps-heading { font-size: 13px; font-weight: 600; fill: #2d3748; }
.ps-proc rect { fill: #f7fafc; stroke: #a0aec0; stroke-width: 1.5; }
.ps-proc-label { font-size: 12px; font-weight: 700; fill: #1a202c; }
.ps-sect { stroke-width: 1; }
.ps-sect-text { fill: #faf5ff; stroke: #805ad5; }
.ps-sect-data { fill: #feebc8; stroke: #d69e2e; }
.ps-sect-heap { fill: #c6f6d5; stroke: #38a169; }
.ps-sect-stack { fill: #bee3f8; stroke: #3182ce; }
.ps-sect-misc { fill: #edf2f7; stroke: #718096; }
.ps-sect-tls { fill: #fed7d7; stroke: #e53e3e; }
.ps-sect-shared { stroke-dasharray: 0; stroke-width: 2; }
.ps-sect-private { stroke-dasharray: 3 2; }
.ps-sect-lab { font-size: 10.5px; font-weight: 600; fill: #1a202c; }
.ps-sect-sub { font-size: 9.5px; fill: #4a5568; }
.ps-caption { font-size: 11px; fill: #4a5568; font-style: italic; }

[data-mode="dark"] .ps-title { fill: #e2e8f0; }
[data-mode="dark"] .ps-heading { fill: #cbd5e0; }
[data-mode="dark"] .ps-proc rect { fill: #1a202c; stroke: #718096; }
[data-mode="dark"] .ps-proc-label { fill: #e2e8f0; }
[data-mode="dark"] .ps-sect-text { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .ps-sect-data { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .ps-sect-heap { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .ps-sect-stack { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .ps-sect-misc { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .ps-sect-tls { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .ps-sect-lab { fill: #e2e8f0; }
[data-mode="dark"] .ps-sect-sub { fill: #cbd5e0; }
[data-mode="dark"] .ps-caption { fill: #a0aec0; }

@media (max-width: 768px) {
  .ps-title { font-size: 13px; }
  .ps-heading { font-size: 11px; }
  .ps-proc-label { font-size: 10px; }
  .ps-sect-lab { font-size: 9px; }
  .ps-sect-sub { font-size: 8px; }
  .ps-caption { font-size: 9.5px; }
}
</style>

Key takeaways from this diagram:

1. **Threads share heap and globals by default** — "shared memory" exists naturally
2. So two threads both doing `counter++` on the same `int counter` creates a **race condition**
3. Two processes, by contrast, are naturally isolated because their address spaces are separate

The answer to Stage 2's key question — "**why does the program crash only sometimes when two threads use the same variable?**" — is hidden in this diagram. Threads **intentionally share memory**, so concurrency issues arise, and they need **synchronization techniques** to manage them. (We cover that thoroughly in Part 10: Synchronization Primitives.)

### TCB — The Thread Control Block

Just as processes have PCBs, threads have **TCBs (Thread Control Blocks)**. A TCB holds:

- Thread ID
- CPU register state (saved context)
- Thread state (Running, Ready, Waiting)
- Stack pointer, stack base
- Scheduling info (priority etc.)
- Pointer to the owning process

Per-OS implementation:

- **Linux**: `task_struct` — processes and threads use the **same struct**, distinguished by which fields they share
- **Windows**: `KTHREAD` + `ETHREAD`
- **macOS**: Mach's `struct thread`

### Linux's Peculiar Philosophy — "Processes and Threads Are the Same"

Linus Torvalds made a bold decision in the 1990s: **"Don't make processes and threads separate concepts; unify them as a single 'execution unit.'"**

In Linux, instead of `fork()`, there's the more general `clone()` syscall. `clone()` specifies **"what to share with the parent"** as a bit flag.

```c
/* Linux clone() — concept */
clone(fn, stack, flags, arg);

/* Example flags: */
CLONE_VM       /* share address space (true → thread, false → process) */
CLONE_FS       /* share filesystem state */
CLONE_FILES    /* share file descriptors */
CLONE_SIGHAND  /* share signal handlers */
CLONE_THREAD   /* same thread group */
/* ... */
```

- `fork()` = `clone()` with **all share flags OFF**
- `pthread_create()` = `clone()` with **all share flags ON**
- **Any combination** in between is possible

That's Linux's "process and thread are on a continuum" worldview. Android for example uses **"partially sharing" process clones** in practice (the Zygote process).

### TLS — Thread-Local Storage

Sometimes you need variables that **look global but are actually independent per thread**. That's **TLS**.

The canonical example: `errno`. In POSIX, `errno` is "the error code of the last syscall," but it must be per-thread (thread A's failed `read()` must not be overwritten by thread B). So `errno` is implemented as TLS.

TLS declarations by language:

```c
/* C11 */
_Thread_local int counter = 0;

/* GCC/Clang extension */
__thread int counter = 0;
```

```cpp
// C++11
thread_local int counter = 0;
```

```csharp
// C#
[ThreadStatic]
static int counter;

// Or the more flexible ThreadLocal<T>
static ThreadLocal<int> counter = new ThreadLocal<int>(() => 0);
```

Practical uses in game development:
- Logging systems use TLS to store each thread's **name** for inclusion in log lines
- Rendering assigns **per-thread command buffers** that are merged later
- Profilers track the **current scope stack** per thread

---

## Part 4: Thread Models — 1:1, N:1, M:N

A deeper question: when you call `pthread_create()` or `new Thread()`, **how does the kernel manage that thread**?

### Why the Question Matters

The unit that actually runs on a CPU is a **kernel-level thread (KLT)**. Only the kernel schedules the CPU.

In contrast, the "thread" your program creates can be just a **user-space abstraction**. That's called a **user-level thread (ULT)**.

The mapping between user threads and kernel threads falls into three categories.

<div class="pt-model-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Thread mapping models">
  <text x="450" y="28" text-anchor="middle" class="pm-title">User threads ↔ Kernel threads mapping models</text>

  <g class="pm-model">
    <rect x="30" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="165" y="80" text-anchor="middle" class="pm-heading">1:1 (one-to-one)</text>
    <text x="165" y="100" text-anchor="middle" class="pm-sub">Linux NPTL, Windows</text>

    <g class="pm-ulist">
      <rect x="55" y="125" width="60" height="40" rx="4" class="pm-ult"/>
      <text x="85" y="150" text-anchor="middle" class="pm-ult-label">ULT 1</text>
      <rect x="135" y="125" width="60" height="40" rx="4" class="pm-ult"/>
      <text x="165" y="150" text-anchor="middle" class="pm-ult-label">ULT 2</text>
      <rect x="215" y="125" width="60" height="40" rx="4" class="pm-ult"/>
      <text x="245" y="150" text-anchor="middle" class="pm-ult-label">ULT 3</text>
    </g>
    <line x1="85" y1="165" x2="85" y2="215" class="pm-edge"/>
    <line x1="165" y1="165" x2="165" y2="215" class="pm-edge"/>
    <line x1="245" y1="165" x2="245" y2="215" class="pm-edge"/>
    <g class="pm-klist">
      <rect x="55" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="85" y="240" text-anchor="middle" class="pm-klt-label">KLT 1</text>
      <rect x="135" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="165" y="240" text-anchor="middle" class="pm-klt-label">KLT 2</text>
      <rect x="215" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="245" y="240" text-anchor="middle" class="pm-klt-label">KLT 3</text>
    </g>

    <g class="pm-pros">
      <text x="165" y="290" text-anchor="middle" class="pm-sec-label">Pros</text>
      <text x="165" y="310" text-anchor="middle" class="pm-line">• Simple to implement</text>
      <text x="165" y="328" text-anchor="middle" class="pm-line">• True parallelism (multicore)</text>
      <text x="165" y="346" text-anchor="middle" class="pm-line">• Uses the kernel scheduler</text>
    </g>
    <g class="pm-cons">
      <text x="165" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">Cons</text>
      <text x="165" y="400" text-anchor="middle" class="pm-line">• Thread creation is costly</text>
      <text x="165" y="418" text-anchor="middle" class="pm-line">• Thousands exhaust kernel resources</text>
      <text x="165" y="436" text-anchor="middle" class="pm-line">• Context switches are heavy</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="315" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="450" y="80" text-anchor="middle" class="pm-heading">N:1 (many-to-one)</text>
    <text x="450" y="100" text-anchor="middle" class="pm-sub">old green threads, GNU Pth</text>

    <g class="pm-ulist">
      <rect x="340" y="125" width="52" height="40" rx="4" class="pm-ult"/>
      <text x="366" y="150" text-anchor="middle" class="pm-ult-label">ULT 1</text>
      <rect x="400" y="125" width="52" height="40" rx="4" class="pm-ult"/>
      <text x="426" y="150" text-anchor="middle" class="pm-ult-label">ULT 2</text>
      <rect x="460" y="125" width="52" height="40" rx="4" class="pm-ult"/>
      <text x="486" y="150" text-anchor="middle" class="pm-ult-label">ULT 3</text>
      <rect x="520" y="125" width="52" height="40" rx="4" class="pm-ult"/>
      <text x="546" y="150" text-anchor="middle" class="pm-ult-label">ULT 4</text>
    </g>
    <line x1="366" y1="165" x2="450" y2="215" class="pm-edge"/>
    <line x1="426" y1="165" x2="450" y2="215" class="pm-edge"/>
    <line x1="486" y1="165" x2="450" y2="215" class="pm-edge"/>
    <line x1="546" y1="165" x2="450" y2="215" class="pm-edge"/>
    <g class="pm-klist">
      <rect x="420" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="450" y="240" text-anchor="middle" class="pm-klt-label">1 KLT</text>
    </g>

    <g class="pm-pros">
      <text x="450" y="290" text-anchor="middle" class="pm-sec-label">Pros</text>
      <text x="450" y="310" text-anchor="middle" class="pm-line">• Extremely cheap creation</text>
      <text x="450" y="328" text-anchor="middle" class="pm-line">• Supports hundreds of thousands</text>
      <text x="450" y="346" text-anchor="middle" class="pm-line">• User-level scheduler freedom</text>
    </g>
    <g class="pm-cons">
      <text x="450" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">Cons</text>
      <text x="450" y="400" text-anchor="middle" class="pm-line">• No parallelism (one core only)</text>
      <text x="450" y="418" text-anchor="middle" class="pm-line">• Blocking syscalls stop everyone</text>
      <text x="450" y="436" text-anchor="middle" class="pm-line">• Rarely used today</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="600" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="735" y="80" text-anchor="middle" class="pm-heading">M:N (many-to-many)</text>
    <text x="735" y="100" text-anchor="middle" class="pm-sub">Go, Erlang, old Solaris</text>

    <g class="pm-ulist">
      <rect x="625" y="125" width="42" height="40" rx="4" class="pm-ult"/>
      <text x="646" y="150" text-anchor="middle" class="pm-ult-label">U1</text>
      <rect x="675" y="125" width="42" height="40" rx="4" class="pm-ult"/>
      <text x="696" y="150" text-anchor="middle" class="pm-ult-label">U2</text>
      <rect x="725" y="125" width="42" height="40" rx="4" class="pm-ult"/>
      <text x="746" y="150" text-anchor="middle" class="pm-ult-label">U3</text>
      <rect x="775" y="125" width="42" height="40" rx="4" class="pm-ult"/>
      <text x="796" y="150" text-anchor="middle" class="pm-ult-label">U4</text>
      <rect x="825" y="125" width="42" height="40" rx="4" class="pm-ult"/>
      <text x="846" y="150" text-anchor="middle" class="pm-ult-label">U5</text>
    </g>
    <line x1="646" y1="165" x2="680" y2="215" class="pm-edge"/>
    <line x1="696" y1="165" x2="680" y2="215" class="pm-edge"/>
    <line x1="746" y1="165" x2="750" y2="215" class="pm-edge"/>
    <line x1="796" y1="165" x2="820" y2="215" class="pm-edge"/>
    <line x1="846" y1="165" x2="820" y2="215" class="pm-edge"/>
    <g class="pm-klist">
      <rect x="650" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="680" y="240" text-anchor="middle" class="pm-klt-label">KLT 1</text>
      <rect x="720" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="750" y="240" text-anchor="middle" class="pm-klt-label">KLT 2</text>
      <rect x="790" y="215" width="60" height="40" rx="4" class="pm-klt"/>
      <text x="820" y="240" text-anchor="middle" class="pm-klt-label">KLT 3</text>
    </g>

    <g class="pm-pros">
      <text x="735" y="290" text-anchor="middle" class="pm-sec-label">Pros</text>
      <text x="735" y="310" text-anchor="middle" class="pm-line">• Cheap threads + parallelism</text>
      <text x="735" y="328" text-anchor="middle" class="pm-line">• Best of both worlds</text>
      <text x="735" y="346" text-anchor="middle" class="pm-line">• Millions of goroutines</text>
    </g>
    <g class="pm-cons">
      <text x="735" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">Cons</text>
      <text x="735" y="400" text-anchor="middle" class="pm-line">• Complex runtime</text>
      <text x="735" y="418" text-anchor="middle" class="pm-line">• Scheduling fairness issues</text>
      <text x="735" y="436" text-anchor="middle" class="pm-line">• Harder to debug</text>
    </g>
  </g>
</svg>
</div>

<style>
.pt-model-container { margin: 2rem 0; text-align: center; }
.pt-model-container svg { max-width: 100%; height: auto; }
.pm-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.pm-box { fill: #f7fafc; stroke: #cbd5e0; stroke-width: 1.5; stroke-dasharray: 4 4; }
.pm-heading { font-size: 14px; font-weight: 700; fill: #2d3748; }
.pm-sub { font-size: 11px; fill: #4a5568; font-style: italic; }
.pm-ult { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.pm-ult-label { font-size: 11px; font-weight: 600; fill: #1a202c; }
.pm-klt { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1.5; }
.pm-klt-label { font-size: 11px; font-weight: 600; fill: #1a202c; }
.pm-edge { stroke: #4a5568; stroke-width: 1.5; }
.pm-sec-label { font-size: 12px; font-weight: 700; fill: #38a169; }
.pm-sec-con { fill: #c53030; }
.pm-line { font-size: 11px; fill: #2d3748; }

[data-mode="dark"] .pm-title { fill: #e2e8f0; }
[data-mode="dark"] .pm-box { fill: #1a202c; stroke: #4a5568; }
[data-mode="dark"] .pm-heading { fill: #cbd5e0; }
[data-mode="dark"] .pm-sub { fill: #a0aec0; }
[data-mode="dark"] .pm-ult { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pm-ult-label { fill: #e2e8f0; }
[data-mode="dark"] .pm-klt { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .pm-klt-label { fill: #e2e8f0; }
[data-mode="dark"] .pm-edge { stroke: #a0aec0; }
[data-mode="dark"] .pm-sec-label { fill: #68d391; }
[data-mode="dark"] .pm-sec-con { fill: #fc8181; }
[data-mode="dark"] .pm-line { fill: #e2e8f0; }

@media (max-width: 768px) {
  .pm-title { font-size: 13px; }
  .pm-heading { font-size: 11px; }
  .pm-sub { font-size: 9.5px; }
  .pm-ult-label, .pm-klt-label { font-size: 9px; }
  .pm-sec-label { font-size: 10px; }
  .pm-line { font-size: 9px; }
}
</style>

### 1:1 Model — The Current Linux/Windows Choice

In **1:1**, each user-created thread maps to exactly one kernel thread. `pthread_create()` internally calls the `clone()` syscall and directly creates a kernel-managed task.

**Linux NPTL (Native POSIX Thread Library)**:
Since Linux 2.6, the glibc pthread implementation uses NPTL, a 1:1 model. Before that there was **LinuxThreads**, a nonstandard 1:1 implementation, which NPTL replaced on POSIX compliance and performance grounds.

**Windows**:
`CreateThread()` creates a `KTHREAD` directly in the kernel. 1:1 again.

**Pros**: if one thread blocks, others keep running. Natural distribution across cores.

**Cons**: thread creation is relatively expensive; tens of thousands or more strain kernel memory.

### N:1 Model — A Legacy

In **N:1**, multiple user threads map to one kernel thread. The kernel doesn't know the process has multiple threads — it sees just one process.

This model was used in early Java "green threads," in GNU Pth, and others. It was standard in the early 1990s but **fatal drawbacks** nearly drove it extinct:

- **A blocking syscall stops everyone**: one user thread blocking in `read()` freezes all others sharing the kernel thread
- **No multicore use**: one kernel thread lives on one core

### M:N Model — Go's Choice

**M:N** combines the two. M user threads map dynamically to a pool of N kernel threads (typically N = number of CPU cores).

**Representative implementations**:
- **Go goroutines**: the Go runtime has an M:N scheduler, running millions of goroutines over a handful of OS threads
- **Erlang/Elixir**: the BEAM VM implements its own scheduler
- **Old Solaris** (Solaris 2–8): implemented POSIX pthreads M:N, but Solaris 9 switched to 1:1 for complexity reasons

**Theoretical grounding** — Anderson et al.'s SOSP 1991 [Scheduler Activations](https://dl.acm.org/doi/10.1145/121132.121151) paper tackles "what kernel support is needed so a user-level thread library can efficiently implement M:N." The key is that **on blocking syscalls the kernel should wake the user scheduler so it can assign another user thread to another kernel thread**.

The Go runtime implements a similar idea. When a goroutine tries a blocking syscall, the runtime detects it and either **migrates that goroutine to another kernel thread** or spawns a new one. So one `net.Listen` blocking doesn't affect other goroutines.

### From a Game Development Perspective

The threads used in Unity and Unreal are **1:1 at the C++/C# layer**. `new Thread()` or `std::thread` creates kernel threads directly.

However, **engines' internal Job systems or Task graphs are effectively M:N schedulers**. The programmer can queue thousands of "Jobs," yet they run on the engine's handful of worker threads. This ties directly into the Unity Job System design we address in detail in Part 13 (Lock-free and Structural Solutions).

---

## Part 5: Three-OS Thread APIs Compared

### Linux — pthreads

```c
#include <pthread.h>
#include <stdio.h>

void* worker(void* arg) {
    int id = *(int*)arg;
    printf("Thread %d running\n", id);
    return NULL;
}

int main() {
    pthread_t t1, t2;
    int id1 = 1, id2 = 2;

    pthread_create(&t1, NULL, worker, &id1);
    pthread_create(&t2, NULL, worker, &id2);

    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
```

POSIX-standard API. Internally it calls the `clone()` syscall. Officially it's "pthread," but Linux man pages are really documenting NPTL (the glibc implementation).

### Windows — CreateThread / _beginthreadex

```c
#include <windows.h>
#include <process.h>

unsigned __stdcall worker(void* arg) {
    int id = *(int*)arg;
    printf("Thread %d running\n", id);
    return 0;
}

int main() {
    HANDLE t1, t2;
    int id1 = 1, id2 = 2;

    t1 = (HANDLE)_beginthreadex(NULL, 0, worker, &id1, 0, NULL);
    t2 = (HANDLE)_beginthreadex(NULL, 0, worker, &id2, 0, NULL);

    WaitForSingleObject(t1, INFINITE);
    WaitForSingleObject(t2, INFINITE);
    CloseHandle(t1);
    CloseHandle(t2);
    return 0;
}
```

**Why not `CreateThread`?** `CreateThread` skips CRT (C Runtime Library) initialization — so thread-local state like `errno` and `strtok` isn't set up, causing subtle bugs. `_beginthreadex` initializes the CRT, so for C/C++ code you should use it.

### macOS — pthreads + libdispatch

```c
/* POSIX style — same as Linux */
#include <pthread.h>
/* ... */

/* libdispatch (GCD) style — Apple's preferred */
#include <dispatch/dispatch.h>

int main() {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        printf("Running in background\n");
        dispatch_async(dispatch_get_main_queue(), ^{
            printf("Back to main thread\n");
        });
    });

    dispatch_main();
    return 0;
}
```

macOS supports pthreads too, but Apple recommends **GCD (Grand Central Dispatch)**. We covered the rationale in Part 7 — no manual thread lifetime management, QoS-based routing to P/E cores, a predictable queue abstraction.

### C# — Language-Level Abstraction

C# works on all three OSes. The .NET runtime (CLR or CoreCLR) hides OS differences.

```csharp
using System;
using System.Threading;
using System.Threading.Tasks;

// 1) Most primitive — rarely used today
Thread t = new Thread(() => Console.WriteLine("Hello"));
t.Start();
t.Join();

// 2) ThreadPool — thread reuse
ThreadPool.QueueUserWorkItem(_ => Console.WriteLine("Hello"));

// 3) Task / async-await — modern default
await Task.Run(() => HeavyComputation());

// 4) Parallel — data parallelism
Parallel.For(0, 100, i => ProcessItem(i));
```

Underneath:
- Linux: libcoreclr uses `pthread_create()`
- Windows: uses `CreateThread()`
- macOS: uses `pthread_create()` (doesn't use GCD directly)

**Unity's quirk**: Unity discourages `Thread` usage. It nudges you to Job System, UniTask, and coroutines instead. Because most Unity Engine APIs **crash if called outside the main thread**. (See Part 13 for details.)

---

## Part 6: Context Switching — Why It's Expensive

### What a Context Switch Is

To run multiple threads alternately on one CPU core, the OS saves the current thread's state and restores the next thread's state. That's **context switching**.

What must be saved:
- **CPU registers**: RAX, RBX, …, RIP (program counter), RSP (stack pointer), flags
- **Floating-point registers**: XMM, YMM, ZMM (tens of KB in the AVX era)
- **MMU state**: on a process switch, the **page table pointer** (CR3 on x86) changes too

### The "Hidden Cost" of Context Switching

Saving and restoring registers is just **the tip of the iceberg**. The real cost is indirect effects.

<div class="pt-ctx-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Context switch cost breakdown">
  <text x="450" y="28" text-anchor="middle" class="pc-title">Context switch — direct vs hidden costs</text>

  <g class="pc-timeline">
    <line x1="60" y1="80" x2="840" y2="80" class="pc-line"/>
    <rect x="60" y="65" width="120" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="120" y="85" text-anchor="middle" class="pc-block-label">Thread A running</text>

    <rect x="180" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="220" y="80" text-anchor="middle" class="pc-block-label">switch</text>
    <text x="220" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="260" y="65" width="260" height="30" rx="3" class="pc-block pc-block-b"/>
    <text x="390" y="85" text-anchor="middle" class="pc-block-label">Thread B (cache rebuild)</text>

    <rect x="520" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="560" y="80" text-anchor="middle" class="pc-block-label">switch</text>
    <text x="560" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="600" y="65" width="240" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="720" y="85" text-anchor="middle" class="pc-block-label">Thread A (cache rebuild)</text>
  </g>

  <g class="pc-direct">
    <rect x="40" y="140" width="400" height="140" rx="8" class="pc-box pc-box-direct"/>
    <text x="240" y="162" text-anchor="middle" class="pc-box-heading">Direct cost (visible)</text>
    <text x="55" y="190" class="pc-box-line">• Register save (~30 regs, hundreds of bytes)</text>
    <text x="55" y="210" class="pc-box-line">• SIMD regs (several KB with AVX-512)</text>
    <text x="55" y="230" class="pc-box-line">• Enter kernel → run scheduler → return</text>
    <text x="55" y="250" class="pc-box-line">• MMU pointer swap (on process switch)</text>
    <text x="55" y="270" class="pc-box-line pc-box-sum">Typically <tspan class="pc-emph">1–10 microseconds</tspan> (hardware-dependent)</text>
  </g>

  <g class="pc-hidden">
    <rect x="460" y="140" width="400" height="200" rx="8" class="pc-box pc-box-hidden"/>
    <text x="660" y="162" text-anchor="middle" class="pc-box-heading">Hidden cost (invisible)</text>
    <text x="475" y="190" class="pc-box-line">• <tspan class="pc-emph">TLB flush</tspan>: address translation cache invalidated</text>
    <text x="475" y="205" class="pc-box-line-sub">→ hundreds to thousands of cycles to rebuild</text>
    <text x="475" y="225" class="pc-box-line">• <tspan class="pc-emph">CPU cache pollution</tspan>: Thread A's L1/L2 data</text>
    <text x="475" y="240" class="pc-box-line-sub">is evicted by Thread B's execution</text>
    <text x="475" y="260" class="pc-box-line">• <tspan class="pc-emph">Branch predictor pollution</tspan>: history mingled</text>
    <text x="475" y="280" class="pc-box-line">• <tspan class="pc-emph">Prefetcher state reset</tspan></text>
    <text x="475" y="300" class="pc-box-line pc-box-sum">Total <tspan class="pc-emph">tens of microseconds to milliseconds</tspan></text>
    <text x="475" y="318" class="pc-box-line pc-box-sum">of "post-switch slowdown"</text>
  </g>

  <g class="pc-conclusion">
    <rect x="40" y="360" width="820" height="60" rx="8" class="pc-concl"/>
    <text x="450" y="385" text-anchor="middle" class="pc-concl-title">Conclusion: too many threads and the CPU just context-switches without real work</text>
    <text x="450" y="405" text-anchor="middle" class="pc-concl-sub">Mitigations: (1) keep thread count near core count, (2) queue fine-grained Jobs/Tasks</text>
  </g>
</svg>
</div>

<style>
.pt-ctx-container { margin: 2rem 0; text-align: center; }
.pt-ctx-container svg { max-width: 100%; height: auto; }
.pc-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.pc-line { stroke: #4a5568; stroke-width: 1; }
.pc-block { stroke-width: 1.5; }
.pc-block-a { fill: #bee3f8; stroke: #3182ce; }
.pc-block-b { fill: #c6f6d5; stroke: #38a169; }
.pc-block-switch { fill: #fed7d7; stroke: #e53e3e; }
.pc-block-label { font-size: 11px; font-weight: 600; fill: #1a202c; }
.pc-block-sub { font-size: 9px; fill: #4a5568; }
.pc-box { stroke-width: 1.5; }
.pc-box-direct { fill: #e6fffa; stroke: #319795; }
.pc-box-hidden { fill: #fff5f5; stroke: #e53e3e; }
.pc-box-heading { font-size: 13px; font-weight: 700; fill: #2d3748; }
.pc-box-line { font-size: 11px; fill: #2d3748; }
.pc-box-line-sub { font-size: 10px; fill: #4a5568; font-style: italic; }
.pc-box-sum { font-weight: 600; }
.pc-emph { font-weight: 700; fill: #c53030; }
.pc-concl { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.5; }
.pc-concl-title { font-size: 13px; font-weight: 700; fill: #553c9a; }
.pc-concl-sub { font-size: 11px; fill: #2d3748; }

[data-mode="dark"] .pc-title { fill: #e2e8f0; }
[data-mode="dark"] .pc-line { stroke: #a0aec0; }
[data-mode="dark"] .pc-block-a { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pc-block-b { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .pc-block-switch { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .pc-block-label { fill: #e2e8f0; }
[data-mode="dark"] .pc-block-sub { fill: #a0aec0; }
[data-mode="dark"] .pc-box-direct { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .pc-box-hidden { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .pc-box-heading { fill: #e2e8f0; }
[data-mode="dark"] .pc-box-line { fill: #e2e8f0; }
[data-mode="dark"] .pc-box-line-sub { fill: #cbd5e0; }
[data-mode="dark"] .pc-emph { fill: #fc8181; }
[data-mode="dark"] .pc-concl { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .pc-concl-title { fill: #d6bcfa; }
[data-mode="dark"] .pc-concl-sub { fill: #e2e8f0; }

@media (max-width: 768px) {
  .pc-title { font-size: 13px; }
  .pc-block-label { font-size: 9px; }
  .pc-block-sub { font-size: 8px; }
  .pc-box-heading { font-size: 11px; }
  .pc-box-line { font-size: 9px; }
  .pc-box-line-sub { font-size: 8px; }
  .pc-concl-title { font-size: 11px; }
  .pc-concl-sub { font-size: 9px; }
}
</style>

### TLBs and Process-to-Process Switches

The **TLB (Translation Lookaside Buffer)** is a small CPU cache that stores "virtual address → physical address" lookups. Typical L1 TLBs have **64–128 entries**.

When a process switch occurs, the CR3 register (the page-table base) changes, and the TLB is **fully flushed** (absent PCID/ASID optimizations). Every subsequent memory access then has to walk the page tables again.

**Thread-to-thread switches are cheaper** — threads share an address space, so CR3 doesn't change and the TLB isn't flushed. That's **one concrete reason** "threads are lighter than processes."

### Measuring It

On Linux you can measure with `perf stat`:

```bash
$ perf stat -e context-switches,cpu-migrations,cache-misses -p <PID> sleep 10

Performance counter stats for process id '1234':

     12,345      context-switches
        567      cpu-migrations
 10,234,567      cache-misses
```

On macOS, **Instruments**'s **System Trace** template lets you observe thread scheduling and context switches at microsecond resolution.

On Windows, **Xperf** and **Windows Performance Analyzer** fill the same role.

### A LaMarca & Ladner Observation

As [LaMarca & Ladner 1996, "The Influence of Caches on the Performance of Heaps"](https://dl.acm.org/doi/10.1145/244851.244933) argues, **theoretical asymptotic complexity alone cannot predict real performance**. By the same token, the naive expectation that "more threads = faster" breaks down because of cache/TLB costs.

The rule "optimal thread count = core count" comes from this observation. Beyond that, context switching eats the gains.

---

## Part 7: Game Engine Execution Models

Now we link theory to **game engines**.

### Unity — The Hard Main-Thread Constraint

If you've used Unity, you've likely seen the warning "this API can only be called on the main thread." Most Unity Engine APIs — `Transform.position`, `GameObject.Instantiate()`, `Renderer.sharedMaterial`, etc. — are main-thread only.

**Why?**

The Unity Engine is written in C++ and its internal data structures have **no locks**. Unity's team assumed "all engine calls come from the main thread" by design, eliminating lock-acquisition overhead.

This is a **deliberate trade-off**:
- ✅ Engine calls are very fast (no locks)
- ❌ Multithreaded use is awkward

Unity's answer: **Job System + Burst + Native Containers**. Leave the main thread alone and provide a separate layer that **parallelizes only the data processing**. (Details in Part 13.)

### Unreal Engine — The Task Graph

Unreal Engine uses a **Task Graph** system. "Tasks" submitted by game code form a dependency DAG that the engine spreads across a worker thread pool.

Unreal's worker threads:
- **Game Thread**: game logic (Unity's main thread equivalent)
- **Render Thread**: build rendering commands
- **RHI Thread**: GPU driver calls
- **Worker Threads**: general-purpose work

Tasks specify their target via `ENamedThreads`. Examples: `ENamedThreads::GameThread`, `ENamedThreads::AnyBackgroundHiPriTask`.

### Fiber — Naughty Dog's Approach

[Christian Gyrling's GDC 2015 talk "Parallelizing the Naughty Dog Engine Using Fibers"](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine) is famous for its **fiber**-based engine design.

A **fiber** is a cooperative user-level thread. The OS isn't involved; the application switches them itself. If kernel threads are **workers**, fibers are the **tasks the workers are carrying at the moment**.

- Fiber creation cost: extremely cheap (nanoseconds)
- Fiber switch: save/restore registers only, no kernel involvement
- Can dispatch thousands

Naughty Dog's *The Last of Us Part II* used this system to reliably exploit the PS4's 7 cores. Fibers can be viewed as **one form of the M:N model** (fibers = user threads, kernel threads = workers).

**Windows fiber API**: `CreateFiber`, `SwitchToFiber`. On macOS/Linux you'd use `ucontext.h`'s `makecontext/swapcontext` (legacy, discouraged) or libraries like Boost.Context and `libco`.

### Engine Execution Models Compared

<div class="pt-engine-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Game engine execution models">
  <text x="450" y="28" text-anchor="middle" class="pe-title">Execution models of major engines</text>

  <g class="pe-unity">
    <rect x="30" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="165" y="85" text-anchor="middle" class="pe-heading">Unity</text>
    <rect x="50" y="105" width="230" height="40" rx="4" class="pe-main"/>
    <text x="165" y="128" text-anchor="middle" class="pe-main-label">Main Thread (fixed)</text>
    <text x="165" y="168" text-anchor="middle" class="pe-note">Most Engine APIs</text>
    <text x="165" y="185" text-anchor="middle" class="pe-note">Transform, GameObject, etc.</text>

    <line x1="50" y1="210" x2="280" y2="210" class="pe-sep"/>

    <text x="165" y="235" text-anchor="middle" class="pe-sub-label">Job System (separate layer)</text>
    <g class="pe-workers">
      <rect x="50" y="250" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="75" y="269" text-anchor="middle" class="pe-worker-text">W0</text>
      <rect x="108" y="250" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="133" y="269" text-anchor="middle" class="pe-worker-text">W1</text>
      <rect x="166" y="250" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="191" y="269" text-anchor="middle" class="pe-worker-text">W2</text>
      <rect x="224" y="250" width="56" height="30" rx="3" class="pe-worker"/>
      <text x="252" y="269" text-anchor="middle" class="pe-worker-text">W..N</text>
    </g>

    <text x="165" y="310" text-anchor="middle" class="pe-note">IJob / IJobParallelFor</text>
    <text x="165" y="327" text-anchor="middle" class="pe-note">Burst + Native Containers</text>
    <text x="165" y="370" text-anchor="middle" class="pe-key">Idea: keep engine + parallelize data</text>
  </g>

  <g class="pe-unreal">
    <rect x="315" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="450" y="85" text-anchor="middle" class="pe-heading">Unreal Engine</text>

    <rect x="335" y="105" width="110" height="30" rx="3" class="pe-named"/>
    <text x="390" y="124" text-anchor="middle" class="pe-named-text">Game Thread</text>
    <rect x="455" y="105" width="110" height="30" rx="3" class="pe-named"/>
    <text x="510" y="124" text-anchor="middle" class="pe-named-text">Render Thread</text>
    <rect x="335" y="140" width="110" height="30" rx="3" class="pe-named"/>
    <text x="390" y="159" text-anchor="middle" class="pe-named-text">RHI Thread</text>
    <rect x="455" y="140" width="110" height="30" rx="3" class="pe-named"/>
    <text x="510" y="159" text-anchor="middle" class="pe-named-text">Audio Thread</text>

    <line x1="335" y1="190" x2="565" y2="190" class="pe-sep"/>

    <text x="450" y="215" text-anchor="middle" class="pe-sub-label">Worker Thread Pool</text>
    <g class="pe-workers">
      <rect x="335" y="230" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="360" y="249" text-anchor="middle" class="pe-worker-text">W0</text>
      <rect x="393" y="230" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="418" y="249" text-anchor="middle" class="pe-worker-text">W1</text>
      <rect x="451" y="230" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="476" y="249" text-anchor="middle" class="pe-worker-text">W2</text>
      <rect x="509" y="230" width="56" height="30" rx="3" class="pe-worker"/>
      <text x="537" y="249" text-anchor="middle" class="pe-worker-text">W..N</text>
    </g>

    <text x="450" y="290" text-anchor="middle" class="pe-note">Task Graph: dependency DAG</text>
    <text x="450" y="307" text-anchor="middle" class="pe-note">ENamedThreads picks target</text>
    <text x="450" y="370" text-anchor="middle" class="pe-key">Idea: multiple named threads + pool</text>
  </g>

  <g class="pe-fiber">
    <rect x="600" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="735" y="85" text-anchor="middle" class="pe-heading">Fiber (Naughty Dog)</text>

    <text x="735" y="115" text-anchor="middle" class="pe-sub-label">Worker threads (core count)</text>
    <g class="pe-workers">
      <rect x="620" y="125" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="645" y="144" text-anchor="middle" class="pe-worker-text">W0</text>
      <rect x="678" y="125" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="703" y="144" text-anchor="middle" class="pe-worker-text">W1</text>
      <rect x="736" y="125" width="50" height="30" rx="3" class="pe-worker"/>
      <text x="761" y="144" text-anchor="middle" class="pe-worker-text">W2</text>
      <rect x="794" y="125" width="66" height="30" rx="3" class="pe-worker"/>
      <text x="827" y="144" text-anchor="middle" class="pe-worker-text">W..7</text>
    </g>

    <line x1="620" y1="180" x2="850" y2="180" class="pe-sep"/>

    <text x="735" y="205" text-anchor="middle" class="pe-sub-label">Fiber pool (thousands)</text>
    <g class="pe-fibers">
      <rect x="620" y="220" width="32" height="22" rx="2" class="pe-fiber-el"/>
      <text x="636" y="236" text-anchor="middle" class="pe-fiber-text">F</text>
      <rect x="658" y="220" width="32" height="22" rx="2" class="pe-fiber-el"/>
      <text x="674" y="236" text-anchor="middle" class="pe-fiber-text">F</text>
      <rect x="696" y="220" width="32" height="22" rx="2" class="pe-fiber-el"/>
      <text x="712" y="236" text-anchor="middle" class="pe-fiber-text">F</text>
      <rect x="734" y="220" width="32" height="22" rx="2" class="pe-fiber-el"/>
      <text x="750" y="236" text-anchor="middle" class="pe-fiber-text">F</text>
      <rect x="772" y="220" width="32" height="22" rx="2" class="pe-fiber-el"/>
      <text x="788" y="236" text-anchor="middle" class="pe-fiber-text">F</text>
      <rect x="810" y="220" width="40" height="22" rx="2" class="pe-fiber-el"/>
      <text x="830" y="236" text-anchor="middle" class="pe-fiber-text">...</text>
    </g>

    <text x="735" y="275" text-anchor="middle" class="pe-note">Job = run on a fiber</text>
    <text x="735" y="292" text-anchor="middle" class="pe-note">Cooperative switch, no kernel</text>
    <text x="735" y="309" text-anchor="middle" class="pe-note">Swap fibers on wait</text>
    <text x="735" y="370" text-anchor="middle" class="pe-key">Idea: cooperative user-level scheduling</text>
  </g>
</svg>
</div>

<style>
.pt-engine-container { margin: 2rem 0; text-align: center; }
.pt-engine-container svg { max-width: 100%; height: auto; }
.pe-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.pe-box { fill: #f7fafc; stroke: #cbd5e0; stroke-width: 1.5; stroke-dasharray: 4 4; }
.pe-heading { font-size: 14px; font-weight: 700; fill: #2d3748; }
.pe-main { fill: #fed7d7; stroke: #e53e3e; stroke-width: 2; }
.pe-main-label { font-size: 12px; font-weight: 700; fill: #1a202c; }
.pe-named { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.pe-named-text { font-size: 11px; font-weight: 600; fill: #1a202c; }
.pe-sub-label { font-size: 12px; font-weight: 600; fill: #4a5568; }
.pe-worker { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.2; }
.pe-worker-text { font-size: 11px; fill: #1a202c; }
.pe-fiber-el { fill: #e9d8fd; stroke: #805ad5; stroke-width: 1; }
.pe-fiber-text { font-size: 10px; fill: #1a202c; }
.pe-note { font-size: 10.5px; fill: #4a5568; }
.pe-key { font-size: 11px; font-weight: 700; fill: #2b6cb0; }
.pe-sep { stroke: #a0aec0; stroke-width: 1; stroke-dasharray: 3 3; }

[data-mode="dark"] .pe-title { fill: #e2e8f0; }
[data-mode="dark"] .pe-box { fill: #1a202c; stroke: #4a5568; }
[data-mode="dark"] .pe-heading { fill: #cbd5e0; }
[data-mode="dark"] .pe-main { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .pe-main-label { fill: #e2e8f0; }
[data-mode="dark"] .pe-named { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .pe-named-text { fill: #e2e8f0; }
[data-mode="dark"] .pe-sub-label { fill: #cbd5e0; }
[data-mode="dark"] .pe-worker { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .pe-worker-text { fill: #e2e8f0; }
[data-mode="dark"] .pe-fiber-el { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .pe-fiber-text { fill: #e2e8f0; }
[data-mode="dark"] .pe-note { fill: #cbd5e0; }
[data-mode="dark"] .pe-key { fill: #63b3ed; }
[data-mode="dark"] .pe-sep { stroke: #a0aec0; }

@media (max-width: 768px) {
  .pe-title { font-size: 13px; }
  .pe-heading { font-size: 11px; }
  .pe-main-label { font-size: 10px; }
  .pe-named-text { font-size: 9px; }
  .pe-sub-label { font-size: 10px; }
  .pe-worker-text { font-size: 9px; }
  .pe-note { font-size: 9px; }
  .pe-key { font-size: 9px; }
}
</style>

---

## Part 8: Hands-On — How Are My Threads Actually Running?

Once you know the theory, it's time to **actually look**. All three OSes ship rich tools for observing processes and threads.

### Linux — /proc, ps, top

On Linux everything is exposed in the `/proc` virtual filesystem.

```bash
# List threads of a specific process
$ ls /proc/<PID>/task/
1234  1235  1236  ...

# State of each thread
$ cat /proc/1234/task/1234/status
Name:   myapp
State:  R (running)
Tgid:   1234
Pid:    1234
Threads: 8

# Address-space mappings
$ cat /proc/1234/maps
00400000-00452000 r-xp 00000000 08:01 12345 /usr/bin/myapp
00651000-00652000 r--p 00051000 08:01 12345 /usr/bin/myapp
7f1234000000-7f1234021000 r-xp 00000000 08:01 54321 /lib/x86_64-linux-gnu/libc.so.6
...
```

`top -H` shows per-thread CPU usage.

### macOS — Activity Monitor, ps, Instruments

Activity Monitor is the GUI tool, but more precise data lives in CLI tools.

```bash
# Show thread count for a process
$ ps -M <PID>

# Detailed info
$ sample <PID> 5 -mayDie
```

The most powerful option is **Instruments'** **System Trace** template. It shows a per-P/E-core execution timeline, context-switch events, and blocking causes. It's especially useful on Apple Silicon — visualizing which threads ran on P-cores and which were pushed to E-cores.

### Windows — Process Explorer, WPA

**Process Explorer** (Sysinternals) is a beefed-up Task Manager:
- Visualized process tree
- Thread list per process with stack traces
- Handles, DLLs, memory details

**Windows Performance Analyzer (WPA)** is the Instruments equivalent, analyzing ETW events collected via Xperf.

### Threads in C# — Code Example

```csharp
using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;

class ThreadInspector {
    static void Main() {
        Console.WriteLine($"Current process ID: {Process.GetCurrentProcess().Id}");
        Console.WriteLine($"Managed thread ID: {Thread.CurrentThread.ManagedThreadId}");
        Console.WriteLine($"CPU core count: {Environment.ProcessorCount}");

        // Measure thread-creation cost
        var sw = Stopwatch.StartNew();
        var threads = new Thread[100];
        for (int i = 0; i < 100; i++) {
            threads[i] = new Thread(() => Thread.Sleep(1));
            threads[i].Start();
        }
        foreach (var t in threads) t.Join();
        sw.Stop();
        Console.WriteLine($"100 thread create+join: {sw.ElapsedMilliseconds}ms");

        // ThreadPool.QueueUserWorkItem is much faster
        sw.Restart();
        var countdown = new CountdownEvent(100);
        for (int i = 0; i < 100; i++) {
            ThreadPool.QueueUserWorkItem(_ => {
                Thread.Sleep(1);
                countdown.Signal();
            });
        }
        countdown.Wait();
        sw.Stop();
        Console.WriteLine($"100 ThreadPool items: {sw.ElapsedMilliseconds}ms");
    }
}
```

Run output (approximate on my machine):
```
Current process ID: 12345
Managed thread ID: 1
CPU core count: 8
100 thread create+join: 85ms
100 ThreadPool items: 8ms
```

**10× difference**. That's the practical case for thread pools. .NET's `ThreadPool`, Java's `ExecutorService`, C++'s `std::async` all share the idea — amortize creation cost by reusing threads.

---

## Wrap-up

What this post covered:

**Processes**:
- PCB (`task_struct`, `EPROCESS`, `proc`+`task`) — how the OS tracks a process
- Address space layout: Text, Data, BSS, Heap, Stack, Kernel
- State transitions: New, Ready, Running, Waiting, Terminated

**Process creation**:
- Unix `fork() + exec()` — two steps, Copy-on-Write keeps it fast
- Windows `CreateProcess()` — one step, many parameters
- macOS `posix_spawn()` — iOS-compatible, more efficient
- COW in fork() relies on hardware MMU support

**Threads**:
- Process vs thread: whether the address space is shared is the key
- Shared: text, data, heap, file descriptors
- Private: stack, registers, TLS
- Linux's peculiar philosophy: same struct for process and thread (`clone()`)

**Thread mapping models**:
- 1:1 (Linux NPTL, Windows): standard, true parallelism
- N:1 (old green threads): nearly obsolete
- M:N (Go goroutines, Erlang): millions of concurrent threads, complex runtime

**Context switching**:
- Direct cost: register save/restore ~1–10μs
- Hidden cost: TLB flush, cache pollution, branch predictor pollution
- Process switches are more expensive than thread switches (CR3 change)
- "Thread count = core count" rule

**Game engine execution models**:
- Unity: main thread constraint + Job System (data parallelism)
- Unreal: multiple named threads + Task Graph
- Naughty Dog engine: fiber-based cooperative scheduling

The next post is **Part 9 Scheduling** — when several threads are all Ready, who does the OS hand the CPU to? We look at Linux's CFS → EEVDF, Windows' priority boost, and macOS's QoS-based scheduling. We also cover the 16.67 ms game frame budget and the priority-inversion problem.

---

## References

### Textbooks
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.3 (Processes), Ch.4 (Threads)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — `task_struct` and process management Ch.3
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — modern Linux kernel internals
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — EPROCESS/ETHREAD details
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNU's task/proc dual structure
- Butenhof — *Programming with POSIX Threads*, Addison-Wesley, 1997 — the classic pthreads reference
- Stevens, Rago — *Advanced Programming in the UNIX Environment*, 3rd ed., Addison-Wesley, 2013 — fork/exec in practice
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 multiprocessor engine design

### Papers
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — [DOI](https://dl.acm.org/doi/10.1145/121132.121151) — theoretical basis for the M:N model
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — measuring the hidden cost of context switches
- Engelschall — "Portable Multithreading: The Signal Stack Trick for User-Space Thread Creation", USENIX 2000 — implementing user-level threads
- Kleiman, Smaalders — "The LWP Framework: Building and Debugging Mach Tasks and Threads", Mach Workshop 1990 — Mach's thread model

### Official Docs
- Linux man pages — `clone(2)`, `fork(2)`, `pthread_create(3)`, `proc(5)` — [man7.org](https://man7.org/linux/man-pages/)
- Apple Developer — *Threading Programming Guide* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/Introduction/Introduction.html)
- Apple Developer — *Dispatch* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Microsoft Docs — *Processes and Threads* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/processes-and-threads)
- Microsoft Docs — *Fibers* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/fibers)
- Go Runtime — *The Go Scheduler* (Dmitry Vyukov) — [morsmachine.dk/go-scheduler](https://morsmachine.dk/go-scheduler)

### Game Development / GDC Resources
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Unity Technologies — *C# Job System manual* — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Unreal Engine Documentation — *Task Graph System* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)

### Blogs / Articles
- Raymond Chen — *The Old New Thing* — internals of Win32 CreateProcess
- Linus Torvalds — early comp.os.minix thread-related discussions (1992)
- Dmitry Vyukov — *1024cores.net* — lock-free concurrency reference (including Go scheduler internals)
- Howard Oakley — *The Eclectic Light Company* — macOS thread-observability techniques

### Tools
- Linux: `ps`, `top`, `htop`, `strace`, `perf`, `ftrace`
- macOS: Activity Monitor, `ps`, `sample`, Instruments (System Trace, Time Profiler)
- Windows: Task Manager, Process Explorer, WPA, PerfView
- Cross-platform: Tracy Profiler — great for embedding in games
