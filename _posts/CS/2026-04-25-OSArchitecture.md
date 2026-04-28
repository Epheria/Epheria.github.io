---
title: "CS 로드맵 7편 — OS 아키텍처 입문: Unix, NT, XNU의 갈림길"
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
  - 세 운영체제의 차이는 "기술 선택"이 아니라 "역사적 경로 의존성"이다 — Unix, VMS, NeXTSTEP이라는 1970~80년대의 결정이 오늘의 Linux, Windows, macOS를 만들었다
  - 커널 구조가 다르다 (Linux 모놀리식, Windows NT 하이브리드, macOS XNU는 Mach microkernel 위에 BSD를 얹은 이중 구조)
  - macOS는 Grand Central Dispatch로 스레드 추상화를, Apple Silicon으로 P/E 이질 코어와 16KB 페이지를, Rosetta 2로 하드웨어 TSO 모드를 도입했다
  - 실행 바이너리 포맷(ELF/PE/Mach-O)부터 다르기 때문에 게임 멀티플랫폼 빌드에서 크로스 컴파일이 복잡해진다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: 왜 OS부터 시작하는가

Stage 1에서는 자료구조와 메모리를 다뤘습니다. 배열과 연결 리스트, 해시 테이블, 트리와 그래프, 그리고 힙까지 — 모두 **"데이터를 어떻게 정리할 것인가"**의 이야기였습니다.

Stage 2의 질문은 조금 다릅니다.

> **"스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?"**

이 질문에 답하려면 프로그램이 어떻게 실행되는지, 누가 CPU를 나눠주는지, 메모리가 어떻게 보호되는지를 알아야 합니다. 그것이 **운영체제(OS)**의 역할입니다.

그런데 OS 공부를 시작하면 바로 이상한 벽에 부딪힙니다. 교과서에는 "프로세스는 PCB를 가진다" 같은 추상적인 설명이 나옵니다. 하지만 실제로 macOS에서 `ps` 명령어를 쳐보고, Windows에서 작업 관리자를 열어보면, 세 OS의 세계가 전혀 다르게 보입니다.

- Linux에서는 프로세스 생성이 `fork()` 두 글자로 끝납니다
- Windows에서는 `CreateProcess()`에 12개의 매개변수가 들어갑니다
- macOS에서는 같은 `fork()`를 써도, 그 아래에는 Mach 커널이라는 완전히 다른 것이 있습니다

이 **세 OS의 차이**는 기술적 선택이 아니라 **역사의 산물**입니다. 1969년 Unix의 탄생, 1977년 Berkeley의 분기, 1989년 NeXTSTEP의 도박, 1993년 Windows NT의 설계 — 이 결정들이 오늘 우리가 Unity 게임을 빌드할 때 `.exe`가 나오는지 `.app`이 나오는지를 결정합니다.

Stage 2 첫 편은 **본격적인 이론으로 들어가기 전에 지도를 그리는 작업**입니다. 각 OS가 어떤 혈통에서 왔고, 왜 서로 다른 모습이 되었고, 게임 개발자에게 어떤 차이가 있는지를 훑습니다. 다음 편부터는 프로세스, 스레드, 스케줄링 같은 구체적인 주제로 파고들지만, 그때마다 **"이 개념은 Linux에서 A고 Windows에서 B다"**를 비교할 수 있으려면, 먼저 세 OS의 **뼈대**를 알아야 합니다.

특히 맥 유저이신 독자를 위해 **macOS 특화 섹션**을 자세히 다룹니다. XNU 커널의 독특한 이중 구조, Grand Central Dispatch의 설계 사상, Apple Silicon의 하드웨어 기믹까지 — 다른 OS 책에서는 주변부로 밀리는 이야기들이 여기서는 주인공입니다.

---

## Part 1: 세 OS의 혈통 — 1969년의 결정이 2026년을 만들다

### Unix의 탄생 (1969)

![Ken Thompson과 Dennis Ritchie (1973)](/assets/img/post/cs/os-thompson-ritchie-1973.jpg){: width="500" }
_Ken Thompson (왼쪽)과 Dennis Ritchie (오른쪽), 1973년. Unix와 C 언어의 창시자들. 출처: Jargon File (Public Domain)_

모든 이야기는 1969년 미국 뉴저지의 AT&T Bell Labs에서 시작합니다. **Ken Thompson**과 **Dennis Ritchie**는 GE-645라는 거대한 메인프레임에서 Multics라는 복잡한 OS 프로젝트에 참여하다 좌절을 겪습니다. Multics는 너무 야심 차고, 너무 느리고, 너무 복잡했습니다.

Thompson은 Bell Labs 구석에 방치된 PDP-7이라는 작은 컴퓨터에서 **Multics의 불필요한 복잡성을 덜어낸 단순한 OS**를 취미로 만들기 시작합니다. 이름은 "Multi-" 대신 "Uni-"를 붙여 **UNICS (Uniplexed Information and Computing Service)**. 나중에 이름이 **Unix**로 정착합니다.

Unix의 설계 원칙은 후대에 **"Unix 철학"**으로 불리게 됩니다:

1. **한 가지 일만 잘해라 (Do one thing and do it well)**
2. **모든 것은 파일이다 (Everything is a file)**
3. **프로그램을 조합하라 (Pipe 기호 `|`로 출력을 다음 입력으로)**
4. **텍스트가 범용 인터페이스다**

1973년, Ritchie는 Unix를 **C 언어**로 다시 씁니다. 이것이 결정적이었습니다. 그 전까지 OS는 어셈블리어로만 작성됐기 때문에 다른 하드웨어로 이식할 수 없었는데, C로 작성된 Unix는 **이식 가능한 OS의 시대를 열었습니다**.

1970년대 후반, Unix의 소스 코드는 AT&T가 저렴한 라이선스로 대학에 배포합니다. 특히 **UC Berkeley**가 열정적으로 받아들였고, 학생들은 자기네가 Unix를 고쳐서 배포하기 시작합니다. 이것이 분기점입니다.

### BSD 갈래: Berkeley의 학생들

1977년부터 Berkeley에서 배포한 Unix 파생판을 **Berkeley Software Distribution (BSD)**라 부릅니다. BSD는 기존 Unix에 없던 많은 기능을 추가했습니다:

- **TCP/IP 네트워킹 스택** (1983, 인터넷의 기초)
- **Berkeley Sockets API** (지금도 네트워크 프로그래밍의 표준)
- **가상 메모리 개선**
- **Fast File System (FFS)**

1980년대 중반까지 BSD는 Unix의 사실상 표준 중 하나로 자리잡습니다. 하지만 AT&T가 라이선스 소송을 걸면서 Berkeley는 오랜 법정 다툼에 시달렸고, 그 결과 **AT&T 코드를 완전히 제거한 자유로운 BSD**가 만들어집니다. 이것이 FreeBSD, NetBSD, OpenBSD의 뿌리입니다.

**중요한 점**: BSD는 완전히 오픈소스이고, 라이선스가 GPL(Linux)보다 훨씬 자유롭습니다. 이 때문에 나중에 **Apple이 macOS의 기반으로 BSD를 선택**하게 됩니다. GPL이라면 Apple이 자신의 수정 내용을 모두 공개해야 했을 테지만, BSD 라이선스는 그런 의무가 없었기 때문입니다.

### NeXTSTEP → macOS: Steve Jobs의 귀환

![NeXTcube 컴퓨터 (1990)](/assets/img/post/cs/os-next-cube.jpg){: width="600" }
_NeXTcube (1990), Computer History Museum 소장. 이 컴퓨터에 실린 NeXTSTEP이 오늘의 macOS의 뿌리다. 사진: Michael Hicks, CC BY 2.0_

1985년, Apple에서 쫓겨난 Steve Jobs는 **NeXT**라는 회사를 차립니다. NeXT의 목표는 "대학과 연구자를 위한 고급 워크스테이션"이었습니다. 그 컴퓨터에 실릴 OS가 **NeXTSTEP** (1989)입니다.

NeXTSTEP의 설계는 독특했습니다:

- 커널은 **Mach microkernel** (Carnegie Mellon University에서 개발)
- 그 위에 **BSD Unix layer**를 얹어 POSIX 호환성 제공
- 응용 프로그램 프레임워크는 **Objective-C**로 작성된 **Cocoa** (당시 이름은 AppKit)

당시 이 구조는 학계에서 유행하던 "microkernel이 미래다"라는 사상의 실천이었습니다. 하지만 NeXT 컴퓨터는 상업적으로 실패했고, 회사는 살아남기 위해 하드웨어를 포기하고 **NeXTSTEP을 다른 하드웨어에 이식**하는 방향으로 전환합니다 (1993~).

1996년, 놀라운 일이 일어납니다. **Apple이 NeXT를 인수**합니다. 당시 Apple은 Mac OS 9의 후계가 될 차세대 OS를 만들려던 "Copland" 프로젝트가 실패하면서 기반 기술이 없었습니다. Apple은 외부에서 OS를 사오기로 하고, BeOS와 NeXTSTEP을 놓고 고민하다 NeXTSTEP을 선택합니다. 금액은 약 **4억 달러**.

Steve Jobs는 NeXT와 함께 Apple로 돌아왔고, 1997년 임시 CEO로 복귀합니다. 그리고 **NeXTSTEP이 macOS의 기반**이 되었습니다.

- 1999: **Mac OS X Server 1.0** (NeXTSTEP 기반)
- 2001: **Mac OS X 10.0 Cheetah** — 일반 사용자용
- 2007: **iPhone OS** (Mac OS X의 축소판)
- 2016: "Mac OS X"에서 "**macOS**"로 이름 변경

즉, **오늘 여러분의 MacBook에서 돌아가는 macOS의 커널은 1980년대 NeXT가 1990년대 Apple에 팔았고, 그 뿌리는 Carnegie Mellon University의 Mach 연구 프로젝트로 거슬러 올라갑니다**. 30년 이상 된 설계가 아직 살아 있습니다.

### Linux: 핀란드 대학생의 취미 프로젝트 (1991)

