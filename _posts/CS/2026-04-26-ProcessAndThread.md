---
title: "CS 로드맵 8편 — 프로세스와 스레드: OS는 실행 단위를 어떻게 추상화하는가"
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
  - 프로세스는 "독립된 주소 공간 + 자원의 묶음"이고, 스레드는 "프로세스 안의 실행 흐름"이다. 스레드는 코드/힙/전역 변수를 공유하지만 스택과 레지스터는 전용으로 갖는다
  - Unix의 fork()는 프로세스를 복제 후 exec()로 덮어쓰는 2단계이고, Windows의 CreateProcess()는 한 번에 새로 만든다. 복제가 비싸 보이지만 Copy-on-Write로 실제로는 빠르다
  - 스레드 모델은 1:1 (Linux NPTL, Windows), N:1 (그린 스레드), M:N (Go goroutine, Erlang)으로 나뉘며, 성능과 구현 복잡도의 트레이드오프가 다르다
  - 컨텍스트 스위치는 레지스터 저장/복원뿐 아니라 TLB flush와 캐시 오염까지 일으키므로, 현대 게임 엔진은 "스레드 개수를 늘리기"보다 "Job/TaskGraph/Fiber로 작업을 잘게 쪼개 코어에 분배"하는 방향으로 간다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: 지도에서 본론으로

[지난 편](/posts/OSArchitecture/)에서는 세 운영체제의 혈통과 뼈대를 훑었습니다. Linux는 모놀리식, Windows NT는 하이브리드, macOS XNU는 Mach + BSD 이중 구조. 이게 **지도**였다면, 이번 편부터는 **본론**입니다.

Stage 2의 핵심 질문을 다시 꺼내 보겠습니다.

> **"스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?"**

이 질문에 답하려면 먼저 **"스레드가 뭔가"**부터 정확히 알아야 합니다. 그리고 스레드를 이해하려면 그 상위 개념인 **프로세스**를 먼저 알아야 합니다. 프로세스와 스레드의 차이, 둘이 메모리를 어떻게 공유하고 어떻게 분리하는지, 그리고 OS가 이것을 어떻게 추상화하는지 — 이것이 동시성의 모든 문제의 출발점입니다.

이번 편에서 다루는 것:

- **프로세스**: PCB와 주소 공간 레이아웃. Linux의 `task_struct`, Windows의 `EPROCESS`, macOS의 `proc`/`task`
- **프로세스 생성**: Unix의 `fork()`+`exec()` 2단계 모델, Windows의 `CreateProcess()` 단일 호출, 그리고 Copy-on-Write
- **스레드**: 왜 프로세스만으로 부족한가, TCB, 공유 영역과 전용 영역, TLS
- **스레드 매핑 모델**: 1:1, N:1, M:N — Go의 goroutine이 왜 그렇게 가벼운가
- **컨텍스트 스위칭**: 레지스터·TLB·캐시 비용의 실제
- **게임 엔진의 실행 모델**: Unity main thread, Unreal TaskGraph, Naughty Dog의 Fiber

게임 개발 시각을 계속 유지하면서도, 이번 편은 **이론적 기초**가 많습니다. 다음 편(스케줄링), 그 다음 편(동기화)이 이 위에 쌓이기 때문입니다.

---

## Part 1: 프로세스 — OS가 보는 실행 단위

### 프로세스란 무엇인가

교과서적 정의부터 봅시다. **프로세스 (Process)**는 **실행 중인 프로그램**입니다. 하드 디스크에 있는 `.exe` 파일이나 Mach-O 바이너리는 **프로그램**이고, 그것이 메모리에 적재되어 CPU에서 실행되는 인스턴스가 **프로세스**입니다.

프로세스가 가지는 것들:

1. **고유한 주소 공간 (Address Space)** — 다른 프로세스와 격리된 메모리
2. **실행 상태** — CPU 레지스터 값, 프로그램 카운터
3. **열린 파일 테이블** — 현재 사용 중인 파일 디스크립터 목록
4. **소유자 정보** — UID, GID 등 권한
5. **자식 프로세스 관계** — 누가 누구를 만들었나 (프로세스 트리)

OS는 이 모든 정보를 하나의 **구조체**로 관리합니다. 이것이 **PCB (Process Control Block)** 혹은 **프로세스 디스크립터**입니다.

### PCB의 실체 — OS별 구조체

**Linux — `task_struct`**

Linux 커널에서 프로세스(그리고 스레드)를 나타내는 구조체는 `struct task_struct`입니다. `include/linux/sched.h`에 정의되어 있고, **수백 개의 필드**를 가진 거대한 구조체입니다.

```c
/* Linux 커널 task_struct의 일부 (kernel 6.x 기준, 극단 단순화) */
struct task_struct {
    /* 상태 */
    unsigned int           __state;          /* TASK_RUNNING 등 */

    /* 식별자 */
    pid_t                  pid;              /* 프로세스 ID */
    pid_t                  tgid;             /* 스레드 그룹 ID */
    struct task_struct    *parent;           /* 부모 프로세스 */
    struct list_head       children;         /* 자식 목록 */

    /* 메모리 */
    struct mm_struct      *mm;               /* 주소 공간 */

    /* 파일 */
    struct files_struct   *files;            /* 열린 파일 테이블 */

    /* 스케줄링 */
    int                    prio;
    struct sched_entity    se;               /* CFS 스케줄링 엔티티 */

    /* 신호, 자원 제한 등 수백 필드... */
};
```

실제 구조체는 700줄이 넘습니다. Linux에서 **프로세스와 스레드는 같은 구조체**로 표현됩니다 — 이것이 Linux의 독특한 설계로, 뒤에서 다시 다룹니다.

**Windows — `EPROCESS`, `KPROCESS`**

Windows NT는 두 계층으로 나뉩니다:
- `KPROCESS` (Kernel Process Block) — 스케줄링 관련 최소 정보
- `EPROCESS` (Executive Process Block) — `KPROCESS`를 감싸고 추가 정보 포함

```c
/* 개념적 의사 코드 — 실제 Windows 내부는 WinDbg나 NT 소스 누출본 참조 */
typedef struct _EPROCESS {
    KPROCESS Pcb;                    /* 커널 프로세스 블록 (상속) */
    HANDLE UniqueProcessId;          /* PID */
    LIST_ENTRY ActiveProcessLinks;   /* 전역 프로세스 리스트 */
    PVOID SectionBaseAddress;        /* 이미지 로드 주소 */
    PVOID Token;                     /* 보안 토큰 */
    /* ... */
} EPROCESS;
```

**macOS — `proc` + `task`**

macOS의 이중 구조가 여기서도 드러납니다. **BSD 레이어**에는 Unix 전통의 `struct proc`이 있고, **Mach 레이어**에는 `struct task`가 있습니다.

```c
/* BSD 측 — bsd/sys/proc_internal.h */
struct proc {
    pid_t                  p_pid;           /* POSIX 프로세스 ID */
    struct proc           *p_pptr;          /* 부모 */
    struct task           *task;            /* Mach task로의 링크 */
    /* ... */
};

/* Mach 측 — osfmk/kern/task.h */
struct task {
    queue_head_t           threads;         /* 이 task에 속한 스레드들 */
    vm_map_t               map;             /* 주소 공간 */
    ipc_space_t            itk_space;       /* Mach port 공간 */
    /* ... */
};
```

즉, macOS에서 `fork()`로 프로세스를 만들면 **BSD의 `proc`과 Mach의 `task`가 쌍으로 생성**됩니다. Unix 프로그램(`ps`, `top`)은 `proc`을 보고, Mach 기반 도구(`lldb`, `Instruments`)는 `task`를 봅니다.

### 프로세스 주소 공간 레이아웃

프로세스가 가진 메모리는 **어떻게 배치**되어 있을까요? 전통적인 Unix/Linux 프로세스의 32비트 주소 공간 레이아웃을 봅시다.

