---
title: "Understanding SIMD - From Vector Registers to Unity Burst Intrinsics"
lang: en
date: 2026-07-28 10:00:00 +0900
categories: [Unity, JobSystem]
tags: [simd, vector, intrinsics, neon, avx2, burst, unity-mathematics, vectorization, optimization, unity]
toc: true
toc_sticky: true
image: /assets/img/og/jobsystem.png
chart: true
difficulty: intermediate
prerequisites:
  - /posts/UnityJobSystemBurst/
  - /posts/SoAvsAoS/
tldr:
  - SIMD is a CPU feature that packs several values into one vector register and computes on all of them with a single instruction. ARM NEON is 128-bit and handles 4 floats; x86 AVX2 is 256-bit and handles 8 at a time
  - SIMD is not a separate device like a GPU but an execution port inside the CPU core. Its offload cost is zero, which is the decisive difference from GPU compute — it pays off even on microsecond-scale work
  - Intel consumer CPUs, the i9-14900K included, have no AVX-512 (AVX2 256-bit is the ceiling). Zen 5 has a native 512-bit datapath, and Radeon is a SIMD machine by construction with two SIMD32 units per CU
  - Every 64-bit CPU has SIMD — SSE2 is mandatory on x86-64 and NEON is mandatory on AArch64. The technique is industry-proven too, from Unreal's VectorRegister and ISPC to Jolt Physics (Horizon Forbidden West) and shipped Unity DOTS titles
  - An explicit SIMD loop is always the same five stages — broadcast the constant, traverse in vector-width steps, operate across lanes in parallel, reduce to a scalar, handle the remaining tail
  - Measured on .NET 10 with an Apple M4 Pro, summing 1 million floats ran 3.6x faster than scalar and match counting 2.7x faster. Both allocate zero heap memory
  - Burst is the only trustworthy SIMD path in Unity. Auto-vectorization plus Unity.Mathematics is the default, and v128 from Unity.Burst.Intrinsics goes only into bottlenecks verified with Burst Inspector
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: Is SIMD Really an Expert-Only Technique?

Mitchell Hashimoto, the creator of the Ghostty terminal, recently published a piece arguing that "SIMD is an everyday optimization tool every programmer should know." Rewriting Ghostty's codepoint search loop with AVX2 made it roughly 5x faster, and his point was that the structure of that code was not assembly wizardry but a formulaic five-stage pattern anyone can follow.

> Mitchell Hashimoto, *"SIMD Basics"* — <https://mitchellh.com/writing/simd-basics>

SIMD has already come up several times in this series. [The Burst Compiler deep dive](/posts/BurstCompilerDeepDive/) covered how LLVM's Loop Vectorizer vectorizes loops **on its own**, and [the SoA vs AoS post](/posts/SoAvsAoS/) covered the memory layouts that vectorize well. Both, however, skipped one question: **what exactly do SIMD instructions do in hardware that makes them fast**, and **how do you write them by hand when auto-vectorization fails**?

This post has three goals.

1. Understand SIMD at the level of vector registers and lanes, and see what form SIMD actually takes on real hardware (Intel i9, Ryzen, Apple M, Radeon)
2. Write the five-stage structure of an explicit SIMD loop directly in C# `Vector<T>` and measure it
3. Bring that knowledge into Unity and lay out the three-tier selection criteria running from auto-vectorization to Unity.Mathematics to Burst Intrinsics

All measurements were taken by me with BenchmarkDotNet on .NET 10 with an Apple M4 Pro.

---

## Part 1: What SIMD Does in Hardware

### Scalar Instructions and Vector Instructions

SIMD stands for **S**ingle **I**nstruction, **M**ultiple **D**ata. Exactly as the name says, there is one instruction, and that instruction processes multiple pieces of data.

Beyond the general-purpose registers used for ordinary arithmetic (`x0`–`x30`, 64-bit on Arm64), a CPU has separate **vector registers** (`v0`–`v31`, 128-bit). A `float` is 32 bits, so four of them fit in one 128-bit vector register, and each of those slots is called a **lane**. A single vector addition instruction performs four additions at once, pairing lanes at matching positions in the two registers.

<div class="sml-wrap">
  <div class="sml-grid">
    <div class="sml-col">
      <div class="sml-head sml-head-scalar">Scalar — 4 instructions</div>
      <div class="sml-row">
        <div class="sml-reg"><span class="sml-lane">a[i]</span></div>
        <span class="sml-op">+</span>
        <div class="sml-reg"><span class="sml-lane">b[i]</span></div>
        <span class="sml-op">=</span>
        <div class="sml-reg"><span class="sml-lane sml-lane-res">c[i]</span></div>
      </div>
      <div class="sml-loop">&#8635; i = 0, 1, 2, 3 — the same instruction repeated 4 times</div>
      <code class="sml-asm">fadd s0, s1, s2</code>
    </div>
    <div class="sml-col">
      <div class="sml-head sml-head-simd">SIMD — 1 instruction</div>
      <div class="sml-row">
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">a[0]</span><span class="sml-lane">a[1]</span><span class="sml-lane">a[2]</span><span class="sml-lane">a[3]</span>
        </div>
        <span class="sml-op">+</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">b[0]</span><span class="sml-lane">b[1]</span><span class="sml-lane">b[2]</span><span class="sml-lane">b[3]</span>
        </div>
      </div>
      <div class="sml-row sml-row-eq">
        <span class="sml-op">=</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane sml-lane-res">c[0]</span><span class="sml-lane sml-lane-res">c[1]</span><span class="sml-lane sml-lane-res">c[2]</span><span class="sml-lane sml-lane-res">c[3]</span>
        </div>
      </div>
      <div class="sml-loop">4 lanes of a 128-bit register computed simultaneously</div>
      <code class="sml-asm">fadd v0.4s, v1.4s, v2.4s</code>
    </div>
  </div>
  <p class="sml-cap">Two ways to perform the same four additions (Arm64 NEON)</p>
</div>