![Linus Torvalds at LinuxCon Europe 2014](/assets/img/post/cs/os-linus-torvalds.jpg){: width="400" }
_Linus Torvalds, LinuxCon Europe 2014. 23년 전 취미 프로젝트가 세계 인프라의 기반이 된 것을 회고 중. 사진: Krd, CC BY-SA 4.0_

1991년, 핀란드 헬싱키 대학의 **Linus Torvalds**는 학교에서 OS 수업을 들으며 Andrew Tanenbaum이 교육용으로 만든 **Minix**를 사용하고 있었습니다. Minix는 훌륭한 교육용 OS였지만, 상업 라이선스로 사용이 제한됐고 Linus는 자기 집 386 PC에서 더 자유롭게 쓸 수 있는 것이 필요했습니다.

그래서 **취미로** OS를 만들기 시작합니다. 8월 25일, comp.os.minix 뉴스그룹에 올린 메시지가 유명합니다:

> *"Hello everybody out there using minix — I'm doing a (free) operating system (just a hobby, won't be big and professional like gnu)..."*

*"크지도, 전문적이지도 않을 것"*이라던 그 취미 프로젝트가 30년 뒤 세계의 절대다수 서버, 스마트폰, 슈퍼컴퓨터에서 돌아가고 있습니다.

Linux는 처음부터 **GPL 라이선스**를 채택했고, 전 세계 개발자들이 기여할 수 있는 모델을 구축했습니다. 그리고 GNU 프로젝트의 유저랜드 도구(gcc, bash, coreutils 등)와 결합해 완전한 OS가 되었습니다 — 그래서 엄밀히는 **GNU/Linux**라고 부릅니다.

**Linux의 결정적 특징** — 커널 구조 면에서:

- **모놀리식 커널**: Unix 전통을 따라 커널에 모든 기능(파일 시스템, 네트워크, 드라이버, 메모리 관리)을 모아둠
- Tanenbaum이 "microkernel이 우월하다"고 비판하자 Linus가 맞받아친 1992년의 논쟁은 OS 역사에서 유명합니다
- 30년이 지난 지금 Linux는 **부분적으로 모듈화된 모놀리식 커널**로 진화했습니다 (커널 모듈 기능)

### VMS → Windows NT: Dave Cutler의 복수

지금까지의 이야기는 모두 Unix 계열입니다. 그런데 Windows는 Unix와 전혀 다른 혈통입니다.

1970년대, **Digital Equipment Corporation (DEC)**은 미니컴퓨터 시장의 강자였습니다. 그들의 OS는 **VMS (Virtual Memory System)**로, 대형 서버를 위한 고안정성 OS였습니다. VMS의 수석 설계자가 **Dave Cutler**였습니다.

1988년, DEC에서 새 프로젝트가 무산되자 Dave Cutler는 팀을 이끌고 **Microsoft로 이적**합니다. Microsoft의 Bill Gates가 "OS/2의 뒤를 이을 차세대 32비트 OS를 만들어 달라"고 제안했기 때문입니다.

Cutler는 **Windows NT** (NT = New Technology)를 설계합니다. 내부적으로 VMS의 많은 아이디어를 가져왔습니다 — 심지어 VMS의 각 문자를 한 칸씩 밀면 WNT가 된다는 농담이 있을 정도입니다 (V→W, M→N, S→T).

Windows NT의 핵심 특징:

- **하이브리드 커널**: microkernel처럼 서브시스템을 나눴지만, 성능을 위해 많은 부분을 커널 공간에 두었습니다
- **POSIX 서브시스템, OS/2 서브시스템, Win32 서브시스템**이 분리 — 이론상 다른 OS API를 동시에 지원
- **유니코드 우선**: 설계 단계부터 Unicode를 전제 (UTF-16)
- **멀티 아키텍처 지원**: x86, MIPS, Alpha, PowerPC (초기에는)

1993년 Windows NT 3.1이 출시됐고, 이후 NT 4.0, Windows 2000, XP, 7, 10, 11까지 모두 **같은 NT 커널 계보**를 따릅니다. 즉, 여러분이 Windows 11에서 Unity를 빌드할 때 돌아가는 커널의 뿌리는 **DEC VMS (1977)**로 이어집니다.

한편 Windows 95, 98, ME는 **완전히 다른 혈통**이었습니다 — MS-DOS 기반의 Windows 1.0~3.1 계보. Microsoft는 2001년 Windows XP에서 이 두 계보를 NT 쪽으로 통합하며 DOS 계보를 끝냅니다.

### 혈통 트리

지금까지의 이야기를 시각화하면 다음과 같습니다.

<div class="os-lineage-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three OS lineage tree">
  <defs>
    <marker id="os-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="os-arrow-head" />
    </marker>
  </defs>

  <text x="450" y="28" text-anchor="middle" class="os-title">세 운영체제의 혈통 — 1969~2026</text>

  <g class="os-lane os-unix-lane">
    <rect x="20" y="55" width="600" height="340" rx="8" class="os-lane-bg"/>
    <text x="320" y="78" text-anchor="middle" class="os-lane-label">Unix 계열</text>
  </g>

  <g class="os-lane os-vms-lane">
    <rect x="640" y="55" width="240" height="340" rx="8" class="os-lane-bg"/>
    <text x="760" y="78" text-anchor="middle" class="os-lane-label">VMS 계열</text>
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

  <text x="450" y="430" text-anchor="middle" class="os-caption">macOS는 BSD → NeXTSTEP 경로로, Linux는 Minix의 영향으로, Windows는 완전히 다른 VMS 경로로.</text>
  <text x="450" y="455" text-anchor="middle" class="os-caption">Unix는 기술이 아니라 <tspan class="os-emph">철학과 API</tspan>를 남겼다. VMS는 Dave Cutler와 함께 Microsoft로 이동했다.</text>
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

## Part 2: 세 OS의 설계 철학

혈통이 다르면 철학도 달라집니다. 같은 문제 — "메모리 부족 시 어떻게 처리할까" — 에 대해 세 OS가 다르게 대응하는 이유가 여기 있습니다.

### Linux: 개방성과 성능

Linux의 문화는 "**해킹 가능성**"에 최고 가치를 둡니다.

- **모든 것이 공개**: 커널 소스 전체가 GPL로 공개되어 누구나 읽고 수정할 수 있습니다
- **파일 시스템을 통한 제어**: `/proc`, `/sys` 파일 시스템으로 커널 상태를 파일처럼 읽고 쓸 수 있습니다
  - 예: `cat /proc/meminfo`로 메모리 상태 확인, `echo 3 > /proc/sys/vm/drop_caches`로 캐시 비우기
- **텍스트 우선**: 설정 파일은 거의 대부분 텍스트. 바이너리 설정 DB(레지스트리)가 없습니다
- **성능 우선**: 호환성보다 성능. 예를 들어 **ABI 호환성은 보장하지만 커널 내부 API는 언제든 바뀔 수 있습니다**
- **다양성 수용**: 배포판(Ubuntu, Arch, Fedora, Alpine…)마다 다른 철학을 허용

**단점**: 파편화. "Linux"라고 뭉뚱그려 말하지만 Ubuntu와 Alpine은 서로 다른 OS에 가까울 정도입니다. 또한 데스크톱 UX는 상대적으로 약합니다.

### Windows: 하위 호환성의 극한

Microsoft의 문화는 "**고객이 이미 돈을 낸 프로그램이 10년 뒤에도 돌아가야 한다**"입니다.

- **하위 호환성이 거의 신성불가침**: Windows 95용 프로그램이 Windows 11에서도 대부분 실행됩니다
  - 유명한 일화: Windows에는 특정 유명 게임(SimCity)의 버그를 우회하는 코드가 커널에 들어 있습니다. 게임이 해제된 메모리를 읽는 버그가 있었는데, Windows 95에서 Win NT로 넘어가며 그 메모리가 즉시 회수되자 SimCity가 크래시했고, Microsoft는 **"SimCity가 실행 중이면 메모리 해제를 지연시키는 코드"**를 Windows에 추가했습니다 (Raymond Chen 블로그 기록)
- **강력한 바이너리 API**: Win32 API는 30년 동안 사실상 그대로. COM, .NET 같은 상위 레이어도 하위 호환을 유지
- **레지스트리**: 시스템 전역 설정 DB. 텍스트 파일 대신 구조화된 키-값 저장소
- **GUI 우선**: 커맨드라인보다 GUI가 먼저 설계됨. PowerShell이 뒤늦게 등장
- **엔터프라이즈 중심**: Active Directory, Group Policy 등 대규모 조직 관리 기능이 매우 강력

**단점**: 하위 호환성을 위한 코드가 누적되면서 **커널이 무거워지고 보안 표면이 넓어집니다**. 30년 전 API의 버그가 2025년에도 사라지지 않는 이유입니다.

### macOS: 통제된 경험과 하드웨어 통합

Apple의 문화는 "**하드웨어와 소프트웨어를 함께 설계한다**"입니다.

- **수직 통합**: Apple은 CPU(Apple Silicon), OS(macOS), GUI(Aqua), 응용 프레임워크(Cocoa), 개발 도구(Xcode)를 모두 직접 만듭니다
- **단일 공식 경로**: Linux처럼 다양한 배포판이 없고, Windows처럼 여러 서브시스템이 공존하지도 않습니다. 한 가지 공식 방식만 지원
- **급진적 전환 수용**: Apple은 과감하게 구버전을 버립니다
  - PowerPC → Intel (2006, Rosetta 1로 전환)
  - 32비트 → 64비트 (2019 macOS Catalina에서 32비트 앱 지원 완전 제거)
  - Intel → Apple Silicon (2020, Rosetta 2로 전환)
- **사용자 경험 우선**: 애니메이션, 폰트 렌더링, 색 관리 같은 것들이 OS 수준에서 일관됨
- **보안 통제**: Gatekeeper, notarization, SIP 같은 계층적 보안 체계로 모든 앱을 Apple의 검증 하에 둠