<div class="pt-addr-container">
<svg viewBox="0 0 700 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process address space layout">
  <text x="350" y="28" text-anchor="middle" class="pa-title">프로세스 주소 공간 레이아웃 (개념도)</text>

  <g class="pa-layer pa-kernel">
    <rect x="180" y="55" width="340" height="50" rx="4"/>
    <text x="350" y="78" text-anchor="middle" class="pa-label">Kernel Space</text>
    <text x="350" y="95" text-anchor="middle" class="pa-sub">(유저 프로세스가 직접 접근 불가)</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="130" x2="600" y2="105" class="pa-arrow"/>
    <text x="615" y="122" class="pa-addr">높은 주소</text>
    <text x="615" y="138" class="pa-addr">0xFFFFFFFF</text>
  </g>

  <g class="pa-layer pa-stack">
    <rect x="180" y="120" width="340" height="70" rx="4"/>
    <text x="350" y="145" text-anchor="middle" class="pa-label">Stack</text>
    <text x="350" y="165" text-anchor="middle" class="pa-sub">함수 호출 프레임, 지역 변수</text>
    <text x="350" y="180" text-anchor="middle" class="pa-sub pa-emph">↓ 아래로 자란다</text>
  </g>

  <g class="pa-layer pa-gap">
    <rect x="180" y="200" width="340" height="120" rx="4"/>
    <text x="350" y="235" text-anchor="middle" class="pa-label pa-gray">미사용 영역</text>
    <text x="350" y="258" text-anchor="middle" class="pa-sub pa-gray">Stack이 자랄 공간</text>
    <text x="350" y="280" text-anchor="middle" class="pa-sub pa-gray">mmap된 공유 라이브러리가 여기 배치</text>
    <text x="350" y="300" text-anchor="middle" class="pa-sub pa-gray">(libc, libdl, 힙 확장 등)</text>
  </g>

  <g class="pa-layer pa-heap">
    <rect x="180" y="330" width="340" height="70" rx="4"/>
    <text x="350" y="355" text-anchor="middle" class="pa-label">Heap</text>
    <text x="350" y="375" text-anchor="middle" class="pa-sub">malloc / new로 할당되는 메모리</text>
    <text x="350" y="390" text-anchor="middle" class="pa-sub pa-emph">↑ 위로 자란다 (brk / sbrk)</text>
  </g>

  <g class="pa-layer pa-bss">
    <rect x="180" y="410" width="340" height="40" rx="4"/>
    <text x="350" y="432" text-anchor="middle" class="pa-label">BSS (Uninitialized Data)</text>
    <text x="350" y="445" text-anchor="middle" class="pa-sub">int x; (0으로 초기화)</text>
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
    <text x="350" y="583" text-anchor="middle" class="pa-sub">실행 가능 기계어</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="568" x2="600" y2="590" class="pa-arrow"/>
    <text x="615" y="583" class="pa-addr">낮은 주소</text>
    <text x="615" y="598" class="pa-addr">0x00400000</text>
  </g>

  <g class="pa-note">
    <text x="40" y="78" class="pa-sectlabel">보호</text>
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

각 영역을 설명합니다 (낮은 주소부터):

- **Text (`.text`)**: 실행 가능한 기계어. **읽기 + 실행**만 허용. 쓰기 시도는 세그멘테이션 폴트
- **Read-only Data (`.rodata`)**: 문자열 리터럴(`"Hello"`), 상수 배열 등. **읽기 전용**
- **Data (`.data`)**: 초기화된 전역/정적 변수 (`int x = 42;`). 파일에 초기값이 들어 있음
- **BSS (Block Started by Symbol)**: 0으로 초기화된 전역 변수 (`int x;`, `static char buf[1024];`). 파일에는 **크기만** 기록되고, 실행 시 OS가 0으로 채운다 — 실행 파일 크기를 줄이는 트릭
- **Heap**: 동적 할당 (`malloc`, `new`). `brk()` 시스템 콜로 위쪽으로 확장
- **공유 라이브러리 영역 (mmap)**: `libc.so`, `libstdc++.so` 등이 `mmap()`으로 이 영역에 매핑됨
- **Stack**: 함수 호출 프레임, 지역 변수, 반환 주소. **아래쪽으로** 자람
- **Kernel Space**: 커널 코드와 데이터. 유저 프로세스는 직접 접근 불가. 32비트 Linux에서는 상위 1GB, x86-64에서는 상위 절반

**Windows도 PE와 다른 섹션 이름을 쓰지만 구조는 거의 동일**합니다 (`.text`, `.data`, `.rdata`, `.bss`).

### 프로세스 상태 전이

프로세스는 **여러 상태**를 왔다 갔다 합니다. Silberschatz 교재의 표준 모델:

<div class="ps-container">
<svg viewBox="0 0 900 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="프로세스 상태 전이 다이어그램">
  <defs>
    <marker id="ps-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" class="ps-arrowfill"/>
    </marker>
  </defs>

  <text x="450" y="22" text-anchor="middle" class="ps-title">프로세스 상태 전이 (Silberschatz 모델)</text>

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

- **New**: 프로세스가 막 생성됨
- **Ready**: 실행 가능하지만 CPU를 기다리는 중
- **Running**: CPU에서 실제로 실행 중
- **Waiting (또는 Blocked)**: I/O 완료나 이벤트를 기다리는 중
- **Terminated**: 종료됨

실제 OS들은 이보다 **훨씬 더 복잡한 상태**를 가집니다. Linux의 `task_struct`에는 `TASK_RUNNING`, `TASK_INTERRUPTIBLE`, `TASK_UNINTERRUPTIBLE`, `TASK_STOPPED`, `TASK_TRACED`, `TASK_DEAD`, `TASK_WAKEKILL`, `TASK_WAKING`, `TASK_PARKED` 등이 있습니다. `ps`에서 보이는 `S`, `R`, `D`, `Z` 같은 문자가 이것들입니다.

```bash
$ ps aux
USER  PID  %CPU %MEM  COMMAND
root   1   0.0  0.1   /sbin/init           <- S (sleeping)
www    1234 2.1  1.5   nginx: worker        <- R (running)
root   5678 0.0  0.0   [kworker/u8:2]       <- D (uninterruptible sleep)
```

**D 상태 (uninterruptible sleep)**는 게임 개발자에게도 중요합니다 — 디스크 I/O나 드라이버 요청을 기다리는 상태로, 이 상태에서는 `kill -9`조차 통하지 않습니다. "응답 없는 프로세스" 상당수가 D 상태입니다.

---

## Part 2: 프로세스 생성 — fork, exec, CreateProcess

이제 프로세스를 **어떻게 만드는가**를 봅시다. 세 OS의 철학 차이가 가장 극명하게 드러나는 지점입니다.

### Unix: fork() + exec() — 2단계 모델

Unix의 아이디어는 **"부모를 복제한 다음 덮어쓴다"**입니다.

```c
#include <unistd.h>
#include <sys/wait.h>

int main() {
    pid_t pid = fork();   /* 1단계: 자신을 복제 */

    if (pid == 0) {
        /* 자식 프로세스 */
        execl("/bin/ls", "ls", "-l", NULL);   /* 2단계: 새 프로그램으로 덮어쓰기 */
        /* execl이 성공하면 여기는 실행되지 않음 */
    } else if (pid > 0) {
        /* 부모 프로세스 */
        int status;
        waitpid(pid, &status, 0);             /* 자식 종료 대기 */
    } else {
        perror("fork failed");
    }
    return 0;
}
```

`fork()` 하나의 호출이 **두 번 리턴**합니다. 부모에게는 자식의 PID를, 자식에게는 0을 돌려줍니다. 희한한 API입니다.

**fork()가 하는 일** (naive 구현):
1. 새 PCB (`task_struct`) 생성
2. 부모의 주소 공간을 **전부 복사** (text, data, heap, stack 모두)
3. 열린 파일 디스크립터도 복사
4. 자식에게 새 PID 할당
5. 자식을 ready 큐에 넣음

2번이 문제입니다. 프로세스 주소 공간이 수백 MB일 때 **매번 복사하면 엄청나게 비쌉니다**. 그런데 `fork()` 직후 `exec()`를 부르면 어차피 주소 공간을 덮어쓸 텐데, 복사했다가 바로 버리는 셈입니다.

### Copy-on-Write — "진짜로 쓸 때 복사하자"

해결책은 **Copy-on-Write (COW)**입니다. `fork()` 시점에는 **페이지 테이블만 복사**하고, 실제 메모리 페이지들은 부모와 자식이 **공유**합니다. 그런데 페이지들을 **읽기 전용**으로 표시해 둡니다.

어느 한쪽이 페이지에 **쓰려고 하면** 하드웨어가 page fault를 일으키고, OS가 그제야 **해당 페이지만** 복사해 줍니다.

