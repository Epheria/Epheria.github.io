---
title: .NET 역사 — Framework에서 하나의 .NET까지
date: 2026-04-27 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, history, mono, xamarin, dotnet-core]
toc: true
toc_sticky: true
difficulty: beginner
prerequisites:
  - /posts/DotnetEcosystemMap/
tldr:
  - .NET Framework는 2002년 Windows 전용으로 시작했고, 2022년 4.8.1이 마지막 버전으로 동결되었습니다
  - .NET Core는 2016년 Windows 종속성을 끊은 재출발이었고, 2020년 .NET 5에서 두 계보가 하나로 통합됐습니다
  - Mono는 2001년 Linux에서 .NET을 쓰려던 외부 프로젝트로 출발해 Xamarin과 Microsoft를 거치며 공식 구현체로 편입됐고, Unity의 런타임 기반이 되었습니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: 역사를 아는 것이 실용적인 이유

이 편은 세 가지 질문에 답하기 위한 글입니다.

1. **".NET 4"는 왜 건너뛰어졌는가?** — .NET Core 3.1 다음 버전이 왜 4가 아니라 5인가?
2. **"Core"는 왜 이름에서 빠졌는가?** — .NET Core 3.1은 있었는데 .NET Core 5는 왜 없는가?
3. **Unity는 왜 Mono 위에 있는가?** — Microsoft가 만든 런타임이 따로 있는데 Unity는 왜 외부 구현체를 쓰는가?

이 질문들은 **역사를 모르면 답할 수 없습니다**. 공식 문서는 현재 상태만 서술하지, 왜 지금 모습이 됐는지는 알려주지 않습니다. 그 공백을 메우는 것이 이 편의 목적입니다.

역사는 긴 편이니 Part를 나눠 갑니다. **네 시대** — 탄생(2000~2004), 성숙(2005~2013), 대전환(2014~2019), 통합(2020~). 각 시대의 끝에서 게임 프로그래머에게 의미 있는 지점만 짚습니다.

---

## Part 1. 탄생 (2000~2004)

### .NET Framework의 출발

1990년대 후반, Microsoft는 두 방향의 압력을 받고 있었습니다.

- **Sun의 Java가 급부상** — "한 번 작성하면 어디서든 돈다"는 구호가 엔터프라이즈 시장을 흔들었습니다. J2EE 스택은 은행·통신사의 기본 선택지였습니다.
- **Windows 개발 스택의 파편화** — Visual Basic, MFC, COM, ActiveX가 뒤섞여 있었고, 서로 호환이 잘 되지 않았습니다.

