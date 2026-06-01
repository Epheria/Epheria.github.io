---
title: "CS 로드맵 10편 — 동기화 프리미티브: Mutex는 어떻게 단 한 명만 들여보내는가"
date: 2026-05-19 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, synchronization, mutex, semaphore, spinlock, cas, futex, cache-coherence, mesi, unity, unreal, job-system]
toc: true
toc_sticky: true
math: true
image: /assets/img/og/cs.png
difficulty: advanced
prerequisites:
  - /posts/ProcessAndThread/
  - /posts/Scheduling/
tldr:
  - 두 스레드가 같은 변수를 건드리면 때때로 죽는 이유는 read-modify-write가 원자적이지 않기 때문입니다. 락은 "한 번에 한 스레드만" 임계 구역에 들이는 추상이고, 그 추상의 바닥에는 항상 하드웨어 atomic 명령(x86 LOCK CMPXCHG, ARM LDXR/STXR)이 있습니다
  - Mutex/Semaphore/RWLock/Spinlock/CondVar는 같은 atomic 위에서 다른 정책을 제공할 뿐입니다. Linux는 futex로 fast path를 user-space에 두고 slow path에서만 커널로 넘어가며, Windows의 SRWLock과 macOS의 os_unfair_lock도 같은 사상으로 설계되었습니다
  - 락의 비용은 명령 자체보다 cache line bouncing에 있습니다. MESI 프로토콜에서 한 코어가 lock을 잡으면 다른 코어의 해당 line이 Invalidate되고, cross-socket이면 비용이 10배 이상 차이납니다. False sharing은 이걸 의도치 않게 만드는 함정입니다
  - Unity Job System은 JobHandle dependency DAG를 만들어 read/write 충돌을 컴파일 시점에 막고, AtomicSafetyHandle로 런타임 race를 잡습니다. Burst는 NativeContainer 접근을 atomic intrinsic으로 컴파일합니다. DOTS는 ComponentSystem의 read/write를 분석해 락 없이 병렬화합니다
  - Unreal은 Game/Render/RHI/Audio Thread를 분리하고 TaskGraph + FRenderCommandFence로 명령을 큐잉합니다. ENQUEUE_RENDER_COMMAND는 보이는 락이 아니라 lock-free MPSC 큐로 동작합니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: "때때로 죽는다"라는 말의 의미

Stage 2를 시작할 때 던진 질문이 있었습니다.

> **스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?**

[7편 OS 아키텍처](/posts/OSArchitecture/), [8편 프로세스와 스레드](/posts/ProcessAndThread/), [9편 스케줄링](/posts/Scheduling/)을 거치면서 답의 절반에는 도착했습니다. OS가 스레드를 보이지 않는 곳에서 갈아끼우고 있고, 갈아끼우는 순간은 예측 불가능하다는 것 — 그래서 "때때로"라는 단어가 정당화됩니다.

이번 편에서 나머지 절반에 답합니다. **읽고-수정하고-쓰는 한 줄의 코드가 사실은 원자적이지 않다**는 것, 그리고 OS와 CPU가 협력해서 어떻게 "한 번에 한 명"이라는 추상을 만들어내는가 입니다.

다루는 내용은 다음과 같습니다.

- **race condition의 정체**: 왜 `counter++`가 데이터를 잃어버리는가
- **락의 가족**: Mutex / Semaphore / RWLock / Spinlock / CondVar / Monitor / Barrier
- **락은 어떻게 만드는가**: Peterson → Test-and-Set → CAS → 하드웨어 atomic
- **OS-specific 프리미티브**: Linux futex, Windows SRWLock, macOS os_unfair_lock
- **하드웨어 메커니즘**: CPU 캐시 계층, MESI, atomic이 cache line ownership을 잡는 원리, false sharing, memory barrier
- **Unity의 동기화 (심층)**: Main Thread 모델, Job System, NativeContainer, AtomicSafetyHandle, Burst, DOTS — 데이터가 코어 간 어떻게 흐르는가
- **Unreal의 동기화**: Game/Render/RHI Thread 분리, TaskGraph, ENQUEUE_RENDER_COMMAND 내부
- **게임 엔진 패턴**: lockless ring buffer, double buffer로 락 회피, frame-locked sync

길어 보이지만 한 줄로 줄이면 이렇습니다. **락은 추상이고, 그 추상은 atomic 명령 위에 있고, atomic 명령은 cache line ownership 위에 있습니다.** 위에서부터 내려가 보겠습니다.

<div class="sy-guide">
  <div class="sy-guide-h">
    <span class="sy-guide-icon">⛟</span>
    읽는 방향 가이드
  </div>
  <div class="sy-guide-body">
    <p>이 글은 깁니다. 한 번에 다 읽지 않아도 됩니다.</p>
    <ul class="sy-guide-list">
      <li><strong>처음 보신다면</strong> — Part 1 (race condition) → Part 2 (락의 가족) → Part 8 (락을 피하는 패턴) 만으로도 큰 그림이 잡힙니다</li>
      <li><strong>Stage 2의 핵심 답 — "왜 때때로만 죽는가"</strong> — 을 정면으로 보시려면 Part 5 (하드웨어와 MESI) 까지 끝까지 권합니다</li>
      <li><strong>엔진 동작 원리가 궁금하시면</strong> — Part 6 (Unity), Part 7 (Unreal) 이 메인</li>
      <li><strong>OS 내부 구현은 필요할 때</strong> — Part 3 (락 만들기), Part 4 (futex/SRWLock/os_unfair_lock) 는 reference로 돌아오시면 됩니다</li>
    </ul>
    <p class="sy-guide-note">가장 깊은 두 구간 — MESI 상태 전이 그리고 Burst가 컴파일하는 4단계 — 은 접이식으로 두었습니다. 필요할 때만 펼치세요.</p>
  </div>

