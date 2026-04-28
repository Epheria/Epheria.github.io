---
title: .NET 생태계 지도 — 언어, 런타임, BCL의 관계
date: 2026-04-26 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, clr, bcl, il, runtime, mono, il2cpp]
toc: true
toc_sticky: true
difficulty: beginner
tldr:
  - C#은 언어, .NET은 플랫폼, CLR은 런타임입니다. 같은 이름처럼 들리지만 서로 다른 층에 있습니다
  - C# 코드는 IL이라는 중간 언어로 컴파일되고, 런타임이 그 IL을 JIT 또는 AOT로 네이티브 코드로 바꿔 실행합니다
  - Unity는 Mono 또는 IL2CPP라는 자체 런타임 위에서 .NET 하위 집합을 사용합니다. "Unity는 .NET이 아니다"가 아니라 "Unity는 .NET의 특정 구현을 씁니다"가 정확합니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: ".NET"이라는 말의 모호함

개발 문서·이력서·블로그에서 ".NET"이라는 단어는 놀라울 정도로 다양한 의미로 쓰입니다.

- ".NET으로 백엔드를 짭니다"
- ".NET Framework 4.8 전용 프로젝트입니다"
- ".NET 8로 마이그레이션했습니다"
- "Unity는 .NET이 아닙니다" / "Unity도 사실상 .NET입니다"

같은 단어가 **언어·런타임·표준 라이브러리·애플리케이션 프레임워크**를 오가며 모호하게 쓰이기 때문입니다. 한 번 정리하지 않으면, 이후 C# 시리즈의 거의 모든 편이 이 모호함 위에서 흔들립니다.

이 글의 목표는 단 하나입니다. **.NET이라는 단어가 어느 층을 가리키는지 구분할 수 있게 되는 것**.

역사(2편)와 런타임 갈래(3편)는 다음 편부터 다룹니다. 오늘은 **지도**를 그립니다.

---

## Part 1. 여섯 층으로 나누기

.NET은 단일 기술이 아니라 **여섯 층이 쌓인 탑**입니다. 한 층씩 분리해서 보면 ".NET"이라는 단어가 지금 어느 층을 가리키는지 말할 수 있게 됩니다.

<div class="dotnet-stack-container">
<svg viewBox="0 0 720 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET 스택 레이어 다이어그램">
  <defs>
    <linearGradient id="dotnet-stack-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.18"/>
    </linearGradient>
  </defs>

  <text x="360" y="30" text-anchor="middle" class="dotnet-stack-title">.NET 여섯 층 — 위에서 아래로</text>

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
    <text x="80" y="310" class="dotnet-stack-desc">하드웨어 독립적인 중간 바이트코드 · .dll / .exe 안에 저장됨</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="2">
    <rect x="60" y="332" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="357" class="dotnet-stack-name">2. Compiler</text>
    <text x="80" y="378" class="dotnet-stack-desc">Roslyn (csc) · 소스 코드를 IL로 번역</text>
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

각 층은 **바로 아래 층에만 의존**합니다. C# 코드는 Roslyn을 거쳐 IL이 되고, IL은 Runtime에서 해석되며, Runtime은 BCL을 기본 라이브러리로 제공하고, 그 위에서 Application Framework가 동작합니다.

".NET"이라는 단어는 맥락에 따라 이 중 **어느 층**을 가리킵니다. 이후 모든 논의는 이 지도를 참조로 삼습니다.

---

## Part 2. C#과 .NET의 관계

가장 자주 섞이는 혼동부터 정리합니다.

### C#은 언어입니다

C#은 **ECMA-334**와 **ISO/IEC 23270**으로 표준화된 프로그래밍 언어입니다. 문법과 타입 시스템을 정의하는 문서가 있고, 컴파일러(Roslyn)가 그 문서를 구현합니다. C#은 **Java와 같은 수준의 개념**입니다.

### .NET은 플랫폼입니다

.NET은 언어·런타임·BCL·SDK·애플리케이션 프레임워크를 **모두 포함하는 생태계의 이름**입니다. 위 다이어그램의 2층부터 6층까지를 통칭합니다.