Microsoft의 응답이 **.NET Framework**였습니다. 여러 언어(C#·VB.NET·C++/CLI)가 하나의 런타임(CLR)과 하나의 표준 라이브러리(BCL)를 공유하는 설계. Java의 "write once, run anywhere"를 언어 축에서 "write in any .NET language, run on any Windows"로 바꾼 것이라고 볼 수 있습니다.

**2002년 2월 13일, .NET Framework 1.0** 출시. 이때 C# 1.0도 함께 나왔습니다.

한 가지 핵심 제약이 있었습니다. **Windows 전용**이었다는 것. Java가 JVM을 통해 OS 독립성을 확보한 것과 달리, .NET Framework의 CLR은 Windows에서만 돌았습니다. 이 제약이 이후 20년 역사를 끌고 가는 주요 축이 됩니다.

### Mono — Linux에서 .NET을 쓰고 싶었던 사람

같은 시기 스페인 출신 개발자 **Miguel de Icaza**는 GNOME 데스크톱 프로젝트를 이끌고 있었습니다. 그는 .NET 사양이 **ECMA에 공개 표준으로 제출된 것**을 보고, 같은 런타임을 **Linux에서 구현할 수 있지 않을까** 생각했습니다.

- **2001년 7월 19일** — O'Reilly 컨퍼런스에서 **Mono** 프로젝트 발표. 그의 회사 Ximian이 주도.
- **2003년** — Novell이 Ximian 인수. Mono는 Novell의 자산이 됩니다.
- **2004년 6월 30일** — Mono 1.0 출시. C# 1.x와 CLR을 Linux·macOS에서 구동.

이 시점에서 Microsoft는 Mono에 우호적이지도, 적대적이지도 않았습니다. "우리가 만든 게 아니지만 막지도 않는" 상태였습니다. ([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

### 의미

Part 1이 만든 것은 **두 개의 계보**입니다.

- **.NET Framework 계보** — Microsoft 공식, Windows 전용, 상용
- **Mono 계보** — 외부 오픈소스, 크로스 플랫폼, Linux/macOS

이 둘이 하나로 합쳐지기까지는 **15년**이 더 걸립니다.

---

## Part 2. 성숙 (2005~2013)

### .NET Framework의 언어 진화

2005년부터 2010년까지 .NET Framework는 언어와 BCL을 빠르게 확장합니다.

| 연도 | 버전 | 주요 추가 |
|------|------|----------|
| 2005 | 2.0 | **제네릭(Generics)** — C#의 핵심 기능 |
| 2006 | 3.0 | WPF, WCF, WF (Windows 통합 프레임워크들) |
| 2008 | 3.5 | **LINQ** — 질의 표현의 언어화 |
| 2010 | 4.0 | TPL (Task Parallel Library), `dynamic` |
| 2012 | 4.5 | **`async/await`** — 비동기의 언어화 |
| 2015 | 4.6 | RyuJIT(새 JIT), 성능 개선 |
| 2017 | 4.7 | 고DPI 개선 |
| 2019 | 4.8 | JIT 최적화, 마지막 메이저 |
| 2022 | 4.8.1 | 마지막 릴리스 — **사실상 동결** |

.NET Framework는 여기서 멈춥니다. **4.8.1이 마지막 버전**이고, 이후로는 보안 패치만 제공됩니다. Microsoft는 ".NET Framework는 계속 지원하지만 신규 기능은 없다"는 입장을 공식화했습니다. ([Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies))

### Mono의 확장과 Xamarin 창립

Mono도 같은 시기에 성숙합니다.

- **2011년 4월** — Attachmate가 Novell을 인수하면서 Mono 팀 해고 위기.
- **2011년 5월 16일** — Miguel de Icaza가 **Xamarin**이라는 회사를 창립하며 Mono를 이어받습니다.
- Xamarin은 Mono를 상업 제품화 — **iOS·Android용 C# 개발 도구**(MonoTouch, Mono for Android)로 매출을 창출합니다.

### Unity의 Mono 채택

Unity Technologies는 2005년 게임 엔진 Unity를 출시했고, 스크립팅 언어로 **Mono 기반 C#(과 초기의 UnityScript·Boo)**을 채택합니다. 그 이유는 단순합니다.

- **크로스 플랫폼**: Unity는 처음부터 Mac·Windows·콘솔을 타깃으로 했고, .NET Framework는 Windows에서만 돌았습니다. Mono만이 선택지였습니다.
- **작은 풋프린트**: Mono는 모바일·임베디드를 타깃으로 설계돼 메모리 사용이 적었습니다.
- **라이선스 유연성**: 상용 라이선스 협상이 가능한 구조였습니다.

이 결정이 **오늘날 Unity 게임의 C# 코드가 Mono 런타임 위에서 도는 이유**입니다. 20년 전의 엔지니어링 선택이 지금까지 이어지고 있습니다.

### 의미

Part 2에서 .NET Framework는 **완성도 높은 상용 Windows 스택**이 되었고, Mono는 **크로스 플랫폼 .NET의 유일한 실용적 선택**이 되었습니다. 두 계보는 점점 더 다른 길을 갔습니다.

---

## Part 3. 대전환 (2014~2019)

### Microsoft의 전략 전환

**2014년 4월**, Microsoft는 개발자 컨퍼런스 Build에서 두 가지를 발표합니다.

1. **.NET Foundation 설립** ([Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation)) — .NET 생태계의 오픈소스 운영을 관리하는 비영리 재단. Miguel de Icaza(당시 Xamarin CTO)가 초기 이사회에 포함
2. **.NET Core 프로젝트 공개** — Windows 종속성을 끊은 **새로운 .NET 구현체** 개발 선언

같은 해 **2014년 11월**, Microsoft는 Connect() 컨퍼런스에서 **.NET 서버 스택 전체를 오픈소스로 전환**하고 Linux·macOS로 확장하겠다고 공식 발표합니다. ([Microsoft News — .NET open source and cross-platform (2014.11.12)](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/), [".NET Core is Open Source" — .NET Blog](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/))

이것은 Microsoft의 역사적 전환점입니다. 이전까지 Microsoft는 Windows를 중심에 두고 모든 것을 설계했습니다. 하지만 이 시점에 판도가 바뀌고 있었습니다.

- 서버 시장은 **Linux가 압도적**이 됐습니다.
- 클라우드(Azure) 전략상 Linux 지원은 선택이 아니라 필수가 됐습니다.
- 개발자들은 Mac을 쓰고 있었습니다.

이 흐름을 따라잡으려면 **.NET을 Windows에서 분리**해야 했습니다. .NET Framework의 코드베이스는 Windows API와 너무 얽혀 있어 이식이 불가능했기 때문에, **처음부터 다시 쓰기로** 결정합니다. 그것이 .NET Core입니다.

### Xamarin 인수

**2016년 2월 24일**, Microsoft는 **Xamarin을 인수**한다고 공식 발표합니다. ([Microsoft Blog — "Microsoft to acquire Xamarin" (2016.02.24)](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/)) 이 결정의 의미는 두 가지였습니다.

- Mono가 **Microsoft 공식 자산**이 되었습니다. 외부 오픈소스 구현체가 본가로 편입된 것입니다.
- **2016년 3월**, Mono는 **MIT 라이선스로 재배포**됩니다. 상용 Xamarin 라이선스 없이도 누구나 자유롭게 사용 가능해졌습니다.

Unity 개발자에게 이 사건은 조용한 변화였지만, **.NET 생태계의 경계가 다시 그려진 시점**이었습니다. 14년 동안 외부에서 Linux·macOS의 .NET을 지탱해온 프로젝트가 Microsoft의 품으로 들어왔습니다.

### .NET Core 1.0~3.1

- **2016년 6월 27일 — .NET Core 1.0** 출시. Windows·Linux·macOS에서 동작하는 첫 공식 .NET 구현체
- **2017년 — .NET Core 2.0**. .NET Standard 2.0 지원으로 Framework와의 API 호환성 크게 개선
- **2019년 12월 — .NET Core 3.1 LTS**. 안정판. 여기까지가 ".NET Core" 브랜딩의 마지막

이 시기 **.NET 생태계에는 세 가지 구현체가 공존**했습니다.

- **.NET Framework 4.x** — Windows 상용 스택 (레거시 유지)
- **.NET Core 3.1** — 크로스 플랫폼 새 스택 (신규 개발 권장)
- **Mono (+ Xamarin)** — 모바일·게임 (Xamarin은 모바일, Mono는 Unity)

**같은 C# 코드를 세 군데서 돌려야 하는 상황**이 된 겁니다. 개발자와 라이브러리 저자들은 .NET Standard라는 API 계약으로 세 구현체를 묶으려 했지만, 근본적으로는 세 런타임·세 BCL이 존재하는 상태였습니다.

### 의미

Part 3이 만든 것은 **세 구현체의 난립**과 **통합의 예고**였습니다. Microsoft는 이 혼란을 .NET 5에서 끝내겠다고 발표합니다.

---

## Part 4. 통합 (2020~현재)

### .NET 5 — 두 가지 이름이 풀리다

**2020년 11월, .NET 5** 출시. ([".NET Blog — Announcing .NET 5.0" (2020.11.10)](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/)) 여기서 두 가지 결정이 내려졌습니다.

**① 버전 번호 4를 건너뛴다.**
.NET Core 3.1의 다음 버전이 왜 4가 아니라 5였을까요? 이유는 **.NET Framework 4.x와의 혼동을 피하기 위해서**였습니다. ([Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET))

같은 회사가 만든 두 개의 ".NET 4"가 존재하는 상황은 말이 되지 않습니다. 하나는 Windows 전용 레거시, 다른 하나는 크로스 플랫폼 미래. 버전 번호 충돌을 피하려면 하나가 양보해야 했고, Core가 4를 건너뜁니다.

**② "Core"를 이름에서 떨어뜨린다.**
.NET Core는 **.NET**이 되었습니다. 이유는 **정체성 선언**이었습니다.

> ".NET Core"는 ".NET의 축소판"이라는 인상을 줍니다. 하지만 이제 .NET Core가 기능·성능·생태계 면에서 Framework를 넘어섰으니, 이것이 **정식 .NET**입니다.

이후로는 `.NET 5`, `.NET 6`, `.NET 7` 식으로 부릅니다. 공식 문서에서도 **".NET Core"라는 말은 3.1 이하를 가리킬 때만** 씁니다.

### 버전 흐름

| 연도 | 버전 | 종류 | 주요 이슈 |
|------|------|------|----------|
| 2020.11 | .NET 5 | STS | 통합의 출발 |
| 2021.11 | .NET 6 | **LTS** | Hot Reload, Minimal API |
| 2022.11 | .NET 7 | STS | **NativeAOT 첫 도입** (콘솔 앱·라이브러리) |
| 2023.11 | .NET 8 | **LTS** | NativeAOT 확대, ASP.NET Core AOT |
| 2024.11 | .NET 9 | STS | 성능 개선 |
| 2025.11 | .NET 10 | **LTS** | 현재 안정판 |

LTS(Long Term Support)는 3년 지원, STS(Standard Term Support)는 1.5년 지원입니다. 짝수 버전이 LTS 관례입니다.

### Mono의 마지막 장

**2024년 8월 27일**, Microsoft는 **Mono 프로젝트의 소유권을 WineHQ에 이관**한다고 발표합니다. WineHQ는 Linux에서 Windows 프로그램을 돌리는 Wine의 개발팀입니다. ([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

이 결정의 의미는 명확합니다. Microsoft가 관심을 두는 런타임은 **CoreCLR(.NET 8+)과 NativeAOT**입니다. Mono는 더 이상 Microsoft의 전략적 자산이 아닙니다.

단 Unity의 Mono는 **별도로 유지**됩니다. Unity Technologies는 자체적으로 Mono 포크를 관리해왔고, 엔진 빌드 파이프라인에 깊게 통합돼 있기 때문에 본가(WineHQ)와 분리된 상태로 계속 발전합니다.

### 의미

Part 4가 만든 것은 **이름의 정리**였습니다. 지금 시점에서 ".NET"이라는 단어의 현대적 용법은 이렇게 확정됐습니다.

- **.NET** (버전 번호 없이) = 2020년 이후 통합 .NET 구현체 (CoreCLR 기반)
- **.NET Framework** = 2002년부터 2022년까지의 Windows 전용 레거시 (4.8.1에서 동결)
- **Mono** = 모바일·게임용 구현체 (Unity·WineHQ가 관리)
- **.NET Core** = 2016~2019년의 과도기 이름 (현재는 쓰지 않음)

---

## .NET 계보 타임라인

네 시대를 하나의 그림으로 요약합니다.

<div class="dotnet-lineage-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET 역사 계보 타임라인 2001-2025">
  <text x="450" y="28" text-anchor="middle" class="dotnet-lineage-title">.NET 계보 — 2001년부터 2025년까지</text>

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
    <text x="70" y="95" class="dotnet-lane-name">.NET Framework (2002~2022, Windows 전용)</text>
    <text x="700" y="95" text-anchor="end" class="dotnet-lane-tag">4.8.1에서 동결</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="mono">
    <rect x="80" y="130" width="780" height="40" rx="6" class="dotnet-lane-mono"/>
    <text x="90" y="155" class="dotnet-lane-name">Mono (2001~, 크로스 플랫폼, 2016 Microsoft 편입, 2024 WineHQ 이관)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="xamarin">
    <rect x="340" y="190" width="280" height="40" rx="6" class="dotnet-lane-xamarin"/>
    <text x="350" y="215" class="dotnet-lane-name">Xamarin (2011~2024)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="core">
    <rect x="500" y="250" width="180" height="40" rx="6" class="dotnet-lane-core"/>
    <text x="510" y="275" class="dotnet-lane-name">.NET Core (2016~2019)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="dotnet">
    <rect x="680" y="310" width="180" height="40" rx="6" class="dotnet-lane-dotnet"/>
    <text x="690" y="335" class="dotnet-lane-name">.NET (2020~)</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="500" y1="250" x2="500" y2="350" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="510" y="340" class="dotnet-event-label">통합 흐름</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="680" y1="110" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <line x1="680" y1="290" x2="680" y2="310" class="dotnet-event-line-solid"/>
    <text x="688" y="306" class="dotnet-event-label">.NET 5 통합</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="620" y1="230" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="860" y1="170" x2="860" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="835" y="302" text-anchor="end" class="dotnet-event-label">Unity Mono는 유지</text>
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

## 서두의 세 질문에 답하기

이제 처음 던진 세 질문에 답할 수 있습니다.

### Q1. 왜 .NET 4가 건너뛰어졌는가?

.NET Core 3.1 다음 버전이 4가 되었다면 **.NET Framework 4.x와 이름이 겹쳐서** 혼란이 극심했을 것입니다. 같은 회사가 "4"라는 이름으로 두 개의 서로 다른 .NET을 동시에 가지고 있을 수는 없기 때문에, Core 쪽이 5로 건너뛰었습니다.

### Q2. 왜 "Core"가 이름에서 빠졌는가?

.NET Core가 완성도 면에서 .NET Framework를 넘어선 시점에서, Microsoft는 **"Core"라는 부제가 오히려 하위 호환 축소판이라는 인상**을 준다고 판단했습니다. 2020년 .NET 5부터 Core가 사라지고, 그것이 **"진짜 .NET"**이 되었습니다. Framework는 4.8.1에서 동결된 레거시가 됐습니다.

### Q3. Unity는 왜 Mono 위에 있는가?

2005년 Unity가 엔진을 출시하던 시점에는 **.NET Framework가 Windows 전용**이었습니다. Mac·Linux·콘솔을 타깃으로 하는 게임 엔진 입장에서 Mono가 유일한 실용적 선택이었습니다. 그 결정이 20년간 유지되면서 Unity의 엔진 빌드 파이프라인, 에디터, 플러그인 생태계가 모두 Mono 위에 쌓였고, 바꾸기 어려운 기반이 되었습니다. 2014년 등장한 Unity의 **IL2CPP**는 이 제약을 부분적으로 우회하는 대안입니다(3편에서 상세히 다룹니다).

---

## 게임 프로그래머에게 이 역사가 의미하는 것

역사를 정리한 뒤 남는 **실용적 결론 네 가지**입니다.

**① Unity의 Mono는 본가와 분리됐습니다.**
2024년 Microsoft가 Mono를 WineHQ에 이관한 이후, **Unity의 Mono는 Unity가 자체 유지**합니다. Mono 본가의 업데이트를 기다리는 관계가 아닙니다.

**② `.NET Standard`는 통합 이전의 유산입니다.**
.NET Core 시대에 Framework·Mono·Core 세 구현체의 API를 묶기 위해 만들어진 계약입니다. 지금은 .NET 5+가 통합됐기 때문에 신규 라이브러리에서는 `.NET Standard` 대신 **구체적 .NET 버전 타기팅**이 권장됩니다. 단 Unity가 쓰는 API 호환 레벨이 여전히 `.NET Standard 2.1` 기반이라 이 유산은 계속 살아있습니다.

**③ ".NET Framework 프로젝트"를 지금 시작하지 마세요.**
4.8.1로 동결됐고 신규 기능이 없습니다. 레거시 유지 보수가 아니라면 모든 신규 개발은 .NET 8+ (또는 Unity의 Mono/IL2CPP) 위에서 시작합니다.

**④ ".NET Core"라는 말을 봤을 때의 시점 감각.**
"We use .NET Core 3.1"이라고 쓰여 있으면 **2019년 이후 업데이트가 없는 프로젝트**일 가능성이 높습니다. 기술 블로그·Stack Overflow 답변의 날짜를 볼 때도 "Core"라는 단어가 들어있으면 2019년 이전 자료로 간주합니다.

---

## 요약

이번 편의 핵심을 세 줄로 압축합니다.

1. **.NET Framework(2002)와 Mono(2001)가 15년 간 평행선으로 발전**했고, 2014년 Microsoft의 전략 전환으로 **2020년 .NET 5에서 통합**됐습니다.
2. **"Core"는 과도기 이름**이고 지금은 그냥 **.NET**입니다. 버전은 5·6·7·8·9·10으로 이어지며 짝수가 LTS입니다.
3. **Unity의 Mono는 독자적**으로 유지되고, Microsoft의 관심은 **CoreCLR과 NativeAOT**로 이동했습니다.

---

## 다음 편 예고

3편에서는 시간 축 대신 **공간 축**으로 .NET을 봅니다. 현재 시점에서 존재하는 **다섯 런타임 구현체** — CLR · CoreCLR · Mono · IL2CPP · NativeAOT — 를 JIT/AOT·메모리·리플렉션·제네릭·배포 관점에서 비교합니다. 게임 프로그래머에게 가장 실용적인 편이 될 겁니다.

---

## 참고 자료

### Microsoft 공식 1차 출처

- [.NET Blog — "Announcing .NET 5.0"](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/) · 2020년 11월 10일, .NET 5 통합 공식 발표 포스트
- [Microsoft Blog — "Microsoft to acquire Xamarin"](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/) · 2016년 2월 24일, Xamarin 인수 공식 발표
- [.NET Blog — ".NET Core is Open Source"](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/) · 2014년, .NET Core 오픈소스 선언
- [Microsoft News — "Microsoft takes .NET open source and cross-platform"](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/) · 2014년 11월 12일, Connect() 이벤트에서 크로스 플랫폼 전환 공식 뉴스룸

### 레퍼런스 자료

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · 공식 용어집
- [Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies) · Framework 버전 공식 기록
- [Wikipedia — .NET Framework version history](https://en.wikipedia.org/wiki/.NET_Framework_version_history) · 버전별 연혁
- [Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)) · Mono 역사
- [Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET) · 통합 및 버전 번호 정책
- [Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation) · 2014년 Build에서 출범
- [endoflife.date — Microsoft .NET](https://endoflife.date/dotnet) · 지원 종료 일정
