---
title: .NET History — From Framework to One .NET
lang: en
date: 2026-04-27 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, history, mono, xamarin, dotnet-core]
toc: true
toc_sticky: true
difficulty: beginner
prerequisites:
  - /posts/DotnetEcosystemMap/
tldr:
  - .NET Framework launched in 2002 as a Windows-only platform; its final version, 4.8.1 (2022), has been frozen in maintenance mode ever since
  - .NET Core was a clean-slate restart in 2016 that cut the Windows dependency; in 2020, .NET 5 merged the two lineages into a single unified platform
  - Mono started in 2001 as an independent open-source effort to run .NET on Linux, moved through Xamarin and then Microsoft, was folded into the official implementation, and became the runtime foundation for Unity
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: Why Knowing the History Is Practical

This episode answers three questions.

1. **Why was ".NET 4" skipped?** — Why does the version after .NET Core 3.1 jump to 5 instead of 4?
2. **Why was "Core" dropped from the name?** — There was a .NET Core 3.1, so why is there no .NET Core 5?
3. **Why is Unity on top of Mono?** — Microsoft ships its own runtime, so why does Unity use an external implementation?

These questions **cannot be answered without knowing the history**. Official documentation describes the current state; it does not explain how that state came to be. Filling that gap is the purpose of this episode.

The history spans a long arc, so it is divided into parts: **four eras** — Birth (2000–2004), Maturity (2005–2013), Transformation (2014–2019), and Unification (2020–present). At the end of each era, only the points that matter to a game programmer are highlighted.

---

## Part 1. Birth (2000–2004)

### The Launch of .NET Framework

In the late 1990s, Microsoft faced pressure from two directions.

- **Sun's Java was surging** — the slogan "write once, run anywhere" was shaking the enterprise market. The J2EE stack had become the default choice for banks and telecoms.
- **Windows development was fragmented** — Visual Basic, MFC, COM, and ActiveX coexisted without working well together.

Microsoft's response was **.NET Framework**: a design where multiple languages (C#, VB.NET, C++/CLI) share a single runtime (CLR) and a single standard library (BCL). It reframed Java's "write once, run anywhere" along the language axis as "write in any .NET language, run on any Windows."

**February 13, 2002 — .NET Framework 1.0** shipped. C# 1.0 launched alongside it.

There was one fundamental constraint: **Windows only**. Unlike Java, which achieved OS independence through the JVM, the CLR in .NET Framework ran exclusively on Windows. This constraint would drive the next twenty years of history.

### Mono — Someone Who Wanted .NET on Linux

At the same time, Spanish developer **Miguel de Icaza** was leading the GNOME desktop project. When he saw that the .NET specification had been **submitted to ECMA as an open standard**, he wondered whether **the same runtime could be implemented on Linux**.

- **July 19, 2001** — the **Mono** project was announced at the O'Reilly conference. His company, Ximian, led the effort.
- **2003** — Novell acquired Ximian. Mono became a Novell asset.
- **June 30, 2004** — Mono 1.0 shipped, running C# 1.x and the CLR on Linux and macOS.