### 두 가지 조합

그래서 다음 네 가지가 모두 **서로 다른 진술**입니다.

| 진술 | 가리키는 대상 |
|------|---------------|
| "C#으로 짰다" | 1층(언어) — 컴파일러·런타임은 미지정 |
| ".NET 8로 짰다" | 2~6층 전체 — 특정 버전 지정 |
| ".NET Framework 4.8 전용이다" | Windows 전용 .NET 구현체 |
| "Unity의 C#" | C# 언어 + Unity의 특정 런타임(Mono 또는 IL2CPP) |

"C#과 .NET은 같은 것 아닌가요?"라는 질문에 답한다면, "**C#은 .NET의 한 층(언어)**"입니다.

---

## Part 3. IL — 중간층이 왜 필요한가

다이어그램에서 가장 주목할 층은 **3층 IL**입니다. 여기를 이해하면 이후 모든 런타임 논의가 쉬워집니다.

### 컴파일·실행 파이프라인

<div class="dotnet-pipeline-container">
<svg viewBox="0 0 820 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="C# 컴파일 및 실행 파이프라인">
  <defs>
    <marker id="dotnet-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="dotnet-arrow-head"/>
    </marker>
  </defs>

  <text x="410" y="26" text-anchor="middle" class="dotnet-pipeline-title">컴파일 타임과 실행 타임의 경계</text>

  <g class="dotnet-pipeline-step">
    <rect x="20" y="100" width="120" height="60" rx="8" class="dotnet-step-source"/>
    <text x="80" y="128" text-anchor="middle" class="dotnet-step-name">C# 소스</text>
    <text x="80" y="146" text-anchor="middle" class="dotnet-step-sub">.cs</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="180" y="100" width="120" height="60" rx="8" class="dotnet-step-compiler"/>
    <text x="240" y="128" text-anchor="middle" class="dotnet-step-name">Roslyn (csc)</text>
    <text x="240" y="146" text-anchor="middle" class="dotnet-step-sub">컴파일러</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="340" y="100" width="120" height="60" rx="8" class="dotnet-step-il"/>
    <text x="400" y="128" text-anchor="middle" class="dotnet-step-name">IL</text>
    <text x="400" y="146" text-anchor="middle" class="dotnet-step-sub">.dll / .exe</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="60" width="140" height="60" rx="8" class="dotnet-step-jit"/>
    <text x="570" y="88" text-anchor="middle" class="dotnet-step-name">JIT</text>
    <text x="570" y="106" text-anchor="middle" class="dotnet-step-sub">실행 타임 번역</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="140" width="140" height="60" rx="8" class="dotnet-step-aot"/>
    <text x="570" y="168" text-anchor="middle" class="dotnet-step-name">AOT</text>
    <text x="570" y="186" text-anchor="middle" class="dotnet-step-sub">빌드 타임 번역</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="680" y="100" width="120" height="60" rx="8" class="dotnet-step-native"/>
    <text x="740" y="128" text-anchor="middle" class="dotnet-step-name">네이티브 코드</text>
    <text x="740" y="146" text-anchor="middle" class="dotnet-step-sub">x86 / ARM</text>
  </g>

  <line x1="140" y1="130" x2="175" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="300" y1="130" x2="335" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="120" x2="495" y2="95" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="140" x2="495" y2="165" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="95" x2="680" y2="125" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="165" x2="680" y2="140" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>

  <line x1="460" y1="220" x2="460" y2="40" class="dotnet-pipeline-divider"/>
  <text x="240" y="240" text-anchor="middle" class="dotnet-pipeline-label">컴파일 타임 (빌드 머신)</text>
  <text x="650" y="240" text-anchor="middle" class="dotnet-pipeline-label">실행 타임 또는 배포 전</text>
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

### 왜 중간층(IL)을 끼워넣었는가

C 언어는 컴파일러가 소스 코드를 바로 네이티브 코드로 번역합니다. `.c` 파일은 Windows x64용 `.exe`가 되거나 Linux ARM64용 바이너리가 됩니다. 한 번 컴파일한 결과물은 **특정 OS + 특정 CPU 조합**에 묶입니다.