<div class="pt-fork-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="fork with COW">
  <text x="450" y="28" text-anchor="middle" class="pf-title">fork() + Copy-on-Write의 실제 동작</text>

  <g class="pf-step">
    <text x="150" y="65" text-anchor="middle" class="pf-step-label">1) fork() 호출 직후</text>
    <rect x="30" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="80" y="105" text-anchor="middle" class="pf-proc-label">부모</text>
    <text x="80" y="125" text-anchor="middle" class="pf-proc-sub">페이지 테이블</text>

    <rect x="170" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="220" y="105" text-anchor="middle" class="pf-proc-label">자식</text>
    <text x="220" y="125" text-anchor="middle" class="pf-proc-sub">페이지 테이블 (복사)</text>

    <rect x="80" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="150" y="194" text-anchor="middle" class="pf-page-label">물리 페이지 (읽기 전용)</text>

    <line x1="80" y1="140" x2="130" y2="170" class="pf-edge"/>
    <line x1="220" y1="140" x2="170" y2="170" class="pf-edge"/>

    <text x="150" y="235" text-anchor="middle" class="pf-note">페이지 테이블만 복사 — 빠르다</text>
    <text x="150" y="252" text-anchor="middle" class="pf-note">실제 메모리는 공유</text>
  </g>

  <g class="pf-step">
    <text x="450" y="65" text-anchor="middle" class="pf-step-label">2) 자식이 페이지에 쓰기 시도</text>
    <rect x="330" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="380" y="105" text-anchor="middle" class="pf-proc-label">부모</text>
    <text x="380" y="125" text-anchor="middle" class="pf-proc-sub">페이지 테이블</text>

    <rect x="470" y="80" width="100" height="60" rx="4" class="pf-proc pf-proc-active"/>
    <text x="520" y="105" text-anchor="middle" class="pf-proc-label">자식</text>
    <text x="520" y="125" text-anchor="middle" class="pf-proc-sub">쓰기 시도 ✍️</text>

    <rect x="380" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="450" y="194" text-anchor="middle" class="pf-page-label">물리 페이지 (읽기 전용)</text>

    <line x1="380" y1="140" x2="430" y2="170" class="pf-edge"/>
    <line x1="520" y1="140" x2="470" y2="170" class="pf-edge pf-edge-fault"/>

    <text x="450" y="235" text-anchor="middle" class="pf-note pf-fault">⚡ Page Fault 발생</text>
    <text x="450" y="252" text-anchor="middle" class="pf-note">CPU → OS에게 처리 요청</text>
  </g>

  <g class="pf-step">
    <text x="750" y="65" text-anchor="middle" class="pf-step-label">3) OS가 페이지를 복사</text>
    <rect x="630" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="680" y="105" text-anchor="middle" class="pf-proc-label">부모</text>

    <rect x="770" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="820" y="105" text-anchor="middle" class="pf-proc-label">자식</text>

    <rect x="620" y="170" width="120" height="40" rx="4" class="pf-page pf-page-orig"/>
    <text x="680" y="194" text-anchor="middle" class="pf-page-label">원본 (RW 복원)</text>

    <rect x="760" y="170" width="120" height="40" rx="4" class="pf-page pf-page-new"/>
    <text x="820" y="194" text-anchor="middle" class="pf-page-label">복사본 (자식 전용)</text>

    <line x1="680" y1="140" x2="680" y2="170" class="pf-edge"/>
    <line x1="820" y1="140" x2="820" y2="170" class="pf-edge"/>

    <text x="750" y="235" text-anchor="middle" class="pf-note">실제로 쓴 페이지만 복사</text>
    <text x="750" y="252" text-anchor="middle" class="pf-note">나머지는 계속 공유</text>
  </g>

  <g class="pf-conclusion">
    <rect x="30" y="290" width="840" height="130" rx="8" class="pf-concl-box"/>
    <text x="450" y="315" text-anchor="middle" class="pf-concl-title">결과: fork()는 "복사"가 아니라 "공유 + 지연 복사"</text>
    <text x="450" y="343" text-anchor="middle" class="pf-concl-line">• fork() 자체는 페이지 테이블 크기만큼만 작업 — 수 마이크로초</text>
    <text x="450" y="363" text-anchor="middle" class="pf-concl-line">• 자식이 대부분의 페이지를 쓰지 않고 바로 exec()를 부르면 복사 비용이 0에 가깝다</text>
    <text x="450" y="383" text-anchor="middle" class="pf-concl-line">• 페이지 수준 granularity (보통 4KB 또는 16KB) — 바이트 하나 쓰면 페이지 전체 복사</text>
    <text x="450" y="403" text-anchor="middle" class="pf-concl-line">• Linux는 이걸 태스크 생성의 기본으로 삼아 프로세스 생성이 극히 빠르다</text>
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

COW는 하드웨어 지원이 필요합니다 — CPU의 MMU (Memory Management Unit)가 페이지 단위 보호와 page fault를 일으켜 주어야 OS가 개입할 수 있습니다. 그래서 **페이지 단위 MMU**는 현대 OS의 거의 모든 트릭(COW, 스왑, mmap, 공유 메모리)의 기반입니다.

### Windows: CreateProcess() — 단일 호출

Windows는 다른 길을 갔습니다. 부모 복제 개념이 없고, **새 프로세스를 처음부터 만듭니다**.

```c
#include <windows.h>

int main() {
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    BOOL ok = CreateProcess(
        "C:\\Windows\\System32\\notepad.exe",  /* 실행 파일 */
        NULL,                                   /* 명령줄 */
        NULL, NULL,                             /* 프로세스/스레드 보안 속성 */
        FALSE,                                  /* 핸들 상속 여부 */
        0,                                      /* 생성 플래그 */
        NULL, NULL,                             /* 환경 변수, 작업 디렉토리 */
        &si, &pi);

    if (ok) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    return 0;
}
```

Unix의 `fork()`는 매개변수가 없는데, `CreateProcess()`는 **10개**의 매개변수를 받습니다. 이는 "프로세스 생성 시 설정 가능한 모든 옵션을 한 함수에 몰아넣는" Windows의 철학입니다.

**트레이드오프**:

| 측면 | Unix `fork()+exec()` | Windows `CreateProcess()` |
|------|---------------------|---------------------------|
| **API 복잡도** | 두 단계지만 각각 단순 | 한 단계지만 매개변수 많음 |
| **프로세스 생성 비용** | COW로 매우 저렴 | 상대적으로 비쌈 |
| **셸 구현** | 자연스럽 (fork → 리다이렉션 설정 → exec) | ShellExecute 같은 별도 API 필요 |
| **보안** | 부모 핸들이 자동 상속 (실수 여지 있음) | 명시적으로 상속 지정 |
| **유연성** | fork 후 exec 전에 임의 코드 실행 가능 | 생성 시점에만 설정 |

### macOS — Unix 계승 + 몇 가지 트위스트

macOS는 BSD 계승이니 당연히 `fork()`와 `exec()`를 지원합니다. 하지만 **XNU의 내부 구현은 약간 독특**합니다.

BSD의 `fork()`가 Mach에 매핑될 때 실제로는:
1. 현재 `proc` 구조체를 복제
2. 현재 `task`를 Mach 레벨에서 복제 (`task_create()`)
3. 초기 스레드 하나 만들기 (`thread_create()`)
4. 주소 공간도 복제 (Mach의 vm_map을 COW로 복제)

즉, **BSD `fork()` 호출 하나가 Mach 레이어의 여러 연산**으로 분해됩니다. 이것이 XNU 이중 구조의 실제 모습입니다.

또 하나 흥미로운 것은 macOS의 **`posix_spawn()`**입니다. POSIX 표준인데 macOS가 적극 장려하는 API로, **fork+exec를 한 번에 수행**합니다.

```c
posix_spawn(&pid, "/bin/ls", NULL, NULL, argv, environ);
```

왜 이걸 쓰라는가? **iOS 때문**입니다. iOS에서는 `fork()`가 보안상 금지됐고, `posix_spawn()`만 허용됩니다. 또한 내부 구현이 더 효율적인 경우도 있습니다 (COW 페이지 테이블 복제조차 건너뛸 수 있음).

