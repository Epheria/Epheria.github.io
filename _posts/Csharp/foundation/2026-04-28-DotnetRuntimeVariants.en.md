---
title: CLR · Mono · IL2CPP · NativeAOT — Comparing the Runtime Branches
lang: en
date: 2026-04-28 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, clr, mono, il2cpp, nativeaot, jit, aot, runtime]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/DotnetEcosystemMap/
  - /posts/DotnetHistory/
tldr:
  - .NET runtimes broadly split into JIT (CLR · CoreCLR · Mono) and AOT (IL2CPP · NativeAOT · Mono Full AOT) families
  - AOT runtimes have advantages in startup time and deployment size, but break features like Reflection.Emit, dynamic generic instantiation, and Expression.Compile
  - The constraints game developers hit with IL2CPP stem from deliberate runtime design decisions — they are not Unity-specific problems
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: Same IL, Different Fate

The previous two episodes established that the **Runtime layer** of the .NET stack is divided into multiple implementations. This episode examines those implementations one by one.

At this point in time, the five runtimes with practical relevance are:

| Runtime | Belongs to | Introduced | Status |
|---------|-----------|------------|--------|
| **CLR** | .NET Framework | 2002 | Frozen (4.8.1) |
| **CoreCLR** | .NET 5+ | 2016 (Core 1.0) | Active |
| **Mono** | Xamarin · Unity | 2004 | Active (Unity fork) |
| **IL2CPP** | Unity | 2014 | Active |
| **NativeAOT** | .NET 7+ | 2022 | Active |

Even when you write the same C# code, **which runtime it runs on** dramatically affects performance, memory, available APIs, and deployment size. The goal of this episode is to distill those differences into **practical selection criteria**.

Five runtimes may look complex, but grasping **one single axis** brings most of it into focus. That axis is **JIT vs AOT**.

---

## Part 1. The Single Axis — JIT vs AOT

Episode 1 mentioned that there are two points in time when IL can be translated into native code. This translation timing is **the decisive factor that splits the five runtimes into two camps**.

<div class="dotnet-runtime-tree-container">
<svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Classification tree of 5 .NET runtimes by JIT and AOT">
  <text x="380" y="28" text-anchor="middle" class="runtime-tree-title">5 .NET Runtimes — JIT / AOT Classification</text>

  <g class="runtime-tree-root">
    <rect x="310" y="60" width="140" height="50" rx="8" class="runtime-tree-box-root"/>
    <text x="380" y="82" text-anchor="middle" class="runtime-tree-text-bold">IL</text>
    <text x="380" y="100" text-anchor="middle" class="runtime-tree-text-sm">(intermediate bytecode)</text>
  </g>

  <line x1="380" y1="110" x2="200" y2="160" class="runtime-tree-line"/>
  <line x1="380" y1="110" x2="560" y2="160" class="runtime-tree-line"/>

  <g class="runtime-tree-branch jit">
    <rect x="120" y="160" width="160" height="50" rx="8" class="runtime-tree-box-jit"/>
    <text x="200" y="182" text-anchor="middle" class="runtime-tree-text-bold">JIT Family</text>
    <text x="200" y="200" text-anchor="middle" class="runtime-tree-text-sm">Translate at runtime</text>
  </g>

  <g class="runtime-tree-branch aot">
    <rect x="480" y="160" width="160" height="50" rx="8" class="runtime-tree-box-aot"/>
    <text x="560" y="182" text-anchor="middle" class="runtime-tree-text-bold">AOT Family</text>
    <text x="560" y="200" text-anchor="middle" class="runtime-tree-text-sm">Translate at build time</text>
  </g>

  <line x1="200" y1="210" x2="80" y2="260" class="runtime-tree-line"/>
  <line x1="200" y1="210" x2="200" y2="260" class="runtime-tree-line"/>
  <line x1="200" y1="210" x2="320" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="440" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="560" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="680" y2="260" class="runtime-tree-line"/>

  <g class="runtime-tree-leaf">
    <rect x="20" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="80" y="282" text-anchor="middle" class="runtime-tree-text-bold">CLR</text>
    <text x="80" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET Framework</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="140" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="200" y="282" text-anchor="middle" class="runtime-tree-text-bold">CoreCLR</text>
    <text x="200" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET 5+</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="260" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="320" y="282" text-anchor="middle" class="runtime-tree-text-bold">Mono</text>
    <text x="320" y="300" text-anchor="middle" class="runtime-tree-text-sm">Unity default</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="380" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="440" y="282" text-anchor="middle" class="runtime-tree-text-bold">IL2CPP</text>
    <text x="440" y="300" text-anchor="middle" class="runtime-tree-text-sm">Unity iOS/WebGL</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="500" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="560" y="282" text-anchor="middle" class="runtime-tree-text-bold">NativeAOT</text>
    <text x="560" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET 7+</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="620" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="680" y="282" text-anchor="middle" class="runtime-tree-text-bold">Mono Full AOT</text>
    <text x="680" y="300" text-anchor="middle" class="runtime-tree-text-sm">Xamarin iOS</text>
  </g>
