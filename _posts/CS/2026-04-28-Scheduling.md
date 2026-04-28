---
title: "CS 로드맵 9편 — 스케줄링: OS는 누구에게 CPU를 줄까"
date: 2026-04-27 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, scheduler, cfs, eevdf, qos, frame-budget, game-engine]
toc: true
toc_sticky: true
math: true
difficulty: intermediate
prerequisites:
  - /posts/OSArchitecture/
  - /posts/ProcessAndThread/
tldr:
  - 스케줄러의 두 결정은 "누구에게 CPU를 줄까"와 "얼마나 오래"이며, 평가 기준은 Throughput·Latency·Fairness·Response time입니다
  - Linux는 O(n) → O(1) → CFS (2007) → EEVDF (2024)로 진화했습니다. CFS는 vruntime이 가장 작은 스레드를 RB-tree에서 항상 선택하고, EEVDF는 eligibility와 deadline 축을 추가해 지연 민감 작업을 더 잘 다룹니다
  - Windows는 32단계 priority + 동적 boost(전경 창, I/O 완료, GUI 입력)로 응답성을 높이고, macOS는 5단계 QoS로 우선순위·P/E 코어 배정·전력 관리를 한 번에 결정합니다
  - 60fps 16.67ms, 120fps 8.33ms 안에 입력→로직→물리→렌더→present가 끝나야 하며, priority inversion 한 번이 프레임 드랍의 원인이 됩니다
  - Unity Job priority, Unreal TaskGraph named thread, SetThreadPriority / pthread / dispatch_qos는 같은 OS 스케줄러 위에서 다른 추상화를 제공할 뿐입니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: "누가, 얼마나"의 문제

[지난 편](/posts/ProcessAndThread/)에서는 프로세스와 스레드가 무엇이고 OS가 그것을 어떻게 추상화하는지 보았습니다. 이제 자연스럽게 따라오는 질문이 있습니다.

> **준비 상태인 스레드가 100개 있는데 코어가 8개라면, OS는 누구에게 CPU를 줄까요? 그리고 얼마나 오래 줄까요?**

이 두 질문에 답하는 것이 **스케줄러 (Scheduler)** 입니다. 그리고 이 답이 다음 두 가지를 결정합니다.

- **체감 응답성**: 클릭하고 0.1초 안에 반응하는가, 1초가 걸리는가
- **프레임 안정성**: 게임이 60fps를 유지하는가, 17ms를 가끔 넘기는가

이번 편에서 다루는 내용은 다음과 같습니다.

- **스케줄링 기초**: Preemptive vs Cooperative, Throughput·Latency·Fairness·Response의 트레이드오프
- **고전 알고리즘**: FCFS, SJF, RR, Priority, MLFQ
- **Linux**: O(n) → O(1) → **CFS** → **EEVDF**의 진화
- **Windows**: 32단계 priority, dynamic boost, foreground quantum stretch
- **macOS**: **QoS** 기반 스케줄링과 Apple Silicon P/E 코어 배정
- **게임 프레임 예산**: 16.67ms를 채우는 일들과 priority inversion
- **게임 엔진의 우선순위·친화성 활용**: Unity, Unreal, 그리고 OS API 레벨

Stage 2의 핵심 질문 — *"스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?"* — 의 "**때때로**"라는 단어가 결국 스케줄러의 동작에서 나옵니다. 어떤 순서로, 어떤 간격으로 실행이 섞이는지가 보이지 않는 곳에서 결정되고 있다는 뜻이기 때문입니다.

---

## Part 1: 스케줄링이 필요한 이유

### 멀티태스킹의 환상

데스크톱에 브라우저, IDE, Slack, Spotify, Discord가 동시에 떠 있습니다. 코어는 8개이고, 프로세스와 스레드는 합쳐서 보통 수백 개 수준입니다. 그런데도 모두 "동시에" 동작하는 것처럼 보입니다.

실제로는 OS가 매우 빠른 속도로 스레드를 갈아끼우고 있을 뿐입니다. 한 스레드가 몇 밀리초 동안 코어를 잡고, 다음 스레드로 넘어가고, 또 그 다음 스레드로 넘어갑니다. 인간의 인지 한계(약 50ms) 보다 훨씬 짧은 단위로 갈아끼우면 동시 실행처럼 느껴집니다.

이 갈아끼우기를 결정하는 것이 **스케줄러**이며, 두 가지 질문에 답합니다.

1. **누구에게 줄까** — 준비 상태(Ready)인 스레드 중 어떤 것을 골라 코어에 올릴 것인가
2. **얼마나 오래** — 한 번 올렸으면 언제 다시 빼앗을 것인가, 혹은 빼앗을 수 있는가

### Preemptive vs Cooperative

**선점형 (Preemptive)**: 스케줄러가 스레드를 강제로 빼앗을 수 있습니다. 타이머 인터럽트가 주기적으로 발생하면 커널이 깨어나 "다음은 누구인가"를 결정합니다. 현대의 거의 모든 OS — Linux, Windows, macOS — 가 이 방식입니다.

**협력형 (Cooperative)**: 스레드가 스스로 양보(`yield`)하기 전까지 계속 돕니다. 80년대 Mac, 95 이전 Windows, 그리고 현재의 일부 코루틴/Fiber 시스템이 이 방식입니다. 한 스레드가 무한 루프를 돌면 시스템이 같이 멈춥니다 — 옛 "Mac 폭탄 아이콘"의 한 원인이었습니다.

> **잠깐, 이건 짚고 넘어갑시다.** 그럼 Goroutine이나 async/await는 cooperative입니까?
>
> Go의 goroutine은 **부분적으로 cooperative**입니다. 함수 호출, 채널 연산, GC 안전점에서만 양보 지점이 생깁니다. 그래서 무한 루프 안에 함수 호출이 없으면 다른 goroutine이 굶을 수 있었고, Go 1.14에서야 비동기 선점이 도입됐습니다. async/await도 마찬가지로 `await` 지점에서만 양보합니다 — 다만 그 위에서 실제 스레드는 OS의 선점형 스케줄러로 돌기 때문에, 두 계층이 겹쳐 있는 셈입니다.

### 스케줄러의 평가 기준

스케줄러를 설계할 때 고려해야 할 지표는 여러 개이고, 서로 충돌합니다.

| 지표 | 의미 | 누가 좋아하는가 |
|------|------|----------------|
| Throughput | 단위 시간당 완료 작업 수 | 배치 처리, 빌드 서버 |
| Turnaround time | 작업 전체 소요 시간 | 컴파일러, 데이터 처리 |
| Waiting time | Ready 큐에서 기다린 시간 | 모든 작업 |
| Response time | 입력에서 첫 반응까지 | 데스크톱, 게임 |
| Fairness | 자원의 공평한 분배 | 다중 사용자 시스템 |
| Predictability | 예측 가능한 지연 | 실시간 시스템, 게임 |
| Energy | 전력 효율 | 모바일, 노트북 |

데스크톱과 모바일은 보통 **Response time + Energy**를 우선합니다. 서버는 **Throughput + Fairness**, 실시간/게임은 **Predictability**를 우선합니다. 같은 알고리즘이 모든 환경에 최적일 수 없는 이유입니다.

---

## Part 2: 고전 스케줄링 알고리즘

본격적인 OS 스케줄러를 보기 전에 교과서적 알고리즘 다섯 개를 짚어보겠습니다. 현대 스케줄러는 모두 이 아이디어들의 조합·진화체입니다.

### FCFS (First-Come, First-Served)

가장 단순합니다. 도착한 순서대로 실행하며, 한 번 시작하면 끝날 때까지 빼앗지 않습니다 (non-preemptive).

문제는 **convoy effect**입니다. 100초짜리 작업이 먼저 들어오면 그 뒤의 0.1초짜리 작업들이 모두 100초씩 기다려야 합니다. 평균 대기시간이 폭발합니다.

### SJF / SRTF (Shortest Job First / Shortest Remaining Time First)

가장 짧은 작업을 먼저 실행합니다. **평균 대기시간이 이론적으로 최적**임이 수학적으로 증명되어 있습니다.

문제 1: **작업의 길이를 미리 알아야 합니다**. 실제로는 알 수 없으므로 과거 실행 이력으로 추정합니다.
문제 2: **starvation** — 짧은 작업이 계속 들어오면 긴 작업은 영원히 시작하지 못할 수 있습니다.

### Round Robin (RR)

준비 큐를 순환하며 각 스레드에 **타임 퀀텀 (time quantum)** 만큼 CPU를 줍니다. 퀀텀이 끝나면 큐의 뒤로 보내고 다음 스레드로 넘어갑니다.

타임 퀀텀의 크기가 핵심 파라미터입니다.

- **너무 크면**: FCFS와 비슷해지고 응답성이 나빠집니다
- **너무 작으면**: 컨텍스트 스위치 오버헤드가 작업 시간을 잡아먹습니다

전형적인 값은 10~100ms입니다. Linux는 동적으로 결정하고(CFS), Windows는 약 6ms(서버는 12ms 이상)입니다.

다음 다이어그램은 같은 작업 셋(A=8ms, B=4ms, C=2ms)이 동시에 도착했을 때 FCFS와 RR의 동작을 비교합니다.