> ### 잠깐, 이건 짚고 넘어가자
>
> **"iOS에서 fork()를 왜 금지했는가?"**
>
> 세 가지 이유가 겹칩니다.
>
> 1. **샌드박스 침해 위험**: fork()된 자식 프로세스는 부모의 권한을 상속하는데, iOS의 엄격한 앱 샌드박스 모델에서는 이 경계를 깨뜨릴 수 있는 잠재적 취약점이 됩니다
> 2. **Objective-C 런타임의 상태 복제 문제**: iOS 앱은 대부분 Objective-C나 Swift로 작성되며, 이들 언어의 런타임은 초기화 시 많은 상태(스레드, GCD 큐, IOKit 연결 등)를 생성합니다. fork() 이후 이들 상태가 일관성을 잃기 쉽습니다
> 3. **메모리 효율**: iOS는 메모리가 제한적이며 COW도 페이지 테이블 복제는 필요합니다. posix_spawn()은 이것조차 생략 가능
>
> macOS에서는 fork()가 여전히 허용되지만, Apple은 "가능하면 posix_spawn()을 쓰라"고 권고합니다.

---

## Part 3: 스레드 — 왜 프로세스만으로는 부족한가

### 프로세스 기반 동시성의 한계

1970~80년대 Unix는 **프로세스 하나 = 실행 흐름 하나**였습니다. 여러 일을 동시에 하려면 `fork()`로 프로세스를 여러 개 만들었습니다. 웹 서버라면 연결마다 프로세스를 하나씩 만드는 식 (고전적인 Apache `prefork` 모드).

이 모델의 문제:

1. **프로세스 생성 비용**: COW로 저렴해졌다지만, 페이지 테이블 복제, PCB 할당 등 여전히 수 마이크로초~밀리초 단위
2. **컨텍스트 스위치 비용**: 프로세스 간 전환 시 주소 공간도 바뀌므로 TLB flush가 필요 (뒤에서 자세히)
3. **프로세스 간 통신 (IPC) 비용**: 프로세스끼리는 주소 공간이 분리되어 있어, 데이터를 주고받으려면 파이프, 소켓, 공유 메모리 같은 무거운 메커니즘이 필요
4. **공유 상태 표현의 어려움**: 여러 실행 흐름이 같은 자료 구조를 다루고 싶을 때 복잡

1990년대 들어 해결책이 필요해졌고, 그것이 **스레드 (Thread)**입니다.

### 스레드의 정의

**스레드**는 **프로세스 내부의 독립된 실행 흐름**입니다. 한 프로세스 안에 여러 스레드가 있으면, 모두가 같은 주소 공간을 공유하면서 **각자 CPU에서 동시에 실행될 수 있습니다**.

스레드가 **공유**하는 것:
- **Text (코드)**: 당연히 같은 코드를 실행
- **Heap**: `malloc`으로 할당한 메모리
- **Data / BSS**: 전역 변수, 정적 변수
- **열린 파일 디스크립터**
- **신호 핸들러**

스레드가 **따로 가지는** 것:
- **스택 (Stack)**: 각 스레드마다 별도
- **CPU 레지스터 상태**: PC, SP, 범용 레지스터 등
- **TLS (Thread-Local Storage)**: 스레드별 전역 변수
- **에러 상태**: `errno` (POSIX에서는 스레드별)

<div class="pt-share-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process vs thread memory sharing">
  <text x="450" y="28" text-anchor="middle" class="ps-title">프로세스 간 vs 스레드 간 메모리 공유</text>

  <g class="ps-left">
    <text x="225" y="62" text-anchor="middle" class="ps-heading">여러 프로세스 — 완전 분리</text>

    <g class="ps-proc">
      <rect x="40" y="80" width="170" height="330" rx="8"/>
      <text x="125" y="103" text-anchor="middle" class="ps-proc-label">프로세스 A</text>
      <rect x="55" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="125" y="137" text-anchor="middle" class="ps-sect-lab">Text (코드)</text>
      <rect x="55" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="125" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="55" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="125" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="55" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="125" y="302" text-anchor="middle" class="ps-sect-lab">Stack (실행 흐름 1)</text>
      <rect x="55" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="55" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="55" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <g class="ps-proc">
      <rect x="240" y="80" width="170" height="330" rx="8"/>
      <text x="325" y="103" text-anchor="middle" class="ps-proc-label">프로세스 B</text>
      <rect x="255" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="325" y="137" text-anchor="middle" class="ps-sect-lab">Text (별개)</text>
      <rect x="255" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="325" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="255" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="325" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="255" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="325" y="302" text-anchor="middle" class="ps-sect-lab">Stack (실행 흐름 1)</text>
      <rect x="255" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="255" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="255" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <text x="225" y="433" text-anchor="middle" class="ps-caption">IPC (파이프/소켓/공유메모리) 없이는 소통 불가</text>
  </g>

  <g class="ps-right">
    <text x="675" y="62" text-anchor="middle" class="ps-heading">한 프로세스 내 여러 스레드 — 대부분 공유</text>

    <g class="ps-proc ps-proc-big">
      <rect x="470" y="80" width="410" height="330" rx="8"/>
      <text x="675" y="103" text-anchor="middle" class="ps-proc-label">프로세스 C (스레드 3개)</text>

      <rect x="485" y="118" width="380" height="28" rx="3" class="ps-sect ps-sect-text ps-sect-shared"/>
      <text x="675" y="137" text-anchor="middle" class="ps-sect-lab">Text (공유)</text>
      <rect x="485" y="152" width="380" height="28" rx="3" class="ps-sect ps-sect-data ps-sect-shared"/>
      <text x="675" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS (공유)</text>
      <rect x="485" y="186" width="380" height="60" rx="3" class="ps-sect ps-sect-heap ps-sect-shared"/>
      <text x="675" y="221" text-anchor="middle" class="ps-sect-lab">Heap (공유)</text>

      <g class="ps-thread">
        <rect x="485" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="545" y="272" text-anchor="middle" class="ps-sect-lab">Stack T1</text>
        <text x="545" y="290" text-anchor="middle" class="ps-sect-sub">전용</text>
      </g>
      <g class="ps-thread">
        <rect x="615" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="675" y="272" text-anchor="middle" class="ps-sect-lab">Stack T2</text>
        <text x="675" y="290" text-anchor="middle" class="ps-sect-sub">전용</text>
      </g>
      <g class="ps-thread">
        <rect x="745" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="805" y="272" text-anchor="middle" class="ps-sect-lab">Stack T3</text>
        <text x="805" y="290" text-anchor="middle" class="ps-sect-sub">전용</text>
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
      <text x="675" y="361" text-anchor="middle" class="ps-sect-lab">File descriptors (공유)</text>

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

    <text x="675" y="433" text-anchor="middle" class="ps-caption">같은 heap/data를 그냥 읽고 쓴다 — 경합 조건의 근원</text>
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

이 그림에서 중요한 점:

1. **스레드 간에는 heap과 전역 변수가 그냥 공유됩니다** — "공유 메모리"가 자연스럽게 존재
2. 즉 스레드 두 개가 같은 `int counter`를 동시에 `counter++` 하면 **race condition**이 생깁니다
3. 반면 프로세스 두 개는 주소 공간이 분리되어 있어 자연히 격리됨

Stage 2의 핵심 질문 — "**스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?**" — 의 답이 이 그림 안에 있습니다. 스레드는 **의도적으로 메모리를 공유**하기 때문에 동시성 문제가 생기고, 그것을 관리할 **동기화 기법**이 필요합니다. (다음 편 [Part 10 동기화 프리미티브]에서 본격적으로 다룹니다.)

### TCB — 스레드 제어 블록

프로세스에 PCB가 있듯 스레드에는 **TCB (Thread Control Block)**이 있습니다. TCB가 담는 것:

- 스레드 ID
- CPU 레지스터 상태 (저장된 컨텍스트)
- 스레드 상태 (Running, Ready, Waiting)
- 스택 포인터, 스택 베이스
- 스케줄링 정보 (우선순위 등)
- 소속 프로세스 포인터

OS별 구현:

- **Linux**: `task_struct` — 프로세스와 스레드를 **같은 구조체**로 표현. 어떤 필드를 공유하느냐로 구분
- **Windows**: `KTHREAD` + `ETHREAD`
- **macOS**: Mach의 `struct thread`

### Linux의 독특한 철학 — "프로세스와 스레드는 같다"

Linus Torvalds는 1990년대에 과감한 결정을 내렸습니다. **"프로세스와 스레드를 별도 개념으로 만들지 말고, 하나의 '실행 단위'로 통합하자."**

Linux에서는 `fork()` 대신 더 일반적인 `clone()` 시스템 콜이 있습니다. `clone()`은 **"부모와 무엇을 공유할지"**를 비트 플래그로 지정합니다.

