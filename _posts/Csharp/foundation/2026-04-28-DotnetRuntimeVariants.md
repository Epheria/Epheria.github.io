---
title: CLR · Mono · IL2CPP · NativeAOT — 런타임 갈래 비교
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
  - .NET 런타임은 크게 JIT 계열(CLR·CoreCLR·Mono)과 AOT 계열(IL2CPP·NativeAOT·Mono Full AOT)로 나뉩니다
  - AOT 계열은 시작 시간·배포 크기 면에서 유리하지만 Reflection.Emit·동적 제네릭 인스턴스화·Expression.Compile 같은 기능이 깨집니다
  - 게임 개발자가 IL2CPP에서 만나는 제약은 런타임 자체의 설계 선택에서 나오는 것이지 Unity의 고유 문제가 아닙니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: 같은 IL, 다른 운명

앞의 두 편에서 우리는 **.NET 스택의 4층(Runtime)**이 여러 구현체로 나뉜다는 사실을 확인했습니다. 이번 편은 그 구현체들을 하나씩 뜯어 비교합니다.

현재 시점에서 실무적으로 의미 있는 **다섯 런타임**은 다음과 같습니다.

| 런타임 | 소속 | 등장 | 상태 |
|--------|------|------|------|
| **CLR** | .NET Framework | 2002 | 동결 (4.8.1) |
| **CoreCLR** | .NET 5+ | 2016 (Core 1.0) | 활성 |
| **Mono** | Xamarin·Unity | 2004 | 활성 (Unity 포크) |
| **IL2CPP** | Unity | 2014 | 활성 |
| **NativeAOT** | .NET 7+ | 2022 | 활성 |

같은 C# 코드를 작성해도 **어느 런타임 위에서 도는가**에 따라 성능·메모리·가용 API·배포 크기가 크게 달라집니다. 이 편의 목적은 그 차이를 **실용적 선택 기준**으로 정리하는 것입니다.

다섯 런타임이 복잡해 보이지만, **하나의 축**만 잡으면 대부분이 정리됩니다. 그 축이 **JIT vs AOT**입니다.

---

## Part 1. 단 하나의 축 — JIT vs AOT

앞서 1편에서 IL을 네이티브 코드로 번역하는 시점이 두 가지라고 했습니다. 이 번역 시점이 **다섯 런타임을 두 무리로 가르는 결정적 차이**입니다.

<div class="dotnet-runtime-tree-container">
<svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="런타임 5종 JIT AOT 분류 트리">
  <text x="380" y="28" text-anchor="middle" class="runtime-tree-title">.NET 런타임 5종 — JIT / AOT 분류</text>

  <g class="runtime-tree-root">
    <rect x="310" y="60" width="140" height="50" rx="8" class="runtime-tree-box-root"/>
    <text x="380" y="82" text-anchor="middle" class="runtime-tree-text-bold">IL</text>
    <text x="380" y="100" text-anchor="middle" class="runtime-tree-text-sm">(중간 바이트코드)</text>
  </g>

  <line x1="380" y1="110" x2="200" y2="160" class="runtime-tree-line"/>
  <line x1="380" y1="110" x2="560" y2="160" class="runtime-tree-line"/>

  <g class="runtime-tree-branch jit">
    <rect x="120" y="160" width="160" height="50" rx="8" class="runtime-tree-box-jit"/>
    <text x="200" y="182" text-anchor="middle" class="runtime-tree-text-bold">JIT 계열</text>
    <text x="200" y="200" text-anchor="middle" class="runtime-tree-text-sm">실행 타임 번역</text>
  </g>

  <g class="runtime-tree-branch aot">
    <rect x="480" y="160" width="160" height="50" rx="8" class="runtime-tree-box-aot"/>
    <text x="560" y="182" text-anchor="middle" class="runtime-tree-text-bold">AOT 계열</text>
    <text x="560" y="200" text-anchor="middle" class="runtime-tree-text-sm">빌드 타임 번역</text>
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
    <text x="320" y="300" text-anchor="middle" class="runtime-tree-text-sm">Unity 기본</text>
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

### JIT 계열 — CLR · CoreCLR · Mono

