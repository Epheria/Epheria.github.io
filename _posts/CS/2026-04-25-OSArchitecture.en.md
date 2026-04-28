---
title: "CS Roadmap Part 7 — OS Architecture: The Forking Paths of Unix, NT, and XNU"
lang: en
date: 2026-04-25 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, unix, linux, windows, macos, xnu, kernel, architecture]
toc: true
toc_sticky: true
math: true
difficulty: intermediate
prerequisites:
  - /posts/MemoryManagement/
tldr:
  - The three OSes differ not by "technical choice" but by "historical path dependency" — decisions made in the 1970s–80s around Unix, VMS, and NeXTSTEP shape today's Linux, Windows, and macOS
  - Their kernel architectures diverge (Linux monolithic, Windows NT hybrid, macOS XNU is a dual structure layering BSD on top of the Mach microkernel)
  - macOS introduced Grand Central Dispatch for thread abstraction, Apple Silicon for heterogeneous P/E cores and 16KB pages, and Rosetta 2 for a hardware TSO mode
  - Executable binary formats (ELF/PE/Mach-O) differ, making cross-compilation complex in game multi-platform builds
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: Why Start with the OS

Stage 1 covered data structures and memory. Arrays and linked lists, hash tables, trees and graphs, and heaps — all of these were stories of **"how to organize data."**

Stage 2 asks a different question.

> **"When two threads use the same variable, why does the program crash only sometimes?"**

To answer this, you need to know how programs execute, who hands out the CPU, and how memory is protected. That is the role of the **operating system (OS)**.

Studying OSes, however, hits an odd wall right away. Textbooks describe things abstractly: "a process has a PCB." But when you actually run `ps` on macOS and open Task Manager on Windows, the three OS worlds look completely different.

- On Linux, creating a process is a two-character call: `fork()`
- On Windows, `CreateProcess()` takes 12 parameters
- On macOS, the same `fork()` sits atop something entirely different — the Mach kernel

These **three-OS differences** are not technical choices but **products of history**. Unix's birth in 1969, Berkeley's fork in 1977, NeXTSTEP's gamble in 1989, Windows NT's design in 1993 — these decisions determine whether your Unity build today produces a `.exe` or an `.app`.

The first post of Stage 2 is about **drawing a map before diving into theory**. We trace the lineage of each OS, why they took different shapes, and what that means for game developers. From the next post onward we dig into concrete topics — processes, threads, scheduling — but each time we compare "this concept is A on Linux and B on Windows," we need to understand the **bones** of these three systems first.

Especially for Mac users among our readers, we cover **macOS-specific sections** in detail: the XNU kernel's unusual dual structure, the design philosophy of Grand Central Dispatch, and the hardware tricks of Apple Silicon — topics pushed to the margins in other OS books, but which take center stage here.

---

## Part 1: The Three OS Lineages — How a 1969 Decision Shaped 2026

### The Birth of Unix (1969)

![Ken Thompson and Dennis Ritchie (1973)](/assets/img/post/cs/os-thompson-ritchie-1973.jpg){: width="500" }
_Ken Thompson (left) and Dennis Ritchie (right), 1973. Creators of Unix and the C language. Source: Jargon File (Public Domain)_

Every story starts at AT&T Bell Labs in New Jersey, 1969. **Ken Thompson** and **Dennis Ritchie** had been working on Multics, a sprawling OS project on the GE-645 mainframe, and came away frustrated. Multics was too ambitious, too slow, too complex.

In a neglected corner of Bell Labs, Thompson found an unused PDP-7 and started building, as a hobby, **a simple OS that stripped away Multics's unnecessary complexity**. Instead of "Multi-", he used "Uni-": **UNICS (Uniplexed Information and Computing Service)**. The name later settled as **Unix**.

Unix's design principles became known as **"the Unix philosophy"**:

1. **Do one thing and do it well**
2. **Everything is a file**
3. **Compose programs (pipe stdout of one as stdin of the next with `|`)**
4. **Text is the universal interface**

In 1973, Ritchie rewrote Unix in **C**. This was decisive. Before this, OSes were written in assembly and couldn't be ported to different hardware. A C-written Unix **opened the era of portable operating systems**.

In the late 1970s, AT&T distributed Unix source code to universities at low cost. **UC Berkeley** took it up enthusiastically, and students began fixing and redistributing Unix. This was the branching point.

### The BSD Branch: Berkeley's Students

From 1977 onward, the Berkeley-derived Unix came to be called **Berkeley Software Distribution (BSD)**. BSD added many features absent from the original Unix:

- **TCP/IP networking stack** (1983, the foundation of the Internet)
- **Berkeley Sockets API** (still the standard for network programming)
- **Improved virtual memory**
- **Fast File System (FFS)**

By the mid-1980s, BSD had become a de facto Unix standard. But AT&T filed licensing lawsuits, and Berkeley endured years of legal disputes. The result was a **fully AT&T-free BSD**, the ancestor of FreeBSD, NetBSD, and OpenBSD.

**A key point**: BSD is fully open source, with a license far more permissive than Linux's GPL. This is why **Apple later chose BSD as the foundation of macOS**. Under GPL, Apple would have had to publish all their modifications; the BSD license imposed no such obligation.

### NeXTSTEP → macOS: The Return of Steve Jobs

![NeXTcube computer (1990)](/assets/img/post/cs/os-next-cube.jpg){: width="600" }
_NeXTcube (1990), held at the Computer History Museum. The NeXTSTEP that ran on this machine is the root of today's macOS. Photo: Michael Hicks, CC BY 2.0_

In 1985, pushed out of Apple, Steve Jobs founded **NeXT**. NeXT's goal was "a high-end workstation for universities and researchers." The OS for that computer was **NeXTSTEP** (1989).

NeXTSTEP's design was unusual:

- The kernel was the **Mach microkernel** (developed at Carnegie Mellon University)
- Layered on top was a **BSD Unix layer** for POSIX compatibility
- The application framework was **Cocoa** (originally AppKit) written in **Objective-C**

This layout was the practical expression of the then-fashionable "microkernels are the future" school. But NeXT computers flopped commercially. The company abandoned hardware to survive and shifted to **porting NeXTSTEP to other hardware** (1993~).

In 1996, something remarkable happened. **Apple acquired NeXT**. At the time Apple was bleeding from the failed "Copland" project meant to succeed Mac OS 9; they had no next-generation OS foundation. Apple debated between BeOS and NeXTSTEP as an outside purchase, and chose NeXTSTEP. The price was roughly **$400 million**.

Steve Jobs returned to Apple with NeXT and became interim CEO in 1997. And **NeXTSTEP became the foundation of macOS**.

- 1999: **Mac OS X Server 1.0** (NeXTSTEP-based)
- 2001: **Mac OS X 10.0 Cheetah** — for general users
- 2007: **iPhone OS** (a shrunken Mac OS X)
- 2016: renamed from "Mac OS X" to **macOS**

So **the kernel running on your MacBook today was sold by 1980s NeXT to 1990s Apple, and its roots trace back to the Mach research project at Carnegie Mellon University**. A design over 30 years old is still alive.

### Linux: A Finnish Student's Hobby Project (1991)

![Linus Torvalds at LinuxCon Europe 2014](/assets/img/post/cs/os-linus-torvalds.jpg){: width="400" }
_Linus Torvalds at LinuxCon Europe 2014, reflecting on how a 23-year-old hobby project became a backbone of the world's infrastructure. Photo: Krd, CC BY-SA 4.0_

In 1991, at the University of Helsinki, **Linus Torvalds** was taking an OS course and using **Minix**, Andrew Tanenbaum's educational OS. Minix was an excellent learning tool but its commercial license restricted use, and Linus wanted something he could freely use on his home 386 PC.

So he started building an OS, **as a hobby**. His August 25 post to comp.os.minix is famous:

> *"Hello everybody out there using minix — I'm doing a (free) operating system (just a hobby, won't be big and professional like gnu)..."*

"Not big, not professional" — that hobby project runs today on the vast majority of the world's servers, smartphones, and supercomputers, 30 years later.

Linux was GPL-licensed from the start and established a model where developers worldwide could contribute. It combined with the GNU project's userland tools (gcc, bash, coreutils) to become a complete OS — which is why strictly it's called **GNU/Linux**.

**Linux's defining trait** — in kernel architecture:

- **Monolithic kernel**: following Unix tradition, all functionality (filesystem, networking, drivers, memory management) lives inside the kernel
- Tanenbaum's 1992 critique that "microkernels are superior" and Linus's retort became one of the famous debates in OS history
- Thirty years later, Linux has evolved into a **partially modularized monolithic kernel** (kernel modules)

### VMS → Windows NT: Dave Cutler's Comeback

Up to here every story is Unix-lineage. But Windows comes from a completely different bloodline.

In the 1970s, **Digital Equipment Corporation (DEC)** dominated the minicomputer market. Its OS was **VMS (Virtual Memory System)**, a high-reliability server OS. VMS's lead architect was **Dave Cutler**.

In 1988, with a new project canceled at DEC, Dave Cutler took his team and **moved to Microsoft**. Bill Gates had proposed: "build the next-generation 32-bit OS to succeed OS/2."

Cutler designed **Windows NT** (NT = New Technology). Internally he carried many VMS ideas over — there's even the joke that shifting each letter of VMS by one gives WNT (V→W, M→N, S→T).

Key characteristics of Windows NT:

- **Hybrid kernel**: it separates subsystems like a microkernel but keeps much in kernel space for performance
- **POSIX subsystem, OS/2 subsystem, Win32 subsystem** — in theory it could support multiple OS APIs concurrently
- **Unicode-first**: Unicode (UTF-16) was assumed from the design phase
- **Multi-architecture support**: x86, MIPS, Alpha, PowerPC (early on)

Windows NT 3.1 shipped in 1993, and NT 4.0, Windows 2000, XP, 7, 10, and 11 all follow the **same NT kernel lineage**. So when you build a Unity project on Windows 11, the kernel underneath traces back to **DEC VMS (1977)**.

Meanwhile, Windows 95, 98, and ME were a **completely separate lineage** — a MS-DOS-based line from Windows 1.0–3.1. Microsoft unified the two lineages on the NT side with Windows XP in 2001, ending the DOS line.

### Lineage Tree

Visualizing the story so far:

<div class="os-lineage-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three OS lineage tree">
  <defs>
    <marker id="os-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="os-arrow-head" />
    </marker>
  </defs>

  <text x="450" y="28" text-anchor="middle" class="os-title">Three OS Lineages — 1969~2026</text>

  <g class="os-lane os-unix-lane">
    <rect x="20" y="55" width="600" height="340" rx="8" class="os-lane-bg"/>
    <text x="320" y="78" text-anchor="middle" class="os-lane-label">Unix line</text>
  </g>

  <g class="os-lane os-vms-lane">
    <rect x="640" y="55" width="240" height="340" rx="8" class="os-lane-bg"/>
    <text x="760" y="78" text-anchor="middle" class="os-lane-label">VMS line</text>
  </g>

  <g class="os-node os-node-root">
    <rect x="230" y="100" width="180" height="40" rx="6"/>
    <text x="320" y="125" text-anchor="middle">Unix (1969)</text>
  </g>

  <g class="os-node os-node-root">
    <rect x="680" y="100" width="160" height="40" rx="6"/>
    <text x="760" y="125" text-anchor="middle">VMS (1977)</text>
  </g>

  <g class="os-node">
    <rect x="50" y="175" width="160" height="36" rx="6"/>
    <text x="130" y="198" text-anchor="middle">BSD (1977)</text>
  </g>

  <g class="os-node">
    <rect x="230" y="175" width="160" height="36" rx="6"/>
    <text x="310" y="198" text-anchor="middle">Minix (1987)</text>
  </g>

  <g class="os-node">
    <rect x="410" y="175" width="200" height="36" rx="6"/>
    <text x="510" y="198" text-anchor="middle">System V (1983)</text>
  </g>

  <g class="os-node">
    <rect x="50" y="240" width="160" height="36" rx="6"/>
    <text x="130" y="263" text-anchor="middle">NeXTSTEP (1989)</text>
  </g>

  <g class="os-node">
    <rect x="230" y="240" width="160" height="36" rx="6"/>
    <text x="310" y="263" text-anchor="middle">Linux (1991)</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="50" y="315" width="160" height="40" rx="6"/>
    <text x="130" y="340" text-anchor="middle">macOS (2001)</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="230" y="315" width="160" height="40" rx="6"/>
    <text x="310" y="340" text-anchor="middle">Android / Server</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="680" y="315" width="160" height="40" rx="6"/>
    <text x="760" y="340" text-anchor="middle">Windows 11</text>
  </g>

  <g class="os-node">
    <rect x="680" y="175" width="160" height="36" rx="6"/>
    <text x="760" y="198" text-anchor="middle">Windows NT (1993)</text>
  </g>

  <g class="os-node os-node-subtle">
    <rect x="680" y="240" width="160" height="36" rx="6"/>
    <text x="760" y="263" text-anchor="middle">Windows 2000 / XP</text>
  </g>

  <path d="M 280 140 L 150 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 320 140 L 310 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 360 140 L 510 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 130 211 L 130 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 310 211 L 310 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 130 276 L 130 315" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 310 276 L 310 315" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 140 L 760 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 211 L 760 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 276 L 760 315" class="os-edge" marker-end="url(#os-arrow)"/>

  <text x="450" y="430" text-anchor="middle" class="os-caption">macOS arrived via BSD → NeXTSTEP; Linux was spawned under Minix's influence; Windows followed an entirely separate VMS path.</text>
  <text x="450" y="455" text-anchor="middle" class="os-caption">Unix bequeathed not technology but <tspan class="os-emph">philosophy and APIs</tspan>. VMS moved to Microsoft with Dave Cutler.</text>
</svg>
</div>