```c
/* Linux clone() — 개념 */
clone(fn, stack, flags, arg);

/* 플래그 예: */
CLONE_VM       /* 주소 공간 공유 (true이면 스레드, false이면 프로세스) */
CLONE_FS       /* 파일 시스템 상태 공유 */
CLONE_FILES    /* 파일 디스크립터 공유 */
CLONE_SIGHAND  /* 신호 핸들러 공유 */
CLONE_THREAD   /* 같은 스레드 그룹에 소속 */
/* ... */
```

- `fork()` = `clone()` with **모든 공유 플래그 OFF**
- `pthread_create()` = `clone()` with **모든 공유 플래그 ON**
- 그 사이의 **어떤 조합**도 가능

이것이 Linux의 "프로세스와 스레드는 연속적"인 관점입니다. 실제로 Android 같은 환경에서는 **"일부만 공유하는" 프로세스 복제**를 유용하게 사용합니다 (Zygote 프로세스).

### TLS — Thread-Local Storage

스레드별로 **전역처럼 보이지만 실제로는 스레드마다 독립적인 변수**가 필요할 때가 있습니다. 이것이 **TLS**입니다.

전형적 예: `errno`. POSIX에서 `errno`는 "마지막 시스템 콜의 오류 코드"인데, 스레드마다 별개여야 합니다 (스레드 A가 `read()`를 실패한 결과를 스레드 B가 덮어쓰면 안 됨). 그래서 `errno`는 TLS로 구현됩니다.

언어별 TLS 선언:

```c
/* C11 */
_Thread_local int counter = 0;

/* GCC/Clang 확장 */
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

// 또는 더 유연한 ThreadLocal<T>
static ThreadLocal<int> counter = new ThreadLocal<int>(() => 0);
```

게임 개발에서의 실용 예:
- 로깅 시스템에서 각 스레드의 **이름**을 TLS로 저장해 로그 라인에 포함
- 렌더링에서 **스레드별 command buffer** 할당 후 나중에 merge
- 프로파일링에서 **현재 실행 중인 스코프 스택**을 스레드별로 관리

---

## Part 4: 스레드 모델 — 1:1, N:1, M:N

이제 좀 더 깊은 질문입니다. 여러분이 `pthread_create()`나 `new Thread()`를 부를 때, **OS 커널은 그 스레드를 어떻게 관리**할까요?

### 왜 이 질문이 중요한가

CPU에서 실제로 실행 가능한 단위는 **커널 스레드 (Kernel-level Thread, KLT)**입니다. 커널만이 CPU를 스케줄링할 수 있기 때문입니다.

반면 프로그램이 만드는 "스레드"는 그저 **유저 공간의 추상화**일 수 있습니다. 이것을 **유저 스레드 (User-level Thread, ULT)**라고 부릅니다.

유저 스레드와 커널 스레드의 매핑 방식이 세 가지로 나뉩니다.

<div class="pt-model-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Thread mapping models">
  <text x="450" y="28" text-anchor="middle" class="pm-title">유저 스레드 ↔ 커널 스레드 매핑 모델</text>

  <g class="pm-model">
    <rect x="30" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="165" y="80" text-anchor="middle" class="pm-heading">1:1 (일대일)</text>
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
      <text x="165" y="290" text-anchor="middle" class="pm-sec-label">장점</text>
      <text x="165" y="310" text-anchor="middle" class="pm-line">• 구현 단순</text>
      <text x="165" y="328" text-anchor="middle" class="pm-line">• 진정한 병렬성 (멀티코어)</text>
      <text x="165" y="346" text-anchor="middle" class="pm-line">• 커널 스케줄러 활용</text>
    </g>
    <g class="pm-cons">
      <text x="165" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">단점</text>
      <text x="165" y="400" text-anchor="middle" class="pm-line">• 스레드 생성 비용 높음</text>
      <text x="165" y="418" text-anchor="middle" class="pm-line">• 수천 개면 커널 자원 고갈</text>
      <text x="165" y="436" text-anchor="middle" class="pm-line">• 컨텍스트 스위치 무거움</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="315" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="450" y="80" text-anchor="middle" class="pm-heading">N:1 (다대일)</text>
    <text x="450" y="100" text-anchor="middle" class="pm-sub">옛 그린 스레드, GNU Pth</text>

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
      <text x="450" y="240" text-anchor="middle" class="pm-klt-label">KLT 1개</text>
    </g>

    <g class="pm-pros">
      <text x="450" y="290" text-anchor="middle" class="pm-sec-label">장점</text>
      <text x="450" y="310" text-anchor="middle" class="pm-line">• 스레드 생성 극히 저렴</text>
      <text x="450" y="328" text-anchor="middle" class="pm-line">• 수십만 개 가능</text>
      <text x="450" y="346" text-anchor="middle" class="pm-line">• 사용자 스케줄러 자유</text>
    </g>
    <g class="pm-cons">
      <text x="450" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">단점</text>
      <text x="450" y="400" text-anchor="middle" class="pm-line">• 병렬성 없음 (코어 1개만)</text>
      <text x="450" y="418" text-anchor="middle" class="pm-line">• 블로킹 syscall = 전체 멈춤</text>
      <text x="450" y="436" text-anchor="middle" class="pm-line">• 현재는 거의 쓰이지 않음</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="600" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="735" y="80" text-anchor="middle" class="pm-heading">M:N (다대다)</text>
    <text x="735" y="100" text-anchor="middle" class="pm-sub">Go, Erlang, 옛 Solaris</text>

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
      <text x="735" y="290" text-anchor="middle" class="pm-sec-label">장점</text>
      <text x="735" y="310" text-anchor="middle" class="pm-line">• 스레드 저렴 + 병렬성</text>
      <text x="735" y="328" text-anchor="middle" class="pm-line">• 둘의 장점 결합</text>
      <text x="735" y="346" text-anchor="middle" class="pm-line">• 수백만 개 goroutine 가능</text>
    </g>
    <g class="pm-cons">
      <text x="735" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">단점</text>
      <text x="735" y="400" text-anchor="middle" class="pm-line">• 런타임 구현 복잡</text>
      <text x="735" y="418" text-anchor="middle" class="pm-line">• 스케줄링 공정성 이슈</text>
      <text x="735" y="436" text-anchor="middle" class="pm-line">• 디버깅 까다로움</text>
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

### 1:1 모델 — 현대 Linux/Windows의 선택

**1:1 모델**에서는 유저가 만든 스레드 하나가 곧 커널 스레드 하나입니다. `pthread_create()`가 내부적으로 `clone()` 시스템 콜을 호출해 커널이 관리하는 태스크를 직접 만듭니다.

**Linux NPTL (Native POSIX Thread Library)**:
Linux 2.6부터 glibc의 pthread 구현은 NPTL을 사용하고, NPTL은 1:1 모델입니다. 이전에는 **LinuxThreads**라는 비표준 1:1 구현이 있었는데, NPTL이 POSIX 준수 + 성능으로 대체했습니다.

**Windows**:
`CreateThread()`는 커널의 `KTHREAD`를 직접 만듭니다. 역시 1:1.

**장점**: 스레드가 블로킹되어도 다른 스레드는 계속 돌아감. 멀티코어에서 자동 분산.

**단점**: 스레드 생성 비용이 비교적 크고, 수만~수십만 개가 되면 커널 메모리 압박.

### N:1 모델 — 과거의 유산

**N:1 모델**에서는 여러 유저 스레드가 커널 스레드 하나에 매핑됩니다. 커널은 "이 프로세스에 스레드가 여럿 있다"는 걸 모릅니다 — 프로세스 하나로만 봅니다.

이 모델은 Java의 초기 "그린 스레드", GNU Pth 같은 라이브러리에서 사용됐습니다. 1990년대 초반에는 표준이었지만, **치명적 단점** 때문에 거의 사라졌습니다:

- **블로킹 시스템 콜이 전체를 멈춤**: 유저 스레드 하나가 `read()`로 블록되면, 같은 커널 스레드를 공유하는 모든 유저 스레드가 멈춤
- **멀티코어를 못 씀**: 커널 스레드 하나는 CPU 코어 하나에만 할당됨

### M:N 모델 — Go의 선택

**M:N 모델**은 두 모델의 장점을 합칩니다. M개의 유저 스레드가 N개의 커널 스레드 풀에 동적으로 매핑됩니다 (보통 N = CPU 코어 수).

**대표 구현**:
- **Go goroutine**: Go 런타임이 M:N 스케줄러. 수백만 goroutine을 수 개의 OS 스레드로 돌림
- **Erlang/Elixir**: BEAM VM이 자체 스케줄러 구현
- **옛 Solaris** (Solaris 2~8): 표준 POSIX pthreads를 M:N으로 구현했지만, 복잡성 때문에 Solaris 9에서 1:1로 전환