</svg>
</div>

<style>
.dotnet-runtime-tree-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-runtime-tree-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.runtime-tree-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.runtime-tree-box-root { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.4; }
.runtime-tree-box-jit { fill: #cffafe; stroke: #06b6d4; stroke-width: 1.4; }
.runtime-tree-box-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1.4; }
.runtime-tree-box-leaf { fill: #e0f2fe; stroke: #0284c7; stroke-width: 1.2; }
.runtime-tree-box-leaf-aot { fill: #ecfccb; stroke: #65a30d; stroke-width: 1.2; }
.runtime-tree-text-bold { font-size: 14px; font-weight: 700; fill: #1e293b; }
.runtime-tree-text-sm { font-size: 11px; fill: #475569; }
.runtime-tree-line { stroke: #94a3b8; stroke-width: 1.5; fill: none; }
[data-mode="dark"] .runtime-tree-title { fill: #e5e7eb; }
[data-mode="dark"] .runtime-tree-box-root { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .runtime-tree-box-jit { fill: rgba(6,182,212,0.25); stroke: #22d3ee; }
[data-mode="dark"] .runtime-tree-box-aot { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .runtime-tree-box-leaf { fill: rgba(2,132,199,0.25); stroke: #38bdf8; }
[data-mode="dark"] .runtime-tree-box-leaf-aot { fill: rgba(101,163,13,0.25); stroke: #a3e635; }
[data-mode="dark"] .runtime-tree-text-bold { fill: #f1f5f9; }
[data-mode="dark"] .runtime-tree-text-sm { fill: #cbd5e1; }
[data-mode="dark"] .runtime-tree-line { stroke: #64748b; }
@media (max-width: 768px) {
  .runtime-tree-text-bold { font-size: 11px; }
  .runtime-tree-text-sm { font-size: 9px; }
}
</style>

### JIT Family — CLR · CoreCLR · Mono

JIT (Just-In-Time) translates IL to native code **on the machine the app is running on, at the moment it runs**. The trade-offs are as follows.

**Advantages**
- Can pull hardware information from **the actual machine** and optimize accordingly
- Supports follow-up re-optimization using runtime execution statistics (Tiered Compilation, PGO)
- **Runtime code generation APIs** like **`Reflection.Emit`·`Expression.Compile`** work

**Disadvantages**
- JIT cost is paid at startup (slow Cold Start)
- The runtime must be installed on the target machine
- The JIT itself consumes memory and CPU

### AOT Family — IL2CPP · NativeAOT · Mono Full AOT

AOT (Ahead-Of-Time) translates IL to native code **before the app is deployed**, on the developer's build machine.

**Advantages**
- **Extremely fast Cold Start** — the translation cost has already been paid
- The only option on **platforms that do not allow JIT** (iOS, consoles, WebAssembly)
- No runtime installation required at deployment (NativeAOT ships as a single binary)

**Disadvantages**
- **Cannot create new code at runtime** → `Reflection.Emit` breaks
- **Dynamic generic instantiation is restricted** → cannot create a new `List<MyRuntimeType>` at runtime
- **Longer build times** — all IL is translated upfront
- All generic instantiations must be pre-generated → larger deployment binary

This single table is the foundation for every comparison that follows.

---

## Part 2. The Five Runtimes

### CLR — The .NET Framework Runtime

- Released: 2002
- Platform: Windows only
- Compilation: JIT
- Status: **Frozen**. .NET Framework 4.8.1 (2022) was the final release
- Notable: Tightly coupled with Windows-only upper frameworks such as WPF, WinForms, and WCF

There is no reason to choose CLR for new development. It is only relevant for maintaining legacy systems.

### CoreCLR — The Main Runtime of Modern .NET

- Released: 2016 (.NET Core 1.0), absorbed into .NET 5+ from 2020
- Platform: Windows · Linux · macOS · FreeBSD
- Compilation: **Tiered JIT** (Tier 0 fast initial translation → Tier 1 optimized recompilation)
- Notable: Supports **PGO (Profile-Guided Optimization)**, aggressively optimizing hot code using execution statistics

CoreCLR is a runtime that mitigates the JIT disadvantage (startup cost) with **Tiered Compilation**. It performs only a fast Tier 0 translation at startup, then later recompiles frequently called hot code to Tier 1. ([Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr))

It is the default runtime for server, web, desktop, and WASM — and the most actively evolving one.

### Mono — The Original Cross-Platform Runtime

- Released: 2004
- Platform: Windows · Linux · macOS · iOS · Android · WebAssembly
- Compilation: JIT by default, **Full AOT mode also available** (for environments where JIT is forbidden, such as iOS)
- Notable: Small footprint. Well-suited for mobile, embedded, and game engines

As seen in episode 2, Mono started as an external open-source project and eventually became a Microsoft-official implementation. In 2024, Microsoft transferred ownership to WineHQ and the upstream moved into maintenance mode, but **Unity runs its own fork**.

Selecting `Scripting Backend: Mono` in Unity uses this runtime for the editor and desktop builds.

### IL2CPP — Unity's AOT Pipeline

- Released: 2014
- Platform: iOS · WebGL · consoles (PS5 · Xbox · Switch) · Android · Windows · macOS
- Compilation: **AOT only**. Converts IL to **C++ code**, then produces a native binary using the platform's C++ toolchain (Xcode · Emscripten · console SDK)
- Notable: `Reflection.Emit` is forbidden, generic instantiation is restricted, build times increase

The reason IL2CPP exists can be summarized in one sentence: **"Because iOS, WebGL, and consoles do not allow JIT, and Unity chose to solve the performance and constraint problems that Mono Full AOT could not address with its own AOT pipeline."** ([Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)) The internal workings are explained with real examples in Unity's own ["An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) blog series.

### NativeAOT — Microsoft's Server and Cloud AOT

- Released: 2022 (.NET 7, console apps and library support — [.NET Blog — "Announcing .NET 7" (2022.11.08)](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/))
- 2023 (.NET 8, expanded ASP.NET Core support)
- Platform: Windows · Linux · macOS · iOS (experimental) · Android (experimental)
- Compilation: **AOT only**. Compiles IL directly to native code (no C++ intermediary)
- Notable: Deployable as a **single native binary**, no runtime installation required, extremely fast startup

NativeAOT targets **containers, serverless, and CLI tools**. The motivation differs from why game developers use IL2CPP (because the platform forbids JIT). The journey from experimental to official release is detailed in ["Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/). ([Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

---

## Part 3. Runtime Comparison Matrix

The five runtimes compared side by side along the same axes.

| Axis | CLR | CoreCLR | Mono | IL2CPP | NativeAOT |
|------|-----|---------|------|--------|-----------|
| **Compilation** | JIT | Tiered JIT | JIT (+Full AOT option) | AOT only | AOT only |
| **Cross-platform** | Windows | Win/Lin/Mac | Wide | All Unity-supported platforms | Win/Lin/Mac |
| **Cold Start** | Slow | Medium (Tier 0 is fast) | Medium | **Fast** | **Fastest** |
| **Re-optimization at runtime** | None | **Yes (PGO)** | Limited | None | None |
| **`Reflection.Emit`** | O | O | O | **X** | **X** |
| **`Expression.Compile`** | O | O | O | **Interpreted mode** | **Interpreted mode** |
| **Dynamic generic instantiation** | O | O | O | **Restricted** | **Restricted** |
| **Runtime install required** | O | O (or Self-contained) | O | X (bundled in engine) | **X** |
| **Deployment size** | Small (runtime separate) | Medium | Medium | Large (includes engine) | Medium |
| **Build time** | Fast | Fast | Fast | **Very slow** | **Slow** |
| **Primary use** | Legacy Windows | Server · web · desktop | Unity editor · desktop | Unity mobile · console | Serverless · CLI |

### Three Things to Take Away from This Table

**① The two AOT runtimes (IL2CPP and NativeAOT) share the same constraints.**
`Reflection.Emit`, `Expression.Compile`, and dynamic generics are all **features that depend on JIT**. In an AOT environment there is fundamentally no engine to generate new IL at runtime.

**② Cold Start is overwhelmingly in favor of AOT.**
JIT is forbidden on iOS for security reasons (the `W^X` memory principle), but AOT's **fast startup** is also a decisive advantage for serverless and CLI tools. Running `dotnet run` no longer requires paying hundreds of milliseconds in JIT cost every time.

**③ CoreCLR's Tiered JIT is a middle ground.**
It cannot eliminate JIT cost entirely, but it **"avoids the worst and pursues the best"** by translating quickly at Tier 0 and only re-optimizing frequently called code at Tier 1. This is why CoreCLR remains the default for server and web workloads.

---

## Part 4. The IL2CPP Build Pipeline in Detail

The description "IL2CPP converts IL to C++ and then compiles to native" can sound abstract. Here is the actual build pipeline visualized.

<div class="il2cpp-pipeline-container">
<svg viewBox="0 0 860 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="IL2CPP build pipeline">
  <defs>
    <marker id="il2cpp-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="il2cpp-arrow-head"/>
    </marker>
  </defs>

  <text x="430" y="28" text-anchor="middle" class="il2cpp-pipeline-title">IL2CPP Build Pipeline — From IL to Native Binary</text>

  <g>
    <rect x="20" y="90" width="130" height="60" rx="8" class="il2cpp-box-cs"/>
    <text x="85" y="118" text-anchor="middle" class="il2cpp-box-text-bold">C# Source</text>
    <text x="85" y="136" text-anchor="middle" class="il2cpp-box-text-sm">.cs</text>
  </g>

  <g>
    <rect x="180" y="90" width="130" height="60" rx="8" class="il2cpp-box-roslyn"/>
    <text x="245" y="118" text-anchor="middle" class="il2cpp-box-text-bold">Roslyn</text>
    <text x="245" y="136" text-anchor="middle" class="il2cpp-box-text-sm">C# → IL</text>
  </g>

  <g>
    <rect x="340" y="90" width="130" height="60" rx="8" class="il2cpp-box-il"/>
    <text x="405" y="118" text-anchor="middle" class="il2cpp-box-text-bold">IL</text>
    <text x="405" y="136" text-anchor="middle" class="il2cpp-box-text-sm">.NET Assemblies</text>
  </g>

  <g>
    <rect x="500" y="90" width="160" height="60" rx="8" class="il2cpp-box-converter"/>
    <text x="580" y="118" text-anchor="middle" class="il2cpp-box-text-bold">il2cpp.exe</text>
    <text x="580" y="136" text-anchor="middle" class="il2cpp-box-text-sm">IL → C++</text>
  </g>

  <g>
    <rect x="690" y="90" width="150" height="60" rx="8" class="il2cpp-box-native"/>
    <text x="765" y="114" text-anchor="middle" class="il2cpp-box-text-bold">Platform Toolchain</text>
    <text x="765" y="130" text-anchor="middle" class="il2cpp-box-text-sm">Xcode / Emscripten</text>
    <text x="765" y="144" text-anchor="middle" class="il2cpp-box-text-sm">Console SDK</text>
  </g>

  <line x1="150" y1="120" x2="175" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="310" y1="120" x2="335" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="470" y1="120" x2="495" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="660" y1="120" x2="685" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>

  <text x="85" y="178" text-anchor="middle" class="il2cpp-stage-label">1. Authoring</text>
  <text x="245" y="178" text-anchor="middle" class="il2cpp-stage-label">2. IL compile</text>
  <text x="405" y="178" text-anchor="middle" class="il2cpp-stage-label">3. IL artifact</text>
  <text x="580" y="178" text-anchor="middle" class="il2cpp-stage-label">4. C++ conversion (Unity)</text>
  <text x="765" y="178" text-anchor="middle" class="il2cpp-stage-label">5. Native build</text>
</svg>
</div>

<style>
.il2cpp-pipeline-container { margin: 1.5rem 0; overflow-x: auto; }
.il2cpp-pipeline-container svg { width: 100%; max-width: 860px; height: auto; display: block; margin: 0 auto; }
.il2cpp-pipeline-title { font-size: 16px; font-weight: 700; fill: #1f2937; }
.il2cpp-box-cs { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.2; }
.il2cpp-box-roslyn { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.il2cpp-box-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.il2cpp-box-converter { fill: #d1fae5; stroke: #10b981; stroke-width: 1.4; }
.il2cpp-box-native { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.il2cpp-box-text-bold { font-size: 14px; font-weight: 700; fill: #1e293b; }
.il2cpp-box-text-sm { font-size: 11px; fill: #475569; }
.il2cpp-line { stroke: #6366f1; stroke-width: 1.8; fill: none; }
.il2cpp-arrow-head { fill: #6366f1; }
.il2cpp-stage-label { font-size: 11px; fill: #64748b; font-style: italic; }
[data-mode="dark"] .il2cpp-pipeline-title { fill: #e5e7eb; }
[data-mode="dark"] .il2cpp-box-cs { fill: rgba(99,102,241,0.25); stroke: #818cf8; }
[data-mode="dark"] .il2cpp-box-roslyn { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .il2cpp-box-il { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .il2cpp-box-converter { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .il2cpp-box-native { fill: rgba(236,72,153,0.25); stroke: #f472b6; }
[data-mode="dark"] .il2cpp-box-text-bold { fill: #f1f5f9; }
[data-mode="dark"] .il2cpp-box-text-sm { fill: #cbd5e1; }
[data-mode="dark"] .il2cpp-line { stroke: #a78bfa; }
[data-mode="dark"] .il2cpp-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .il2cpp-stage-label { fill: #94a3b8; }
@media (max-width: 768px) {
  .il2cpp-box-text-bold { font-size: 11px; }
  .il2cpp-box-text-sm { font-size: 9px; }
  .il2cpp-stage-label { font-size: 9px; }
}
</style>

### Why Insert C++ in the Middle

A compiler that goes **directly from IL to native code** is theoretically possible — that is exactly what NativeAOT does. Yet Unity chose the two-step **IL → C++ → native** path. The rationale is explained with real generated C++ examples in Unity's own ["IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) blog post. The summary is as follows.

**① Reuse of platform-specific C++ toolchains**
iOS uses Xcode LLVM, WebGL uses Emscripten, consoles use each manufacturer's SDK, Android uses NDK — every platform already has a **top-tier, highly optimized C++ compiler**. By converting IL to C++ alone, the remaining optimization is handled by the platform toolchain. Achieving the same quality without this approach would have required Unity to develop and maintain **a separate backend for every platform**.

**② Access to platform-specific features**
The C++ intermediary integrates naturally with each platform's native libraries and SDK. Building a direct AOT compiler would have made this integration far more complex.

**③ Debuggability**
When a runtime crash occurs in an IL2CPP build, the generated C++ code can be read. This is far easier to trace than pure binary output.

---

## Part 5. Five Constraints of AOT Environments

These are the key constraints of NativeAOT as stated in the official Microsoft documentation. IL2CPP shares **most of the same constraints**. ([Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

### ① `Reflection.Emit` Is Forbidden

**Symptom**: Code that dynamically creates methods or types at runtime using `System.Reflection.Emit` does not execute.

**Cause**: An AOT environment **has no JIT to receive IL and translate it to native code at runtime**. Emit is an API for producing IL, but without a translator to receive it, it cannot function.

**Impact**: Many serialization libraries (some paths in legacy `Newtonsoft.Json`), fast proxy generation (Castle DynamicProxy), and dynamic constructor injection in DI containers either break or slow down.

**Alternative**: **Source Generator**. Generating the required code at compile time eliminates the need for runtime Emit. `System.Text.Json` has moved in this direction and is AOT-friendly.

### ② `Expression.Compile` Falls Back to Interpreted Mode

**Symptom**: LINQ queries or `Expression<Func<T>>.Compile()` execute in **interpreter mode**. They are not as fast as compiled native code.

**Cause**: Expression compilation works by generating IL at runtime and JIT-compiling it — impossible in an AOT environment.

**Impact**: Performance may degrade for ORM (some EF Core paths) and repeatedly invoked LINQ-to-Expression code.

**Alternative**: Pre-convert frequently executed expressions to delegates ahead of time. Alternatively, evaluate Source Generator-based replacement libraries.

### ③ Dynamic Generic Instantiation Is Restricted

**Symptom**: Constructing **generic combinations that do not appear in the source code** at runtime — such as `Type.MakeGenericType(typeof(List<>), runtimeType)` — fails or throws an error.

**Cause**: The AOT compiler **pre-generates all generic instances at build time**. Combinations that did not exist at build time have no corresponding native code.

**Impact**: The common pattern of optimizing a `Dictionary<string, object>` to `Dictionary<string, RuntimeType>` based on a runtime type breaks.

**Alternative**: Use the generic combination explicitly at build time at least once (a "hint" such as `_ = new List<MyType>()`) or work around it with a non-generic version.

### ④ Reflection Interacts with the Trimmer

**Symptom**: String-based reflection such as `Type.GetMethod("SomeMethod")` fails unexpectedly — **because the trimmer determined that the method was unused and removed it**.

**Cause**: AOT deployment requires **trimming (Trimming)**. It removes unused code from the build output to reduce binary size, but string-based references cannot be statically analyzed.

**Impact**: Many older libraries throw runtime errors in AOT builds.

**Alternative**: Use the `DynamicDependency` attribute to hint the trimmer, or remove the reflection with a Source Generator.

### ⑤ Deployment Binary Size Increases

**Symptom**: An AOT build **bundles all generic instances, runtime libraries, and dependencies into a single binary**, making the file larger than a framework-dependent JIT build.

**Cause**: "Self-contained" is the default. Instead of requiring a runtime installation, the app carries everything with it.

**Impact**: Larger mobile app install size, larger container image size, longer deployment times.

**Alternative**: Aggressive trimming, `PublishTrimmed=true`, and disabling unnecessary feature flags.

---

## Part 6. Runtime Decision Guide

A concise decision tree for which runtime to choose by project type.

**Building a server or web API** → **CoreCLR** (.NET 8+). For high-load, low-latency, or fast-deployment requirements, **consider NativeAOT** — but always verify AOT constraints first.

**Building a CLI tool or serverless function** → **NativeAOT**. Cold Start is critical and the dependency footprint is small enough to accept AOT constraints.

**Building a game with Unity** → Editor and desktop builds use **Mono**. iOS, WebGL, and console builds use **IL2CPP** (mandatory). Desktop builds can also switch to IL2CPP for a performance boost.

**Starting a new Windows desktop app** → **CoreCLR + WPF/WinForms on .NET 8+**. Avoid CLR (.NET Framework).

**Maintaining a legacy .NET Framework system** → **CLR**. Plan a gradual migration of new feature development to .NET 8+.

**Building a mobile app (non-Unity)** → After Xamarin's end of support in 2024, **.NET MAUI** is the official path. Internally it uses a mix of Mono and NativeAOT.

---

## Summary

Four lines that capture the core of this episode.

1. **.NET runtimes split into JIT and AOT families**, and this single axis determines most of the performance characteristics, constraints, and deployment size.
2. **AOT constraints are design choices, not platform constraints**. The breakage of `Reflection.Emit`, dynamic generics, and `Expression.Compile` is a consequence of having no JIT at runtime — this is common to both IL2CPP and NativeAOT.
3. **The reason IL2CPP takes the IL → C++ → native two-step** is to reuse the high-level optimization already built into each platform's C++ toolchain.
4. **The constraints game programmers encounter in Unity** (Reflection.Emit, generic pitfalls, trimmer issues) are the inevitable consequence of runtime design, and **compile-time metaprogramming** such as Source Generators is the modern solution.

---

## Closing the Foundation Series

Across three episodes we explored **.NET's map (ep. 1) → history (ep. 2) → runtime branches (ep. 3)**. These three episodes serve as the **common coordinate system** for every C# series that follows.

The next series is the **async series (6 episodes)**. The JIT/AOT context covered today connects naturally to why `UniTask` is better suited to Unity than `Task`, how `async/await` is transformed under IL2CPP, and why Source Generators that avoid `Reflection.Emit` matter.

---

## References

### Primary Sources — Official Announcements and Technical Analysis

- [.NET Blog — "Announcing .NET 7"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/) · November 2022, official .NET 7 release announcement including the formal inclusion of NativeAOT
- [.NET Blog — "Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/) · Details on NativeAOT's promotion from `runtimelab` to `runtime`
- [Unity Blog — "An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) · IL2CPP internal architecture explained by Unity engineers
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · The IL → C++ conversion process through real generated C++ examples

### Reference Documentation

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · Official definitions of CLR, JIT, AOT, NativeAOT
- [Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR design philosophy
- [Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · Official list of NativeAOT constraints
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · Implementation comparison
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · Official IL2CPP documentation
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP selection guide