<style>
.os-lineage-container { margin: 2rem 0; text-align: center; }
.os-lineage-container svg { max-width: 100%; height: auto; }
.os-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.os-lane-bg { fill: #f7fafc; stroke: #cbd5e0; stroke-width: 1; }
.os-lane-label { font-size: 13px; fill: #4a5568; font-weight: 600; }
.os-node rect { fill: #edf2f7; stroke: #718096; stroke-width: 1.5; }
.os-node text { font-size: 13px; fill: #1a202c; font-weight: 500; }
.os-node-root rect { fill: #fef5e7; stroke: #d69e2e; stroke-width: 2; }
.os-node-current rect { fill: #d6e6ff; stroke: #3182ce; stroke-width: 2; }
.os-node-subtle rect { fill: #f7fafc; stroke: #a0aec0; stroke-dasharray: 3 3; }
.os-edge { fill: none; stroke: #4a5568; stroke-width: 1.5; }
.os-arrow-head { fill: #4a5568; }
.os-caption { font-size: 12px; fill: #4a5568; }
.os-emph { font-weight: 700; fill: #2b6cb0; }

[data-mode="dark"] .os-title { fill: #e2e8f0; }
[data-mode="dark"] .os-lane-bg { fill: #1a202c; stroke: #4a5568; }
[data-mode="dark"] .os-lane-label { fill: #a0aec0; }
[data-mode="dark"] .os-node rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .os-node text { fill: #e2e8f0; }
[data-mode="dark"] .os-node-root rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .os-node-current rect { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .os-node-subtle rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .os-edge { stroke: #a0aec0; }
[data-mode="dark"] .os-arrow-head { fill: #a0aec0; }
[data-mode="dark"] .os-caption { fill: #a0aec0; }
[data-mode="dark"] .os-emph { fill: #63b3ed; }

@media (max-width: 768px) {
  .os-title { font-size: 14px; }
  .os-node text { font-size: 11px; }
  .os-caption { font-size: 10px; }
}
</style>

---

## Part 2: The Design Philosophies of the Three OSes

Different lineages produce different philosophies. That's why the three OSes respond differently to the same problem — "what to do when memory runs low."

### Linux: Openness and Performance

Linux culture places supreme value on **"hackability."**

- **Everything is exposed**: the entire kernel source is GPL-open, readable and modifiable by anyone
- **Control through the filesystem**: `/proc` and `/sys` expose kernel state as files
  - Examples: `cat /proc/meminfo`, `echo 3 > /proc/sys/vm/drop_caches`
- **Text first**: configuration files are almost all plain text. There is no binary config DB (registry)
- **Performance first**: performance trumps compatibility. For instance, **ABI compatibility is guaranteed but kernel-internal APIs can change at any time**
- **Accepting diversity**: distros (Ubuntu, Arch, Fedora, Alpine…) each carry different philosophies

**Downsides**: fragmentation. We lump everything as "Linux," but Ubuntu and Alpine are almost separate OSes in practice. Desktop UX also lags.

### Windows: Binary Backward Compatibility Taken to the Extreme

Microsoft's culture says, **"a program a customer paid for ten years ago must still run today."**

- **Backward compatibility is near-sacred**: most Windows 95 programs still run on Windows 11
  - Famous anecdote: Windows contains code to work around a specific game's (SimCity) bug inside the kernel. SimCity had a bug reading freed memory; when Windows 95 became Windows NT and that memory was freed immediately, SimCity crashed — so Microsoft added **code that delays memory frees when SimCity is running** (documented on Raymond Chen's blog)
- **Strong binary APIs**: Win32 has been effectively unchanged for 30 years. Higher layers (COM, .NET) maintain backward compatibility too
- **Registry**: system-wide config database — structured key-value rather than text files
- **GUI first**: GUI was designed before the command line. PowerShell arrived later
- **Enterprise focus**: Active Directory, Group Policy, and other large-organization management features are very strong

**Downsides**: accumulated compatibility code makes the kernel **heavy and widens the security surface**. That's why bugs in 30-year-old APIs don't disappear in 2025.

### macOS: Controlled Experience and Hardware Integration

Apple's culture says, **"we design the hardware and the software together."**

- **Vertical integration**: Apple designs CPUs (Apple Silicon), OS (macOS), GUI (Aqua), app frameworks (Cocoa), and dev tools (Xcode) in-house
- **A single official path**: unlike Linux with many distros, unlike Windows with multiple subsystems. Only one official way exists
- **Willingness to make bold transitions**: Apple drops old versions aggressively
  - PowerPC → Intel (2006, Rosetta 1 for transition)
  - 32-bit → 64-bit (2019 macOS Catalina removed 32-bit app support entirely)
  - Intel → Apple Silicon (2020, Rosetta 2 for transition)
- **UX-first**: animations, font rendering, color management are consistent at the OS level
- **Security control**: hierarchical security (Gatekeeper, notarization, SIP) places every app under Apple's vetting

**Downsides**: low freedom. Once Apple drops support, there's no recourse (e.g., Macs older than ~7 years can't run the latest macOS). Compatibility outside the Apple ecosystem is secondary.

### Philosophy Comparison

| Criterion | Linux | Windows | macOS |
|-----------|-------|---------|-------|
| **Core value** | openness, performance | compatibility, enterprise | integration, experience |
| **Kernel modification** | anyone can | only Microsoft | only Apple |
| **Binary compatibility** | kernel ABI only | maintained for 30 years | Rosetta during big transitions |
| **User interface** | many choices (GNOME, KDE…) | Windows Shell (fixed) | Aqua (fixed) |
| **Config storage** | text files | registry | plist (XML/binary) |
| **Package management** | per-distro (apt, dnf, pacman) | MSI/EXE/Store | App Store / Homebrew / dmg |
| **Main usage** | servers, embedded, developers | enterprise, gaming, consumers | creative, developers, consumers |
| **Gaming** | poor (Proton improving) | best | moderate (Metal + Apple Silicon) |

---

## Part 3: Kernel Architecture — Monolithic, Micro, Hybrid

The **kernel** is the heart of the OS. It manages resources between hardware and applications. **How to organize the kernel** has been an OS designer's long-running debate since the 1980s.

### Three Styles

**1. Monolithic kernel**

The entire kernel runs as **one big program**. Filesystem, network stack, drivers, memory management — all run in the same address space.

- **Pros**: fast; internal kernel calls are regular function calls
- **Cons**: a single driver bug can take the whole kernel down; the kernel becomes enormous
- **Examples**: Linux, traditional Unix, FreeBSD

**2. Microkernel**

The kernel holds only the minimum — processes, memory, IPC (inter-process communication). Filesystem, drivers, and so on live as **server processes in user space**.

- **Pros**: modular, stable, secure
- **Cons**: IPC cost makes it slow (messages go through the kernel one extra time)
- **Examples**: pure Mach, MINIX 3, QNX, L4, seL4

**3. Hybrid kernel**

Aims for microkernel modularity but keeps much in **kernel space** for performance.

- **Pros**: compromise between the two
- **Cons**: criticized as "not a real microkernel"
- **Examples**: Windows NT, macOS (XNU)

### Linux — Monolithic at its Peak

The Linux kernel is enormous: over **30 million lines** of source code as of 2024. Internally it is modular — drivers and filesystems can be loaded and unloaded as **kernel modules**.

```bash
# List currently loaded modules on Linux
lsmod

# Load a module
sudo modprobe nvidia

# Unload
sudo rmmod nvidia
```

These modules run in the **same kernel address space**. A malicious or buggy driver module can bring down the entire system. Linux adds additional security layers like module signing and SecureBoot for this reason.

### Windows NT — A Hybrid in Practice

Windows NT separates an upper layer called the **Executive** from a lower layer called the **Microkernel**. But despite the name "Microkernel," drivers, filesystems, and network stack all run in kernel space in practice.

The Windows NT stack:

<div class="nt-container">
<svg viewBox="0 0 860 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Windows NT Layered Architecture">
  <text x="430" y="24" text-anchor="middle" class="nt-title">Windows NT Layered Architecture</text>

  <rect x="40" y="44" width="780" height="70" rx="4" class="nt-user"/>
  <text x="60" y="68" class="nt-layer">User Mode</text>
  <text x="60" y="92" class="nt-sub">Win32 apps · POSIX subsystem · .NET</text>

  <rect x="40" y="130" width="780" height="216" rx="4" class="nt-kernel"/>
  <text x="60" y="154" class="nt-layer">Kernel Mode</text>

  <rect x="60" y="166" width="740" height="92" rx="3" class="nt-inner"/>
  <text x="76" y="184" class="nt-component">Executive</text>
  <text x="76" y="204" class="nt-item">· Object Manager · Process Manager</text>
  <text x="76" y="222" class="nt-item">· Memory Manager · I/O Manager</text>
  <text x="76" y="240" class="nt-item">· Security Reference Monitor</text>

  <rect x="60" y="268" width="740" height="42" rx="3" class="nt-inner"/>
  <text x="76" y="286" class="nt-component">Microkernel</text>
  <text x="76" y="303" class="nt-item">· Thread Scheduler · Interrupt Handler</text>

  <rect x="60" y="318" width="740" height="28" rx="3" class="nt-hal"/>
  <text x="76" y="337" class="nt-component">HAL (Hardware Abstraction Layer)</text>

  <rect x="40" y="362" width="780" height="58" rx="4" class="nt-hw"/>
  <text x="60" y="386" class="nt-layer">Hardware</text>
  <text x="60" y="406" class="nt-sub">CPU · Memory · Disk · Network card</text>
</svg>
</div>

<style>
.nt-container { margin: 2rem 0; text-align: center; }
.nt-container svg { max-width: 100%; height: auto; }
.nt-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.nt-user { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.nt-kernel { fill: #e9d8fd; stroke: #805ad5; stroke-width: 1.5; }
.nt-inner { fill: #faf5ff; stroke: #805ad5; stroke-width: 1; stroke-dasharray: 3 2; }
.nt-hal { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1; stroke-dasharray: 3 2; }
.nt-hw { fill: #edf2f7; stroke: #4a5568; stroke-width: 1.5; }
.nt-layer { font-size: 14px; font-weight: 700; fill: #1a202c; }
.nt-sub { font-size: 12px; fill: #4a5568; }
.nt-component { font-size: 13px; font-weight: 600; fill: #1a202c; }
.nt-item { font-size: 11px; fill: #2d3748; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

[data-mode="dark"] .nt-title { fill: #e2e8f0; }
[data-mode="dark"] .nt-user { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .nt-kernel { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .nt-inner { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .nt-hal { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .nt-hw { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .nt-layer { fill: #e2e8f0; }
[data-mode="dark"] .nt-sub { fill: #cbd5e0; }
[data-mode="dark"] .nt-component { fill: #e2e8f0; }
[data-mode="dark"] .nt-item { fill: #cbd5e0; }

@media (max-width: 768px) {
  .nt-title { font-size: 13px; }
  .nt-layer { font-size: 12px; }
  .nt-sub { font-size: 10px; }
  .nt-component { font-size: 11px; }
  .nt-item { font-size: 9.5px; }
}
</style>

**A curious detail**: early Windows NT had **POSIX and OS/2 subsystems**. In theory, POSIX programs could run on Windows unmodified. It proved impractical — POSIX was removed in Windows 8, and **WSL (Windows Subsystem for Linux)** emerged later via a completely different approach (running a real Linux kernel inside a VM).

### XNU — A Mach + BSD Dual Structure

macOS's kernel is called **XNU** ("X is Not Unix"). XNU has two layers:

1. **Mach 3.0 microkernel** (lower): from CMU research, providing tasks, threads, message passing (Mach ports), and virtual memory
2. **BSD layer** (upper): the Unix implementation ported from FreeBSD — process model (POSIX), network stack, filesystem (HFS+/APFS)
3. **I/O Kit**: driver framework (written in C++)

**Why such an odd structure?**

Originally NeXTSTEP tried a "pure microkernel = Mach" with "BSD as a server process" on top. But that design was **too slow**. Even reading a file had to pass through multiple IPCs between a user-space BSD server and the Mach kernel.

So they compromised: **ported BSD code into the same kernel space as Mach**. The "microkernel" architectural philosophy broke, but performance was secured. That's today's XNU — **theoretically a microkernel, practically a hybrid**.

<div class="os-kernel-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three kernel architectures">
  <text x="450" y="28" text-anchor="middle" class="ok-title">Three Kernel Architectures Compared</text>

  <g class="ok-box">
    <rect x="30" y="60" width="270" height="320" rx="8"/>
    <text x="165" y="82" text-anchor="middle" class="ok-heading">Linux Monolithic</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="50" y="100" width="230" height="50" rx="4"/>
    <text x="165" y="130" text-anchor="middle">User space</text>
  </g>
  <g class="ok-layer ok-layer-kernel">
    <rect x="50" y="160" width="230" height="180" rx="4"/>
    <text x="165" y="185" text-anchor="middle">Kernel space (single large program)</text>
    <text x="165" y="215" text-anchor="middle" class="ok-sublabel">Filesystems</text>
    <text x="165" y="235" text-anchor="middle" class="ok-sublabel">Network stack</text>
    <text x="165" y="255" text-anchor="middle" class="ok-sublabel">Drivers</text>
    <text x="165" y="275" text-anchor="middle" class="ok-sublabel">Memory management</text>
    <text x="165" y="295" text-anchor="middle" class="ok-sublabel">Scheduler</text>
    <text x="165" y="315" text-anchor="middle" class="ok-sublabel">IPC</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="50" y="350" width="230" height="20" rx="4"/>
    <text x="165" y="365" text-anchor="middle">Hardware</text>
  </g>

  <g class="ok-box">
    <rect x="315" y="60" width="270" height="320" rx="8"/>
    <text x="450" y="82" text-anchor="middle" class="ok-heading">Windows NT Hybrid</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="335" y="100" width="230" height="50" rx="4"/>
    <text x="450" y="130" text-anchor="middle">User space (Win32, .NET)</text>
  </g>
  <g class="ok-layer ok-layer-kernel">
    <rect x="335" y="160" width="230" height="80" rx="4"/>
    <text x="450" y="180" text-anchor="middle">Executive</text>
    <text x="450" y="200" text-anchor="middle" class="ok-sublabel">Object / Memory / I/O Manager</text>
    <text x="450" y="220" text-anchor="middle" class="ok-sublabel">Security Reference Monitor</text>
  </g>
  <g class="ok-layer ok-layer-micro">
    <rect x="335" y="250" width="230" height="60" rx="4"/>
    <text x="450" y="275" text-anchor="middle">Microkernel Layer</text>
    <text x="450" y="295" text-anchor="middle" class="ok-sublabel">Scheduler, interrupts</text>
  </g>
  <g class="ok-layer ok-layer-hal">
    <rect x="335" y="320" width="230" height="30" rx="4"/>
    <text x="450" y="340" text-anchor="middle">HAL</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="335" y="355" width="230" height="20" rx="4"/>
    <text x="450" y="370" text-anchor="middle">Hardware</text>
  </g>

  <g class="ok-box">
    <rect x="600" y="60" width="270" height="320" rx="8"/>
    <text x="735" y="82" text-anchor="middle" class="ok-heading">macOS XNU (Mach+BSD)</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="620" y="100" width="230" height="50" rx="4"/>
    <text x="735" y="130" text-anchor="middle">User space (Cocoa, UIKit)</text>
  </g>
  <g class="ok-layer ok-layer-bsd">
    <rect x="620" y="160" width="230" height="70" rx="4"/>
    <text x="735" y="185" text-anchor="middle">BSD Layer</text>
    <text x="735" y="205" text-anchor="middle" class="ok-sublabel">POSIX, networking, filesystems</text>
    <text x="735" y="220" text-anchor="middle" class="ok-sublabel">Process model</text>
  </g>
  <g class="ok-layer ok-layer-mach">
    <rect x="620" y="240" width="230" height="70" rx="4"/>
    <text x="735" y="265" text-anchor="middle">Mach Microkernel</text>
    <text x="735" y="285" text-anchor="middle" class="ok-sublabel">Task, Thread, Mach Port</text>
    <text x="735" y="300" text-anchor="middle" class="ok-sublabel">VM, scheduler</text>
  </g>
  <g class="ok-layer ok-layer-iokit">
    <rect x="620" y="320" width="230" height="30" rx="4"/>
    <text x="735" y="340" text-anchor="middle">I/O Kit (drivers in C++)</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="620" y="355" width="230" height="20" rx="4"/>
    <text x="735" y="370" text-anchor="middle">Hardware</text>
  </g>

  <text x="450" y="405" text-anchor="middle" class="ok-caption">All three share the same user/kernel boundary, but partition inside the kernel differently.</text>
</svg>
</div>

<style>
.os-kernel-container { margin: 2rem 0; text-align: center; }
.os-kernel-container svg { max-width: 100%; height: auto; }
.ok-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.ok-box rect { fill: none; stroke: #cbd5e0; stroke-width: 1.5; stroke-dasharray: 4 4; }
.ok-heading { font-size: 14px; font-weight: 600; fill: #2d3748; }
.ok-layer rect { stroke-width: 1.5; }
.ok-layer text { font-size: 12px; fill: #1a202c; font-weight: 500; }
.ok-sublabel { font-size: 10.5px !important; fill: #4a5568 !important; font-weight: 400 !important; }
.ok-layer-user rect { fill: #e6fffa; stroke: #319795; }
.ok-layer-kernel rect { fill: #fef5e7; stroke: #d69e2e; }
.ok-layer-bsd rect { fill: #e6fffa; stroke: #38b2ac; }
.ok-layer-mach rect { fill: #fed7d7; stroke: #e53e3e; }
.ok-layer-micro rect { fill: #fed7d7; stroke: #e53e3e; }
.ok-layer-iokit rect { fill: #fefcbf; stroke: #d69e2e; }
.ok-layer-hal rect { fill: #f7fafc; stroke: #a0aec0; }
.ok-layer-hw rect { fill: #edf2f7; stroke: #718096; }
.ok-caption { font-size: 12px; fill: #4a5568; }

[data-mode="dark"] .ok-title { fill: #e2e8f0; }
[data-mode="dark"] .ok-box rect { stroke: #4a5568; }
[data-mode="dark"] .ok-heading { fill: #cbd5e0; }
[data-mode="dark"] .ok-layer text { fill: #e2e8f0; }
[data-mode="dark"] .ok-sublabel { fill: #a0aec0 !important; }
[data-mode="dark"] .ok-layer-user rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .ok-layer-kernel rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .ok-layer-bsd rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .ok-layer-mach rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .ok-layer-micro rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .ok-layer-iokit rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .ok-layer-hal rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .ok-layer-hw rect { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .ok-caption { fill: #a0aec0; }

@media (max-width: 768px) {
  .ok-title { font-size: 14px; }
  .ok-heading { font-size: 12px; }
  .ok-layer text { font-size: 10px; }
  .ok-sublabel { font-size: 9px !important; }
}
</style>

> ### Hold on, let's clarify this
>
> **"If microkernels are theoretically good, why does nobody use pure microkernels?"**
>
> The answer is **IPC cost**. Reading a file in a microkernel goes roughly like:
>
> 1. App sends "read me a file" to the kernel
> 2. Kernel forwards that message to the filesystem server process
> 3. Filesystem server sends a message to the disk driver server
> 4. Disk driver actually reads the disk, returns the result to the filesystem server
> 5. Filesystem server returns the result to the app
>
> Each step is a **context switch plus message copy**. On 1980s–90s hardware this cost was unbearable.
>
> A monolithic kernel completes the same work in **a single function call**.
>
> So most practical OSes converged on a hybrid — **"adopt the microkernel philosophy, compromise for performance"**. Pure microkernels survive only in **specialized fields**: real-time systems (QNX) or security-critical systems (seL4 — a mathematically verified kernel).

---

## Part 4: Executable Binary Formats — Same C Code, Different Output

When you build the same C++-based Unity game, the three OSes produce different binaries:

- Linux: **ELF (Executable and Linkable Format)**
- Windows: **PE / PE32+ (Portable Executable)**
- macOS: **Mach-O**

These formats are **completely different**. Not just extension differences — the internal file structures diverge, so a binary from one OS can't run on another without an emulator.

### ELF — The Linux Standard (1988~)

<div class="oe-elf-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELF file layout">
  <text x="450" y="28" text-anchor="middle" class="oe-title">ELF File Layout — Linking View vs Execution View</text>

  <text x="180" y="60" text-anchor="middle" class="oe-heading">Linking View (Sections)</text>
  <text x="180" y="78" text-anchor="middle" class="oe-sub">used by linker / compiler</text>

  <text x="720" y="60" text-anchor="middle" class="oe-heading">Execution View (Segments)</text>
  <text x="720" y="78" text-anchor="middle" class="oe-sub">used by loader at runtime</text>

  <g class="oe-left">
    <rect x="60" y="95" width="240" height="30" rx="3" class="oe-sect oe-sect-header"/>
    <text x="180" y="115" text-anchor="middle" class="oe-sect-label">ELF Header</text>
    <rect x="60" y="130" width="240" height="30" rx="3" class="oe-sect oe-sect-prog"/>
    <text x="180" y="150" text-anchor="middle" class="oe-sect-label">Program Header Table</text>
    <rect x="60" y="170" width="240" height="30" rx="3" class="oe-sect oe-sect-text"/>
    <text x="180" y="190" text-anchor="middle" class="oe-sect-label">.text (executable code)</text>
    <rect x="60" y="205" width="240" height="30" rx="3" class="oe-sect oe-sect-ro"/>
    <text x="180" y="225" text-anchor="middle" class="oe-sect-label">.rodata (const / strings)</text>
    <rect x="60" y="245" width="240" height="30" rx="3" class="oe-sect oe-sect-data"/>
    <text x="180" y="265" text-anchor="middle" class="oe-sect-label">.data (init globals)</text>
    <rect x="60" y="280" width="240" height="30" rx="3" class="oe-sect oe-sect-bss"/>
    <text x="180" y="300" text-anchor="middle" class="oe-sect-label">.bss (zero-init, size only)</text>
    <rect x="60" y="320" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="337" text-anchor="middle" class="oe-sect-label-sm">.symtab (symbol table)</text>
    <rect x="60" y="350" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="367" text-anchor="middle" class="oe-sect-label-sm">.strtab (string table)</text>
    <rect x="60" y="380" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="397" text-anchor="middle" class="oe-sect-label-sm">.debug_* (DWARF)</text>
    <rect x="60" y="410" width="240" height="30" rx="3" class="oe-sect oe-sect-shdr"/>
    <text x="180" y="430" text-anchor="middle" class="oe-sect-label">Section Header Table</text>
  </g>

  <g class="oe-right">
    <rect x="600" y="95" width="240" height="30" rx="3" class="oe-seg oe-seg-header"/>
    <text x="720" y="115" text-anchor="middle" class="oe-seg-label">ELF Header</text>
    <rect x="600" y="130" width="240" height="30" rx="3" class="oe-seg oe-seg-prog"/>
    <text x="720" y="150" text-anchor="middle" class="oe-seg-label">Program Header Table</text>
    <rect x="600" y="170" width="240" height="65" rx="3" class="oe-seg oe-seg-loadrx"/>
    <text x="720" y="195" text-anchor="middle" class="oe-seg-label">LOAD Segment #1</text>
    <text x="720" y="212" text-anchor="middle" class="oe-seg-sub">Read + Execute</text>
    <text x="720" y="228" text-anchor="middle" class="oe-seg-sub">.text + .rodata</text>
    <rect x="600" y="245" width="240" height="65" rx="3" class="oe-seg oe-seg-loadrw"/>
    <text x="720" y="270" text-anchor="middle" class="oe-seg-label">LOAD Segment #2</text>
    <text x="720" y="287" text-anchor="middle" class="oe-seg-sub">Read + Write</text>
    <text x="720" y="303" text-anchor="middle" class="oe-seg-sub">.data + .bss</text>
    <rect x="600" y="320" width="240" height="85" rx="3" class="oe-seg oe-seg-ignored"/>
    <text x="720" y="345" text-anchor="middle" class="oe-seg-label">(not loaded)</text>
    <text x="720" y="362" text-anchor="middle" class="oe-seg-sub">symbol table, debug info</text>
    <text x="720" y="378" text-anchor="middle" class="oe-seg-sub">stripped in production</text>
    <text x="720" y="395" text-anchor="middle" class="oe-seg-sub">or kept for debugging</text>
    <rect x="600" y="410" width="240" height="30" rx="3" class="oe-seg oe-seg-meta"/>
    <text x="720" y="430" text-anchor="middle" class="oe-seg-label-sm">Section Header Table (optional at runtime)</text>
  </g>

  <g class="oe-conn">
    <line x1="300" y1="185" x2="600" y2="195" class="oe-line oe-line-rx"/>
    <line x1="300" y1="220" x2="600" y2="210" class="oe-line oe-line-rx"/>
    <line x1="300" y1="260" x2="600" y2="270" class="oe-line oe-line-rw"/>
    <line x1="300" y1="295" x2="600" y2="285" class="oe-line oe-line-rw"/>
    <line x1="300" y1="333" x2="600" y2="360" class="oe-line oe-line-ignored"/>
    <line x1="300" y1="363" x2="600" y2="372" class="oe-line oe-line-ignored"/>
    <line x1="300" y1="393" x2="600" y2="384" class="oe-line oe-line-ignored"/>
  </g>

  <text x="450" y="480" text-anchor="middle" class="oe-note">Same file, two perspectives: the linker groups by section, the loader groups by segment (permission).</text>
  <text x="450" y="500" text-anchor="middle" class="oe-note">A production binary can omit the Section Header Table and strip .symtab / .debug_* to shrink size.</text>
</svg>
</div>

<style>
.oe-elf-container { margin: 2rem 0; text-align: center; }
.oe-elf-container svg { max-width: 100%; height: auto; }
.oe-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.oe-heading { font-size: 13px; font-weight: 700; fill: #2d3748; }
.oe-sub { font-size: 11px; fill: #4a5568; font-style: italic; }
.oe-sect, .oe-seg { stroke-width: 1.5; }
.oe-sect-header, .oe-seg-header { fill: #e9d8fd; stroke: #805ad5; }
.oe-sect-prog, .oe-seg-prog { fill: #bee3f8; stroke: #3182ce; }
.oe-sect-text { fill: #faf5ff; stroke: #553c9a; }
.oe-sect-ro { fill: #e9d8fd; stroke: #805ad5; }
.oe-sect-data { fill: #c6f6d5; stroke: #38a169; }
.oe-sect-bss { fill: #c6f6d5; stroke: #38a169; stroke-dasharray: 4 3; }
.oe-sect-meta, .oe-seg-meta { fill: #edf2f7; stroke: #718096; }
.oe-sect-shdr { fill: #fed7d7; stroke: #e53e3e; }
.oe-seg-loadrx { fill: #bee3f8; stroke: #3182ce; }
.oe-seg-loadrw { fill: #c6f6d5; stroke: #38a169; }
.oe-seg-ignored { fill: #f7fafc; stroke: #a0aec0; stroke-dasharray: 4 4; }
.oe-sect-label, .oe-seg-label { font-size: 11px; font-weight: 600; fill: #1a202c; }
.oe-sect-label-sm, .oe-seg-label-sm { font-size: 10px; fill: #2d3748; }
.oe-seg-sub { font-size: 10px; fill: #4a5568; }
.oe-line { stroke-width: 1.2; fill: none; }
.oe-line-rx { stroke: #3182ce; opacity: 0.6; }
.oe-line-rw { stroke: #38a169; opacity: 0.6; }
.oe-line-ignored { stroke: #a0aec0; opacity: 0.5; stroke-dasharray: 3 2; }
.oe-note { font-size: 11px; fill: #4a5568; font-style: italic; }

[data-mode="dark"] .oe-title { fill: #e2e8f0; }
[data-mode="dark"] .oe-heading { fill: #cbd5e0; }
[data-mode="dark"] .oe-sub { fill: #a0aec0; }
[data-mode="dark"] .oe-sect-header, [data-mode="dark"] .oe-seg-header { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-prog, [data-mode="dark"] .oe-seg-prog { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .oe-sect-text { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-ro { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-data { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .oe-sect-bss { fill: #22543d; stroke: #68d391; stroke-dasharray: 4 3; }
[data-mode="dark"] .oe-sect-meta, [data-mode="dark"] .oe-seg-meta { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .oe-sect-shdr { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .oe-seg-loadrx { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .oe-seg-loadrw { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .oe-seg-ignored { fill: #1a202c; stroke: #718096; stroke-dasharray: 4 4; }
[data-mode="dark"] .oe-sect-label, [data-mode="dark"] .oe-seg-label { fill: #e2e8f0; }
[data-mode="dark"] .oe-sect-label-sm, [data-mode="dark"] .oe-seg-label-sm { fill: #cbd5e0; }
[data-mode="dark"] .oe-seg-sub { fill: #cbd5e0; }
[data-mode="dark"] .oe-line-rx { stroke: #63b3ed; }
[data-mode="dark"] .oe-line-rw { stroke: #68d391; }
[data-mode="dark"] .oe-line-ignored { stroke: #a0aec0; }
[data-mode="dark"] .oe-note { fill: #a0aec0; }

@media (max-width: 768px) {
  .oe-title { font-size: 13px; }
  .oe-heading { font-size: 11px; }
  .oe-sub { font-size: 9.5px; }
  .oe-sect-label, .oe-seg-label { font-size: 9.5px; }
  .oe-sect-label-sm, .oe-seg-label-sm { font-size: 8.5px; }
  .oe-seg-sub { font-size: 8.5px; }
  .oe-note { font-size: 9.5px; }
}
</style>

**Executable and Linkable Format** was introduced in System V and is now used by most Unix-like systems (Linux, FreeBSD, Solaris).

ELF file structure:

<div class="bf-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELF file structure">
  <text x="450" y="30" text-anchor="middle" class="bf-title">ELF File Structure (Linux)</text>

  <rect x="160" y="56" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="77" text-anchor="middle" class="bf-label">ELF Header</text>
  <text x="480" y="77" class="bf-note">magic bytes 0x7f 'E' 'L' 'F'</text>

  <rect x="160" y="102" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="123" text-anchor="middle" class="bf-label">Program Header Table</text>
  <text x="480" y="123" class="bf-note">memory mapping info for execution</text>

  <rect x="160" y="148" width="300" height="258" rx="3" class="bf-group"/>
  <text x="170" y="166" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="176" width="276" height="28" rx="2" class="bf-text"/>
  <text x="310" y="194" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="194" class="bf-note">executable code</text>

  <rect x="172" y="208" width="276" height="28" rx="2" class="bf-ro"/>
  <text x="310" y="226" text-anchor="middle" class="bf-sect">.rodata</text>
  <text x="480" y="226" class="bf-note">read-only data (string literals etc.)</text>

  <rect x="172" y="240" width="276" height="28" rx="2" class="bf-data"/>
  <text x="310" y="258" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="258" class="bf-note">initialized global variables</text>

  <rect x="172" y="272" width="276" height="28" rx="2" class="bf-bss"/>
  <text x="310" y="290" text-anchor="middle" class="bf-sect">.bss</text>
  <text x="480" y="290" class="bf-note">zero-initialized globals (size only in file)</text>

  <rect x="172" y="304" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="322" text-anchor="middle" class="bf-sect">.symtab</text>
  <text x="480" y="322" class="bf-note">symbol table</text>

  <rect x="172" y="336" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="354" text-anchor="middle" class="bf-sect">.strtab</text>
  <text x="480" y="354" class="bf-note">string table</text>

  <rect x="172" y="368" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="386" text-anchor="middle" class="bf-sect">.debug_*</text>
  <text x="480" y="386" class="bf-note">DWARF debug info</text>

  <rect x="160" y="420" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="441" text-anchor="middle" class="bf-label">Section Header Table</text>
  <text x="480" y="441" class="bf-note">section location / attribute info</text>
</svg>
</div>

<style>
.bf-container { margin: 2rem 0; text-align: center; }
.bf-container svg { max-width: 100%; height: auto; }
.bf-title { font-size: 15px; font-weight: 700; fill: #1a202c; }
.bf-meta { fill: #e9d8fd; stroke: #805ad5; stroke-width: 1.5; }
.bf-group { fill: none; stroke: #805ad5; stroke-width: 1; stroke-dasharray: 4 3; }
.bf-group-label { font-size: 11px; font-weight: 700; fill: #805ad5; letter-spacing: 0.5px; }
.bf-text { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.2; }
.bf-ro { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.2; }
.bf-data { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.2; }
.bf-bss { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.2; stroke-dasharray: 4 3; }
.bf-aux { fill: #edf2f7; stroke: #718096; stroke-width: 1; }
.bf-rsrc { fill: #fefcbf; stroke: #d69e2e; stroke-width: 1.2; }
.bf-reloc { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1.2; stroke-dasharray: 4 3; }
.bf-dos { fill: #fbd38d; stroke: #c05621; stroke-width: 1.5; }
.bf-stub { fill: #feebc8; stroke: #c05621; stroke-width: 1; stroke-dasharray: 3 2; }
.bf-load { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.2; }
.bf-seg { fill: none; stroke: #3182ce; stroke-width: 1; stroke-dasharray: 4 3; }
.bf-linkedit { fill: #e6fffa; stroke: #319795; stroke-width: 1.2; }
.bf-arch-x86 { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.bf-arch-arm { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.bf-label { font-size: 12px; font-weight: 600; fill: #1a202c; }
.bf-sect { font-size: 11.5px; fill: #1a202c; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.bf-sub { font-size: 10.5px; fill: #4a5568; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.bf-note { font-size: 11px; fill: #4a5568; }

[data-mode="dark"] .bf-title { fill: #e2e8f0; }
[data-mode="dark"] .bf-meta { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .bf-group { stroke: #b794f4; }
[data-mode="dark"] .bf-group-label { fill: #b794f4; }
[data-mode="dark"] .bf-text { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-ro { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .bf-data { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .bf-bss { fill: #22543d; stroke: #68d391; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-aux { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .bf-rsrc { fill: #5c4a10; stroke: #ecc94b; }
[data-mode="dark"] .bf-reloc { fill: #742a2a; stroke: #fc8181; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-dos { fill: #5c2f0c; stroke: #dd6b20; }
[data-mode="dark"] .bf-stub { fill: #5c2f0c; stroke: #dd6b20; stroke-dasharray: 3 2; }
[data-mode="dark"] .bf-load { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-seg { stroke: #63b3ed; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-linkedit { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .bf-arch-x86 { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-arch-arm { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .bf-label { fill: #e2e8f0; }
[data-mode="dark"] .bf-sect { fill: #e2e8f0; }
[data-mode="dark"] .bf-sub { fill: #cbd5e0; }
[data-mode="dark"] .bf-note { fill: #cbd5e0; }

@media (max-width: 768px) {
  .bf-title { font-size: 12px; }
  .bf-label { font-size: 10px; }
  .bf-sect { font-size: 9.5px; }
  .bf-sub { font-size: 9px; }
  .bf-note { font-size: 9px; }
  .bf-group-label { font-size: 9.5px; }
}
</style>

Inspecting ELF:

```bash
$ file /bin/ls
/bin/ls: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), ...

$ readelf -h /bin/ls
ELF Header:
  Magic:   7f 45 4c 46 02 01 01 00 00 00 00 00 00 00 00 00
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           Advanced Micro Devices X86-64
```

### PE — The Windows Lineage (1993~)

**Portable Executable** is the format introduced by Windows NT. It derives from Unix's COFF (Common Object File Format) but has many Microsoft-specific extensions.

PE file structure:

<div class="bf-container">
<svg viewBox="0 0 900 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PE file structure">
  <text x="450" y="30" text-anchor="middle" class="bf-title">PE File Structure (Windows)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-dos"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">DOS Header (MZ)</text>
  <text x="480" y="75" class="bf-note">16-bit era compatibility vestige</text>

  <rect x="160" y="90" width="300" height="30" rx="3" class="bf-stub"/>
  <text x="310" y="109" text-anchor="middle" class="bf-label">DOS Stub</text>
  <text x="480" y="109" class="bf-note">"This program cannot be run in DOS mode"</text>

  <rect x="160" y="124" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="143" text-anchor="middle" class="bf-label">PE Signature "PE\0\0"</text>

  <rect x="160" y="158" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="177" text-anchor="middle" class="bf-label">COFF Header</text>
  <text x="480" y="177" class="bf-note">CPU architecture · section count</text>

  <rect x="160" y="192" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="211" text-anchor="middle" class="bf-label">Optional Header</text>
  <text x="480" y="211" class="bf-note">entry point · image base · subsystem</text>

  <rect x="160" y="226" width="300" height="30" rx="3" class="bf-aux"/>
  <text x="310" y="245" text-anchor="middle" class="bf-label">Section Headers</text>

  <rect x="160" y="266" width="300" height="174" rx="3" class="bf-group"/>
  <text x="170" y="284" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="292" width="276" height="26" rx="2" class="bf-text"/>
  <text x="310" y="309" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="309" class="bf-note">executable code</text>

  <rect x="172" y="322" width="276" height="26" rx="2" class="bf-ro"/>
  <text x="310" y="339" text-anchor="middle" class="bf-sect">.rdata</text>
  <text x="480" y="339" class="bf-note">read-only data · import table</text>

  <rect x="172" y="352" width="276" height="26" rx="2" class="bf-data"/>
  <text x="310" y="369" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="369" class="bf-note">initialized global variables</text>

  <rect x="172" y="382" width="276" height="26" rx="2" class="bf-rsrc"/>
  <text x="310" y="399" text-anchor="middle" class="bf-sect">.rsrc</text>
  <text x="480" y="399" class="bf-note">icons · version info · resources</text>

  <rect x="172" y="412" width="276" height="26" rx="2" class="bf-reloc"/>
  <text x="310" y="429" text-anchor="middle" class="bf-sect">.reloc</text>
  <text x="480" y="429" class="bf-note">relocation info</text>
</svg>
</div>

An amusing detail: PE files still start with a **DOS-compatible "MZ" magic** (MZ are the initials of DOS developer Mark Zbikowski). A format designed in 1993 **still carries a 1981-era DOS-compatibility string in 2026**. This epitomizes Windows's backward-compatibility culture.

### Mach-O — The macOS Format

**Mach-O (Mach Object)** was designed alongside the Mach kernel. It started with NeXTSTEP and is still used by macOS and iOS.

Mach-O file structure:

<div class="bf-container">
<svg viewBox="0 0 900 490" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mach-O file structure">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Mach-O File Structure (macOS / iOS)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">Header</text>
  <text x="480" y="75" class="bf-note">magic 0xFEEDFACE (32) / 0xFEEDFACF (64)</text>

  <rect x="160" y="98" width="300" height="134" rx="3" class="bf-meta"/>
  <text x="310" y="116" text-anchor="middle" class="bf-label">Load Commands</text>
  <text x="480" y="116" class="bf-note">instructions for the loader</text>
  <text x="176" y="140" class="bf-sub">LC_SEGMENT</text>
  <text x="306" y="140" class="bf-sub">define memory segments</text>
  <text x="176" y="160" class="bf-sub">LC_DYLD_INFO</text>
  <text x="306" y="160" class="bf-sub">dynamic linker info</text>
  <text x="176" y="180" class="bf-sub">LC_SYMTAB</text>
  <text x="306" y="180" class="bf-sub">symbol table</text>
  <text x="176" y="200" class="bf-sub">LC_LOAD_DYLIB</text>
  <text x="306" y="200" class="bf-sub">required libraries</text>
  <text x="176" y="220" class="bf-sub">LC_CODE_SIGNATURE</text>
  <text x="306" y="220" class="bf-sub">code signature</text>

  <rect x="160" y="244" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="262" class="bf-group-label">SEGMENT · __TEXT</text>
  <rect x="172" y="272" width="276" height="24" rx="2" class="bf-text"/>
  <text x="310" y="289" text-anchor="middle" class="bf-sect">__text</text>
  <text x="480" y="289" class="bf-note">executable code</text>
  <rect x="172" y="300" width="276" height="24" rx="2" class="bf-ro"/>
  <text x="310" y="317" text-anchor="middle" class="bf-sect">__cstring</text>
  <text x="480" y="317" class="bf-note">C string constants</text>

  <rect x="160" y="340" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="358" class="bf-group-label">SEGMENT · __DATA</text>
  <rect x="172" y="368" width="276" height="24" rx="2" class="bf-data"/>
  <text x="310" y="385" text-anchor="middle" class="bf-sect">__data</text>
  <text x="480" y="385" class="bf-note">initialized global variables</text>
  <rect x="172" y="396" width="276" height="24" rx="2" class="bf-bss"/>
  <text x="310" y="413" text-anchor="middle" class="bf-sect">__bss</text>
  <text x="480" y="413" class="bf-note">zero-initialized globals</text>

  <rect x="160" y="436" width="300" height="30" rx="3" class="bf-linkedit"/>
  <text x="310" y="455" text-anchor="middle" class="bf-label">Segment: __LINKEDIT</text>
  <text x="480" y="455" class="bf-note">symbols · relocations · signatures</text>
</svg>
</div>

**Universal Binary (Fat Binary)**: one file can contain Mach-O for several architectures.

<div class="bf-container">
<svg viewBox="0 0 900 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Universal Binary (Fat Binary) structure">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Universal Binary (Fat Binary)</text>

  <rect x="160" y="50" width="300" height="32" rx="3" class="bf-meta"/>
  <text x="310" y="71" text-anchor="middle" class="bf-label">Fat Header</text>
  <text x="480" y="71" class="bf-note">embedded architecture list · offsets</text>

  <rect x="160" y="90" width="300" height="46" rx="3" class="bf-arch-x86"/>
  <text x="310" y="110" text-anchor="middle" class="bf-label">Arch 0: x86_64</text>
  <text x="310" y="128" text-anchor="middle" class="bf-sub">(full Mach-O)</text>
  <text x="480" y="119" class="bf-note">for Intel Mac</text>

  <rect x="160" y="144" width="300" height="46" rx="3" class="bf-arch-arm"/>
  <text x="310" y="164" text-anchor="middle" class="bf-label">Arch 1: arm64</text>
  <text x="310" y="182" text-anchor="middle" class="bf-sub">(full Mach-O)</text>
  <text x="480" y="173" class="bf-note">for Apple Silicon</text>
</svg>
</div>

This is the structure that lets **"the same app run natively on Intel Macs and M1 Macs"**. The PowerPC→Intel transition in 2006 and the Intel→Apple Silicon transition in 2020 were both done the same way.

### What It Means for Multi-platform Builds

Engines like Unity and Unreal advertise "build once, run on many platforms," but the reality is that **the engine rebuilds internally for each of the three formats**. When you switch platform in Build Settings:

- **Windows**: compile with MSVC or clang-cl → emit PE32+, link Windows SDK
- **macOS**: clang/Xcode toolchain → emit Mach-O, link Cocoa frameworks (Universal Binary for Intel+ARM)
- **Linux**: gcc or clang → emit ELF, link glibc

Same C++ code, **entirely different final binaries**. That's why dropping a `.exe` built on Windows onto macOS does nothing.

**Another gotcha**: game engines use many dynamic libraries.

- Windows: `.dll`
- macOS: `.dylib` or `.framework` (bundles)
- Linux: `.so`

Each needs its **own build per platform**. That's a common reason Unity native plugins only ship for Windows.

---

## Part 5: macOS-specific Stories — What Apple Built Up

Now a section that will be especially fun for Mac users. We dig into **Apple-proprietary systems** that set macOS apart.

### The Behind-the-Scenes of XNU

We said XNU is a Mach + BSD dual structure. But there's a history of **failure and compromise** behind it.

**Phase 1 (1985~88) — The dream of pure Mach**
The Mach project at Carnegie Mellon was an academic experiment to *"reimplement BSD Unix features as a microkernel."* Rashid and students produced Mach 2.0, which was actually a **hybrid** where "Mach + BSD server" cohabited in one kernel.

**Phase 2 (1990) — The attempt at Mach 3.0**
Mach 3.0 aimed at a pure microkernel by completely separating BSD code into **user-space servers**. Theoretically elegant, but performance was dreadful. OSF/1, a commercial OS on Mach 3.0, failed in the market.

**Phase 3 (1989~96) — NeXTSTEP's pragmatic choice**
NeXT originally built NeXTSTEP on Mach 2.0, merging some BSD features directly into the Mach kernel for performance. That became NeXTSTEP's kernel foundation.

**Phase 4 (2000~) — XNU**
When Apple pulled NeXTSTEP into macOS, they significantly updated the BSD side pulling from **FreeBSD 5.x**. The result is XNU. That's why `uname -a` on macOS reports "Darwin" — **Darwin = XNU + BSD userland = the open-source portion of macOS**.

```bash
$ uname -a
Darwin MacBook.local 23.0.0 Darwin Kernel Version 23.0.0: ...
```

Apple publishes Darwin as open source. You can download XNU sources from [opensource.apple.com](https://opensource.apple.com) and build them yourself.

### Mach Port — The Root of Everything

The central abstraction of the Mach microkernel is the **port**. A Mach port plays a role similar to Unix's file descriptor but is far broader.

- **Inter-process communication**: messages are sent and received via ports
- **Signal handling**: Unix signals are translated into Mach port messages
- **IOKit drivers**: user-space apps communicate with drivers via ports
- **Bootstrap**: name services (provided by `launchd`) also live on ports

**Why does this matter?** macOS's security model and IPC are all built on top of ports. App sandboxes, for example, are implemented as "this app may only use these specific ports." iOS's strict app isolation is fundamentally Mach-port-based.

```c
/* Sending a message via a Mach port (heavily simplified) */
mach_port_t target_port = ...;
mach_msg_send(&msg_header);
```

Developers rarely touch this directly, but it runs inside tools like the lldb debugger and Xcode Instruments.

### Grand Central Dispatch (2009)

In **macOS 10.6 Snow Leopard (2009)**, Apple introduced Grand Central Dispatch (GCD, libdispatch). It was Apple's answer to the multi-core era.

**Problems with traditional thread models**:
```c
/* Traditional C/Unix style */
pthread_t thread;
pthread_create(&thread, NULL, worker_function, arg);
pthread_join(thread, NULL);
```
- Developer manages thread count, lifetime, synchronization manually
- Without knowing core count, you create too many or too few
- Synchronization primitives are easy to misuse

**GCD's answer**: throw work onto a **queue** instead of a thread.

```swift
/* Swift */
DispatchQueue.global(qos: .userInitiated).async {
    /* this runs in the background */
    let result = heavyComputation()
    DispatchQueue.main.async {
        updateUI(result)
    }
}
```

The OS **automatically** creates and reuses threads given core count and system load. The developer only specifies "what priority to run at" (QoS: User Interactive, User Initiated, Utility, Background).

**GCD was open-sourced as libdispatch** and is used by Swift on Linux. That is, GCD-style programming is available on other languages and platforms.

**From a game developer's angle**: Unity's Job System shares GCD's philosophy — "delegate work, not threads, to a scheduler." We cover this in detail in Part 13.

### launchd — Five Years Before systemd

In macOS 10.4 Tiger (2005), Apple introduced **launchd**, unifying Unix's traditional init system (SysVinit, cron, xinetd, inetd, atd — historically spread across many daemons) into **one process**.

Before launchd in Unix:
- `init` (PID 1): system boot init
- `cron`: periodic jobs
- `atd`: one-shot scheduled jobs
- `inetd`: start daemons on network connection
- Each daemon runs separately

launchd consolidates these into **a universal daemon manager**:
- runs as PID 1, manages all system processes
- services are defined via XML plist files
- supports **on-demand launches** based on file access or network activity
- auto-restart on failure

**Historical significance**: Linux's **systemd** (Lennart Poettering, 2010) was inspired by launchd. When systemd landed, the Linux community criticized it as "against Unix philosophy" — but launchd had already taken the same approach five years earlier, quietly running well on macOS.

Managed via `launchctl`:

```bash
# List running services
launchctl list

# Start a service
launchctl load ~/Library/LaunchAgents/com.example.myservice.plist

# Stop it
launchctl unload ~/Library/LaunchAgents/com.example.myservice.plist
```

### Apple Silicon — Heterogeneous P/E Cores

In 2020 Apple introduced its in-house CPU **M1 (Apple Silicon)** to the Mac. M1 is ARM64-based, but with a **distinctive structure unlike a typical ARM server**.

**P-core (Performance) and E-core (Efficiency)**

M1 has **two core types** running the same ARM ISA:

- **P-core "Firestorm"**: high performance, high power. Games, compilation, rendering
- **E-core "Icestorm"**: low performance, low power. Background tasks, system daemons, battery saving

| Spec | P-core | E-core |
|------|--------|--------|
| Clock | 3.2 GHz | 2.0 GHz |
| L1 cache | 192KB | 128KB |
| L2 cache | shared 12MB | shared 4MB |
| Power | ~15W | ~1W |
| Perf ratio | ~100% | ~25% |
| M1 count | 4 | 4 |

**macOS's QoS-based scheduling**: GCD's QoS classes reappear here.

- **User Interactive / User Initiated** QoS → mostly P-cores
- **Utility** QoS → context-dependent
- **Background** QoS → mostly E-cores

A developer writes `DispatchQueue.global(qos: .userInitiated)`, and **the OS decides which cores to run on**. This reflects Apple's philosophy of "developers shouldn't need to know hardware details."

**16KB page size**

Another oddity of Apple Silicon: the **page size is 16KB**. The Linux/Windows standard is **4KB**.

- **Pros**: fewer TLB (Translation Lookaside Buffer) misses, better performance for large-memory apps
- **Cons**: changed memory alignment requirements. Legacy apps assuming 4KB pages can break

Early in the 2020 Apple Silicon transition, **Homebrew, Docker, and some binary compatibility tools** struggled with the 16KB page issue. Most are resolved today, but Unity native plugin developers should still be careful with page alignment in calls like `mprotect()`.

### Rosetta 2 — Not an Emulator, a Translator

One reason the Apple Silicon transition succeeded is **Rosetta 2**. It runs x86_64 Mach-O binaries on ARM64, achieving **70–80% of native performance**. Impressive.

**Rosetta 2 is not a JIT emulator**. When an app is installed (or on first launch), x86 instructions are **AOT-translated** (Ahead-of-Time) to ARM and cached as a file. Subsequent runs execute an already-translated ARM binary and are fast.

**The decisive trick — hardware TSO mode**: this is the most interesting part.

x86 has a **strong memory model (TSO, Total Store Order)**. The order in which one CPU's writes become visible to other CPUs closely matches program order.

ARM has a **weak memory model**. The CPU may **freely reorder** memory reads/writes for performance. Programmers must insert explicit memory barriers to guarantee order.

The problem arises when **programs written for x86** implicitly assume TSO. Translating such programs naively to ARM introduces **new race conditions** caused by ARM's reordering.

Apple's answer: **they put a "TSO mode" into the M1's hardware**. When a Rosetta 2 translated binary runs, the CPU sets a "this thread runs in TSO mode" flag. Then the ARM CPU behaves with **x86-like strong memory ordering**.

> 💡 This topic returns in Part 12 (Memory Models and Atomics). For now, remember that **Apple pulled off a compatibility trick at the hardware level**.

**Limits of Rosetta 2**:
- Latest x86 extensions like AVX-512 are not translated
- Kernel extensions (.kext) can't run under Rosetta — the OS itself must be native
- Programs with built-in JITs (Chrome V8 etc.) incur double translation (Rosetta + JIT) and can be slow

### XNU Internals

<div class="os-xnu-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="XNU kernel internals">
  <text x="450" y="28" text-anchor="middle" class="xu-title">XNU Internals — Mach + BSD + I/O Kit</text>

  <g class="xu-user">
    <rect x="60" y="60" width="780" height="70" rx="8"/>
    <text x="450" y="88" text-anchor="middle" class="xu-heading">User Space</text>
    <text x="210" y="112" text-anchor="middle" class="xu-sub">Cocoa / UIKit</text>
    <text x="380" y="112" text-anchor="middle" class="xu-sub">Swift / Objective-C</text>
    <text x="550" y="112" text-anchor="middle" class="xu-sub">POSIX apps (bash, ls)</text>
    <text x="730" y="112" text-anchor="middle" class="xu-sub">System daemons (launchd)</text>
  </g>

  <path d="M 450 130 L 450 155" class="xu-syscall" stroke-dasharray="4 4"/>
  <text x="500" y="148" class="xu-sc-label">syscall / Mach trap</text>

  <g class="xu-boundary">
    <line x1="60" y1="160" x2="840" y2="160"/>
    <text x="840" y="155" text-anchor="end" class="xu-bd-label">Kernel Space ↓</text>
  </g>

  <g class="xu-bsd">
    <rect x="60" y="175" width="780" height="80" rx="8"/>
    <text x="450" y="200" text-anchor="middle" class="xu-heading">BSD Layer</text>
    <text x="180" y="225" text-anchor="middle" class="xu-sub">Process model (POSIX)</text>
    <text x="380" y="225" text-anchor="middle" class="xu-sub">File system (APFS/HFS+)</text>
    <text x="560" y="225" text-anchor="middle" class="xu-sub">Networking (BSD sockets)</text>
    <text x="730" y="225" text-anchor="middle" class="xu-sub">Signals, permissions</text>
    <text x="450" y="245" text-anchor="middle" class="xu-note">"the Unix face we see"</text>
  </g>

  <g class="xu-mach">
    <rect x="60" y="270" width="780" height="90" rx="8"/>
    <text x="450" y="295" text-anchor="middle" class="xu-heading">Mach Microkernel</text>
    <text x="200" y="320" text-anchor="middle" class="xu-sub">Task (process)</text>
    <text x="380" y="320" text-anchor="middle" class="xu-sub">Thread</text>
    <text x="560" y="320" text-anchor="middle" class="xu-sub">Mach Port (IPC)</text>
    <text x="730" y="320" text-anchor="middle" class="xu-sub">VM, scheduler</text>
    <text x="450" y="345" text-anchor="middle" class="xu-note">"product of CMU research (1985~91)"</text>
  </g>

  <g class="xu-iokit">
    <rect x="60" y="375" width="780" height="50" rx="8"/>
    <text x="450" y="395" text-anchor="middle" class="xu-heading">I/O Kit (C++ driver framework)</text>
    <text x="450" y="415" text-anchor="middle" class="xu-sub">GPU, USB, sensors, power management</text>
  </g>

  <g class="xu-hw">
    <rect x="60" y="430" width="780" height="24" rx="4"/>
    <text x="450" y="447" text-anchor="middle" class="xu-hwtext">Hardware (Apple Silicon / Intel)</text>
  </g>
</svg>
</div>

<style>
.os-xnu-container { margin: 2rem 0; text-align: center; }
.os-xnu-container svg { max-width: 100%; height: auto; }
.xu-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.xu-heading { font-size: 13px; font-weight: 700; fill: #2d3748; }
.xu-sub { font-size: 11px; fill: #2d3748; }
.xu-note { font-size: 10px; fill: #4a5568; font-style: italic; }
.xu-sc-label { font-size: 10px; fill: #718096; }
.xu-bd-label { font-size: 11px; fill: #718096; font-weight: 600; }
.xu-user rect { fill: #e6fffa; stroke: #319795; stroke-width: 1.5; }
.xu-bsd rect { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.xu-mach rect { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1.5; }
.xu-iokit rect { fill: #fefcbf; stroke: #d69e2e; stroke-width: 1.5; }
.xu-hw rect { fill: #edf2f7; stroke: #718096; stroke-width: 1; }
.xu-hwtext { font-size: 11px; fill: #2d3748; font-weight: 500; }
.xu-syscall { fill: none; stroke: #805ad5; stroke-width: 2; }
.xu-boundary line { stroke: #4a5568; stroke-width: 2; stroke-dasharray: 6 3; }

[data-mode="dark"] .xu-title { fill: #e2e8f0; }
[data-mode="dark"] .xu-heading { fill: #cbd5e0; }
[data-mode="dark"] .xu-sub { fill: #e2e8f0; }
[data-mode="dark"] .xu-note { fill: #a0aec0; }
[data-mode="dark"] .xu-sc-label { fill: #a0aec0; }
[data-mode="dark"] .xu-bd-label { fill: #a0aec0; }
[data-mode="dark"] .xu-user rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .xu-bsd rect { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .xu-mach rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .xu-iokit rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .xu-hw rect { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .xu-hwtext { fill: #e2e8f0; }
[data-mode="dark"] .xu-syscall { stroke: #b794f4; }
[data-mode="dark"] .xu-boundary line { stroke: #a0aec0; }

@media (max-width: 768px) {
  .xu-title { font-size: 14px; }
  .xu-heading { font-size: 11px; }
  .xu-sub { font-size: 9.5px; }
  .xu-note { font-size: 9px; }
}
</style>

### Apple Silicon Heterogeneous Cores

<div class="os-silicon-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Apple Silicon heterogeneous cores">
  <text x="450" y="28" text-anchor="middle" class="si-title">Apple Silicon M1 — P/E Cores and QoS Mapping</text>

  <g class="si-chip">
    <rect x="60" y="60" width="780" height="260" rx="12"/>
    <text x="450" y="85" text-anchor="middle" class="si-chip-label">M1 SoC (System on Chip)</text>
  </g>

  <g class="si-pcluster">
    <rect x="100" y="110" width="340" height="100" rx="8"/>
    <text x="270" y="130" text-anchor="middle" class="si-cluster-label">P-cluster (Firestorm × 4)</text>
    <g class="si-core si-pcore">
      <rect x="115" y="145" width="75" height="55" rx="4"/>
      <text x="152" y="168" text-anchor="middle" class="si-corename">P0</text>
      <text x="152" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="195" y="145" width="75" height="55" rx="4"/>
      <text x="232" y="168" text-anchor="middle" class="si-corename">P1</text>
      <text x="232" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="275" y="145" width="75" height="55" rx="4"/>
      <text x="312" y="168" text-anchor="middle" class="si-corename">P2</text>
      <text x="312" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="355" y="145" width="75" height="55" rx="4"/>
      <text x="392" y="168" text-anchor="middle" class="si-corename">P3</text>
      <text x="392" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
  </g>

  <g class="si-ecluster">
    <rect x="460" y="110" width="340" height="100" rx="8"/>
    <text x="630" y="130" text-anchor="middle" class="si-cluster-label">E-cluster (Icestorm × 4)</text>
    <g class="si-core si-ecore">
      <rect x="475" y="145" width="75" height="55" rx="4"/>
      <text x="512" y="168" text-anchor="middle" class="si-corename">E0</text>
      <text x="512" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="555" y="145" width="75" height="55" rx="4"/>
      <text x="592" y="168" text-anchor="middle" class="si-corename">E1</text>
      <text x="592" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="635" y="145" width="75" height="55" rx="4"/>
      <text x="672" y="168" text-anchor="middle" class="si-corename">E2</text>
      <text x="672" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="715" y="145" width="75" height="55" rx="4"/>
      <text x="752" y="168" text-anchor="middle" class="si-corename">E3</text>
      <text x="752" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
  </g>

  <g class="si-uma">
    <rect x="100" y="230" width="700" height="60" rx="8"/>
    <text x="450" y="252" text-anchor="middle" class="si-uma-label">Unified Memory (16KB pages)</text>
    <text x="450" y="275" text-anchor="middle" class="si-uma-sub">CPU, GPU, and Neural Engine share a single memory pool</text>
  </g>

  <g class="si-qos">
    <rect x="60" y="340" width="780" height="80" rx="8"/>
    <text x="450" y="362" text-anchor="middle" class="si-qos-title">macOS QoS → Core Mapping</text>
    <line x1="140" y1="380" x2="270" y2="380" class="si-qos-arrow" marker-end="url(#si-arr-p)"/>
    <text x="205" y="402" text-anchor="middle" class="si-qos-label">User Interactive / User Initiated → P-cluster</text>
    <line x1="560" y1="380" x2="700" y2="380" class="si-qos-arrow" marker-end="url(#si-arr-e)"/>
    <text x="630" y="402" text-anchor="middle" class="si-qos-label">Utility / Background → E-cluster</text>
  </g>

  <defs>
    <marker id="si-arr-p" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#3182ce"/>
    </marker>
    <marker id="si-arr-e" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#38a169"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.os-silicon-container { margin: 2rem 0; text-align: center; }
.os-silicon-container svg { max-width: 100%; height: auto; }
.si-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.si-chip rect { fill: #f7fafc; stroke: #4a5568; stroke-width: 2; stroke-dasharray: 5 5; }
.si-chip-label { font-size: 13px; font-weight: 600; fill: #2d3748; }
.si-pcluster rect { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.si-ecluster rect { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.si-cluster-label { font-size: 12px; font-weight: 600; fill: #1a202c; }
.si-pcore rect { fill: #3182ce; stroke: #2c5282; stroke-width: 1; }
.si-ecore rect { fill: #38a169; stroke: #276749; stroke-width: 1; }
.si-corename { font-size: 13px; font-weight: 700; fill: white; }
.si-coreghz { font-size: 10px; fill: white; }
.si-uma rect { fill: #feebc8; stroke: #d69e2e; stroke-width: 1.5; }
.si-uma-label { font-size: 13px; font-weight: 600; fill: #2d3748; }
.si-uma-sub { font-size: 11px; fill: #4a5568; }
.si-qos rect { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.5; }
.si-qos-title { font-size: 13px; font-weight: 700; fill: #553c9a; }
.si-qos-arrow { stroke-width: 2; }
.si-qos-label { font-size: 11px; fill: #2d3748; }

[data-mode="dark"] .si-title { fill: #e2e8f0; }
[data-mode="dark"] .si-chip rect { fill: #1a202c; stroke: #a0aec0; }
[data-mode="dark"] .si-chip-label { fill: #cbd5e0; }
[data-mode="dark"] .si-pcluster rect { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .si-ecluster rect { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .si-cluster-label { fill: #e2e8f0; }
[data-mode="dark"] .si-pcore rect { fill: #63b3ed; stroke: #2c5282; }
[data-mode="dark"] .si-ecore rect { fill: #68d391; stroke: #276749; }
[data-mode="dark"] .si-corename { fill: #1a202c; }
[data-mode="dark"] .si-coreghz { fill: #1a202c; }
[data-mode="dark"] .si-uma rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .si-uma-label { fill: #e2e8f0; }
[data-mode="dark"] .si-uma-sub { fill: #a0aec0; }
[data-mode="dark"] .si-qos rect { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .si-qos-title { fill: #d6bcfa; }
[data-mode="dark"] .si-qos-label { fill: #e2e8f0; }

@media (max-width: 768px) {
  .si-title { font-size: 14px; }
  .si-cluster-label { font-size: 10px; }
  .si-uma-label { font-size: 11px; }
  .si-qos-title { font-size: 11px; }
  .si-qos-label { font-size: 9px; }
}
</style>

> ### Hold on, let's clarify this
>
> **"Why is Rosetta 2 fast? It's an emulator — how does 70% of native perf make sense?"**
>
> Three overlapping reasons.
>
> 1. **AOT translation (translate in advance)**: it's not an emulator. At install time (or on first run), x86 binaries are **fully translated to ARM and cached**. After that, only native ARM executes.
> 2. **M1 is simply faster than contemporary x86 in absolute terms**: M1's single-core performance is excellent against same-era Intel CPUs. Even dropping to 70%, absolute perf remains strong.
> 3. **Hardware TSO mode**: emulating x86 memory ordering in software on ARM is expensive. Apple moved that cost **into hardware**, making it free.
>
> **Limits**: the hardware TSO mode is active only when x86 binaries run. Native ARM apps use ARM's weak model as-is.

---

## Part 6: The Three OSes Side by Side

Let's consolidate what we've covered. Strengths and weaknesses of each, laid out objectively.

### Developer Perspective

| Area | Linux | Windows | macOS |
|------|-------|---------|-------|
| **Kernel source access** | ✅ Fully open | ❌ Closed | 🟡 Darwin only (GUI/Cocoa closed) |
| **CLI ecosystem** | ✅ Best (bash, coreutils native) | 🟡 PowerShell great, needs WSL | ✅ Unix-standard tools included |
| **Package management** | ✅ apt/dnf/pacman | 🟡 winget/choco (latecomer) | 🟡 Homebrew (unofficial) |
| **Virtualization/containers** | ✅ Docker native | 🟡 WSL 2 / Hyper-V | 🟡 Docker Desktop (via VM) |
| **Language support** | ✅ All | ✅ All (especially .NET) | ✅ All (Swift first-class) |
| **IDE** | 🟡 VS Code, CLion | ✅ Visual Studio best | ✅ Xcode, JetBrains |
| **Documentation** | 🟡 Scattered, man pages | ✅ MSDN systematic | ✅ Apple Developer docs |
| **Community** | ✅ Huge, open | 🟡 Enterprise-centric | 🟡 Apple ecosystem-centric |

### Game Development Perspective

| Area | Linux | Windows | macOS |
|------|-------|---------|-------|
| **Primary graphics APIs** | Vulkan, OpenGL | DirectX 11/12, Vulkan | Metal (OpenGL/Vulkan deprecating) |
| **Engine support** | 🟡 Unity/Unreal target only | ✅ Best (including editors) | 🟡 Unity/Unreal editor improving |
| **Audio APIs** | ALSA, PulseAudio, PipeWire | XAudio2, WASAPI | Core Audio |
| **Debugger/profiler** | 🟡 GDB, Valgrind | ✅ Visual Studio | ✅ Instruments, Xcode |
| **Steam gameplay** | 🟡 Proton (improving) | ✅ Native | 🟡 Limited |
| **VR/AR support** | 🟡 SteamVR | ✅ WMR, SteamVR | 🟡 Vision Pro ecosystem |

### Server Operations Perspective

| Area | Linux | Windows | macOS |
|------|-------|---------|-------|
| **Web server share** | ~75% | ~20% | ~0% (not server-oriented) |
| **Containers native** | ✅ | 🟡 LCOW (Linux containers via WSL) | ❌ |
| **Low-resource ops** | ✅ Runs in hundreds of MB | 🟡 Several GB needed | 🟡 Rarely used as server |
| **License cost** | ✅ Free | 💰 Paid (Windows Server) | 🟡 Apple hardware required |

### Key Takeaways

- **There is no "best OS"** — it depends on use case
- **Server/dev**: Linux dominates
- **Enterprise/gaming client**: Windows dominates
- **Creative work/individual dev**: macOS is strong
- **All OSes borrow each other's strengths**:
  - Windows with WSL gains Linux compatibility
  - macOS leverages Linux tooling via Homebrew
  - Linux is investing in desktop UX

---

## Part 7: Security and Sandboxing — Briefly

Each OS has a different security model. Focusing only on what's relevant to game developers.

### macOS — Layered Security

**SIP (System Integrity Protection)**: protects system files. Even root cannot modify `/System`, `/bin`. Introduced in El Capitan, 2015.

**Gatekeeper**: blocks execution of unsigned apps. The "developer not verified by Apple" warning comes from this.

**Notarization**: apps must be submitted to Apple for malware verification before running without Gatekeeper warnings. Mandatory since 2019.

**App Sandbox**: Mac App Store apps must be sandboxed. General apps optional. Filesystem, network, camera are declared via entitlements.

**Hardened Runtime**: additional security layer blocking JIT, library injection, etc.

Developer angle: shipping commercial Mac apps requires an **Apple Developer account ($99/year)** for signing + notarization. Critical for game distribution.

### Windows — UAC and Defender

**UAC (User Account Control)**: prompts the user for admin-level actions. Introduced with Vista (unpopular then), now an essential security layer.

**Windows Defender**: built-in AV. Since Windows 10, third-party AV is rarely needed.

**Code Signing**: Authenticode signatures. EV certificates allow execution without SmartScreen warnings. Recommended for game distribution.

**AppContainer**: UWP app isolation. Similar to Mac App Sandbox but narrower in use.

### Linux — A Flexible Toolbox

**User/Group permissions**: Unix tradition. rwx bits, UID/GID.

**Capabilities**: slice root's privileges into specific ones (`CAP_NET_BIND_SERVICE`, `CAP_SYS_ADMIN`, etc.).

**SELinux / AppArmor**: Mandatory Access Control for fine-grained policy.

**cgroups + namespaces**: the foundation of Docker. Resource limits and isolation for process groups.

**seccomp**: syscall filtering. Sandbox apps to only allowed syscalls.

For game distribution, packaging formats like **AppImage, Flatpak, and Snap** use these technologies internally.

---

## Part 8: From a Game Developer's Angle

Finally, how do these OS differences show up **from a game dev perspective**?

### Platform-specific Considerations

**1. Unity Editor**
- Windows: full features, recommended
- macOS: well supported, native Apple Silicon builds available
- Linux: limited support (official Editor exists, plugin compatibility weaker)

**2. Unreal Engine Editor**
- Windows: full features, default
- macOS: supported with some feature limits (Vulkan support, etc.)
- Linux: officially supported, editor buildable

**3. Graphics API choice**
- If cross-platform, abstract across **Vulkan + DirectX 12**
- If Apple-only, consider **Metal** (Apple is deprecating OpenGL/Vulkan)
- Engines abstract this, but native optimization requires direct engagement

**4. Crash handlers**
- Windows: **SEH (Structured Exception Handling)**, `SetUnhandledExceptionFilter`
- Linux/macOS: **POSIX signals** (`SIGSEGV`, `SIGABRT`), `signal()` or `sigaction()`
- The two approaches differ, making cross-platform crash reporters (Sentry, Crashlytics) complex

**5. File paths**
- Windows: `C:\Users\name\AppData\...`, backslash
- macOS: `/Users/name/Library/Application Support/...`, slash
- Linux: `/home/name/.local/share/...` (XDG spec), slash
- Use engine abstractions like `Application.persistentDataPath`; be careful when dealing directly

**6. Thread priority**
- Windows: `SetThreadPriority`, 7 levels (IDLE~TIME_CRITICAL)
- macOS: QoS classes (4) + pthread priorities
- Linux: nice (-20~19) + pthread SCHED_FIFO/RR
- APIs differ when you need to elevate e.g. audio threads

### Cross-platform Engine Abstractions

Engines have **layers to hide OS differences**. For Unreal Engine:

```cpp
/* UE platform abstraction (conceptual example) */
#if PLATFORM_WINDOWS
#include "Windows/WindowsPlatformFile.h"
typedef FWindowsPlatformFile FPlatformFile;
#elif PLATFORM_MAC
#include "Apple/ApplePlatformFile.h"
typedef FApplePlatformFile FPlatformFile;
#elif PLATFORM_LINUX
#include "Unix/UnixPlatformFile.h"
typedef FUnixPlatformFile FPlatformFile;
#endif
```

Engine developers (those modifying the engine) need to **understand all three OS APIs**. Game programmers (who consume the engine) can operate at the `FPlatformFile` abstraction.

### Toolchain Compatibility

| Tool | Linux | Windows | macOS |
|------|-------|---------|-------|
| **Primary compiler** | gcc/clang | MSVC/clang-cl | clang |
| **Standard library** | glibc/libstdc++/libc++ | MSVC STL | libc++ |
| **Linker** | ld/lld | link.exe/lld-link | ld64 |
| **Debugger** | gdb, lldb | Visual Studio, WinDbg | lldb, Xcode |
| **Profiler** | perf, Tracy | Visual Studio Profiler, PIX | Instruments |
| **CI/CD availability** | ✅ Best | ✅ GitHub Actions Windows Runner | 🟡 Mac Runner is paid/limited |

**The Apple catch**: building iOS/macOS apps requires **Xcode**, and **Xcode only runs on macOS**. Building Apple-target games requires a Mac build machine. That's why Mac Runners are expensive on CI/CD.

### Platform Debugging Experience

**Windows (Visual Studio)**
- Best-in-class IDE + debugger integration
- Edit and Continue, conditional breakpoints, data breakpoints — all smooth
- PIX for GPU profiling

**macOS (Xcode + Instruments)**
- Instruments is one of the world's best profilers (System Trace, Time Profiler, Allocations)
- Visualizes Apple Silicon P/E core timelines
- Metal Frame Debugger

**Linux (gdb/lldb + Tracy)**
- CLI tools primarily; VS Code has improved UX greatly
- Valgrind (Memcheck) is powerful but slow
- Tracy Profiler is one of the top cross-platform options

---

## Wrap-up

One-page summary of what this post covered.

**Lineages**:
- Unix (1969) → BSD (1977) → NeXTSTEP (1989) → **macOS (2001)**
- Unix → Minix → **Linux (1991)**
- VMS (1977) + Dave Cutler → **Windows NT (1993)**

**Design philosophies**:
- Linux: openness + performance
- Windows: backward compatibility
- macOS: vertical integration + experience

**Kernel architecture**:
- Linux: monolithic
- Windows NT: hybrid
- macOS XNU: Mach microkernel + BSD layer (dual structure)

**Binary formats**:
- Linux: ELF
- Windows: PE (still carries the 1981 DOS MZ header)
- macOS: Mach-O (Universal Binary for multiple architectures)

**macOS-proprietary items**:
- XNU: microkernel in theory, hybrid in practice
- Mach port: root of macOS IPC and security
- Grand Central Dispatch (2009): "queues not threads" abstraction
- launchd (2005): systemd's five-year forerunner
- Apple Silicon: P/E heterogeneous cores + 16KB pages
- Rosetta 2: AOT translation + hardware TSO mode

**Remember for game dev**:
- Executable formats differ — multi-platform builds are **per-OS builds**
- Seemingly small details — crash handlers, thread priority, file paths — diverge at the API level
- Trust engine abstractions, but performance-critical code often needs per-platform optimization
- Apple platform targets require a Mac build machine

From the next post we enter **concrete theory** atop this map. Part 8 is **Processes and Threads** — PCB/TCB structures, the actual difference between `fork()` and `CreateProcess()`, thread mapping models, and context-switching costs linked to game engines' execution models.

---

## References

### Textbooks
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — OS standard textbook, chapters 3 (Processes) and 4 (Threads)
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — origin of the microkernel vs. monolithic debate
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Linux kernel internals
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — NT kernel details
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNU, Mach, BSD layer
- Levin — *\*OS Internals: Volume I — User Mode* and *Volume II — Kernel Mode*, Technologeeks, 2019 — the most detailed modern writing on macOS/iOS internals
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — OS use in game engines

### Papers and Research
- Accetta, Baron, Bolosky, Golub, Rashid, Tevanian, Young — "Mach: A New Kernel Foundation for UNIX Development", USENIX Summer 1986 — Mach's first exposition
- Young, Tevanian, Rashid, Golub, Eppinger, Chew, Bolosky, Black, Baron — "The Duality of Memory and Communication in the Implementation of a Multiprocessor Operating System", SOSP 1987
- Rashid, Baron, Forin, Golub, Jones, Julin, Orr, Sanzi — "Mach: A Foundation for Open Systems", Workshop on Workstation Operating Systems, 1989
- Bershad, Anderson, Lazowska, Levy — "Lightweight Remote Procedure Call", SOSP 1989 — microkernel IPC optimization
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:N thread model

### Official Docs and Sources
- Apple Open Source — [opensource.apple.com](https://opensource.apple.com) — XNU, Darwin sources
- Apple Developer — *Dispatch Queues and Concurrency* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Apple Developer — *About the Rosetta Translation Environment* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment)
- Linux Kernel Documentation — [kernel.org/doc](https://www.kernel.org/doc/)
- Microsoft Docs — *Windows Kernel-Mode Architecture* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/windows-kernel-mode-architecture)
- FreeBSD Architecture Handbook — [docs.freebsd.org/en/books/arch-handbook/](https://docs.freebsd.org/en/books/arch-handbook/)

### Blogs / Articles
- Raymond Chen — *The Old New Thing* — Windows backward-compat anecdotes (including the SimCity case)
- Howard Oakley — *The Eclectic Light Company* — macOS internals
- Hector Martin (marcan) — *Apple Silicon reverse engineering* — Asahi Linux project
- Dougall Johnson — "M1 Memory and Performance" series — Apple Silicon hardware analysis
- Linus Torvalds — *comp.os.minix* "Hello everybody" post (1991-08-25)
- Linus vs. Tanenbaum debate (1992) — microkernel debate archives

### Tools
- `file`, `readelf`, `objdump` (Linux) — ELF analysis
- `dumpbin`, `PEview` (Windows) — PE analysis
- `otool`, `nm`, `lipo` (macOS) — Mach-O analysis
- `launchctl`, `ps`, `top` — common observability tools across the three
- Instruments (macOS) — Apple's official profiler

### Image Credits
- Ken Thompson & Dennis Ritchie (1973) — Jargon File, Public Domain — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Ken_Thompson_and_Dennis_Ritchie--1973.jpg)
- Linus Torvalds at LinuxCon Europe 2014 — photo by Krd, CC BY-SA 4.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:LinuxCon_Europe_Linus_Torvalds_03_(cropped).jpg)
- NeXTcube (1990) at Computer History Museum — photo by Michael Hicks, CC BY 2.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:NeXTcube_computer_(1990)_-_Computer_History_Museum.jpg)