**단점**: 자유도가 낮고, Apple이 지원을 끊으면 방법이 없습니다 (예: 7년 이상 된 Mac은 최신 macOS 설치 불가). 또한 Apple 생태계 밖과의 호환성은 부차적.

### 철학 비교표

| 기준 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **핵심 가치** | 개방성, 성능 | 호환성, 엔터프라이즈 | 통합, 경험 |
| **커널 수정** | 누구나 가능 | Microsoft만 | Apple만 |
| **바이너리 호환성** | 커널 ABI만 보장 | 30년 유지 | 대전환 시 Rosetta로 |
| **유저 인터페이스** | 선택지 많음 (GNOME, KDE…) | Windows Shell 고정 | Aqua 고정 |
| **설정 저장** | 텍스트 파일 | 레지스트리 | plist (XML/바이너리) |
| **패키지 관리** | 배포판별 (apt, dnf, pacman) | MSI/EXE/Store | App Store / Homebrew / dmg |
| **주요 사용처** | 서버, 임베디드, 개발자 | 기업, 게임, 일반 소비자 | 크리에이티브, 개발자, 일반 |
| **게임** | 열악 (Proton이 개선 중) | 최고 | 중간 (Metal + Apple Silicon) |

---

## Part 3: 커널 구조 — 모놀리식, 마이크로, 하이브리드

OS의 심장은 **커널**입니다. 커널은 하드웨어와 응용 프로그램 사이에서 자원을 관리합니다. 그런데 커널을 **어떻게 구성할 것인가**는 1980년대 이후 OS 설계자들의 오랜 논쟁거리였습니다.

### 세 가지 구조

**1. 모놀리식 커널 (Monolithic Kernel)**

커널 전체가 **하나의 큰 프로그램**입니다. 파일 시스템, 네트워크 스택, 드라이버, 메모리 관리 등이 모두 같은 주소 공간에서 실행됩니다.

- **장점**: 빠름. 커널 내부 호출이 일반 함수 호출
- **단점**: 드라이버 하나 버그로 전체 커널 크래시, 커널이 거대해짐
- **대표**: Linux, 전통적 Unix, FreeBSD

**2. 마이크로커널 (Microkernel)**

커널은 최소한의 기능만 가집니다 — 프로세스, 메모리, IPC(프로세스 간 통신). 파일 시스템, 드라이버 등은 **사용자 공간의 서버 프로세스**로 분리됩니다.

- **장점**: 모듈화, 안정성, 보안
- **단점**: IPC 비용으로 느림 (메시지 전달이 커널을 한 번 더 거침)
- **대표**: 순수 Mach, MINIX 3, QNX, L4, seL4

**3. 하이브리드 커널 (Hybrid Kernel)**

마이크로커널의 모듈화를 추구하지만, 성능을 위해 많은 부분을 **커널 공간**에 둡니다.

- **장점**: 두 구조의 타협
- **단점**: "진짜 microkernel이 아니다"라는 비판
- **대표**: Windows NT, macOS (XNU)

### Linux — 모놀리식의 정점

Linux 커널은 거대합니다. 2024년 기준 소스 코드 **3천만 줄 이상**. 하지만 내부적으로는 모듈화되어 있어 드라이버나 파일 시스템을 **커널 모듈**로 로드/언로드할 수 있습니다.

```bash
# Linux에서 현재 로드된 모듈 보기
lsmod

# 모듈 로드
sudo modprobe nvidia

# 모듈 언로드
sudo rmmod nvidia
```

이 모듈들은 **같은 커널 주소 공간**에서 실행됩니다. 즉, 악성 모듈이나 버그 있는 드라이버는 전체 시스템을 무너뜨릴 수 있습니다. 그래서 Linux 커널 모듈은 서명 검증, SecureBoot 같은 보안 계층을 추가로 둡니다.

### Windows NT — 하이브리드의 실례

Windows NT는 **Executive**라 불리는 커널 상위 계층과 **Microkernel**이라 불리는 하위 계층으로 나뉩니다. 하지만 "Microkernel"이라는 이름과 달리 실제로는 드라이버, 파일 시스템, 네트워크 스택이 모두 커널 공간에서 실행됩니다.

Windows NT의 계층:

<div class="nt-container">
<svg viewBox="0 0 860 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Windows NT 계층 구조">
  <text x="430" y="24" text-anchor="middle" class="nt-title">Windows NT 계층 구조</text>

  <rect x="40" y="44" width="780" height="70" rx="4" class="nt-user"/>
  <text x="60" y="68" class="nt-layer">User Mode</text>
  <text x="60" y="92" class="nt-sub">Win32 앱 · POSIX 서브시스템 · .NET</text>

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
  <text x="60" y="406" class="nt-sub">CPU · 메모리 · 디스크 · 네트워크 카드</text>
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

**특이한 점**: Windows NT는 초기에 **POSIX 서브시스템**과 **OS/2 서브시스템**을 가졌습니다. 이론적으로 POSIX 프로그램이 Windows에서 수정 없이 돌 수 있었습니다. 하지만 실용성이 낮아 POSIX 서브시스템은 Windows 8에서 제거됐고, 대신 **WSL (Windows Subsystem for Linux)**이 완전히 다른 방식(Linux 커널 자체를 돌리는 VM)으로 구현됐습니다.

### XNU — Mach + BSD의 이중 구조

macOS의 커널은 **XNU**라 불립니다 ("X is Not Unix"). XNU는 두 레이어로 구성됩니다:

1. **Mach 3.0 microkernel** (하위): Carnegie Mellon 연구에서 온 것. 태스크, 스레드, 메시지 전달(Mach port), 가상 메모리 담당
2. **BSD layer** (상위): FreeBSD에서 포팅된 Unix 구현. 프로세스 모델(POSIX), 네트워크 스택, 파일 시스템(HFS+/APFS)
3. **I/O Kit**: 드라이버 프레임워크 (C++로 작성)

**왜 이렇게 이상한 구조인가?**

원래 NeXTSTEP은 "순수 microkernel = Mach" 위에 "서버 프로세스로서의 BSD"를 얹는 구조를 시도했습니다. 그런데 이 방식은 **너무 느렸습니다**. 파일을 읽는 것조차 유저 공간의 BSD 서버와 Mach 커널 사이의 IPC를 여러 번 거쳐야 했기 때문입니다.

그래서 타협했습니다: **BSD 코드를 Mach와 같은 커널 공간에 이식**. "Microkernel"이라는 건축 철학은 깨졌지만, 성능이 확보됐습니다. 이것이 지금의 XNU입니다 — **이론상 microkernel이지만 실제로는 하이브리드**.

<div class="os-kernel-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three kernel architectures">
  <text x="450" y="28" text-anchor="middle" class="ok-title">세 커널 구조 비교</text>

  <g class="ok-box">
    <rect x="30" y="60" width="270" height="320" rx="8"/>
    <text x="165" y="82" text-anchor="middle" class="ok-heading">Linux 모놀리식</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="50" y="100" width="230" height="50" rx="4"/>
    <text x="165" y="130" text-anchor="middle">유저 공간</text>
  </g>
  <g class="ok-layer ok-layer-kernel">
    <rect x="50" y="160" width="230" height="180" rx="4"/>
    <text x="165" y="185" text-anchor="middle">커널 공간 (하나의 거대한 프로그램)</text>
    <text x="165" y="215" text-anchor="middle" class="ok-sublabel">파일 시스템</text>
    <text x="165" y="235" text-anchor="middle" class="ok-sublabel">네트워크 스택</text>
    <text x="165" y="255" text-anchor="middle" class="ok-sublabel">드라이버</text>
    <text x="165" y="275" text-anchor="middle" class="ok-sublabel">메모리 관리</text>
    <text x="165" y="295" text-anchor="middle" class="ok-sublabel">스케줄러</text>
    <text x="165" y="315" text-anchor="middle" class="ok-sublabel">IPC</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="50" y="350" width="230" height="20" rx="4"/>
    <text x="165" y="365" text-anchor="middle">하드웨어</text>
  </g>

  <g class="ok-box">
    <rect x="315" y="60" width="270" height="320" rx="8"/>
    <text x="450" y="82" text-anchor="middle" class="ok-heading">Windows NT 하이브리드</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="335" y="100" width="230" height="50" rx="4"/>
    <text x="450" y="130" text-anchor="middle">유저 공간 (Win32, .NET)</text>
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
    <text x="450" y="295" text-anchor="middle" class="ok-sublabel">스케줄러, 인터럽트</text>
  </g>
  <g class="ok-layer ok-layer-hal">
    <rect x="335" y="320" width="230" height="30" rx="4"/>
    <text x="450" y="340" text-anchor="middle">HAL</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="335" y="355" width="230" height="20" rx="4"/>
    <text x="450" y="370" text-anchor="middle">하드웨어</text>
  </g>

  <g class="ok-box">
    <rect x="600" y="60" width="270" height="320" rx="8"/>
    <text x="735" y="82" text-anchor="middle" class="ok-heading">macOS XNU (Mach+BSD)</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="620" y="100" width="230" height="50" rx="4"/>
    <text x="735" y="130" text-anchor="middle">유저 공간 (Cocoa, UIKit)</text>
  </g>
  <g class="ok-layer ok-layer-bsd">
    <rect x="620" y="160" width="230" height="70" rx="4"/>
    <text x="735" y="185" text-anchor="middle">BSD Layer</text>
    <text x="735" y="205" text-anchor="middle" class="ok-sublabel">POSIX, 네트워크, 파일 시스템</text>
    <text x="735" y="220" text-anchor="middle" class="ok-sublabel">프로세스 모델</text>
  </g>
  <g class="ok-layer ok-layer-mach">
    <rect x="620" y="240" width="230" height="70" rx="4"/>
    <text x="735" y="265" text-anchor="middle">Mach Microkernel</text>
    <text x="735" y="285" text-anchor="middle" class="ok-sublabel">Task, Thread, Mach Port</text>
    <text x="735" y="300" text-anchor="middle" class="ok-sublabel">VM, 스케줄러</text>
  </g>
  <g class="ok-layer ok-layer-iokit">
    <rect x="620" y="320" width="230" height="30" rx="4"/>
    <text x="735" y="340" text-anchor="middle">I/O Kit (드라이버 C++)</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="620" y="355" width="230" height="20" rx="4"/>
    <text x="735" y="370" text-anchor="middle">하드웨어</text>
  </g>

  <text x="450" y="405" text-anchor="middle" class="ok-caption">세 구조 모두 유저/커널 경계는 같지만, 커널 내부의 분할 방식이 다르다.</text>
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