.NET은 이 구조를 한 번 쪼갰습니다. C# 소스는 일단 **IL(Intermediate Language)**이라는 중간 바이트코드로만 번역됩니다. IL은 하드웨어에 독립적이고, OS에도 독립적입니다. 실제 네이티브 번역은 **실행 시점**(JIT) 또는 **배포 직전**(AOT)에 **그 기계가 어떤 기계인지 알게 된 뒤** 수행됩니다.

이 구조의 이점은 세 가지입니다.

**① 플랫폼 독립성.** 같은 `.dll`이 Windows·Linux·macOS 어디서든 실행됩니다. 런타임이 그 기계의 네이티브 명령어로 번역해 주기 때문입니다.

**② 언어 독립성.** IL로만 떨어뜨리면 되기 때문에, C# 외에 F#·VB.NET도 같은 런타임·BCL을 씁니다. 언어가 바뀌어도 아래 층은 그대로입니다.

**③ 런타임 최적화.** JIT는 **실제 실행되는 하드웨어 정보와 실행 중 통계**를 보고 최적화할 수 있습니다. 정적 컴파일러보다 늦게 번역하는 대신 더 많은 정보를 쓸 수 있다는 거래입니다.

### JIT와 AOT — 같은 IL, 다른 번역 시점

IL을 네이티브 코드로 번역하는 시점이 두 가지입니다.

- **JIT (Just-In-Time)**: 프로그램이 실행되는 **그 기계에서**, **그 순간에** 번역합니다. 번역 비용은 실행 타임에 포함됩니다. 대신 하드웨어 정보를 정확히 알 수 있습니다. 데스크톱 .NET·Mono가 이 방식입니다.
- **AOT (Ahead-Of-Time)**: 앱을 배포하기 **전에 미리** 네이티브 코드로 번역해 둡니다. 실행 타임에는 JIT가 없어도 돌아갑니다. **iOS처럼 JIT를 허용하지 않는 플랫폼**에서는 유일한 선택지입니다. IL2CPP·NativeAOT가 이 방식입니다.

이 경계가 Unity의 Mono vs IL2CPP 선택, 모바일·콘솔 빌드 함정, `Reflection.Emit`이 IL2CPP에서 깨지는 이유를 전부 설명합니다. 상세는 3편에서 다룹니다.

---

## Part 4. Runtime과 BCL — 실행을 책임지는 두 기둥

3층(IL)까지는 "소스에서 무엇이 만들어지는가"의 이야기였습니다. 4·5층은 "만들어진 것이 어떻게 실행되는가"의 이야기입니다.

### Runtime — IL을 실제로 돌리는 주체

**Runtime(런타임)**은 IL을 읽어 네이티브로 번역하고 실행하는 엔진입니다. 메모리 관리(GC), 예외 처리, 타입 시스템, 스레드 관리, 보안을 모두 담당합니다. Microsoft 공식 용어집의 정의는 이렇습니다.

> A CLR handles memory allocation and management. A CLR is also a virtual machine that not only executes apps but also generates and compiles code on-the-fly using a JIT compiler. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

중요한 점은 **런타임이 하나가 아니라는 것**입니다.

- **CLR** — .NET Framework의 런타임. Windows 전용
- **CoreCLR** — .NET 5+ (구 .NET Core)의 런타임. 크로스 플랫폼
- **Mono** — 오픈소스 크로스 플랫폼 구현. Unity의 기본 런타임
- **IL2CPP** — Unity가 만든 AOT 런타임. IL을 C++로 바꿔 네이티브 컴파일
- **NativeAOT** — .NET 공식 AOT 배포 모드

같은 C# 코드·같은 IL이라도 **어느 런타임 위에서 도는지**에 따라 성능·메모리 특성·사용 가능한 기능이 달라집니다.

### BCL — 모든 런타임이 기본으로 제공하는 라이브러리

**BCL(Base Class Library)**은 `System.*` 네임스페이스에 속한 표준 라이브러리입니다. `Console.WriteLine`, `List<T>`, `Dictionary<K,V>`, `File.ReadAllText`, `Task`, `CancellationToken` — 여러분이 당연하게 쓰는 거의 모든 것이 BCL입니다.