<div class="sk-tl">
  <div class="sk-tl-title">FCFS vs Round Robin (quantum 2ms)</div>

  <div class="sk-tl-row">
    <div class="sk-tl-label">FCFS</div>
    <div class="sk-tl-track">
      <div class="sk-tl-blk sk-tl-a" style="flex: 8">A (8ms)</div>
      <div class="sk-tl-blk sk-tl-b" style="flex: 4">B (4ms)</div>
      <div class="sk-tl-blk sk-tl-c" style="flex: 2">C (2ms)</div>
    </div>
    <div class="sk-tl-axis">
      <span>0</span><span>8</span><span>12</span><span>14</span>
    </div>
    <div class="sk-tl-meta">평균 turnaround = (8 + 12 + 14) / 3 = 11.33ms · C 응답시간 12ms</div>
  </div>

  <div class="sk-tl-divider"></div>

  <div class="sk-tl-row">
    <div class="sk-tl-label">RR (q=2)</div>
    <div class="sk-tl-track">
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-b" style="flex: 2">B</div>
      <div class="sk-tl-blk sk-tl-c sk-tl-done" style="flex: 2">C ✓</div>
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-b sk-tl-done" style="flex: 2">B ✓</div>
      <div class="sk-tl-blk sk-tl-a" style="flex: 2">A</div>
      <div class="sk-tl-blk sk-tl-a sk-tl-done" style="flex: 2">A ✓</div>
    </div>
    <div class="sk-tl-axis">
      <span>0</span><span>2</span><span>4</span><span>6</span><span>8</span><span>10</span><span>12</span><span>14</span>
    </div>
    <div class="sk-tl-meta">C 응답시간 4ms (FCFS의 1/3) · 평균 turnaround = (14 + 8 + 6) / 3 = 9.33ms</div>
  </div>

  <div class="sk-tl-legend">
    <span class="sk-tl-lg sk-tl-a"></span>A (8ms)
    <span class="sk-tl-lg sk-tl-b"></span>B (4ms)
    <span class="sk-tl-lg sk-tl-c"></span>C (2ms)
    <span class="sk-tl-note">✓ 작업 완료 시점</span>
  </div>

  <div class="sk-tl-foot">RR은 turnaround에서 항상 우월하지는 않지만, 짧은 작업의 응답성과 공정성에서 압도적입니다.</div>