> ### 잠깐, 이건 짚고 넘어가자
>
> **"Microkernel이 이론적으로 좋다면서 왜 아무도 순수 microkernel을 안 쓰는가?"**
>
> 답은 **IPC 비용**입니다. Microkernel에서는 파일을 읽으려면 다음과 같이 진행됩니다:
>
> 1. 앱이 "파일 읽어줘" 메시지를 커널에 보냄
> 2. 커널이 그 메시지를 파일 시스템 서버 프로세스에 전달
> 3. 파일 시스템 서버가 디스크 드라이버 서버에 메시지를 보냄
> 4. 디스크 드라이버가 실제로 디스크를 읽고 결과를 파일 시스템 서버에 돌려보냄
> 5. 파일 시스템 서버가 앱에 결과를 돌려보냄
>
> 각 단계마다 **컨텍스트 스위치 + 메시지 복사**가 발생합니다. 1980~90년대 하드웨어에서는 이 비용이 감당 안 될 정도였습니다.
>
> 모놀리식 커널에서는 같은 작업이 **함수 호출 한 번**으로 끝납니다.
>
> 그래서 대부분의 실용 OS는 **"microkernel 설계 사상은 받아들이되, 성능을 위해 타협"**하는 하이브리드로 수렴했습니다. 순수 microkernel은 실시간 시스템(QNX), 보안 중요 시스템(seL4 — 수학적으로 검증된 커널)처럼 **특수 분야**에서만 살아남았습니다.

---

## Part 4: 실행 바이너리 포맷 — 같은 C 코드, 다른 결과물

여러분이 C++로 작성된 Unity 게임을 빌드하면 세 OS에서 다른 바이너리가 나옵니다:

- Linux: **ELF (Executable and Linkable Format)**
- Windows: **PE / PE32+ (Portable Executable)**
- macOS: **Mach-O**

이 포맷들은 **완전히 다릅니다**. 단순한 확장자 차이가 아니라 파일 내부 구조가 다르기 때문에, 한 OS의 바이너리를 다른 OS에서 실행할 수 없습니다 (에뮬레이터를 쓰지 않는 한).

### ELF — Linux의 표준 (1988~)

**Executable and Linkable Format**은 System V에서 도입된 포맷으로, 지금은 대부분의 Unix 계열(Linux, FreeBSD, Solaris)이 씁니다.

<div class="oe-elf-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELF file layout">
  <text x="450" y="28" text-anchor="middle" class="oe-title">ELF 파일 레이아웃 — Linking View vs Execution View</text>

  <text x="180" y="60" text-anchor="middle" class="oe-heading">Linking View (섹션)</text>
  <text x="180" y="78" text-anchor="middle" class="oe-sub">링커 / 컴파일러가 사용</text>

  <text x="720" y="60" text-anchor="middle" class="oe-heading">Execution View (세그먼트)</text>
  <text x="720" y="78" text-anchor="middle" class="oe-sub">런타임에 로더가 사용</text>

  <g class="oe-left">
    <rect x="60" y="95" width="240" height="30" rx="3" class="oe-sect oe-sect-header"/>
    <text x="180" y="115" text-anchor="middle" class="oe-sect-label">ELF Header</text>
    <rect x="60" y="130" width="240" height="30" rx="3" class="oe-sect oe-sect-prog"/>
    <text x="180" y="150" text-anchor="middle" class="oe-sect-label">Program Header Table</text>
    <rect x="60" y="170" width="240" height="30" rx="3" class="oe-sect oe-sect-text"/>
    <text x="180" y="190" text-anchor="middle" class="oe-sect-label">.text (실행 코드)</text>
    <rect x="60" y="205" width="240" height="30" rx="3" class="oe-sect oe-sect-ro"/>
    <text x="180" y="225" text-anchor="middle" class="oe-sect-label">.rodata (상수 / 문자열)</text>
    <rect x="60" y="245" width="240" height="30" rx="3" class="oe-sect oe-sect-data"/>
    <text x="180" y="265" text-anchor="middle" class="oe-sect-label">.data (초기화 전역)</text>
    <rect x="60" y="280" width="240" height="30" rx="3" class="oe-sect oe-sect-bss"/>
    <text x="180" y="300" text-anchor="middle" class="oe-sect-label">.bss (0 초기화, 크기만)</text>
    <rect x="60" y="320" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="337" text-anchor="middle" class="oe-sect-label-sm">.symtab (심볼 테이블)</text>
    <rect x="60" y="350" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="367" text-anchor="middle" class="oe-sect-label-sm">.strtab (문자열 테이블)</text>
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
    <text x="720" y="345" text-anchor="middle" class="oe-seg-label">(로드되지 않음)</text>
    <text x="720" y="362" text-anchor="middle" class="oe-seg-sub">심볼 테이블, 디버그 정보</text>
    <text x="720" y="378" text-anchor="middle" class="oe-seg-sub">프로덕션 빌드에서는 strip</text>
    <text x="720" y="395" text-anchor="middle" class="oe-seg-sub">또는 디버깅용 보존</text>
    <rect x="600" y="410" width="240" height="30" rx="3" class="oe-seg oe-seg-meta"/>
    <text x="720" y="430" text-anchor="middle" class="oe-seg-label-sm">Section Header Table (런타임엔 선택적)</text>
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

  <text x="450" y="480" text-anchor="middle" class="oe-note">같은 파일이지만 링커는 섹션 단위로, 로더는 세그먼트(권한) 단위로 본다.</text>
  <text x="450" y="500" text-anchor="middle" class="oe-note">프로덕션 바이너리는 Section Header Table을 생략하고 .symtab / .debug_*을 strip해 크기를 줄일 수 있다.</text>
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

ELF 파일의 구조:

<div class="bf-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELF 파일 구조">
  <text x="450" y="30" text-anchor="middle" class="bf-title">ELF 파일 구조 (Linux)</text>

  <rect x="160" y="56" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="77" text-anchor="middle" class="bf-label">ELF Header</text>
  <text x="480" y="77" class="bf-note">매직 넘버 0x7f 'E' 'L' 'F'</text>

  <rect x="160" y="102" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="123" text-anchor="middle" class="bf-label">Program Header Table</text>
  <text x="480" y="123" class="bf-note">실행 시 메모리 매핑 정보</text>

  <rect x="160" y="148" width="300" height="258" rx="3" class="bf-group"/>
  <text x="170" y="166" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="176" width="276" height="28" rx="2" class="bf-text"/>
  <text x="310" y="194" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="194" class="bf-note">실행 코드</text>

  <rect x="172" y="208" width="276" height="28" rx="2" class="bf-ro"/>
  <text x="310" y="226" text-anchor="middle" class="bf-sect">.rodata</text>
  <text x="480" y="226" class="bf-note">읽기 전용 데이터 (문자열 리터럴 등)</text>

  <rect x="172" y="240" width="276" height="28" rx="2" class="bf-data"/>
  <text x="310" y="258" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="258" class="bf-note">초기화된 전역 변수</text>

  <rect x="172" y="272" width="276" height="28" rx="2" class="bf-bss"/>
  <text x="310" y="290" text-anchor="middle" class="bf-sect">.bss</text>
  <text x="480" y="290" class="bf-note">0 초기화 전역 변수 (파일엔 크기만 기록)</text>

  <rect x="172" y="304" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="322" text-anchor="middle" class="bf-sect">.symtab</text>
  <text x="480" y="322" class="bf-note">심볼 테이블</text>

  <rect x="172" y="336" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="354" text-anchor="middle" class="bf-sect">.strtab</text>
  <text x="480" y="354" class="bf-note">문자열 테이블</text>

  <rect x="172" y="368" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="386" text-anchor="middle" class="bf-sect">.debug_*</text>
  <text x="480" y="386" class="bf-note">DWARF 디버그 정보</text>

  <rect x="160" y="420" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="441" text-anchor="middle" class="bf-label">Section Header Table</text>
  <text x="480" y="441" class="bf-note">섹션 위치 / 속성 정보</text>
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

ELF 확인:

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

### PE — Windows의 계보 (1993~)

**Portable Executable**은 Windows NT에서 도입된 포맷입니다. Unix의 COFF(Common Object File Format)에서 파생했지만 Microsoft 고유의 확장이 많습니다.

PE 파일의 구조:

<div class="bf-container">
<svg viewBox="0 0 900 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PE 파일 구조">
  <text x="450" y="30" text-anchor="middle" class="bf-title">PE 파일 구조 (Windows)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-dos"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">DOS Header (MZ)</text>
  <text x="480" y="75" class="bf-note">16비트 시절 호환성 유산</text>

  <rect x="160" y="90" width="300" height="30" rx="3" class="bf-stub"/>
  <text x="310" y="109" text-anchor="middle" class="bf-label">DOS Stub</text>
  <text x="480" y="109" class="bf-note">"This program cannot be run in DOS mode"</text>

  <rect x="160" y="124" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="143" text-anchor="middle" class="bf-label">PE Signature "PE\0\0"</text>

  <rect x="160" y="158" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="177" text-anchor="middle" class="bf-label">COFF Header</text>
  <text x="480" y="177" class="bf-note">CPU 아키텍처 · 섹션 수</text>

  <rect x="160" y="192" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="211" text-anchor="middle" class="bf-label">Optional Header</text>
  <text x="480" y="211" class="bf-note">엔트리 포인트 · 이미지 베이스 · 서브시스템</text>

  <rect x="160" y="226" width="300" height="30" rx="3" class="bf-aux"/>
  <text x="310" y="245" text-anchor="middle" class="bf-label">Section Headers</text>

  <rect x="160" y="266" width="300" height="174" rx="3" class="bf-group"/>
  <text x="170" y="284" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="292" width="276" height="26" rx="2" class="bf-text"/>
  <text x="310" y="309" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="309" class="bf-note">실행 코드</text>

  <rect x="172" y="322" width="276" height="26" rx="2" class="bf-ro"/>
  <text x="310" y="339" text-anchor="middle" class="bf-sect">.rdata</text>
  <text x="480" y="339" class="bf-note">읽기 전용 데이터 · 임포트 테이블</text>

  <rect x="172" y="352" width="276" height="26" rx="2" class="bf-data"/>
  <text x="310" y="369" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="369" class="bf-note">초기화된 전역 변수</text>

  <rect x="172" y="382" width="276" height="26" rx="2" class="bf-rsrc"/>
  <text x="310" y="399" text-anchor="middle" class="bf-sect">.rsrc</text>
  <text x="480" y="399" class="bf-note">아이콘 · 버전 정보 등 리소스</text>

  <rect x="172" y="412" width="276" height="26" rx="2" class="bf-reloc"/>
  <text x="310" y="429" text-anchor="middle" class="bf-sect">.reloc</text>
  <text x="480" y="429" class="bf-note">재배치 정보</text>
</svg>
</div>

재미있는 점: PE 파일 맨 앞에는 여전히 **DOS 호환용 "MZ" 매직 넘버**가 있습니다 (MZ는 DOS의 개발자 Mark Zbikowski의 이니셜). 1993년에 설계된 포맷이 **1981년 DOS 호환성 문자열을 지금도 들고 있습니다**. 이게 Windows의 하위 호환성 문화를 보여주는 대표 사례입니다.

### Mach-O — macOS의 포맷

**Mach-O (Mach Object)**는 Mach 커널과 함께 설계된 포맷입니다. NeXTSTEP에서 시작해 지금도 macOS/iOS가 씁니다.

Mach-O 파일의 구조:

<div class="bf-container">
<svg viewBox="0 0 900 490" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mach-O 파일 구조">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Mach-O 파일 구조 (macOS / iOS)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">Header</text>
  <text x="480" y="75" class="bf-note">매직 0xFEEDFACE (32) / 0xFEEDFACF (64)</text>

  <rect x="160" y="98" width="300" height="134" rx="3" class="bf-meta"/>
  <text x="310" y="116" text-anchor="middle" class="bf-label">Load Commands</text>
  <text x="480" y="116" class="bf-note">로더에게 주는 지시</text>
  <text x="176" y="140" class="bf-sub">LC_SEGMENT</text>
  <text x="306" y="140" class="bf-sub">메모리 세그먼트 정의</text>
  <text x="176" y="160" class="bf-sub">LC_DYLD_INFO</text>
  <text x="306" y="160" class="bf-sub">동적 링커 정보</text>
  <text x="176" y="180" class="bf-sub">LC_SYMTAB</text>
  <text x="306" y="180" class="bf-sub">심볼 테이블</text>
  <text x="176" y="200" class="bf-sub">LC_LOAD_DYLIB</text>
  <text x="306" y="200" class="bf-sub">필요한 라이브러리</text>
  <text x="176" y="220" class="bf-sub">LC_CODE_SIGNATURE</text>
  <text x="306" y="220" class="bf-sub">코드 서명</text>

  <rect x="160" y="244" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="262" class="bf-group-label">SEGMENT · __TEXT</text>
  <rect x="172" y="272" width="276" height="24" rx="2" class="bf-text"/>
  <text x="310" y="289" text-anchor="middle" class="bf-sect">__text</text>
  <text x="480" y="289" class="bf-note">실행 코드</text>
  <rect x="172" y="300" width="276" height="24" rx="2" class="bf-ro"/>
  <text x="310" y="317" text-anchor="middle" class="bf-sect">__cstring</text>
  <text x="480" y="317" class="bf-note">C 문자열 상수</text>

  <rect x="160" y="340" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="358" class="bf-group-label">SEGMENT · __DATA</text>
  <rect x="172" y="368" width="276" height="24" rx="2" class="bf-data"/>
  <text x="310" y="385" text-anchor="middle" class="bf-sect">__data</text>
  <text x="480" y="385" class="bf-note">초기화된 전역 변수</text>
  <rect x="172" y="396" width="276" height="24" rx="2" class="bf-bss"/>
  <text x="310" y="413" text-anchor="middle" class="bf-sect">__bss</text>
  <text x="480" y="413" class="bf-note">0 초기화 전역 변수</text>

  <rect x="160" y="436" width="300" height="30" rx="3" class="bf-linkedit"/>
  <text x="310" y="455" text-anchor="middle" class="bf-label">Segment: __LINKEDIT</text>
  <text x="480" y="455" class="bf-note">심볼 · 재배치 · 서명</text>
</svg>
</div>

**Universal Binary (Fat Binary)**: 하나의 파일에 여러 아키텍처의 Mach-O를 모두 담을 수 있습니다.

<div class="bf-container">
<svg viewBox="0 0 900 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Universal Binary (Fat Binary) 구조">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Universal Binary (Fat Binary)</text>

  <rect x="160" y="50" width="300" height="32" rx="3" class="bf-meta"/>
  <text x="310" y="71" text-anchor="middle" class="bf-label">Fat Header</text>
  <text x="480" y="71" class="bf-note">내장된 아키텍처 목록 · 각 오프셋</text>

  <rect x="160" y="90" width="300" height="46" rx="3" class="bf-arch-x86"/>
  <text x="310" y="110" text-anchor="middle" class="bf-label">Arch 0: x86_64</text>
  <text x="310" y="128" text-anchor="middle" class="bf-sub">(완전한 Mach-O)</text>
  <text x="480" y="119" class="bf-note">Intel Mac용</text>

  <rect x="160" y="144" width="300" height="46" rx="3" class="bf-arch-arm"/>
  <text x="310" y="164" text-anchor="middle" class="bf-label">Arch 1: arm64</text>
  <text x="310" y="182" text-anchor="middle" class="bf-sub">(완전한 Mach-O)</text>
  <text x="480" y="173" class="bf-note">Apple Silicon용</text>
</svg>
</div>

이것이 **"동일한 앱이 Intel Mac과 M1 Mac 양쪽에서 네이티브로 돌아가는"** 구조입니다. 2006년 PowerPC→Intel 전환 때도, 2020년 Intel→Apple Silicon 전환 때도 같은 방식으로 이식이 이뤄졌습니다.

### 멀티플랫폼 빌드에서의 의미

Unity, Unreal 같은 엔진이 "한 번 만들면 여러 플랫폼에서 돈다"고 광고하지만, 실제로는 **엔진이 내부적으로 세 포맷에 맞춰 다시 빌드**합니다. 여러분이 Build Settings에서 플랫폼을 바꿀 때 엔진이 하는 일:

- **Windows**: MSVC 또는 clang-cl로 컴파일 → PE32+ 생성, Windows SDK 링크
- **macOS**: clang/xcode 툴체인 → Mach-O 생성, Cocoa 프레임워크 링크 (Universal Binary로 Intel+ARM 동시)
- **Linux**: gcc 또는 clang → ELF 생성, glibc 링크

같은 C++ 코드여도 **최종 바이너리는 전혀 다른 파일**입니다. 그래서 Windows에서 빌드한 `.exe`를 macOS로 가져다 둬도 안 돕니다.

**또 하나의 함정**: 게임 엔진은 동적 라이브러리를 많이 씁니다.

- Windows: `.dll`
- macOS: `.dylib` 또는 `.framework` (번들 형태)
- Linux: `.so`

각 플랫폼별로 **전부 따로 빌드**해야 합니다. Unity 네이티브 플러그인이 Windows만 지원하는 경우가 흔한 이유입니다.

---

## Part 5: macOS 특화 이야기 — Apple이 쌓아 올린 것들

이제 Mac 유저에게 특히 재미있을 섹션입니다. macOS가 다른 OS와 구별되는 **Apple 고유의 시스템**들을 깊이 살펴봅니다.

### XNU 탄생의 뒷이야기

앞서 XNU가 Mach + BSD의 이중 구조라고 했지만, 그 과정에는 **실패와 타협의 역사**가 있습니다.

**1단계 (1985~88) — 순수 Mach의 꿈**
Carnegie Mellon University의 Mach 프로젝트는 *"BSD Unix 기능을 microkernel로 재구현"*하는 학술 실험이었습니다. Rashid 교수와 학생들이 Mach 2.0을 내놓았는데, 이것은 "Mach + BSD 서버"가 한 커널에 섞인 **혼합 구조**였습니다.

**2단계 (1990) — Mach 3.0의 시도**
Mach 3.0은 순수 microkernel을 지향해 BSD 코드를 완전히 **유저 공간 서버**로 분리했습니다. 이론적으로 완벽했지만 성능이 끔찍했습니다. OSF/1이라는 상업 OS가 Mach 3.0으로 나왔지만 시장에서 실패했습니다.

**3단계 (1989~96) — NeXTSTEP의 실용적 선택**
NeXT는 처음에 Mach 2.0을 기반으로 NeXTSTEP을 만들었습니다. 일부 BSD 기능을 Mach 커널에 직접 병합해 성능을 확보. 이것이 NeXTSTEP의 커널 기반입니다.

**4단계 (2000~) — XNU**
Apple이 NeXTSTEP을 가져와 macOS로 만들 때, BSD 쪽을 **FreeBSD 5.x**에서 대대적으로 업데이트해 가져왔습니다. 이 결과가 XNU. 그래서 macOS에서 `uname -a`를 치면 "Darwin"이 나오는데, **Darwin = XNU + BSD 유저랜드 = macOS의 오픈소스 부분**입니다.

```bash
$ uname -a
Darwin MacBook.local 23.0.0 Darwin Kernel Version 23.0.0: ...
```