Microsoft 공식 용어집의 정의:

> A set of libraries that comprise the `System.*` (and to a limited extent `Microsoft.*`) namespaces. The BCL is a general purpose, lower-level framework that higher-level application frameworks, such as ASP.NET Core, build on. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

BCL의 위치를 한 문장으로 요약하면 이렇습니다. **"런타임은 IL을 돌리는 엔진이고, BCL은 그 엔진 위에서 기본 제공되는 표준 라이브러리입니다."** 엔진만 있고 라이브러리가 없으면 `Console.WriteLine("hi")` 한 줄도 돌아가지 않습니다.

### 세 단어의 관계 정리

| 단어 | 층 | 예시 | 역할 |
|------|-----|------|------|
| Assembly | 3층(IL 묶음) | `MyApp.dll`, `System.Collections.dll` | IL을 담은 파일 단위 |
| Runtime | 4층 | CLR / CoreCLR / Mono / IL2CPP | IL을 실제로 돌리는 엔진 |
| BCL | 5층 | `System.*` 네임스페이스 | 런타임 위에서 기본 제공되는 라이브러리 |

".NET Runtime을 설치한다"는 말은 일상적으로 **4층(엔진) + 5층(BCL)** 묶음을 설치한다는 뜻입니다. 이 둘은 거의 항상 함께 배포됩니다.

---

## Part 5. SDK vs Runtime — 개발자와 사용자의 차이

배포 이야기를 하면 꼭 나오는 질문이 있습니다. **"SDK랑 Runtime 중에 뭘 깔아야 하나요?"**

답은 역할에 달려 있습니다.

- **SDK(Software Development Kit)**: 앱을 **만드는** 사람이 필요한 것. 컴파일러, CLI 도구(`dotnet`), 런타임, BCL, 템플릿이 모두 들어 있습니다
- **Runtime**: 앱을 **실행만** 하는 사람이 필요한 것. 엔진(4층)과 BCL(5층)만 들어 있습니다. 컴파일러는 없습니다

확인 명령은 이렇습니다.

```bash
$ dotnet --list-sdks
8.0.404 [/usr/local/share/dotnet/sdk]
10.0.100 [/usr/local/share/dotnet/sdk]

$ dotnet --list-runtimes
Microsoft.NETCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
Microsoft.AspNetCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.AspNetCore.App]
Microsoft.NETCore.App 10.0.0 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
```

개발자 머신에는 보통 SDK가 설치되어 있고, SDK 안에 런타임이 포함됩니다. 서버나 일반 사용자 머신에는 런타임만 설치해도 충분합니다.

단, **Self-contained 배포**로 패키징하면 런타임을 앱 안에 포함해서 내보낼 수 있습니다. 이 경우 사용자 머신에는 아무것도 설치할 필요가 없습니다. NativeAOT로 빌드하면 아예 단일 네이티브 바이너리가 됩니다. 4층의 선택지가 여기까지 이어집니다.

---

## Part 6. Unity는 어디에 걸치는가

이 블로그 독자 대부분은 게임 프로그래머입니다. 그러니 지도에 **Unity의 위치**를 표시해야 그림이 완성됩니다.

<div class="dotnet-unity-container">
<svg viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Unity가 .NET 스택에 걸치는 위치">
  <text x="380" y="28" text-anchor="middle" class="dotnet-unity-title">Unity와 .NET 스택 — 세 경로</text>

  <g class="dotnet-unity-col" data-col="server">
    <rect x="30" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane"/>
    <text x="140" y="78" text-anchor="middle" class="dotnet-unity-lane-label">서버·데스크톱 .NET</text>

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
    <text x="380" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + Mono (Editor/데스크톱)</text>

    <rect x="290" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="380" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="290" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="380" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard 하위)</text>

    <rect x="290" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt"/>
    <text x="380" y="220" text-anchor="middle" class="dotnet-unity-block-text">Mono (JIT)</text>

    <rect x="290" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="380" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="290" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="380" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>

  <g class="dotnet-unity-col" data-col="il2cpp">
    <rect x="510" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane dotnet-unity-lane-accent"/>
    <text x="620" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + IL2CPP (iOS/WebGL/콘솔)</text>

    <rect x="530" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="620" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="530" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="620" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard 하위)</text>

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