At this point, Microsoft was neither friendly nor hostile toward Mono. The relationship was "not ours, but we won't stop it." ([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

### Significance

Part 1 established **two separate lineages**.

- **.NET Framework lineage** — Microsoft official, Windows-only, proprietary
- **Mono lineage** — external open source, cross-platform, Linux/macOS

It would take **another fifteen years** for the two to merge.

---

## Part 2. Maturity (2005–2013)

### Language Evolution in .NET Framework

From 2005 to 2010, .NET Framework expanded its language features and BCL rapidly.

| Year | Version | Key Additions |
|------|---------|--------------|
| 2005 | 2.0 | **Generics** — a core C# feature |
| 2006 | 3.0 | WPF, WCF, WF (Windows integration frameworks) |
| 2008 | 3.5 | **LINQ** — query expressions as a language feature |
| 2010 | 4.0 | TPL (Task Parallel Library), `dynamic` |
| 2012 | 4.5 | **`async/await`** — asynchrony as a language feature |
| 2015 | 4.6 | RyuJIT (new JIT), performance improvements |
| 2017 | 4.7 | High-DPI improvements |
| 2019 | 4.8 | JIT optimizations, last major release |
| 2022 | 4.8.1 | Final release — **effectively frozen** |

.NET Framework stops here. **4.8.1 is the last version**, with only security patches provided going forward. Microsoft officially stated that ".NET Framework will continue to be supported, but no new features will be added." ([Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies))

### Mono's Expansion and the Founding of Xamarin

Mono matured during the same period.

- **April 2011** — Attachmate acquired Novell, placing the Mono team at risk of layoffs.
- **May 16, 2011** — Miguel de Icaza founded **Xamarin** and took stewardship of Mono with it.
- Xamarin commercialized Mono — generating revenue through **C# development tools for iOS and Android** (MonoTouch, Mono for Android).

### Unity Adopts Mono

Unity Technologies shipped the Unity game engine in 2005 and chose **Mono-based C# (alongside the early UnityScript and Boo)** as its scripting language. The reasoning was straightforward.

- **Cross-platform**: Unity targeted Mac, Windows, and consoles from the start, and .NET Framework only ran on Windows. Mono was the only viable option.
- **Small footprint**: Mono was designed with mobile and embedded targets in mind, with low memory overhead.
- **License flexibility**: commercial licensing negotiations were feasible.

This decision is **why C# code in Unity games runs on a Mono runtime today**. An engineering choice made twenty years ago has persisted to the present.

### Significance

By the end of Part 2, .NET Framework had become **a mature, polished commercial Windows stack**, and Mono had become **the only practical choice for cross-platform .NET**. The two lineages diverged further with each passing year.

---

## Part 3. Transformation (2014–2019)

### Microsoft's Strategic Pivot

**April 2014** — at the Build developer conference, Microsoft announced two things:

1. **The .NET Foundation** ([Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation)) — a non-profit governing the open-source stewardship of the .NET ecosystem. Miguel de Icaza (then Xamarin CTO) was included on the initial board.
2. **The .NET Core project** — a declaration to build a **new .NET implementation** with no Windows dependencies.

Later that year, **November 2014**, at the Connect() conference, Microsoft officially announced that the **.NET server stack would go entirely open source** and expand to Linux and macOS. ([Microsoft News — .NET open source and cross-platform (2014.11.12)](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/), [".NET Core is Open Source" — .NET Blog](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/))

This was a historic turning point for Microsoft. Up to this point, Microsoft had designed everything with Windows at the center. But the landscape had shifted.

- **Linux dominated** the server market.
- Supporting Linux was a **requirement, not an option**, for the Azure cloud strategy.
- Developers were using Macs.

To keep pace, **.NET had to be separated from Windows**. The .NET Framework codebase was too deeply entangled with Windows APIs to port, so Microsoft decided to **rewrite from scratch**. That rewrite became .NET Core.

### The Xamarin Acquisition

**February 24, 2016** — Microsoft officially announced the **acquisition of Xamarin**. ([Microsoft Blog — "Microsoft to acquire Xamarin" (2016.02.24)](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/)) The move had two implications.

- Mono became a **Microsoft official asset** — an external open-source implementation brought into the house.
- **March 2016** — Mono was **re-licensed under the MIT license**. Anyone could use it freely without a commercial Xamarin license.

For Unity developers this was a quiet change, but it marked **a redrawing of the .NET ecosystem's boundaries**. The project that had sustained .NET on Linux and macOS from the outside for fourteen years was now part of Microsoft.

### .NET Core 1.0–3.1

- **June 27, 2016 — .NET Core 1.0** shipped. The first official .NET implementation to run on Windows, Linux, and macOS.
- **2017 — .NET Core 2.0**. .NET Standard 2.0 support dramatically improved API compatibility with Framework.
- **December 2019 — .NET Core 3.1 LTS**. The stable release. This was the last version under the ".NET Core" branding.

During this period, **three implementations coexisted in the .NET ecosystem**.

- **.NET Framework 4.x** — Windows commercial stack (maintained as legacy)
- **.NET Core 3.1** — cross-platform new stack (recommended for new development)
- **Mono (+ Xamarin)** — mobile and games (Xamarin for mobile, Mono for Unity)

**The same C# code had to be able to run in three different places**. Developers and library authors tried to tie the three implementations together through the .NET Standard API contract, but at its core the situation remained: three runtimes, three BCLs.

### Significance

Part 3 produced **three competing implementations** and **the foreshadowing of unification**. Microsoft announced it would end this confusion with .NET 5.

---

## Part 4. Unification (2020–present)

### .NET 5 — Two Names Resolved

**November 2020 — .NET 5** shipped. ([".NET Blog — Announcing .NET 5.0" (2020.11.10)](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/)) Two decisions were made here.

**① Skip version number 4.**
Why did the next version after .NET Core 3.1 become 5 instead of 4? The reason was to **avoid confusion with .NET Framework 4.x**. ([Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET))

Having two different ".NET 4" products from the same company at the same time made no sense — one a Windows-only legacy platform, the other a cross-platform future. To avoid the version number collision, Core skipped 4.

**② Drop "Core" from the name.**
.NET Core became **.NET**. The reason was a **declaration of identity**.

> ".NET Core" implies a stripped-down subset of .NET. But now that .NET Core had surpassed Framework in features, performance, and ecosystem, it was simply **.NET** — the real one.

From .NET 5 onward, the naming follows `.NET 5`, `.NET 6`, `.NET 7`, and so on. In official documentation, **".NET Core" is only used to refer to version 3.1 and earlier**.

### Version Timeline

| Year | Version | Type | Key Notes |
|------|---------|------|----------|
| 2020.11 | .NET 5 | STS | Start of unification |
| 2021.11 | .NET 6 | **LTS** | Hot Reload, Minimal API |
| 2022.11 | .NET 7 | STS | **NativeAOT first introduced** (console apps and libraries) |
| 2023.11 | .NET 8 | **LTS** | NativeAOT expanded, ASP.NET Core AOT |
| 2024.11 | .NET 9 | STS | Performance improvements |
| 2025.11 | .NET 10 | **LTS** | Current stable release |

LTS (Long Term Support) receives 3 years of support; STS (Standard Term Support) receives 1.5 years. Even-numbered versions are LTS by convention.

### Mono's Final Chapter

**August 27, 2024** — Microsoft announced the **transfer of the Mono project to WineHQ**. WineHQ is the development team behind Wine, the software that runs Windows programs on Linux. ([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

The implication is clear. The runtimes Microsoft cares about are **CoreCLR (.NET 8+) and NativeAOT**. Mono is no longer a strategic asset for Microsoft.

Unity's Mono, however, **continues independently**. Unity Technologies has maintained its own Mono fork and it is deeply integrated into the engine's build pipeline, so it continues to evolve separately from the upstream WineHQ project.

### Significance

Part 4 delivered **clarity of naming**. At this point, the modern usage of ".NET" is settled as follows.

- **.NET** (without a version number) = the unified .NET implementation since 2020 (CoreCLR-based)
- **.NET Framework** = the Windows-only legacy from 2002 to 2022 (frozen at 4.8.1)
- **Mono** = the mobile/game implementation (maintained by Unity and WineHQ)
- **.NET Core** = the transitional name used from 2016–2019 (no longer in active use)

---

## .NET Lineage Timeline

A single diagram summarizing all four eras.

<div class="dotnet-lineage-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET History Lineage Timeline 2001–2025">
  <text x="450" y="28" text-anchor="middle" class="dotnet-lineage-title">.NET Lineage — 2001 to 2025</text>

  <g class="dotnet-lineage-axis">
    <line x1="60" y1="400" x2="860" y2="400" class="dotnet-lineage-axis-line"/>
    <text x="60" y="420" text-anchor="middle" class="dotnet-lineage-year">2001</text>
    <text x="180" y="420" text-anchor="middle" class="dotnet-lineage-year">2005</text>
    <text x="340" y="420" text-anchor="middle" class="dotnet-lineage-year">2011</text>
    <text x="500" y="420" text-anchor="middle" class="dotnet-lineage-year">2016</text>
    <text x="660" y="420" text-anchor="middle" class="dotnet-lineage-year">2020</text>
    <text x="820" y="420" text-anchor="middle" class="dotnet-lineage-year">2025</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="framework">
    <rect x="60" y="70" width="640" height="40" rx="6" class="dotnet-lane-framework"/>
    <text x="70" y="95" class="dotnet-lane-name">.NET Framework (2002–2022, Windows only)</text>
    <text x="700" y="95" text-anchor="end" class="dotnet-lane-tag">Frozen at 4.8.1</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="mono">
    <rect x="80" y="130" width="780" height="40" rx="6" class="dotnet-lane-mono"/>
    <text x="90" y="155" class="dotnet-lane-name">Mono (2001–, cross-platform, folded into Microsoft 2016, transferred to WineHQ 2024)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="xamarin">
    <rect x="340" y="190" width="280" height="40" rx="6" class="dotnet-lane-xamarin"/>
    <text x="350" y="215" class="dotnet-lane-name">Xamarin (2011–2024)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="core">
    <rect x="500" y="250" width="180" height="40" rx="6" class="dotnet-lane-core"/>
    <text x="510" y="275" class="dotnet-lane-name">.NET Core (2016–2019)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="dotnet">
    <rect x="680" y="310" width="180" height="40" rx="6" class="dotnet-lane-dotnet"/>
    <text x="690" y="335" class="dotnet-lane-name">.NET (2020–)</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="500" y1="250" x2="500" y2="350" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="510" y="340" class="dotnet-event-label">convergence</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="680" y1="110" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <line x1="680" y1="290" x2="680" y2="310" class="dotnet-event-line-solid"/>
    <text x="688" y="306" class="dotnet-event-label">.NET 5 unification</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="620" y1="230" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="860" y1="170" x2="860" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="835" y="302" text-anchor="end" class="dotnet-event-label">Unity Mono continues</text>
  </g>
</svg>
</div>

<style>
.dotnet-lineage-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-lineage-container svg { width: 100%; max-width: 900px; height: auto; display: block; margin: 0 auto; }
.dotnet-lineage-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-lineage-axis-line { stroke: #94a3b8; stroke-width: 1.5; }
.dotnet-lineage-year { font-size: 12px; fill: #64748b; }
.dotnet-lane-framework { fill: #dbeafe; stroke: #2563eb; stroke-width: 1.2; }
.dotnet-lane-mono { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.dotnet-lane-xamarin { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.dotnet-lane-core { fill: #d1fae5; stroke: #10b981; stroke-width: 1.2; }
.dotnet-lane-dotnet { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.dotnet-lane-name { font-size: 13px; font-weight: 600; fill: #1e293b; }
.dotnet-lane-tag { font-size: 11px; fill: #475569; font-style: italic; }
.dotnet-event-line { stroke: #6366f1; stroke-width: 1.5; fill: none; }
.dotnet-event-line-solid { stroke: #6366f1; stroke-width: 1.5; fill: none; }
.dotnet-event-label { font-size: 11px; fill: #475569; font-style: italic; }
[data-mode="dark"] .dotnet-lineage-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-lineage-axis-line { stroke: #64748b; }
[data-mode="dark"] .dotnet-lineage-year { fill: #94a3b8; }
[data-mode="dark"] .dotnet-lane-framework { fill: rgba(37,99,235,0.25); stroke: #60a5fa; }
[data-mode="dark"] .dotnet-lane-mono { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-lane-xamarin { fill: rgba(236,72,153,0.25); stroke: #f472b6; }
[data-mode="dark"] .dotnet-lane-core { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .dotnet-lane-dotnet { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-lane-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-lane-tag { fill: #cbd5e1; }
[data-mode="dark"] .dotnet-event-line { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-event-line-solid { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-event-label { fill: #cbd5e1; }
@media (max-width: 768px) {
  .dotnet-lane-name { font-size: 10px; }
  .dotnet-lane-tag { font-size: 9px; }
  .dotnet-event-label { font-size: 9px; }
  .dotnet-lineage-year { font-size: 10px; }
}
</style>

---

## Answering the Three Opening Questions

The three questions posed at the start can now be answered.

### Q1. Why was .NET 4 skipped?

If the version after .NET Core 3.1 had been called 4, it would have **collided with the name .NET Framework 4.x**, creating enormous confusion. The same company cannot simultaneously ship two different ".NET 4" products, so Core skipped ahead to 5.

### Q2. Why was "Core" dropped from the name?

At the point where .NET Core had surpassed .NET Framework in completeness, Microsoft concluded that the "Core" suffix was giving the wrong impression — **it implied a reduced, compatibility-subset edition**. From .NET 5 in 2020, "Core" was dropped, and that platform became **the real .NET**. Framework became the frozen legacy, stopped at 4.8.1.

### Q3. Why is Unity on top of Mono?

When Unity shipped its engine in 2005, **.NET Framework was Windows-only**. For a game engine targeting Mac, Linux, and consoles, Mono was the only practical choice. That decision has held for twenty years, during which Unity's engine build pipeline, editor, and plugin ecosystem were all built on top of Mono — making it a foundation that is very hard to replace. Unity's **IL2CPP**, introduced in 2014, is an alternative that partially works around this constraint (covered in detail in episode 3).

---

## What This History Means for Game Programmers

Four **practical takeaways** after reviewing the history.

**① Unity's Mono is separate from upstream.**
Since Microsoft transferred Mono to WineHQ in 2024, **Unity maintains its own Mono independently**. It is not waiting on updates from the upstream project.

**② `.NET Standard` is a legacy of the pre-unification era.**
It was a contract created during the .NET Core era to tie together the three implementations — Framework, Mono, and Core. Now that .NET 5+ has unified everything, new libraries are encouraged to **target a specific .NET version** rather than `.NET Standard`. That said, Unity's API compatibility level is still based on `.NET Standard 2.1`, so this legacy lives on.

**③ Do not start a new ".NET Framework project" today.**
It is frozen at 4.8.1 with no new features. Unless you are maintaining legacy code, all new development belongs on .NET 8+ (or Unity's Mono/IL2CPP).

**④ Calibrate your timeline when you see ".NET Core."**
A document that says "We use .NET Core 3.1" likely reflects a **project that has not been updated since 2019**. When reading tech blogs or Stack Overflow answers, treat any mention of "Core" as a pre-2020 source.

---

## Summary

The key points of this episode in three lines.

1. **.NET Framework (2002) and Mono (2001) developed in parallel for fifteen years**, then Microsoft's strategic pivot brought them together into **.NET 5 in 2020**.
2. **"Core" was a transitional name** — today it is simply **.NET**. Versions continue as 5, 6, 7, 8, 9, 10, with even numbers being LTS.
3. **Unity's Mono is maintained independently**, and Microsoft's focus has shifted to **CoreCLR and NativeAOT**.

---

## Coming Up Next

Episode 3 shifts from the **time axis** to the **spatial axis** — examining .NET as it exists today. It compares the **five runtime implementations** — CLR, CoreCLR, Mono, IL2CPP, and NativeAOT — across JIT/AOT, memory, reflection, generics, and deployment. It will be the most practically useful episode for game programmers.

---

## References

### Microsoft Official Primary Sources

- [.NET Blog — "Announcing .NET 5.0"](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/) · November 10, 2020, official .NET 5 unification announcement
- [Microsoft Blog — "Microsoft to acquire Xamarin"](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/) · February 24, 2016, official Xamarin acquisition announcement
- [.NET Blog — ".NET Core is Open Source"](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/) · 2014, .NET Core open-source declaration
- [Microsoft News — "Microsoft takes .NET open source and cross-platform"](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/) · November 12, 2014, official newsroom announcement from the Connect() event

### Reference Materials

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · Official terminology reference
- [Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies) · Official Framework version history
- [Wikipedia — .NET Framework version history](https://en.wikipedia.org/wiki/.NET_Framework_version_history) · Version-by-version history
- [Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)) · Mono history
- [Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET) · Unification and version numbering policy
- [Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation) · Launched at Build 2014
- [endoflife.date — Microsoft .NET](https://endoflife.date/dotnet) · End-of-life schedule
