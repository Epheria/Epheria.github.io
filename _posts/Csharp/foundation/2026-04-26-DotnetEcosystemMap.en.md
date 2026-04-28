---
title: .NET Ecosystem Map — How Language, Runtime, and BCL Fit Together
lang: en
date: 2026-04-26 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, clr, bcl, il, runtime, mono, il2cpp]
toc: true
toc_sticky: true
difficulty: beginner
tldr:
  - C# is a language, .NET is a platform, CLR is a runtime. They sound like the same thing, but they live on different layers.
  - C# code is compiled into an intermediate language called IL. The runtime then translates that IL into native code via JIT or AOT.
  - Unity runs on its own runtime — Mono or IL2CPP — and uses a subset of .NET. The accurate statement is not "Unity is not .NET" but "Unity uses a specific implementation of .NET."
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: The ambiguity behind ".NET"

In developer documentation, resumes, and blog posts, the word ".NET" is used with a surprisingly wide range of meanings.

- "I build backends with .NET"
- "This project targets .NET Framework 4.8 only"
- "We migrated to .NET 8"
- "Unity is not .NET" / "Unity is basically .NET"

The same word floats ambiguously across **language, runtime, standard library, and application framework**. Without sorting this out once, nearly every episode of this C# series ends up wobbling on that ambiguity.

This post has exactly one goal: **being able to tell which layer ".NET" is pointing to in any given context**.

History (part 2) and runtime variants (part 3) come later. Today, the goal is to draw the **map**.

---

## Part 1. Six Layers

.NET is not a single technology — it is a **tower of six stacked layers**. Separating them one by one makes it possible to say which layer ".NET" is referring to at any moment.

<div class="dotnet-stack-container">
<svg viewBox="0 0 720 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET stack layer diagram">
  <defs>
    <linearGradient id="dotnet-stack-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.18"/>
    </linearGradient>
  </defs>

  <text x="360" y="30" text-anchor="middle" class="dotnet-stack-title">.NET Six Layers — Top to Bottom</text>

  <g class="dotnet-stack-layer" data-layer="6">
    <rect x="60" y="60" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="85" class="dotnet-stack-name">6. Application Framework</text>
    <text x="80" y="106" class="dotnet-stack-desc">ASP.NET Core · WinForms · WPF · MAUI · Unity · Xamarin</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="5">
    <rect x="60" y="128" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="153" class="dotnet-stack-name">5. BCL (Base Class Library)</text>
    <text x="80" y="174" class="dotnet-stack-desc">System.* · System.Collections · System.IO · System.Threading</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="4">
    <rect x="60" y="196" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="221" class="dotnet-stack-name">4. Runtime</text>
    <text x="80" y="242" class="dotnet-stack-desc">CLR · CoreCLR · Mono · IL2CPP · NativeAOT</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="3">
    <rect x="60" y="264" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="289" class="dotnet-stack-name">3. IL (Intermediate Language)</text>
    <text x="80" y="310" class="dotnet-stack-desc">Hardware-independent intermediate bytecode · stored inside .dll / .exe</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="2">
    <rect x="60" y="332" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="357" class="dotnet-stack-name">2. Compiler</text>
    <text x="80" y="378" class="dotnet-stack-desc">Roslyn (csc) · translates source code into IL</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="1">
    <rect x="60" y="400" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="425" class="dotnet-stack-name">1. Language</text>
    <text x="80" y="446" class="dotnet-stack-desc">C# · F# · VB.NET</text>
  </g>
</svg>
</div>