<style>
.sk-tl { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-tl-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-tl-row { margin: 14px 0; }
.sk-tl-label { font-weight: 700; color: #2d3748; font-size: 12px; margin-bottom: 6px; }
.sk-tl-track { display: flex; height: 38px; border: 1px solid #cbd5e0; border-radius: 4px; overflow: hidden; }
.sk-tl-blk { display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.1); }
.sk-tl-blk:last-child { border-right: 0; }
.sk-tl-a { background: #fed7d7; }
.sk-tl-b { background: #c6f6d5; }
.sk-tl-c { background: #bee3f8; }
.sk-tl-done { box-shadow: inset 0 0 0 2px #2d3748; }
.sk-tl-axis { display: flex; justify-content: space-between; margin-top: 4px; padding: 0 2px; font-family: monospace; font-size: 10px; color: #718096; }
.sk-tl-meta { margin-top: 6px; font-size: 11px; color: #2b6cb0; font-weight: 600; }
.sk-tl-divider { height: 1px; background: #cbd5e0; margin: 18px 0; border-top: 1px dashed #cbd5e0; background: none; }
.sk-tl-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 14px; font-size: 11px; color: #4a5568; }
.sk-tl-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid #cbd5e0; vertical-align: middle; margin-right: 4px; }
.sk-tl-note { margin-left: auto; color: #718096; }
.sk-tl-foot { margin-top: 12px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-tl { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-tl-title { color: #e2e8f0; }
[data-mode="dark"] .sk-tl-label { color: #e2e8f0; }
[data-mode="dark"] .sk-tl-track { border-color: #4a5568; }
[data-mode="dark"] .sk-tl-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.08); }
[data-mode="dark"] .sk-tl-a { background: #742a2a; }
[data-mode="dark"] .sk-tl-b { background: #22543d; }
[data-mode="dark"] .sk-tl-c { background: #2a4365; }
[data-mode="dark"] .sk-tl-done { box-shadow: inset 0 0 0 2px #f7fafc; }
[data-mode="dark"] .sk-tl-axis { color: #a0aec0; }
[data-mode="dark"] .sk-tl-meta { color: #63b3ed; }
[data-mode="dark"] .sk-tl-divider { border-top-color: #4a5568; }
[data-mode="dark"] .sk-tl-legend { color: #cbd5e0; }
[data-mode="dark"] .sk-tl-lg { border-color: #4a5568; }
[data-mode="dark"] .sk-tl-note { color: #a0aec0; }
[data-mode="dark"] .sk-tl-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-tl { padding: 14px 12px 12px; }
  .sk-tl-title { font-size: 13px; }
  .sk-tl-blk { font-size: 9.5px; }
  .sk-tl-axis { font-size: 9px; }
  .sk-tl-meta { font-size: 10px; }
  .sk-tl-legend { font-size: 10px; gap: 6px; }
  .sk-tl-foot { font-size: 10px; }
}
</style>
</div>

### Priority Scheduling

각 스레드에 **우선순위**를 매기고 가장 높은 것부터 실행합니다. 같은 우선순위끼리는 RR로 처리합니다.

문제는 다시 **starvation**입니다. 낮은 우선순위 스레드가 영원히 돌지 못할 수 있습니다. 해결책 중 하나가 **aging**으로, 오래 기다린 스레드의 우선순위를 점진적으로 올려 줍니다.

또 다른 깊은 문제가 **priority inversion**입니다. 낮은 우선순위 스레드가 잠금을 잡고 있는 동안 높은 우선순위 스레드가 그 잠금을 기다리면, 중간 우선순위 스레드가 낮은 쪽을 끊임없이 선점하면서 결과적으로 **높은 쪽이 중간 쪽 때문에 막히는** 역설이 생깁니다. 이 문제는 다음 편(동기화)에서 본격적으로 다룹니다.

### MLFQ (Multi-Level Feedback Queue)

여러 개의 큐를 우선순위별로 두고, 스레드의 **행동을 관찰해 큐를 옮깁니다**.

기본 규칙은 다음과 같습니다.

1. 새 스레드는 가장 높은 큐에 들어갑니다
2. 타임 퀀텀을 다 쓰면 한 단계 낮은 큐로 내려갑니다
3. 퀀텀을 다 쓰지 않고 I/O로 양보하면 같은 큐에 남거나 한 단계 올라갑니다

이 규칙의 결과가 흥미롭습니다.

- I/O 위주 작업(대화형 GUI, 게임 입력): 짧은 burst 후 양보 → 높은 큐 유지 → 빠른 응답
- CPU 위주 작업(컴파일러, 인코딩): 긴 burst → 낮은 큐로 내려감 → 응답 작업을 방해하지 않음

알고리즘이 작업의 본질을 모르더라도 **행동만 보고 분류**한다는 발상이 핵심입니다. Windows의 dynamic boost, macOS의 QoS 보정, Linux의 sleeper bonus 모두 본질적으로 같은 아이디어의 변형입니다.

> MLFQ는 Solaris와 옛 Mac OS, Windows NT가 직접 사용했고, 현대 OS는 표면적으로 다른 알고리즘(CFS 등)을 쓰지만 내부 휴리스틱은 MLFQ와 닮아 있습니다.

---

## Part 3: Linux 스케줄러 — O(n) → O(1) → CFS → EEVDF

Linux 스케줄러의 진화는 학습용으로 더할 나위 없습니다. 같은 문제를 네 번 다시 풀면서 **무엇이 잘못되었고, 어떻게 고쳤는가**가 모두 공개되어 있기 때문입니다.

### O(n) 스케줄러 — 2.4 이전

초기 Linux 스케줄러는 한 번 결정할 때마다 **전체 Ready 큐를 순회**했습니다. 코어가 적고 프로세스가 적던 시절에는 문제가 없었지만, 서버가 수천 프로세스를 띄우는 시대가 오자 스케줄러 자체가 병목이 됐습니다. CPU 코어를 추가해도 락 경합이 심해 성능이 늘지 않았습니다.

### O(1) 스케줄러 — 2.6 (Ingo Molnár, 2003)

**Ingo Molnár**가 2002년 말에 도입한 알고리즘입니다.

핵심 아이디어는 다음과 같습니다.

- **140개의 우선순위 큐** (실시간 0~99, 일반 100~139)
- 각 우선순위마다 active queue와 expired queue 한 쌍
- 다음 실행 스레드를 **상수 시간**에 결정 — 비트맵에서 가장 높은 비트만 찾으면 되기 때문

또한 **대화형 작업 보너스**를 휴리스틱으로 도입했습니다. sleep 시간이 길수록 우선순위를 살짝 올려 데스크톱 응답성을 개선했습니다. 그러나 이 휴리스틱이 점점 복잡해졌고, 보너스 계산을 농락하는 워크로드가 발견되면서 코드가 누더기가 됐습니다.

### CFS — Completely Fair Scheduler (2.6.23, 2007)

**Ingo Molnár가 다시** 만든 스케줄러입니다. 영감은 **Con Kolivas**의 RSDL (Rotating Staircase Deadline) 패치에서 받았다고 본인이 밝혔습니다.

핵심 발상은 "공정성"을 단순한 회전이 아니라 **누적 실행시간의 균형**으로 정의하는 것입니다. 모든 스레드는 자기가 받았어야 할 가상의 CPU 시간 — `vruntime` — 을 가지며, 스케줄러는 항상 **vruntime이 가장 작은 스레드**를 선택합니다.

가상 실행시간(`vruntime`)은 실제 실행시간(`runtime`)을 weight로 보정한 값입니다.

$$
\Delta \text{vruntime} = \Delta \text{runtime} \times \frac{w_0}{w}
$$

여기서 $w$는 스레드의 weight(nice 값으로 결정)이고, $w_0$은 nice 0의 기준 weight(1024)입니다. nice가 음수일수록(우선순위가 높을수록) weight가 커지고, vruntime이 천천히 증가하므로 자주 선택됩니다.

**자료구조**는 Red-Black Tree이고, 키는 vruntime입니다. 가장 왼쪽 노드(최소 vruntime)가 다음 실행 대상이며, 삽입·삭제·선택 모두 $O(\log n)$입니다. O(1) 보다 점근적으로 느리지만 실측에서는 n이 작아 차이가 거의 없고, 휴리스틱이 사라져 코드가 훨씬 깔끔해졌습니다.

다음 다이어그램은 CFS의 핵심 사이클입니다. RB-tree에서 vruntime이 가장 작은 스레드를 뽑아 실행하고, 일정 시간 뒤 갱신된 vruntime으로 다시 트리에 넣습니다.

<div class="sk-cfs">
  <div class="sk-cfs-title">CFS — vruntime 정렬과 실행 사이클</div>

  <div class="sk-cfs-rq-label">runqueue (key = vruntime, leftmost가 다음 실행 대상)</div>
  <div class="sk-cfs-rq">
    <div class="sk-cfs-node sk-cfs-pick">
      <div class="sk-cfs-tname">T0</div>
      <div class="sk-cfs-tvrun">v=18</div>
      <div class="sk-cfs-pickmark">leftmost ← next</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T1</div>
      <div class="sk-cfs-tvrun">v=30</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T2</div>
      <div class="sk-cfs-tvrun">v=35</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T3</div>
      <div class="sk-cfs-tvrun">v=42</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T4</div>
      <div class="sk-cfs-tvrun">v=50</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T5</div>
      <div class="sk-cfs-tvrun">v=58</div>
    </div>
    <div class="sk-cfs-node">
      <div class="sk-cfs-tname">T6</div>
      <div class="sk-cfs-tvrun">v=72</div>
    </div>
  </div>

  <div class="sk-cfs-flow">
    <div class="sk-cfs-step sk-cfs-step-pick">pick_next_task<br><span>(leftmost = T0)</span></div>
    <div class="sk-cfs-arrow">→</div>
    <div class="sk-cfs-step sk-cfs-step-run">CPU 실행<br><span>vruntime += Δ × w₀ / w_T0</span></div>
    <div class="sk-cfs-arrow">→</div>
    <div class="sk-cfs-step sk-cfs-step-back">enqueue_task<br><span>갱신된 v로 RB-tree 재삽입</span></div>
  </div>

  <div class="sk-cfs-formula">
    Δvruntime = Δruntime × (w₀ / w) &nbsp;·&nbsp; w₀ = 1024 (nice 0) &nbsp;·&nbsp; nice ↓ → w ↑ → Δv ↓ → 자주 선택
  </div>
  <div class="sk-cfs-foot">결국 모든 스레드의 vruntime이 거의 같게 유지되도록 자가 균형 — 이것이 "Completely Fair"의 의미입니다.</div>

<style>
.sk-cfs { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-cfs-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-cfs-rq-label { font-size: 12px; font-weight: 700; color: #4a5568; margin-bottom: 8px; }
.sk-cfs-rq { display: flex; gap: 6px; flex-wrap: wrap; padding: 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sk-cfs-node { flex: 1; min-width: 70px; padding: 10px 8px; border: 1.5px solid #4a5568; border-radius: 6px; background: #edf2f7; text-align: center; position: relative; }
.sk-cfs-pick { background: #38a169; border-color: #276749; color: #fff; }
.sk-cfs-tname { font-weight: 700; font-size: 13px; }
.sk-cfs-tvrun { font-family: monospace; font-size: 11px; opacity: 0.85; }
.sk-cfs-pick .sk-cfs-tvrun { color: #fff; opacity: 1; }
.sk-cfs-pickmark { position: absolute; top: 100%; left: 50%; transform: translateX(-50%); margin-top: 4px; font-size: 10px; font-weight: 700; color: #38a169; white-space: nowrap; }
.sk-cfs-flow { display: flex; align-items: stretch; gap: 8px; margin: 32px 0 14px; flex-wrap: wrap; }
.sk-cfs-step { flex: 1; min-width: 130px; padding: 10px 12px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 12px; }
.sk-cfs-step span { display: block; margin-top: 4px; font-weight: 400; font-size: 10.5px; font-family: monospace; opacity: 0.8; }
.sk-cfs-step-pick { background: #ebf8ff; color: #2c5282; border: 1px solid #3182ce; }
.sk-cfs-step-run { background: #faf5ff; color: #553c9a; border: 1px solid #805ad5; }
.sk-cfs-step-back { background: #fefcbf; color: #744210; border: 1px solid #d69e2e; }
.sk-cfs-arrow { display: flex; align-items: center; justify-content: center; font-size: 18px; color: #4a5568; font-weight: 700; }
.sk-cfs-formula { padding: 10px 14px; background: #f7fafc; border: 1px dashed #cbd5e0; border-radius: 6px; font-family: monospace; font-size: 12px; color: #2d3748; text-align: center; font-weight: 600; }
.sk-cfs-foot { margin-top: 8px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-cfs { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-cfs-title { color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-rq-label { color: #cbd5e0; }
[data-mode="dark"] .sk-cfs-rq { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-cfs-node { background: #2d3748; border-color: #718096; color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-pick { background: #38a169; border-color: #2f855a; color: #fff; }
[data-mode="dark"] .sk-cfs-pickmark { color: #68d391; }
[data-mode="dark"] .sk-cfs-step-pick { background: #2a4365; color: #bee3f8; border-color: #63b3ed; }
[data-mode="dark"] .sk-cfs-step-run { background: #322659; color: #d6bcfa; border-color: #b794f4; }
[data-mode="dark"] .sk-cfs-step-back { background: #744210; color: #fefcbf; border-color: #ecc94b; }
[data-mode="dark"] .sk-cfs-arrow { color: #a0aec0; }
[data-mode="dark"] .sk-cfs-formula { background: #2d3748; border-color: #4a5568; color: #e2e8f0; }
[data-mode="dark"] .sk-cfs-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-cfs { padding: 14px 12px 12px; }
  .sk-cfs-title { font-size: 13px; }
  .sk-cfs-node { min-width: 56px; padding: 6px 4px; }
  .sk-cfs-tname { font-size: 11px; }
  .sk-cfs-tvrun { font-size: 9.5px; }
  .sk-cfs-pickmark { font-size: 9px; }
  .sk-cfs-step { font-size: 11px; min-width: 100px; padding: 8px; }
  .sk-cfs-step span { font-size: 9.5px; }
  .sk-cfs-arrow { font-size: 14px; }
  .sk-cfs-formula { font-size: 10.5px; padding: 8px 10px; }
  .sk-cfs-foot { font-size: 10px; }
}
</style>
</div>

CFS의 핵심 파라미터는 다음과 같습니다.

- `sched_latency_ns` — 한 주기 동안 모든 Ready 스레드를 한 번씩 돌리려는 목표 시간 (기본 6ms × 코어 수)
- `sched_min_granularity_ns` — 한 스레드가 한 번에 도는 최소 시간 (기본 0.75ms)
- `sched_wakeup_granularity_ns` — 깨어난 스레드가 현재 스레드를 선점하기 위한 vruntime 차이 임계값

값은 `sysctl -a | grep sched`로 확인할 수 있고, 코어 수에 따라 자동 조정됩니다.

```c
/* 단순화한 CFS 선택 로직 */
struct task_struct *pick_next_task_fair(struct rq *rq) {
    struct cfs_rq *cfs_rq = &rq->cfs;
    struct sched_entity *se = __pick_first_entity(cfs_rq);  /* RB-tree leftmost */
    return container_of(se, struct task_struct, se);
}

/* tick마다 호출 — vruntime 갱신 후 재배치 */
void update_curr(struct cfs_rq *cfs_rq) {
    struct sched_entity *curr = cfs_rq->curr;
    u64 delta_exec = now - curr->exec_start;
    curr->vruntime += calc_delta_fair(delta_exec, curr);
    /* 선점 조건이 맞으면 resched_curr() */
}
```

### EEVDF — Earliest Eligible Virtual Deadline First (6.6, 2023~2024)

CFS를 16년간 잘 썼는데도 한 가지 구조적 문제가 남아 있었습니다. **latency-sensitive 작업의 표현이 어렵다**는 것입니다.

CFS는 nice를 통해 *얼마나 자주* 도는가는 조절할 수 있지만, *얼마나 빨리* 응답해야 하는가는 별도로 지정할 수 없었습니다. 두 개념을 같은 축에 묶어버린 셈입니다.

**Peter Zijlstra**가 2023년부터 EEVDF를 메인라인에 넣었고, 6.6 LTS 커널부터 기본 스케줄러로 전환됐습니다. 학술 배경은 **Stoica·Abdel-Wahab·Jeffay·Baruah**의 1996년 논문입니다.

EEVDF의 두 축은 다음과 같습니다.

1. **Eligibility (적격성)** — 이 스레드가 자기 몫만큼 충분히 돌았는가. 못 받았으면 eligible입니다
2. **Virtual Deadline (가상 마감)** — eligible 스레드 중 마감이 가장 빠른 것을 선택합니다

deadline은 다음과 같이 계산됩니다.

$$
\text{deadline} = \text{eligible time} + \frac{\text{request size}}{\text{weight}}
$$

요청 크기(latency-nice라는 새 매개변수)가 작을수록 deadline이 빨라지고, 더 자주 선점됩니다. 즉 게임 메인 스레드처럼 "**자주는 안 도는 대신 깨어나면 즉시 응답해야** 하는" 작업을 정확히 표현할 수 있게 됐습니다.

```c
/* Linux 6.6+ : nice와 별개로 latency-nice 설정 */
struct sched_attr attr = {
    .sched_policy   = SCHED_NORMAL,
    .sched_nice     = 0,
    .sched_runtime  = 1   * 1000 * 1000,   /* 1ms */
    .sched_deadline = 16  * 1000 * 1000,   /* 16.67ms */
    .sched_period   = 16  * 1000 * 1000,
};
sched_setattr(pid, &attr, 0);
```

> EEVDF가 도입되었어도 vruntime 기반 공정성은 그대로 유지됩니다. EEVDF는 CFS의 대체라기보다 **선택 정책의 정교화**에 가깝고, 외부 인터페이스(`nice`, `cgroup cpu.weight`)도 거의 그대로 쓰입니다.

### Linux의 다른 스케줄링 클래스

Linux는 한 가지 알고리즘만 쓰지 않고 **클래스**를 계층으로 둡니다. 클래스마다 우선순위가 정해져 있고, 위 클래스에 작업이 있으면 아래 클래스는 돌지 못합니다.

| 클래스 | 정책 | 용도 |
|--------|------|------|
| stop | (커널 전용) | CPU 핫플러그, RCU 등 |
| dl | SCHED_DEADLINE | 실시간 (period + runtime + deadline 보장) |
| rt | SCHED_FIFO, SCHED_RR | 실시간 우선순위 1~99 |
| fair | SCHED_NORMAL/BATCH/IDLE | 일반, CFS/EEVDF |
| idle | (모두 idle일 때) | swapper |

게임에서 **SCHED_FIFO/RR을 함부로 써서는 안 되는 이유**가 있습니다. 잘못 쓰면 시스템 전체를 멈출 수 있습니다 — priority 99짜리 무한 루프 한 번이면 그 코어는 이후 응답 불가가 됩니다. 진짜 RT가 필요한 오디오 스레드도 `SCHED_FIFO`보다 `dispatch_qos` / `AVAudioSession.realtime`처럼 OS가 제공하는 **상위 추상화**를 통해 접근하는 편이 안전합니다.

---

## Part 4: Windows 스케줄러 — Priority + Boost

Windows NT의 스케줄러는 **Dave Cutler**가 VMS 경험을 가져와 설계한 32단계 우선순위 기반 시스템입니다. 기본 골격은 NT 3.1(1993) 이래 거의 그대로 유지되고 있고, 시간이 지나면서 휴리스틱과 하드웨어 적응 코드만 두텁게 쌓였습니다.

### 32 Priority Levels

| 레벨 | 의미 |
|------|------|
| 0 | Zero page thread (메모리 0 채우기 전용) |
| 1~15 | Variable priority (일반 프로세스, 동적 조정 대상) |
| 16~31 | Real-time priority (관리자 권한 필요, 동적 조정 없음) |

각 프로세스에는 **Priority Class**가 있고, 그 안에서 스레드는 **Thread Priority**로 미세 조정합니다.

```c
/* Windows 우선순위 = Process Class + Thread Priority offset */
SetPriorityClass(hProcess, NORMAL_PRIORITY_CLASS);    /* base 8 */
SetThreadPriority(hThread, THREAD_PRIORITY_NORMAL);   /* offset 0 */

/* HIGH_PRIORITY_CLASS = 13, THREAD_PRIORITY_HIGHEST = +2 → effective 15 */
/* REALTIME_PRIORITY_CLASS = 24, ... */
```

### Quantum

Windows의 타임 퀀텀은 **clock interval**의 배수로 측정됩니다. 보통 클럭 인터벌은 약 15ms(HPET 기반) 혹은 1ms(멀티미디어 타이머 활성화 시)입니다.

- **Workstation**: 2 clock interval (기본은 약 30ms이지만 부팅 후 보정으로 보통 더 짧아짐)
- **Server**: 12 clock interval (긴 퀀텀으로 throughput 우선)

또한 **foreground 프로세스는 quantum이 stretch**됩니다. 사용자가 보고 있는 창의 스레드에 더 긴 시간을 주어 응답성을 높입니다 (제어판 → 시스템 → 고급 → 성능 옵션 → 고급의 "프로그램" / "백그라운드 서비스" 토글이 이 기능을 켜고 끕니다).

### Priority Boost — Windows의 핵심 휴리스틱

Variable priority 영역(1~15)의 스레드는 다양한 이벤트로 **일시적으로 우선순위가 올라갑니다**. boost는 매 quantum마다 1씩 감소해 결국 base로 돌아갑니다.

| 이벤트 | Boost 양 |
|--------|---------|
| Disk I/O 완료 | +1 |
| 네트워크 / Mailslot | +2 |
| Mouse / Keyboard 입력 | +6 |
| 사운드 카드 | +8 |
| GUI 스레드가 메시지 수신 | +2 (foreground 추가) |
| Semaphore wait 종료 | +1 |
| Mutex/Event/Timer wait 종료 | +1 |

이 휴리스틱이 **Windows의 응답성을 만드는 메커니즘**입니다. 사용자가 마우스를 움직이면 GUI 스레드가 +6, 키 입력도 +6을 받습니다. 다른 CPU-bound 작업이 돌고 있어도 입력 반응이 즉시 옵니다.

> **잠깐, 이건 짚고 넘어갑시다.** GUI 스레드 boost가 +6이라면, 여러 창에 우선순위는 어떻게 분배됩니까?
>
> **포커스를 가진 창의 스레드**만 foreground 추가 boost를 받습니다. Alt-Tab으로 활성 창이 바뀌는 순간 boost 분배도 즉시 바뀝니다. Process Explorer에서 우선순위 칸을 켜고 다른 창을 클릭해 보면, 클릭된 창의 스레드 우선순위 숫자가 잠깐 올라가는 것을 확인할 수 있습니다.

### Realtime Priority의 함정

레벨 16~31은 **dynamic boost가 없고**, 항상 그 우선순위로 돕니다. 이론적으로는 "절대 양보하지 않는다"가 됩니다. 그래서 오디오, 비디오 캡처, 일부 게임 스레드가 16~22 정도를 사용합니다.

그러나 **REALTIME_PRIORITY_CLASS (24~31)** 를 일반 코드에서 쓰면 위험합니다. 24 이상의 무한 루프 한 번이 마우스 커서까지 멈출 수 있습니다 — 마우스 처리도 결국 스레드이기 때문입니다.

### NUMA, SMT, Heterogeneous

현대 Windows 스케줄러는 NUMA 노드, SMT(하이퍼스레딩), Intel Thread Director(P/E 코어 힌트)를 모두 고려합니다. Windows 11에서 도입된 **Hardware Threaded Scheduling**이 Thread Director의 힌트를 받아 P/E 코어 배치를 조정합니다 — Apple Silicon이 OS 레벨에서 한 일을 Intel은 OS·CPU 협업으로 풀고 있습니다.

```cpp
/* Windows: 스레드 priority 조정 + affinity */
HANDLE h = GetCurrentThread();
SetThreadPriority(h, THREAD_PRIORITY_TIME_CRITICAL);  /* +15 */

/* 코어 0,1번에만 고정 */
DWORD_PTR mask = 0x3;
SetThreadAffinityMask(h, mask);

/* Windows 10+ : E-core 권장 힌트 */
THREAD_POWER_THROTTLING_STATE state = {};
state.Version = THREAD_POWER_THROTTLING_CURRENT_VERSION;
state.ControlMask = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
state.StateMask   = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
SetThreadInformation(h, ThreadPowerThrottling, &state, sizeof(state));
```

마지막의 `THREAD_POWER_THROTTLING_EXECUTION_SPEED`는 "이 스레드는 E-core에서 천천히 돌아도 됩니다"라고 OS에 힌트를 주는 API입니다. 백그라운드 작업에 적용하면 P-core가 게임 메인 스레드용으로 비워집니다.

---

## Part 5: macOS 스케줄러 — QoS + P/E 코어

macOS는 외형은 Mach 기반이지만, 스케줄러는 BSD 기반의 priority 시스템 위에 **QoS (Quality of Service)** 라는 상위 추상화를 얹은 형태입니다. 개발자는 거의 항상 QoS를 통해 우선순위를 표현하고, 커널이 그것을 priority + 코어 배정 + 전력 관리로 번역합니다.

### QoS Class 5단계

| QoS Class | 의미 | 예시 | 매핑 priority |
|-----------|------|------|---------------|
| User Interactive | 즉시 반응 필요, 사용자가 직접 보는 작업 | 메인 스레드, 애니메이션, 입력 | 47 |
| User Initiated | 사용자가 시작해 결과를 기다리는 작업 | 파일 열기, 검색 | 37 |
| Default | 명시 안 했을 때 | 일반 작업 | 31 |
| Utility | 사용자가 즉시 결과를 안 봐도 되는 작업 (진행률 표시) | 다운로드, 가져오기 | 20 |
| Background | 사용자에게 보이지 않는 작업 | 인덱싱, 백업 | 5 |

이 QoS 값이 결정하는 것은 다음과 같습니다.

1. **CPU priority** — 위 표의 숫자
2. **CPU scheduling latency** — User Interactive는 빠른 wake-up, Background는 묶어서 처리
3. **I/O priority** — 디스크 큐의 우선순위
4. **CPU 코어 배정** (Apple Silicon) — User Interactive/Initiated는 P-core 우선, Utility/Background는 E-core 우선
5. **Timer coalescing** — Background는 타이머 발화를 배치로 모음
6. **GPU 우선순위** — 일부 그래픽 워크로드에 영향

QoS 한 줄이 **여섯 가지를 동시에** 결정합니다.

### QoS API

```c
/* C/Objective-C — 스레드 자기 자신의 QoS 설정 */
pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);

/* GCD 큐 생성 시 */
dispatch_queue_t q = dispatch_queue_create_with_target(
    "com.example.render",
    DISPATCH_QUEUE_SERIAL,
    dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE, 0));

/* dispatch_async에 QoS attach */
dispatch_async(q, ^{
    /* User Interactive로 실행 */
});
```

```swift
// Swift
DispatchQueue.global(qos: .userInteractive).async {
    // 메인 스레드 부담을 줄이기 위한 빠른 처리
}

// Operation API
let op = BlockOperation { /* ... */ }
op.qualityOfService = .userInitiated
queue.addOperation(op)
```

### QoS Inheritance — 우선순위 역전 방지

QoS는 **자동 전파**됩니다. User Interactive 큐에서 dispatch한 작업이 내부에서 다른 큐에 dispatch_sync 하면, 호출되는 측 큐의 QoS가 일시적으로 User Interactive로 부스트됩니다. 이 메커니즘이 macOS의 priority inversion 방지의 핵심입니다.

락에도 같은 메커니즘이 적용됩니다. `os_unfair_lock`은 잠금 보유 스레드의 QoS를 대기 스레드의 QoS까지 끌어올립니다 — POSIX의 `PTHREAD_PRIO_INHERIT`와 같은 일을 OS 레벨에서 자동으로 합니다.

### QoS → priority → P/E 코어 매핑

다음 다이어그램은 QoS 한 줄이 Mach priority와 Apple Silicon의 P/E 코어 배정으로 어떻게 번역되는지를 보여줍니다.

<div class="sk-qos">
  <div class="sk-qos-title">macOS QoS — 한 줄로 결정되는 여섯 가지</div>

  <div class="sk-qos-grid">
    <div class="sk-qos-h">QoS Class</div>
    <div class="sk-qos-h sk-qos-h-prio">Mach priority</div>
    <div class="sk-qos-h">Apple Silicon 코어 배정</div>

    <div class="sk-qos-cell sk-qos-ui">
      <div class="sk-qos-name">USER_INTERACTIVE</div>
      <div class="sk-qos-sub">메인 스레드 / 애니메이션</div>
    </div>
    <div class="sk-qos-prio">47</div>
    <div class="sk-qos-cell sk-qos-pcore-strong">
      <div class="sk-qos-name">P-core 전용</div>
      <div class="sk-qos-sub">최고 성능 / 최대 전력</div>
    </div>

    <div class="sk-qos-cell sk-qos-uin">
      <div class="sk-qos-name">USER_INITIATED</div>
      <div class="sk-qos-sub">파일 열기 / 검색</div>
    </div>
    <div class="sk-qos-prio">37</div>
    <div class="sk-qos-cell sk-qos-pcore-pref">
      <div class="sk-qos-name">P-core 선호</div>
      <div class="sk-qos-sub">필요시 E-core 사용 가능</div>
    </div>

    <div class="sk-qos-cell sk-qos-def">
      <div class="sk-qos-name">DEFAULT</div>
      <div class="sk-qos-sub">명시 안 함</div>
    </div>
    <div class="sk-qos-prio">31</div>
    <div class="sk-qos-cell sk-qos-mixed">
      <div class="sk-qos-name">P/E 혼합</div>
      <div class="sk-qos-sub">로드에 따라 OS가 결정</div>
    </div>

    <div class="sk-qos-cell sk-qos-ut">
      <div class="sk-qos-name">UTILITY</div>
      <div class="sk-qos-sub">진행률 표시 작업</div>
    </div>
    <div class="sk-qos-prio">20</div>
    <div class="sk-qos-cell sk-qos-ecore-pref">
      <div class="sk-qos-name">E-core 선호</div>
      <div class="sk-qos-sub">전력 효율 우선</div>
    </div>

    <div class="sk-qos-cell sk-qos-bg">
      <div class="sk-qos-name">BACKGROUND</div>
      <div class="sk-qos-sub">인덱싱 / 백업</div>
    </div>
    <div class="sk-qos-prio">5</div>
    <div class="sk-qos-cell sk-qos-ecore-strong">
      <div class="sk-qos-name">E-core 전용 + 묶음</div>
      <div class="sk-qos-sub">timer coalescing, 저전력</div>
    </div>
  </div>

  <div class="sk-qos-foot">
    <div class="sk-qos-foot-title">QoS 한 줄이 동시에 결정하는 것</div>
    <div class="sk-qos-foot-grid">
      <span>① CPU priority</span>
      <span>② scheduling latency</span>
      <span>③ I/O priority</span>
      <span>④ P/E core 배정</span>
      <span>⑤ timer coalescing</span>
      <span>⑥ GPU 우선순위</span>
    </div>
    <div class="sk-qos-foot-note">QoS는 자동 전파(inheritance)되어 dispatch 체인과 락 보유자까지 부스트되므로 priority inversion이 자동 완화됩니다.</div>
  </div>

<style>
.sk-qos { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-qos-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sk-qos-grid { display: grid; grid-template-columns: 1.2fr 0.5fr 1.2fr; gap: 8px; align-items: stretch; }
.sk-qos-h { font-size: 12px; font-weight: 700; color: #4a5568; text-align: center; padding-bottom: 4px; border-bottom: 1px solid #cbd5e0; }
.sk-qos-h-prio { text-align: center; }
.sk-qos-cell { padding: 10px 12px; border-radius: 6px; border: 1.5px solid; text-align: center; }
.sk-qos-name { font-family: monospace; font-weight: 700; font-size: 12px; color: #1a202c; }
.sk-qos-sub { font-size: 10.5px; color: #4a5568; margin-top: 2px; }
.sk-qos-prio { display: flex; align-items: center; justify-content: center; font-family: monospace; font-size: 18px; font-weight: 700; color: #2b6cb0; position: relative; }
.sk-qos-prio::before, .sk-qos-prio::after { content: ""; position: absolute; top: 50%; height: 1px; background: #a0aec0; }
.sk-qos-prio::before { left: 0; right: calc(50% + 16px); }
.sk-qos-prio::after { right: 0; left: calc(50% + 16px); }
.sk-qos-ui  { background: #fed7d7; border-color: #c53030; }
.sk-qos-uin { background: #feebc8; border-color: #d69e2e; }
.sk-qos-def { background: #fefcbf; border-color: #b7791f; }
.sk-qos-ut  { background: #c6f6d5; border-color: #38a169; }
.sk-qos-bg  { background: #bee3f8; border-color: #3182ce; }
.sk-qos-pcore-strong { background: #fed7d7; border-color: #c53030; }
.sk-qos-pcore-pref   { background: #feebc8; border-color: #d69e2e; }
.sk-qos-mixed        { background: #e9d8fd; border-color: #805ad5; }
.sk-qos-ecore-pref   { background: #c6f6d5; border-color: #38a169; }
.sk-qos-ecore-strong { background: #bee3f8; border-color: #3182ce; }

.sk-qos-foot { margin-top: 16px; padding: 12px 14px; background: #f7fafc; border: 1px solid #cbd5e0; border-radius: 6px; }
.sk-qos-foot-title { font-size: 12px; font-weight: 700; color: #2d3748; margin-bottom: 8px; }
.sk-qos-foot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px 12px; font-family: monospace; font-size: 11.5px; color: #2d3748; }
.sk-qos-foot-note { margin-top: 8px; font-size: 11px; color: #4a5568; font-style: italic; }

[data-mode="dark"] .sk-qos { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-qos-title { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-h { color: #cbd5e0; border-bottom-color: #4a5568; }
[data-mode="dark"] .sk-qos-name { color: #f7fafc; }
[data-mode="dark"] .sk-qos-sub { color: #cbd5e0; }
[data-mode="dark"] .sk-qos-prio { color: #63b3ed; }
[data-mode="dark"] .sk-qos-prio::before, [data-mode="dark"] .sk-qos-prio::after { background: #4a5568; }
[data-mode="dark"] .sk-qos-ui  { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sk-qos-uin { background: #744210; border-color: #ecc94b; }
[data-mode="dark"] .sk-qos-def { background: #5a4017; border-color: #d69e2e; }
[data-mode="dark"] .sk-qos-ut  { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-qos-bg  { background: #2a4365; border-color: #63b3ed; }
[data-mode="dark"] .sk-qos-pcore-strong { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sk-qos-pcore-pref   { background: #744210; border-color: #ecc94b; }
[data-mode="dark"] .sk-qos-mixed        { background: #322659; border-color: #b794f4; }
[data-mode="dark"] .sk-qos-ecore-pref   { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-qos-ecore-strong { background: #2a4365; border-color: #63b3ed; }
[data-mode="dark"] .sk-qos-foot { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-qos-foot-title { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-foot-grid { color: #e2e8f0; }
[data-mode="dark"] .sk-qos-foot-note { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-qos { padding: 14px 12px 12px; }
  .sk-qos-title { font-size: 13px; }
  .sk-qos-grid { grid-template-columns: 1fr 0.4fr 1fr; gap: 5px; }
  .sk-qos-cell { padding: 6px 6px; }
  .sk-qos-name { font-size: 10px; }
  .sk-qos-sub { font-size: 8.5px; }
  .sk-qos-prio { font-size: 14px; }
  .sk-qos-foot-grid { grid-template-columns: 1fr 1fr; font-size: 10px; }
  .sk-qos-foot-title { font-size: 11px; }
  .sk-qos-foot-note { font-size: 10px; }
}
</style>
</div>

### Game Mode (macOS 14+)

macOS Sonoma부터 추가된 **Game Mode**는 게임이 풀스크린일 때 OS가 자동 활성화하는 모드입니다. 효과는 다음과 같습니다.

- 백그라운드 작업의 QoS를 더 강하게 억제 (Spotlight 인덱싱, Time Machine 등)
- 게임 프로세스에 P-core 배정 우선권 강화
- AirPods/PS5 컨트롤러의 오디오·입력 폴링 레이트 2배 증가

iOS의 Sustained Performance API와 발상이 비슷합니다 — "지금 이 앱은 16.67ms를 못 놓치는 상태입니다"를 OS에 알려, 시스템 전체의 자원 분배가 조정됩니다.

---

## Part 6: 게임 프레임 예산 — 16.67ms

지금까지의 OS 이론을 게임 컨텍스트로 옮겨 보겠습니다. 게임 개발자에게 스케줄링은 결국 **프레임 예산**의 문제입니다.

### 프레임 예산의 수학

$$
\text{frame budget} = \frac{1000\,\text{ms}}{\text{target FPS}}
$$

| Target FPS | 프레임 예산 | 누가 쓰는가 |
|------------|-------------|-------------|
| 30 | 33.33ms | 콘솔 시네마틱, 일부 모바일 |
| 60 | 16.67ms | 일반 게임 표준 |
| 90 | 11.11ms | VR 최소선 |
| 120 | 8.33ms | 고프레임 PC, PS5 Performance |
| 144 | 6.94ms | 고주사율 모니터 |
| 240 | 4.17ms | 경쟁 FPS, e스포츠 |

이 시간 안에 다음이 모두 끝나야 합니다.

1. **Input 처리** — 키보드, 마우스, 게임패드, 터치
2. **Game Logic** — AI, 행동, 상태 업데이트
3. **Physics / Collision** — 이산 시뮬레이션 한 스텝
4. **Animation** — 본 행렬 계산, 블렌딩
5. **Particle / VFX** — 파티클 업데이트
6. **Render command 빌드** — 드로 콜 정렬, 컬링
7. **GPU submit** — 명령 버퍼 큐잉
8. **Present** — 백버퍼 → 화면 (VSync 대기 포함)

게임 엔진은 이를 **여러 스레드에 분산**합니다. 한 프레임 안에 일어나는 일을 시간축에 그리면 다음과 같은 모양이 됩니다.

<div class="sk-fr">
  <div class="sk-fr-title">60fps 프레임 예산 16.67ms — 누가 언제 무엇을 하는가</div>
  <div class="sk-fr-budget">단단한 마감: 16.67ms 안에 끝내지 못하면 프레임 드랍</div>

  <div class="sk-fr-grid">
    <div class="sk-fr-trackname">Main</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-input"   style="left: 0%;    width: 6%;">Input</div>
      <div class="sk-fr-blk sk-fr-logic"   style="left: 6%;    width: 14%;">Logic / AI</div>
      <div class="sk-fr-blk sk-fr-physics" style="left: 20%;   width: 12%;">Physics</div>
      <div class="sk-fr-blk sk-fr-anim"    style="left: 32%;   width: 10%;">Animation</div>
      <div class="sk-fr-blk sk-fr-cmd"     style="left: 42%;   width: 12%;">Cull / Sort</div>
    </div>

    <div class="sk-fr-trackname">Render</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-cmd"     style="left: 20%;   width: 30%;">CommandBuffer build (frame N-1)</div>
      <div class="sk-fr-blk sk-fr-submit"  style="left: 50%;   width: 22%;">GPU submit + sync</div>
    </div>

    <div class="sk-fr-trackname">Workers</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-job"     style="left: 6%;    width: 13%;">AI Job</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 19%;   width: 13%;">Particle</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 32%;   width: 10%;">Skinning</div>
      <div class="sk-fr-blk sk-fr-job"     style="left: 42%;   width: 14%;">Frustum Cull</div>
    </div>

    <div class="sk-fr-trackname">GPU</div>
    <div class="sk-fr-track">
      <div class="sk-fr-blk sk-fr-gpu"     style="left: 52%;   width: 44%;">GPU 렌더링 (shadow → opaque → transparent → post)</div>
    </div>

    <div class="sk-fr-trackname sk-fr-vbname">VBlank</div>
    <div class="sk-fr-track sk-fr-vbtrack">
      <div class="sk-fr-vb">VBlank → Present</div>
    </div>
  </div>

  <div class="sk-fr-axis">
    <span style="left: 0%;">0</span>
    <span style="left: 25%;">4.2</span>
    <span style="left: 50%;">8.3</span>
    <span style="left: 75%;">12.5</span>
    <span style="left: 100%;">16.67ms</span>
  </div>

  <div class="sk-fr-legend">
    <span class="sk-fr-lg sk-fr-input"></span>Input
    <span class="sk-fr-lg sk-fr-logic"></span>Logic/AI
    <span class="sk-fr-lg sk-fr-physics"></span>Physics
    <span class="sk-fr-lg sk-fr-anim"></span>Animation
    <span class="sk-fr-lg sk-fr-cmd"></span>CommandBuffer/Cull
    <span class="sk-fr-lg sk-fr-job"></span>Worker Job
    <span class="sk-fr-lg sk-fr-gpu"></span>GPU
  </div>

  <div class="sk-fr-foot">CPU 메인 스레드는 Render와 1프레임 파이프라인 — Render가 보는 데이터는 Main의 N-1 프레임 결과입니다.</div>

<style>
.sk-fr { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sk-fr-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 8px; text-align: center; }
.sk-fr-budget { font-size: 11px; color: #2b6cb0; font-weight: 700; text-align: center; margin-bottom: 14px; padding: 4px 8px; border: 1px dashed #2b6cb0; border-radius: 4px; }
.sk-fr-grid { display: grid; grid-template-columns: 80px 1fr; gap: 6px 10px; align-items: center; }
.sk-fr-trackname { font-size: 12px; font-weight: 700; color: #2d3748; text-align: right; }
.sk-fr-track { position: relative; height: 32px; background: #fff; border: 1px solid #cbd5e0; border-radius: 4px; overflow: hidden; }
.sk-fr-blk { position: absolute; top: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 10.5px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.1); padding: 0 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sk-fr-input    { background: #fefcbf; }
.sk-fr-logic    { background: #fed7d7; }
.sk-fr-physics  { background: #e9d8fd; }
.sk-fr-anim     { background: #c6f6d5; }
.sk-fr-cmd      { background: #bee3f8; }
.sk-fr-submit   { background: #feebc8; }
.sk-fr-job      { background: #c6f6d5; border: 1px solid #38a169; }
.sk-fr-gpu      { background: #fbb6ce; }
.sk-fr-vbtrack { background: transparent; border: 0; position: relative; }
.sk-fr-vbname { color: #c53030; }
.sk-fr-vb { position: absolute; right: 0; top: 50%; transform: translateY(-50%) translateX(50%); font-size: 11px; color: #c53030; font-weight: 700; padding: 4px 8px; background: #fff5f5; border: 1px dashed #c53030; border-radius: 4px; white-space: nowrap; }
.sk-fr-axis { position: relative; height: 18px; margin-top: 6px; margin-left: 90px; font-family: monospace; font-size: 10px; color: #718096; }
.sk-fr-axis span { position: absolute; transform: translateX(-50%); }
.sk-fr-axis span:last-child { transform: translateX(-100%); }
.sk-fr-legend { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 14px; font-size: 11px; color: #4a5568; }
.sk-fr-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid #cbd5e0; vertical-align: middle; margin-right: 4px; }
.sk-fr-foot { margin-top: 12px; font-size: 11px; color: #718096; font-style: italic; text-align: center; }

[data-mode="dark"] .sk-fr { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sk-fr-title { color: #e2e8f0; }
[data-mode="dark"] .sk-fr-budget { color: #63b3ed; border-color: #63b3ed; }
[data-mode="dark"] .sk-fr-trackname { color: #e2e8f0; }
[data-mode="dark"] .sk-fr-track { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sk-fr-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.08); }
[data-mode="dark"] .sk-fr-input    { background: #5a4017; }
[data-mode="dark"] .sk-fr-logic    { background: #742a2a; }
[data-mode="dark"] .sk-fr-physics  { background: #322659; }
[data-mode="dark"] .sk-fr-anim     { background: #22543d; }
[data-mode="dark"] .sk-fr-cmd      { background: #2a4365; }
[data-mode="dark"] .sk-fr-submit   { background: #744210; }
[data-mode="dark"] .sk-fr-job      { background: #22543d; border-color: #68d391; }
[data-mode="dark"] .sk-fr-gpu      { background: #702459; }
[data-mode="dark"] .sk-fr-vbname { color: #fc8181; }
[data-mode="dark"] .sk-fr-vb { color: #fc8181; background: #2d3748; border-color: #fc8181; }
[data-mode="dark"] .sk-fr-axis { color: #a0aec0; }
[data-mode="dark"] .sk-fr-legend { color: #cbd5e0; }
[data-mode="dark"] .sk-fr-lg { border-color: #4a5568; }
[data-mode="dark"] .sk-fr-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sk-fr { padding: 14px 12px 12px; }
  .sk-fr-title { font-size: 13px; }
  .sk-fr-grid { grid-template-columns: 60px 1fr; gap: 4px 6px; }
  .sk-fr-trackname { font-size: 10px; }
  .sk-fr-track { height: 26px; }
  .sk-fr-blk { font-size: 8.5px; }
  .sk-fr-vb { font-size: 9px; padding: 3px 5px; }
  .sk-fr-axis { margin-left: 66px; font-size: 9px; }
  .sk-fr-legend { font-size: 9.5px; gap: 4px 8px; }
  .sk-fr-foot { font-size: 10px; }
}
</style>
</div>

### 1프레임 파이프라인

대부분의 엔진은 **Main과 Render를 1프레임 떨어뜨립니다**. Main이 Frame N의 게임 상태를 만드는 동안 Render는 Frame N-1의 상태로 GPU에 작업을 던집니다. 두 스레드가 같은 데이터를 동시에 만지지 않으므로 락이 줄지만, **입력 지연이 한 프레임 늘어납니다**.

VR과 e스포츠 타이틀은 이 트레이드오프에 매우 민감합니다. NVIDIA Reflex나 AMD Anti-Lag 같은 GPU 드라이버 기능이 이 파이프라인 깊이를 줄이려고 시도합니다.

### Frame Spike의 원인 — 스케줄링 관점

프레임 시간이 평균 11ms인데 가끔 23ms가 튀는 현상("frame spike")의 원인은 **GC, 디스크 I/O, syscall** 외에도 **OS 스케줄링** 자체가 흔합니다.

- **컨텍스트 스위치 폭주**: 스레드 수가 코어 수보다 많을 때 OS가 자주 갈아끼우고, 캐시 오염으로 메인 스레드가 느려짐
- **Priority inversion**: 메인 스레드가 worker 스레드의 락을 기다리는 동안 무관한 다른 스레드가 worker를 선점
- **NUMA 미스**: 스레드가 다른 NUMA 노드로 이동하며 캐시·메모리 지연 폭발
- **P/E 코어 강등**: macOS Game Mode 미적용 시 게임 메인 스레드가 잠깐 E-core로 밀려 frametime이 두 배

대처법은 다음과 같습니다.

1. 메인 스레드와 렌더 스레드는 **고정 코어 (affinity)** 에 묶기
2. 워커는 `코어 수 - 2` 정도로 제한해 메인/렌더용 코어를 비워두기
3. macOS는 `QOS_CLASS_USER_INTERACTIVE`, Windows는 `THREAD_PRIORITY_HIGHEST`(TIME_CRITICAL은 가급적 피함) 사용
4. 백그라운드 스레드는 명시적으로 BACKGROUND/낮은 priority로 — OS가 P/E 분리 처리

### Priority Inversion 시나리오

게임에서 흔히 보는 모양입니다.

```
시각      Main (qos=USER_INTERACTIVE)         Worker (qos=UTILITY)         Other (qos=DEFAULT)
0ms       enqueue logic                        idle                          running
1ms       AI 결과 필요 → mutex_lock(M) wait    M 보유 중                     -
2ms       (대기)                                preempted by Other            running ← 문제
... 6ms   (대기)                                preempted by Other            running
7ms       (대기)                                M 해제                        -
7.1ms     unblock → 진행 시작                                                 -
```

Main이 1ms부터 7ms까지 멈춰 있는데 그 사이 Worker도 돌지 못하고 Other만 돕니다. **macOS는 이 경우 자동으로 M 보유자(Worker)의 QoS를 USER_INTERACTIVE로 부스트**하므로 Other가 Worker를 선점하지 못합니다. POSIX의 `PTHREAD_PRIO_INHERIT`나 Windows의 ALPC 자동 boost도 같은 종류의 해결책입니다. 다음 편(동기화)에서 더 깊이 다룹니다.

---

## Part 7: 게임 엔진의 우선순위·친화성 활용

### Unity — Job System priority

Unity의 C# Job System은 내부적으로 worker 스레드 풀을 관리하며(`worker count = ProcessorCount - 1`이 기본), `JobHandle`을 통해 스케줄링됩니다.

```csharp
// Unity 2022+
using Unity.Jobs;
using Unity.Collections;

[Unity.Burst.BurstCompile]
struct PhysicsStepJob : IJobParallelFor {
    public NativeArray<float3> positions;
    public NativeArray<float3> velocities;
    public float dt;

    public void Execute(int i) {
        positions[i] += velocities[i] * dt;
    }
}

void Update() {
    var job = new PhysicsStepJob {
        positions = positionsArray,
        velocities = velocitiesArray,
        dt = Time.deltaTime
    };
    JobHandle h = job.Schedule(positionsArray.Length, 64);
    h.Complete();  /* 메인 스레드 동기화 — 프레임 안에 끝나야 함 */
}
```

`ScheduleBatchedJobs()`나 `JobsUtility.JobWorkerMaximumCount`로 개수 제어가 가능합니다. **Player Settings → Other Settings → Use job worker count**에서 명시적 설정도 됩니다 — 8코어 P-core + 4코어 E-core 머신에서 worker를 8로 줄이면 메인이 P-core를 더 안정적으로 점유합니다.

### Unity — Application.targetFrameRate, vSyncCount

```csharp
// 모바일 60fps 고정
QualitySettings.vSyncCount = 0;
Application.targetFrameRate = 60;

// 데스크톱 모니터 주사율 따라가기
QualitySettings.vSyncCount = 1;
Application.targetFrameRate = -1;
```

### Unreal — TaskGraph와 Named Threads

```cpp
// Unreal: 특정 thread에 작업 던지기
ENamedThreads::Type Target = ENamedThreads::GameThread;  /* or RenderThread, AnyThread */
FFunctionGraphTask::CreateAndDispatchWhenReady(
    [](){ /* GameThread에서 실행 */ },
    TStatId(),
    nullptr,
    Target);

// 평행 worker pool
ParallelFor(NumElements, [&](int32 i) {
    Process(i);
}, EParallelForFlags::None);
```

Unreal은 GameThread, RenderThread, RHIThread 등 **named thread**를 둬서 명시적 직렬화를 강제합니다. WorkerPool에 떨어지는 작업은 우선순위 큐로 들어가고, Insights 도구로 작업이 어디서 도는지 시각화할 수 있습니다.

### OS API 직접 호출

엔진을 거치지 않고 OS API로 직접 우선순위를 설정해야 할 때도 있습니다.

```cpp
// 크로스플랫폼 스레드 우선순위 설정 — 게임 엔진 코어에서 자주 쓰는 패턴
void SetThreadHighPriority(std::thread& t) {
#if defined(_WIN32)
    SetThreadPriority(t.native_handle(), THREAD_PRIORITY_HIGHEST);
#elif defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
    /* 혹은 thread_policy_set + thread_extended_policy_data_t */
#elif defined(__linux__)
    struct sched_param p;
    p.sched_priority = 0;  /* SCHED_NORMAL 안에서는 nice로 조정 */
    pthread_setschedparam(t.native_handle(), SCHED_NORMAL, &p);
    setpriority(PRIO_PROCESS, gettid_via_syscall(), -5);
#endif
}
```

### Thread Affinity — 코어 고정

```cpp
// Linux
cpu_set_t set;
CPU_ZERO(&set);
CPU_SET(0, &set);  /* 코어 0번 */
CPU_SET(1, &set);
pthread_setaffinity_np(pthread_self(), sizeof(set), &set);

// Windows
SetThreadAffinityMask(GetCurrentThread(), 0x3);

// macOS — affinity API는 deprecated, hint만 가능
thread_affinity_policy_data_t policy = { 1 /* tag */ };
thread_policy_set(pthread_mach_thread_np(pthread_self()),
                  THREAD_AFFINITY_POLICY,
                  (thread_policy_t)&policy, 1);
```

> **잠깐, 이건 짚고 넘어갑시다.** macOS는 왜 hard affinity가 없습니까?
>
> Apple의 입장은 일관됩니다 — "**개발자가 OS보다 더 잘 알지 못한다**". P/E 이질 코어, 전력 상태, 발열 한계, 코어 파킹 등을 OS가 종합 판단하므로, 앱이 코어를 강제로 잡으면 오히려 손해가 큽니다. 대신 `THREAD_AFFINITY_POLICY`로 **같은 캐시 그룹에 묶어 달라**는 힌트는 줄 수 있고, QoS로 P/E 선호를 표현할 수 있습니다.

### Naughty Dog의 Fiber 사례 (재방문)

Part 8(프로세스와 스레드)에서 Naughty Dog 엔진의 Fiber 모델을 짧게 소개했습니다. 스케줄링 관점에서 다시 보면, **Naughty Dog는 OS 스케줄러를 거의 쓰지 않습니다**.

- 코어당 worker 스레드 1개씩, affinity로 코어에 고정
- 모든 스레드는 fiber 풀에서 다음 fiber를 가져와 실행 (협력형)
- fiber 간 전환은 약 수십 ns (OS 컨텍스트 스위치 약 수 μs의 100분의 1)
- OS 입장에서는 사실상 "스레드 7개를 코어 7개에 고정해 둔 후 깨우지 마"라는 상태

이것이 GDC 2015 Christian Gyrling 발표의 핵심입니다. 일반 게임에서는 과한 설계이지만, 첨예한 프레임 일관성이 필요한 AAA 콘솔 타이틀에서는 OS에 의존하지 않고 직접 스케줄을 통제하는 길을 택한 것입니다.

---

## Part 8: 실전 관찰 — 어떤 스레드가 어디서 도는가

### Linux — chrt, nice, perf sched

```bash
# 현재 쉘의 nice 변경 (값이 작을수록 높은 우선순위)
$ nice -n -5 ./mygame

# 실행 중인 프로세스의 정책/우선순위 확인
$ chrt -p $(pidof mygame)
pid 12345's current scheduling policy: SCHED_OTHER
pid 12345's current scheduling priority: 0

# SCHED_RR로 변경 (root 필요)
$ sudo chrt -r -p 50 $(pidof mygame)

# 스케줄링 이벤트 추적
$ sudo perf sched record -a sleep 10
$ sudo perf sched latency
# Task                       | Runtime ms | Switches | Avg delay ms | Max delay ms |
# mygame:12345               |   2543.123 |     8421 |        0.045 |        2.103 |
```

`Max delay`가 16ms를 넘기면 그 프레임에서 frame spike가 발생했을 가능성이 높습니다.

### macOS — Activity Monitor, Instruments, sample

Instruments의 **System Trace** 템플릿이 가장 정확합니다. 측정 대상은 다음과 같습니다.

- 각 코어(P0~P7, E0~E3)에서 어떤 스레드가 도는지
- QoS 클래스별 색상 표시
- 컨텍스트 스위치 이벤트와 그 사유 (preemption, voluntary block 등)
- 스레드 상태 전이 (run / runnable / waiting / stopped)

```bash
# 스레드별 CPU 사용량
$ top -F -R -o cpu -stats pid,command,cpu,th,state

# 프로세스의 모든 스레드 호출 스택을 1초 간격으로 5회 샘플링
$ sample <pid> 5 1 -mayDie

# powermetrics으로 코어별 사용률 (P/E 분리)
$ sudo powermetrics --samplers cpu_power -i 1000
```

### Windows — Process Explorer, WPA, Xperf

Process Explorer의 **Threads 탭**이 보여주는 것:
- 각 스레드의 base/dynamic priority 컬럼
- "Stack" 버튼으로 호출 스택 확인
- "I/O Priority", "Memory Priority" 컬럼 (Win10+)

**Xperf / Windows Performance Recorder**:

```powershell
# 1: 프로파일 시작
wpr -start GeneralProfile -filemode

# 2: 게임 실행, 측정 구간 진행

# 3: 정지 → ETL 수집
wpr -stop trace.etl

# 4: WPA로 분석 (CPU usage by Thread, Generic Events 등)
wpa.exe trace.etl
```

WPA의 "CPU Usage (Sampled)"와 "CPU Usage (Precise)" 두 그래프 차이가 중요합니다. Sampled는 평균이고, Precise는 컨텍스트 스위치 이벤트 기반이라 frame spike 분석에 정확합니다.

### 측정하는 습관

스케줄러가 무엇을 하는지 추측 대신 **측정**하는 습관이 중요합니다. Tracy Profiler는 게임 엔진에 임베드해 프레임 안의 모든 thread 활동을 ns 단위로 시각화해 줍니다 — Unity, Unreal 모두 통합 플러그인이 있습니다.

```cpp
// Tracy 사용 예
#include "Tracy.hpp"

void GameLoop() {
    ZoneScoped;  /* 함수 단위 자동 측정 */
    {
        ZoneScopedN("AI Update");
        UpdateAI();
    }
    {
        ZoneScopedN("Physics Step");
        StepPhysics();
    }
}
```

Tracy는 LockableBase, FrameMark 등 동기화·프레임 경계 표시 매크로도 제공해 priority inversion을 시각적으로 잡아내기에 좋습니다.

---

## 정리

이 편에서 다룬 내용은 다음과 같습니다.

**스케줄링 기초**:
- 두 가지 결정: "누구에게" + "얼마나 오래"
- Preemptive vs Cooperative
- 평가 기준: Throughput, Latency, Fairness, Response, Energy

**고전 알고리즘**:
- FCFS — convoy effect
- SJF — 평균 대기시간 최적, starvation
- RR — quantum 트레이드오프
- Priority — starvation, priority inversion 예고
- MLFQ — 행동 관찰 기반 우선순위 자동 조정

**Linux**:
- O(n) → O(1) (Ingo Molnár, 2003)
- CFS (2007) — vruntime, RB-tree, completely fair
- EEVDF (2024) — eligibility + virtual deadline, latency-nice 추가
- 클래스 계층: stop > dl > rt > fair > idle

**Windows**:
- 32 priority levels (Variable 1~15, Realtime 16~31)
- Foreground quantum stretch
- Dynamic boost: I/O 완료 +1, Mouse/Keyboard +6, Sound +8
- Realtime은 dynamic boost 없음 — 위험한 영역

**macOS**:
- 5 QoS 클래스 (User Interactive ↔ Background)
- 한 줄로 priority + scheduling latency + I/O priority + P/E core + timer coalescing + GPU priority 동시 결정
- QoS inheritance로 priority inversion 자동 완화
- Game Mode (macOS 14+)

**게임 프레임 예산**:
- 60fps = 16.67ms, 120fps = 8.33ms, VR 90fps = 11.11ms
- 한 프레임에 input → logic → physics → animation → render build → submit → present
- 1프레임 파이프라인: Main과 Render의 시차로 병렬성 확보, 입력 지연 +1프레임 트레이드오프
- Frame spike의 스케줄링 원인: 컨텍스트 스위치 폭주, priority inversion, NUMA 미스, P/E 강등

**게임 엔진 활용**:
- Unity Job System, Unreal TaskGraph + Named Thread
- OS API: SetThreadPriority / pthread_setschedparam / pthread_set_qos_class_self_np
- Affinity: Linux/Windows hard, macOS hint only
- Naughty Dog Fiber — OS 스케줄러를 거의 우회

**관찰 도구**:
- Linux: chrt, nice, perf sched
- macOS: Instruments System Trace, sample, powermetrics
- Windows: Process Explorer, WPA / Xperf
- 크로스플랫폼: Tracy Profiler

다음 편은 **Part 10 동기화 프리미티브**입니다. 이번 편에서 priority inversion을 살짝 언급했는데, 거기에 답하려면 먼저 **lock**의 본질부터 봐야 합니다. Mutex, Semaphore, SpinLock의 차이는 무엇이고, 왜 OS는 futex / SRWLock / os_unfair_lock 같은 OS-specific 프리미티브를 따로 두는지 다룹니다. 그리고 마침내 Stage 2의 핵심 질문 — *"스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가"* — 의 정면 답에 가까워집니다.

---

## References

### 교재
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.5 (CPU Scheduling), Ch.6 (Synchronization)
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.4 (Process Scheduling)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Ch.7 (Process Scheduling, O(1) 시절)
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — Ch.2 (Process Management and Scheduling, CFS 도입 후)
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.4 (Thread Scheduling)
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.7 (Processes), Mach scheduler
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 (Multiprocessor Game Loops)

### 논문
- Stoica, Abdel-Wahab, Jeffay, Baruah, Plaxton, Tan — "A Proportional Share Resource Allocation Algorithm for Real-Time, Time-Shared Systems", RTSS 1996 — EEVDF의 이론적 원전 — [DOI](https://doi.org/10.1109/REAL.1996.563725)
- Pabla — "Completely Fair Scheduler", *Linux Journal*, 2009 — CFS 입문 — [linuxjournal.com](https://www.linuxjournal.com/magazine/completely-fair-scheduler)
- Molnár, Ingo — "Modular Scheduler Core and Completely Fair Scheduler [CFS]", LKML 패치 시리즈, 2007 — CFS 도입 발표
- Zijlstra, Peter — "EEVDF Scheduler", LWN articles, 2023 — [lwn.net/Articles/925371](https://lwn.net/Articles/925371/)
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:N 모델 (스케줄링 관점에서 재참조)
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — frame spike 원리

### 공식 문서
- Linux man pages — `sched(7)`, `chrt(1)`, `sched_setattr(2)`, `nice(1)` — [man7.org](https://man7.org/linux/man-pages/man7/sched.7.html)
- Linux Kernel Documentation — `Documentation/scheduler/sched-design-CFS.rst`, `sched-eevdf.rst`
- Microsoft Docs — *Scheduling Priorities* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)
- Microsoft Docs — *Priority Boosts* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts)
- Apple Developer — *Energy Efficiency Guide for Mac Apps — Prioritize Work with Quality of Service Classes* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-Mac/PrioritizeWorkAtTheTaskLevel.html)
- Apple Developer — *Tuning Your Code's Performance for Apple Silicon* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/tuning-your-code-s-performance-for-apple-silicon)
- Apple Developer — *Game Mode* (macOS 14+) — WWDC23 "Bring your game to Mac" 세션

### 게임 개발 / GDC
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Acton, M. — *Data-Oriented Design and C++*, CppCon 2014 — Insomniac Games의 캐시·스케줄 사고방식
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungie의 스레드 모델
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICE의 Job 시스템
- Unity Technologies — *C# Job System*, *Burst Compiler* 매뉴얼 — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Epic Games — *Task Graph System*, *Async Tasks in Unreal* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Tracy Profiler — [github.com/wolfpld/tracy](https://github.com/wolfpld/tracy)

### 블로그 / 기사
- Brendan Gregg — *Linux Performance, perf sched* — [brendangregg.com](https://www.brendangregg.com/perf.html)
- Howard Oakley — *The Eclectic Light Company* — macOS QoS / P-E core 관찰 시리즈
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Raymond Chen — *The Old New Thing* — Windows priority boost 회상록
- LWN.net — *EEVDF*, *CFS group scheduling*, *sched_ext* 시리즈
- Dmitry Vyukov — *1024cores.net* — go scheduler 내부

### 도구
- Linux: `chrt`, `nice`, `taskset`, `perf sched`, `ftrace`, `bpftrace`
- macOS: Instruments (System Trace, Time Profiler, CPU Counters), `sample`, `powermetrics`, `dispatch_introspection`
- Windows: Process Explorer, Windows Performance Recorder + Analyzer, ETW, PerfView
- 크로스플랫폼: Tracy Profiler, Optick, Superluminal