JIT(Just-In-Time)는 **앱이 실행되는 그 기계에서, 그 순간에** IL을 네이티브로 번역합니다. 이 방식의 장단은 다음과 같습니다.

**장점**
- 하드웨어 정보를 **실제 실행되는 기계**에서 가져와 최적화 가능
- 런타임 실행 통계(Tiered Compilation, PGO)를 활용한 후속 재최적화 가능
- **`Reflection.Emit`·`Expression.Compile`** 같은 **런타임 코드 생성 API**가 동작

**단점**
- 실행 초기에 JIT 비용을 지불 (Cold Start 느림)
- 실행 머신에 런타임 설치 필요
- JIT 자체가 메모리·CPU를 소비

### AOT 계열 — IL2CPP · NativeAOT · Mono Full AOT

AOT(Ahead-Of-Time)는 **앱을 배포하기 전**, 개발자 빌드 머신에서 IL을 네이티브 코드로 번역해 둡니다.

**장점**
- **Cold Start가 극도로 빠름** — 번역 비용이 이미 지불됨
- **JIT가 허용되지 않는 플랫폼**(iOS, 콘솔, WebAssembly)에서 유일한 선택지
- 배포 시 런타임 설치 불필요 (NativeAOT의 경우 단일 바이너리)

**단점**
- **런타임에 새 코드를 만들 수 없음** → `Reflection.Emit` 깨짐
- **동적 제네릭 인스턴스화 제한** → 런타임에 새로운 `List<MyRuntimeType>` 못 만듦
- **빌드 시간 증가** — 모든 IL을 미리 번역
- 모든 제네릭 인스턴스화를 사전 생성 → 배포 바이너리 크기 증가

이 표 한 장이 이후 모든 비교의 기반이 됩니다.

---

## Part 2. 각 런타임 소개

### CLR — .NET Framework의 런타임

- 출시: 2002년
- 플랫폼: Windows 전용
- 컴파일: JIT
- 상태: **동결**. .NET Framework 4.8.1(2022)이 마지막 릴리스
- 특이점: WPF·WinForms·WCF 같은 Windows 전용 상위 프레임워크와 단단히 묶여 있음

신규 개발에서는 CLR을 선택할 이유가 없습니다. 레거시 유지보수 용도로만 의미가 있습니다.

### CoreCLR — 현대 .NET의 메인 런타임

- 출시: 2016년 (.NET Core 1.0), 2020년부터 .NET 5+로 흡수
- 플랫폼: Windows·Linux·macOS·FreeBSD
- 컴파일: **Tiered JIT** (Tier 0 빠른 초기 번역 → Tier 1 최적화 재번역)
- 특이점: **PGO(Profile-Guided Optimization)** 지원, 실행 통계로 핫 코드를 더 공격적으로 최적화

CoreCLR은 JIT의 단점(초기 비용)을 **Tiered Compilation**으로 완화한 런타임입니다. 시작할 때는 빠른 Tier 0 번역만 하고, 자주 호출되는 핫 코드만 나중에 Tier 1으로 다시 컴파일합니다. ([Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr))

서버·웹·데스크톱·WASM까지 .NET의 기본값이자 가장 활발히 발전하는 런타임입니다.

### Mono — 크로스 플랫폼의 원조

- 출시: 2004년
- 플랫폼: Windows·Linux·macOS·iOS·Android·WebAssembly
- 컴파일: JIT가 기본, **Full AOT 모드도 가능** (iOS처럼 JIT가 금지된 환경용)
- 특이점: 작은 풋프린트. 모바일·임베디드·게임 엔진에 적합

Mono는 2편에서 본 것처럼 외부 오픈소스에서 시작해 Microsoft 공식 구현체가 된 런타임입니다. 2024년 Microsoft가 WineHQ에 소유권을 이관하면서 본가는 유지보수 모드로 들어갔지만, **Unity는 자체 포크를 운영**합니다.

Unity에서 `Scripting Backend: Mono`를 선택하면 이 런타임이 에디터와 데스크톱 빌드에 쓰입니다.

### IL2CPP — Unity가 만든 AOT 파이프라인