<style>
.dotnet-stack-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-stack-container svg { width: 100%; max-width: 720px; height: auto; display: block; margin: 0 auto; }
.dotnet-stack-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-stack-box { fill: url(#dotnet-stack-grad); stroke: #6366f1; stroke-width: 1.2; }
.dotnet-stack-name { font-size: 15px; font-weight: 700; fill: #1e293b; }
.dotnet-stack-desc { font-size: 13px; fill: #475569; }
[data-mode="dark"] .dotnet-stack-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-stack-box { stroke: #818cf8; }
[data-mode="dark"] .dotnet-stack-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-stack-desc { fill: #94a3b8; }
@media (max-width: 768px) {
  .dotnet-stack-name { font-size: 13px; }
  .dotnet-stack-desc { font-size: 11px; }
}
</style>

Each layer **depends only on the layer directly beneath it**. C# code passes through Roslyn to become IL; IL is interpreted by the Runtime; the Runtime provides the BCL as its standard library; Application Frameworks run on top of all that.

The word ".NET" points to **whichever layer** the context calls for. Every discussion from here on uses this map as its reference.

---

## Part 2. C# and .NET

The most common source of confusion comes first.

### C# is a language

C# is a programming language standardized as **ECMA-334** and **ISO/IEC 23270**. A specification document defines its syntax and type system, and the compiler (Roslyn) implements that document. C# is a concept **at the same level as Java**.

### .NET is a platform

.NET is **the name of the ecosystem** that encompasses language, runtime, BCL, SDK, and application frameworks together. It refers collectively to layers 2 through 6 in the diagram above.

### Two different things

All four of the following are **distinct statements**:

| Statement | What it refers to |
|------|---------------|
| "I wrote it in C#" | Layer 1 (language) — compiler and runtime unspecified |
| "I wrote it targeting .NET 8" | All of layers 2–6 — a specific version |
| "It only runs on .NET Framework 4.8" | The Windows-only .NET implementation |
| "Unity's C#" | C# language + Unity's specific runtime (Mono or IL2CPP) |

To answer "aren't C# and .NET the same thing?": **C# is one layer (language) within .NET**.

---

## Part 3. IL — Why the Middle Layer Exists

The layer worth paying the most attention to in the diagram is **layer 3, IL**. Once this clicks, every later runtime discussion becomes easier.

### The compile and execution pipeline

<div class="dotnet-pipeline-container">
<svg viewBox="0 0 820 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="C# compile and execution pipeline">
  <defs>
    <marker id="dotnet-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="dotnet-arrow-head"/>
    </marker>
  </defs>

  <text x="410" y="26" text-anchor="middle" class="dotnet-pipeline-title">The Boundary Between Compile Time and Execution Time</text>

  <g class="dotnet-pipeline-step">
    <rect x="20" y="100" width="120" height="60" rx="8" class="dotnet-step-source"/>
    <text x="80" y="128" text-anchor="middle" class="dotnet-step-name">C# Source</text>
    <text x="80" y="146" text-anchor="middle" class="dotnet-step-sub">.cs</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="180" y="100" width="120" height="60" rx="8" class="dotnet-step-compiler"/>
    <text x="240" y="128" text-anchor="middle" class="dotnet-step-name">Roslyn (csc)</text>
    <text x="240" y="146" text-anchor="middle" class="dotnet-step-sub">Compiler</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="340" y="100" width="120" height="60" rx="8" class="dotnet-step-il"/>
    <text x="400" y="128" text-anchor="middle" class="dotnet-step-name">IL</text>
    <text x="400" y="146" text-anchor="middle" class="dotnet-step-sub">.dll / .exe</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="60" width="140" height="60" rx="8" class="dotnet-step-jit"/>
    <text x="570" y="88" text-anchor="middle" class="dotnet-step-name">JIT</text>
    <text x="570" y="106" text-anchor="middle" class="dotnet-step-sub">Execution-time translation</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="140" width="140" height="60" rx="8" class="dotnet-step-aot"/>
    <text x="570" y="168" text-anchor="middle" class="dotnet-step-name">AOT</text>
    <text x="570" y="186" text-anchor="middle" class="dotnet-step-sub">Build-time translation</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="680" y="100" width="120" height="60" rx="8" class="dotnet-step-native"/>
    <text x="740" y="128" text-anchor="middle" class="dotnet-step-name">Native Code</text>
    <text x="740" y="146" text-anchor="middle" class="dotnet-step-sub">x86 / ARM</text>
  </g>

  <line x1="140" y1="130" x2="175" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="300" y1="130" x2="335" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="120" x2="495" y2="95" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="140" x2="495" y2="165" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="95" x2="680" y2="125" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="165" x2="680" y2="140" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>

  <line x1="460" y1="220" x2="460" y2="40" class="dotnet-pipeline-divider"/>
  <text x="240" y="240" text-anchor="middle" class="dotnet-pipeline-label">Compile time (build machine)</text>
  <text x="650" y="240" text-anchor="middle" class="dotnet-pipeline-label">Execution time or pre-deployment</text>
</svg>
</div>

<style>
.dotnet-pipeline-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-pipeline-container svg { width: 100%; max-width: 820px; height: auto; display: block; margin: 0 auto; }
.dotnet-pipeline-title { font-size: 16px; font-weight: 700; fill: #1f2937; }
.dotnet-step-source { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.2; }
.dotnet-step-compiler { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.dotnet-step-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.dotnet-step-jit { fill: #cffafe; stroke: #06b6d4; stroke-width: 1.2; }
.dotnet-step-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1.2; }
.dotnet-step-native { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.dotnet-step-name { font-size: 14px; font-weight: 700; fill: #1e293b; }
.dotnet-step-sub { font-size: 11px; fill: #475569; }
.dotnet-pipeline-line { stroke: #6366f1; stroke-width: 1.8; fill: none; }
.dotnet-arrow-head { fill: #6366f1; }
.dotnet-pipeline-divider { stroke: #94a3b8; stroke-dasharray: 4 4; stroke-width: 1; }
.dotnet-pipeline-label { font-size: 12px; fill: #64748b; font-style: italic; }
[data-mode="dark"] .dotnet-pipeline-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-step-source { fill: rgba(99,102,241,0.2); stroke: #818cf8; }
[data-mode="dark"] .dotnet-step-compiler { fill: rgba(217,119,6,0.2); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-step-il { fill: rgba(124,58,237,0.2); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-step-jit { fill: rgba(6,182,212,0.2); stroke: #22d3ee; }
[data-mode="dark"] .dotnet-step-aot { fill: rgba(16,185,129,0.2); stroke: #34d399; }
[data-mode="dark"] .dotnet-step-native { fill: rgba(236,72,153,0.2); stroke: #f472b6; }
[data-mode="dark"] .dotnet-step-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-step-sub { fill: #94a3b8; }
[data-mode="dark"] .dotnet-pipeline-line { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .dotnet-pipeline-divider { stroke: #475569; }
[data-mode="dark"] .dotnet-pipeline-label { fill: #94a3b8; }
@media (max-width: 768px) {
  .dotnet-step-name { font-size: 12px; }
  .dotnet-step-sub { font-size: 10px; }
}
</style>

### Why insert a middle layer (IL)?

In C, the compiler translates source code directly into native code. A `.c` file becomes a Windows x64 `.exe` or a Linux ARM64 binary. The result of a single compilation is **locked to a specific OS + CPU combination**.

.NET splits this structure in two. C# source is first translated only into **IL (Intermediate Language)**, a hardware-independent and OS-independent intermediate bytecode. The actual native translation happens **at execution time** (JIT) or **just before deployment** (AOT) — after the target machine is known.

This design delivers three benefits.

**① Platform independence.** The same `.dll` runs on Windows, Linux, and macOS. The runtime handles translation into the machine's native instructions.

**② Language independence.** Because any language only needs to produce IL, F# and VB.NET can share the same runtime and BCL as C#. The lower layers stay unchanged regardless of which language is used.

**③ Runtime optimization.** JIT can optimize using **real hardware characteristics and runtime statistics**. The trade-off is translating later than a static compiler, in exchange for access to more information.

### JIT and AOT — Same IL, Different Translation Timing

There are two points in time at which IL can be translated to native code.

- **JIT (Just-In-Time)**: translates **on the target machine**, **at the moment of execution**. Translation cost is included in execution time, but hardware information is known precisely. Standard desktop .NET and Mono use this approach.
- **AOT (Ahead-Of-Time)**: translates to native code **before deployment**. No JIT is needed at execution time. **On platforms like iOS that do not allow JIT**, this is the only option. IL2CPP and NativeAOT use this approach.

This boundary explains the Unity Mono vs IL2CPP choice, mobile and console build pitfalls, and why `Reflection.Emit` breaks under IL2CPP. The details are covered in part 3.

---

## Part 4. Runtime and BCL — The Two Pillars of Execution

Layers 1 through 3 were about "what is produced from source code." Layers 4 and 5 are about "how what was produced actually runs."

### Runtime — the engine that actually runs IL

The **Runtime** is the engine that reads IL, translates it to native code, and executes it. It handles memory management (GC), exception handling, the type system, thread management, and security. The Microsoft glossary defines it as:

> A CLR handles memory allocation and management. A CLR is also a virtual machine that not only executes apps but also generates and compiles code on-the-fly using a JIT compiler. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

The key point is that **there is not just one runtime**.

- **CLR** — the runtime for .NET Framework. Windows only.
- **CoreCLR** — the runtime for .NET 5+ (formerly .NET Core). Cross-platform.
- **Mono** — an open-source cross-platform implementation. Unity's default runtime.
- **IL2CPP** — an AOT runtime built by Unity. Converts IL to C++ and then compiles natively.
- **NativeAOT** — the official .NET AOT deployment mode.

Even with the same C# code and the same IL, **which runtime it runs on** determines performance characteristics, memory behavior, and which features are available.

### BCL — the standard library every runtime provides by default

The **BCL (Base Class Library)** is the standard library under the `System.*` namespace. `Console.WriteLine`, `List<T>`, `Dictionary<K,V>`, `File.ReadAllText`, `Task`, `CancellationToken` — nearly everything used without a second thought is part of the BCL.

The Microsoft glossary defines it as:

> A set of libraries that comprise the `System.*` (and to a limited extent `Microsoft.*`) namespaces. The BCL is a general purpose, lower-level framework that higher-level application frameworks, such as ASP.NET Core, build on. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

The BCL's position in one sentence: **"The runtime is the engine that runs IL; the BCL is the standard library shipped with that engine."** Without the library, even a single `Console.WriteLine("hi")` cannot run.

### Relationship between the three terms

| Term | Layer | Example | Role |
|------|-----|------|------|
| Assembly | Layer 3 (IL bundle) | `MyApp.dll`, `System.Collections.dll` | File unit containing IL |
| Runtime | Layer 4 | CLR / CoreCLR / Mono / IL2CPP | Engine that actually runs IL |
| BCL | Layer 5 | `System.*` namespace | Standard library shipped with the runtime |

When someone says "install the .NET Runtime," they typically mean installing the **layer 4 (engine) + layer 5 (BCL)** bundle. These two are almost always deployed together.

---

## Part 5. SDK vs Runtime — Developer vs End User

One question always comes up when talking about deployment: **"Should I install the SDK or the Runtime?"**

The answer depends on the role.

- **SDK (Software Development Kit)**: needed by anyone **building** an app. Includes the compiler, CLI tools (`dotnet`), the runtime, BCL, and project templates.
- **Runtime**: needed by anyone who only needs to **run** an app. Contains the engine (layer 4) and BCL (layer 5) only. No compiler.

The commands to check what is installed:

```bash
$ dotnet --list-sdks
8.0.404 [/usr/local/share/dotnet/sdk]
10.0.100 [/usr/local/share/dotnet/sdk]

$ dotnet --list-runtimes
Microsoft.NETCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
Microsoft.AspNetCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.AspNetCore.App]
Microsoft.NETCore.App 10.0.0 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
```

Developer machines typically have the SDK installed, which includes the runtime. Servers and end-user machines only need the runtime.

That said, a **self-contained deployment** bundles the runtime inside the app itself, so the target machine needs nothing installed. Building with NativeAOT goes further and produces a single native binary. The choices available at layer 4 extend all the way here.

---

## Part 6. Where Unity Fits on the Map

Most readers of this blog are game programmers. The map is not complete without marking **Unity's position** on it.

<div class="dotnet-unity-container">
<svg viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Where Unity sits in the .NET stack">
  <text x="380" y="28" text-anchor="middle" class="dotnet-unity-title">Unity and the .NET Stack — Three Paths</text>

  <g class="dotnet-unity-col" data-col="server">
    <rect x="30" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane"/>
    <text x="140" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Server / Desktop .NET</text>

    <rect x="50" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="140" y="120" text-anchor="middle" class="dotnet-unity-block-text">ASP.NET Core / WPF</text>

    <rect x="50" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="140" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET)</text>

    <rect x="50" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt"/>
    <text x="140" y="220" text-anchor="middle" class="dotnet-unity-block-text">CoreCLR (JIT)</text>

    <rect x="50" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="140" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="50" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="140" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>

  <g class="dotnet-unity-col" data-col="mono">
    <rect x="270" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane"/>
    <text x="380" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + Mono (Editor / Desktop)</text>

    <rect x="290" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="380" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="290" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="380" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard subset)</text>

    <rect x="290" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt"/>
    <text x="380" y="220" text-anchor="middle" class="dotnet-unity-block-text">Mono (JIT)</text>

    <rect x="290" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="380" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="290" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="380" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>

  <g class="dotnet-unity-col" data-col="il2cpp">
    <rect x="510" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane dotnet-unity-lane-accent"/>
    <text x="620" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + IL2CPP (iOS/WebGL/Console)</text>

    <rect x="530" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="620" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="530" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="620" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard subset)</text>

    <rect x="530" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt-aot"/>
    <text x="620" y="220" text-anchor="middle" class="dotnet-unity-block-text">IL2CPP (AOT → C++)</text>

    <rect x="530" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="620" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="530" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="620" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>
</svg>
</div>

<style>
.dotnet-unity-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-unity-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.dotnet-unity-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-unity-lane { fill: rgba(99,102,241,0.05); stroke: #cbd5e1; stroke-width: 1; }
.dotnet-unity-lane-accent { fill: rgba(236,72,153,0.06); stroke: #f472b6; }
.dotnet-unity-lane-label { font-size: 13px; font-weight: 700; fill: #475569; }
.dotnet-unity-block-app { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1; }
.dotnet-unity-block-bcl { fill: #fef3c7; stroke: #d97706; stroke-width: 1; }
.dotnet-unity-block-rt { fill: #cffafe; stroke: #06b6d4; stroke-width: 1; }
.dotnet-unity-block-rt-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1; }
.dotnet-unity-block-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1; }
.dotnet-unity-block-lang { fill: #f1f5f9; stroke: #94a3b8; stroke-width: 1; }
.dotnet-unity-block-text { font-size: 12px; font-weight: 600; fill: #1e293b; }
.dotnet-unity-block-text-sm { font-size: 11px; fill: #475569; }
[data-mode="dark"] .dotnet-unity-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-unity-lane { fill: rgba(99,102,241,0.1); stroke: #475569; }
[data-mode="dark"] .dotnet-unity-lane-accent { fill: rgba(236,72,153,0.12); stroke: #f472b6; }
[data-mode="dark"] .dotnet-unity-lane-label { fill: #cbd5e1; }
[data-mode="dark"] .dotnet-unity-block-app { fill: rgba(99,102,241,0.25); stroke: #818cf8; }
[data-mode="dark"] .dotnet-unity-block-bcl { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-unity-block-rt { fill: rgba(6,182,212,0.25); stroke: #22d3ee; }
[data-mode="dark"] .dotnet-unity-block-rt-aot { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .dotnet-unity-block-il { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-unity-block-lang { fill: rgba(148,163,184,0.15); stroke: #64748b; }
[data-mode="dark"] .dotnet-unity-block-text { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-unity-block-text-sm { fill: #cbd5e1; }
@media (max-width: 768px) {
  .dotnet-unity-block-text { font-size: 10px; }
  .dotnet-unity-block-text-sm { font-size: 9px; }
  .dotnet-unity-lane-label { font-size: 11px; }
}
</style>

All three paths **share the same C# and the same IL**. The only layers that differ are **layer 4 (runtime) and layer 6 (application framework)**. The reason Unity appears to be "not .NET" is simply that it **uses a different runtime**.

### Unity's two runtimes

- **Mono (JIT)** — the default for the Unity Editor and desktop builds. Builds are fast and well-suited for iterative development. Mono is explicitly listed in the Microsoft glossary as "one of the implementations of .NET." [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations)

- **IL2CPP (AOT)** — the default and mandatory choice for iOS, WebGL, and console targets. It converts IL into **C++ source**, then uses each platform's native toolchain (Xcode, Emscripten, console SDK) to produce a native binary. iOS does not allow JIT at the OS level, so Mono is simply not an option there. [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)

### What game programmers should take from this map

Three practical conclusions from this map.

**① The root cause of `Reflection.Emit` breaking under IL2CPP** is that IL2CPP has **no JIT to generate new IL at runtime**. A change at layer 4 propagates up to the behavior of APIs in the layers above.

**② Unity's "C#" is bound to the runtime and BCL combination Unity has chosen.** APIs available in server-side .NET may be absent in Unity, and vice versa. The **API Compatibility Level** setting in `.csproj` is exactly the switch that defines the scope of layer 5.

**③ The answer to "does Unity belong to the .NET ecosystem?" is clear.** It uses layers 1–3 (C#, Roslyn, IL) unchanged, and only at layer 4 (runtime) does it use a Unity-specific implementation. It is simply **a different implementation within the same ecosystem**.

---

## Summary

Three lines to close the map built today.

1. **C# is the language at layer 1**; **.NET is the platform spanning layers 2–6**. They are not at the same layer.
2. **The IL middle layer** is the core trade-off that enables language independence, platform independence, and runtime optimization.
3. **Multiple runtimes** (CLR, CoreCLR, Mono, IL2CPP, NativeAOT) coexist, and **which runtime the code runs on** determines the performance characteristics, constraints, and available APIs for the same code.

This map is the coordinate system every subsequent post in this series will reference. For any post going forward, start by asking: "which layer is this discussion about?"

---

## Next in the Series

- **Part 2. .NET History — From Framework to One .NET** — The lineage from .NET Framework 1.0 in 2002 through the .NET 5 unification in 2020 and up to .NET 10 today. Why "Core" was dropped from the name and why version 4 was skipped are both explained here.
- **Part 3. CLR, Mono, IL2CPP, NativeAOT — Comparing the Runtime Variants** — A comparison of the five layer-4 implementations across JIT/AOT, memory, reflection, and generics. This will be the most practically useful episode for game programmers.

---

## References

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · Official terminology reference
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · Implementation overview
- [Microsoft Learn — Common Language Runtime (CLR) overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR overview
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · Unity IL2CPP documentation
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP background