<style>
.sml-wrap{margin:2rem 0}
.sml-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.sml-col{border-radius:14px;padding:1.1rem 1rem 1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15)}
.sml-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13.5px;font-weight:700;color:#fff;margin-bottom:1rem}
.sml-head-scalar{background:linear-gradient(135deg,#ef9a9a,#c62828)}
.sml-head-simd{background:linear-gradient(135deg,#81c784,#2e7d32)}
.sml-row{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:.5rem;flex-wrap:nowrap}
.sml-row-eq{margin-top:.1rem}
.sml-reg{display:flex;border:1.5px solid #90a4ae;border-radius:6px;overflow:hidden}
.sml-lane{display:flex;align-items:center;justify-content:center;min-width:40px;height:32px;font-size:12px;font-weight:600;background:#e3f2fd;color:#1565c0;border-right:1px dashed #90a4ae;padding:0 4px}
.sml-lane:last-child{border-right:none}
.sml-lane-res{background:#e8f5e9;color:#2e7d32}
.sml-op{font-size:16px;font-weight:700;color:#546e7a}
.sml-loop{text-align:center;font-size:12px;color:var(--text-muted-color,#6c757d);margin:.4rem 0}
.sml-asm{display:block;text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);background:rgba(128,128,128,.08);border-radius:6px;padding:3px 6px}
.sml-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sml-lane{background:#1a2a3a;color:#90caf9;border-right-color:#546e7a}
[data-mode="dark"] .sml-lane-res{background:#1a3320;color:#a5d6a7}
[data-mode="dark"] .sml-reg{border-color:#546e7a}
[data-mode="dark"] .sml-op{color:#b0bec5}
@media(max-width:768px){.sml-grid{grid-template-columns:1fr}}
</style>

### Vector Width — A Theoretical Ceiling That Differs by Platform

How many values one instruction processes is fixed by the width of the vector registers the instruction set provides.

| Instruction Set | Register Width | float Lanes | Main Platforms |
|------------|-----------|-----------|------------|
| **ARM NEON** | 128-bit | 4 | All mobile devices, Apple Silicon, Nintendo Switch |
| **x86 SSE4** | 128-bit | 4 | Common x86-64 baseline |
| **x86 AVX2** | 256-bit | 8 | Desktops since 2013, PS5, Xbox Series |
| **x86 AVX-512** | 512-bit | 16 | Some servers and recent desktop CPUs |

For a game programmer this table has a single conclusion. **The conservative cross-platform baseline is 128-bit, that is, "4 floats = 4x in theory."** For a mobile target it is NEON 128-bit, full stop. Desktop is somewhat better off — Burst's default 64-bit desktop setting compiles two variants, SSE2 and AVX2, and picks between them at runtime by inspecting the CPU (runtime dispatch), so 256-bit is used automatically on CPUs that support AVX2. AVX-512 can be dropped from the game shipping matrix entirely.

### Why You Don't Always Get 4x

Four lanes does not turn arbitrary code into 4x. Three preconditions have to hold for SIMD to pay off.

- **Contiguous memory**: a vector load instruction fetches a contiguous 128 bits from memory in one go. If the data is scattered, the cost of filling the lanes eats the arithmetic gain
- **Identical operation**: the same instruction is applied to all four lanes. If each element needs different handling, the SIMD model does not apply at all
- **Minimal branching**: there is no per-lane `if`. Conditionals have to be rewritten as comparison masks and arithmetic (we do exactly this in Part 3)

The thing that forces these three preconditions into your code structure is the [SoA layout](/posts/SoAvsAoS/). The previous post's conclusion that "SoA suits SIMD" was, in the end, the software-side expression of a hardware constraint: vector loads demand a contiguous 128 bits.

---

## Part 2: SIMD on Real Hardware — i9, Ryzen, Apple M, and Radeon

### Is There a Dedicated Pipeline? No, It's an Execution Port Inside the Core

To answer "does SIMD have a dedicated pipeline the way the CPU has a path to the GPU" up front: **SIMD has no separate device and no separate transfer path**. The vector unit is a subset of the execution ports inside the CPU core. It shares the front end — instruction fetch, decode, scheduler — with scalar instructions as-is, and the scheduler merely looks at the instruction type and decides whether to send it to an integer ALU port or a vector FMA port. The data comes straight out of the same L1 cache.

<div class="shw-wrap">
  <div class="shw-grid">
    <div class="shw-panel">
      <div class="shw-head shw-head-cpu">Inside a CPU core — SIMD is an execution port</div>
      <div class="shw-box shw-box-wide">Front end (fetch &#183; decode)</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">Scheduler — assigns ports by instruction type</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-ports">
        <div class="shw-box shw-box-scalar">Scalar<br/>ALU port</div>
        <div class="shw-box shw-box-vec">Vector FMA<br/>ports &#215;2</div>
      </div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">L1 cache (shared)</div>
      <div class="shw-note">Zero offload cost — applies even to µs-scale work</div>
    </div>
    <div class="shw-panel">
      <div class="shw-head shw-head-gpu">GPU — a separate device</div>
      <div class="shw-box shw-box-wide">CPU — record command buffer</div>
      <div class="shw-varrow shw-varrow-cost">&#8595; PCIe transfer + dispatch latency</div>
      <div class="shw-box shw-box-gpu">GPU<br/><span class="shw-sub">dozens of CUs, two SIMD32 units per CU</span></div>
      <div class="shw-varrow shw-varrow-cost">&#8595; result readback (sync wait)</div>
      <div class="shw-box shw-box-wide">CPU — receive results</div>
      <div class="shw-note">Round trip of tens of µs to ms — bulk work only</div>
    </div>
  </div>
  <p class="shw-cap">The same "parallel computation", but in different places — CPU SIMD sits inside the core, the GPU across the bus</p>
</div>

<style>
.shw-wrap{margin:2rem 0}
.shw-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.shw-panel{border-radius:14px;padding:1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15);display:flex;flex-direction:column}
.shw-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700;color:#fff;margin-bottom:.8rem}
.shw-head-cpu{background:linear-gradient(135deg,#64b5f6,#1565c0)}
.shw-head-gpu{background:linear-gradient(135deg,#ba68c8,#6a1b9a)}
.shw-box{border-radius:8px;padding:.5rem .6rem;text-align:center;font-size:12px;font-weight:600;background:#eceff1;color:#37474f;line-height:1.5}
.shw-box-wide{width:100%}
.shw-ports{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.shw-box-scalar{background:#f5f5f5;color:#546e7a}
.shw-box-vec{background:#e8f5e9;color:#2e7d32;border:1.5px solid #66bb6a}
.shw-box-gpu{background:#f3e5f5;color:#6a1b9a;border:1.5px solid #ba68c8;padding:.7rem .6rem}
.shw-sub{font-size:11px;font-weight:500}
.shw-varrow{text-align:center;font-size:13px;color:#90a4ae;padding:2px 0}
.shw-varrow-cost{color:#e65100;font-size:11.5px;font-weight:600}
.shw-note{text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);margin-top:.7rem;font-style:italic}
.shw-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .shw-box{background:#2a2a2e;color:#cfd8dc}
[data-mode="dark"] .shw-box-scalar{background:#26262a;color:#90a4ae}
[data-mode="dark"] .shw-box-vec{background:#1a3320;color:#a5d6a7;border-color:#4caf50}
[data-mode="dark"] .shw-box-gpu{background:#31173a;color:#ce93d8;border-color:#8e24aa}
[data-mode="dark"] .shw-varrow-cost{color:#ffcc80}
@media(max-width:768px){.shw-grid{grid-template-columns:1fr}}
</style>

Being located at an "execution port" determines SIMD's character. Since it is not a separate device, **the startup cost is zero**. GPU compute has a round trip — record the command buffer, dispatch, read the results back — that runs from tens of microseconds to milliseconds, so small jobs cost more than they return. SIMD has no setup cost whatsoever for vectorizing a loop, so the gain shows up even on microsecond-scale work. In exchange it consumes the core's own resources, so the scale of parallelism is capped at core count × lane count.

That said, even the "free execution port" had one historical exception. Early AVX-512 implementations (Skylake-X) dropped the core clock substantially when running the 512-bit units because of power limits, and vector code ended up slowing down the scalar code on the same core. Recent implementations have largely fixed this: Zen 5 (Ryzen 9950X) drops only from 5.7 to 5.3 GHz, roughly 10%, even under an AVX-512 power-virus load.

### Where the Gaming PC Stands — the i9 Has No AVX-512

The answer to "can I use SIMD on an Intel i9" is "definitely up to AVX2, and no AVX-512." Here is the SIMD support picture for the major gaming CPUs as of 2026.

| CPU | Max SIMD | Vector Width | Vector Register Capacity | Notes |
|-----|----------|--------|------------------|------|
| Intel i9-14900K (Raptor Lake) | AVX2 | 256-bit | 16 YMM = 512 B | AVX-512 hardware exists but is fused off |
| Intel Core Ultra 9 285K (Arrow Lake) | AVX2 | 256-bit | 16 YMM = 512 B | Consumer line still lacks AVX-512 |
| Intel Nova Lake (planned for 2026) | AVX10.2 | 512-bit | 32 ZMM = 2 KB | 512-bit announced for both P- and E-cores |
| AMD Ryzen 9 9950X (Zen 5) | AVX-512 | 512-bit | 32 ZMM = 2 KB | Native 512-bit datapath (Zen 4 double-pumped 256-bit) |
| Apple M4 | NEON | 128-bit | 32 V = 512 B | Secures throughput with pipe count (4 per P-core) instead of width |

What a game developer should take from this table is not the ranking but the **history**. Intel supported consumer AVX-512 in the 11th generation (Rocket Lake), disabled it in the 12th (Alder Lake) because of the instruction set mismatch with the E-cores, and never brought it back to the consumer line in later generations. AMD went the other way, adding AVX-512 from Zen 4 and expanding it to full 512-bit in Zen 5. So the assumption "any modern desktop has AVX-512" is wrong on half the market — the safe line that covers the entire shipping target is AVX2 (256-bit). This support fragmentation is exactly why Burst's desktop default compiles two variants, SSE2 and AVX2, and chooses at runtime.

Viewed as "capacity," the vector register file is tiny — kilobytes. All 16 AVX2 YMM registers together come to 512 bytes, and even AVX-512's 32 ZMM registers total 2 KB. A vector register is not storage for holding data but **a window through which data streaming from L1 cache passes**, which is why Part 1's "contiguous memory" precondition matters again. No matter how wide the window, it is useless if the supply dries up.

The table also shows that width is not everything. Effective throughput is **width × vector ports per core**. The i9's P-core has two 256-bit FMA ports, so per cycle in FP32 terms that is 8 lanes × 2 ports × 2 operations (multiply + add) = 32 FLOP; the Apple M4's P-core has four 128-bit pipes, so 4 lanes × 4 pipes × 2 operations = 32 FLOP as well. The intuition that NEON "is slow because it's half as wide" is arithmetic that forgot to count ports.

### CPUs With No SIMD at All — If It's 64-bit, It Has SIMD

Talk of support fragmentation invites the worry that "maybe some CPUs have no SIMD at all," but as long as 64-bit is your shipping target, no such CPU exists. The **presence** of SIMD is guaranteed by the architecture standard.

- **x86-64**: SSE2 (128-bit) is a mandatory architectural feature. Every x86-64 CPU since the first one in 2003 has it without exception, and compilers even compile ordinary `float` arithmetic into SSE registers rather than x87
- **AArch64 (64-bit ARM)**: NEON (AdvSIMD) is mandatory. That covers every 64-bit smartphone, tablet, and Apple Silicon chip
- **The exceptions live in the past and in embedded**: back in the 32-bit ARMv7 era NEON was optional, and chips shipped without it (the NVIDIA Tegra 2 used in early Android tablets is the famous case), and Cortex-M microcontrollers still have no vector unit today

In fact, this guarantee was already hidden in the Part 1 diagram. The `s0` in the scalar instruction `fadd s0, s1, s2` is not a separate scalar register but **the lower 32 bits of vector register `v0`**. On a 64-bit CPU even scalar floating-point code runs on top of the vector register file, and using SIMD is closer to finishing off the remaining lanes of hardware that is already there. So the thing to worry about is not "is it there" but the single question the previous table answered: "how wide is it."

### What the Minimum Spec Sheet Really Means — Guess the Width Wrong and You Get Illegal Instruction

You should also know what happens when that "width" assumption is violated. The result is not a slowdown but **instant death**. When a CPU meets an instruction it cannot decode, an Illegal Instruction exception fires and the process terminates on the spot. Running a game built for a higher instruction set on an older CPU produces exactly this crash, and there are several real-world incidents.

- **Cyberpunk 2077** (2020) — the executable contained AVX instructions and crashed on CPUs without AVX (the AMD Phenom family and others). Hotfix 1.05 removed AVX usage and resolved it
- **Helldivers 2** (2024) — an update effectively made AVX2 mandatory, and overnight the game became unlaunchable for users with pre-2013 CPUs
- Nixxes, Sony's PC porting studio, even maintains an official error page titled "This game requires a CPU that supports the AVX2 instruction set"

The CPU model names on a game's minimum spec sheet often mean precisely this. "Core i3-8100 or better" is not saying the clock is too low; it is closer to **specifying an instruction set generation**.

The standard fix on the developer side is the **runtime dispatch** mentioned earlier. You put both SSE2 and AVX2 code in the executable and pick between them at startup by checking CPU support via CPUID — and that is exactly what Burst's desktop default (compiling SSE2 + AVX2 variants) does. Cyberpunk and Helldivers 2 are cases where higher instructions were baked in without dispatch. Consoles, on the other hand, have fixed hardware (the Zen 2 in PS5 and Xbox Series guarantees AVX2), so hardcoding AVX2 is safe there — which is why this problem blows up specifically in PC ports of console games.

### Is Radeon SIMD Too? A GPU Is a Machine Built Out of SIMD

The question "do GPUs like Radeon have SIMD" gets accurate only when you flip the direction. It is not that GPUs "have" SIMD — **a GPU is a machine built from the ground up by stacking SIMD units in bulk**.

One Compute Unit (CU) in AMD's RDNA architecture consists of **two SIMD32 units**. A SIMD32 unit is a scaled-up version of a CPU vector unit in which 32 lanes execute the same instruction every cycle. The marketing phrase "64 stream processors" is just this 32 lanes × 2 units spelled out, and converting the Radeon RX 7900 XTX's 96 CUs gives 6,144 FP32 lanes. That is three orders of magnitude away from the 8–16 lanes of a single CPU core.

Yet nobody writes intrinsics on a GPU. The programming model is different.

- **CPU SIMD**: the programmer is directly aware of lanes. Broadcast, mask, and reduction are written out in code (the five stages of Part 3)
- **GPU (SIMT)**: the programmer writes scalar code for "one thread" (HLSL and friends), and the hardware bundles 32 threads into a wavefront and assigns them automatically to the lanes of a SIMD32 unit
- **Branch handling**: when threads take different sides of an `if` (divergence), the hardware executes both paths and picks results with a mask — the hardware doing for you the mask arithmetic we will write by hand in Part 3

In other words, SIMT is a convenience layer laid over SIMD hardware, and the cost model "a branch becomes a mask" is identical on CPU and GPU. The common wisdom that branches are expensive in GPU shaders is rooted in the same place as the fact that CPU SIMD has no per-lane `if`.

In the Unity context, this choice is Compute Shader vs Burst Job. The criterion was already shown by the diagram in the previous section — if the data is already on the GPU (wired into the rendering pipeline) or the workload is large enough to amortize the round-trip latency, use a Compute Shader; if CPU logic has to consume the results every frame and the work is on the scale of microseconds to hundreds of microseconds, CPU SIMD (Burst) is the right call. 6,144 lanes do not always beat 8 lanes. To beat them, the data first has to cross the bus.

---

## Part 3: The Five-Stage Structure of an Explicit SIMD Loop

### Always the Same Five Stages

What makes Mitchell Hashimoto's article good is that it pins down how SIMD code, regardless of language and instruction set, is **always composed of the same five stages**. Whether you write it in Zig, in C intrinsics, or in the C# `Vector<T>` we are about to see, the structure is identical.

<div class="sm5-wrap">
  <div class="sm5-flow">
    <div class="sm5-step">
      <div class="sm5-num">1</div>
      <div class="sm5-name">Broadcast</div>
      <div class="sm5-desc">Copy the constant into every lane</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">2</div>
      <div class="sm5-name">Vector traversal</div>
      <div class="sm5-desc">Advance the array in vector-width steps</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step sm5-step-core">
      <div class="sm5-num">3</div>
      <div class="sm5-name">Lane-parallel operation</div>
      <div class="sm5-desc">Apply one instruction across all lanes</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">4</div>
      <div class="sm5-name">Reduction</div>
      <div class="sm5-desc">Collapse the lane results into one scalar</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">5</div>
      <div class="sm5-name">Tail handling</div>
      <div class="sm5-desc">Handle the remainder with a scalar loop</div>
    </div>
  </div>
  <p class="sm5-cap">The five stages of an explicit SIMD loop — success or failure is decided at ③ the lane-parallel operation</p>
</div>

<style>
.sm5-wrap{margin:2rem 0}
.sm5-flow{display:flex;align-items:stretch;justify-content:center;gap:4px;max-width:760px;margin:0 auto;flex-wrap:nowrap}
.sm5-step{flex:1;min-width:0;border-radius:12px;padding:.8rem .5rem;text-align:center;background:linear-gradient(160deg,#e3f2fd,#bbdefb);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.sm5-step-core{background:linear-gradient(160deg,#fff8e1,#ffe082);box-shadow:0 2px 10px rgba(230,150,0,.25)}
.sm5-num{width:24px;height:24px;border-radius:50%;background:#1565c0;color:#fff;font-size:12.5px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto .4rem}
.sm5-step-core .sm5-num{background:#e65100}
.sm5-name{font-size:13px;font-weight:700;color:#0d47a1;margin-bottom:.25rem}
.sm5-step-core .sm5-name{color:#bf360c}
.sm5-desc{font-size:11px;line-height:1.5;color:#37474f}
.sm5-arr{display:flex;align-items:center;font-size:15px;color:#90a4ae;font-weight:700}
.sm5-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sm5-step{background:linear-gradient(160deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sm5-step-core{background:linear-gradient(160deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sm5-name{color:#90caf9}
[data-mode="dark"] .sm5-step-core .sm5-name{color:#ffcc80}
[data-mode="dark"] .sm5-desc{color:#b0bec5}
@media(max-width:768px){.sm5-flow{flex-direction:column;align-items:stretch}.sm5-arr{justify-content:center;transform:rotate(90deg);padding:2px 0}}
</style>

### Writing It Yourself With C# Vector&lt;T&gt;

.NET's `System.Numerics.Vector<T>` is a type that abstracts "the vector width of the current hardware." `Vector<int>.Count` is 4 on NEON and 8 on AVX2, and the JIT translates each operation into the platform's vector instructions. Porting "count occurrences of a value in an array" — the same structure as Ghostty's codepoint search — straight into the five stages gives this.

```csharp
using System.Numerics;

int CountTarget(int[] data, int target)
{
    // ① Broadcast — copy target into every lane
    var targetVec = new Vector<int>(target);
    var acc = Vector<int>.Zero;

    int width = Vector<int>.Count;   // 4 on NEON
    int i = 0;

    // ② Vector traversal — advance 4 at a time
    for (; i <= data.Length - width; i += width)
    {
        var chunk = new Vector<int>(data, i);

        // ③ Lane-parallel operation — matching lanes become -1 (all bits set), others 0
        acc += Vector.Equals(chunk, targetVec);
    }

    // ④ Reduction — collapse the 4 lane accumulators into one scalar
    int count = -Vector.Sum(acc);

    // ⑤ Tail handling — the remainder that isn't divisible by 4
    for (; i < data.Length; i++)
        if (data[i] == target) count++;

    return count;
}
```

Stage ③ is the heart of this code. In a scalar version this is where you would write `if (data[i] == target) count++`, but SIMD has no per-lane branch, so we **take the comparison result as a mask and handle it with arithmetic**. `Vector.Equals` returns a vector with matching lanes filled with `-1` (all bits set) and non-matching lanes with `0`, and accumulating that directly builds up "match count × (-1)" in each lane. Flipping the sign in ④ gives the total. It is barely an exaggeration to say that this conversion of a branch into mask arithmetic is the whole of the SIMD mindset.

The remaining stages are formulaic boilerplate. ①, ②, and ⑤ look nearly the same in any SIMD code, and the reduction in ④ is a single `Vector.Sum` line. So when you meet a new problem, the thing to think about narrows to one question: "can ③ be built without a branch?"

---

## Part 4: Measurements — Scalar vs Vector&lt;T&gt;

### Environment and Targets

I measured on my own development machine how much of the theoretical 4x actually materializes.

- **Environment**: .NET 10.0.0, Apple M4 Pro, Arm64 RyuJIT (AdvSIMD), BenchmarkDotNet v0.14.0, `[MemoryDiagnoser]`
- **Data**: arrays of 1 million elements (float sum / int match count, fixed-seed random values)
- **Pairs compared**: a plain scalar loop vs the five-stage `Vector<T>` loop above (`Vector<float>.Count` = 4)

The summation code is even simpler than the count.

```csharp
[Benchmark(Baseline = true)]
public float SumScalar()
{
    float sum = 0f;
    for (int i = 0; i < _floats.Length; i++)
        sum += _floats[i];
    return sum;
}

[Benchmark]
public float SumVector()
{
    var acc = Vector<float>.Zero;
    int width = Vector<float>.Count;
    int i = 0;
    for (; i <= _floats.Length - width; i += width)
        acc += new Vector<float>(_floats, i);   // 4 lanes accumulated at once

    float sum = Vector.Sum(acc);                // Reduction
    for (; i < _floats.Length; i++)             // Tail
        sum += _floats[i];
    return sum;
}
```

### Results

| Benchmark | Mean | vs Scalar | Allocated |
|----------|-----:|-----------:|----------:|
| SumScalar (1M floats) | 585.5 µs | 1.00x | 0 B |
| **SumVector** | **163.0 µs** | **3.59x faster** | 0 B |
| CountScalar (1M ints) | 331.1 µs | 1.00x | 0 B |
| **CountVector** | **124.3 µs** | **2.66x faster** | 0 B |

<div class="chart-wrapper">
  <div class="chart-title">Scalar vs Vector&lt;T&gt; — processing time for 1M elements (Apple M4 Pro, .NET 10)</div>
  <canvas id="simdBenchEn" class="chart-canvas" height="260"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'simdBenchEn',
  type: 'bar',
  data: {
    labels: ['Sum of 1M floats', 'Match count over 1M ints'],
    datasets: [
      {label:'Scalar loop',data:[585.5,331.1],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5},
      {label:'Vector<T> (NEON 128bit)',data:[163.0,124.3],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5}
    ]
  },
  options: {
    scales: {
      y: {beginAtZero:true,title:{display:true,text:'Mean execution time (µs) — lower is faster'},grid:{color:'rgba(128,128,128,0.15)'}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom',labels:{padding:16,usePointStyle:true,pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y.toFixed(1)+' µs';}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### Reading the Numbers — Why 3.6x and 2.7x

Why the two speedups differ is where this benchmark has the most to teach.

**Summation reaches 3.59x, close to the theoretical ceiling of 4x**, because scalar summation is the worst-case setup. `sum += x` is a serial dependency chain in which the next addition cannot start until the previous one finishes, so the scalar loop's speed is pinned directly to floating-point addition latency. The vector version splits that chain across 4 lanes, so almost the full width-proportional gain comes through.

**Counting stops at 2.66x** for the opposite reason: the scalar side is already quite fast. In the test data the match probability is 1/256, so the `if (data[i] == target)` branch is almost always predicted "no match," and a loop whose branch predictions keep hitting never stalls the pipeline. The faster your opponent, the smaller the speedup — the size of SIMD's gain is set not by the vector code but by **what the scalar code you're comparing against is bound on**.

Two caveats also surface in the measurements.

- **The floating-point summation order changes.** Scalar adds one at a time from the left, while the vector version splits values across 4 lanes and combines them at the end, so the association order differs — and since floating-point addition is not associative, bit-identical results are not guaranteed. This is exactly why Burst needs `FloatMode.Fast` for reduction vectorization ([deep dive, Part 2](/posts/BurstCompilerDeepDive/))
- **These numbers belong to RyuJIT.** Take the same `Vector<T>` code into Unity and you will not see these ratios. Unity's Mono runtime handles `Vector<T>` in software with no hardware acceleration, and IL2CPP does not guarantee vector instruction generation either

That second caveat is the subject of the next part. There is a separate road to SIMD in Unity.

---

## Part 5: Unity's SIMD Paths — a Three-Tier Ladder

### Why System.Numerics.Vector Is Not the Answer in Unity

In practice there is exactly one path in the Unity runtime along which SIMD instructions actually get generated: Burst.

- **Mono**: the `Vector<T>` API works but has no hardware acceleration. It emulates per-lane operations with a software loop, so it can end up slower than scalar
- **IL2CPP**: it only converts IL to C++ and gives no special treatment to `System.Numerics` types as vector instructions. What remains is the C++ compiler's auto-vectorization, and as the [deep dive](/posts/BurstCompilerDeepDive/) showed, auto-vectorization is a fragile optimization that one condition can break
- **Burst**: it compiles Job code directly through LLVM and emits NEON/SSE/AVX instructions. You can verify vectorization with Burst Inspector, and even force it at compile time with `Loop.ExpectVectorized()`

### How Burst Turns C# Into Vector Instructions

Burst's process for producing SIMD boils down to four stages.

1. **Discovery**: it gathers the IL (intermediate language) of Jobs marked with `[BurstCompile]`
2. **Conversion**: its own front end **converts IL directly into LLVM IR**. This is where it diverges from IL2CPP, which goes through C++ — with no C++ source as an intermediate stage, type and aliasing information reaches LLVM without loss
3. **Optimization**: the LLVM passes run. SROA hoists structs like `float4` wholesale into vector registers, and the Loop Vectorizer rewrites loops in vector-width units
4. **Code generation**: per-target back ends emit NEON/SSE2/AVX2 machine code. On desktop that means two variants, SSE2 and AVX2, plus runtime dispatch, as we saw in Part 2

Burst's decisive weapon in this pipeline is not compiler technology but **the aliasing guarantee the Job structure hands over for free**. A Job's `NativeArray` fields are guaranteed non-overlapping by the Safety System, so Burst can treat every input and output as alias-free and vectorize. The point where a C++ compiler gives up on vectorization, worrying "what if these two pointers refer to the same memory," Burst simply walks past — the core of "why Burst can be faster than C++," covered in the [deep dive](/posts/BurstCompilerDeepDive/).

For example, when a Job that multiplies a `float4` array by a scalar (the `ScaleJob` that appears shortly as the tier 2 example) goes through this pipeline, the loop body conceptually compresses to these three lines.

```
ldr  q0, [x0, x2]          ; load 128 bits (4 floats) from input
fmul v0.4s, v0.4s, v1.4s   ; multiply 4 lanes at once — scale is broadcast into v1
str  q0, [x1, x2]          ; store 128 bits into output
```

One line of C# (`output[i] = input[i] * scale`) came out as one instruction each for load, operate, and store. Burst Inspector is where you confirm this actually happened, and the per-pass LLVM detail plus how to read the assembly are in [deep dive, Parts 1 and 3](/posts/BurstCompilerDeepDive/).

So doing SIMD optimization in Unity comes down to choosing how far down to go on top of Burst. There are three tiers to choose from.

<div class="sbi-wrap">
  <div class="sbi-ladder">
    <div class="sbi-tier sbi-tier1">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge1">Tier 1 — Default</span> Auto-vectorization</div>
      <div class="sbi-tier-body">Leave it to the LLVM Loop Vectorizer with nothing more than [BurstCompile] + Job + NativeArray. The code stays an ordinary C# loop, and in most cases this is where it should end.</div>
    </div>
    <div class="sbi-tier sbi-tier2">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge2">Tier 2 — Recommended</span> Unity.Mathematics</div>
      <div class="sbi-tier-body">Use float4 and int4 and Burst maps the type straight onto a vector register. It depends less on whether auto-vectorization succeeds, while the code stays portable.</div>
    </div>
    <div class="sbi-tier sbi-tier3">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge3">Tier 3 — Last resort</span> Unity.Burst.Intrinsics</div>
      <div class="sbi-tier-body">Specify instructions yourself with the v128 type and NEON/SSE intrinsics. Platform-specific branching becomes necessary, so use it only on bottlenecks where Burst Inspector confirmed tiers 1 and 2 failed.</div>
    </div>
  </div>
  <div class="sbi-axis">
    <span>&#9650; Portability &#183; maintainability</span>
    <span>Control &#183; certainty &#9660;</span>
  </div>
  <p class="sbi-cap">Unity's three SIMD tiers — going lower buys certainty but binds the code to a platform</p>
</div>

<style>
.sbi-wrap{margin:2rem 0}
.sbi-ladder{max-width:680px;margin:0 auto;display:flex;flex-direction:column;gap:.6rem}
.sbi-tier{border-radius:12px;padding:.9rem 1.1rem;box-shadow:0 2px 10px rgba(0,0,0,.07)}
.sbi-tier1{background:linear-gradient(135deg,#e8f5e9,#dcedc8);border-left:5px solid #2e7d32}
.sbi-tier2{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-left:5px solid #1565c0}
.sbi-tier3{background:linear-gradient(135deg,#fff8e1,#ffecb3);border-left:5px solid #e65100}
.sbi-tier-head{font-size:14px;font-weight:700;color:#263238;margin-bottom:.35rem}
.sbi-badge{display:inline-block;border-radius:12px;padding:2px 10px;font-size:11.5px;font-weight:700;color:#fff;margin-right:8px}
.sbi-badge1{background:#2e7d32}
.sbi-badge2{background:#1565c0}
.sbi-badge3{background:#e65100}
.sbi-tier-body{font-size:13px;line-height:1.7;color:#37474f}
.sbi-axis{max-width:680px;margin:.6rem auto 0;display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-muted-color,#6c757d)}
.sbi-cap{text-align:center;margin-top:.6rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sbi-tier1{background:linear-gradient(135deg,#1a3320,#20401f)}
[data-mode="dark"] .sbi-tier2{background:linear-gradient(135deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sbi-tier3{background:linear-gradient(135deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sbi-tier-head{color:#eceff1}
[data-mode="dark"] .sbi-tier-body{color:#b0bec5}
</style>

### Tiers 1 and 2 — Auto-Vectorization and Unity.Mathematics

Tiers 1 and 2 were already covered in detail in this series, so here are just the key points again. The success and failure conditions of auto-vectorization and the workflow for checking assembly in Burst Inspector are in [Burst Compiler deep dive, Parts 3 and 4](/posts/BurstCompilerDeepDive/). The core of tier 2 is that `float4` operations map onto vector instructions by themselves, with no need to wait on auto-vectorization.

```csharp
[BurstCompile]
struct ScaleJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float4> input;
    public NativeArray<float4> output;
    public float scale;

    // One float4 multiply compiles into one NEON fmul v0.4s instruction
    public void Execute(int i) => output[i] = input[i] * scale;
}
```

The thing to watch out for is `float3`. Only three values go into a four-lane register, so one lane is wasted, and laying them out as an array also breaks 16-byte alignment. For data you intend to feed to SIMD, it is better to model it as `float4` from the start, or split x, y, and z into separate arrays with the [SoA layout](/posts/SoAvsAoS/).

### Tier 3 — Writing It Directly With Unity.Burst.Intrinsics

Patterns where auto-vectorization fails and `float4` cannot express the operation either — reductions like Part 3's "mask accumulation" being the classic case — get written directly with intrinsics. Porting Part 3's count loop to the NEON version in `Unity.Burst.Intrinsics` looks like this.

```csharp
using Unity.Burst;
using Unity.Burst.Intrinsics;
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;
using static Unity.Burst.Intrinsics.Arm.Neon;

[BurstCompile]
unsafe struct CountTargetJob : IJob
{
    [ReadOnly] public NativeArray<int> data;
    public int target;
    public NativeReference<int> result;

    public void Execute()
    {
        int* p = (int*)data.GetUnsafeReadOnlyPtr();
        int count = 0;
        int i = 0;

        if (IsNeonSupported)   // compile-time constant — zero runtime branch cost
        {
            v128 targetVec = new v128(target);        // ① Broadcast
            v128 acc = new v128(0);

            for (; i <= data.Length - 4; i += 4)      // ② Vector traversal
            {
                v128 chunk = vld1q_s32(p + i);        //    128-bit load
                v128 mask  = vceqq_s32(chunk, targetVec); // ③ matching lane = -1
                acc = vsubq_s32(acc, mask);           //    -(-1) = +1 accumulated
            }
            count = vaddvq_s32(acc);                  // ④ Reduction via horizontal sum
        }

        for (; i < data.Length; i++)                  // ⑤ Tail + fallback for no NEON
            if (p[i] == target) count++;

        result.Value = count;
    }
}
```

I hope you notice that the structure is exactly the same as the `Vector<T>` version in Part 3. `Vector.Equals` became `vceqq_s32` and `Vector.Sum` became `vaddvq_s32`, and the five stages are otherwise untouched. The learning cost of explicit SIMD lies not in memorizing instruction names but in internalizing this structure once, and once you have, you slot the intrinsics of any platform into the same frame.

The `IsNeonSupported` branch is free thanks to the compile-time evaluation mechanism covered in the [deep dive](/posts/BurstCompilerDeepDive/). Burst compiles code separately per target platform, so the ARM build keeps only the NEON path and the x86 build only the scalar fallback. Put the other way around, if you want SIMD on x86 too, you have to write a separate `X86.Sse2` path — and this per-platform duplication is the real maintenance cost of tier 3.

---

## Part 6: SIMD in Shipped Game Software

The best way to show that Unity's Burst is not some special path is to look at other engines and shipped games. To put the conclusion first: SIMD is a settled, standard technique in the game industry, and what differs between engines is only the answer to "how do we let people use it."

### Unreal Engine ① — VectorRegister, the Floor of Engine Math

Unreal's math library has stood on SIMD from the beginning. The key piece is the `VectorRegister4Float` type. As the name says, it is an abstraction of a four-float vector register, and the platform-specific implementations split at the header level — on x86 `UnrealMathSSE.h` implements the function set (`VectorAdd`, `VectorMultiplyAdd`, `VectorCompareGT`...) with SSE intrinsics, and on ARM `UnrealMathNeon.h` implements the same set with NEON intrinsics.

The structure should look familiar. It is **exactly the same "thin abstraction" pattern as Burst's `v128`**. The difference is placement — in Unity, `v128` is a tier 3 that people optionally descend to when they need optimization, whereas in Unreal `VectorRegister4Float` is the floor that all of engine math stands on at all times: `FMatrix` multiplication, `FTransform` composition, quaternion interpolation. An Unreal game already benefits from SIMD in its per-frame transform math even if the developer never writes a line of SIMD.

### Unreal Engine ② — ISPC, "a Shader for the CPU"

Where explicit SIMD is needed, Unreal's answer was not intrinsics but **a dedicated compiler**. Intel ISPC (Implicit SPMD Program Compiler), integrated since UE 4.23, is a tool where you write the code for "one element" in a C-like language and the compiler generates vector code for SSE4, AVX2, and NEON separately. It is used in Chaos physics, cloth simulation, and the animation system.

```c
/* ISPC — write it like a single thread and it runs in parallel across the lane width */
export void Scale(uniform float input[], uniform float scale,
                  uniform float output[], uniform int count)
{
    foreach (i = 0 ... count)
        output[i] = input[i] * scale;   /* this one line is 8 lanes on AVX2 */
}
```

The code inside `foreach` is written "from one element's point of view" like a GPU shader, but it actually executes in units of the vector lane width — the GPU's SIMT model from Part 2, reproduced in software on top of a CPU vector unit. Comparing the approach with Unity's lays out like this.

| | Unity Burst | Unreal ISPC |
|---|------------|-------------|
| Language | C# as-is | Dedicated language (C-like) |
| Who vectorizes | LLVM auto-vectorization + optional intrinsics | The compiler always vectorizes via the SPMD model |
| Multi-target | Per-platform compilation (SSE2/AVX2 dispatch) | Code generated per ISA, chosen at runtime |
| Scope | All Job code | Designated modules such as physics and cloth |

The approaches differ, but they arrive at the same place. Both engines converged on the same conclusion: leave gameplay code alone and vectorize only the system layer that churns through bulk data.

### Physics Middleware — Jolt Physics and Horizon Forbidden West

The best example outside of engines is **Jolt Physics**. It is the open-source physics engine used by Horizon Forbidden West and Death Stranding 2, and it supports compile targets from SSE4.1 through AVX-512 on x86 and NEON on ARM64 — the hot loops of collision detection and the rigid body solver all sit on SIMD.

The numbers Guerrilla Games published at GDC 2022 sum up the effect of data-oriented design with SIMD. Replacing a commercial physics engine with Jolt **doubled the simulation frequency while reducing memory and executable size, and used less CPU time on top of that**. Physics is a textbook specimen of the "identical operation × bulk contiguous data" pattern, so it is a domain where every condition discussed in this post is satisfied.

### Unity — From First-Party Packages to Shipped Games

The first thing to look at on the Unity side is that **Unity itself practices the three tiers of Part 5 exactly as written**.

- **Unity Physics**: a stateless DOTS-based physics engine whose collision detection and solver are entirely Burst Jobs on top of Unity.Mathematics — a large-scale, in-production instance of tier 2 (SIMD-friendly types + auto-vectorization). What Jolt did with C++ intrinsics, Unity did with C# + Burst
- **xxHash3 in Unity.Collections**: one hash function ships with two implementations — a general-purpose one built on Unity.Mathematics, and a **Burst intrinsics implementation** used on AVX2-capable platforms. Per the official docs, the intrinsics implementation yields an additional 30–50% on large data — a specimen that shows both the principle "descend to tier 3 only for verified bottlenecks" and the cost "once you descend, you maintain two platform-specific copies"

On the shipped-game side, V Rising (2022, released on ECS) and Cities: Skylines II serve as validation. CS2 in particular runs city-wide citizen and traffic simulation on ECS + Burst, and remains the largest commercial DOTS game to date.

CS2 also carries a cautionary lesson. Analyses of the performance controversy right after release found the bottleneck was not the Burst-compiled simulation but **the GPU rendering side** (excessive vertex counts, missing LODs, and so on). No matter how fast you make the simulation layer with SIMD, frame time is decided by the slowest bottleneck — a demonstration at commercial-game scale of the question "is compute the bottleneck?" that the next part will formalize.

The common thread running through these cases is that SIMD **concentrates in the system layer**. Physics (Jolt, Chaos, Unity Physics), animation (ISPC), transform math (VectorRegister), utilities like hashing (xxHash3), bulk simulation (DOTS) — all of it is engine and middleware level, and in none of these cases is the gameplay code above it a vectorization target. Part 7's criteria, in other words, line up with what the whole industry actually does.

---

## Part 7: Deciding Where to Apply It and Where Not To

### Layout Comes First

SIMD sits near the last rung of the optimization ladder. By the time you consider applying it, two things should already be settled.

1. **Is the data laid out contiguously in SoA form?** Code that iterates over scattered `GameObject` fields is not a vectorization candidate at all. The layout change alone yields the first gain from cache efficiency, and SIMD is a factor multiplied on top of that
2. **Is compute the bottleneck?** Once the data grows past the cache, the bottleneck moves to memory bandwidth, and quadrupling the ALUs does nothing when data supply cannot keep up. The 1 million elements (4 MB) in my benchmark fit inside the M4 Pro's L2 cache, which is why the compute bottleneck held

The workloads that pass both conditions are fairly well defined in games. Particle simulation, procedural mesh generation, movement and distance calculation for large unit counts, audio DSP — the "identical operation × bulk contiguous data" pattern. Conversely, general gameplay logic — code full of state branches where each object is handled differently — fails the very first precondition of "identical operation," so it is not up for consideration. A rebuttal comment on the original article argued that "every programmer should know this" is an overstatement, and restricted to game programmers I think the rebuttal is right. The people who need to know are the ones building the systems in that list; for everyone else Burst's auto-vectorization is enough.

### The Question Before SIMD — Does Your Data Structure Chase Pointers?

Condition 1 above ("is the data laid out in SoA form?") actually hides a harder question: **is this a data structure that can be expressed as an array at all?** Trees and graphs, where nodes reference one another, are not fixed by "changing the layout" to SoA.

The reason pointer chasing is the natural enemy of vectorization is specific. The address you read next **lives inside the value you are reading right now.** A load has to complete before the address of the next load is known, so memory accesses become serialized, the hardware prefetcher cannot predict where to go next, and the contiguous 128 bits a vector load demands never exist in the first place. In Part 4 the scalar sum was slow because it was bound to the latency of floating-point addition; pointer chasing is that same serial dependency, except bound to **memory latency** — hundreds of cycles on a cache miss. Layering SIMD on top accomplishes nothing, because compute was never the bottleneck.

The fix is not SIMD but **linearization**: replace pointers with array indices and put the nodes in one contiguous arena. This is exactly what Rendello described on HN — taking a pointer-based tree scattered across the heap and turning it into a linearized array structure to raise cache efficiency.

```csharp
/* Before — pointer chasing: a cache miss per node, no vectorization possible */
class Node { Node left, right; float bound; }

/* After — index references: nodes sit contiguously, traversal becomes a linear scan */
struct Node { int left, right; float bound; }   /* indices into a NativeArray<Node> */
```

The transformation pays off even setting SIMD aside. An index is 32 bits, so nodes shrink relative to 64-bit pointers; the whole array can be serialized, copied, and relocated as a block; and there are no references left for the GC to trace. In Unity, if you want a tree inside a `NativeArray`, this form is the only option anyway.

Push one step further and you reach the most counterintuitive point in this article. **The vector width changes the branching factor of your data structure.** Instead of stopping at linearizing a binary tree, you redesign it to hold four children — so that testing one node compares four children's bounds across four lanes at once.

Unity Physics' BVH is built exactly that way. The fields of `BoundingVolumeHierarchy.Node` are `FourTransposedAabbs Bounds` and `int4 Data`, with up to four children. The "Transposed" in the name is the essential part: instead of storing four AABBs side by side, it transposes them per axis — four minimum-x values, then four minimum-y values, and so on. It is SoA applied inside a single node, and it turns intersection testing against four children into a handful of four-lane comparisons. **The reason this is a 4-way BVH rather than a binary one is register width, not algorithms.**

Rendello's principle — that a data representation should be tied to access patterns rather than dogma — gets pushed this far in game engines. When the access pattern is bound to the hardware, the representation ends up bound to the hardware too.

Which is why the "premature optimization" wariness is only half right. **Bolting SIMD code on later is indeed premature optimization, but which data structure to use is not a decision you can defer.** Converting a pointer tree into a 4-way arena is a structural change that touches every call site, so starting it after the profiler has already named your bottleneck is starting too late. That is what makes the HN comment about "putting high-performance racing tires on a lemon with a broken engine" so accurate — the question is not when you fit the tires, but whether the chassis was ever built to take them.

### There Is No SIMD Without Verification

Finally, the most practical single line of advice in the original article, translated into the Unity context: **don't believe it vectorized — check the assembly.** If your code leans on auto-vectorization (tier 1), confirm in Burst Inspector that vector instructions like `fadd v0.4s` were actually emitted, and plant a `Loop.ExpectVectorized()` to catch regressions at compile time. Even code written explicitly (tier 3) cannot claim a gain without before-and-after profiling — the 3.6x in this post is a number I can state because I measured it.

---

## Summary

| Question | Answer |
|------|-----|
| Why SIMD is fast | It computes 4 lanes of a 128-bit vector register with one instruction — the theoretical ceiling is a multiple of the vector width |
| A dedicated pipeline? | No. Not a separate device like a GPU but an execution port inside the core — zero offload cost, scale capped at core count × lane count |
| Hardware landscape | Intel consumer CPUs (i9 included) top out at AVX2 256-bit, Zen 5 is native 512-bit, and Radeon is a SIMD machine built from two SIMD32 units per CU (SIMT model) |
| CPUs without SIMD? | If it's 64-bit it has SIMD — SSE2 is mandatory on x86-64, NEON on AArch64. The question is width, not presence |
| Industry cases | Unreal uses VectorRegister (the floor of its math) + ISPC (Chaos, cloth), Jolt Physics (Horizon Forbidden West) covers SSE4.1–AVX-512 and NEON, and Unity has Unity Physics and xxHash3 (first-party packages) plus V Rising and Cities: Skylines II (shipped games) |
| Old-CPU risk | An unsupported instruction means instant death by Illegal Instruction (the Cyberpunk 2077 AVX and Helldivers 2 AVX2 cases). The fix is runtime dispatch — Burst's desktop default already works this way |
| How to write explicit SIMD | The fixed five stages of broadcast → vector traversal → lane-parallel operation → reduction → tail, with branches turned into mask arithmetic |
| Measured gain (M4 Pro, .NET 10) | 3.6x on summing 1M floats, 2.7x on match counting — the ratio is set by what the scalar side is bound on |
| The path in Unity | Burst is the only trustworthy path. Descend in order from auto-vectorization to Unity.Mathematics float4 to Burst Intrinsics v128, and check with Burst Inspector before each step down |
| Trees and graphs | Pointer chasing is serialized on memory latency and cannot be vectorized → linearizing into index arrays comes first. Beyond that, the vector width sets the branching factor (Unity Physics' BVH is 4-way with `FourTransposedAabbs`) |

## Series Links

- [Unity Job System and Burst](/posts/UnityJobSystemBurst/) — Job, NativeContainer, and Burst basics plus memory alignment
- [SoA vs AoS](/posts/SoAvsAoS/) — the data layout that SIMD presupposes
- [Burst Compiler Deep Dive](/posts/BurstCompilerDeepDive/) — success and failure conditions of auto-vectorization and a Burst Inspector walkthrough
- This post — SIMD hardware principles and writing explicit SIMD

## References

### Primary Sources · Official Documentation

- Mitchell Hashimoto, *SIMD Basics* — <https://mitchellh.com/writing/simd-basics>
- .NET `Vector<T>` API — <https://learn.microsoft.com/dotnet/api/system.numerics.vector-1>
- Unity Burst Manual, *CPU Intrinsics* — <https://docs.unity3d.com/Packages/com.unity.burst@latest/manual/csharp-burst-intrinsics.html>
- Arm NEON Intrinsics Reference — <https://developer.arm.com/architectures/instruction-sets/intrinsics/>
- AMD, *RDNA Architecture Whitepaper* — <https://gpuopen.com/download/RDNA_Architecture_public.pdf>

### Hardware Analysis

- Phoronix, *Quantifying The AVX-512 Performance Impact With AMD Zen 5* — <https://www.phoronix.com/review/amd-zen5-avx-512-9950x>
- Chips and Cheese, *Zen 5's AVX-512 Frequency Behavior* — <https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior>
- Tom's Hardware, *Ryzen 9000 CPUs drop 10% frequency executing AVX-512* — <https://www.tomshardware.com/pc-components/cpus/ryzen-9000-cpus-drop-10-frequency-executing-avx-512-instructions-intel-cpus-typically-suffer-from-more-substantial-clock-speed-drops>
- TechPowerUp, *Intel Officially Confirms AVX10.2 and APX Support in "Nova Lake"* — <https://www.techpowerup.com/342881/intel-officially-confirms-avx10-2-and-apx-support-in-nova-lake>
- XDA, *A Helldivers 2 update is giving players with older CPUs hell* — <https://www.xda-developers.com/helldivers-2-update-avx2-bug/>
- Nixxes Support, *This game requires a CPU that supports the AVX2 instruction set* — <https://support.nixxes.com/hc/en-us/articles/24667980191645-This-game-requires-a-CPU-that-supports-the-AVX2-instruction-set>

### Game Industry Cases

- Intel, *Unreal Engine's New Chaos Physics System Screams With In-Depth Intel CPU Optimizations* — <https://www.intel.com/content/www/us/en/developer/articles/technical/unreal-engines-new-chaos-physics-system-screams-with-in-depth-intel-cpu-optimizations.html>
- GDC 2020, *Intel ISPC in Unreal Engine 4 — A Peek Behind the Curtain* — <https://gdcvault.com/play/1026686/Intel-ISPC-in-Unreal-Engine>
- Guerrilla Games, *Architecting Jolt Physics for Horizon Forbidden West* (GDC 2022) — <https://www.guerrilla-games.com/read/architecting-jolt-physics-for-horizon-forbidden-west>
- Jolt Physics (GitHub) — <https://github.com/jrouwe/JoltPhysics>
- paavohtl, *Why Cities: Skylines 2 performs poorly* — <https://blog.paavo.me/cities-skylines-2-performance/>
- Unity Physics Manual — <https://docs.unity3d.com/Packages/com.unity.physics@1.0/manual/index.html>
- Unity.Collections `xxHash3` API (describes the dual implementation) — <https://docs.unity3d.com/Packages/com.unity.collections@2.6/api/Unity.Collections.xxHash3.html>
- Unity Physics `BoundingVolumeHierarchy.Node` API (`FourTransposedAabbs` + `int4`) — <https://docs.unity3d.com/Packages/com.unity.physics@0.3/api/Unity.Physics.BoundingVolumeHierarchy.Node.html>

### Data-Oriented Design

- Rendello's Hacker News comments on Data-Oriented Design — <https://hn.algolia.com/?query=Data-Oriented%20Design%20author%3ARendello&sort=byPopularity&type=all>
- Richard Fabian, *Data-Oriented Design* — <https://www.dataorienteddesign.com/dodbook/>

### Community · Discussion

- GeekNews summary and comment thread — <https://news.hada.io/topic?id=31734>
- Arm Learning Path, *Using NEON intrinsics to optimize Unity on Android* — <https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/using-neon-intrinsics-to-optimize-unity-on-android/>

### Measurement Tools

- BenchmarkDotNet — <https://benchmarkdotnet.org/>