<style>
.sy-guide { margin: 22px 0; padding: 16px 18px 14px; border: 1px solid #cbd5e0; border-left: 4px solid #2b6cb0; border-radius: 6px; background: #ebf8ff; font-size: 13px; line-height: 1.55; }
.sy-guide-h { font-size: 13.5px; font-weight: 800; color: #2c5282; margin-bottom: 8px; letter-spacing: 0.01em; display: flex; align-items: center; gap: 8px; }
.sy-guide-icon { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: #2b6cb0; color: #fff; border-radius: 50%; font-size: 12px; font-weight: 700; }
.sy-guide-body p { margin: 4px 0 8px; color: #2c5282; }
.sy-guide-list { margin: 6px 0 6px 0; padding-left: 18px; }
.sy-guide-list li { padding: 3px 0; color: #2c5282; font-size: 12.5px; }
.sy-guide-list li strong { color: #1a365d; }
.sy-guide-note { font-size: 11.5px !important; color: #4a5568 !important; font-style: italic; margin-top: 10px !important; padding-top: 8px; border-top: 1px dashed #bee3f8; }

[data-mode="dark"] .sy-guide { background: #1a365d; border-color: #4a5568; border-left-color: #4299e1; }
[data-mode="dark"] .sy-guide-h { color: #bee3f8; }
[data-mode="dark"] .sy-guide-icon { background: #4299e1; color: #1a202c; }
[data-mode="dark"] .sy-guide-body p { color: #bee3f8; }
[data-mode="dark"] .sy-guide-list li { color: #bee3f8; }
[data-mode="dark"] .sy-guide-list li strong { color: #90cdf4; }
[data-mode="dark"] .sy-guide-note { color: #a0aec0 !important; border-top-color: #2c5282; }

@media (max-width: 768px) {
  .sy-guide { padding: 12px 12px 10px; font-size: 11.5px; }
  .sy-guide-h { font-size: 12px; }
  .sy-guide-list { padding-left: 14px; }
  .sy-guide-list li { font-size: 11px; }
  .sy-guide-note { font-size: 10.5px !important; }
}
</style>
</div>

---

## Part 1: race condition의 정체

### 한 줄짜리 미스터리

다음 코드를 봅시다.

```cpp
static int counter = 0;

void Worker() {
    for (int i = 0; i < 1'000'000; ++i) {
        counter++;
    }
}

int main() {
    std::thread t1(Worker);
    std::thread t2(Worker);
    t1.join(); t2.join();
    std::cout << counter << "\n";  /* 기대: 2,000,000 */
}
```

두 스레드가 100만 번씩 1을 더했으니 결과는 200만이어야 합니다. 그러나 실제로 돌려보면 매번 다른 값이 나오고, 거의 항상 200만보다 작습니다. 데스크톱에서 흔히 1,200,000 ~ 1,800,000 사이 어딘가가 나옵니다.

값이 사라지는 이유는 `counter++`가 한 줄이지만 기계어로는 세 단계라는 점에 있습니다. 다음 그림이 두 스레드가 같은 카운터를 동시에 만질 때 일어나는 일을 시간 순으로 보여줍니다. 한 번의 증가분이 사라지는 순간이 명확히 보입니다.

<div class="sy-race">
  <div class="sy-race-title">counter++ — 세 단계로 분해되어 race가 발생하는 순간</div>

  <div class="sy-race-grid">
    <div class="sy-race-col sy-race-col-head sy-race-col-time">time →</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-t1">Thread A (Core 0)</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-mem">counter (메모리)</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-t2">Thread B (Core 1)</div>

    <div class="sy-race-tick">t₀</div>
    <div class="sy-race-cell sy-race-load">load eax ← [counter]<br><span>eax = 41</span></div>
    <div class="sy-race-mem"><span class="sy-race-val">41</span></div>
    <div class="sy-race-cell sy-race-idle">·</div>

    <div class="sy-race-tick">t₁</div>
    <div class="sy-race-cell sy-race-mod">add eax, 1<br><span>eax = 42</span></div>
    <div class="sy-race-mem"><span class="sy-race-val">41</span></div>
    <div class="sy-race-cell sy-race-load">load eax ← [counter]<br><span>eax = 41</span></div>

    <div class="sy-race-tick">t₂</div>
    <div class="sy-race-cell sy-race-store">store [counter] ← eax<br><span>counter = 42</span></div>
    <div class="sy-race-mem sy-race-mem-change"><span class="sy-race-val">42</span><span class="sy-race-arrow">↑ A의 +1</span></div>
    <div class="sy-race-cell sy-race-mod">add eax, 1<br><span>eax = 42</span></div>

    <div class="sy-race-tick">t₃</div>
    <div class="sy-race-cell sy-race-idle">·</div>
    <div class="sy-race-mem sy-race-mem-lost"><span class="sy-race-val">42</span><span class="sy-race-arrow sy-race-arrow-lost">✗ B의 +1 덮어씀</span></div>
    <div class="sy-race-cell sy-race-store">store [counter] ← eax<br><span>counter = 42</span></div>
  </div>

  <div class="sy-race-foot">
    기대: counter = 43 (A와 B 각각 +1)  ·  실제: counter = 42 — <strong>한 번의 증가가 사라졌습니다</strong><br>
    원인: t₁에서 B가 41을 읽었을 때 A의 결과 (42) 가 아직 메모리에 없었음 — read-modify-write가 원자적이지 않습니다
  </div>

<style>
.sy-race { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.45; }
.sy-race-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-race-grid { display: grid; grid-template-columns: 48px 1fr 110px 1fr; gap: 6px 8px; align-items: stretch; }
.sy-race-col-head { font-size: 12px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; border-bottom: 1px solid #cbd5e0; }
.sy-race-col-time { color: #718096; }
.sy-race-col-t1 { color: #c53030; }
.sy-race-col-mem { color: #2b6cb0; }
.sy-race-col-t2 { color: #2f855a; }
.sy-race-tick { font-family: monospace; font-weight: 700; color: #718096; text-align: center; align-self: center; }
.sy-race-cell { padding: 8px 10px; border-radius: 4px; font-family: monospace; font-size: 11.5px; font-weight: 600; }
.sy-race-cell span { display: block; font-size: 10px; font-weight: 500; color: #4a5568; margin-top: 2px; }
.sy-race-load { background: #fef5e7; color: #7b341e; }
.sy-race-mod  { background: #fef5e7; color: #7b341e; }
.sy-race-store { background: #fed7aa; color: #7b341e; }
.sy-race-idle { background: #f7fafc; color: #cbd5e0; text-align: center; padding: 8px; font-weight: 700; }
.sy-race-mem { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 6px; border: 1px dashed #cbd5e0; border-radius: 4px; background: #ebf8ff; }
.sy-race-mem-change { background: #c6f6d5; border-color: #38a169; border-style: solid; }
.sy-race-mem-lost { background: #fed7d7; border-color: #c53030; border-style: solid; }
.sy-race-val { font-family: monospace; font-size: 18px; font-weight: 800; color: #1a202c; }
.sy-race-arrow { font-size: 10px; font-weight: 700; color: #2f855a; }
.sy-race-arrow-lost { color: #c53030; }
.sy-race-foot { margin-top: 14px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 12px; color: #4a5568; text-align: center; line-height: 1.55; }
.sy-race-foot strong { color: #c53030; }

[data-mode="dark"] .sy-race { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-race-title { color: #e2e8f0; }
[data-mode="dark"] .sy-race-col-head { color: #e2e8f0; border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-race-col-time { color: #a0aec0; }
[data-mode="dark"] .sy-race-col-t1 { color: #feb2b2; }
[data-mode="dark"] .sy-race-col-mem { color: #90cdf4; }
[data-mode="dark"] .sy-race-col-t2 { color: #9ae6b4; }
[data-mode="dark"] .sy-race-tick { color: #a0aec0; }
[data-mode="dark"] .sy-race-cell span { color: #cbd5e0; }
[data-mode="dark"] .sy-race-load { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-race-mod  { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-race-store { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-race-idle { background: #2d3748; color: #4a5568; }
[data-mode="dark"] .sy-race-mem { background: #1a365d; border-color: #4a5568; }
[data-mode="dark"] .sy-race-mem-change { background: #22543d; border-color: #38a169; }
[data-mode="dark"] .sy-race-mem-lost { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sy-race-val { color: #f7fafc; }
[data-mode="dark"] .sy-race-arrow { color: #9ae6b4; }
[data-mode="dark"] .sy-race-arrow-lost { color: #feb2b2; }
[data-mode="dark"] .sy-race-foot { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-race-foot strong { color: #feb2b2; }

@media (max-width: 768px) {
  .sy-race { padding: 14px 10px 12px; font-size: 11px; }
  .sy-race-title { font-size: 13px; }
  .sy-race-grid { grid-template-columns: 32px 1fr 70px 1fr; gap: 4px 5px; }
  .sy-race-col-head { font-size: 10px; padding: 6px 2px; }
  .sy-race-cell { padding: 6px 6px; font-size: 10px; }
  .sy-race-cell span { font-size: 9px; }
  .sy-race-val { font-size: 14px; }
  .sy-race-arrow { font-size: 8.5px; }
  .sy-race-foot { font-size: 10.5px; }
}
</style>
</div>

### race condition vs data race — 같은 말이 아닙니다

> **잠깐, 이건 짚고 넘어갑시다.** race condition과 data race는 같은 말입니까?
>
> 자주 혼용되지만 학술적으로는 다릅니다.
>
> - **Data race**: 두 스레드가 동기화 없이 같은 메모리에 접근하고, 그중 하나 이상이 쓰기인 경우. 여러 언어 메모리 모델에서 **명시적으로 정의된 용어**입니다. **C++/Rust에서는 일어나면 undefined behavior**, **Java/Go는 메모리 모델 안에서 동작이 제한적으로 정의**되어 있어 UB는 아니지만 "correctly synchronized"가 아닌 프로그램의 결과는 직관과 다를 수 있습니다.
> - **Race condition**: 결과가 스레드 실행 순서에 의존하는 더 넓은 개념. 예를 들어 두 스레드가 각자 atomic 변수를 통해 안전하게 통신하더라도, 누가 먼저 도착하느냐에 따라 비즈니스 로직 결과가 달라지면 race condition입니다.
>
> 즉 모든 data race는 race condition을 일으키지만, 모든 race condition이 data race는 아닙니다. 락은 data race를 제거하는 도구이고, race condition은 그보다 위 계층의 설계 문제입니다.

### 원자성, 가시성, 순서 — 세 가지 보장

동기화 프리미티브가 우리에게 약속해 주는 것은 세 가지입니다.

1. **원자성 (Atomicity)**: 한 연산이 중간 상태가 관찰되지 않고 통째로 일어남
2. **가시성 (Visibility)**: 한 스레드가 쓴 값이 다른 스레드에 보이는 것이 보장됨
3. **순서 (Ordering)**: 프로그램이 본 코드의 순서대로 메모리 연산이 다른 스레드에도 보임

`counter++`가 깨진 원인은 원자성 위반입니다. 그런데 가시성과 순서도 별도의 문제입니다 — CPU는 명령을 재배치하고, 캐시는 즉시 동기화되지 않습니다. 이 셋은 Part 12 (메모리 모델과 원자 연산)에서 본격적으로 다루지만, 이번 편 내내 배경에 깔려 있습니다.

> **잠깐, 이건 짚고 넘어갑시다.** 단순 read나 단순 write도 원자적이지 않을 수 있습니까?
>
> 그렇습니다. x86/ARM에서 자연 정렬된 4바이트/8바이트 read·write는 일반적으로 원자적입니다(C++의 `std::atomic` 보장과는 별개). 그러나 misaligned 접근, 16바이트 SIMD, 32비트 CPU의 64비트 값 같은 경우 한 번의 store가 두 번에 걸쳐 일어날 수 있고, 그 사이에 다른 코어가 절반만 본 값을 읽을 수 있습니다. 그래서 C++에서는 단순 변수 대신 `std::atomic<T>`을 사용해 컴파일러에게 "이 변수는 진짜 원자적이어야 한다"를 알려줍니다.

### 락의 약속

`counter++`를 망가뜨리지 않는 가장 단순한 방법은 다음과 같습니다.

```cpp
std::mutex m;
/* ... */
{
    std::lock_guard<std::mutex> lk(m);
    counter++;
}
```

`lock_guard`가 잡고 있는 동안에는 다른 스레드가 같은 `m`에 들어올 수 없습니다. 결과는 항상 200만 입니다.

여기서 두 가지 질문이 자연스럽게 따라옵니다.

1. **"한 번에 한 명"이라는 약속을 OS는 어떻게 만들어내는가?** — Part 3
2. **그 약속의 비용은 얼마인가?** — Part 5

먼저 락의 종류와 차이를 정리하겠습니다.

---

## Part 2: 락의 가족

### 한눈에 보는 비교표

| 이름 | 본질 | 누가 풉니까 | 대기 방식 | 대표 용도 |
|------|------|-----------|---------|----------|
| **Mutex** | 1 슬롯 락 | 잠근 스레드 | sleep | 임계 구역 보호 |
| **Recursive Mutex** | 재진입 가능한 Mutex | 잠근 스레드 | sleep | 같은 스레드의 중첩 호출 |
| **Spinlock** | 1 슬롯 락 | 잠근 스레드 | busy-wait | 짧은 임계 구역, 커널 |
| **Semaphore** | N 슬롯 카운터 | 임의의 스레드 | sleep | 자원 풀, producer-consumer |
| **RWLock** | 다중 reader / 단일 writer | 잠근 스레드 | sleep | read 비율이 높은 데이터 |
| **Condition Variable** | 대기 + 신호 | 깨우는 스레드 | sleep | 조건 기반 동기화 |
| **Monitor** | Mutex + CondVar 묶음 | (객체 단위) | sleep | 자바 `synchronized` |
| **Barrier** | N 스레드 도착 대기 | 모두 도착하면 | sleep | 병렬 단계 동기화 |
| **Latch** | 1회용 카운트다운 | 카운트가 0 되면 | sleep | 초기화 완료 신호 |

각 항목을 간단히 짚겠습니다.

### Mutex (Mutual Exclusion)

가장 기본입니다. **0 또는 1 상태**를 가지며, lock에 성공한 스레드만 unlock 할 수 있습니다. 이미 누가 잡고 있으면 들어오려는 스레드는 wait queue에 들어가 sleep 합니다.

```cpp
std::mutex m;
m.lock();
// 임계 구역
m.unlock();
```

C++에서는 거의 항상 RAII 래퍼인 `std::lock_guard`나 `std::unique_lock`을 씁니다. 예외가 나도 unlock이 보장되기 때문입니다.

> **잠깐, 이건 짚고 넘어갑시다.** reentrant, recursive, thread-safe — 자주 헷갈리는 세 용어를 정리합니다.
>
> - **Thread-safe**: 어떤 함수/객체가 여러 스레드에서 동시에 호출돼도 정의된 동작을 보장함. *외부에서 본* 성질입니다.
> - **Reentrant**: 한 스레드가 함수 실행 중에 (인터럽트나 시그널을 통해) 같은 함수에 다시 들어가도 안전함. 글로벌 변수 사용 금지, 정적 버퍼 금지 등이 조건입니다.
> - **Recursive (락)**: 같은 스레드가 이미 잡은 락을 같은 스레드가 또 잡을 수 있음. 카운트가 올라가고, 같은 횟수만큼 풀어야 진짜 풀립니다.
>
> Recursive mutex는 편하지만, 보통 "락의 구조를 잘못 잡았다는 신호"로 봅니다. 깊이 들어간 함수가 자기가 락을 잡았는지 모르는 상태로 다시 잡으려고 한다면, 그건 인터페이스 설계에 락 지점이 명시되지 않았다는 뜻이기 때문입니다.

### Spinlock

상태는 Mutex와 같지만, 잠기지 못한 스레드가 **sleep하지 않고 계속 시도**합니다.

```cpp
while (lock.test_and_set(std::memory_order_acquire)) {
    /* busy-wait */
}
```

언제 Spinlock이 Mutex보다 낫습니까? **임계 구역이 매우 짧고, 컨텍스트 스위치 비용이 spin 비용보다 클 때**입니다. 대표적으로 커널 인터럽트 핸들러는 sleep 자체가 금지되어 있어 spinlock만 쓸 수 있습니다.

반대로 임계 구역이 길거나 스레드 수가 코어 수보다 많으면 spinlock은 재앙입니다. 다른 스레드가 sleep해야 할 시간을 CPU 사이클로 태우게 됩니다.

> **잠깐, 이건 짚고 넘어갑시다.** Spinlock과 그냥 busy-wait의 차이는 무엇입니까?
>
> Spinlock은 **atomic primitive 위에 만들어진 락**이고, 그냥 busy-wait은 일반 변수를 폴링하는 패턴입니다. 일반 변수 폴링은 컴파일러가 루프를 hoist해 버리거나(`while(flag);`가 무한 루프로 컴파일), 다른 코어의 변경을 영원히 못 볼 수 있습니다. Spinlock은 atomic + memory ordering으로 그 두 가지를 모두 막아줍니다.

### Semaphore

Dijkstra가 1965년에 제안한 가장 오래된 동기화 프리미티브입니다. **음이 아닌 정수 카운터**이며 두 연산을 가집니다.

- **P (wait, acquire)**: 카운터가 0이면 sleep, 아니면 1 감소
- **V (signal, release)**: 1 증가, 대기자가 있으면 한 명 깨움

Mutex는 사실 "초기값 1인 binary semaphore" 입니다. 다만 의미가 다릅니다 — Mutex는 잠근 스레드가 풀어야 하지만, Semaphore는 누가 release 해도 됩니다. 그래서 Semaphore는 자원 풀(connection pool에서 빈 슬롯 개수)이나 producer-consumer 큐의 "남은 자리/항목 개수" 표현에 적합합니다.

### Reader-Writer Lock

읽기는 여러 명, 쓰기는 한 명. 읽기 비율이 압도적으로 높을 때 throughput이 좋아집니다.

```cpp
std::shared_mutex m;
{
    std::shared_lock<std::shared_mutex> r(m);  /* 여러 reader 동시 가능 */
    // read
}
{
    std::unique_lock<std::shared_mutex> w(m);  /* 단독 writer */
    // write
}
```

함정이 둘 있습니다. 첫째, RWLock 자체의 비용이 일반 Mutex보다 큽니다. 임계 구역이 매우 짧다면 일반 Mutex가 빠를 수 있습니다. 둘째, **writer starvation** — reader가 끊임없이 들어오면 writer가 무한히 기다릴 수 있습니다. 대부분의 구현은 writer-preferring 모드를 제공합니다.

### Condition Variable

"조건이 만족될 때까지 기다린다"를 표현합니다. 항상 **Mutex와 짝**으로 쓰입니다.

```cpp
std::mutex m;
std::condition_variable cv;
bool ready = false;

/* Waiter */
{
    std::unique_lock<std::mutex> lk(m);
    cv.wait(lk, []{ return ready; });
    // 깨어났고, ready == true
}

/* Notifier */
{
    std::lock_guard<std::mutex> lk(m);
    ready = true;
}
cv.notify_one();
```

`cv.wait`이 "lock을 풀고 sleep, 깨어나면 다시 lock 획득"을 원자적으로 수행한다는 점이 핵심입니다. 그렇지 않으면 notify가 wait 직전에 도착해 영원히 깨어나지 못하는 **lost wakeup** 문제가 생깁니다.

또한 wait의 술어를 람다로 넘기는 이유는 **spurious wakeup** 때문입니다. CV는 조건 만족 없이도 깨어날 수 있는 것이 표준에 허용되어 있어, 깨어난 뒤 다시 검사해야 합니다.

### Monitor

Mutex + Condition Variable을 객체 단위로 묶은 추상입니다. 자바의 `synchronized` 키워드와 모든 객체에 딸려 있는 `wait/notify`가 정확히 이 패턴입니다. C#의 `lock` 블록도 동일합니다.

```csharp
lock (gameState) {
    while (!gameState.Ready)
        Monitor.Wait(gameState);
    /* 작업 */
    Monitor.PulseAll(gameState);
}
```

`gameState` 객체 헤더에 monitor가 박혀 있어 별도 mutex를 선언하지 않아도 됩니다. 편하지만 그만큼 한 객체에 락이 강하게 결합되어 있어 락 입자 크기 조절이 어렵습니다.

### Barrier / Latch

**Barrier**: N개 스레드가 모두 한 지점에 도착할 때까지 기다립니다. 게임의 frame-locked 병렬 처리 — "물리 업데이트 N개 잡(job)이 모두 끝나야 다음 단계 진행" — 가 전형적인 예입니다. 재사용 가능합니다 (cyclic barrier).

**Latch**: 카운터가 0이 될 때까지 모두 기다립니다. 일회용입니다. 초기화가 끝났음을 모든 시작 스레드에 한 번에 알릴 때 씁니다.

### 정리: 어떤 락을 언제 쓰는가

다음 매트릭스는 락을 두 축 — 임계 구역 길이(가로)와 read/write 비율(세로) — 위에 놓고 적합한 프리미티브를 표시합니다. 같은 atomic 위에 정책만 다른 도구들이 어떤 상황에 자기 자리를 찾는지가 한 눈에 보입니다.

<div class="sy-locks">
  <div class="sy-locks-title">상황별 적합한 동기화 프리미티브</div>

  <div class="sy-locks-axis-y">read/write 균형</div>

  <div class="sy-locks-grid">
    <div class="sy-locks-corner"></div>
    <div class="sy-locks-xh">짧음 (< 1μs)</div>
    <div class="sy-locks-xh">중간 (1~100μs)</div>
    <div class="sy-locks-xh">긴 / I/O 포함</div>

    <div class="sy-locks-yh">읽기 ≈ 쓰기</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Spinlock</div>
      <div class="sy-locks-note">커널·인터럽트 한정. 유저는 거의 금지</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex</div>
      <div class="sy-locks-note">기본 선택. futex/SRWLock/os_unfair_lock</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex + CondVar</div>
      <div class="sy-locks-note">긴 대기는 sleep + 조건 신호</div>
    </div>

    <div class="sy-locks-yh">읽기 ≫ 쓰기</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Mutex / atomic</div>
      <div class="sy-locks-note">RWLock 오버헤드가 더 클 수 있음</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RWLock (Shared)</div>
      <div class="sy-locks-note">writer starvation 주의</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RCU / Seqlock</div>
      <div class="sy-locks-note">읽기 lock-free, 쓰기 보호</div>
    </div>

    <div class="sy-locks-yh">자원 풀 / Queue</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Semaphore</div>
      <div class="sy-locks-note">슬롯 수 = 카운터</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Semaphore + CondVar</div>
      <div class="sy-locks-note">producer-consumer 표준</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Lock-free Queue</div>
      <div class="sy-locks-note">SPSC ring / Vyukov MPSC</div>
    </div>

    <div class="sy-locks-yh">단계 동기화</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">atomic flag</div>
      <div class="sy-locks-note">짧은 phase 신호</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Barrier / Latch</div>
      <div class="sy-locks-note">N 스레드 일제 sync</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">JobHandle / Fence</div>
      <div class="sy-locks-note">엔진 단위 dependency</div>
    </div>
  </div>

  <div class="sy-locks-legend">
    <span class="sy-locks-lg sy-locks-cell-good"></span>적합
    <span class="sy-locks-lg sy-locks-cell-warm"></span>가능하지만 주의 (오버헤드/금기)
    <span class="sy-locks-foot">— 모든 셀의 바닥에는 같은 atomic CAS가 있습니다. 정책만 바뀝니다.</span>
  </div>

<style>
.sy-locks { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.45; position: relative; }
.sy-locks-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-locks-axis-y { position: absolute; left: 4px; top: 50%; transform: rotate(-90deg) translateX(50%); transform-origin: left center; font-size: 11px; font-weight: 700; color: #718096; letter-spacing: 0.05em; }
.sy-locks-grid { display: grid; grid-template-columns: 110px 1fr 1fr 1fr; gap: 8px; margin-left: 14px; }
.sy-locks-corner { background: transparent; }
.sy-locks-xh { font-size: 11.5px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; background: #edf2f7; border-radius: 4px; }
.sy-locks-yh { font-size: 11.5px; font-weight: 700; color: #2d3748; padding: 8px 6px; background: #edf2f7; border-radius: 4px; display: flex; align-items: center; }
.sy-locks-cell { padding: 10px 10px; border-radius: 5px; border: 1px solid; min-height: 60px; }
.sy-locks-cell-good { background: #c6f6d5; border-color: #68d391; }
.sy-locks-cell-warm { background: #fef5e7; border-color: #f6ad55; }
.sy-locks-name { font-weight: 700; font-size: 12.5px; color: #1a202c; margin-bottom: 4px; }
.sy-locks-note { font-size: 10.5px; color: #4a5568; line-height: 1.4; }
.sy-locks-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 16px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 11px; color: #4a5568; }
.sy-locks-lg { display: inline-block; width: 14px; height: 12px; border: 1px solid; vertical-align: middle; margin-right: 4px; border-radius: 2px; }
.sy-locks-foot { margin-left: auto; color: #718096; font-style: italic; font-size: 11px; }

[data-mode="dark"] .sy-locks { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-locks-title { color: #e2e8f0; }
[data-mode="dark"] .sy-locks-axis-y { color: #a0aec0; }
[data-mode="dark"] .sy-locks-xh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-locks-yh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-locks-cell-good { background: #22543d; border-color: #38a169; }
[data-mode="dark"] .sy-locks-cell-warm { background: #5f370e; border-color: #c05621; }
[data-mode="dark"] .sy-locks-name { color: #f7fafc; }
[data-mode="dark"] .sy-locks-note { color: #cbd5e0; }
[data-mode="dark"] .sy-locks-legend { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-locks-foot { color: #a0aec0; }

@media (max-width: 768px) {
  .sy-locks { padding: 14px 8px 12px; }
  .sy-locks-title { font-size: 13px; }
  .sy-locks-axis-y { display: none; }
  .sy-locks-grid { grid-template-columns: 78px 1fr 1fr 1fr; gap: 5px; margin-left: 0; }
  .sy-locks-xh, .sy-locks-yh { font-size: 9.5px; padding: 6px 3px; }
  .sy-locks-cell { padding: 6px 6px; min-height: 50px; }
  .sy-locks-name { font-size: 10.5px; }
  .sy-locks-note { font-size: 9px; }
  .sy-locks-legend { font-size: 10px; gap: 8px; }
  .sy-locks-foot { margin-left: 0; width: 100%; }
}
</style>
</div>

여기까지가 사용자가 보는 인터페이스 레이어입니다. 이제 한 층 내려가서, OS와 컴파일러가 이 약속들을 어떻게 만들어내는지 봅니다.

---

## Part 3: 락은 어떻게 만드는가

### 시도 1 — 소프트웨어만으로 가능합니까?

먼저 가장 순진한 시도부터 봅니다. 두 스레드를 위한 락을 변수 하나만으로 만들 수 있을까요?

```c
int locked = 0;

void lock() {
    while (locked) ;       /* spin */
    locked = 1;            /* 잡았다! */
}
```

명백히 깨집니다. `while(locked)`을 통과한 두 스레드가 동시에 `locked = 1`을 실행하면 둘 다 임계 구역에 들어갑니다. read와 write 사이가 비어 있어 race가 발생합니다.

### Peterson의 알고리즘 (1981)

소프트웨어만으로 락을 만들 수 있긴 합니다. 두 스레드에 한정하면 **Gary Peterson**이 1981년에 보인 알고리즘이 가장 우아합니다.

<div class="sy-pt">
  <div class="sy-pt-title">Peterson 알고리즘 — 두 스레드 동시 진입 시도</div>

  <div class="sy-pt-vars">
    <span class="sy-pt-tag">공유 변수</span>
    <code>flag[2] = {0, 0}</code>
    <code>turn = 0</code>
    <span class="sy-pt-meaning">flag[i] = "나는 들어가고 싶다", turn = "다음 양보 대상"</span>
  </div>

  <div class="sy-pt-cols">
    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-a">Thread A (self=0)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[0] = 1</code><span class="sy-pt-cmt">들어가고 싶음 선언</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 1</code><span class="sy-pt-cmt">B에게 양보</span></div>
      <div class="sy-pt-step sy-pt-pass"><span class="sy-pt-num">3</span><code>while (flag[1] &amp;&amp; turn == 1) ;</code><span class="sy-pt-cmt">B도 들어가고 싶고, turn이 B면 대기</span></div>
      <div class="sy-pt-step sy-pt-enter"><span class="sy-pt-num">4</span><strong>임계 구역 진입</strong></div>
      <div class="sy-pt-step"><span class="sy-pt-num">5</span><code>flag[0] = 0</code><span class="sy-pt-cmt">unlock</span></div>
    </div>

    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-b">Thread B (self=1)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[1] = 1</code><span class="sy-pt-cmt">들어가고 싶음 선언</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 0</code><span class="sy-pt-cmt">A에게 양보</span></div>
      <div class="sy-pt-step sy-pt-wait"><span class="sy-pt-num">3</span><code>while (flag[0] &amp;&amp; turn == 0) ;</code><span class="sy-pt-cmt">spinning ...</span></div>
      <div class="sy-pt-step sy-pt-idle"><span class="sy-pt-num">4</span>(A가 unlock 할 때까지 대기)</div>
      <div class="sy-pt-step sy-pt-enter-late"><span class="sy-pt-num">5</span><strong>이후 임계 구역 진입</strong></div>
    </div>
  </div>

  <div class="sy-pt-key">
    <strong>왜 한 명만 통과합니까?</strong> 두 스레드가 step 2를 거의 동시에 실행해도 <code>turn</code>은 단 하나의 값만 가집니다 (마지막 write가 이깁니다). 그 값이 0이면 A가 양보한 게 되고 B가 통과, 1이면 그 반대 — 어느 경우든 정확히 한 명만 step 3의 while을 빠져나옵니다.
  </div>

  <div class="sy-pt-warn">
    <strong>그러나 실제 CPU에서는 동작하지 않습니다.</strong> step 1과 step 2가 다른 코어 입장에선 순서가 뒤바뀌어 보일 수 있고 (memory reorder), store buffer 때문에 자기 코어의 쓰기가 다른 코어에 즉시 보이지 않습니다. 결국 memory barrier — 하드웨어 명령 — 가 필요합니다.
  </div>

<style>
.sy-pt { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-pt-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-pt-vars { padding: 8px 12px; background: #edf2f7; border-radius: 4px; margin-bottom: 14px; font-size: 12px; }
.sy-pt-vars code { background: #fff; padding: 1px 6px; margin: 0 4px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; }
.sy-pt-tag { display: inline-block; padding: 2px 8px; background: #2b6cb0; color: #fff; border-radius: 3px; font-size: 10.5px; font-weight: 700; margin-right: 6px; }
.sy-pt-meaning { display: block; margin-top: 4px; font-size: 11px; color: #4a5568; }
.sy-pt-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sy-pt-col { border: 1px solid #cbd5e0; border-radius: 6px; padding: 12px 12px 8px; background: #fff; }
.sy-pt-head { font-weight: 700; font-size: 13px; text-align: center; padding: 6px 0 10px; border-bottom: 1px dashed #cbd5e0; margin-bottom: 10px; }
.sy-pt-head-a { color: #c53030; }
.sy-pt-head-b { color: #2f855a; }
.sy-pt-step { display: flex; align-items: flex-start; gap: 8px; padding: 6px 8px; margin: 4px 0; border-radius: 4px; font-size: 11.5px; }
.sy-pt-num { flex: 0 0 22px; height: 22px; line-height: 22px; text-align: center; background: #4a5568; color: #fff; border-radius: 50%; font-weight: 700; font-size: 10.5px; }
.sy-pt-step code { font-family: monospace; color: #2b6cb0; font-weight: 600; flex: 1 1 auto; }
.sy-pt-cmt { display: block; width: 100%; padding-left: 30px; font-size: 10.5px; color: #718096; margin-top: -2px; font-style: italic; }
.sy-pt-pass { background: #c6f6d5; }
.sy-pt-pass .sy-pt-num { background: #2f855a; }
.sy-pt-enter { background: #2f855a; color: #fff; font-weight: 700; }
.sy-pt-enter .sy-pt-num { background: #fff; color: #2f855a; }
.sy-pt-enter strong { color: #fff; }
.sy-pt-wait { background: #fef5e7; }
.sy-pt-wait .sy-pt-num { background: #c05621; }
.sy-pt-idle { background: #f7fafc; color: #a0aec0; font-style: italic; }
.sy-pt-idle .sy-pt-num { background: #a0aec0; }
.sy-pt-enter-late { background: #fbd38d; }
.sy-pt-enter-late .sy-pt-num { background: #7b341e; }
.sy-pt-enter-late strong { color: #7b341e; }
.sy-pt-key { margin-top: 14px; padding: 10px 12px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; }
.sy-pt-key strong { color: #2b6cb0; }
.sy-pt-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; }
.sy-pt-warn { margin-top: 10px; padding: 10px 12px; background: #fff5f5; border-left: 3px solid #c53030; border-radius: 3px; font-size: 12px; color: #742a2a; }
.sy-pt-warn strong { color: #c53030; }

[data-mode="dark"] .sy-pt { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-pt-title { color: #e2e8f0; }
[data-mode="dark"] .sy-pt-vars { background: #2d3748; }
[data-mode="dark"] .sy-pt-vars code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-pt-meaning { color: #cbd5e0; }
[data-mode="dark"] .sy-pt-col { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-pt-head { border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-pt-head-a { color: #feb2b2; }
[data-mode="dark"] .sy-pt-head-b { color: #9ae6b4; }
[data-mode="dark"] .sy-pt-step code { color: #90cdf4; }
[data-mode="dark"] .sy-pt-cmt { color: #a0aec0; }
[data-mode="dark"] .sy-pt-pass { background: #22543d; }
[data-mode="dark"] .sy-pt-wait { background: #5f370e; }
[data-mode="dark"] .sy-pt-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-pt-enter-late { background: #7b341e; }
[data-mode="dark"] .sy-pt-enter-late strong { color: #fbd38d; }
[data-mode="dark"] .sy-pt-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-pt-key strong { color: #90cdf4; }
[data-mode="dark"] .sy-pt-key code { background: #2d3748; }
[data-mode="dark"] .sy-pt-warn { background: #742a2a; color: #fed7d7; }
[data-mode="dark"] .sy-pt-warn strong { color: #feb2b2; }

@media (max-width: 768px) {
  .sy-pt { padding: 14px 10px 12px; }
  .sy-pt-title { font-size: 13px; }
  .sy-pt-cols { grid-template-columns: 1fr; gap: 10px; }
  .sy-pt-col { padding: 10px 10px 6px; }
  .sy-pt-step { font-size: 10.5px; padding: 5px 6px; }
  .sy-pt-cmt { padding-left: 28px; font-size: 9.5px; }
  .sy-pt-num { flex-basis: 20px; height: 20px; line-height: 20px; font-size: 10px; }
  .sy-pt-key, .sy-pt-warn { font-size: 11px; padding: 8px 10px; }
}
</style>
</div>

원리는 **"내가 양보한다"라는 의사 표시와 "지금 누구 차례인가"라는 합의**를 결합한 것입니다. 두 스레드가 동시에 들어오면 `turn` 변수가 단 하나의 값밖에 못 가지므로 한 명만 통과합니다.

이 알고리즘이 정말로 동작합니까? **이론적으로는 그렇고, 실제 CPU에서는 그렇지 않습니다.**

이유는 두 가지입니다.

1. **CPU의 명령 재배치**: `flag[self] = 1; turn = other;` 가 메모리에 도착하는 순서가 코드 순서와 다를 수 있습니다. 다른 코어에서는 `turn` 변경을 먼저 보고 `flag[self]`는 아직 0으로 볼 수 있습니다.
2. **Store buffer**: 각 코어가 가지는 쓰기 버퍼 때문에 자신이 쓴 값이 다른 코어에 즉시 보이지 않습니다.

이 두 문제를 해결하려면 **memory barrier**가 필요한데, barrier는 사실상 하드웨어 명령입니다. 결국 소프트웨어만으로는 안 됩니다.

### 시도 2 — 하드웨어가 도와줍니다

근본적으로 필요한 것은 **"읽고-비교하고-쓰기"를 원자적으로 하는 단일 명령**입니다. CPU 제조사들이 이를 위해 특별한 명령을 제공합니다. 가장 자주 쓰이는 세 가족을 한 그림에 정리하면 다음과 같습니다.

<div class="sy-cas">
  <div class="sy-cas-title">하드웨어 atomic primitive — 세 가족</div>

  <div class="sy-cas-fams">

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Test-and-Set (TAS)</div>
      <div class="sy-cas-fsub">"값을 쓰고 이전 값을 받기"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">읽기<br><span>old = *X</span></div>
        <div class="sy-cas-amp">∧</div>
        <div class="sy-cas-box sy-cas-out">쓰기<br><span>*X = true</span></div>
      </div>
      <div class="sy-cas-bracket">한 번에 — 분리 불가</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>XCHG</code> · <code>LOCK BTS</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> 쌍
      </div>
    </div>

    <div class="sy-cas-fam sy-cas-fam-hi">
      <div class="sy-cas-fname">Compare-and-Swap (CAS)</div>
      <div class="sy-cas-fsub">"기대값과 같으면 새 값으로 바꾸기"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">읽기<br><span>cur = *X</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-cmp">비교<br><span>cur == exp ?</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-out">분기 쓰기<br><span>*X = desired</span></div>
      </div>
      <div class="sy-cas-bracket">성공/실패 boolean 반환</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK CMPXCHG</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> · <code>CAS</code> (v8.1+)
      </div>
    </div>

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Fetch-and-Add (FAA)</div>
      <div class="sy-cas-fsub">"더하고 이전 값을 받기"</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">읽기<br><span>old = *X</span></div>
        <div class="sy-cas-amp">+</div>
        <div class="sy-cas-box sy-cas-out">더해서 쓰기<br><span>*X = old + δ</span></div>
      </div>
      <div class="sy-cas-bracket">old 반환</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK XADD</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDADD</code> (v8.1+)
      </div>
    </div>

  </div>

  <div class="sy-cas-sep">↓ 이 위에 spinlock을 만들면</div>

  <div class="sy-cas-spin">
    <div class="sy-cas-spin-title">CAS 한 번이 만드는 Spinlock 한 사이클</div>
    <div class="sy-cas-spin-flow">
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">1</div>
        <div class="sy-cas-step-name">acquire 시도</div>
        <div class="sy-cas-step-desc"><code>CAS(lock, 0, 1)</code></div>
      </div>
      <div class="sy-cas-spin-branch">
        <div class="sy-cas-branch sy-cas-branch-ok">
          <div class="sy-cas-branch-h">✓ 성공</div>
          <div class="sy-cas-branch-d">lock = 1<br>임계 구역 진입</div>
        </div>
        <div class="sy-cas-branch sy-cas-branch-no">
          <div class="sy-cas-branch-h">✗ 실패 (이미 1)</div>
          <div class="sy-cas-branch-d">PAUSE 힌트<br>다시 1로</div>
        </div>
      </div>
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">2</div>
        <div class="sy-cas-step-name">임계 구역</div>
        <div class="sy-cas-step-desc">acquire-release<br>memory barrier 포함</div>
      </div>
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">3</div>
        <div class="sy-cas-step-name">release</div>
        <div class="sy-cas-step-desc"><code>store(lock, 0)</code></div>
      </div>
    </div>
  </div>

<style>
.sy-cas { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-cas-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-cas-fams { display: grid; grid-template-columns: 1fr 1.15fr 1fr; gap: 12px; }
.sy-cas-fam { padding: 12px 12px 10px; border: 1px solid #cbd5e0; border-radius: 6px; background: #fff; display: flex; flex-direction: column; }
.sy-cas-fam-hi { border-color: #2b6cb0; background: #ebf8ff; box-shadow: 0 0 0 2px rgba(43, 108, 176, 0.15); }
.sy-cas-fname { font-weight: 700; font-size: 13px; color: #1a202c; text-align: center; }
.sy-cas-fsub { font-size: 11px; color: #718096; text-align: center; margin-top: 2px; margin-bottom: 12px; font-style: italic; }
.sy-cas-flow { display: flex; align-items: center; justify-content: center; gap: 4px; margin: 8px 0; flex-wrap: wrap; }
.sy-cas-box { padding: 6px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 700; text-align: center; min-width: 60px; }
.sy-cas-box span { display: block; font-family: monospace; font-size: 9.5px; font-weight: 500; margin-top: 2px; opacity: 0.85; }
.sy-cas-in  { background: #fef5e7; color: #7b341e; }
.sy-cas-cmp { background: #ebf8ff; color: #2c5282; }
.sy-cas-out { background: #c6f6d5; color: #22543d; }
.sy-cas-amp { font-weight: 700; color: #2d3748; font-size: 14px; padding: 0 2px; }
.sy-cas-bracket { text-align: center; padding: 6px 8px; margin: 6px 0; background: #edf2f7; border-radius: 3px; font-size: 10.5px; font-weight: 700; color: #4a5568; letter-spacing: 0.02em; }
.sy-cas-isa { margin-top: auto; padding-top: 8px; border-top: 1px dashed #cbd5e0; font-size: 11px; line-height: 1.6; color: #4a5568; }
.sy-cas-arch { display: inline-block; min-width: 38px; padding: 1px 6px; margin-right: 6px; background: #4a5568; color: #fff; border-radius: 3px; font-size: 9.5px; font-weight: 700; text-align: center; }
.sy-cas-isa code { background: #edf2f7; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 10.5px; color: #2b6cb0; font-weight: 700; }

.sy-cas-sep { text-align: center; margin: 18px 0 10px; font-size: 11.5px; color: #718096; font-weight: 700; letter-spacing: 0.04em; }

.sy-cas-spin { padding: 12px 14px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-cas-spin-title { font-size: 12.5px; font-weight: 700; color: #2d3748; text-align: center; margin-bottom: 12px; }
.sy-cas-spin-flow { display: grid; grid-template-columns: 1fr 1.4fr 1fr 1fr; gap: 8px; align-items: stretch; }
.sy-cas-spin-step { padding: 10px 10px; background: #edf2f7; border-radius: 5px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.sy-cas-step-num { width: 22px; height: 22px; line-height: 22px; background: #2b6cb0; color: #fff; border-radius: 50%; font-weight: 700; font-size: 11px; }
.sy-cas-step-name { font-weight: 700; font-size: 11.5px; color: #1a202c; }
.sy-cas-step-desc { font-size: 10.5px; color: #4a5568; }
.sy-cas-step-desc code { background: #cbd5e0; padding: 1px 4px; border-radius: 2px; font-family: monospace; color: #2c5282; font-size: 10px; font-weight: 700; }
.sy-cas-spin-branch { display: grid; grid-template-rows: 1fr 1fr; gap: 4px; }
.sy-cas-branch { padding: 6px 8px; border-radius: 4px; }
.sy-cas-branch-ok { background: #c6f6d5; color: #22543d; }
.sy-cas-branch-no { background: #fed7d7; color: #742a2a; }
.sy-cas-branch-h { font-weight: 700; font-size: 11px; }
.sy-cas-branch-d { font-size: 10px; line-height: 1.35; margin-top: 2px; }

[data-mode="dark"] .sy-cas { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-cas-title { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-fam { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-cas-fam-hi { background: #1a365d; border-color: #4299e1; }
[data-mode="dark"] .sy-cas-fname { color: #f7fafc; }
[data-mode="dark"] .sy-cas-fsub { color: #a0aec0; }
[data-mode="dark"] .sy-cas-in  { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-cas-cmp { background: #1a365d; color: #90cdf4; }
[data-mode="dark"] .sy-cas-out { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-cas-amp { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-bracket { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-cas-isa { color: #cbd5e0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-cas-arch { background: #cbd5e0; color: #1a202c; }
[data-mode="dark"] .sy-cas-isa code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-cas-sep { color: #a0aec0; }
[data-mode="dark"] .sy-cas-spin { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-cas-spin-title { color: #e2e8f0; }
[data-mode="dark"] .sy-cas-spin-step { background: #1a202c; }
[data-mode="dark"] .sy-cas-step-name { color: #f7fafc; }
[data-mode="dark"] .sy-cas-step-desc { color: #cbd5e0; }
[data-mode="dark"] .sy-cas-step-desc code { background: #4a5568; color: #90cdf4; }
[data-mode="dark"] .sy-cas-branch-ok { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-cas-branch-no { background: #742a2a; color: #feb2b2; }

@media (max-width: 768px) {
  .sy-cas { padding: 14px 10px 12px; }
  .sy-cas-title { font-size: 13px; }
  .sy-cas-fams { grid-template-columns: 1fr; gap: 10px; }
  .sy-cas-fam { padding: 10px 10px 8px; }
  .sy-cas-fname { font-size: 12px; }
  .sy-cas-spin-flow { grid-template-columns: 1fr; gap: 6px; }
  .sy-cas-spin-step { padding: 8px 8px; }
  .sy-cas-spin-branch { grid-template-rows: auto; grid-template-columns: 1fr 1fr; }
}
</style>
</div>

CAS가 가장 일반적이고 강력합니다. **lock-free 자료구조의 기본 단위**가 되기 때문입니다 (Part 13에서 본격). TAS는 spinlock 같은 단순 mutual exclusion에 충분하고, FAA는 counter 증가나 ticket lock의 핵심 연산입니다.

> **잠깐, 이건 짚고 넘어갑시다.** "CAS"와 "atomic"은 같은 말입니까?
>
> 다릅니다. **Atomic operation**은 "한 단계로 분리 불가능하게 일어나는 모든 연산"의 일반 개념입니다. **CAS는 atomic operation의 한 종류**일 뿐이고, 다른 형제로 TAS, FAA, LL/SC, atomic load/store가 있습니다. C++의 `std::atomic<T>`은 이런 명령들을 추상화한 인터페이스이며, `compare_exchange_weak`이 CAS, `fetch_add`가 FAA에 매핑됩니다.

### Spinlock의 CAS 기반 구현

CAS로 spinlock을 만들면 다음과 같습니다.

```cpp
struct Spinlock {
    std::atomic<bool> locked{false};

    void acquire() {
        bool expected = false;
        while (!locked.compare_exchange_weak(
                expected, true,
                std::memory_order_acquire)) {
            expected = false;       /* CAS 실패 시 변형됨 */
            while (locked.load(std::memory_order_relaxed))
                __builtin_ia32_pause();  /* x86 PAUSE 힌트 */
        }
    }

    void release() {
        locked.store(false, std::memory_order_release);
    }
};
```

여기서 두 가지를 짚을 만합니다.

1. **acquire / release 메모리 순서**: 락을 잡은 뒤 쓴 값들이 다른 스레드가 락을 다시 잡은 뒤에도 보이도록 보장합니다. 자세한 건 Part 12.
2. **`PAUSE` 힌트**: x86은 spin 루프에 PAUSE를 끼우면 power 소비를 줄이고 메모리 순서 위반 페널티를 피합니다. ARM에서는 `YIELD`가 비슷한 역할.

다음 그림은 CAS 한 번이 어떻게 spinlock의 한 사이클을 만드는지 보여줍니다.

<!-- DIAGRAM: sy-cas (CAS 동작 + spinlock 구성) -->

### Spin이냐 Sleep이냐 — 결정 규칙

같은 atomic 위에 정책만 바꾸면 spinlock과 mutex가 만들어집니다. 둘 중 무엇을 쓸지는 임계 구역 길이와 컨텍스트 스위치 비용의 비교입니다.

| 조건 | Spin이 유리 | Sleep이 유리 |
|------|-----------|-----------|
| 임계 구역 길이 | < 1μs | > 10μs |
| 스레드 수 vs 코어 수 | ≤ | > |
| 환경 | 인터럽트 핸들러, RT 커널 | 유저 공간 일반 코드 |

현대의 mutex 구현은 그래서 **adaptive** 입니다. 짧게 spin한 후에도 못 잡으면 sleep으로 전환합니다. Linux glibc의 NPTL이 그렇고, Windows의 SRWLock도 그렇습니다.

---

## Part 4: OS-specific 프리미티브

### Linux futex — fast userspace mutex (2002)

`pthread_mutex_lock`을 호출하면 매번 시스템 콜이 일어나야 합니까? 락이 비어 있다면 굳이 커널을 부를 이유가 없습니다. 이 통찰에서 나온 것이 **futex**입니다.

Hubertus Franke, Rusty Russell, Matthew Kirkwood가 2002년 Linux에 도입했습니다. 핵심 아이디어:

위 의사 코드는 흔히 인용되는 **3-state mutex 구현 예** (0 unlocked, 1 locked-no-waiters, 2 locked-with-waiters) 입니다. 다만 이 상태 인코딩은 **유저 공간 라이브러리의 정책 선택**이지 futex 자체의 의미가 아닙니다 — futex는 커널이 제공하는 일반적 **wait/wake 빌딩 블록**이고, 그 위에 mutex/semaphore/condvar 같은 추상이 각자 다른 상태 인코딩으로 만들어집니다. unlock 시점에 대기자 유무를 알아야 wake 시스템 콜을 부를지 결정할 수 있기 때문에 위 구현은 두 비트가 필요합니다.

futex 한 번의 비용 — 락이 비어 있을 때 — 은 약 10~20ns로 시스템 콜(~수백 ns)의 1/10 이하입니다. 이게 Linux의 **대부분의 user-space blocking lock 구현** (`pthread_mutex`, `sem_t`, glibc의 `std::mutex` 등) 이 futex 위에 만들어진 이유입니다.

<div class="sy-futex">
  <div class="sy-futex-title">futex — fast path vs slow path 분기</div>

  <div class="sy-futex-states">
    <span class="sy-futex-stag">상태</span>
    <span class="sy-futex-st sy-futex-st-0">0 unlocked</span>
    <span class="sy-futex-st sy-futex-st-1">1 locked · 대기자 없음</span>
    <span class="sy-futex-st sy-futex-st-2">2 locked · 대기자 있음</span>
  </div>

  <div class="sy-futex-cols">
    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_lock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>CAS(m, 0, 1)</code></div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ 성공: lock 획득, 끝</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ 실패: 누가 이미 잡음</div>
        </div>
        <div class="sy-futex-cost">~10ns · CAS 1번 · syscall 없음</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>atomic_xchg(m, 2)</code> · 상태를 "대기자 있음"으로</div>
        <div class="sy-futex-line"><code>futex_wait(m, 2)</code> syscall · 커널 wait queue에 들어가 sleep</div>
        <div class="sy-futex-cost">~수백 ns + context switch · sleep 시간 추가</div>
      </div>
    </div>

    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_unlock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>fetch_sub(m, 1)</code> → 이전 값 확인</div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ 이전이 1: 대기자 없음, 끝</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ 이전이 2: 대기자 있음</div>
        </div>
        <div class="sy-futex-cost">~10ns · atomic 1번 · syscall 없음</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>store(m, 0)</code> · unlock</div>
        <div class="sy-futex-line"><code>futex_wake(m, 1)</code> syscall · 대기자 한 명 깨움</div>
        <div class="sy-futex-cost">~수백 ns · 깨운 스레드는 다시 lock 시도</div>
      </div>
    </div>
  </div>

  <div class="sy-futex-key">
    <strong>핵심 통찰</strong> — 90%+ 시간에 락이 비어 있다는 통계적 사실에 의존합니다. 락이 비어 있으면 모든 게 user space의 atomic 명령 한 번으로 끝나고 — kernel을 부르는 비용을 피합니다. 경합이 있을 때만 kernel에 들어가 wait queue에 등록합니다.
    Windows SRWLock도, macOS os_unfair_lock도 같은 사상의 변형입니다.
  </div>

<style>
.sy-futex { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-futex-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-futex-states { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 10px 12px; background: #edf2f7; border-radius: 5px; font-size: 11.5px; }
.sy-futex-stag { font-weight: 700; color: #2d3748; padding-right: 6px; border-right: 1px solid #cbd5e0; }
.sy-futex-st { padding: 3px 8px; border-radius: 3px; font-family: monospace; font-weight: 700; font-size: 11px; }
.sy-futex-st-0 { background: #c6f6d5; color: #22543d; }
.sy-futex-st-1 { background: #fef5e7; color: #7b341e; }
.sy-futex-st-2 { background: #fed7d7; color: #742a2a; }
.sy-futex-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.sy-futex-col { display: flex; flex-direction: column; gap: 10px; }
.sy-futex-ch { font-weight: 700; font-size: 13.5px; color: #1a202c; text-align: center; padding: 6px 0; }
.sy-futex-step { padding: 10px 12px; border-radius: 6px; border: 1px solid; }
.sy-futex-step-fast { background: #ebf8ff; border-color: #4299e1; }
.sy-futex-step-slow { background: #fff5f5; border-color: #fc8181; }
.sy-futex-zone { font-size: 10px; font-weight: 800; letter-spacing: 0.08em; color: #2b6cb0; text-transform: uppercase; margin-bottom: 6px; }
.sy-futex-zone-kernel { color: #c53030; }
.sy-futex-line { font-size: 11.5px; padding: 3px 0; color: #2d3748; }
.sy-futex-line code { background: #fff; padding: 1px 6px; margin-right: 4px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; font-size: 11px; }
.sy-futex-branch { padding: 6px 0 4px; font-size: 11px; }
.sy-futex-arrow { padding: 2px 0; font-weight: 600; }
.sy-futex-arrow-ok { color: #2f855a; }
.sy-futex-arrow-no { color: #c53030; }
.sy-futex-cost { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #cbd5e0; font-size: 10.5px; color: #4a5568; font-style: italic; }
.sy-futex-key { margin-top: 16px; padding: 12px 14px; background: #fffbeb; border-left: 3px solid #f6ad55; border-radius: 3px; font-size: 12px; color: #744210; line-height: 1.55; }
.sy-futex-key strong { color: #c05621; }

[data-mode="dark"] .sy-futex { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-futex-title { color: #e2e8f0; }
[data-mode="dark"] .sy-futex-states { background: #2d3748; }
[data-mode="dark"] .sy-futex-stag { color: #e2e8f0; border-right-color: #4a5568; }
[data-mode="dark"] .sy-futex-st-0 { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-futex-st-1 { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-futex-st-2 { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-futex-ch { color: #f7fafc; }
[data-mode="dark"] .sy-futex-step-fast { background: #1a365d; border-color: #4299e1; }
[data-mode="dark"] .sy-futex-step-slow { background: #742a2a; border-color: #fc8181; }
[data-mode="dark"] .sy-futex-zone { color: #90cdf4; }
[data-mode="dark"] .sy-futex-zone-kernel { color: #feb2b2; }
[data-mode="dark"] .sy-futex-line { color: #e2e8f0; }
[data-mode="dark"] .sy-futex-line code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-futex-arrow-ok { color: #9ae6b4; }
[data-mode="dark"] .sy-futex-arrow-no { color: #feb2b2; }
[data-mode="dark"] .sy-futex-cost { color: #a0aec0; border-top-color: #4a5568; }
[data-mode="dark"] .sy-futex-key { background: #5f370e; color: #fbd38d; }
[data-mode="dark"] .sy-futex-key strong { color: #fbd38d; }

@media (max-width: 768px) {
  .sy-futex { padding: 14px 10px 12px; }
  .sy-futex-title { font-size: 13px; }
  .sy-futex-cols { grid-template-columns: 1fr; gap: 14px; }
  .sy-futex-step { padding: 8px 10px; }
  .sy-futex-line { font-size: 10.5px; }
  .sy-futex-line code { font-size: 10px; }
  .sy-futex-cost { font-size: 9.5px; }
  .sy-futex-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

> **잠깐, 이건 짚고 넘어갑시다.** "fast path"와 "slow path"는 일반적으로 어떻게 갈립니까?
>
> 락 구현에서 fast path는 **경합이 없을 때 가능한 한 빠르게 끝내는 경로**이고, slow path는 **경합이 있을 때 보조 작업이 필요한 경로**입니다. 거의 모든 현대 동기화 프리미티브 — futex, SRWLock, os_unfair_lock, parking_lot — 가 이 패턴을 따릅니다. Fast path는 CAS 1~2개, slow path는 커널 진입이나 별도 wait queue 관리입니다. 90% 이상의 시간에 락이 비어 있다는 통계적 사실에 의존하는 설계입니다.

### Windows SRWLock과 CRITICAL_SECTION

Windows에는 동기화 프리미티브가 여러 세대 있고, 시기마다 트레이드오프가 다릅니다.

**Mutex (커널 객체)**: 가장 오래된 것. 핸들 기반이며 프로세스 간 공유가 가능합니다. 그러나 모든 lock/unlock이 시스템 콜이라 느립니다. ~수백 ns.

**CRITICAL_SECTION**: NT 4 시절(1996) 도입. 유저 공간 atomic으로 fast path를 처리하고, 대기 시점에만 `WaitForSingleObject` 커널 이벤트로 sleep. futex보다 5년 빠른 같은 사상입니다. 단점은 구조체가 무겁다는 것(약 40 바이트, 내부 카운터·핸들 포함)과 프로세스 내부에서만 동작한다는 것.

**SRWLock (Slim Reader/Writer Lock)**: Windows Vista(2007) 도입. 8바이트 포인터 크기, futex와 거의 동일한 fast/slow path 설계, RWLock 의미. 초기화 함수도 필요 없습니다 (`= SRWLOCK_INIT`). 새 코드에서는 거의 항상 SRWLock이 답입니다.

```c
SRWLOCK lock = SRWLOCK_INIT;

AcquireSRWLockExclusive(&lock);   /* writer lock */
/* ... */
ReleaseSRWLockExclusive(&lock);

AcquireSRWLockShared(&lock);      /* reader lock */
/* ... */
ReleaseSRWLockShared(&lock);
```

내부적으로 SRWLock은 8바이트 atomic 한 개에 다음을 패킹합니다: locked bit, waiting bit, waking bit, reader count, 그리고 wait queue head pointer의 상위 비트. CAS 한 번으로 fast path를 처리하기 위한 비트 패킹입니다.

**Condition Variable**: SRWLock과 짝을 이루는 `CONDITION_VARIABLE`도 같은 시기 도입.

> **잠깐, 이건 짚고 넘어갑시다.** `CRITICAL_SECTION`과 `Mutex` 중 어느 쪽을 써야 합니까?
>
> 단일 프로세스 안이고 새 코드라면 **SRWLock**이 답입니다. 더 가볍고 RWLock까지 됩니다. `CRITICAL_SECTION`은 오래된 코드와의 호환을 위해서만, `Mutex`(커널 객체)는 프로세스 간 동기화나 named mutex가 필요할 때만 씁니다.

### macOS os_unfair_lock과 그 가족

macOS는 BSD pthread를 기반으로 하지만, 추가로 Mach 포트 기반 동기화와 Apple 고유 락들이 있습니다.

**pthread_mutex_t**: 표준. 내부적으로 Mach `__ulock_wait` / `__ulock_wake` 시스템 콜을 씁니다 (Linux futex의 macOS 등가물). fast/slow path 구조 동일.

**os_unfair_lock**: macOS 10.12 / iOS 10 (2016) 도입. **`OSSpinLock`을 대체하기 위해** 만들어졌습니다. OSSpinLock은 priority inversion에 취약했습니다 — 낮은 우선순위 스레드가 락을 잡은 채로 P/E 코어 강등되면 높은 우선순위 스레드가 영원히 spin할 수 있습니다.

```c
os_unfair_lock lock = OS_UNFAIR_LOCK_INIT;

os_unfair_lock_lock(&lock);
/* ... */
os_unfair_lock_unlock(&lock);
```

이름의 "unfair"는 의도적입니다. **FIFO 공정성을 포기하고** 대신 락을 잡고 있는 스레드의 정보를 락에 기록해 둡니다. 그래서 priority inversion이 감지되면 잡고 있는 스레드의 priority를 **임시로 올립니다 (priority donation)**. 이걸 가능하게 한 것이 4바이트 atomic에 owner thread ID를 인코딩해 둔 설계입니다.

> os_unfair_lock의 4바이트 안에는 owner thread의 mach thread port id가 들어 있습니다. 이를 통해 커널은 contended path에서 누가 락을 잡고 있는지 알 수 있고, QoS 상속(boost)을 자동 수행합니다. 9편에서 다룬 QoS와 직접 연결됩니다.

**OSSpinLock**: deprecated. 새 코드에서는 절대 쓰지 말아야 합니다.

**NSLock / @synchronized**: Objective-C 객체 단위 monitor. 모든 NSObject가 잠재적으로 락을 가질 수 있습니다. 자바의 `synchronized`와 같은 사상이지만 비용이 큽니다.

**Dispatch semaphore (`dispatch_semaphore_t`)**: GCD의 카운팅 semaphore. P/V 의미.

### 세 OS의 같은 사상

| OS | uncontended (fast) | contended (slow) | 추천 신규 락 |
|------|------------------|------------------|--------------|
| Linux | atomic CAS | `futex(WAIT/WAKE)` syscall | `pthread_mutex`, `std::mutex` |
| Windows | atomic CAS | `NtWaitForAlertByThreadId` (Win8+) | `SRWLock` |
| macOS | atomic CAS | `__ulock_wait/wake` syscall | `os_unfair_lock` |

세 OS가 다른 이름의 다른 API를 제공하지만 공통점은 다음과 같습니다.

1. fast path는 유저 공간 atomic 한두 개
2. slow path만 커널 wait queue
3. RWLock이 필요하면 비트 패킹으로 reader count 추가

다만 **priority inheritance/donation 처리는 OS마다 다릅니다.** macOS `os_unfair_lock`은 4바이트 안에 owner thread ID를 인코딩해 커널이 boost 대상을 즉시 알 수 있게 했고, Linux는 별도의 `PI_futex` 모드 (PTHREAD_PRIO_INHERIT 속성으로 활성화) 에서만 owner를 기록해 RT 작업의 priority inheritance를 지원합니다. Windows의 SRWLock과 CRITICAL_SECTION은 기본적으로 priority inheritance를 보장하지 않으며 — 이 부분은 Part 11(데드락과 priority inversion)에서 다시 다룹니다.

C++ 표준 라이브러리, Rust `parking_lot`, Java `j.u.c.locks`는 모두 이 OS API들 위에 만들어집니다.

---

## Part 5: 하드웨어가 락을 실현하는 방법

지금까지 "CAS는 atomic하게 일어난다"고 말해 왔습니다. 그런데 그게 실제로 어떻게 가능합니까? **여러 코어가 동시에 같은 주소를 만질 때 한 코어만 통과시키는 메커니즘**이 CPU 내부에 있어야 합니다. 그 메커니즘이 **cache coherence**이고, 그 위에서 atomic 명령이 동작합니다.

### CPU 캐시 계층 — 왜 여러 단계입니까

현대 CPU는 메모리에 직접 접근하지 않습니다. 코어와 DRAM 사이에 여러 단계의 캐시가 있습니다.

| 계층 | 크기 (코어당/공유) | 접근 시간 | 누가 가집니까 |
|------|------------------|---------|-----------|
| Register | ~32개 | 0 cycle | 코어 단독 |
| L1 D-cache | 32~48KB | 4~5 cycle | 코어 단독 |
| L1 I-cache | 32~48KB | 4~5 cycle | 코어 단독 |
| L2 | 256KB~1MB | 12~15 cycle | 코어 단독 (보통) |
| L3 (LLC) | 4~64MB | 30~50 cycle | 같은 socket의 코어들 공유 |
| DRAM | GB | 100~300 cycle (200~400ns) | 모두 |
| 다른 socket DRAM | GB | 200~600 cycle | NUMA |

캐시의 단위는 **cache line**이고, 거의 모든 현대 x86/ARM에서 **64바이트**입니다. CPU가 메모리에서 1바이트를 읽어도 64바이트를 통째로 가져옵니다.

> **잠깐, 이건 짚고 넘어갑시다.** 코어가 각자 L1을 가지면 같은 변수의 값이 코어마다 다를 수 있지 않습니까?
>
> 정확히 그 문제를 푸는 것이 **cache coherence protocol** 입니다. 여러 코어가 같은 cache line의 사본을 가질 수 있지만, 한 코어가 그 line에 쓰는 순간 다른 코어의 사본을 무효화하거나 갱신해 모순을 막습니다. 가장 널리 쓰이는 프로토콜이 MESI(Intel)와 그 변형 MOESI(AMD)입니다.

### MESI 프로토콜

각 cache line은 4가지 상태 중 하나를 가집니다.

| 상태 | 의미 | 다른 코어 |
|------|------|---------|
| **M (Modified)** | 이 코어만 가지고 있고, DRAM과 다름 (dirty) | 사본 없음 |
| **E (Exclusive)** | 이 코어만 가지고 있고, DRAM과 같음 (clean) | 사본 없음 |
| **S (Shared)** | 여러 코어가 같은 값을 가지고 있음 (clean) | 같은 값 있음 |
| **I (Invalid)** | 이 코어의 사본은 무효함 | (다른 곳에 있음) |

핵심 규칙은 단 하나입니다.

> **한 cache line이 M 상태이면 그 코어만 그 line을 가집니다.**

쓰기 작업이 일어나면 다른 코어들의 그 line은 모두 I로 떨어집니다. 이걸 가능하게 하기 위해 코어들은 **coherence message**를 주고받습니다.

| 메시지 | 의미 |
|---------|------|
| Read | "이 line을 주세요 (읽기 목적)" |
| Read-for-Ownership (RFO) | "이 line을 주세요 (쓰기 목적)" — 다른 코어 사본 무효화 요청 |
| Invalidate | "이 line의 사본을 버려주세요" |
| Read-Response | "여기 그 line이 있습니다" |

한 줄로 요약하면 — **한 cache line이 누구의 것이고, 누구의 사본은 아직 유효한지를 추적하는 4상태(M/E/S/I) 기계**입니다. 한 코어가 line에 쓰면 다른 사본은 모두 I로 떨어지고, 이게 atomic 명령이 "한 번에 한 명"을 만들어내는 메커니즘입니다.

다음 시각화는 한 cache line이 두 코어 사이를 오가는 모습을 7단계로 추적합니다. 깊이 들어가는 부록이라 접어 두었습니다 — 필요할 때 펼쳐 보세요.

<details class="sy-fold" markdown="1">
<summary>▸ MESI 상태 전이 자세히 보기 — 한 cache line이 코어 간 이동하는 모든 단계</summary>

<div class="sy-mesi">
  <div class="sy-mesi-title">한 cache line의 MESI 전이 — 두 코어가 같은 line에 접근할 때</div>

  <div class="sy-mesi-states">
    <span class="sy-mesi-stag">상태</span>
    <span class="sy-mesi-state sy-mesi-m">M Modified</span>
    <span class="sy-mesi-state sy-mesi-e">E Exclusive</span>
    <span class="sy-mesi-state sy-mesi-s">S Shared</span>
    <span class="sy-mesi-state sy-mesi-i">I Invalid</span>
  </div>

  <div class="sy-mesi-grid">
    <div class="sy-mesi-h">이벤트</div>
    <div class="sy-mesi-h sy-mesi-h-c0">Core 0 line 상태</div>
    <div class="sy-mesi-h sy-mesi-h-c1">Core 1 line 상태</div>
    <div class="sy-mesi-h">coherence 메시지</div>

    <div class="sy-mesi-evt"><strong>t₀</strong> 초기: 아무도 안 가짐</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg">—</div>

    <div class="sy-mesi-evt"><strong>t₁</strong> Core 0 read</div>
    <div class="sy-mesi-cell sy-mesi-e">I → E</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg"><code>Read</code> → DRAM → response</div>

    <div class="sy-mesi-evt"><strong>t₂</strong> Core 0 write (atomic CAS)</div>
    <div class="sy-mesi-cell sy-mesi-m">E → M</div>
    <div class="sy-mesi-cell sy-mesi-i">I</div>
    <div class="sy-mesi-msg">로컬 — 메시지 없음 (이미 Exclusive)</div>

    <div class="sy-mesi-evt"><strong>t₃</strong> Core 1 read 시도</div>
    <div class="sy-mesi-cell sy-mesi-s">M → S</div>
    <div class="sy-mesi-cell sy-mesi-s">I → S</div>
    <div class="sy-mesi-msg"><code>Read</code> → Core 0이 dirty data 공급, DRAM 업데이트</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₄</strong> Core 1 write (atomic CAS) — bouncing 시작</div>
    <div class="sy-mesi-cell sy-mesi-i">S → I</div>
    <div class="sy-mesi-cell sy-mesi-m">S → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO (Read-for-Ownership)</code> → Core 0 사본 무효화</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₅</strong> Core 0 다시 write</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → Core 1에서 dirty data 가져오고 Core 1 무효화</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₆</strong> Core 1 다시 write</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → 또 ping-pong</div>
  </div>

  <div class="sy-mesi-key">
    <strong>같은 line의 M-I 토글이 cache line bouncing입니다.</strong> intra-socket이면 30~50ns/회, cross-socket이면 150~300ns/회. <code>LOCK CMPXCHG</code> 명령 자체는 cache line이 M 상태일 때 ~10ns 이지만, RFO를 거쳐야 하면 30~100배 비싸집니다. <strong>이게 lock contention의 진짜 비용입니다.</strong>
  </div>

<style>
.sy-mesi { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-mesi-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-mesi-states { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; padding: 10px 12px; background: #edf2f7; border-radius: 5px; font-size: 11.5px; }
.sy-mesi-stag { font-weight: 700; color: #2d3748; padding-right: 6px; border-right: 1px solid #cbd5e0; }
.sy-mesi-state { padding: 3px 9px; border-radius: 3px; font-weight: 700; font-size: 11px; }
.sy-mesi-m { background: #fed7d7; color: #742a2a; }
.sy-mesi-e { background: #fbd38d; color: #7b341e; }
.sy-mesi-s { background: #bee3f8; color: #2c5282; }
.sy-mesi-i { background: #e2e8f0; color: #4a5568; }
.sy-mesi-grid { display: grid; grid-template-columns: 1.6fr 1fr 1fr 2fr; gap: 4px; }
.sy-mesi-h { font-size: 11px; font-weight: 700; padding: 8px 8px; background: #2d3748; color: #fff; text-align: center; border-radius: 3px; }
.sy-mesi-h-c0 { background: #2b6cb0; }
.sy-mesi-h-c1 { background: #2f855a; }
.sy-mesi-evt { padding: 8px 8px; font-size: 11.5px; background: #fff; border-radius: 3px; display: flex; align-items: center; }
.sy-mesi-evt strong { color: #c05621; margin-right: 6px; font-family: monospace; }
.sy-mesi-evt-hi { background: #fff5f5; border-left: 3px solid #c53030; }
.sy-mesi-cell { padding: 8px 4px; text-align: center; font-weight: 700; font-size: 11.5px; border-radius: 3px; font-family: monospace; }
.sy-mesi-msg { padding: 8px 10px; font-size: 11px; background: #fff; border-radius: 3px; color: #4a5568; display: flex; align-items: center; }
.sy-mesi-msg code { background: #edf2f7; padding: 1px 6px; border-radius: 3px; font-family: monospace; color: #2b6cb0; font-weight: 700; margin: 0 4px; }
.sy-mesi-msg-hi { background: #fff5f5; }
.sy-mesi-msg-hi code { background: #fed7d7; color: #c53030; }
.sy-mesi-key { margin-top: 16px; padding: 12px 14px; background: #fff5f5; border-left: 3px solid #c53030; border-radius: 3px; font-size: 12px; color: #742a2a; line-height: 1.55; }
.sy-mesi-key strong { color: #c53030; }
.sy-mesi-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; }

[data-mode="dark"] .sy-mesi { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-mesi-title { color: #e2e8f0; }
[data-mode="dark"] .sy-mesi-states { background: #2d3748; }
[data-mode="dark"] .sy-mesi-stag { color: #e2e8f0; border-right-color: #4a5568; }
[data-mode="dark"] .sy-mesi-m { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-mesi-e { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-mesi-s { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-mesi-i { background: #2d3748; color: #a0aec0; }
[data-mode="dark"] .sy-mesi-evt { background: #2d3748; color: #e2e8f0; }
[data-mode="dark"] .sy-mesi-evt-hi { background: #742a2a; border-left-color: #fc8181; }
[data-mode="dark"] .sy-mesi-msg { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-mesi-msg code { background: #1a202c; color: #90cdf4; }
[data-mode="dark"] .sy-mesi-msg-hi { background: #742a2a; }
[data-mode="dark"] .sy-mesi-msg-hi code { background: #1a202c; color: #feb2b2; }
[data-mode="dark"] .sy-mesi-key { background: #742a2a; color: #fed7d7; border-left-color: #fc8181; }
[data-mode="dark"] .sy-mesi-key strong { color: #feb2b2; }
[data-mode="dark"] .sy-mesi-key code { background: #1a202c; }

@media (max-width: 768px) {
  .sy-mesi { padding: 14px 8px 12px; }
  .sy-mesi-title { font-size: 13px; }
  .sy-mesi-states { gap: 5px; padding: 8px 10px; }
  .sy-mesi-state { padding: 2px 6px; font-size: 9.5px; }
  .sy-mesi-grid { grid-template-columns: 1.5fr 0.8fr 0.8fr 1.8fr; gap: 3px; }
  .sy-mesi-h { font-size: 9.5px; padding: 6px 4px; }
  .sy-mesi-evt { font-size: 9.5px; padding: 6px 6px; }
  .sy-mesi-cell { padding: 6px 2px; font-size: 9.5px; }
  .sy-mesi-msg { font-size: 9.5px; padding: 6px 7px; }
  .sy-mesi-msg code { font-size: 9px; padding: 1px 3px; }
  .sy-mesi-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

</details>

<style>
.sy-fold { margin: 20px 0; border: 1px solid #cbd5e0; border-radius: 6px; background: #f7fafc; overflow: hidden; }
.sy-fold > summary { padding: 12px 16px; cursor: pointer; font-weight: 700; font-size: 13.5px; color: #2b6cb0; background: #edf2f7; list-style: none; user-select: none; transition: background 0.15s; }
.sy-fold > summary::-webkit-details-marker { display: none; }
.sy-fold > summary:hover { background: #e2e8f0; }
.sy-fold[open] > summary { background: #ebf8ff; border-bottom: 1px solid #cbd5e0; color: #2c5282; }
.sy-fold > summary::before { content: ""; display: inline-block; width: 0; height: 0; margin-right: 10px; vertical-align: middle; border-left: 6px solid #2b6cb0; border-top: 4px solid transparent; border-bottom: 4px solid transparent; transition: transform 0.15s; }
.sy-fold[open] > summary::before { transform: rotate(90deg); }
.sy-fold > *:not(summary):first-of-type { margin-top: 4px; }

[data-mode="dark"] .sy-fold { background: #1a202c; border-color: #4a5568; }
[data-mode="dark"] .sy-fold > summary { background: #2d3748; color: #90cdf4; }
[data-mode="dark"] .sy-fold > summary:hover { background: #4a5568; }
[data-mode="dark"] .sy-fold[open] > summary { background: #1a365d; border-bottom-color: #4a5568; color: #bee3f8; }
[data-mode="dark"] .sy-fold > summary::before { border-left-color: #90cdf4; }

@media (max-width: 768px) {
  .sy-fold > summary { padding: 10px 12px; font-size: 12px; }
}
</style>

### atomic 명령이 실제로 하는 일

x86에서 `LOCK CMPXCHG`가 실행되면 다음 일이 일어납니다.

1. CPU가 해당 메모리 주소의 cache line을 **Modified 상태로** 가져옵니다 (RFO 메시지로 다른 코어 사본 무효화)
2. 그 line이 M 상태인 동안 — **다른 코어가 동시에 RFO를 보내도 cache coherence 메커니즘이 직렬화** — compare와 swap을 수행합니다
3. line은 M 상태로 남거나 ZEC 시점에 evict 됩니다

요점은 atomic의 "atomicity"가 **하드웨어 cache coherence가 RFO 요청을 직렬화한다는 사실**에서 나온다는 것입니다. 락이 따로 있는 게 아니라, cache line 자체가 한 순간에 한 코어만 M 상태로 가질 수 있다는 cache 프로토콜의 불변식이 곧 lock입니다.

ARM에서는 약간 다릅니다. ARM은 **LL/SC (Load-Linked / Store-Conditional)** 쌍입니다.

```asm
loop:
    LDXR  w0, [x1]        ; load-exclusive, x1 주소를 추적
    CMP   w0, w_expected
    B.NE  fail
    STXR  w2, w_desired, [x1]  ; store-exclusive, x1이 그동안 변경됐으면 실패
    CBNZ  w2, loop        ; 실패면 다시 시도
```

LL/SC의 장점은 CAS의 ABA 문제 일부에 면역이라는 점, 단점은 fail이 가능해 루프가 필요하다는 점입니다.

### cache line bouncing — 락의 진짜 비용

두 코어가 동일한 락을 번갈아 잡으면 무슨 일이 일어납니까?

코어 A가 락을 잡습니다 → cache line이 A에서 M 상태
코어 B가 락을 잡으려고 CAS합니다 → cache line이 A에서 B로 옮겨오면서 A는 I, B는 M
코어 A가 다시 락을 잡습니다 → cache line이 B에서 A로 옮겨오면서 B는 I, A는 M

이 ping-pong이 **cache line bouncing**입니다. 한 번의 bounce 비용은:

| 시나리오 | 비용 |
|---------|------|
| 같은 L3를 공유하는 코어 간 (intra-socket) | ~30~50ns |
| 다른 socket 코어 간 (NUMA, cross-socket) | ~150~300ns |
| 다른 NUMA 노드 | ~수백~1000ns |

`LOCK CMPXCHG` 명령 자체의 비용은 cache line이 이미 M 상태일 때 ~10ns 수준입니다. **bouncing이 있으면 30~100배 비싸집니다.** 이게 lock contention의 진짜 비용이며, 락 자체보다 cache 효과가 더 큰 이유입니다.

> **잠깐, 이건 짚고 넘어갑시다.** cache coherence가 자동으로 일관성을 보장한다면 락은 왜 또 필요합니까?
>
> 두 가지가 다른 보장입니다.
>
> - **Cache coherence**는 "한 cache line의 모든 사본이 결국 일관됩니다"를 약속합니다. 단일 메모리 위치 단위입니다.
> - **Lock**은 "여러 메모리 위치에 걸친 임계 구역을 단일 트랜잭션으로 만듭니다"를 약속합니다. 의미 단위입니다.
>
> 예를 들어 `account_a -= x; account_b += x;`는 두 cache line에 걸친 작업입니다. coherence는 각 line의 일관성을 보장하지만, 둘이 동시에 보이는 것은 락이 보장합니다.

### False sharing — 의도치 않은 cache line bouncing

다음 구조체를 생각해봅시다.

```cpp
struct Counters {
    std::atomic<int> threadA_count;  /* offset 0  */
    std::atomic<int> threadB_count;  /* offset 4  */
};
```

스레드 A는 자기 카운터만, 스레드 B는 자기 카운터만 만집니다. 논리적으로는 공유하는 데이터가 없습니다. 그런데 두 atomic이 **같은 64바이트 cache line에 들어가 있다면**, A의 쓰기가 B의 line을 I로 만들고, B의 쓰기가 A의 line을 I로 만듭니다. 둘은 무의미한 ping-pong을 합니다. 이 현상이 **false sharing**입니다.

해결책은 **cache line 정렬**입니다.

```cpp
struct Counters {
    alignas(64) std::atomic<int> threadA_count;  /* line 0 */
    alignas(64) std::atomic<int> threadB_count;  /* line 1 */
};
```

C++17은 `std::hardware_destructive_interference_size` 상수를 제공해 컴파일 타임에 cache line 크기를 알 수 있게 했습니다.

게임 엔진 코드에서 false sharing은 보통 다음에서 나타납니다.

- 스레드별 통계 배열 — `int hits[NUM_THREADS]` 에서 인접한 슬롯
- producer/consumer ring buffer의 head/tail 포인터
- 작은 Job 구조체들이 배열에 빽빽이 들어 있을 때

측정은 어렵습니다. CPU 카운터 `mem_load_uops_l3_hit_retired.xsnp_hitm` (Intel)이 false sharing을 잡아내는 지표 중 하나입니다. Linux `perf c2c`가 이걸 자동화합니다.

### Memory barrier — 순서 보장의 하드웨어 면

cache coherence는 "값"을 일관되게 만들지만, **"순서"**는 별도 문제입니다. CPU는 명령을 재배치하고, store buffer는 자기 코어의 쓰기를 잠시 가두기 때문입니다.

```cpp
/* Thread A */
data = 42;
ready = true;       /* 이 두 store의 순서가 다른 코어에 보장됩니까? */

/* Thread B */
if (ready)
    use(data);      /* data가 정말 42입니까? */
```

x86은 **TSO (Total Store Order)**라 store-store 재배치가 일어나지 않지만, ARM은 weak ordering이라 위 코드는 깨질 수 있습니다. ARM에서는 두 store 사이에 **memory barrier (`DMB ST`)**가 필요합니다.

락이 우리에게 약속하는 것 중 하나가 이 순서입니다. `mutex.unlock()`이 내부적으로 `release` 의미의 barrier를 포함하고, `mutex.lock()`이 `acquire` 의미의 barrier를 포함하기 때문에 락 안에서 쓴 값이 락 밖에서 일관되게 보입니다.

| Barrier | x86 | ARM | 의미 |
|---------|-----|-----|------|
| store-store | (자동) | DMB ST | 이전 store들이 끝난 뒤 이후 store |
| load-load | (자동) | DMB LD | 이전 load들이 끝난 뒤 이후 load |
| store-load | MFENCE | DMB SY | 이전 store가 globally visible 후 이후 load |
| full | MFENCE | DMB SY | 모든 메모리 op 직렬화 |

Part 12에서 이 부분을 본격적으로 다루지만, **락이 atomic 명령 + barrier의 묶음**이라는 점만 짚고 넘어갑니다.

### 정리: 한 번의 lock이 일으키는 일

`mutex.lock()` / `mutex.unlock()` 한 쌍이 user space부터 하드웨어 cache까지 어떤 단계를 거치는지 한 그림으로 모으면 다음과 같습니다.

<div class="sy-mflow">
  <div class="sy-mflow-title">mutex.lock() → critical section → mutex.unlock() — 모든 계층</div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-lock">mutex.lock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">1</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>cache line ownership 요청</strong><br>
          <span>RFO 메시지를 다른 코어들에 전송</span>
        </div>
        <div class="sy-mflow-cost">~30~300ns</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">2</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>다른 코어 사본 무효화</strong><br>
          <span>그 line을 I 상태로 만들고 데이터 가져옴 (M 상태로)</span>
        </div>
        <div class="sy-mflow-cost">RFO 응답</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">3</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>atomic 명령 실행</strong><br>
          <span><code>LOCK CMPXCHG</code> (x86) · <code>LDXR/STXR</code> (ARM): 0 → 1 시도</span>
        </div>
        <div class="sy-mflow-cost">~10ns</div>
      </div>
      <div class="sy-mflow-branch">
        <div class="sy-mflow-bok"><strong>✓ 성공</strong> — fast path 종료, 임계 구역 진입</div>
        <div class="sy-mflow-bno"><strong>✗ 실패</strong> — slow path로</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">4</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>kernel wait queue 진입</strong><br>
          <span><code>futex_wait</code> / <code>NtWaitForAlertByThreadId</code> / <code>__ulock_wait</code> — 대기 큐에 등록 후 sleep</span>
        </div>
        <div class="sy-mflow-cost">~수백 ns + sleep</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">5</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>acquire 순서 제약</strong><br>
          <span>이 atomic 이후의 메모리 연산이 atomic보다 앞으로 reorder되지 않도록 — ARM은 <code>DMB ISH</code> 또는 <code>LDA*</code>, x86은 일반 load로 충분</span>
        </div>
        <div class="sy-mflow-cost">~수 ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-cs">
    <span class="sy-mflow-cs-h">— 임계 구역 (critical section) —</span>
    <span class="sy-mflow-cs-d">이 동안 다른 누구도 같은 락 위에 들어올 수 없음</span>
  </div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-unlock">mutex.unlock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">6</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>release 순서 제약</strong><br>
          <span>락 안에서 쓴 값들이 unlock store보다 뒤로 reorder되지 않도록 — ARM은 <code>DMB ISH</code> 또는 <code>STL*</code>, x86은 일반 store로 충분</span>
        </div>
        <div class="sy-mflow-cost">~수 ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">7</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>atomic store</strong><br>
          <span>lock 변수를 0으로 설정 (대기자 비트 검사 포함)</span>
        </div>
        <div class="sy-mflow-cost">~5ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">8</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>대기자 깨우기 (있을 때만)</strong><br>
          <span><code>futex_wake</code> / <code>NtAlertThreadByThreadId</code> / <code>__ulock_wake</code></span>
        </div>
        <div class="sy-mflow-cost">~수백 ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-legend">
    <span class="sy-mflow-lg sy-mflow-layer-hw">HW</span>cache coherence / MESI
    <span class="sy-mflow-lg sy-mflow-layer-cpu">CPU</span>atomic 명령 + barrier
    <span class="sy-mflow-lg sy-mflow-layer-os">OS</span>kernel wait queue (slow path만)
  </div>

<style>
.sy-mflow { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-mflow-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 16px; text-align: center; }
.sy-mflow-section { margin-bottom: 4px; }
.sy-mflow-sh { font-size: 12.5px; font-weight: 800; padding: 6px 12px; border-radius: 4px 4px 0 0; display: inline-block; }
.sy-mflow-sh-lock   { background: #2b6cb0; color: #fff; }
.sy-mflow-sh-unlock { background: #2f855a; color: #fff; }
.sy-mflow-steps { padding: 10px 10px; background: #fff; border: 1px solid #cbd5e0; border-radius: 0 6px 6px 6px; }
.sy-mflow-step { display: grid; grid-template-columns: 32px 56px 1fr 90px; gap: 10px; padding: 8px 8px; margin: 3px 0; border-radius: 4px; background: #f7fafc; align-items: center; }
.sy-mflow-step-pivot { background: #ebf8ff; }
.sy-mflow-step-slow { background: #fff5f5; }
.sy-mflow-stnum { width: 26px; height: 26px; line-height: 26px; text-align: center; background: #4a5568; color: #fff; border-radius: 50%; font-weight: 700; font-size: 11.5px; }
.sy-mflow-step-pivot .sy-mflow-stnum { background: #2b6cb0; }
.sy-mflow-step-slow .sy-mflow-stnum { background: #c53030; }
.sy-mflow-stlayer { font-size: 10px; font-weight: 800; padding: 4px 6px; border-radius: 3px; text-align: center; letter-spacing: 0.05em; }
.sy-mflow-layer-hw  { background: #fbd38d; color: #7b341e; }
.sy-mflow-layer-cpu { background: #bee3f8; color: #2c5282; }
.sy-mflow-layer-os  { background: #d6bcfa; color: #44337a; }
.sy-mflow-stbody { font-size: 11.5px; color: #2d3748; line-height: 1.45; }
.sy-mflow-stbody strong { color: #1a202c; }
.sy-mflow-stbody span { display: block; font-size: 10.5px; color: #4a5568; margin-top: 2px; }
.sy-mflow-stbody code { background: #edf2f7; padding: 1px 5px; border-radius: 2px; font-family: monospace; color: #2b6cb0; font-weight: 700; font-size: 10px; }
.sy-mflow-cost { font-size: 11px; color: #c05621; text-align: right; font-weight: 700; font-family: monospace; }
.sy-mflow-branch { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 4px 0; padding: 0 8px; }
.sy-mflow-bok { padding: 6px 10px; background: #c6f6d5; color: #22543d; border-radius: 4px; font-size: 11px; font-weight: 600; }
.sy-mflow-bno { padding: 6px 10px; background: #fed7d7; color: #742a2a; border-radius: 4px; font-size: 11px; font-weight: 600; }
.sy-mflow-bok strong, .sy-mflow-bno strong { font-weight: 800; }
.sy-mflow-cs { text-align: center; padding: 12px 14px; margin: 6px 0; background: linear-gradient(90deg, transparent, #fef5e7, transparent); border-radius: 0; }
.sy-mflow-cs-h { font-size: 12px; font-weight: 700; color: #7b341e; letter-spacing: 0.05em; }
.sy-mflow-cs-d { display: block; font-size: 11px; color: #4a5568; margin-top: 4px; font-style: italic; }
.sy-mflow-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; margin-top: 16px; padding-top: 12px; border-top: 1px dashed #cbd5e0; font-size: 11px; color: #4a5568; }
.sy-mflow-lg { padding: 3px 7px; border-radius: 3px; font-size: 9.5px; font-weight: 800; letter-spacing: 0.05em; margin-right: 4px; }

[data-mode="dark"] .sy-mflow { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-mflow-title { color: #e2e8f0; }
[data-mode="dark"] .sy-mflow-steps { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-mflow-step { background: #1a202c; }
[data-mode="dark"] .sy-mflow-step-pivot { background: #1a365d; }
[data-mode="dark"] .sy-mflow-step-slow { background: #742a2a; }
[data-mode="dark"] .sy-mflow-stbody { color: #e2e8f0; }
[data-mode="dark"] .sy-mflow-stbody strong { color: #f7fafc; }
[data-mode="dark"] .sy-mflow-stbody span { color: #cbd5e0; }
[data-mode="dark"] .sy-mflow-stbody code { background: #2d3748; color: #90cdf4; }
[data-mode="dark"] .sy-mflow-cost { color: #fbd38d; }
[data-mode="dark"] .sy-mflow-layer-hw  { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-mflow-layer-cpu { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-mflow-layer-os  { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-mflow-bok { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-mflow-bno { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-mflow-cs { background: linear-gradient(90deg, transparent, #5f370e, transparent); }
[data-mode="dark"] .sy-mflow-cs-h { color: #fbd38d; }
[data-mode="dark"] .sy-mflow-cs-d { color: #cbd5e0; }
[data-mode="dark"] .sy-mflow-legend { color: #cbd5e0; border-top-color: #4a5568; }

@media (max-width: 768px) {
  .sy-mflow { padding: 14px 8px 12px; }
  .sy-mflow-title { font-size: 13px; }
  .sy-mflow-step { grid-template-columns: 26px 42px 1fr; gap: 6px; padding: 6px 6px; }
  .sy-mflow-cost { grid-column: 1 / -1; text-align: left; padding-left: 76px; font-size: 9.5px; }
  .sy-mflow-stnum { width: 22px; height: 22px; line-height: 22px; font-size: 10px; }
  .sy-mflow-stlayer { font-size: 9px; padding: 3px 4px; }
  .sy-mflow-stbody { font-size: 10.5px; }
  .sy-mflow-stbody span { font-size: 9.5px; }
  .sy-mflow-stbody code { font-size: 9px; }
  .sy-mflow-branch { padding: 0 4px; }
  .sy-mflow-bok, .sy-mflow-bno { font-size: 10px; padding: 5px 8px; }
  .sy-mflow-cs-h { font-size: 11px; }
  .sy-mflow-cs-d { font-size: 10px; }
  .sy-mflow-legend { font-size: 10px; gap: 8px; }
}
</style>
</div>

여기까지가 락의 바닥입니다. 이제 이 모든 메커니즘 위에서 게임 엔진이 어떻게 동기화 문제를 푸는지 보겠습니다.

---

## Part 6: Unity의 동기화 — Main Thread, Job System, DOTS

게임 엔진은 락을 그대로 쓰지 않습니다. 60fps 게임에서 한 프레임은 16.67ms이고, lock contention 한 번이 100~300ns ~ 수 μs까지 들어갑니다. 락이 1000개 일어나면 그것만으로 1ms를 까먹습니다. 그래서 엔진은 **락을 피하는 구조**를 택합니다. 그 구조의 핵심이 두 가지입니다.

1. **Thread affinity**: 어떤 데이터는 한 스레드에서만 만집니다 (그러면 락이 아예 필요 없습니다)
2. **Dependency-based parallelism**: 락 대신 dependency graph를 만들어 read/write 충돌을 컴파일 시점에 막습니다

Unity가 정확히 이 두 가지를 합니다.

### Main Thread 모델

Unity의 모든 `MonoBehaviour` 콜백 — `Update`, `LateUpdate`, `FixedUpdate`, `OnGUI`, `OnTriggerEnter` 등 — 은 **단 하나의 스레드, Main Thread에서 실행됩니다.** 그리고 거의 모든 Unity API (`Transform.position`, `GameObject.Find`, `Component.GetComponent` 등) 는 main thread에서만 호출할 수 있습니다. 다른 스레드에서 호출하면 `UnityException: ... can only be called from the main thread.` 가 던져집니다.

이게 엄청난 단순화입니다. Scene graph 전체에 락이 하나도 없습니다 — 모든 접근이 한 스레드이기 때문입니다.

> **잠깐, 이건 짚고 넘어갑시다.** Unity의 main thread는 OS 스레드 1번입니까?
>
> "1번"이라는 것은 OS 관점에선 무의미합니다. main thread는 Unity 프로세스가 시작할 때 가장 먼저 만들어지는 스레드이며, OS 입장에선 일반 pthread/Win32 thread 중 하나입니다. 다만 Unity 런타임이 이 특정 thread의 ID를 기록해 두고 `IsMainThread()` 체크에 사용합니다. macOS에서는 main thread가 NSRunLoop과 결합되어 있어 UI 이벤트와 함께 돕니다.

main thread 모델의 함정은 한 가지입니다. **무거운 작업을 main thread에서 하면 그대로 프레임 드랍이 됩니다.** 그래서 Unity는 워커 스레드를 따로 띄우고, 그 위에 **Job System**이라는 추상을 제공합니다.

### Unity Job System

Job System은 두 가지를 동시에 합니다.

1. **Native 메모리에 대한 병렬 처리**: managed heap을 건드리지 않으므로 GC와 무관
2. **schedule 시점 race 감지**: dependency graph와 NativeContainer safety로 read/write 충돌을 검사. 어트리뷰트 (`[ReadOnly]`/`[WriteOnly]`/`[NativeDisableContainerSafetyRestriction]`) 는 컴파일러가 읽지만, **실제 충돌 검사는 `Schedule()` 호출 시점의 런타임 검사**이며 `ENABLE_UNITY_COLLECTIONS_CHECKS` 매크로 (Editor/Development 빌드) 에서만 활성화됩니다

기본 사용은 다음과 같습니다.

```csharp
public struct ApplyVelocityJob : IJobParallelFor {
    [ReadOnly]  public NativeArray<float3> velocities;
    [WriteOnly] public NativeArray<float3> positions;
    public float deltaTime;

    public void Execute(int index) {
        positions[index] += velocities[index] * deltaTime;
    }
}

void Update() {
    var job = new ApplyVelocityJob {
        velocities = velocityBuffer,
        positions = positionBuffer,
        deltaTime = Time.deltaTime,
    };
    JobHandle handle = job.Schedule(positionBuffer.Length, 64);  /* batch=64 */
    handle.Complete();
}
```

여기서 `Schedule`은 job을 즉시 실행하지 않고 **dependency graph에 등록**합니다. `JobHandle`은 그 job의 완료를 추적하는 핸들입니다.

#### 내부 동작 — 한 호출이 어디로 갑니까

`Schedule()` 한 줄이 일으키는 일을 단계별로 추적해 봅니다.

1. **컴파일 시점**: `[ReadOnly]`, `[WriteOnly]` 어트리뷰트를 IL2CPP/Burst가 읽어 `velocities`는 read만, `positions`는 write만 한다고 표시
2. **Schedule 호출 (main thread)**:
   - JobHandle을 생성하고 dependency를 등록
   - Job 구조체를 unmanaged 메모리에 복사 (워커가 main heap을 안 건드리도록)
   - NativeContainer들의 AtomicSafetyHandle을 검사 — 다른 진행 중인 job이 같은 컨테이너를 write 중이면 컴파일이 아닌 런타임 예외
3. **워커 스레드 (`Unity Job Worker N`)**:
   - 자체 wait-list에서 job을 꺼냄 (work-stealing deque)
   - `IJobParallelFor`이면 batch(64개씩)로 인덱스 범위를 잘라 분산
   - 각 batch에 대해 `Execute(index)` 호출
4. **Complete 호출 (main thread)**:
   - `handle.Complete()`이 dependency graph에서 모든 transitively dependent job이 끝났는지 확인
   - 끝나지 않았으면 main thread도 워커처럼 job을 훔쳐와 실행 (work-stealing, main thread도 일꾼이 됨)

#### 데이터가 코어 간 어떻게 흐릅니까

`positionBuffer`가 워커 스레드에서 어떻게 만져지는지 cache 단위로 추적해 봅시다.

1. **Schedule 시점**: `positionBuffer`의 처음 64개 슬롯 (16바이트 × 64 = 1024바이트 = 16개 cache line) 이 main thread CPU의 L1/L2에 있습니다 (이전 프레임에 만졌으니까).
2. **워커 스레드 시작**: 워커 N이 `Execute(0)` ~ `Execute(63)`을 받습니다. 이 워커가 다른 코어에 있다면, 64개 슬롯의 cache line들에 대한 **RFO 메시지**가 발송됩니다. main thread의 L1에서 워커 코어의 L1로 line들이 이동합니다 — intra-socket 30~50ns씩, 16개 line이면 첫 batch 워밍업에 ~600ns.
3. **Batch 실행**: 워커가 64개를 순차 처리하면, 그 사이 cache line은 모두 워커 코어의 L1에 머뭅니다. 16바이트 슬롯 4개가 한 line이므로 1 line당 4번 만지는 동안 line은 M 상태 유지 — cache hit.
4. **다음 batch (64~127번)**: 또 16개 line이 새로 워커 L1으로. 이전 16개 line은 evict되거나 워커 L2/L3에 남음.
5. **Complete 시점**: main thread가 결과를 다시 읽으면, 모든 line이 다시 main thread CPU 쪽으로 RFO됩니다.

여기서 보이는 비용은 두 가지입니다.

- **첫 batch warm-up**: cache line이 main → 워커로 이동하는 비용
- **결과 회수**: 워커 → main으로 다시 이동하는 비용

그래서 Job의 입력/출력 크기가 작으면 Job 스케줄링 자체의 비용이 작업 비용을 넘을 수 있습니다. `IJobParallelFor`의 `batchCount` 파라미터 (위 예시의 64)는 이 트레이드오프를 조절합니다. 너무 작으면 batch 경계마다 cache miss와 dispatch 오버헤드, 너무 크면 load balancing이 무너집니다. Unity 문서가 "1보다는 16~64가 보통 좋다"고 가이드하는 이유입니다.

다음 그림이 Job dependency DAG와 워커 매핑을 보여줍니다. 위쪽이 dependency graph (논리적 순서), 아래쪽이 실제 worker thread 매핑 (시간 축).

<div class="sy-unity">
  <div class="sy-unity-title">Unity Job System — dependency DAG와 worker mapping</div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">dependency DAG (논리적 순서)</div>
    <div class="sy-unity-dag">
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-r">VelocityJob<br><span>read input</span></div>
        <div class="sy-unity-node sy-unity-node-r">CollisionJob<br><span>read AABB</span></div>
      </div>
      <div class="sy-unity-arrows">
        <span class="sy-unity-edge"></span>
        <span class="sy-unity-edge"></span>
      </div>
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-w">ApplyVelocityJob<br><span>write Position</span></div>
      </div>
      <div class="sy-unity-arrows">
        <span class="sy-unity-edge sy-unity-edge-c"></span>
      </div>
      <div class="sy-unity-row">
        <div class="sy-unity-node sy-unity-node-r">RenderBoundsJob<br><span>read Position</span></div>
        <div class="sy-unity-node sy-unity-node-r">CullingJob<br><span>read Position</span></div>
      </div>
      <div class="sy-unity-deplabel">read-after-write — 자동으로 dependency 추가됨</div>
    </div>
  </div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">worker thread 매핑 (실제 실행, time →)</div>
    <div class="sy-unity-timeline">
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel sy-unity-tlabel-main">Main Thread</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-main" style="flex: 1">Update / Schedule</div>
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 3">work-stealing</div>
          <div class="sy-unity-blk sy-unity-blk-sync" style="flex: 1">Complete</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 1</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.2">Vel[0..15]</div>
          <div class="sy-unity-blk sy-unity-blk-w" style="flex: 1.4">ApplyVel[0..15]</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">RenderB[0..15]</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 2</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.2">Vel[16..31]</div>
          <div class="sy-unity-blk sy-unity-blk-w" style="flex: 1.4">ApplyVel[16..31]</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">Culling[0..31]</div>
        </div>
      </div>
      <div class="sy-unity-trow">
        <div class="sy-unity-tlabel">Worker 3</div>
        <div class="sy-unity-track">
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1">idle</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">Collision[0..63]</div>
          <div class="sy-unity-blk sy-unity-blk-idle" style="flex: 1.2">wait dep</div>
          <div class="sy-unity-blk sy-unity-blk-r" style="flex: 1.4">RenderB[16..31]</div>
        </div>
      </div>
      <div class="sy-unity-axis"><span>schedule</span><span>parallel reads</span><span>writes</span><span>parallel reads</span><span>sync</span></div>
    </div>
  </div>

  <div class="sy-unity-cache">
    <div class="sy-unity-sec">데이터 흐름 — Worker 1이 ApplyVel[0..15]를 실행하는 동안</div>
    <div class="sy-unity-cacheflow">
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">①</div>
        <div class="sy-unity-cstep-t">Schedule 시점</div>
        <div class="sy-unity-cstep-d">positionBuffer[0..15] cache line이 main CPU L1에 있음</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-rfo">
        <div class="sy-unity-cstep-i">②</div>
        <div class="sy-unity-cstep-t">워커 시작</div>
        <div class="sy-unity-cstep-d">RFO 메시지로 line들이 worker CPU L1로 이동 (~30~50ns × 4 lines)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-hot">
        <div class="sy-unity-cstep-i">③</div>
        <div class="sy-unity-cstep-t">Batch 실행</div>
        <div class="sy-unity-cstep-d">16 슬롯 = 4 lines, 모두 worker L1에 머묾 (cache hit, M 상태)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">④</div>
        <div class="sy-unity-cstep-t">Complete</div>
        <div class="sy-unity-cstep-d">결과 line들이 다시 main CPU로 RFO됨 (read 시점)</div>
      </div>
    </div>
  </div>

  <div class="sy-unity-key">
    <strong>락이 한 번도 없습니다.</strong> Job 사이 dependency를 graph로 표현해 read-after-write 충돌을 schedule 시점에 직렬화하고, 같은 read 권한을 가진 job들은 자유롭게 병렬로 보냅니다. AtomicSafetyHandle은 <code>Schedule()</code> 호출 시점의 런타임 검사로 (Editor/Development 빌드 한정) 컨테이너 사용 권한 충돌을 잡아 예외를 던집니다.
  </div>

<style>
.sy-unity { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-unity-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-unity-block { margin-bottom: 18px; }
.sy-unity-sec { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; padding-left: 6px; border-left: 3px solid #2b6cb0; letter-spacing: 0.02em; }
.sy-unity-dag { padding: 14px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-row { display: flex; gap: 12px; justify-content: center; margin: 6px 0; flex-wrap: wrap; }
.sy-unity-node { padding: 8px 14px; border-radius: 5px; font-weight: 700; font-size: 11.5px; text-align: center; min-width: 120px; }
.sy-unity-node span { display: block; font-size: 10px; font-weight: 500; opacity: 0.85; margin-top: 2px; font-family: monospace; }
.sy-unity-node-r { background: #c6f6d5; color: #22543d; }
.sy-unity-node-w { background: #fed7aa; color: #7b341e; }
.sy-unity-arrows { display: flex; justify-content: center; gap: 80px; height: 14px; align-items: center; }
.sy-unity-edge { width: 1px; height: 14px; background: linear-gradient(to bottom, #cbd5e0 0 60%, transparent 60% 100%); position: relative; }
.sy-unity-edge:after { content: ""; position: absolute; bottom: 0; left: -3px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #4a5568; }
.sy-unity-edge-c { background: #c53030; }
.sy-unity-edge-c:after { border-top-color: #c53030; }
.sy-unity-deplabel { text-align: center; font-size: 10.5px; color: #c53030; font-style: italic; margin-top: 4px; font-weight: 600; }

.sy-unity-timeline { padding: 12px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-trow { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.sy-unity-tlabel { flex: 0 0 86px; font-size: 11px; font-weight: 700; color: #2d3748; text-align: right; }
.sy-unity-tlabel-main { color: #c53030; }
.sy-unity-track { display: flex; flex: 1; height: 30px; border: 1px solid #e2e8f0; border-radius: 3px; overflow: hidden; }
.sy-unity-blk { display: flex; align-items: center; justify-content: center; font-size: 10.5px; font-weight: 700; color: #1a202c; border-right: 1px solid rgba(0,0,0,0.08); }
.sy-unity-blk:last-child { border-right: 0; }
.sy-unity-blk-main { background: #fed7d7; color: #742a2a; }
.sy-unity-blk-r { background: #c6f6d5; color: #22543d; }
.sy-unity-blk-w { background: #fed7aa; color: #7b341e; }
.sy-unity-blk-sync { background: #d6bcfa; color: #44337a; }
.sy-unity-blk-idle { background: #f7fafc; color: #a0aec0; font-style: italic; font-weight: 500; }
.sy-unity-axis { display: flex; justify-content: space-around; margin-top: 6px; padding-left: 94px; font-size: 10px; color: #718096; font-family: monospace; }

.sy-unity-cache { padding: 12px 10px; background: #fff; border-radius: 6px; border: 1px solid #cbd5e0; }
.sy-unity-cacheflow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sy-unity-cstep { flex: 1 1 130px; padding: 10px 10px; background: #ebf8ff; border-radius: 5px; min-height: 80px; display: flex; flex-direction: column; gap: 4px; }
.sy-unity-cstep-rfo { background: #fef5e7; }
.sy-unity-cstep-hot { background: #c6f6d5; }
.sy-unity-cstep-i { font-weight: 800; color: #2b6cb0; font-size: 14px; }
.sy-unity-cstep-rfo .sy-unity-cstep-i { color: #c05621; }
.sy-unity-cstep-hot .sy-unity-cstep-i { color: #2f855a; }
.sy-unity-cstep-t { font-weight: 700; font-size: 11.5px; color: #1a202c; }
.sy-unity-cstep-d { font-size: 10.5px; color: #4a5568; line-height: 1.45; }
.sy-unity-carrow { font-size: 16px; color: #cbd5e0; font-weight: 700; }
.sy-unity-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-unity-key strong { color: #2b6cb0; }

[data-mode="dark"] .sy-unity { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-unity-title { color: #e2e8f0; }
[data-mode="dark"] .sy-unity-sec { color: #90cdf4; border-left-color: #4299e1; }
[data-mode="dark"] .sy-unity-dag { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-node-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-unity-node-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-unity-edge { background: linear-gradient(to bottom, #4a5568 0 60%, transparent 60% 100%); }
[data-mode="dark"] .sy-unity-edge:after { border-top-color: #4a5568; }
[data-mode="dark"] .sy-unity-edge-c { background: #feb2b2; }
[data-mode="dark"] .sy-unity-edge-c:after { border-top-color: #feb2b2; }
[data-mode="dark"] .sy-unity-deplabel { color: #feb2b2; }
[data-mode="dark"] .sy-unity-timeline { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-tlabel { color: #e2e8f0; }
[data-mode="dark"] .sy-unity-tlabel-main { color: #feb2b2; }
[data-mode="dark"] .sy-unity-track { border-color: #4a5568; }
[data-mode="dark"] .sy-unity-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.05); }
[data-mode="dark"] .sy-unity-blk-main { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-unity-blk-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-unity-blk-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-unity-blk-sync { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-unity-blk-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-unity-axis { color: #a0aec0; }
[data-mode="dark"] .sy-unity-cache { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-unity-cstep { background: #1a365d; }
[data-mode="dark"] .sy-unity-cstep-rfo { background: #5f370e; }
[data-mode="dark"] .sy-unity-cstep-hot { background: #22543d; }
[data-mode="dark"] .sy-unity-cstep-i { color: #90cdf4; }
[data-mode="dark"] .sy-unity-cstep-rfo .sy-unity-cstep-i { color: #fbd38d; }
[data-mode="dark"] .sy-unity-cstep-hot .sy-unity-cstep-i { color: #9ae6b4; }
[data-mode="dark"] .sy-unity-cstep-t { color: #f7fafc; }
[data-mode="dark"] .sy-unity-cstep-d { color: #cbd5e0; }
[data-mode="dark"] .sy-unity-carrow { color: #4a5568; }
[data-mode="dark"] .sy-unity-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-unity-key strong { color: #90cdf4; }

@media (max-width: 768px) {
  .sy-unity { padding: 14px 8px 12px; }
  .sy-unity-title { font-size: 13px; }
  .sy-unity-node { padding: 6px 10px; font-size: 10.5px; min-width: 100px; }
  .sy-unity-node span { font-size: 9px; }
  .sy-unity-tlabel { flex-basis: 60px; font-size: 9.5px; }
  .sy-unity-track { height: 24px; }
  .sy-unity-blk { font-size: 9px; }
  .sy-unity-axis { font-size: 8.5px; padding-left: 68px; }
  .sy-unity-cacheflow { flex-direction: column; }
  .sy-unity-cstep { flex-basis: auto; }
  .sy-unity-carrow { transform: rotate(90deg); }
  .sy-unity-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

#### NativeContainer와 AtomicSafetyHandle

Unity는 GC 힙이 아닌 native 메모리에 대해서도 race를 잡아냅니다. 어떻게요?

`NativeArray<T>`, `NativeList<T>`, `NativeQueue<T>` 같은 NativeContainer들은 내부에 **AtomicSafetyHandle**을 가집니다. Editor 빌드와 Development 빌드에서만 활성화되는 디버그 메타입니다. 구조는 대략:

```csharp
struct AtomicSafetyHandle {
    int version;          /* 컨테이너가 dispose 됐는지 */
    AtomicSafetyNodePtr nodePtr;  /* read/write reader list 관리 */
}
```

이 핸들은 다음을 추적합니다.

- **현재 이 컨테이너를 write하고 있는 job**: 0 또는 1개 (있으면 다른 누구도 read조차 못 함)
- **현재 이 컨테이너를 read하고 있는 job들**: N개 (writer는 차단됨)
- **컨테이너가 살아 있는지 (DisposeSentinel)**: dispose된 컨테이너 접근 시 즉시 예외

Schedule 시점에 Unity가 job의 `[ReadOnly]/[WriteOnly]` 표시와 AtomicSafetyHandle 상태를 비교해 **충돌 가능성을 발견하면 예외**를 던집니다. Job을 schedule도 못 하게 막아버리는 셈입니다.

```csharp
var a = new NativeArray<int>(100, Allocator.TempJob);
var jobA = new WriteJob { data = a }.Schedule();          /* a를 write */
var jobB = new ReadJob  { data = a }.Schedule();          /* a를 read — 충돌! */
/* InvalidOperationException: The previously scheduled job WriteJob writes
   to the NativeArray a. You must call JobHandle.Complete() on the job
   before you can read from the NativeArray safely. */
```

해결은 dependency를 명시하는 것입니다.

```csharp
var handleA = jobA.Schedule();
var handleB = jobB.Schedule(handleA);   /* B는 A 끝난 뒤에 */
handleB.Complete();
```

이걸 시키지 않으려면 `[NativeDisableContainerSafetyRestriction]`을 붙이지만, 그건 "race는 내가 책임진다"는 선언입니다. 정말 안전한 경우 — 예: index range가 겹치지 않는 두 job — 에만 써야 합니다.

> **잠깐, 이건 짚고 넘어갑시다.** AtomicSafetyHandle은 production build에서도 동작합니까?
>
> 아닙니다. `ENABLE_UNITY_COLLECTIONS_CHECKS` 매크로가 정의된 Editor와 Development 빌드에서만 활성화됩니다. Release 빌드에서는 컴파일러가 모든 safety check 코드를 제거합니다. **이게 정적 보장은 아닙니다** — Editor에서 잡히지 않았다는 것은 *그때 실행된 코드 경로에서* safety system이 충돌을 못 봤다는 뜻일 뿐, 다른 입력·다른 타이밍에서 race가 안 난다는 증명은 아닙니다. 그래서 production에 내보내기 전 가능한 모든 경로를 통과시키는 테스트가 필요하고, `[NativeDisableContainerSafetyRestriction]`을 쓴 경로는 그 검사조차 우회하므로 더더욱 그렇습니다.

#### Burst — atomic은 어떻게 보장됩니까

요약하면 — **Burst는 IL을 LLVM으로 native code로 컴파일하지만, 평범한 array 접근을 atomic으로 바꿔주지는 않습니다.** atomic이 필요하면 `Interlocked.*`을 명시적으로 호출해야 하고, 그것만이 하드웨어 atomic 명령으로 emit됩니다. 이게 핵심이고, 그 아래 4~5단계는 컴파일러 내부 디테일이라 접어두었습니다.

<details class="sy-fold" markdown="1">
<summary>▸ Burst가 컴파일하는 단계 자세히 — IL → native, atomic emit, NoAlias, SIMD 매핑</summary>

`[BurstCompile]`을 붙인 job은 IL이 아닌 native code로 컴파일됩니다 (LLVM 백엔드). Burst가 NativeArray 접근을 컴파일할 때 일어나는 일:

1. **일반 `array[i]` read/write는 일반 load/store** — atomic이 아닙니다. 그래서 race가 가능하고, 충돌 방지는 schedule 시점의 dependency·safety system에 의존합니다
2. **`Interlocked.*` 같은 명시적 atomic 호출만** x86 `LOCK XADD` / `LOCK CMPXCHG`, ARM `LDADD` / `LDXR-STXR` 등 하드웨어 atomic 명령으로 직접 emit
3. Bounds check를 SIMD-friendly한 형태로 유지하거나, Editor에서만 활성화
4. `[NoAlias]` 표시를 활용해 ptr aliasing 가정 — 컴파일러가 더 공격적으로 최적화
5. SIMD intrinsic (`Unity.Mathematics.float4`) 를 SSE/AVX/NEON으로 매핑

```csharp
[BurstCompile]
public struct CountJob : IJobParallelFor {
    [NativeDisableContainerSafetyRestriction]
    public NativeArray<int> counter;   /* 길이 1, 모든 job이 같은 슬롯 */

    public void Execute(int i) {
        unsafe {
            Interlocked.Increment(ref UnsafeUtility.As<int, int>(
                ref counter.GetUnsafePtrReadOnly()[0]));
        }
    }
}
```

Burst가 `Interlocked.Increment`를 본 순간 그것이 x86이면 `LOCK INC` 또는 `LOCK XADD`로 직접 emit됩니다. 즉 Part 5에서 본 하드웨어 atomic 명령이 그대로 발생합니다. cache line bouncing 비용도 그대로 듭니다.

> **잠깐, 이건 짚고 넘어갑시다.** Job이 같은 cache line의 슬롯에 동시에 쓰면 어떻게 됩니까?
>
> 그게 정확히 **false sharing**입니다. 위 예시처럼 길이 1짜리 counter에 모든 job이 atomic increment를 하면 그 1바이트 (사실은 4바이트, line 1개) 가 코어들 사이를 끊임없이 ping-pong 합니다. 100만 번 호출하면 cache bounce만으로 50~100ms가 사라집니다. 해결책은 스레드 로컬 카운터를 각자 다른 cache line에 두고 마지막에 합치는 것 — `[ThreadStatic]` 또는 `NativeQueue<int>.Concurrent`의 enqueue 패턴.

</details>

#### DOTS / ECS — 시스템 단위 dependency

`SystemBase`나 `ISystem` 기반의 ECS는 위 메커니즘을 한 단계 더 끌어올립니다.

```csharp
public partial struct MoveSystem : ISystem {
    public void OnUpdate(ref SystemState state) {
        new MoveJob { dt = SystemAPI.Time.DeltaTime }
            .ScheduleParallel();
    }
}

[BurstCompile]
public partial struct MoveJob : IJobEntity {
    public float dt;
    void Execute(ref LocalTransform t, in Velocity v) {
        t.Position += v.Value * dt;
    }
}
```

`IJobEntity`는 어떤 Component를 read/write하는지 시그니처에서 자동 추출합니다 (`ref` = write, `in` = read). 이 정보를 소스 생성기가 컴파일 시점에 메타데이터로 만들어 두면, World scheduler가 런타임에 그것을 읽어 다음을 자동으로 처리합니다.

- 같은 Component를 write하는 두 System은 **자동으로 순서가 잡힙니다**
- 서로 다른 Component를 만지는 System들은 **자동으로 병렬로 돌아갑니다**

이게 락이 아니라 dependency graph로 동기화를 푸는 가장 극단적인 예시입니다. 프로그래머가 lock을 한 번도 안 잡지만, scheduler가 schedule 시점에 read/write 권한을 검사해 충돌을 직렬화합니다 (Editor/Development 빌드에서는 safety system이 추가로 동작합니다).

내부적으로 ECS는 Component마다 ReaderWriterLock 의미의 dependency 정보를 유지합니다. 이게 Burst와 합쳐지면 다음 그림처럼 됩니다.

<div class="sy-ecs">
  <div class="sy-ecs-title">DOTS ECS scheduler — Component 권한 분석으로 자동 병렬화</div>

  <div class="sy-ecs-comp">
    <div class="sy-ecs-comp-h">Component 권한 분석 (컴파일 시점)</div>
    <div class="sy-ecs-comp-grid">
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">SpawnSystem</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> Entity 추가/제거</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">MoveJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> LocalTransform.Position</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-r">read</span> Velocity</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">RotateJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> LocalTransform.Rotation</div>
      </div>
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">RenderBoundsJob</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-r">read</span> LocalTransform.Position</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> RenderBounds</div>
      </div>
    </div>
    <div class="sy-ecs-note">scheduler가 read/write 패턴을 보고 자동으로 dependency edge를 추가합니다</div>
  </div>

  <div class="sy-ecs-tl">
    <div class="sy-ecs-tl-h">실행 타임라인 (Frame N)</div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl sy-ecs-tlbl-main">Main</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-main" style="flex: 1">SpawnSystem</div>
        <div class="sy-ecs-blk sy-ecs-blk-sched" style="flex: 0.8">schedule jobs</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 2.2">— work-stealing —</div>
        <div class="sy-ecs-blk sy-ecs-blk-sync" style="flex: 1">SyncPoint</div>
        <div class="sy-ecs-blk sy-ecs-blk-main" style="flex: 1">RenderSystem</div>
      </div>
    </div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl">W1</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.8">idle</div>
        <div class="sy-ecs-blk sy-ecs-blk-w" style="flex: 1.5">MoveJob [Position write]</div>
        <div class="sy-ecs-blk sy-ecs-blk-r" style="flex: 1.5">RenderBoundsJob [Position read]</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.2">idle</div>
      </div>
    </div>
    <div class="sy-ecs-trow">
      <div class="sy-ecs-tlbl">W2</div>
      <div class="sy-ecs-track">
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.8">idle</div>
        <div class="sy-ecs-blk sy-ecs-blk-w" style="flex: 1.5">RotateJob [Rotation write]</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.5">idle (no Position dep)</div>
        <div class="sy-ecs-blk sy-ecs-blk-idle" style="flex: 1.2">idle</div>
      </div>
    </div>
    <div class="sy-ecs-tl-arrows">
      <span class="sy-ecs-arrow-h">↑ 같은 시각 — 다른 Component를 만지므로 락 없이 동시 실행</span>
      <span class="sy-ecs-arrow-d">↑ Position read는 MoveJob 완료 대기 (자동 dependency)</span>
    </div>
  </div>

  <div class="sy-ecs-key">
    <strong>개발자가 락도, dependency도 명시하지 않습니다.</strong> ECS scheduler가 각 job/system의 Component 권한 (<code>ref</code>=write, <code>in</code>=read) 을 읽고 read-after-write 충돌만 직렬화합니다. 결과: 다른 Component를 만지는 작업은 자유롭게 병렬, 같은 Component를 만지면 자동 순서 보장.
  </div>

<style>
.sy-ecs { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-ecs-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-ecs-comp { padding: 12px 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; margin-bottom: 14px; }
.sy-ecs-comp-h { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; }
.sy-ecs-comp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.sy-ecs-comp-cell { padding: 8px 10px; background: #f7fafc; border-radius: 4px; border: 1px solid #e2e8f0; }
.sy-ecs-sys { font-weight: 700; font-size: 11.5px; color: #1a202c; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed #cbd5e0; }
.sy-ecs-perm { font-size: 10.5px; padding: 2px 0; color: #4a5568; font-family: monospace; }
.sy-ecs-r { display: inline-block; padding: 1px 5px; background: #c6f6d5; color: #22543d; border-radius: 2px; font-size: 9.5px; font-weight: 800; margin-right: 4px; }
.sy-ecs-w { display: inline-block; padding: 1px 5px; background: #fed7aa; color: #7b341e; border-radius: 2px; font-size: 9.5px; font-weight: 800; margin-right: 4px; }
.sy-ecs-note { margin-top: 10px; font-size: 11px; color: #2b6cb0; font-style: italic; text-align: center; }
.sy-ecs-tl { padding: 12px 12px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-ecs-tl-h { font-size: 11.5px; font-weight: 700; color: #2b6cb0; margin-bottom: 10px; }
.sy-ecs-trow { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.sy-ecs-tlbl { flex: 0 0 50px; font-size: 11px; font-weight: 700; color: #2d3748; text-align: right; }
.sy-ecs-tlbl-main { color: #c53030; }
.sy-ecs-track { display: flex; flex: 1; height: 28px; border: 1px solid #e2e8f0; border-radius: 3px; overflow: hidden; }
.sy-ecs-blk { display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; padding: 0 4px; text-align: center; border-right: 1px solid rgba(0,0,0,0.06); }
.sy-ecs-blk:last-child { border-right: 0; }
.sy-ecs-blk-main { background: #fed7d7; color: #742a2a; }
.sy-ecs-blk-sched { background: #d6bcfa; color: #44337a; }
.sy-ecs-blk-sync { background: #fbd38d; color: #7b341e; }
.sy-ecs-blk-w { background: #fed7aa; color: #7b341e; }
.sy-ecs-blk-r { background: #c6f6d5; color: #22543d; }
.sy-ecs-blk-idle { background: #f7fafc; color: #a0aec0; font-weight: 500; font-style: italic; }
.sy-ecs-tl-arrows { margin-top: 10px; padding-top: 8px; border-top: 1px dashed #cbd5e0; display: flex; flex-direction: column; gap: 3px; }
.sy-ecs-arrow-h { font-size: 10.5px; color: #2f855a; font-weight: 600; }
.sy-ecs-arrow-d { font-size: 10.5px; color: #c05621; font-weight: 600; }
.sy-ecs-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-ecs-key strong { color: #2b6cb0; }
.sy-ecs-key code { background: #fff; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 11px; color: #2b6cb0; font-weight: 700; }

[data-mode="dark"] .sy-ecs { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-ecs-title { color: #e2e8f0; }
[data-mode="dark"] .sy-ecs-comp { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-comp-h { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-comp-cell { background: #1a202c; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-sys { color: #f7fafc; border-bottom-color: #4a5568; }
[data-mode="dark"] .sy-ecs-perm { color: #cbd5e0; }
[data-mode="dark"] .sy-ecs-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-note { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-tl { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-tl-h { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-tlbl { color: #e2e8f0; }
[data-mode="dark"] .sy-ecs-tlbl-main { color: #feb2b2; }
[data-mode="dark"] .sy-ecs-track { border-color: #4a5568; }
[data-mode="dark"] .sy-ecs-blk { color: #f7fafc; border-right-color: rgba(255,255,255,0.05); }
[data-mode="dark"] .sy-ecs-blk-main { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-ecs-blk-sched { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-ecs-blk-sync { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-blk-w { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-ecs-blk-r { background: #22543d; color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-blk-idle { background: #1a202c; color: #4a5568; }
[data-mode="dark"] .sy-ecs-tl-arrows { border-top-color: #4a5568; }
[data-mode="dark"] .sy-ecs-arrow-h { color: #9ae6b4; }
[data-mode="dark"] .sy-ecs-arrow-d { color: #fbd38d; }
[data-mode="dark"] .sy-ecs-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-ecs-key strong { color: #90cdf4; }
[data-mode="dark"] .sy-ecs-key code { background: #2d3748; color: #90cdf4; }

@media (max-width: 768px) {
  .sy-ecs { padding: 14px 8px 12px; }
  .sy-ecs-title { font-size: 13px; }
  .sy-ecs-comp-grid { grid-template-columns: 1fr 1fr; gap: 5px; }
  .sy-ecs-comp-cell { padding: 6px 8px; }
  .sy-ecs-sys { font-size: 10.5px; }
  .sy-ecs-perm { font-size: 9.5px; }
  .sy-ecs-r, .sy-ecs-w { font-size: 8.5px; padding: 1px 4px; }
  .sy-ecs-tlbl { flex-basis: 36px; font-size: 9.5px; }
  .sy-ecs-track { height: 22px; }
  .sy-ecs-blk { font-size: 8.5px; }
  .sy-ecs-arrow-h, .sy-ecs-arrow-d { font-size: 9.5px; }
  .sy-ecs-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

여기서 RenderBoundsJob이 MoveJob 완료를 기다리는 의존성은 **개발자가 명시하지 않아도** ECS가 자동 추론합니다. 두 job 모두 `LocalTransform.Position`을 만지고, MoveJob이 write, RenderBoundsJob이 read이기 때문에 ECS scheduler가 자동으로 dependency edge를 추가합니다.

#### 한 프레임의 메모리 흐름 — 정리

Unity가 한 프레임 (16.67ms) 안에 일으키는 동기화 관련 일을 시간 순으로 정리하면:

| 시점 | 위치 | 일어나는 일 |
|------|------|-----------|
| 0ms | Main | Input/MonoBehaviour Update — main thread only, 락 없음 |
| 2ms | Main | Job들을 schedule, dependency graph 생성 |
| 2~10ms | Worker 1~N | 워커들이 dependency 순서대로 job 실행, NativeArray cache line이 워커 코어로 RFO 이동 |
| 10ms | Main | `JobHandle.Complete()` 또는 sync point — main도 일꾼이 되어 work-stealing |
| 12ms | Render thread | command buffer가 GPU로 submit (다음 섹션에서) |
| 16ms | GPU | present, 다음 프레임 시작 |

여기까지가 Unity 측면입니다. Unreal은 비슷한 사상이지만 thread 분리가 더 강합니다.

---

## Part 7: Unreal Engine의 동기화

Unreal은 Unity보다 명시적인 **multi-thread 모델**을 가집니다. 엔진 자체가 여러 named thread로 나뉘어 있고, thread 간 통신은 거의 모두 lock-free queue 위에 만들어져 있습니다.

### 네 가지 Named Thread

기본 Unreal 게임은 다음 스레드들이 항상 도는 구조입니다.

| 스레드 | 책임 | OS 스레드 |
|--------|------|----------|
| **Game Thread** | Tick, gameplay 로직, Blueprint, AI | main thread (Unity의 main에 해당) |
| **Render Thread** | high-level 렌더 명령 생성 (FRDG, RHI command 작성) | 별도 OS 스레드 |
| **RHI Thread** | GPU API 호출 (D3D12/Vulkan/Metal/Mantle) | 별도 OS 스레드 |
| **Audio Thread** | 사운드 믹싱, voice 관리 | 별도 OS 스레드 |
| **Worker Threads** | TaskGraph job 실행 | 코어 수만큼 |

핵심 발상은 **각 스레드가 자신만 만지는 데이터를 가지고, 다른 스레드와의 통신은 명시적인 명령 큐를 거친다**는 것입니다. 락을 잡는 대신 데이터의 소유권을 thread에 단단히 묶습니다.

### Game Thread → Render Thread — 한 프레임의 흐름

Unreal의 Render Thread는 Game Thread보다 **보통 1 프레임 뒤에서 동작**합니다 (Epic 공식 문서는 0 또는 1 프레임 behind라고 설명합니다 — Game이 빨리 끝나면 Render가 따라잡을 수도 있고, Render가 무거우면 Game이 다음 프레임에 sync로 막힙니다). 이 글에서는 정상 부하 상태의 "1 프레임 뒤" 케이스를 기준으로 설명합니다. Game이 N번째 프레임 로직을 돌릴 때, Render는 N-1번째의 렌더 명령을 만들고, RHI는 N-2번째를 GPU에 제출합니다.

<div class="sy-upipe">
  <div class="sy-upipe-title">Unreal 4-thread 파이프라인 — 같은 시점, 다른 프레임</div>

  <div class="sy-upipe-grid">
    <div class="sy-upipe-corner">스레드 ↓ / 프레임 →</div>
    <div class="sy-upipe-fh">Frame N</div>
    <div class="sy-upipe-fh">Frame N+1</div>
    <div class="sy-upipe-fh">Frame N+2</div>

    <div class="sy-upipe-th sy-upipe-th-game">Game Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active">N 로직<br><span>Tick, AI, Physics, Blueprint</span></div>
    <div class="sy-upipe-cell">N+1 로직</div>
    <div class="sy-upipe-cell">N+2 로직</div>

    <div class="sy-upipe-th sy-upipe-th-render">Render Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-r">N-1 렌더<br><span>RDG 빌드, FMeshBatch 생성</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N 렌더</div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N+1 렌더</div>

    <div class="sy-upipe-th sy-upipe-th-rhi">RHI Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-h">N-2 submit<br><span>D3D12/Vulkan/Metal API</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N-1 submit</div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N submit</div>

    <div class="sy-upipe-th sy-upipe-th-gpu">GPU</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-g">N-3 draw + present<br><span>실제 픽셀 표시</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-2 draw + present</div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-1 draw + present</div>
  </div>

  <div class="sy-upipe-flow">
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ ENQUEUE_RENDER_COMMAND</div>
      <div class="sy-upipe-fl-d">Game이 Render에 데이터 push (lock-free MPSC queue)</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ RHI command list</div>
      <div class="sy-upipe-fl-d">Render가 RHI에 GPU 명령 dispatch</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ GPU submit</div>
      <div class="sy-upipe-fl-d">RHI가 GPU에 제출, fence로 추적</div>
    </div>
    <div class="sy-upipe-fl sy-upipe-fl-back">
      <div class="sy-upipe-fl-h">← FRenderCommandFence</div>
      <div class="sy-upipe-fl-d">Game이 Render 완료를 기다려야 할 때만 (드물게)</div>
    </div>
  </div>

  <div class="sy-upipe-key">
    <strong>같은 시점에 같은 데이터를 만지는 스레드가 단 하나입니다.</strong> Game이 N을 만드는 동안 Render는 N-1을, RHI는 N-2를 처리하므로 락이 거의 필요 없습니다. 트레이드오프는 입력 지연 +1프레임 — 9편에서 본 1프레임 파이프라이닝의 정확한 구현입니다.
  </div>

<style>
.sy-upipe { margin: 24px 0; padding: 20px 18px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; font-size: 13px; line-height: 1.5; }
.sy-upipe-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; text-align: center; }
.sy-upipe-grid { display: grid; grid-template-columns: 120px 1fr 1fr 1fr; gap: 4px; margin-bottom: 16px; }
.sy-upipe-corner { font-size: 10.5px; color: #718096; font-style: italic; padding: 8px 4px; }
.sy-upipe-fh { font-size: 11.5px; font-weight: 700; color: #2d3748; text-align: center; padding: 8px 4px; background: #edf2f7; border-radius: 3px; }
.sy-upipe-th { font-size: 11.5px; font-weight: 700; color: #fff; padding: 12px 8px; border-radius: 3px; display: flex; align-items: center; justify-content: center; text-align: center; }
.sy-upipe-th-game   { background: #c53030; }
.sy-upipe-th-render { background: #c05621; }
.sy-upipe-th-rhi    { background: #2b6cb0; }
.sy-upipe-th-gpu    { background: #553c9a; }
.sy-upipe-cell { padding: 10px 8px; font-size: 11.5px; font-weight: 700; background: #f7fafc; border-radius: 3px; color: #4a5568; text-align: center; opacity: 0.55; }
.sy-upipe-cell span { display: block; font-size: 10px; font-weight: 500; margin-top: 3px; opacity: 0.85; }
.sy-upipe-cell-active { opacity: 1; box-shadow: 0 0 0 2px rgba(43, 108, 176, 0.25); }
.sy-upipe-cell-r { background: #fed7aa; color: #7b341e; }
.sy-upipe-cell-h { background: #bee3f8; color: #2c5282; }
.sy-upipe-cell-g { background: #d6bcfa; color: #44337a; }
.sy-upipe-cell:not([class*="cell-"]):not(.sy-upipe-cell-active) { background: #fed7d7; color: #742a2a; opacity: 0.55; }
.sy-upipe-grid > .sy-upipe-cell:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #fed7d7; color: #742a2a; }
.sy-upipe-grid > .sy-upipe-cell.sy-upipe-cell-active:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #fc8181; color: #742a2a; }

.sy-upipe-flow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 12px 10px; background: #fff; border: 1px solid #cbd5e0; border-radius: 6px; }
.sy-upipe-fl { padding: 8px 10px; background: #ebf8ff; border-radius: 4px; border-left: 3px solid #2b6cb0; }
.sy-upipe-fl-back { background: #fff5f5; border-left-color: #c53030; }
.sy-upipe-fl-h { font-size: 11px; font-weight: 700; color: #2b6cb0; margin-bottom: 4px; }
.sy-upipe-fl-back .sy-upipe-fl-h { color: #c53030; }
.sy-upipe-fl-d { font-size: 10.5px; color: #4a5568; line-height: 1.4; }
.sy-upipe-key { margin-top: 14px; padding: 12px 14px; background: #ebf8ff; border-left: 3px solid #2b6cb0; border-radius: 3px; font-size: 12px; color: #2c5282; line-height: 1.55; }
.sy-upipe-key strong { color: #2b6cb0; }

[data-mode="dark"] .sy-upipe { background: #1a202c; border-color: #2d3748; }
[data-mode="dark"] .sy-upipe-title { color: #e2e8f0; }
[data-mode="dark"] .sy-upipe-corner { color: #a0aec0; }
[data-mode="dark"] .sy-upipe-fh { color: #e2e8f0; background: #2d3748; }
[data-mode="dark"] .sy-upipe-cell { background: #2d3748; color: #cbd5e0; }
[data-mode="dark"] .sy-upipe-cell-r { background: #7b341e; color: #fbd38d; }
[data-mode="dark"] .sy-upipe-cell-h { background: #2c5282; color: #bee3f8; }
[data-mode="dark"] .sy-upipe-cell-g { background: #553c9a; color: #d6bcfa; }
[data-mode="dark"] .sy-upipe-grid > .sy-upipe-cell:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #742a2a; color: #feb2b2; }
[data-mode="dark"] .sy-upipe-grid > .sy-upipe-cell.sy-upipe-cell-active:not(.sy-upipe-cell-r):not(.sy-upipe-cell-h):not(.sy-upipe-cell-g) { background: #9b2c2c; color: #feb2b2; }
[data-mode="dark"] .sy-upipe-flow { background: #2d3748; border-color: #4a5568; }
[data-mode="dark"] .sy-upipe-fl { background: #1a365d; }
[data-mode="dark"] .sy-upipe-fl-back { background: #742a2a; border-left-color: #fc8181; }
[data-mode="dark"] .sy-upipe-fl-h { color: #90cdf4; }
[data-mode="dark"] .sy-upipe-fl-back .sy-upipe-fl-h { color: #feb2b2; }
[data-mode="dark"] .sy-upipe-fl-d { color: #cbd5e0; }
[data-mode="dark"] .sy-upipe-key { background: #1a365d; color: #bee3f8; }
[data-mode="dark"] .sy-upipe-key strong { color: #90cdf4; }

@media (max-width: 768px) {
  .sy-upipe { padding: 14px 8px 12px; }
  .sy-upipe-title { font-size: 13px; }
  .sy-upipe-grid { grid-template-columns: 80px 1fr 1fr 1fr; gap: 3px; }
  .sy-upipe-corner { font-size: 9px; }
  .sy-upipe-fh { font-size: 10px; padding: 6px 2px; }
  .sy-upipe-th { font-size: 10px; padding: 8px 4px; }
  .sy-upipe-cell { font-size: 10px; padding: 6px 4px; }
  .sy-upipe-cell span { font-size: 8.5px; }
  .sy-upipe-flow { grid-template-columns: 1fr 1fr; gap: 6px; }
  .sy-upipe-fl { padding: 6px 8px; }
  .sy-upipe-fl-h { font-size: 10px; }
  .sy-upipe-fl-d { font-size: 9.5px; }
  .sy-upipe-key { font-size: 11px; padding: 10px 12px; }
}
</style>
</div>

이 파이프라이닝 덕분에 락이 거의 필요 없습니다. 한 시점에 같은 데이터를 만지는 스레드가 하나뿐이기 때문입니다.

### TaskGraph — Unreal의 Job System

`FTaskGraphInterface`가 Unity Job System의 등가물입니다.

```cpp
FGraphEventRef MyTask = FFunctionGraphTask::CreateAndDispatchWhenReady(
    [Data]() {
        // 워커 스레드에서 실행
        ProcessData(Data);
    },
    TStatId(),
    nullptr,                      /* dependency prerequisite */
    ENamedThreads::AnyThread      /* 어느 스레드에서 실행할지 */
);

/* 나중에 결과를 기다리기 */
FTaskGraphInterface::Get().WaitUntilTaskCompletes(MyTask);
```

특징:

- **Named thread 선택 가능**: `GameThread`, `RenderThread`, `RHIThread`, `AnyThread` 중 골라 dispatch
- **Dependency edge 표현**: prerequisite array를 넘기면 그것들이 끝난 뒤 시작
- **자동 work-stealing**: AnyThread는 가장 한가한 worker가 가져감
- **계층적 task**: task 안에서 자식 task를 spawn 가능

### ENQUEUE_RENDER_COMMAND — 락이 보이지 않는 명령 큐

Game Thread에서 Render Thread로 데이터를 전달하는 가장 일반적인 매크로입니다.

```cpp
FVector NewPos = Actor->GetActorLocation();
FRHICommandListImmediate& RHICmdList = ...;

ENQUEUE_RENDER_COMMAND(UpdateActorPos)(
    [NewPos](FRHICommandListImmediate& RHICmdList) {
        /* 이 람다는 Render Thread에서 실행됩니다 */
        UpdateConstantBuffer(RHICmdList, NewPos);
    });
```

이 매크로의 의미는 다음과 같습니다 — **람다를 명령 객체로 만들어 Render Thread의 명령 큐에 enqueue하면, Render Thread는 자기 큐에서 FIFO 순서로 꺼내 실행합니다.** Epic 공식 문서는 내부 큐 구현을 lock-free MPSC로 보장한다고 명시하지는 않으며 (버전마다 달라질 수 있는 구현 디테일), 이 매크로의 계약은 *"순서 보장 + Render Thread에서 실행"* 까지입니다. 개념적으로 multi-producer (worker thread도 enqueue 가능) single-consumer (Render Thread만 pop) 패턴이며, 그래서 일반적으로 lock-free MPSC가 적합한 자리입니다.

> **잠깐, 이건 짚고 넘어갑시다.** lock-free MPSC 큐는 어떻게 락 없이 동작합니까?
>
> 핵심은 **producer는 atomic CAS 또는 atomic exchange로 큐 tail에 노드를 append**하고 **consumer는 단일 스레드이므로 동기화가 필요 없다**는 비대칭을 이용하는 것입니다. 가장 유명한 디자인이 **Vyukov MPSC queue** — atomic exchange 한 번으로 prev tail을 잡고, prev tail의 next 포인터를 새 노드로 갱신합니다. 재시도(retry) 루프 없이 contention을 거의 없앱니다.

다음 코드가 Vyukov MPSC의 핵심입니다.

```cpp
struct Node { std::atomic<Node*> next; T payload; };
std::atomic<Node*> tail;

void push(Node* node) {
    node->next.store(nullptr, std::memory_order_relaxed);
    Node* prev = tail.exchange(node, std::memory_order_acq_rel);
    prev->next.store(node, std::memory_order_release);
}
/* pop은 single-consumer라 atomic이 거의 필요 없음 */
```

이 패턴이 Unreal의 거의 모든 inter-thread 통신에 깔려 있습니다. 그래서 ENQUEUE_RENDER_COMMAND가 매 프레임 수백 번 호출되어도 lock contention이 없습니다.

### FRenderCommandFence — Game이 Render를 기다려야 할 때

가끔은 Game Thread가 "Render Thread에 보낸 명령이 정말 끝났는지" 알아야 합니다. 예를 들어 GPU 리소스를 안전하게 destroy하려면 Render Thread가 그것을 더 이상 안 만지는 것을 보장해야 합니다.

```cpp
FRenderCommandFence Fence;
Fence.BeginFence();      /* 이 시점까지의 모든 render command를 mark */
Fence.Wait();            /* mark된 command가 모두 끝날 때까지 block */
```

`BeginFence`는 Render Thread의 큐에 fence 마커를 enqueue 합니다. `Wait`은 Game Thread가 fence가 처리될 때까지 sleep (FEvent로 wait). 이게 Game ↔ Render 사이의 거의 유일한 명시적 동기화 포인트입니다.

### FCriticalSection / FRWLock — 명시적 락

물론 가끔 명시적 락이 필요합니다. Unreal은 다음을 제공합니다.

- **`FCriticalSection`**: Windows의 `CRITICAL_SECTION`을 추상화 (다른 OS는 pthread_mutex). 일반 mutex.
- **`FRWLock`**: Reader-Writer lock. macOS는 `os_unfair_lock` 대신 pthread_rwlock으로 매핑.
- **`FScopeLock`**: RAII 헬퍼 (`std::lock_guard` 등가).
- **`TQueue<T, EQueueMode::Spsc>`**: lock-free single-producer single-consumer 큐.
- **`TQueue<T, EQueueMode::Mpsc>`**: lock-free multi-producer single-consumer.

엔진 코드 자체는 lock-free 큐와 TaskGraph dependency를 더 선호하고, gameplay 코드 (gameplay framework 위에서) 에서 `FCriticalSection`이 가끔 쓰입니다.

### Unity와 Unreal 비교

| 항목 | Unity | Unreal |
|------|-------|--------|
| Main thread | 하나, 모든 API가 여기로 | Game Thread, gameplay 한정 |
| Render 분리 | 있음 (Render Thread, 명시적 API 적음) | 강함 (Render Thread + RHI Thread + RDG) |
| Job 추상 | Job System + DOTS | TaskGraph + Async Tasks |
| 컴파일 시 race 감지 | NativeContainer + AtomicSafetyHandle | 없음 (런타임 assert 위주) |
| 락 회피 사상 | dependency graph + main thread affinity | named thread + lock-free queue |
| ECS | DOTS / Entities (공식) | Mass Entity (5.x), 비공식 ECS도 다수 |

Unity는 **dependency를 안전하게 표현하게 만들고 schedule 시점에 (Editor/Development에서) 검증**하는 쪽으로 갑니다 (safety on by default). Unreal은 **데이터를 thread에 묶고 명령 큐로 통신**하는 쪽입니다 (performance by convention). 둘 다 결국 락 자체는 거의 안 잡지만 그 이유와 검증 시점이 다릅니다.

---

## Part 8: 락을 피하는 게임 엔진 패턴

엔진 내부에서 락이 거의 안 쓰이는 만큼, 락을 우회하는 패턴이 발달해 있습니다. 게임 코드에서 직접 활용할 수 있는 것들을 정리합니다.

### Double Buffering

가장 단순하고 자주 쓰입니다. **두 개의 버퍼를 번갈아 쓰는 것**입니다. 다만 안전하게 쓰려면 **read와 write가 시간상 겹치지 않는다는 전제** — 보통 frame boundary나 fence — 가 필요합니다.

```cpp
/* 전제: GameTick과 PhysicsTick이 frame boundary에서 순차 호출됨.
   한 프레임 내부에서는 read가 끝난 뒤에 worker가 다음 write를 시작한다 */

struct PhysicsState {
    std::vector<Transform> transforms;
};

PhysicsState buffers[2];
std::atomic<int> readIdx{0};   /* main이 읽음 */

/* Frame N — Worker가 다음 write할 버퍼를 결정 (read가 끝난 시점 보장 필요) */
void PhysicsTick() {
    int w = 1 - readIdx.load(std::memory_order_acquire);
    UpdatePhysics(buffers[w]);
    readIdx.store(w, std::memory_order_release);  /* publish */
}

/* Frame N — Main이 가장 최근 publish된 버퍼를 read */
void GameTick() {
    int r = readIdx.load(std::memory_order_acquire);
    Render(buffers[r]);
}
```

락이 한 번도 없습니다. atomic 1개로 "지금 읽기 가능한 버퍼 인덱스"만 교환합니다. 메모리 비용은 버퍼 두 배. **단, writer와 reader가 독립적으로 비동기 루프를 돌면 위 코드는 안전하지 않습니다.** publish 직후 reader가 아직 그 버퍼를 읽는 사이에 worker가 다음 tick에서 *다른* 버퍼를 쓰려고 했을 때 인덱스가 같아질 수 있기 때문입니다. 게임 엔진은 보통 **frame boundary에서 sync**해 read 단계와 write 단계가 시간상 분리되도록 설계합니다 — 그 전제 위에서만 double buffer가 안전합니다. 그렇지 못한 패턴이라면 triple buffer 또는 명시적 sequence handoff가 필요합니다.

게임 엔진에서 이 패턴이 쓰이는 곳:

- **물리 → 렌더**: frame boundary에서 buffer swap, render thread가 N을 그리는 동안 physics가 N+1 준비
- **AI tick**: 다음 프레임 행동을 미리 계산 후 frame 경계에서 swap
- **네트워크 input**: 받은 패킷을 한 프레임 동안 모았다가 frame 경계에서 swap

### Triple Buffering

writer와 reader가 독립 루프를 돌아 read·write가 시간상 겹칠 수 있으면 double buffer만으론 부족합니다. 셋을 두면 됩니다 — "지금 그리는 것", "방금 만든 것", "다음에 쓸 것". OS 그래픽 스택의 swap chain, V-sync 큐, 게임 엔진의 ring buffer 등에서 쓰입니다. 세 버퍼가 있으면 writer는 항상 reader가 안 쓰는 슬롯을 골라 쓸 수 있습니다.

### Lock-free SPSC Ring Buffer

Single-producer single-consumer 큐는 atomic 두 개로 락 없이 구현됩니다.

```cpp
template<typename T, size_t N>
struct SpscRing {
    T buf[N];
    alignas(64) std::atomic<size_t> head{0};  /* producer가 씀 */
    alignas(64) std::atomic<size_t> tail{0};  /* consumer가 씀 */

    bool push(const T& v) {
        size_t h = head.load(std::memory_order_relaxed);
        size_t next = (h + 1) % N;
        if (next == tail.load(std::memory_order_acquire))
            return false;  /* full */
        buf[h] = v;
        head.store(next, std::memory_order_release);
        return true;
    }

    bool pop(T& out) {
        size_t t = tail.load(std::memory_order_relaxed);
        if (t == head.load(std::memory_order_acquire))
            return false;  /* empty */
        out = buf[t];
        tail.store((t + 1) % N, std::memory_order_release);
        return true;
    }
};
```

`alignas(64)`는 head와 tail이 다른 cache line에 있도록 합니다 — false sharing 방지. producer와 consumer가 다른 코어에서 돌아도 contention이 없습니다.

이 구조가 game ↔ render command queue, audio sample buffer, log queue 등 거의 모든 1:1 통신에 깔려 있습니다.

### Per-thread accumulation

여러 스레드가 카운터를 증가시켜야 한다면 false sharing 함정에 빠지기 쉽습니다. 해결은 **각 스레드가 자기 슬롯을 가지고 마지막에 합치는 것**입니다.

```cpp
struct alignas(64) Slot { int64_t v = 0; };
Slot per_thread[NUM_THREADS];

/* 각 스레드 */
per_thread[tid].v++;        /* atomic이 아닌 일반 store */

/* 합치기 (한 스레드에서) */
int64_t total = 0;
for (auto& s : per_thread) total += s.v;
```

`alignas(64)` 덕분에 각 슬롯이 자기 cache line을 독점합니다. 100만 번 증가가 false-sharing 락-free 카운터보다 50~100배 빠릅니다.

### Frame-locked sync — 명시적 동기 지점

Job 단위로 끊임없이 락을 잡는 대신, **프레임 경계에서만 동기화**합니다. 한 프레임 안에서는 한 스레드가 자기 데이터만 만지고, 프레임 끝에서 모든 스레드 결과를 main이 한 번에 통합합니다.

Naughty Dog의 fiber 시스템 (9편 참조) 도 이 사상의 극단입니다 — 한 프레임을 수천 개 fiber로 쪼개되, 모든 fiber가 끝나는 sync point에서만 다음 프레임으로 넘어갑니다.

### 정리: 락 회피의 사고방식

엔진 내부에서 락 대신 쓰이는 패턴들의 공통점은:

1. **데이터를 thread에 묶기** — 한 스레드가 자기 데이터를 단독으로 만지면 락이 필요 없음
2. **명시적 통신 채널** — lock-free queue로 thread 간 데이터를 전달
3. **시간 분리** — double/triple buffer로 read와 write를 시간상 분리
4. **공간 분리** — per-thread slot으로 false sharing 회피
5. **드물게만 sync** — frame boundary처럼 자연스러운 sync point에 비용 집중

락이 나쁜 게 아니라 **lock contention과 cache bouncing**이 비싼 것이고, 위 패턴들은 그 둘을 자연스럽게 회피합니다.

---

## Part 9: 락의 비용 — 측정하기

추측 대신 측정입니다. 락이 정말로 비싼지, 어디서 비용이 발생하는지를 확인하는 도구들입니다.

### Linux — perf와 perf c2c

```bash
# 시스템 콜 (futex_wait/wake) 빈도
$ perf stat -e syscalls:sys_enter_futex ./game

# cache miss, hitm (다른 코어의 modified line hit)
$ perf stat -e mem_load_uops_l3_hit_retired.xsnp_hitm ./game

# false sharing 탐지 (Cache-to-Cache analysis)
$ perf c2c record ./game
$ perf c2c report
```

`perf c2c`는 false sharing의 표준 진단 도구입니다. HITM(Hit Modified) 이벤트가 같은 cache line에서 빈번하면 그 line이 의심 대상입니다.

### Windows — Concurrency Visualizer, ETW

Visual Studio Concurrency Visualizer는 thread별 CPU usage, lock contention block, I/O wait를 시각화합니다. WPA의 "Wait Analysis" 페이지도 같은 정보를 더 자세히 보여줍니다.

```powershell
# 락 contention 추적
wpr -start LockHeldTimes -filemode
# (게임 실행)
wpr -stop trace.etl
```

### macOS — Instruments System Trace

System Trace template의 "Thread State" 트랙이 thread blocking을 시각화합니다. "Pthread mutex contention" 마커가 따로 표시되어 어느 mutex가 contended인지 바로 보입니다.

```bash
# 또는 dtrace로 즉석 측정
$ sudo dtrace -n 'pid$target:libsystem_pthread:_pthread_mutex_lock:entry {@[ustack()]=count();}' -p <pid>
```

### 크로스플랫폼 — Tracy Profiler

Tracy는 mutex 사용을 직접 추적할 수 있는 매크로를 제공합니다.

```cpp
#include "Tracy.hpp"
#include "TracyLock.hpp"

TracyLockable(std::mutex, m);

void DoWork() {
    std::lock_guard<LockableBase(std::mutex)> lk(m);
    ZoneScoped;
    /* ... */
}
```

`LockableBase`로 감싼 mutex의 lock/unlock 시점과 contention 시간이 Tracy 타임라인에 시각화됩니다. 어느 mutex가 hot한지 한 눈에 보입니다.

### 게임 엔진 내장 프로파일러

- **Unity Profiler**: Job System tab에서 worker thread 활용도, dependency wait time 표시
- **Unreal Insights**: TaskGraph 시각화, fence wait time, ENQUEUE_RENDER_COMMAND 호출 빈도
- **PIX (Xbox/PC)**: D3D12 fence wait, RHI thread blocking 표시

### 한 줄 진단

"내 게임이 느린데 lock이 원인입니까?"의 한 줄 답은 **"thread state 시각화에서 spinning 또는 wait이 보이면 그 시간만큼 비용"**입니다. 코드 한 줄 보지 않고도 thread state graph만 보면 lock이 진짜 문제인지 즉시 알 수 있습니다.

---

## 정리

이 편에서 다룬 내용을 한 번에 모으면 다음과 같습니다.

**race condition의 정체**:
- `counter++`가 load/modify/store 3단계로 분해되어 원자성 깨짐
- data race(undefined behavior)와 race condition(실행 순서 의존)은 다른 개념
- 락은 원자성·가시성·순서 세 가지를 함께 보장

**락의 가족**:
- Mutex, Spinlock, Semaphore, RWLock, CondVar, Monitor, Barrier, Latch
- 같은 atomic 위에 다른 정책일 뿐

**락의 구현**:
- Peterson은 이론적으로만 동작, 실제 CPU는 memory barrier 필요
- 하드웨어 atomic: x86 LOCK CMPXCHG, ARM LDXR/STXR
- Spin vs Sleep은 임계 구역 길이 vs 컨텍스트 스위치 비용 비교

**OS 프리미티브**:
- Linux futex (2002), Windows SRWLock (Vista, 2007), macOS os_unfair_lock (2016)
- 모두 같은 사상: fast path는 user-space atomic, slow path만 kernel
- macOS os_unfair_lock은 owner thread ID 인코딩으로 QoS donation 가능

**하드웨어 메커니즘**:
- CPU 캐시: L1(4 cycle) ~ L3(50 cycle) ~ DRAM(300 cycle)
- MESI 프로토콜: 한 cache line은 단 하나의 코어만 Modified 가능
- atomic의 atomicity는 cache coherence가 RFO를 직렬화하는 데서 나옴
- Cache line bouncing: intra-socket 30~50ns, cross-socket 150~300ns
- False sharing: 다른 변수가 같은 cache line이면 의도치 않은 contention

**Unity 동기화**:
- Main thread 모델: 모든 Unity API가 main only
- Job System: JobHandle dependency graph, batch 64, work-stealing
- NativeContainer + AtomicSafetyHandle: schedule 시점 런타임 race 검사 (Editor/Development 한정)
- Burst: 일반 read/write는 일반 load/store, `Interlocked.*` 호출만 하드웨어 atomic으로 emit
- DOTS: Component read/write를 자동 분석, scheduler가 schedule 시점에 dependency edge 자동 생성

**Unreal 동기화**:
- Game / Render / RHI / Audio Thread 분리
- TaskGraph + Named Thread + dependency
- ENQUEUE_RENDER_COMMAND는 lock-free MPSC 큐로 동작
- FRenderCommandFence가 Game ↔ Render의 명시적 sync point

**락을 피하는 패턴**:
- Double/Triple buffer, lock-free SPSC ring, per-thread slot
- Frame-locked sync로 동기화 비용을 한 점에 집중

다음 편 **Part 11 — 데드락과 기아**에서는 락이 멀쩡히 동작하는데도 프로그램이 멈추는 경우 — 두 락의 순환 대기, priority inversion, livelock — 를 다룹니다. 그 뒤 Part 12에서 memory model과 atomic ordering, Part 13에서 lock-free 자료구조와 Unity Job System의 더 깊은 내부로 이어집니다.

Stage 2의 원전 질문에 이제 답할 수 있습니다.

> **스레드 두 개가 같은 변수를 쓰면 왜 프로그램이 때때로만 죽는가?**

- "쓴다"는 행위가 load/modify/store 3단계라 도중에 다른 스레드가 끼어들 수 있고
- "끼어든다"는 일은 스케줄러가 임의의 순간에 정하기 때문에 "때때로"이고
- "막으려면" cache coherence와 atomic 명령 위에 만든 lock이라는 추상이 필요하다.

---

## References

### 교재

- Herlihy, M., Shavit, N. — *The Art of Multiprocessor Programming*, 2nd ed., Morgan Kaufmann, 2020 — Ch.2~7 (Mutex 알고리즘, lock-free, hardware foundations) — 멀티스레드 동기화의 정전
- Silberschatz, A., Galvin, P. B., Gagne, G. — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.6 (Synchronization Tools), Ch.7 (Synchronization Examples)
- Tanenbaum, A. S., Bos, H. — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.3 (Interprocess Communication)
- Russinovich, M., Solomon, D., Ionescu, A. — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.8 (System Mechanisms, SRWLock / pushlock 내부)
- Singh, A. — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.10 (Mach IPC, locks)
- Drepper, U. — *What Every Programmer Should Know About Memory*, Red Hat, 2007 — cache coherence 입문의 결정판 — [people.freebsd.org/~lstewart/articles/cpumemory.pdf](https://people.freebsd.org/~lstewart/articles/cpumemory.pdf)
- Gregory, J. — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8.6~8.7 (Multithreading, Job systems)
- McKenney, P. E. — *Is Parallel Programming Hard, And, If So, What Can You Do About It?*, 2024 ed. — [kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) — RCU 저자의 무료 책

### 논문

- Peterson, G. L. — "Myths About the Mutual Exclusion Problem", *Information Processing Letters*, 1981 — Peterson 알고리즘 원전
- Dijkstra, E. W. — "Cooperating Sequential Processes", *Programming Languages*, 1968 — Semaphore 도입
- Lamport, L. — "A New Solution of Dijkstra's Concurrent Programming Problem", *CACM*, 1974 — bakery algorithm
- Lamport, L. — "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs", *IEEE TC*, 1979 — sequential consistency 정의
- Franke, H., Russell, R., Kirkwood, M. — "Fuss, Futexes and Furwocks: Fast Userlevel Locking in Linux", *OLS 2002* — futex 도입 — [kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf](https://www.kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf)
- Drepper, U. — "Futexes Are Tricky", Red Hat, 2011 — futex 구현의 함정 — [akkadia.org/drepper/futex.pdf](https://www.akkadia.org/drepper/futex.pdf)
- Sweeney, T. et al. — "Concurrent Programming in Unreal Engine" (GDC, EpicGames Dev) — TaskGraph 디자인
- Boehm, H.-J. — "Threads Cannot Be Implemented as a Library", *PLDI 2005* — C++ memory model의 동기
- Adve, S. V., Gharachorloo, K. — "Shared Memory Consistency Models: A Tutorial", *IEEE Computer*, 1996 — memory model 비교

### 공식 문서

- Linux man pages — `futex(2)`, `futex(7)`, `pthread_mutex_lock(3)`, `pthread_rwlock_rdlock(3)` — [man7.org/linux/man-pages/man2/futex.2.html](https://man7.org/linux/man-pages/man2/futex.2.html)
- Linux Kernel Documentation — `Documentation/locking/futex2.rst`, `mutex-design.rst`, `lockdep-design.rst`
- Microsoft Docs — *Slim Reader/Writer (SRW) Locks*, *Critical Section Objects* — [learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks](https://learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks)
- Apple Developer — *Threading Programming Guide*, `os_unfair_lock(3)` — [developer.apple.com/documentation/os/os_unfair_lock](https://developer.apple.com/documentation/os/os_unfair_lock)
- Intel — *Intel 64 and IA-32 Architectures Software Developer's Manual*, Vol. 3A — Ch.8 (Multiple-Processor Management), LOCK prefix
- ARM — *ARM Architecture Reference Manual ARMv8-A*, B2 (Memory Model), C6 (Load-Acquire / Store-Release)

### Unity 공식

- Unity Manual — *C# Job System* — [docs.unity3d.com/Manual/JobSystem.html](https://docs.unity3d.com/Manual/JobSystem.html)
- Unity Manual — *Native Containers* — [docs.unity3d.com/Manual/JobSystemNativeContainer.html](https://docs.unity3d.com/Manual/JobSystemNativeContainer.html)
- Unity Manual — *Burst Compiler* — [docs.unity3d.com/Packages/com.unity.burst@latest](https://docs.unity3d.com/Packages/com.unity.burst@latest)
- Unity Manual — *Entities (DOTS)* — [docs.unity3d.com/Packages/com.unity.entities@latest](https://docs.unity3d.com/Packages/com.unity.entities@latest)
- Joachim Ante — *C# Job System and ECS — Unite LA 2018* — Job System 디자인 발표
- Lucas Meijer — *On DOTS: Entity Component System — Unity Blog*, 2019

### Unreal 공식

- Epic Games — *Threading in Unreal Engine* — [dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine)
- Epic Games — *Task Graph System* — [dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Epic Games — *Rendering and the Game Thread* — RDG, ENQUEUE_RENDER_COMMAND 설명
- Tim Sweeney — *The Next Mainstream Programming Language*, POPL 2006 — Unreal의 멀티스레딩 비전

### 게임 개발 / GDC

- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — fiber 기반 sync — [gdcvault.com/play/1022186](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungie의 lock-free 디자인
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICE의 Job 시스템
- Reinders, J., Roberts, B. — *Multithreading for Visual Effects*, A K Peters, 2014 — 영화 엔진의 lock-free 패턴
- Vyukov, D. — *Lock-Free / 1024cores* — Vyukov MPSC, scalability 자료 — [1024cores.net](https://www.1024cores.net/)

### 블로그 / 기사

- Preshing, J. — *Preshing on Programming* — atomic, memory ordering 시리즈 — [preshing.com](https://preshing.com/)
- Howells, D. et al. — *Linux Kernel Memory Barriers (`memory-barriers.txt`)* — kernel 공식 메모리 모델 가이드
- Chen, R. — *The Old New Thing* — Windows critical section/SRWLock 회상
- Giesen, F. — *Reading List on Multithreading* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Oakley, H. — *The Eclectic Light Company* — macOS os_unfair_lock, QoS 관찰
- Bonzini, P. — "QEMU and lock-free RCU" — RCU의 실용 적용

### 도구

- Linux: `perf c2c`, `perf lock`, `bpftrace`, `lockstat`
- Windows: Concurrency Visualizer (VS), WPA Wait Analysis, PIX (게임용)
- macOS: Instruments System Trace, `dtrace`, `sample`
- 크로스플랫폼: Tracy Profiler (LockableBase), Intel VTune, AMD μProf
- ThreadSanitizer (TSan): GCC/Clang의 data race 정적·동적 탐지기