세 경로가 **같은 C#·같은 IL을 공유**합니다. 달라지는 층은 **4층(런타임)과 6층(애플리케이션 프레임워크)**뿐입니다. Unity가 ".NET이 아닌 것"처럼 보이는 이유는 단순히 **다른 런타임을 쓰기 때문**입니다.

### Unity의 두 런타임

- **Mono (JIT)** — Unity 에디터와 데스크톱 빌드의 기본. 빌드가 빠르고 반복 개발에 유리합니다. Mono는 Microsoft 공식 용어집에도 ".NET의 구현체 중 하나"로 명시되어 있습니다. [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations)

- **IL2CPP (AOT)** — iOS·WebGL·콘솔 타깃의 기본이자 강제 선택. IL을 **C++ 소스로 변환**한 뒤 각 플랫폼의 네이티브 툴체인(Xcode, Emscripten, 콘솔 SDK)으로 네이티브 바이너리를 만듭니다. iOS는 OS가 JIT를 허용하지 않기 때문에 Mono는 아예 선택지가 아닙니다. [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)

### 게임 프로그래머가 이 지도에서 얻어야 할 것

이 지도가 주는 실용적 결론 세 가지만 짚습니다.

**① `Reflection.Emit`이 IL2CPP에서 깨진다**는 사실의 **본질**은, IL2CPP가 **런타임에 IL을 새로 만들 JIT가 없기 때문**입니다. 4층이 달라진 결과가 위층 API 동작까지 전파됩니다.

**② Unity의 "C#"은 Unity가 고른 런타임·BCL 조합에 묶입니다.** 서버 .NET에서 쓸 수 있는 API가 Unity에서는 없을 수 있고, 반대도 마찬가지입니다. `.csproj`의 **API Compatibility Level** 설정이 바로 5층의 범위를 정하는 스위치입니다.

**③ "Unity는 .NET 생태계에 속하는가?" 라는 질문의 답은 명확합니다.** 1~3층(C#·Roslyn·IL)을 그대로 쓰고, 4층(런타임)만 Unity 전용을 씁니다. **같은 생태계 안의 다른 구현체**일 뿐입니다.

---

## 요약

오늘 만든 지도의 결론을 세 줄로 정리합니다.

1. **C#은 1층의 언어**이고, **.NET은 2~6층 전체의 플랫폼**입니다. 둘은 같은 층이 아닙니다.
2. **IL이라는 중간층**이 언어 독립성·플랫폼 독립성·런타임 최적화를 만드는 거래의 중심입니다.
3. **런타임**(CLR·CoreCLR·Mono·IL2CPP·NativeAOT)은 여러 개가 공존하며, **어떤 런타임 위에서 도는지**가 같은 코드의 성능·제약·가용 API를 결정합니다.

이 지도는 이후 시리즈의 **모든 글**이 참조할 좌표계입니다. 어떤 글에서든 "이 이야기가 어느 층의 이야기인가?"를 먼저 물어보시길 권합니다.

---

## 다음 편 예고

- **2편. .NET 역사 — Framework에서 하나의 .NET까지** — 2002년 .NET Framework 1.0부터 2020년 .NET 5 통합, 그리고 현재 .NET 10까지의 계보. 왜 "Core"가 이름에서 빠졌는지, 왜 .NET 4가 건너뛰어졌는지도 여기서 풀립니다.
- **3편. CLR · Mono · IL2CPP · NativeAOT — 런타임 갈래 비교** — 4층의 다섯 구현체를 JIT/AOT·메모리·리플렉션·제네릭 관점에서 비교합니다. 게임 프로그래머에게 가장 실용적인 편이 될 편입니다.

---

## 참고 자료

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · 공식 용어집
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · 구현체 개요
- [Microsoft Learn — Common Language Runtime (CLR) overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR 개요
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · Unity IL2CPP 문서
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP 배경