**이론적 배경** — Anderson 등의 1991년 SOSP 논문 [Scheduler Activations](https://dl.acm.org/doi/10.1145/121132.121151): "유저 레벨 스레드 라이브러리가 커널과 협력해 M:N을 효율적으로 구현하려면 어떤 커널 지원이 필요한가"를 다뤘습니다. 핵심은 **블로킹 시스템 콜 시 커널이 유저 스케줄러를 깨워 다른 유저 스레드를 다른 커널 스레드에 할당하게 해야 한다**는 것.

Go 런타임은 이와 유사한 아이디어를 구현합니다. goroutine이 blocking syscall을 부르려 하면 런타임이 그것을 감지해 **그 goroutine을 다른 커널 스레드에 이식**하거나, 새 커널 스레드를 만듭니다. 그래서 `net.Listen`이 블록되어도 다른 goroutine이 영향받지 않습니다.

### 게임 개발 입장에서

Unity, Unreal이 쓰는 스레드는 **C++/C# 수준에서는 1:1 모델**입니다. `new Thread()`나 `std::thread`가 커널 스레드를 직접 만듭니다.

그러나 **엔진 내부의 Job 시스템이나 Task 그래프는 사실상 M:N 스케줄러**입니다. 프로그래머가 수천 개의 "Job"을 발행해도 실제로는 엔진이 만든 수 개의 워커 스레드에서 돌아갑니다. 이건 Part 7 (Part 13 Lock-free와 구조적 해결)에서 자세히 다룰 Unity Job System 설계와 직결됩니다.

---

## Part 5: 3-OS 스레드 API 비교

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

POSIX 표준 API. 내부적으로 `clone()` 시스템 콜을 호출. 공식적 이름은 "pthread"이지만, Linux man 페이지를 보면 실제로는 NPTL (glibc 구현) 문서입니다.

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

**왜 `CreateThread`가 아닌 `_beginthreadex`?** `CreateThread`는 CRT (C Runtime Library)의 초기화 상태를 건너뜁니다 — `errno`, `strtok` 같은 스레드 별 상태가 초기화되지 않아 문제가 생깁니다. `_beginthreadex`는 CRT와 함께 올바르게 초기화되므로 C/C++ 코드에서는 이쪽을 써야 합니다.

### macOS — pthreads + libdispatch

```c
/* POSIX 방식 — Linux와 동일 */
#include <pthread.h>
/* ... */

/* libdispatch (GCD) 방식 — macOS 권장 */
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

macOS에서도 pthreads는 지원되지만 Apple은 **GCD (Grand Central Dispatch)**를 권장합니다. 이유는 Part 7에서 다뤘습니다 — 스레드 수명을 수동 관리하지 않아도 됨, QoS 클래스로 P/E 코어 자동 활용, 예측 가능한 큐 추상화 등.

### C# — 언어 차원의 추상화

C#은 위 세 OS 모두에서 돕니다. .NET 런타임(CLR 또는 CoreCLR)이 OS 차이를 숨겨줍니다.

```csharp
using System;
using System.Threading;
using System.Threading.Tasks;

// 1) 가장 원시적인 방법 — 거의 안 씀
Thread t = new Thread(() => Console.WriteLine("Hello"));
t.Start();
t.Join();

// 2) ThreadPool — 스레드 재사용
ThreadPool.QueueUserWorkItem(_ => Console.WriteLine("Hello"));

// 3) Task / async-await — 현대적 권장
await Task.Run(() => HeavyComputation());

// 4) Parallel — 데이터 병렬성
Parallel.For(0, 100, i => ProcessItem(i));
```

내부적으로:
- Linux: libcoreclr이 `pthread_create()` 사용
- Windows: `CreateThread()` 사용
- macOS: `pthread_create()` 사용 (GCD는 직접 쓰지 않음)

**Unity의 특수성**: Unity는 `Thread` 사용을 제한적으로 권장합니다. 대신 Job System과 UniTask, Coroutine을 쓰라고 합니다. 이유는 Unity Engine API 대부분이 **main thread 외에서 호출하면 크래시**하기 때문입니다. (Part 13에서 자세히)

---

## Part 6: 컨텍스트 스위칭 — 왜 비싼가

### 컨텍스트 스위칭이란

CPU 코어 하나에서 스레드 여러 개를 번갈아 실행하려면, 현재 스레드의 상태를 저장하고 다음 스레드의 상태를 복원해야 합니다. 이것이 **컨텍스트 스위칭**입니다.

저장해야 하는 것:
- **CPU 레지스터**: RAX, RBX, …, RIP (프로그램 카운터), RSP (스택 포인터), 플래그 레지스터
- **부동소수점 레지스터**: XMM, YMM, ZMM (AVX 시대에는 수십 KB)
- **MMU 상태**: 프로세스가 바뀌면 **페이지 테이블 포인터** (x86의 CR3 레지스터) 교체 필요

### 컨텍스트 스위칭의 "숨은 비용"

레지스터 저장/복원은 사실 **빙산의 일각**입니다. 진짜 비싼 건 간접 효과입니다.

<div class="pt-ctx-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Context switch cost breakdown">
  <text x="450" y="28" text-anchor="middle" class="pc-title">컨텍스트 스위칭 — 직접 비용 vs 숨은 비용</text>

  <g class="pc-timeline">
    <line x1="60" y1="80" x2="840" y2="80" class="pc-line"/>
    <rect x="60" y="65" width="120" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="120" y="85" text-anchor="middle" class="pc-block-label">Thread A 실행</text>

    <rect x="180" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="220" y="80" text-anchor="middle" class="pc-block-label">스위치</text>
    <text x="220" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="260" y="65" width="260" height="30" rx="3" class="pc-block pc-block-b"/>
    <text x="390" y="85" text-anchor="middle" class="pc-block-label">Thread B 실행 (캐시 재구축 중)</text>

    <rect x="520" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="560" y="80" text-anchor="middle" class="pc-block-label">스위치</text>
    <text x="560" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="600" y="65" width="240" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="720" y="85" text-anchor="middle" class="pc-block-label">Thread A 실행 (캐시 재구축)</text>
  </g>

  <g class="pc-direct">
    <rect x="40" y="140" width="400" height="140" rx="8" class="pc-box pc-box-direct"/>
    <text x="240" y="162" text-anchor="middle" class="pc-box-heading">직접 비용 (시각적으로 보이는 부분)</text>
    <text x="55" y="190" class="pc-box-line">• 레지스터 저장 (~30개, ~수백 바이트)</text>
    <text x="55" y="210" class="pc-box-line">• SIMD 레지스터 저장 (AVX-512 시 수 KB)</text>
    <text x="55" y="230" class="pc-box-line">• 커널에 진입 → 스케줄러 실행 → 복귀</text>
    <text x="55" y="250" class="pc-box-line">• MMU 포인터 교체 (프로세스 간 스위치 시)</text>
    <text x="55" y="270" class="pc-box-line pc-box-sum">총 대략 <tspan class="pc-emph">1~10마이크로초</tspan> (하드웨어에 따라)</text>
  </g>

  <g class="pc-hidden">
    <rect x="460" y="140" width="400" height="200" rx="8" class="pc-box pc-box-hidden"/>
    <text x="660" y="162" text-anchor="middle" class="pc-box-heading">숨은 비용 (보이지 않는 부분)</text>
    <text x="475" y="190" class="pc-box-line">• <tspan class="pc-emph">TLB flush</tspan>: 프로세스 전환 시 주소 변환 캐시 비움</text>
    <text x="475" y="205" class="pc-box-line-sub">→ 수백~수천 사이클 재구축</text>
    <text x="475" y="225" class="pc-box-line">• <tspan class="pc-emph">CPU 캐시 오염</tspan>: Thread A가 쓰던 L1/L2 데이터가</text>
    <text x="475" y="240" class="pc-box-line-sub">Thread B 실행에 의해 밀려남</text>
    <text x="475" y="260" class="pc-box-line">• <tspan class="pc-emph">분기 예측기 오염</tspan>: 브랜치 히스토리가 뒤섞임</text>
    <text x="475" y="280" class="pc-box-line">• <tspan class="pc-emph">프리페처 상태 초기화</tspan></text>
    <text x="475" y="300" class="pc-box-line pc-box-sum">총 <tspan class="pc-emph">수십 마이크로초~수 밀리초</tspan>의</text>
    <text x="475" y="318" class="pc-box-line pc-box-sum">"이후 성능 저하"로 나타남</text>
  </g>

  <g class="pc-conclusion">
    <rect x="40" y="360" width="820" height="60" rx="8" class="pc-concl"/>
    <text x="450" y="385" text-anchor="middle" class="pc-concl-title">결론: 스레드를 너무 많이 만들면 CPU가 계속 스위칭만 하고 유용한 일은 못 한다</text>
    <text x="450" y="405" text-anchor="middle" class="pc-concl-sub">이를 방지하려면 (1) 스레드 수를 코어 수 근처로 유지, (2) Job/Task로 작업 단위를 쪼개 큐잉</text>
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

### TLB와 프로세스 간 스위치

**TLB (Translation Lookaside Buffer)**는 CPU 내부의 작은 캐시로, "가상 주소 → 물리 주소" 변환 결과를 저장합니다. L1 TLB는 보통 **64~128 엔트리** 정도입니다.

프로세스가 바뀌면 CR3 레지스터(페이지 테이블 베이스)가 바뀌고, TLB는 **완전히 flush** 됩니다 (PCID/ASID 최적화가 없다면). 그러면 이후 메모리 접근마다 페이지 테이블을 다시 거슬러 찾아야 합니다.

**스레드 간 스위치는 덜 비쌉니다** — 같은 주소 공간을 공유하므로 CR3가 바뀌지 않아 TLB flush도 없습니다. 이것이 "프로세스보다 스레드가 가볍다"는 말의 **구체적 근거** 중 하나입니다.

### 측정하기

Linux에서는 `perf stat`로 측정할 수 있습니다:

```bash
$ perf stat -e context-switches,cpu-migrations,cache-misses -p <PID> sleep 10

Performance counter stats for process id '1234':

     12,345      context-switches
        567      cpu-migrations
 10,234,567      cache-misses
```

macOS에서는 **Instruments**의 **System Trace** 템플릿으로 스레드 스케줄링과 컨텍스트 스위치를 마이크로초 단위로 관찰 가능합니다.

Windows에서는 **Xperf** 또는 **Windows Performance Analyzer**가 같은 역할.

### LaMarca & Ladner의 관찰

캐시 친화성 측면에서 [LaMarca & Ladner 1996 — "The Influence of Caches on the Performance of Heaps"](https://dl.acm.org/doi/10.1145/244851.244933) 같은 연구가 다뤘듯, 알고리즘의 **이론적 복잡도만으로는** 실제 성능을 예측할 수 없습니다. 같은 이치로, **스레드를 많이 만들수록 빨라질 것**이라는 순진한 기대는 캐시/TLB 비용 때문에 깨지기 쉽습니다.

"최적 스레드 수 = 코어 수"라는 규칙은 이 관찰에서 나옵니다. 그 이상은 컨텍스트 스위칭이 이득을 잠식합니다.

---

## Part 7: 게임 엔진의 실행 모델

이제 이론을 **게임 엔진**에 연결합니다.

### Unity — Main Thread의 강한 제약

Unity 개발자라면 "이 API는 메인 스레드에서만 호출할 수 있다"는 경고를 한 번쯤 봤을 겁니다. `Transform.position`, `GameObject.Instantiate()`, `Renderer.sharedMaterial` 등 대부분의 Unity Engine API가 메인 스레드 전용입니다.

**왜인가?**

Unity Engine은 C++로 작성됐고, 내부 자료 구조에 **락이 없습니다**. Unity 팀이 "모든 엔진 호출은 메인 스레드에서 온다"는 가정 하에 설계해서, 락 획득 오버헤드를 없앴습니다.

이것은 **의도적 트레이드오프**입니다:
- ✅ 엔진 호출이 매우 빠름 (락 없음)
- ❌ 멀티스레드 활용이 어려움

Unity의 해결책: **Job System + Burst + Native Containers**. 메인 스레드는 그대로 두고, **데이터 처리만 병렬화**하는 별도 레이어를 제공합니다. (Part 13에서 상세)

### Unreal Engine — Task Graph

Unreal Engine은 **Task Graph** 시스템을 씁니다. 게임 코드가 발행한 "태스크"들이 의존성 DAG를 이루고, 엔진이 워커 스레드 풀에 분배합니다.

Unreal의 워커 스레드 풀:
- **Game Thread**: 게임 로직 (Unity의 메인 스레드에 해당)
- **Render Thread**: 렌더링 명령 빌드
- **RHI Thread**: GPU 드라이버 호출
- **Worker Threads**: 나머지 범용 작업

태스크는 `ENamedThreads`로 실행될 스레드를 지정합니다. 예: `ENamedThreads::GameThread`, `ENamedThreads::AnyBackgroundHiPriTask`.

### Fiber — Naughty Dog의 접근

[Christian Gyrling의 GDC 2015 강연 "Parallelizing the Naughty Dog Engine Using Fibers"](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)은 **Fiber** 기반 엔진 설계로 유명합니다.

**Fiber**는 협력적 유저 레벨 스레드입니다. OS가 관여하지 않고 애플리케이션이 스스로 스위치합니다. 커널 스레드가 **한 명의 일꾼**이라면, 그 일꾼이 들고 있는 **여러 일거리**가 Fiber입니다.

- Fiber 생성 비용: 극히 저렴 (수 나노초)
- Fiber 스위치: 레지스터만 저장/복원, 커널 개입 없음
- 수천 개 발행 가능

Naughty Dog의 Last of Us 2는 이 시스템으로 PS4의 7코어를 안정적으로 활용했습니다. Fiber는 **M:N 모델의 한 형태**로 볼 수 있습니다 (Fiber = 유저 스레드, 커널 스레드 = 워커).

**Windows의 Fiber API**: `CreateFiber`, `SwitchToFiber`. macOS/Linux에서는 `ucontext.h`의 `makecontext/swapcontext` (레거시, 권장 안 됨) 또는 Boost.Context, `libco` 같은 라이브러리를 써야 합니다.

### 엔진 실행 모델 비교

<div class="pt-engine-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Game engine execution models">
  <text x="450" y="28" text-anchor="middle" class="pe-title">주요 엔진의 스레드 실행 모델</text>

  <g class="pe-unity">
    <rect x="30" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="165" y="85" text-anchor="middle" class="pe-heading">Unity</text>
    <rect x="50" y="105" width="230" height="40" rx="4" class="pe-main"/>
    <text x="165" y="128" text-anchor="middle" class="pe-main-label">Main Thread (고정)</text>
    <text x="165" y="168" text-anchor="middle" class="pe-note">대부분의 Engine API</text>
    <text x="165" y="185" text-anchor="middle" class="pe-note">Transform, GameObject 등</text>

    <line x1="50" y1="210" x2="280" y2="210" class="pe-sep"/>

    <text x="165" y="235" text-anchor="middle" class="pe-sub-label">Job System (별도 레이어)</text>
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
    <text x="165" y="370" text-anchor="middle" class="pe-key">철학: Engine 유지 + 데이터 병렬</text>
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

    <text x="450" y="290" text-anchor="middle" class="pe-note">Task Graph: 의존성 DAG</text>
    <text x="450" y="307" text-anchor="middle" class="pe-note">ENamedThreads로 타겟 지정</text>
    <text x="450" y="370" text-anchor="middle" class="pe-key">철학: 다중 Named Thread + 범용 풀</text>
  </g>

  <g class="pe-fiber">
    <rect x="600" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="735" y="85" text-anchor="middle" class="pe-heading">Fiber (Naughty Dog)</text>

    <text x="735" y="115" text-anchor="middle" class="pe-sub-label">워커 스레드 (코어 수만큼)</text>
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

    <text x="735" y="205" text-anchor="middle" class="pe-sub-label">Fiber Pool (수천 개)</text>
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

    <text x="735" y="275" text-anchor="middle" class="pe-note">Job = Fiber로 실행</text>
    <text x="735" y="292" text-anchor="middle" class="pe-note">협력적 스위치, 커널 개입 없음</text>
    <text x="735" y="309" text-anchor="middle" class="pe-note">대기 시 Fiber 교체만</text>
    <text x="735" y="370" text-anchor="middle" class="pe-key">철학: 유저 레벨 협력 스케줄링</text>
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

## Part 8: 실전 관찰 — 내 스레드는 어떻게 돌고 있는가

이론을 알고 나서 이제 **실제로 봅시다**. 세 OS 모두 프로세스와 스레드를 관찰하는 풍부한 도구를 제공합니다.

### Linux — /proc, ps, top

Linux에서는 모든 것이 `/proc` 가상 파일 시스템에 노출됩니다.

```bash
# 특정 프로세스의 스레드 목록
$ ls /proc/<PID>/task/
1234  1235  1236  ...

# 각 스레드의 상태
$ cat /proc/1234/task/1234/status
Name:   myapp
State:  R (running)
Tgid:   1234
Pid:    1234
Threads: 8

# 주소 공간 매핑
$ cat /proc/1234/maps
00400000-00452000 r-xp 00000000 08:01 12345 /usr/bin/myapp
00651000-00652000 r--p 00051000 08:01 12345 /usr/bin/myapp
7f1234000000-7f1234021000 r-xp 00000000 08:01 54321 /lib/x86_64-linux-gnu/libc.so.6
...
```

`top -H`로 스레드 단위 CPU 사용률을 볼 수 있습니다.

### macOS — Activity Monitor, ps, Instruments

Activity Monitor는 GUI 도구이지만, 더 정밀한 데이터는 CLI 도구에 있습니다.

```bash
# 프로세스 스레드 수 확인
$ ps -M <PID>

# 상세 정보
$ sample <PID> 5 -mayDie
```

**Instruments**의 **System Trace** 템플릿이 가장 강력합니다. P/E 코어별 실행 타임라인, 컨텍스트 스위치 이벤트, 블로킹 원인까지 다 보여줍니다. Apple Silicon 환경에서 특히 유용 — 어떤 스레드가 P-core에서 돌았고 어떤 스레드가 E-core로 밀렸는지 시각화됩니다.

### Windows — Process Explorer, WPA

**Process Explorer** (Sysinternals)는 작업 관리자의 강화판:
- 프로세스 트리 시각화
- 각 프로세스의 스레드 목록 + 스택 추적
- 핸들, DLL, 메모리 상세

**Windows Performance Analyzer (WPA)**는 Instruments에 해당. Xperf로 수집한 ETW 이벤트를 분석합니다.

### C#에서 스레드 다루기 — 코드 예시

```csharp
using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;

class ThreadInspector {
    static void Main() {
        Console.WriteLine($"현재 프로세스 ID: {Process.GetCurrentProcess().Id}");
        Console.WriteLine($"관리 스레드 ID: {Thread.CurrentThread.ManagedThreadId}");
        Console.WriteLine($"CPU 코어 수: {Environment.ProcessorCount}");

        // 스레드 생성 비용 측정
        var sw = Stopwatch.StartNew();
        var threads = new Thread[100];
        for (int i = 0; i < 100; i++) {
            threads[i] = new Thread(() => Thread.Sleep(1));
            threads[i].Start();
        }
        foreach (var t in threads) t.Join();
        sw.Stop();
        Console.WriteLine($"100개 스레드 생성+종료: {sw.ElapsedMilliseconds}ms");

        // ThreadPool.Queue는 훨씬 빠름
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
        Console.WriteLine($"100개 ThreadPool 작업: {sw.ElapsedMilliseconds}ms");
    }
}
```

실행 결과 (제 머신 기준 대략):
```
현재 프로세스 ID: 12345
관리 스레드 ID: 1
CPU 코어 수: 8
100개 스레드 생성+종료: 85ms
100개 ThreadPool 작업: 8ms
```

**10배 차이**. 이것이 스레드 풀을 쓰는 실용적 이유입니다. .NET의 `ThreadPool`, Java의 `ExecutorService`, C++의 `std::async` 모두 같은 아이디어입니다 — 스레드를 재사용해 생성 비용을 분할 상환.

---

## 정리

이 편에서 다룬 것:

**프로세스**:
- PCB (`task_struct`, `EPROCESS`, `proc`+`task`) — OS가 프로세스를 추적하는 구조
- 주소 공간 레이아웃: Text, Data, BSS, Heap, Stack, Kernel
- 프로세스 상태 전이: New, Ready, Running, Waiting, Terminated

**프로세스 생성**:
- Unix의 `fork() + exec()` — 2단계, Copy-on-Write로 실제로는 빠름
- Windows의 `CreateProcess()` — 1단계, 매개변수 많음
- macOS의 `posix_spawn()` — iOS 호환 + 더 효율적
- fork() 시 COW는 하드웨어 MMU 지원에 기반

**스레드**:
- 프로세스 vs 스레드: 주소 공간 공유 여부가 핵심
- 공유: Text, Data, Heap, 파일 디스크립터
- 전용: Stack, 레지스터, TLS
- Linux의 독특한 철학: 프로세스와 스레드를 같은 구조체로 표현 (`clone()`)

**스레드 매핑 모델**:
- 1:1 (Linux NPTL, Windows): 표준, 진정한 병렬
- N:1 (옛 그린 스레드): 거의 사장
- M:N (Go goroutine, Erlang): 수백만 동시 스레드, 런타임 구현 복잡

**컨텍스트 스위칭**:
- 직접 비용: 레지스터 저장/복원 ~1-10μs
- 숨은 비용: TLB flush, 캐시 오염, 분기 예측기 오염
- 프로세스 간 스위치가 스레드 간 스위치보다 비싸다 (CR3 교체)
- "스레드 수 = 코어 수" 원칙

**게임 엔진 실행 모델**:
- Unity: Main Thread 제약 + Job System (데이터 병렬화)
- Unreal: 여러 Named Thread + Task Graph
- Naughty Dog 엔진: Fiber 기반 협력적 스케줄링

다음 편은 **Part 9 스케줄링** — 여러 스레드가 준비 상태일 때 OS는 누구에게 CPU를 줄까요? Linux의 CFS → EEVDF, Windows의 priority boost, macOS의 QoS 기반 스케줄링을 살펴봅니다. 게임 프레임 예산 16.67ms와 priority inversion 문제도 다룹니다.

---

## References

### 교재
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.3 (Processes), Ch.4 (Threads)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — `task_struct`와 프로세스 관리 Ch.3
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — 현대 Linux 커널 내부
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — EPROCESS/ETHREAD 상세
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNU의 task/proc 이중 구조
- Butenhof — *Programming with POSIX Threads*, Addison-Wesley, 1997 — pthreads의 고전
- Stevens, Rago — *Advanced Programming in the UNIX Environment*, 3rd ed., Addison-Wesley, 2013 — fork/exec 실전
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 멀티프로세서 엔진 설계

### 논문
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — [DOI](https://dl.acm.org/doi/10.1145/121132.121151) — M:N 모델의 이론적 기초
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — 컨텍스트 스위치의 숨은 비용 측정
- Engelschall — "Portable Multithreading: The Signal Stack Trick for User-Space Thread Creation", USENIX 2000 — 유저 레벨 스레드 구현
- Kleiman, Smaalders — "The LWP Framework: Building and Debugging Mach Tasks and Threads", Mach Workshop 1990 — Mach의 스레드 모델

### 공식 문서
- Linux man pages — `clone(2)`, `fork(2)`, `pthread_create(3)`, `proc(5)` — [man7.org](https://man7.org/linux/man-pages/)
- Apple Developer — *Threading Programming Guide* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/Introduction/Introduction.html)
- Apple Developer — *Dispatch* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Microsoft Docs — *Processes and Threads* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/processes-and-threads)
- Microsoft Docs — *Fibers* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/fibers)
- Go Runtime — *The Go Scheduler* (Dmitry Vyukov) — [morsmachine.dk/go-scheduler](https://morsmachine.dk/go-scheduler)

### 게임 개발 / GDC 자료
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Unity Technologies — *C# Job System manual* — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Unreal Engine Documentation — *Task Graph System* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)

### 블로그 / 기사
- Raymond Chen — *The Old New Thing* — Win32 CreateProcess 내부
- Linus Torvalds — comp.os.minix 스레드 관련 초기 논의 (1992)
- Dmitry Vyukov — *1024cores.net* — 무잠금 동시성 자료 (Go scheduler 내부 포함)
- Howard Oakley — *The Eclectic Light Company* — macOS 스레드 관찰 기법

### 도구
- Linux: `ps`, `top`, `htop`, `strace`, `perf`, `ftrace`
- macOS: Activity Monitor, `ps`, `sample`, Instruments (System Trace, Time Profiler)
- Windows: Task Manager, Process Explorer, WPA, PerfView
- 크로스플랫폼: Tracy Profiler — 게임에 임베드하기 좋음