- 출시: 2014년
- 플랫폼: iOS·WebGL·콘솔(PS5·Xbox·Switch)·Android·Windows·macOS
- 컴파일: **AOT 전용**. IL을 **C++ 코드로 변환**한 뒤 플랫폼별 C++ 툴체인(Xcode·Emscripten·콘솔 SDK)으로 네이티브 바이너리 생성
- 특이점: `Reflection.Emit` 금지, 제네릭 인스턴스화 제한, 빌드 시간 증가

IL2CPP의 존재 이유를 한 줄로 요약하면 이렇습니다. **"iOS·WebGL·콘솔이 JIT를 허용하지 않기 때문에, Mono Full AOT로는 풀리지 않는 성능·제약 문제를 Unity가 자체 AOT 파이프라인으로 해결하려 했기 때문입니다."** ([Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)) 내부 동작 원리는 Unity가 직접 공개한 ["An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) 연재에서 확인할 수 있습니다.

### NativeAOT — Microsoft의 서버·클라우드 AOT

- 출시: 2022년 (.NET 7, 콘솔 앱·라이브러리 지원 — [.NET Blog — "Announcing .NET 7" (2022.11.08)](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/))
- 2023년 (.NET 8, ASP.NET Core 지원 확대)
- 플랫폼: Windows·Linux·macOS·iOS (실험적)·Android (실험적)
- 컴파일: **AOT 전용**. IL을 네이티브 코드로 직접 컴파일 (C++ 경유 안 함)
- 특이점: **단일 네이티브 바이너리** 배포, 런타임 설치 불필요, 시작 시간 극히 빠름

NativeAOT의 타깃은 **컨테이너·서버리스·CLI 도구**입니다. 게임 개발자가 IL2CPP를 쓰는 이유(플랫폼이 JIT를 금지)와는 다른 동기입니다. NativeAOT가 실험 단계에서 공식 릴리스로 승격된 과정은 ["Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/)에서 상세히 기술됐습니다. ([Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

---

## Part 3. 런타임 비교 매트릭스

같은 축으로 다섯 런타임을 한눈에 비교합니다.

| 축 | CLR | CoreCLR | Mono | IL2CPP | NativeAOT |
|----|-----|---------|------|--------|-----------|
| **컴파일 방식** | JIT | Tiered JIT | JIT (+Full AOT 옵션) | AOT only | AOT only |
| **크로스 플랫폼** | Windows | Win/Lin/Mac | 광범위 | Unity 지원 모든 플랫폼 | Win/Lin/Mac |
| **Cold Start** | 느림 | 중간 (Tier 0 빠름) | 중간 | **빠름** | **가장 빠름** |
| **실행 중 재최적화** | 없음 | **있음 (PGO)** | 제한적 | 없음 | 없음 |
| **`Reflection.Emit`** | O | O | O | **X** | **X** |
| **`Expression.Compile`** | O | O | O | **보간 모드** | **보간 모드** |
| **동적 제네릭 인스턴스화** | O | O | O | **제한적** | **제한적** |
| **런타임 설치 필요** | O | O (또는 Self-contained) | O | X (엔진 내장) | **X** |
| **배포 크기** | 작음 (런타임 별도) | 중간 | 중간 | 큼 (엔진 포함) | 중간 |
| **빌드 시간** | 빠름 | 빠름 | 빠름 | **매우 느림** | **느림** |
| **주 용도** | 레거시 Windows | 서버·웹·데스크톱 | Unity 에디터·데스크톱 | Unity 모바일·콘솔 | 서버리스·CLI |

### 이 표에서 읽어야 할 세 가지

**① AOT 두 런타임(IL2CPP, NativeAOT)이 같은 제약을 공유합니다.**
`Reflection.Emit`·`Expression.Compile`·동적 제네릭 — 이 세 항목이 모두 **JIT에 의존하는 기능**이기 때문입니다. AOT 환경에서는 근본적으로 실행 타임에 새 IL을 만들 엔진이 없습니다.

**② Cold Start는 AOT가 압도적으로 유리합니다.**
iOS에서 JIT가 금지되는 건 보안 이유(메모리 `W^X` 원칙)이지만, AOT의 **빠른 기동**은 서버리스·CLI 도구에서도 결정적 장점입니다. `dotnet run` 한 번 할 때마다 수백 밀리초의 JIT 비용을 지불하지 않아도 됩니다.

**③ CoreCLR의 Tiered JIT는 절충안입니다.**
JIT 비용을 완전히 없앨 수는 없지만, **Tier 0에서 빠르게 번역 → 자주 호출되는 코드만 Tier 1으로 최적화**하는 방식으로 "최악은 피하고 최선은 추구"합니다. 이것이 서버·웹에서 CoreCLR이 여전히 기본값인 이유입니다.

---

## Part 4. IL2CPP의 실제 파이프라인

IL2CPP의 "IL을 C++로 바꾼 뒤 네이티브로 컴파일한다"는 설명이 추상적으로 들릴 수 있습니다. 실제 빌드 파이프라인을 도식화하면 이렇습니다.

<div class="il2cpp-pipeline-container">
<svg viewBox="0 0 860 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="IL2CPP 빌드 파이프라인">
  <defs>
    <marker id="il2cpp-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="il2cpp-arrow-head"/>
    </marker>
  </defs>

  <text x="430" y="28" text-anchor="middle" class="il2cpp-pipeline-title">IL2CPP 빌드 파이프라인 — IL에서 네이티브 바이너리까지</text>

  <g>
    <rect x="20" y="90" width="130" height="60" rx="8" class="il2cpp-box-cs"/>
    <text x="85" y="118" text-anchor="middle" class="il2cpp-box-text-bold">C# 소스</text>
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
    <text x="765" y="114" text-anchor="middle" class="il2cpp-box-text-bold">플랫폼 툴체인</text>
    <text x="765" y="130" text-anchor="middle" class="il2cpp-box-text-sm">Xcode / Emscripten</text>
    <text x="765" y="144" text-anchor="middle" class="il2cpp-box-text-sm">콘솔 SDK</text>
  </g>

  <line x1="150" y1="120" x2="175" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="310" y1="120" x2="335" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="470" y1="120" x2="495" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="660" y1="120" x2="685" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>

  <text x="85" y="178" text-anchor="middle" class="il2cpp-stage-label">1. 작성</text>
  <text x="245" y="178" text-anchor="middle" class="il2cpp-stage-label">2. IL 컴파일</text>
  <text x="405" y="178" text-anchor="middle" class="il2cpp-stage-label">3. IL 중간물</text>
  <text x="580" y="178" text-anchor="middle" class="il2cpp-stage-label">4. C++ 변환 (Unity)</text>
  <text x="765" y="178" text-anchor="middle" class="il2cpp-stage-label">5. 네이티브 빌드</text>
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

### 왜 중간에 C++을 끼워 넣었는가

IL에서 네이티브 코드로 **직접 가는 컴파일러**도 이론상 가능합니다(NativeAOT가 그렇게 합니다). 그런데 Unity는 **IL → C++ → 네이티브** 2단계를 선택했습니다. 이 선택의 근거는 Unity가 공개한 ["IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) 블로그에서 실제 생성된 C++ 예제와 함께 설명됩니다. 요약하면 다음과 같습니다.

**① 플랫폼별 C++ 툴체인 재활용**
iOS는 Xcode LLVM, WebGL은 Emscripten, 콘솔은 각 제조사 SDK, Android는 NDK — 플랫폼마다 **이미 최고 수준으로 최적화된 C++ 컴파일러**가 존재합니다. IL을 C++로만 변환해두면, 나머지 최적화는 플랫폼 툴체인이 담당합니다. 같은 수준을 달성하려면 Unity는 **플랫폼마다 별도 백엔드**를 개발·유지해야 했을 겁니다.

**② 플랫폼별 특수 기능 접근**
C++ 중간물은 각 플랫폼의 네이티브 라이브러리·SDK와 자연스럽게 연동됩니다. 직접 AOT 컴파일러를 만들었다면 이런 통합이 훨씬 복잡했을 겁니다.

**③ 디버깅 접근성**
IL2CPP 빌드에서 런타임 크래시가 나면 생성된 C++ 코드를 읽을 수 있습니다. 이것이 순수 바이너리 출력보다 훨씬 추적이 쉽습니다.

---

## Part 5. AOT 환경의 다섯 가지 제약

Microsoft 공식 문서가 명시한 NativeAOT의 주요 제약입니다. IL2CPP도 **대부분 동일한 제약**을 갖습니다. ([Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

### ① `Reflection.Emit` 금지

**현상**: `System.Reflection.Emit`으로 런타임에 동적으로 메서드·타입을 만드는 코드가 실행되지 않습니다.

**원인**: AOT 환경은 **런타임에 IL을 받아 네이티브로 번역할 JIT가 없습니다**. Emit은 IL을 만드는 API인데, 받아줄 번역기가 없으니 작동할 수 없습니다.

**영향**: 많은 직렬화 라이브러리(기존 `Newtonsoft.Json` 일부 경로), 빠른 프록시 생성(Castle DynamicProxy), DI 컨테이너의 동적 생성자 주입 등이 깨지거나 느려집니다.

**대안**: **Source Generator**. 컴파일 타임에 필요한 코드를 생성해두면 런타임 Emit이 필요 없습니다. `System.Text.Json`은 이 방향으로 전환돼 AOT 친화적입니다.

### ② `Expression.Compile`은 해석 모드로

**현상**: LINQ 쿼리나 `Expression<Func<T>>.Compile()`이 **인터프리터 모드**로 실행됩니다. 컴파일된 네이티브 코드만큼 빠르지 않습니다.

**원인**: Expression 컴파일은 런타임에 IL을 생성해 JIT하는 방식이라 AOT 환경에서 불가능합니다.

**영향**: ORM(EF Core 일부 경로), 반복 호출되는 LINQ-to-Expression 코드의 성능이 떨어질 수 있습니다.

**대안**: 자주 실행되는 expression은 미리 대리자로 변환해두기. 또는 Source Generator 기반 대안 라이브러리 검토.

### ③ 동적 제네릭 인스턴스화 제한

**현상**: 런타임에 `Type.MakeGenericType(typeof(List<>), runtimeType)` 같은 방식으로 **코드에 없던 제네릭 조합**을 만들면 실패하거나 에러 발생.

**원인**: AOT 컴파일러는 **빌드 시점에 모든 제네릭 인스턴스를 미리 생성**합니다. 빌드 시점에 없던 조합은 네이티브 코드도 없습니다.

**영향**: 런타임 타입 기반 `Dictionary<string, object>` 구성을 `Dictionary<string, RuntimeType>`으로 최적화하는 일반적 패턴이 깨집니다.

**대안**: 제네릭 조합을 빌드 시점에 명시적으로 한 번 사용 (`_ = new List<MyType>()` 같은 "힌트") 또는 비제네릭 버전으로 우회.

### ④ 리플렉션의 트리머 상호작용

**현상**: `Type.GetMethod("SomeMethod")` 같은 문자열 기반 리플렉션이 예기치 않게 실패 — **트리머가 해당 메서드를 사용되지 않는다고 판단해 제거**했기 때문.

**원인**: AOT 배포는 **트리밍(Trimming)이 필수**입니다. 사용되지 않는 코드를 빌드 결과에서 제거해 바이너리 크기를 줄이는데, 문자열 기반 참조는 정적 분석이 불가능합니다.

**영향**: 많은 구형 라이브러리가 AOT 빌드에서 런타임 에러.

**대안**: `DynamicDependency` 속성으로 트리머에 힌트 주기, 또는 Source Generator로 리플렉션 제거.

### ⑤ 배포 바이너리 크기 증가

**현상**: AOT 빌드는 **모든 제네릭 인스턴스·런타임 라이브러리·의존성을 단일 바이너리**에 포함하므로, framework-dependent JIT 빌드보다 파일이 큽니다.

**원인**: "Self-contained"가 기본이기 때문. 런타임 설치가 없는 대신 앱 안에 들고 다닙니다.

**영향**: 모바일 앱 설치 크기, 컨테이너 이미지 크기, 배포 시간 증가.

**대안**: 공격적 트리밍·`PublishTrimmed=true`·불필요한 기능 플래그 끄기.

---

## Part 6. 런타임 의사결정 가이드

프로젝트 타입별로 어떤 런타임을 선택해야 하는지 간단한 트리로 정리합니다.

**서버·웹 API를 만든다** → **CoreCLR** (.NET 8+). 고부하·저지연·빠른 배포가 요구되면 **NativeAOT 검토**. 단 반드시 AOT 제약 체크.

**CLI 도구·서버리스 함수를 만든다** → **NativeAOT**. Cold Start가 결정적이고, 의존성이 많지 않은 경우 AOT 제약 감수 가능.

**Unity로 게임을 만든다** → Editor·데스크톱 빌드는 **Mono**. iOS·WebGL·콘솔 빌드는 **IL2CPP** (강제). 데스크톱 빌드도 IL2CPP로 성능 개선 가능.

**Windows 데스크톱 앱을 신규 개발한다** → **CoreCLR + WPF/WinForms on .NET 8+**. CLR(.NET Framework)은 피함.

**레거시 .NET Framework 시스템을 유지한다** → **CLR**. 단 신규 기능 개발은 .NET 8+로 점진 이관 계획 필요.

**모바일 앱을 만든다 (비 Unity)** → 2024년 Xamarin 지원 종료 이후로는 **.NET MAUI**가 공식 경로. 내부적으로 Mono + NativeAOT 혼합.

---

## 요약

이번 편의 핵심을 네 줄로 정리합니다.

1. **.NET 런타임은 JIT 계열과 AOT 계열로 나뉘고**, 이 축 하나가 성능 특성·제약·배포 크기의 대부분을 결정합니다.
2. **AOT 계열의 제약은 플랫폼 제약이 아니라 설계 선택**입니다. `Reflection.Emit`·동적 제네릭·`Expression.Compile`이 깨지는 것은 런타임에 JIT가 없기 때문이고, 이는 IL2CPP·NativeAOT 모두 공통입니다.
3. **IL2CPP가 IL → C++ → 네이티브 2단계를 거치는 이유**는 플랫폼별 C++ 툴체인의 고수준 최적화를 재활용하기 위해서입니다.
4. **게임 프로그래머가 Unity에서 만나는 제약**(Reflection.Emit, 제네릭 함정, 트리머 이슈)은 런타임 설계의 필연적 귀결이고, Source Generator 같은 **컴파일 타임 메타프로그래밍**으로 우회하는 것이 현대적 해법입니다.

---

## Foundation 시리즈 마무리

3편에 걸쳐 **.NET의 지도(1편) → 역사(2편) → 런타임 갈래(3편)**를 둘러봤습니다. 이 세 편은 앞으로 이어질 모든 C# 시리즈의 **공통 좌표계**가 됩니다.

다음 시리즈는 **비동기 시리즈(6편)**입니다. 오늘 다룬 JIT·AOT 맥락이 `UniTask`가 왜 `Task`보다 Unity에 적합한지, `async/await`가 IL2CPP에서 어떻게 변형되는지, `Reflection.Emit`을 피한 Source Generator가 왜 중요한지에 자연스럽게 연결됩니다.

---

## 참고 자료

### 1차 출처 · 공식 발표 및 기술 분석

- [.NET Blog — "Announcing .NET 7"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/) · 2022년 11월, NativeAOT 정식 편입을 포함한 .NET 7 릴리스 공식 발표
- [.NET Blog — "Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/) · NativeAOT의 `runtimelab`에서 `runtime`으로 승격된 시점 상세
- [Unity Blog — "An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) · Unity 엔지니어가 직접 쓴 IL2CPP 내부 구조 해설
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · 실제 생성된 C++ 코드 예제로 본 IL → C++ 변환 과정

### 레퍼런스 문서

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · CLR·JIT·AOT·NativeAOT 공식 정의
- [Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR 설계 철학
- [Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · NativeAOT 제약 공식 목록
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · 구현체 비교
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · IL2CPP 공식 문서
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP 선택 가이드