Apple은 Darwin을 오픈소스로 공개합니다. 여러분도 [opensource.apple.com](https://opensource.apple.com)에서 XNU 소스를 받아 빌드할 수 있습니다.

### Mach port — 모든 것의 뿌리

Mach microkernel의 핵심 추상화는 **port (포트)**입니다. Mach port는 Unix의 file descriptor와 비슷한 역할이지만, 훨씬 광범위합니다.

- **프로세스 간 통신**: 메시지를 port로 주고받음
- **신호 처리**: Unix 시그널이 Mach port 메시지로 변환됨
- **IOKit 드라이버**: 사용자 공간 앱이 드라이버와 port로 통신
- **Bootstrap**: 이름 서비스(`launchd`가 제공)도 port 기반

**왜 중요한가?** macOS의 보안 모델과 IPC가 전부 port 위에 세워져 있습니다. 예를 들어 앱 샌드박스는 "이 앱은 이 특정 port만 쓸 수 있다"로 구현됩니다. iOS의 엄격한 앱 격리도 근본적으로 Mach port 기반입니다.

```c
/* Mach port로 메시지 보내기 (극단 단순화) */
mach_port_t target_port = ...;
mach_msg_send(&msg_header);
```

개발자가 직접 쓸 일은 거의 없지만, 디버거(lldb)나 Xcode Instruments 같은 도구의 내부에서 동작합니다.

### Grand Central Dispatch (2009)

**2009년 macOS 10.6 Snow Leopard**에서 Apple은 Grand Central Dispatch (GCD, libdispatch)를 도입했습니다. 이것은 멀티코어 시대에 대한 Apple의 답변이었습니다.

**기존 스레드 모델의 문제**:
```c
/* 전통적 C/Unix 스타일 */
pthread_t thread;
pthread_create(&thread, NULL, worker_function, arg);
pthread_join(thread, NULL);
```
- 개발자가 스레드 개수, 수명, 동기화를 직접 관리
- CPU 코어 수를 모르면 과도하거나 부족하게 만듦
- 동기화 프리미티브 사용에 실수가 많음

**GCD의 해결책**: 스레드 대신 **큐**에 작업을 던진다.

```swift
/* Swift */
DispatchQueue.global(qos: .userInitiated).async {
    /* 여기 있는 작업이 백그라운드에서 실행됨 */
    let result = heavyComputation()
    DispatchQueue.main.async {
        updateUI(result)
    }
}
```

OS가 CPU 코어 수, 시스템 부하 등을 고려해 스레드를 **자동으로** 생성/재사용합니다. 개발자는 "어떤 우선순위로 실행할까"만 지정합니다 (QoS: User Interactive, User Initiated, Utility, Background).

**GCD는 오픈소스 libdispatch로 공개**됐고, Swift on Linux에서도 사용됩니다. 즉, 다른 언어나 플랫폼에서도 GCD 스타일 프로그래밍이 가능합니다.

**게임 개발 시각에서**: Unity Job System은 GCD와 사상이 매우 비슷합니다 — "스레드가 아닌 작업을 스케줄러에 맡긴다". Part 13에서 자세히 다룹니다.

### launchd — systemd보다 먼저

2005년 macOS 10.4 Tiger에서 Apple은 **launchd**를 도입했습니다. 이것은 Unix의 전통적 init 시스템(SysVinit, cron, xinetd, inetd, atd 등 여러 데몬의 분산된 역할)을 **하나의 프로세스로 통합**한 것입니다.

launchd 이전의 Unix:
- `init` (PID 1): 부팅 시스템 초기화
- `cron`: 주기적 작업
- `atd`: 일회성 예약 작업
- `inetd`: 네트워크 요청 시 데몬 시작
- 각 데몬이 별도로 실행

launchd는 이걸 전부 합친 **만능 데몬 관리자**입니다:
- PID 1로 실행, 시스템 전체 프로세스 관리
- XML 기반 plist 파일로 서비스 정의
- 파일 접근, 네트워크 연결 등 **온디맨드 실행** 지원
- 실패 시 자동 재시작

**역사적 의미**: Linux의 **systemd** (2010년 Lennart Poettering)가 launchd에서 영감을 받았습니다. systemd가 도입됐을 때 Linux 커뮤니티에서 "Unix 철학에 어긋난다"는 비판이 컸는데, 이미 launchd가 5년 먼저 같은 접근을 했고 macOS에서 별 문제 없이 돌고 있었습니다.

`launchctl` 명령으로 관리:

```bash
# 실행 중인 서비스 목록
launchctl list

# 특정 서비스 시작
launchctl load ~/Library/LaunchAgents/com.example.myservice.plist

# 중지
launchctl unload ~/Library/LaunchAgents/com.example.myservice.plist
```

### Apple Silicon — P/E 코어의 이질 구조

2020년 Apple은 자체 설계 CPU **M1 (Apple Silicon)**을 Mac에 도입했습니다. M1은 ARM64 기반이지만 **일반 ARM 서버와 다른 독특한 구조**를 가집니다.

**P-코어 (Performance)와 E-코어 (Efficiency)**

M1은 동일한 ARM ISA를 실행하는 **두 종류의 코어**를 가집니다:

- **P-코어 "Firestorm"**: 고성능, 고전력. 게임, 컴파일, 렌더링 등 무거운 작업
- **E-코어 "Icestorm"**: 저성능, 저전력. 백그라운드 작업, 시스템 데몬, 배터리 절약

| 스펙 | P-코어 | E-코어 |
|------|--------|--------|
| 클럭 | 3.2 GHz | 2.0 GHz |
| L1 캐시 | 192KB | 128KB |
| L2 캐시 | 공유 12MB | 공유 4MB |
| 전력 | ~15W | ~1W |
| 성능 비율 | ~100% | ~25% |
| M1 구성 | 4개 | 4개 |

**macOS의 QoS 기반 스케줄링**: 앞서 본 GCD의 QoS 클래스가 여기서 다시 등장합니다.

- **User Interactive / User Initiated** QoS → 주로 P-코어
- **Utility** QoS → 상황에 따라
- **Background** QoS → 주로 E-코어

개발자가 `DispatchQueue.global(qos: .userInitiated)`라고만 쓰면 OS가 **어떤 코어에서 실행할지 결정**합니다. 이것이 Apple의 "개발자가 하드웨어 세부를 몰라도 되는" 철학입니다.

**16KB 페이지 크기**

Apple Silicon의 또 다른 특이점은 **페이지 크기가 16KB**라는 것입니다. Linux/Windows 표준은 **4KB**.

- **장점**: TLB(Translation Lookaside Buffer) miss가 줄어들고, 큰 메모리 앱의 성능이 향상됨
- **단점**: 메모리 정렬 요구사항 변경. 4KB 페이지를 가정한 구형 앱이 깨질 수 있음

2020년 Apple Silicon 전환 초기에 **Homebrew, Docker, 일부 바이너리 호환성 툴**이 16KB 페이지 문제로 고생했습니다. 지금은 대부분 해결됐지만, Unity 네이티브 플러그인 개발 시 `mprotect()` 호출 같은 것에서 페이지 정렬에 주의해야 합니다.

### Rosetta 2 — 에뮬레이터가 아니라 번역기

Apple Silicon 전환의 성공 요인 중 하나는 **Rosetta 2**입니다. 이것은 x86_64 Mach-O 바이너리를 ARM64에서 실행합니다. 놀라운 점: **네이티브 성능의 70~80%**가 나옵니다.

**Rosetta 2는 JIT 에뮬레이터가 아닙니다**. 앱을 설치할 때(또는 첫 실행 시) x86 명령을 ARM으로 **AOT(Ahead-of-Time) 번역**해서 파일로 저장합니다. 이후 실행은 이미 번역된 ARM 바이너리를 돌리는 것이라 빠릅니다.

**결정적 트릭 — 하드웨어 TSO 모드**: 이 부분이 가장 흥미롭습니다.

x86은 **강한 메모리 모델 (TSO, Total Store Order)**을 갖습니다. 한 CPU가 쓴 값이 다른 CPU에 보이는 순서가 프로그래밍 순서와 거의 같습니다.

ARM은 **약한 메모리 모델**을 갖습니다. CPU가 성능을 위해 메모리 쓰기/읽기 순서를 **마음대로 재배치**할 수 있습니다. 프로그래머가 명시적으로 메모리 배리어를 넣어야 순서가 보장됩니다.

문제는 **x86용으로 작성된 프로그램**이 TSO를 암묵적으로 가정할 때 생깁니다. 이런 프로그램을 단순히 ARM 명령으로 번역하면, ARM의 재배치 때문에 **race condition이 새로 생깁니다**.

Apple의 해결: **M1 CPU에 "TSO 모드" 하드웨어를 넣었습니다**. Rosetta 2가 번역한 바이너리가 실행될 때, CPU에 "이 스레드는 TSO 모드로 돌려"라는 플래그를 세웁니다. 그러면 ARM CPU가 **x86과 같은 강한 메모리 순서**로 동작합니다.

> 💡 이 주제는 Part 12 (메모리 모델과 원자 연산)에서 다시 등장합니다. 지금은 "Apple이 하드웨어 레벨에서 호환성 트릭을 썼다"는 점만 기억하면 됩니다.

**Rosetta 2의 한계**:
- AVX-512 같은 최신 x86 확장 명령은 번역 안 됨
- 커널 확장(.kext)은 Rosetta로 못 돌림 — OS 자체는 네이티브여야 함
- JIT 컴파일러가 내장된 프로그램(크롬 V8 엔진 등)은 Rosetta + JIT의 이중 번역이라 느릴 수 있음

### XNU 내부 구조

<div class="os-xnu-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="XNU kernel internals">
  <text x="450" y="28" text-anchor="middle" class="xu-title">XNU 커널 내부 — Mach + BSD + I/O Kit</text>

  <g class="xu-user">
    <rect x="60" y="60" width="780" height="70" rx="8"/>
    <text x="450" y="88" text-anchor="middle" class="xu-heading">유저 공간 (User Space)</text>
    <text x="210" y="112" text-anchor="middle" class="xu-sub">Cocoa / UIKit</text>
    <text x="380" y="112" text-anchor="middle" class="xu-sub">Swift / Objective-C</text>
    <text x="550" y="112" text-anchor="middle" class="xu-sub">POSIX 앱 (bash, ls)</text>
    <text x="730" y="112" text-anchor="middle" class="xu-sub">시스템 데몬 (launchd)</text>
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
    <text x="180" y="225" text-anchor="middle" class="xu-sub">프로세스 모델 (POSIX)</text>
    <text x="380" y="225" text-anchor="middle" class="xu-sub">파일 시스템 (APFS/HFS+)</text>
    <text x="560" y="225" text-anchor="middle" class="xu-sub">네트워크 (BSD sockets)</text>
    <text x="730" y="225" text-anchor="middle" class="xu-sub">시그널, 권한</text>
    <text x="450" y="245" text-anchor="middle" class="xu-note">"우리가 보는 Unix의 얼굴"</text>
  </g>

  <g class="xu-mach">
    <rect x="60" y="270" width="780" height="90" rx="8"/>
    <text x="450" y="295" text-anchor="middle" class="xu-heading">Mach Microkernel</text>
    <text x="200" y="320" text-anchor="middle" class="xu-sub">Task (프로세스)</text>
    <text x="380" y="320" text-anchor="middle" class="xu-sub">Thread (스레드)</text>
    <text x="560" y="320" text-anchor="middle" class="xu-sub">Mach Port (IPC)</text>
    <text x="730" y="320" text-anchor="middle" class="xu-sub">VM, 스케줄러</text>
    <text x="450" y="345" text-anchor="middle" class="xu-note">"CMU 1985~91년 연구의 산물"</text>
  </g>

  <g class="xu-iokit">
    <rect x="60" y="375" width="780" height="50" rx="8"/>
    <text x="450" y="395" text-anchor="middle" class="xu-heading">I/O Kit (C++로 작성된 드라이버 프레임워크)</text>
    <text x="450" y="415" text-anchor="middle" class="xu-sub">GPU, USB, 센서, 전원 관리</text>
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

### Apple Silicon 이질 코어 구조

<div class="os-silicon-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Apple Silicon heterogeneous cores">
  <text x="450" y="28" text-anchor="middle" class="si-title">Apple Silicon M1 — P/E 코어와 QoS 매핑</text>

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
    <text x="450" y="252" text-anchor="middle" class="si-uma-label">Unified Memory (16KB 페이지)</text>
    <text x="450" y="275" text-anchor="middle" class="si-uma-sub">CPU, GPU, Neural Engine이 같은 메모리 풀 공유</text>
  </g>

  <g class="si-qos">
    <rect x="60" y="340" width="780" height="80" rx="8"/>
    <text x="450" y="362" text-anchor="middle" class="si-qos-title">macOS QoS → 코어 매핑</text>
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

> ### 잠깐, 이건 짚고 넘어가자
>
> **"Rosetta 2가 왜 빠른가? 에뮬레이터라며 네이티브 성능의 70%가 말이 되는가?"**
>
> 세 가지 이유가 겹쳐서 그렇습니다.
>
> 1. **AOT 번역 (사전 번역)**: 에뮬레이터가 아닙니다. 앱을 설치하거나 처음 실행할 때 x86 바이너리를 ARM으로 **완전히 번역해 캐시**합니다. 그 뒤로는 네이티브 ARM을 실행할 뿐입니다.
> 2. **M1이 애초에 x86보다 훨씬 빠름**: M1의 싱글 코어 성능이 같은 세대 Intel CPU보다 우수합니다. 70%로 떨어져도 절대 성능은 나쁘지 않습니다.
> 3. **하드웨어 TSO 모드**: x86의 메모리 모델을 ARM에 강제하기 위한 소프트웨어 에뮬레이션은 비쌉니다. Apple은 이걸 **하드웨어에 넣어** 공짜로 만들었습니다.
>
> **한계**: 하드웨어 TSO 모드는 x86 바이너리가 실행될 때만 켜집니다. 네이티브 ARM 앱은 약한 메모리 모델을 그대로 씁니다.

---

## Part 6: 세 OS 장단점 표

이제까지의 내용을 한 표로 정리합니다. 각 OS의 강점과 약점을 객관적으로 나열했습니다.

### 개발자 관점 종합 비교

| 영역 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **커널 소스 접근** | ✅ 완전 공개 | ❌ 비공개 | 🟡 Darwin만 공개 (GUI/Cocoa 비공개) |
| **CLI 생태계** | ✅ 최고 (bash, coreutils 네이티브) | 🟡 PowerShell 훌륭, WSL 필요 | ✅ Unix 표준 도구 기본 탑재 |
| **패키지 관리** | ✅ apt/dnf/pacman | 🟡 winget/choco (후발) | 🟡 Homebrew (비공식) |
| **가상화/컨테이너** | ✅ Docker 네이티브 | 🟡 WSL 2 / Hyper-V | 🟡 Docker Desktop (VM 경유) |
| **언어 지원** | ✅ 모든 언어 | ✅ 모든 언어 (특히 .NET) | ✅ 모든 언어 (Swift가 1급) |
| **IDE** | 🟡 VS Code, CLion | ✅ Visual Studio 최고 | ✅ Xcode, JetBrains |
| **문서화** | 🟡 분산됨, man 페이지 | ✅ MSDN 체계적 | ✅ Apple Developer 문서 |
| **커뮤니티** | ✅ 거대, 개방적 | 🟡 엔터프라이즈 중심 | 🟡 Apple 생태계 중심 |

### 게임 개발 관점

| 영역 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **주요 그래픽 API** | Vulkan, OpenGL | DirectX 11/12, Vulkan | Metal (OpenGL/Vulkan 지원 종료 중) |
| **게임 엔진 지원** | 🟡 Unity/Unreal 빌드 타겟으로만 | ✅ 최고 (에디터 포함) | 🟡 Unity/Unreal 에디터 지원 개선 중 |
| **오디오 API** | ALSA, PulseAudio, PipeWire | XAudio2, WASAPI | Core Audio |
| **디버거/프로파일러** | 🟡 GDB, Valgrind | ✅ Visual Studio | ✅ Instruments, Xcode |
| **스팀 게임 플레이** | 🟡 Proton (개선 중) | ✅ 네이티브 | 🟡 제한적 |
| **VR/AR 지원** | 🟡 SteamVR | ✅ WMR, SteamVR | 🟡 Vision Pro 생태계 |

### 서버 운영 관점

| 영역 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **웹 서버 시장 점유율** | ~75% | ~20% | ~0% (서버용 아님) |
| **컨테이너 네이티브** | ✅ | 🟡 LCOW (리눅스 컨테이너를 WSL로) | ❌ |
| **저자원 운영** | ✅ 최소 수백 MB로 동작 | 🟡 수 GB 필요 | 🟡 서버 용도 거의 없음 |
| **라이선스 비용** | ✅ 무료 | 💰 유료 (Windows Server) | 🟡 Apple 하드웨어 강제 |

### 핵심 결론

- **"가장 좋은 OS"는 없다** — 용도에 따라 다릅니다
- **서버/개발**: Linux가 지배적
- **기업/게임 클라이언트**: Windows가 지배적
- **크리에이티브 작업/일반 개인 개발**: macOS가 강세
- **모든 OS가 서로의 강점을 빌려오는 중**:
  - Windows가 WSL로 Linux 호환
  - macOS가 Homebrew로 Linux 도구 생태계 활용
  - Linux가 데스크톱 UX 개선에 투자

---

## Part 7: 보안과 샌드박스 — 짧게

OS마다 보안 모델이 다릅니다. 게임 개발 관점에서 관련 있는 부분만 간단히.

### macOS — 다층 보안

**SIP (System Integrity Protection)**: 시스템 파일 보호. `/System`, `/bin` 등은 root조차 수정 불가. 2015년 El Capitan에서 도입.

**Gatekeeper**: 서명되지 않은 앱 실행 차단. "Apple에서 신원이 확인되지 않은 개발자" 경고가 이것.

**Notarization (공증)**: Apple에 바이너리를 제출해 악성코드 검증을 받아야 Gatekeeper 경고 없이 실행 가능. 2019년 의무화.

**App Sandbox**: Mac App Store 앱은 의무적으로 샌드박스. 일반 앱은 선택적. 파일 시스템, 네트워크, 카메라 등을 entitlement로 명시.

**Hardened Runtime**: JIT, 라이브러리 주입 등을 차단하는 추가 보안 계층.

개발자 관점: Mac용 상용 앱 배포 시 **Apple Developer 계정($99/년)**으로 서명 + 공증 필수. 게임 배포 시 중요.

### Windows — UAC와 Defender

**UAC (User Account Control)**: 관리자 권한이 필요한 작업에 사용자 확인. Vista 때 도입되며 악평 샀지만 지금은 필수 보안 모델.

**Windows Defender**: 기본 내장 안티바이러스. Windows 10 이후 거의 서드파티 AV가 불필요한 수준.

**Code Signing**: Authenticode 서명. EV 인증서는 SmartScreen 경고 없이 실행. 게임 배포 시 권장.

**AppContainer**: UWP 앱 격리. Mac App Sandbox와 유사한 개념이지만 사용 범위가 좁음.

### Linux — 유연한 도구 모음

**User/Group 권한**: Unix 전통. rwx 비트, UID/GID.

**Capabilities**: root의 권한을 쪼개서 부여 (`CAP_NET_BIND_SERVICE`, `CAP_SYS_ADMIN` 등).

**SELinux / AppArmor**: Mandatory Access Control. 더 세밀한 정책 강제.

**cgroups + namespaces**: Docker의 기반 기술. 프로세스 그룹에 자원 제한과 격리.

**seccomp**: 시스템 콜 필터링. 특정 시스템 콜만 허용하도록 샌드박스.

게임 개발 시 **AppImage, Flatpak, Snap** 같은 배포 포맷은 내부적으로 이 기술들을 사용합니다.

---

## Part 8: 게임 개발자 관점에서

이제 **게임 개발자 입장에서** 세 OS의 차이가 어떻게 드러나는지 살펴봅니다.

### 플랫폼별 게임 개발 고려사항

**1. Unity 에디터**
- Windows: 풀 기능, 권장 플랫폼
- macOS: 지원 양호, Apple Silicon 네이티브 빌드 가능
- Linux: 제한적 지원 (공식 Editor 있음, 플러그인 호환성 떨어짐)

**2. Unreal Engine 에디터**
- Windows: 풀 기능, 기본 지원
- macOS: 지원되지만 일부 기능 제한 (Vulkan 지원 등)
- Linux: 공식 지원 있음, 에디터도 빌드 가능

**3. 그래픽 API 선택**
- 크로스플랫폼이 목표라면 **Vulkan + DirectX 12** 추상화
- Apple 플랫폼 타겟이면 **Metal** 고려 (Apple이 OpenGL/Vulkan 지원을 중단 중)
- Unity/Unreal 같은 엔진이 이 추상화를 제공하지만, 네이티브 최적화 시 직접 관여 필요

**4. 크래시 핸들러**
- Windows: **SEH (Structured Exception Handling)**, `SetUnhandledExceptionFilter`
- Linux/macOS: **POSIX 시그널** (`SIGSEGV`, `SIGABRT`), `signal()` 또는 `sigaction()`
- 두 접근이 달라서 크로스플랫폼 크래시 리포터(Sentry, Crashlytics)가 복잡해짐

**5. 파일 경로**
- Windows: `C:\Users\name\AppData\...`, 역슬래시
- macOS: `/Users/name/Library/Application Support/...`, 슬래시
- Linux: `/home/name/.local/share/...` (XDG 표준), 슬래시
- 엔진의 `Application.persistentDataPath` 같은 추상화를 쓰되, 직접 다룰 때 주의

**6. 스레드 우선순위**
- Windows: `SetThreadPriority`, 7단계 (IDLE~TIME_CRITICAL)
- macOS: QoS 클래스 (4단계) + pthread 우선순위
- Linux: nice 값 (-20~19) + pthread SCHED_FIFO/RR
- 게임에서 오디오 스레드 같은 것에 높은 우선순위를 줘야 할 때 API가 달라짐

### 크로스 플랫폼 엔진의 추상화

엔진은 OS 차이를 **숨기기 위한 레이어**를 가집니다. Unreal Engine의 경우:

```cpp
/* UE의 플랫폼 추상화 (개념적 예시) */
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

이 때문에 엔진 개발자(엔진을 수정하는 프로그래머)는 **세 OS의 API를 모두 이해**해야 합니다. 게임 프로그래머(엔진을 소비하는 입장)는 `FPlatformFile` 같은 추상 레이어만 보면 됩니다.

### 툴체인 호환성

| 도구 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **주 컴파일러** | gcc/clang | MSVC/clang-cl | clang |
| **표준 라이브러리** | glibc/libstdc++/libc++ | MSVC STL | libc++ |
| **링커** | ld/lld | link.exe/lld-link | ld64 |
| **디버거** | gdb, lldb | Visual Studio, WinDbg | lldb, Xcode |
| **프로파일러** | perf, Tracy | Visual Studio Profiler, PIX | Instruments |
| **CI/CD 가능성** | ✅ 최고 | ✅ GitHub Actions Windows Runner | 🟡 Mac Runner는 유료/제한 |

**Apple의 함정**: iOS/macOS 앱을 빌드하려면 **Xcode가 필요**하고, Xcode는 **macOS에서만 돕니다**. 즉, Apple 플랫폼 타겟 게임을 만들려면 반드시 Mac 빌드 머신이 있어야 합니다. CI/CD에서 Mac Runner가 비싼 이유입니다.

### 플랫폼 별 디버깅 경험 비교

**Windows (Visual Studio)**
- 최고 수준의 IDE + 디버거 통합
- Edit and Continue, 조건부 중단점, Data Breakpoint 모두 매끄러움
- PIX로 GPU 프로파일링

**macOS (Xcode + Instruments)**
- Instruments는 세계 최고 수준의 프로파일러 중 하나 (System Trace, Time Profiler, Allocations)
- Apple Silicon의 P/E 코어 타임라인을 시각화해줌
- Metal Frame Debugger

**Linux (gdb/lldb + Tracy)**
- 커맨드라인 도구가 주. VS Code가 UX를 많이 개선
- Valgrind (Memcheck)은 강력하지만 느림
- Tracy Profiler는 크로스플랫폼 최고 옵션 중 하나

---

## 정리

이 편에서 다룬 것을 한 페이지로 요약합니다.

**혈통**:
- Unix (1969) → BSD (1977) → NeXTSTEP (1989) → **macOS (2001)**
- Unix → Minix → **Linux (1991)**
- VMS (1977) + Dave Cutler → **Windows NT (1993)**

**설계 철학**:
- Linux: 개방성 + 성능
- Windows: 하위 호환성
- macOS: 수직 통합 + 경험

**커널 구조**:
- Linux: 모놀리식
- Windows NT: 하이브리드
- macOS XNU: Mach microkernel + BSD layer (이중 구조)

**바이너리 포맷**:
- Linux: ELF
- Windows: PE (1981년 DOS 호환 MZ 헤더 유지)
- macOS: Mach-O (Universal Binary로 다중 아키텍처)

**macOS 특유의 것들**:
- XNU: 이론은 microkernel, 실제는 하이브리드
- Mach port: macOS IPC와 보안의 뿌리
- Grand Central Dispatch (2009): "스레드 대신 큐" 추상화
- launchd (2005): systemd의 5년 전 원형
- Apple Silicon: P/E 이질 코어 + 16KB 페이지
- Rosetta 2: AOT 번역 + 하드웨어 TSO 모드

**게임 개발 시 기억할 점**:
- 실행 바이너리 포맷이 다르기 때문에 멀티플랫폼 빌드는 **각 OS별 빌드**
- 크래시 핸들러, 스레드 우선순위, 파일 경로 등 사소해 보이는 것도 API가 다름
- 엔진 추상화 레이어를 믿되, 성능이 중요한 부분은 플랫폼별 최적화 필요
- Apple 플랫폼 타겟이면 반드시 Mac 빌드 머신 필요

다음 편부터는 이 지도를 바탕으로 **구체적인 이론**으로 들어갑니다. Part 8은 **프로세스와 스레드** — PCB/TCB 구조, `fork()`와 `CreateProcess()`의 실제 차이, 스레드 매핑 모델, 컨텍스트 스위칭 비용까지 게임 엔진의 실행 모델과 연결해 살펴봅니다.

---

## References

### 교재
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — OS 표준 교재, 3장(Processes), 4장(Threads) 참조
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — microkernel vs monolithic 논쟁의 원전
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Linux 커널 내부
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — NT 커널 상세
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNU, Mach, BSD layer
- Levin — *\*OS Internals: Volume I - User Mode* and *Volume II - Kernel Mode*, Technologeeks, 2019 — macOS/iOS 내부의 가장 상세한 현대 저술
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — 게임 엔진에서의 OS 활용

### 논문/연구 문서
- Accetta, Baron, Bolosky, Golub, Rashid, Tevanian, Young — "Mach: A New Kernel Foundation for UNIX Development", USENIX Summer 1986 — Mach 최초 설명 논문
- Young, Tevanian, Rashid, Golub, Eppinger, Chew, Bolosky, Black, Baron — "The Duality of Memory and Communication in the Implementation of a Multiprocessor Operating System", SOSP 1987
- Rashid, Baron, Forin, Golub, Jones, Julin, Orr, Sanzi — "Mach: A Foundation for Open Systems", Workshop on Workstation Operating Systems, 1989
- Bershad, Anderson, Lazowska, Levy — "Lightweight Remote Procedure Call", SOSP 1989 — microkernel IPC 최적화
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:N 스레드 모델

### 공식 문서 / 소스
- Apple Open Source — [opensource.apple.com](https://opensource.apple.com) — XNU, Darwin 소스
- Apple Developer — *Dispatch Queues and Concurrency* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Apple Developer — *About the Rosetta Translation Environment* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment)
- Linux Kernel Documentation — [kernel.org/doc](https://www.kernel.org/doc/)
- Microsoft Docs — *Windows Kernel-Mode Architecture* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/windows-kernel-mode-architecture)
- FreeBSD Architecture Handbook — [docs.freebsd.org/en/books/arch-handbook/](https://docs.freebsd.org/en/books/arch-handbook/)

### 블로그/기사
- Raymond Chen — *The Old New Thing* — Windows 하위 호환성 일화 (SimCity 사례 포함)
- Howard Oakley — *The Eclectic Light Company* — macOS 내부 동작 해설
- Hector Martin (marcan) — *Apple Silicon 역공학* — Asahi Linux 프로젝트
- Dougall Johnson — "M1 Memory and Performance" 시리즈 — Apple Silicon 하드웨어 분석
- Linus Torvalds — *comp.os.minix* "Hello everybody" post (1991-08-25)
- Linus vs. Tanenbaum debate (1992) — microkernel 논쟁 아카이브

### 도구
- `file`, `readelf`, `objdump` (Linux) — ELF 분석
- `dumpbin`, `PEview` (Windows) — PE 분석
- `otool`, `nm`, `lipo` (macOS) — Mach-O 분석
- `launchctl`, `ps`, `top` — 세 OS 공통 관찰 도구
- Instruments (macOS) — Apple 공식 프로파일러

### 이미지 출처
- Ken Thompson & Dennis Ritchie (1973) — Jargon File, Public Domain — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Ken_Thompson_and_Dennis_Ritchie--1973.jpg)
- Linus Torvalds at LinuxCon Europe 2014 — photo by Krd, CC BY-SA 4.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:LinuxCon_Europe_Linus_Torvalds_03_(cropped).jpg)
- NeXTcube (1990) at Computer History Museum — photo by Michael Hicks, CC BY 2.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:NeXTcube_computer_(1990)_-_Computer_History_Museum.jpg)
