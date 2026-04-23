---
title: "CS 로드맵 (외전) — 힙과 우선순위 큐: 부분 순서의 경제학"
date: 2026-04-23 10:00:00 +0900
categories: [AI, CS]
tags: [Heap, Priority Queue, Binary Heap, Heapsort, Fibonacci Heap, A-Star, Pathfinding, CS Fundamentals]
difficulty: intermediate
toc: true
toc_sticky: true
math: true
image: /assets/img/og/cs.png
prerequisites:
  - /posts/Tree/
  - /posts/Graph/
tldr:
  - "우선순위 큐는 '최솟값/최댓값만 빠르게' 필요로 하는 문제 — 완전 정렬(O(n log n))은 과잉 사양이다. 힙은 '부분 순서'만 유지하여 O(log n) push/pop을 달성한다"
  - "이진 힙은 완전 이진 트리를 배열로 표현한 마법 — 포인터 없이 parent = (i-1)/2, left = 2i+1이라는 인덱스 산술만으로 트리를 오간다"
  - "Floyd(1964)의 bottom-up build-heap은 O(n)에 완성된다. 직관과 달리 O(n log n)이 아니다 — 깊은 레벨 노드가 많고 얕은 sift-down만 하기 때문"
  - "A* open set의 decrease-key는 실무에서 lazy deletion(stale entry를 꺼낼 때 무시)으로 해결한다. Fibonacci heap의 O(1) decrease-key는 상수 오버헤드 때문에 격자 A*에서는 오히려 손해다"
---

## 서론

> 이 문서는 **CS 로드맵** 시리즈의 외전(bonus)입니다.

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

[5편 그래프](/posts/Graph/)에서 Dijkstra와 A*를 다루면서 한 문장을 남겼다: *"우선순위 큐(이진 힙)를 사용하면 $O((V+E) \log V)$"*. 그런데 그 "이진 힙"이 무엇인지, 왜 이진이고, 어떻게 $O(\log n)$을 달성하는지는 뒤로 미뤘다. 이 외전은 그 빚을 갚는다.

1단계(자료구조와 메모리)가 6편으로 마무리된 뒤, 힙과 우선순위 큐는 "빠진 핵심 한 조각"으로 남아 있었다. 트리의 응용이자 배열의 산술이며, A*의 엔진이자 이벤트 스케줄러의 심장이다. 작은 주제이지만 안 보고 넘기기엔 게임 개발에서 너무 자주 등장한다.

이 글에서 다룰 것:

1. 왜 완전 정렬이 아니라 "부분 순서"로 충분한가
2. 이진 힙이 배열 위에서 동작하는 원리
3. sift-up / sift-down의 수학적 근거와 C# 구현
4. Floyd(1964)의 $O(n)$ build-heap
5. d-ary heap, Pairing heap, Fibonacci heap — 언제 어떤 걸 쓰는가
6. A* open set의 decrease-key 문제와 실무 해법
7. .NET `PriorityQueue<TElement, TPriority>` 분석

---

## Part 1: 우선순위 큐 문제

### "최솟값만 빠르게" — 완전 정렬은 과잉이다

다음 문제를 생각해보자.

> 정수 1,000,000개가 있다. 그중 가장 작은 값 1,000개만 순서대로 꺼내고 싶다.

직관적으로 떠오르는 해법은 **전체를 정렬한 뒤 앞에서 1,000개를 취하는 것**이다. $O(n \log n)$에 전체를 정렬했으니 출력은 $O(k)$. 그런데 잘 생각해보면 낭비다. 뒤쪽 99만 9천 개의 순서는 우리가 쓰지도 않는다. **필요한 것은 "최솟값 추출"과 "삽입"이라는 두 연산뿐이다.**

이것이 **우선순위 큐(Priority Queue)** 문제다. 큐(FIFO)처럼 "넣고 빼는" 인터페이스지만, 나가는 순서는 "먼저 들어온 것"이 아니라 **"우선순위가 가장 높은 것"**이다.

```
일반 큐 (FIFO):                우선순위 큐:

  [4, 7, 1, 9, 3]                [4, 7, 1, 9, 3]
   ↓ dequeue                      ↓ extract-min
   4 (들어온 순서)                1 (가장 작은 값)
```

게임에서 이 문제가 나타나는 순간들:

- **A* / Dijkstra**: "f 값이 가장 작은 노드를 꺼내라"
- **이벤트 스케줄러**: "실행 시각이 가장 이른 이벤트를 꺼내라"
- **AI 행동 선택**: "지금 가장 유용한 행동의 점수를 꺼내라"
- **DSP / 오디오 믹싱**: "가장 중요한 사운드 채널 N개만 재생하라"

### 순진한 구현들의 트레이드오프

우선순위 큐를 **"왜 배열이나 BST로 하면 안 되는가"**를 먼저 짚어야 힙의 가치가 보인다.

| 구조 | insert | extract-min | 비고 |
| --- | --- | --- | --- |
| **Unsorted Array** | $O(1)$ | $O(n)$ | 넣을 땐 맨 뒤에, 뺄 땐 전체 스캔 |
| **Sorted Array** | $O(n)$ | $O(1)$ | 이진 탐색으로 위치 찾아도 이동 비용 $O(n)$ |
| **Sorted LinkedList** | $O(n)$ | $O(1)$ | 탐색이 선형, 이동은 없지만 |
| **BST (균형)** | $O(\log n)$ | $O(\log n)$ | 포인터 4~5개/노드, 캐시 미스 |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | **배열로 구현, 포인터 0개** |

표를 보면 "힙이 BST보다 복잡도가 같은데 왜 더 좋은가?" 하는 질문이 자연스럽게 나온다. 답은 **상수와 캐시**에 있다 — 1편에서 다뤘던 그 이야기가 여기서도 반복된다.

<div class="hp-cmp" style="margin:2rem 0;overflow-x:auto;">
<svg viewBox="0 0 780 320" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:780px;margin:0 auto;display:block;
            font-family:system-ui,-apple-system,sans-serif;">
  <defs>
    <filter id="hp-cmp-sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="hp-cmp-g1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffebee"/><stop offset="100%" stop-color="#ffcdd2"/>
    </linearGradient>
    <linearGradient id="hp-cmp-g2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff8e1"/><stop offset="100%" stop-color="#ffe0b2"/>
    </linearGradient>
    <linearGradient id="hp-cmp-g3" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e3f2fd"/><stop offset="100%" stop-color="#bbdefb"/>
    </linearGradient>
    <linearGradient id="hp-cmp-g4" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e8f5e9"/><stop offset="100%" stop-color="#c8e6c9"/>
    </linearGradient>
  </defs>

  <text class="hp-cmp-title" x="390" y="28" text-anchor="middle" font-weight="700" font-size="16">우선순위 큐 구현별 성능 비교</text>

  <!-- 4개 박스 -->
  <rect x="20" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g1)" filter="url(#hp-cmp-sh)"/>
  <rect x="215" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g2)" filter="url(#hp-cmp-sh)"/>
  <rect x="410" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g3)" filter="url(#hp-cmp-sh)"/>
  <rect x="605" y="60" width="155" height="220" rx="12" fill="url(#hp-cmp-g4)" filter="url(#hp-cmp-sh)" stroke="#2e7d32" stroke-width="2"/>

  <!-- 제목 -->
  <text class="hp-cmp-name" x="107" y="88" text-anchor="middle" font-weight="700" font-size="14">Sorted Array</text>
  <text class="hp-cmp-name" x="302" y="88" text-anchor="middle" font-weight="700" font-size="14">Unsorted Array</text>
  <text class="hp-cmp-name" x="497" y="88" text-anchor="middle" font-weight="700" font-size="14">BST (균형)</text>
  <text class="hp-cmp-name hp-cmp-best" x="682" y="88" text-anchor="middle" font-weight="700" font-size="14">Binary Heap</text>

  <!-- insert -->
  <text class="hp-cmp-label" x="35" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-bad" x="180" y="118" text-anchor="end" font-size="13" font-weight="700">O(n)</text>
  <text class="hp-cmp-label" x="230" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-good" x="375" y="118" text-anchor="end" font-size="13" font-weight="700">O(1)</text>
  <text class="hp-cmp-label" x="425" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-mid" x="570" y="118" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>
  <text class="hp-cmp-label" x="620" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-mid" x="745" y="118" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>

  <!-- extract -->
  <text class="hp-cmp-label" x="35" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-good" x="180" y="145" text-anchor="end" font-size="13" font-weight="700">O(1)</text>
  <text class="hp-cmp-label" x="230" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-bad" x="375" y="145" text-anchor="end" font-size="13" font-weight="700">O(n)</text>
  <text class="hp-cmp-label" x="425" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-mid" x="570" y="145" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>
  <text class="hp-cmp-label" x="620" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-mid" x="745" y="145" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>

  <!-- 구분선 -->
  <line class="hp-cmp-div" x1="35" y1="160" x2="180" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="230" y1="160" x2="375" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="425" y1="160" x2="570" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="620" y1="160" x2="745" y2="160" stroke-dasharray="3,3"/>

  <!-- 메모리 -->
  <text class="hp-cmp-memtitle" x="107" y="180" text-anchor="middle" font-size="11" font-weight="600">메모리/노드</text>
  <text class="hp-cmp-mem" x="107" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="302" y="180" text-anchor="middle" font-size="11" font-weight="600">메모리/노드</text>
  <text class="hp-cmp-mem" x="302" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="497" y="180" text-anchor="middle" font-size="11" font-weight="600">메모리/노드</text>
  <text class="hp-cmp-mem hp-cmp-memwarn" x="497" y="198" text-anchor="middle" font-size="13" font-weight="700">4~5 words</text>
  <text class="hp-cmp-memtitle" x="682" y="180" text-anchor="middle" font-size="11" font-weight="600">메모리/노드</text>
  <text class="hp-cmp-mem" x="682" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>

  <!-- 캐시 -->
  <text class="hp-cmp-memtitle" x="107" y="224" text-anchor="middle" font-size="11" font-weight="600">캐시 친화성</text>
  <text class="hp-cmp-good" x="107" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 연속</text>
  <text class="hp-cmp-memtitle" x="302" y="224" text-anchor="middle" font-size="11" font-weight="600">캐시 친화성</text>
  <text class="hp-cmp-good" x="302" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 연속</text>
  <text class="hp-cmp-memtitle" x="497" y="224" text-anchor="middle" font-size="11" font-weight="600">캐시 친화성</text>
  <text class="hp-cmp-bad" x="497" y="242" text-anchor="middle" font-size="13" font-weight="700">✗ 포인터 추적</text>
  <text class="hp-cmp-memtitle" x="682" y="224" text-anchor="middle" font-size="11" font-weight="600">캐시 친화성</text>
  <text class="hp-cmp-good" x="682" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 연속</text>

  <!-- 치명타 / 장점 -->
  <text class="hp-cmp-weak" x="107" y="268" text-anchor="middle" font-size="11.5" font-style="italic">insert시 O(n) 이동</text>
  <text class="hp-cmp-weak" x="302" y="268" text-anchor="middle" font-size="11.5" font-style="italic">스캔 반복</text>
  <text class="hp-cmp-weak" x="497" y="268" text-anchor="middle" font-size="11.5" font-style="italic">캐시 미스 + 메모리</text>
  <text class="hp-cmp-strong" x="682" y="268" text-anchor="middle" font-size="11.5" font-weight="700">균형 잡힌 최적해</text>
</svg>
</div>
<style>
.hp-cmp-title{fill:#333}
.hp-cmp-name{fill:#333}.hp-cmp-best{fill:#1b5e20}
.hp-cmp-label{fill:#555}
.hp-cmp-good{fill:#2e7d32}
.hp-cmp-bad{fill:#c62828}
.hp-cmp-mid{fill:#e65100}
.hp-cmp-div{stroke:rgba(0,0,0,0.15)}
.hp-cmp-memtitle{fill:#666}
.hp-cmp-mem{fill:#333}
.hp-cmp-memwarn{fill:#c62828}
.hp-cmp-weak{fill:#888}
.hp-cmp-strong{fill:#1b5e20}
[data-mode="dark"] .hp-cmp-title{fill:#e0e0e0}
[data-mode="dark"] .hp-cmp-name{fill:#e0e0e0}
[data-mode="dark"] .hp-cmp-best{fill:#a5d6a7}
[data-mode="dark"] .hp-cmp-label{fill:#bbb}
[data-mode="dark"] .hp-cmp-good{fill:#81c784}
[data-mode="dark"] .hp-cmp-bad{fill:#ef9a9a}
[data-mode="dark"] .hp-cmp-mid{fill:#ffb74d}
[data-mode="dark"] .hp-cmp-div{stroke:rgba(255,255,255,0.2)}
[data-mode="dark"] .hp-cmp-memtitle{fill:#aaa}
[data-mode="dark"] .hp-cmp-mem{fill:#e0e0e0}
[data-mode="dark"] .hp-cmp-memwarn{fill:#ef9a9a}
[data-mode="dark"] .hp-cmp-weak{fill:#999}
[data-mode="dark"] .hp-cmp-strong{fill:#a5d6a7}
@media(max-width:768px){.hp-cmp svg{min-width:720px}}
</style>

### 힙의 핵심 아이디어: 부분 순서로 충분하다

우선순위 큐 문제의 핵심 통찰은 이것이다.

> **우리는 매번 최솟값 하나만 꺼낸다. 나머지 요소들의 상대적 순서는 관심 없다.**

전체 정렬은 "모든 쌍에 대해 $a < b$ 또는 $a > b$"를 결정한다. 하지만 최솟값 추출은 **"루트가 전체의 최소다"**라는 훨씬 약한 조건만 있으면 된다. 이 "약함"이 $O(\log n)$의 여지를 만든다.

**힙의 약속 (min-heap):**
- 루트는 전체의 최솟값이다
- 부모는 두 자식보다 **작거나 같다** (형제끼리는 순서 불문)

이것을 **힙 속성(heap property)**이라고 부른다. BST의 "왼쪽 < 부모 < 오른쪽"과 달리, 힙은 **부모-자식 관계만** 강제하고 형제나 서브트리 간 순서는 아무렇게나 둔다. 이 "느슨함"이 빠른 삽입/삭제의 비결이다.

---

## Part 2: 이진 힙의 구조

### 완전 이진 트리

[4편 트리](/posts/Tree/)에서 **완전 이진 트리(complete binary tree)**를 정의했다: "마지막 레벨을 제외하고 모든 레벨이 꽉 차 있고, 마지막 레벨은 왼쪽부터 채워진 트리". 이진 힙은 **반드시** 완전 이진 트리여야 한다.

```
         1
       /   \
      3     2
     / \   / \
    7   5 4   8
   / \
  9  10

높이 = ⌊log₂(n)⌋ = ⌊log₂(8)⌋ = 3
마지막 레벨은 왼쪽부터 채워졌다
```

왜 **완전**이어야 하는가? 두 가지 이유가 있다.

1. **높이가 항상 $\lfloor \log_2 n \rfloor$로 유지됨** — sift-up/down이 $O(\log n)$임을 보장
2. **배열로 표현 가능** — 빈 슬롯이 없으니 배열에 꽉 채울 수 있다

두 번째가 이 자료구조의 마법이다.

### 배열로 표현된 트리 — 포인터 없는 트리

완전 이진 트리의 노드를 레벨 순서(위에서 아래, 왼쪽에서 오른쪽)로 배열에 저장하면, **부모-자식 관계가 인덱스 산술로 표현된다**.

0-based 인덱스 기준:

$$\text{parent}(i) = \left\lfloor \frac{i-1}{2} \right\rfloor, \quad \text{left}(i) = 2i+1, \quad \text{right}(i) = 2i+2$$

1-based로 쓰면 더 예쁘다 (Williams의 원 논문이 이 형태를 썼다):

$$\text{parent}(i) = \left\lfloor \frac{i}{2} \right\rfloor, \quad \text{left}(i) = 2i, \quad \text{right}(i) = 2i+1$$

<div class="hp-map" style="margin:2rem 0;overflow-x:auto;">
<svg viewBox="0 0 780 420" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:780px;margin:0 auto;display:block;
            font-family:system-ui,-apple-system,sans-serif;">
  <defs>
    <filter id="hp-map-sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="hp-map-gnode" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e3f2fd"/><stop offset="100%" stop-color="#90caf9"/>
    </linearGradient>
    <linearGradient id="hp-map-groot" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#c8e6c9"/><stop offset="100%" stop-color="#81c784"/>
    </linearGradient>
  </defs>

  <text class="hp-map-title" x="390" y="26" text-anchor="middle" font-weight="700" font-size="16">배열 ↔ 완전 이진 트리: 인덱스 매핑</text>

  <!-- 트리 영역 -->
  <text class="hp-map-section" x="390" y="58" text-anchor="middle" font-size="13" font-weight="600">완전 이진 트리 (min-heap)</text>

  <!-- 트리 간선 -->
  <line class="hp-map-edge" x1="390" y1="95" x2="250" y2="155"/>
  <line class="hp-map-edge" x1="390" y1="95" x2="530" y2="155"/>
  <line class="hp-map-edge" x1="250" y1="175" x2="170" y2="235"/>
  <line class="hp-map-edge" x1="250" y1="175" x2="330" y2="235"/>
  <line class="hp-map-edge" x1="530" y1="175" x2="450" y2="235"/>
  <line class="hp-map-edge" x1="530" y1="175" x2="610" y2="235"/>
  <line class="hp-map-edge" x1="170" y1="255" x2="130" y2="315"/>

  <!-- 트리 노드 (값 1, 3, 2, 7, 5, 4, 8, 9) -->
  <g>
    <circle cx="390" cy="80" r="22" fill="url(#hp-map-groot)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="390" y="86" text-anchor="middle" font-size="15" font-weight="700">1</text>
    <text class="hp-map-idx" x="390" y="50" text-anchor="middle" font-size="11" font-weight="600">[0]</text>
  </g>
  <g>
    <circle cx="250" cy="165" r="22" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="250" y="171" text-anchor="middle" font-size="15" font-weight="700">3</text>
    <text class="hp-map-idx" x="212" y="165" text-anchor="end" font-size="11" font-weight="600">[1]</text>
  </g>
  <g>
    <circle cx="530" cy="165" r="22" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="530" y="171" text-anchor="middle" font-size="15" font-weight="700">2</text>
    <text class="hp-map-idx" x="568" y="165" text-anchor="start" font-size="11" font-weight="600">[2]</text>
  </g>
  <g>
    <circle cx="170" cy="245" r="20" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="170" y="251" text-anchor="middle" font-size="14" font-weight="700">7</text>
    <text class="hp-map-idx" x="135" y="245" text-anchor="end" font-size="11" font-weight="600">[3]</text>
  </g>
  <g>
    <circle cx="330" cy="245" r="20" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="330" y="251" text-anchor="middle" font-size="14" font-weight="700">5</text>
    <text class="hp-map-idx" x="365" y="245" text-anchor="start" font-size="11" font-weight="600">[4]</text>
  </g>
  <g>
    <circle cx="450" cy="245" r="20" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="450" y="251" text-anchor="middle" font-size="14" font-weight="700">4</text>
    <text class="hp-map-idx" x="415" y="245" text-anchor="end" font-size="11" font-weight="600">[5]</text>
  </g>
  <g>
    <circle cx="610" cy="245" r="20" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="610" y="251" text-anchor="middle" font-size="14" font-weight="700">8</text>
    <text class="hp-map-idx" x="645" y="245" text-anchor="start" font-size="11" font-weight="600">[6]</text>
  </g>
  <g>
    <circle cx="130" cy="325" r="18" fill="url(#hp-map-gnode)" filter="url(#hp-map-sh)"/>
    <text class="hp-map-val" x="130" y="331" text-anchor="middle" font-size="14" font-weight="700">9</text>
    <text class="hp-map-idx" x="98" y="325" text-anchor="end" font-size="11" font-weight="600">[7]</text>
  </g>

  <!-- 배열 표현 -->
  <text class="hp-map-section" x="390" y="378" text-anchor="middle" font-size="13" font-weight="600">배열 표현 (메모리 연속)</text>

  <g>
    <rect class="hp-map-cellroot" x="130" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="157" y="408" text-anchor="middle" font-size="14" font-weight="700">1</text>
    <text class="hp-map-cellidx" x="157" y="412" text-anchor="middle" font-size="9">0</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="185" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="212" y="408" text-anchor="middle" font-size="14" font-weight="700">3</text>
    <text class="hp-map-cellidx" x="212" y="412" text-anchor="middle" font-size="9">1</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="240" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="267" y="408" text-anchor="middle" font-size="14" font-weight="700">2</text>
    <text class="hp-map-cellidx" x="267" y="412" text-anchor="middle" font-size="9">2</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="295" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="322" y="408" text-anchor="middle" font-size="14" font-weight="700">7</text>
    <text class="hp-map-cellidx" x="322" y="412" text-anchor="middle" font-size="9">3</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="350" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="377" y="408" text-anchor="middle" font-size="14" font-weight="700">5</text>
    <text class="hp-map-cellidx" x="377" y="412" text-anchor="middle" font-size="9">4</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="405" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="432" y="408" text-anchor="middle" font-size="14" font-weight="700">4</text>
    <text class="hp-map-cellidx" x="432" y="412" text-anchor="middle" font-size="9">5</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="460" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="487" y="408" text-anchor="middle" font-size="14" font-weight="700">8</text>
    <text class="hp-map-cellidx" x="487" y="412" text-anchor="middle" font-size="9">6</text>
  </g>
  <g>
    <rect class="hp-map-cell" x="515" y="388" width="55" height="30" rx="4"/>
    <text class="hp-map-cellval" x="542" y="408" text-anchor="middle" font-size="14" font-weight="700">9</text>
    <text class="hp-map-cellidx" x="542" y="412" text-anchor="middle" font-size="9">7</text>
  </g>

  <!-- 인덱스 산술 박스 -->
  <rect class="hp-map-formula" x="600" y="340" width="160" height="70" rx="8"/>
  <text class="hp-map-ftitle" x="680" y="358" text-anchor="middle" font-size="11" font-weight="700">인덱스 산술</text>
  <text class="hp-map-ftext" x="610" y="376" font-size="10.5">parent(i) = (i−1)/2</text>
  <text class="hp-map-ftext" x="610" y="390" font-size="10.5">left(i)   = 2i + 1</text>
  <text class="hp-map-ftext" x="610" y="404" font-size="10.5">right(i)  = 2i + 2</text>
</svg>
</div>
<style>
.hp-map-title{fill:#333}.hp-map-section{fill:#555}
.hp-map-val{fill:#0d47a1}
.hp-map-idx{fill:#666}
.hp-map-edge{stroke:#90a4ae;stroke-width:2}
.hp-map-cell{fill:#e3f2fd;stroke:#64b5f6;stroke-width:1.5}
.hp-map-cellroot{fill:#c8e6c9;stroke:#66bb6a;stroke-width:1.5}
.hp-map-cellval{fill:#0d47a1}
.hp-map-cellidx{fill:#888}
.hp-map-formula{fill:#fff8e1;stroke:#ffcc80;stroke-width:1.2}
.hp-map-ftitle{fill:#e65100}
.hp-map-ftext{fill:#5d4037;font-family:'Consolas','Monaco',monospace}
[data-mode="dark"] .hp-map-title{fill:#e0e0e0}
[data-mode="dark"] .hp-map-section{fill:#bbb}
[data-mode="dark"] .hp-map-val{fill:#0d47a1}
[data-mode="dark"] .hp-map-idx{fill:#aaa}
[data-mode="dark"] .hp-map-edge{stroke:#78909c}
[data-mode="dark"] .hp-map-cell{fill:#1a2a3a;stroke:#42a5f5}
[data-mode="dark"] .hp-map-cellroot{fill:#1a3320;stroke:#81c784}
[data-mode="dark"] .hp-map-cellval{fill:#e3f2fd}
[data-mode="dark"] .hp-map-cellidx{fill:#999}
[data-mode="dark"] .hp-map-formula{fill:#3a2e10;stroke:#ffb74d}
[data-mode="dark"] .hp-map-ftitle{fill:#ffcc80}
[data-mode="dark"] .hp-map-ftext{fill:#ffe0b2}
@media(max-width:768px){.hp-map svg{min-width:720px}}
</style>

**왜 이것이 강력한가?**

1. **메모리 연속** — 트리 전체가 하나의 배열. 프리페처가 다음 노드를 미리 가져온다
2. **포인터 0개** — 노드당 value 하나만 저장. 4~5 워드를 쓰는 BST보다 메모리 밀도가 월등
3. **캐시 라인 효율** — 64바이트 캐시 라인 하나에 `int` 기준 16개 요소. 상위 레벨 몇 개가 L1에 상주

1편에서 **"배열은 연속된 메모리에 데이터를 저장하여 캐시 지역성의 이점을 최대로 누린다"**고 했다. 힙은 이 원리를 트리에 이식한 자료구조다.

> **잠깐, 이건 짚고 넘어가자**
>
> **Q. 1-based 인덱스가 수식이 예쁜데, 왜 실무에선 0-based를 쓰는가?**
>
> 언어의 배열이 0-based이기 때문이다. `array[0]`을 비워두고 1번부터 쓰면 메모리 1개 낭비 + 혼란 증가. 대부분의 구현체(C++ `std::priority_queue`, .NET `PriorityQueue`)는 0-based를 쓴다. 수식이 조금 덜 예쁠 뿐 동작은 동일하다.
>
> **Q. 완전 이진 트리가 아니어도 되지 않는가? 이진 탐색 트리처럼 자유롭게 만들면?**
>
> 완전성이 깨지면 배열 표현이 불가능해진다 — "빈 자리"를 표현해야 하므로 배열에 sentinel이나 포인터가 필요하고, 이는 BST로 후퇴하는 것이다. 또한 한쪽으로 기울면 높이가 $O(n)$이 되어 연산이 느려진다. **"배열에 빈틈 없이"**가 힙의 정체성이다.

---

## Part 3: 핵심 연산 — sift-up과 sift-down

힙에서 힙 속성을 유지하는 두 가지 기본 연산이다. 삽입과 삭제가 모두 이 둘로 귀결된다.

### sift-up (percolate up) — 삽입

새 요소를 넣을 때의 전략:

1. **배열의 맨 뒤**에 새 요소를 추가 (완전성 유지)
2. 부모와 비교, 더 작으면 **교환**
3. 힙 속성이 회복될 때까지 반복 (또는 루트 도달)

```
삽입 1:                 단계 1: 부모와 비교     단계 2: 회복 완료
                       [1]                    [1]
     [1]                / \                   / \
    /   \              [3] [2]               [3] [2]
   [3]  [2]            / \ / \               / \ / \
   /\   /\            [7][5][4][8]          [7][5][4][8]
  [7][5][4][8]        / \                    / \
                     [9][1] ← 새 요소         [1][9]  ← 1과 5 비교 → 교환
```

잠깐, 위 예시는 조금 단순화했다. 실제로 1을 인덱스 9에 넣으면:

```
초기:       [1, 3, 2, 7, 5, 4, 8, 9]
1을 추가:   [1, 3, 2, 7, 5, 4, 8, 9, 1]  ← 인덱스 8

sift-up:
  i=8, parent(8)=3, heap[3]=7 > 1 → 교환
    [1, 3, 2, 1, 5, 4, 8, 9, 7]
  i=3, parent(3)=1, heap[1]=3 > 1 → 교환
    [1, 1, 2, 3, 5, 4, 8, 9, 7]
  i=1, parent(1)=0, heap[0]=1 ≤ 1 → 멈춤
```

C# 구현:

```csharp
void SiftUp(int i) {
    while (i > 0) {
        int parent = (i - 1) / 2;
        if (heap[i].CompareTo(heap[parent]) >= 0)
            break;                        // 힙 속성 만족
        (heap[i], heap[parent]) = (heap[parent], heap[i]);
        i = parent;
    }
}

public void Push(T value) {
    heap.Add(value);
    SiftUp(heap.Count - 1);
}
```

**시간 복잡도:** 최악의 경우 루트까지 올라가므로 $O(\log n)$. 트리의 높이가 $\lfloor \log_2 n \rfloor$로 고정되어 있기 때문이다.

### sift-down (percolate down) — 삭제 / 최솟값 추출

루트를 꺼내는 연산. 조금 까다롭다.

1. 루트(최솟값)를 **반환값으로 저장**
2. **배열의 마지막 요소**를 루트 위치로 이동
3. 배열 길이를 1 감소 (뒤는 버림)
4. 루트부터 **두 자식 중 작은 쪽**과 비교, 더 크면 교환
5. 힙 속성이 회복될 때까지 반복 (또는 리프 도달)

핵심은 4번 — **부모가 두 자식보다 작아야 하므로, 두 자식 중 "작은 쪽"과 교환해야 한다.** 큰 쪽과 교환하면 그 자식이 형제보다 커져서 속성이 깨진다.

<div class="hp-down" style="margin:2rem 0;overflow-x:auto;">
<svg viewBox="0 0 780 420" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:780px;margin:0 auto;display:block;
            font-family:system-ui,-apple-system,sans-serif;">
  <defs>
    <filter id="hp-down-sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="hp-down-gn" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e3f2fd"/><stop offset="100%" stop-color="#90caf9"/>
    </linearGradient>
    <linearGradient id="hp-down-gactive" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffebee"/><stop offset="100%" stop-color="#ef5350"/>
    </linearGradient>
    <linearGradient id="hp-down-gswap" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff3e0"/><stop offset="100%" stop-color="#ffb74d"/>
    </linearGradient>
    <marker id="hp-down-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,2 L9,5 L0,8Z" class="hp-down-af"/>
    </marker>
  </defs>

  <text class="hp-down-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">sift-down: 루트를 삭제하고 힙 복원</text>

  <!-- 3단계 나눠서 표시 -->
  <!-- 단계 1: 마지막을 루트로 -->
  <text class="hp-down-step" x="130" y="58" text-anchor="middle" font-size="12" font-weight="700">① 마지막을 루트로</text>
  <line class="hp-down-edge" x1="130" y1="92" x2="100" y2="132"/>
  <line class="hp-down-edge" x1="130" y1="92" x2="160" y2="132"/>
  <line class="hp-down-edge" x1="100" y1="152" x2="75" y2="192"/>
  <line class="hp-down-edge" x1="100" y1="152" x2="125" y2="192"/>
  <line class="hp-down-edge" x1="160" y1="152" x2="185" y2="192"/>
  <circle cx="130" cy="80" r="16" fill="url(#hp-down-gactive)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="130" y="85" text-anchor="middle" font-size="12" font-weight="700">9</text>
  <circle cx="100" cy="140" r="14" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="100" y="145" text-anchor="middle" font-size="11" font-weight="700">3</text>
  <circle cx="160" cy="140" r="14" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="160" y="145" text-anchor="middle" font-size="11" font-weight="700">2</text>
  <circle cx="75" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="75" y="204" text-anchor="middle" font-size="10" font-weight="700">7</text>
  <circle cx="125" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="125" y="204" text-anchor="middle" font-size="10" font-weight="700">5</text>
  <circle cx="185" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="185" y="204" text-anchor="middle" font-size="10" font-weight="700">4</text>
  <text class="hp-down-note" x="130" y="232" text-anchor="middle" font-size="10">루트가 9로 깨졌다</text>
  <text class="hp-down-note" x="130" y="246" text-anchor="middle" font-size="10">(9 &gt; 3, 9 &gt; 2)</text>

  <!-- 화살표 -->
  <line class="hp-down-flow" x1="230" y1="150" x2="275" y2="150" marker-end="url(#hp-down-arr)"/>

  <!-- 단계 2: 작은 자식(2)과 교환 -->
  <text class="hp-down-step" x="390" y="58" text-anchor="middle" font-size="12" font-weight="700">② 작은 자식(2)과 교환</text>
  <line class="hp-down-edge" x1="390" y1="92" x2="360" y2="132"/>
  <line class="hp-down-edgehot" x1="390" y1="92" x2="420" y2="132"/>
  <line class="hp-down-edge" x1="360" y1="152" x2="335" y2="192"/>
  <line class="hp-down-edge" x1="360" y1="152" x2="385" y2="192"/>
  <line class="hp-down-edge" x1="420" y1="152" x2="445" y2="192"/>
  <circle cx="390" cy="80" r="16" fill="url(#hp-down-gswap)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="390" y="85" text-anchor="middle" font-size="12" font-weight="700">2</text>
  <circle cx="360" cy="140" r="14" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="360" y="145" text-anchor="middle" font-size="11" font-weight="700">3</text>
  <circle cx="420" cy="140" r="14" fill="url(#hp-down-gactive)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="420" y="145" text-anchor="middle" font-size="11" font-weight="700">9</text>
  <circle cx="335" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="335" y="204" text-anchor="middle" font-size="10" font-weight="700">7</text>
  <circle cx="385" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="385" y="204" text-anchor="middle" font-size="10" font-weight="700">5</text>
  <circle cx="445" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="445" y="204" text-anchor="middle" font-size="10" font-weight="700">4</text>
  <text class="hp-down-note" x="390" y="232" text-anchor="middle" font-size="10">루트는 OK, 9 &gt; 4</text>
  <text class="hp-down-note" x="390" y="246" text-anchor="middle" font-size="10">다시 내려간다</text>

  <!-- 화살표 -->
  <line class="hp-down-flow" x1="490" y1="150" x2="535" y2="150" marker-end="url(#hp-down-arr)"/>

  <!-- 단계 3: 작은 자식(4)과 교환, 완료 -->
  <text class="hp-down-step" x="650" y="58" text-anchor="middle" font-size="12" font-weight="700">③ 4와 교환 → 완료</text>
  <line class="hp-down-edge" x1="650" y1="92" x2="620" y2="132"/>
  <line class="hp-down-edge" x1="650" y1="92" x2="680" y2="132"/>
  <line class="hp-down-edge" x1="620" y1="152" x2="595" y2="192"/>
  <line class="hp-down-edge" x1="620" y1="152" x2="645" y2="192"/>
  <line class="hp-down-edgehot" x1="680" y1="152" x2="705" y2="192"/>
  <circle cx="650" cy="80" r="16" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="650" y="85" text-anchor="middle" font-size="12" font-weight="700">2</text>
  <circle cx="620" cy="140" r="14" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="620" y="145" text-anchor="middle" font-size="11" font-weight="700">3</text>
  <circle cx="680" cy="140" r="14" fill="url(#hp-down-gswap)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="680" y="145" text-anchor="middle" font-size="11" font-weight="700">4</text>
  <circle cx="595" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="595" y="204" text-anchor="middle" font-size="10" font-weight="700">7</text>
  <circle cx="645" cy="200" r="12" fill="url(#hp-down-gn)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="645" y="204" text-anchor="middle" font-size="10" font-weight="700">5</text>
  <circle cx="705" cy="200" r="12" fill="url(#hp-down-gactive)" filter="url(#hp-down-sh)"/>
  <text class="hp-down-val" x="705" y="204" text-anchor="middle" font-size="10" font-weight="700">9</text>
  <text class="hp-down-note hp-down-good" x="650" y="232" text-anchor="middle" font-size="10" font-weight="700">힙 복원 완료</text>
  <text class="hp-down-note" x="650" y="246" text-anchor="middle" font-size="10">이동 횟수 = 트리 높이 = O(log n)</text>

  <!-- 하단 배열 표현 -->
  <g transform="translate(60, 290)">
    <text class="hp-down-arrtitle" x="330" y="15" text-anchor="middle" font-size="12" font-weight="600">배열 변화 추적</text>
    <!-- 단계 1 배열 -->
    <text class="hp-down-arrlabel" x="0" y="40" font-size="10" font-weight="600">① [</text>
    <rect class="hp-down-cellhot" x="22" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="36" y="42" text-anchor="middle" font-size="10" font-weight="700">9</text>
    <rect class="hp-down-cell" x="52" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="66" y="42" text-anchor="middle" font-size="10" font-weight="700">3</text>
    <rect class="hp-down-cell" x="82" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="96" y="42" text-anchor="middle" font-size="10" font-weight="700">2</text>
    <rect class="hp-down-cell" x="112" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="126" y="42" text-anchor="middle" font-size="10" font-weight="700">7</text>
    <rect class="hp-down-cell" x="142" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="156" y="42" text-anchor="middle" font-size="10" font-weight="700">5</text>
    <rect class="hp-down-cell" x="172" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="186" y="42" text-anchor="middle" font-size="10" font-weight="700">4</text>
    <text class="hp-down-arrlabel" x="205" y="40" font-size="10" font-weight="600">]</text>

    <!-- 단계 2 -->
    <text class="hp-down-arrlabel" x="230" y="40" font-size="10" font-weight="600">② [</text>
    <rect class="hp-down-cell" x="252" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="266" y="42" text-anchor="middle" font-size="10" font-weight="700">2</text>
    <rect class="hp-down-cell" x="282" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="296" y="42" text-anchor="middle" font-size="10" font-weight="700">3</text>
    <rect class="hp-down-cellhot" x="312" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="326" y="42" text-anchor="middle" font-size="10" font-weight="700">9</text>
    <rect class="hp-down-cell" x="342" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="356" y="42" text-anchor="middle" font-size="10" font-weight="700">7</text>
    <rect class="hp-down-cell" x="372" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="386" y="42" text-anchor="middle" font-size="10" font-weight="700">5</text>
    <rect class="hp-down-cell" x="402" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="416" y="42" text-anchor="middle" font-size="10" font-weight="700">4</text>
    <text class="hp-down-arrlabel" x="435" y="40" font-size="10" font-weight="600">]</text>

    <!-- 단계 3 -->
    <text class="hp-down-arrlabel" x="460" y="40" font-size="10" font-weight="600">③ [</text>
    <rect class="hp-down-cell" x="482" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="496" y="42" text-anchor="middle" font-size="10" font-weight="700">2</text>
    <rect class="hp-down-cell" x="512" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="526" y="42" text-anchor="middle" font-size="10" font-weight="700">3</text>
    <rect class="hp-down-cellgood" x="542" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="556" y="42" text-anchor="middle" font-size="10" font-weight="700">4</text>
    <rect class="hp-down-cell" x="572" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="586" y="42" text-anchor="middle" font-size="10" font-weight="700">7</text>
    <rect class="hp-down-cell" x="602" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="616" y="42" text-anchor="middle" font-size="10" font-weight="700">5</text>
    <rect class="hp-down-cellhot" x="632" y="28" width="28" height="20" rx="3"/>
    <text class="hp-down-cellval" x="646" y="42" text-anchor="middle" font-size="10" font-weight="700">9</text>
    <text class="hp-down-arrlabel" x="665" y="40" font-size="10" font-weight="600">]</text>
  </g>
</svg>
</div>
<style>
.hp-down-title{fill:#333}
.hp-down-step{fill:#555}
.hp-down-val{fill:#0d47a1}
.hp-down-edge{stroke:#90a4ae;stroke-width:1.8}
.hp-down-edgehot{stroke:#f57c00;stroke-width:2.5}
.hp-down-note{fill:#666}
.hp-down-good{fill:#2e7d32}
.hp-down-flow{stroke:#888;stroke-width:2}
.hp-down-af{fill:#888}
.hp-down-arrtitle{fill:#555}
.hp-down-arrlabel{fill:#555;font-family:'Consolas','Monaco',monospace}
.hp-down-cell{fill:#e3f2fd;stroke:#64b5f6;stroke-width:1}
.hp-down-cellhot{fill:#ffcdd2;stroke:#e57373;stroke-width:1.2}
.hp-down-cellgood{fill:#c8e6c9;stroke:#66bb6a;stroke-width:1.2}
.hp-down-cellval{fill:#0d47a1;font-family:'Consolas','Monaco',monospace}
[data-mode="dark"] .hp-down-title{fill:#e0e0e0}
[data-mode="dark"] .hp-down-step{fill:#bbb}
[data-mode="dark"] .hp-down-val{fill:#0d47a1}
[data-mode="dark"] .hp-down-edge{stroke:#78909c}
[data-mode="dark"] .hp-down-edgehot{stroke:#ffb74d}
[data-mode="dark"] .hp-down-note{fill:#aaa}
[data-mode="dark"] .hp-down-good{fill:#a5d6a7}
[data-mode="dark"] .hp-down-flow{stroke:#999}
[data-mode="dark"] .hp-down-af{fill:#999}
[data-mode="dark"] .hp-down-arrtitle{fill:#bbb}
[data-mode="dark"] .hp-down-arrlabel{fill:#bbb}
[data-mode="dark"] .hp-down-cell{fill:#1a2a3a;stroke:#42a5f5}
[data-mode="dark"] .hp-down-cellhot{fill:#4a2525;stroke:#ef9a9a}
[data-mode="dark"] .hp-down-cellgood{fill:#1a3320;stroke:#81c784}
[data-mode="dark"] .hp-down-cellval{fill:#e3f2fd}
@media(max-width:768px){.hp-down svg{min-width:720px}}
</style>

C# 구현:

```csharp
void SiftDown(int i) {
    int n = heap.Count;
    while (true) {
        int left = 2 * i + 1;
        int right = 2 * i + 2;
        int smallest = i;

        if (left < n && heap[left].CompareTo(heap[smallest]) < 0)
            smallest = left;
        if (right < n && heap[right].CompareTo(heap[smallest]) < 0)
            smallest = right;

        if (smallest == i) break;   // 힙 속성 만족

        (heap[i], heap[smallest]) = (heap[smallest], heap[i]);
        i = smallest;
    }
}

public T Pop() {
    if (heap.Count == 0) throw new InvalidOperationException("Heap is empty");

    T min = heap[0];
    int last = heap.Count - 1;
    heap[0] = heap[last];
    heap.RemoveAt(last);
    if (heap.Count > 0) SiftDown(0);
    return min;
}

public T Peek() {
    if (heap.Count == 0) throw new InvalidOperationException("Heap is empty");
    return heap[0];      // 루트만 보기, O(1)
}
```

**시간 복잡도:** 마찬가지로 $O(\log n)$. 단, 주의할 점은 **sift-down은 비교 횟수가 sift-up보다 대략 2배**라는 것이다 — 각 레벨에서 두 자식과 비교한 뒤 작은 쪽을 골라야 하기 때문. 이 세부사항이 나중에 "왜 Floyd build-heap이 $O(n)$인가"에 영향을 준다.

### 전체 min-heap 클래스 (참고용)

위 두 연산을 합친 제네릭 min-heap이다.

```csharp
public class MinHeap<T> where T : IComparable<T> {
    private readonly List<T> heap = new();

    public int Count => heap.Count;

    public void Push(T value) {
        heap.Add(value);
        SiftUp(heap.Count - 1);
    }

    public T Pop() {
        if (heap.Count == 0) throw new InvalidOperationException();
        T min = heap[0];
        int last = heap.Count - 1;
        heap[0] = heap[last];
        heap.RemoveAt(last);
        if (heap.Count > 0) SiftDown(0);
        return min;
    }

    public T Peek() => heap.Count > 0 ? heap[0]
        : throw new InvalidOperationException();

    private void SiftUp(int i) {
        while (i > 0) {
            int p = (i - 1) / 2;
            if (heap[i].CompareTo(heap[p]) >= 0) break;
            (heap[i], heap[p]) = (heap[p], heap[i]);
            i = p;
        }
    }

    private void SiftDown(int i) {
        int n = heap.Count;
        while (true) {
            int l = 2 * i + 1, r = 2 * i + 2, s = i;
            if (l < n && heap[l].CompareTo(heap[s]) < 0) s = l;
            if (r < n && heap[r].CompareTo(heap[s]) < 0) s = r;
            if (s == i) break;
            (heap[i], heap[s]) = (heap[s], heap[i]);
            i = s;
        }
    }
}
```

---

## Part 4: build-heap과 heapsort

### Floyd(1964)의 $O(n)$ build-heap

배열 $n$개를 받아 힙으로 만드는 문제를 생각해보자. 가장 단순한 방법은 **요소를 하나씩 `Push`**하는 것이다.

```csharp
var heap = new MinHeap<int>();
foreach (int x in array) heap.Push(x);   // O(n log n)
```

이 경우 각 `Push`가 $O(\log n)$이므로 전체는 $O(n \log n)$. 정렬과 같은 복잡도다.

하지만 Robert Floyd가 1964년에 발견한 놀라운 사실: **이미 채워진 배열을 힙으로 만드는 것은 $O(n)$에 가능하다.**

알고리즘은 간단하다 — **배열의 마지막 비(非)리프 노드부터 뒤에서 앞으로 sift-down**을 적용한다.

```csharp
public static void BuildHeap<T>(T[] arr) where T : IComparable<T> {
    // 마지막 비리프의 인덱스는 n/2 - 1
    for (int i = arr.Length / 2 - 1; i >= 0; i--)
        SiftDown(arr, i, arr.Length);
}
```

**왜 $O(n)$인가?** 핵심은 **"깊은 노드가 많지만 sift-down 거리는 짧다"**는 비대칭성이다.

높이 $h$에서의 노드 수는 최대 $\lceil n / 2^{h+1} \rceil$개이고, 각 노드에서 sift-down은 최대 $h$만큼 내려간다. 총 비용은:

$$T(n) = \sum_{h=0}^{\lfloor \log_2 n \rfloor} \left\lceil \frac{n}{2^{h+1}} \right\rceil \cdot O(h) = O\left(n \sum_{h=0}^{\infty} \frac{h}{2^h}\right)$$

그리고 무한급수 $\sum_{h=0}^{\infty} h / 2^h = 2$가 상수로 수렴하므로:

$$T(n) = O(2n) = O(n)$$

직관적 그림: 트리의 **절반**이 리프(이동 안 함), **1/4**이 높이 1(한 칸 이동), **1/8**이 높이 2(두 칸 이동)... 지배적인 건 많은 리프들이고, 이들은 일을 거의 하지 않는다.

> **잠깐, 이건 짚고 넘어가자**
>
> **Q. 왜 sift-up이 아니라 sift-down으로 build-heap을 하는가?**
>
> sift-up으로 build-heap을 하면 $O(n \log n)$이 된다. **sift-up은 "부모로 올라가는" 연산**이고, 리프 근처 노드가 가장 많은데 이들이 루트까지 $\log n$ 올라가야 한다. 반대로 **sift-down은 "자식으로 내려가는"** 연산이고, 루트 근처 노드는 적지만 $\log n$ 내려가고 리프 근처 노드는 많지만 거의 안 움직인다. 노드 수와 이동 거리의 곱이 선형이 되는 구조다.
>
> **Q. 그럼 `Push`를 $n$번 하는 대신 항상 build-heap을 쓰는 게 좋은가?**
>
> 배열이 **미리 준비된 경우**라면 그렇다. 하지만 **스트리밍 입력**(요소가 하나씩 도착)이면 build-heap을 쓸 수 없으니 `Push`의 $O(n \log n)$을 받아들여야 한다.

### Heapsort — 힙으로 정렬하기

build-heap을 이해했으면 정렬은 공짜로 따라온다. Williams(1964)가 이 아이디어를 정리해서 발표했다.

1. **build-heap**으로 배열을 **max-heap**으로 만든다 — $O(n)$
2. 루트(최댓값)를 **배열의 맨 뒤**와 교환
3. 마지막 위치를 제외하고 sift-down — $O(\log n)$
4. 반복하면 배열이 오름차순으로 정렬된다

```csharp
public static void HeapSort<T>(T[] arr) where T : IComparable<T> {
    int n = arr.Length;

    // 1. max-heap 빌드 — O(n)
    for (int i = n / 2 - 1; i >= 0; i--)
        SiftDownMax(arr, i, n);

    // 2. 루트와 끝을 교환 후 축소 반복 — O(n log n)
    for (int end = n - 1; end > 0; end--) {
        (arr[0], arr[end]) = (arr[end], arr[0]);
        SiftDownMax(arr, 0, end);
    }
}
```

- **시간 복잡도:** 최선/평균/최악 모두 $O(n \log n)$
- **공간 복잡도:** $O(1)$ — 제자리(in-place) 정렬
- **안정성:** **불안정(unstable)** — 교환이 같은 키 순서를 뒤섞는다

### 왜 Quicksort에 밀렸는가

이론적 최악 복잡도는 heapsort가 더 낫다 (quicksort는 $O(n^2)$ 최악). 그런데 실무에선 quicksort 계열이 지배한다. 이유:

1. **캐시 지역성**이 떨어진다 — sift-down이 `i` → `2i+1` 또는 `2i+2`로 인덱스를 **두 배 점프**한다. 배열이 크면 캐시 라인을 벗어나는 접근이 잦다.
2. **비교/교환 횟수가 많다** — 각 sift-down 스텝이 자식 2개와 비교한다. Quicksort/Mergesort는 비교당 1회 이동에 가깝다.
3. **분기 예측** 친화성이 떨어진다.

현대 표준 라이브러리들의 선택:

| 언어 / 표준 | 정렬 알고리즘 |
| --- | --- |
| C# `Array.Sort` | Introsort (quicksort + heapsort fallback) |
| C++ `std::sort` | Introsort |
| Python `sorted` | **Timsort** (merge + insertion, 안정) |
| Java `Arrays.sort` (primitives) | Dual-pivot quicksort |
| Java `Arrays.sort` (objects) | Timsort |
| Rust `slice::sort` | Timsort 변형 (안정) |

**Introsort**(Musser 1997)는 평소엔 quicksort, 깊이가 $2\log n$을 넘으면 heapsort로 전환한다. Heapsort는 여기서 **"quicksort가 망가질 때의 안전망"** 역할을 한다 — 게임 스튜디오에서도 흔히 "나쁜 상황에서의 보장"이 필요할 때 쓰인다.

---

## Part 5: 힙의 변종들 — 언제 binary가 아닌가

이진 힙만 알면 실무의 95%는 해결된다. 그래도 남은 5%를 위해 몇 가지 변종을 살펴보자.

### d-ary Heap

**각 노드가 $d$개의 자식**을 가지는 힙. 부모/자식 인덱스 수식은:

$$\text{parent}(i) = \left\lfloor \frac{i-1}{d} \right\rfloor, \quad \text{child}_k(i) = di + k + 1 \ (k = 0, 1, ..., d-1)$$

트리 높이가 $\log_d n$으로 줄어드는 대신, 각 sift-down에서 $d$개 자식을 비교해야 한다.

| 연산 | Binary ($d=2$) | 4-ary | 8-ary |
| --- | --- | --- | --- |
| sift-up | $\log_2 n$ | $\log_4 n$ | $\log_8 n$ |
| sift-down | $2 \log_2 n$ | $4 \log_4 n = 2 \log_2 n$ | $8 \log_8 n \approx 2.67 \log_2 n$ |

<div class="hp-dary" style="margin:2rem 0;overflow-x:auto;">
<svg viewBox="0 0 780 260" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:780px;margin:0 auto;display:block;
            font-family:system-ui,-apple-system,sans-serif;">
  <defs>
    <filter id="hp-dary-sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1.5" stdDeviation="2" flood-opacity="0.15"/>
    </filter>
    <linearGradient id="hp-dary-g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e3f2fd"/><stop offset="100%" stop-color="#64b5f6"/>
    </linearGradient>
  </defs>

  <text class="hp-dary-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">Binary vs 4-ary Heap (노드 16개 기준)</text>

  <!-- Binary heap -->
  <text class="hp-dary-label" x="190" y="52" text-anchor="middle" font-size="13" font-weight="700">Binary (d=2)</text>
  <text class="hp-dary-sub" x="190" y="68" text-anchor="middle" font-size="11">높이 4, sift-down 비교 2×log₂16 = 8</text>

  <!-- binary tree skeleton -->
  <g stroke-width="1.5" fill="none" stroke="#90a4ae">
    <line x1="190" y1="86" x2="130" y2="116"/>
    <line x1="190" y1="86" x2="250" y2="116"/>
    <line x1="130" y1="124" x2="95" y2="152"/>
    <line x1="130" y1="124" x2="165" y2="152"/>
    <line x1="250" y1="124" x2="215" y2="152"/>
    <line x1="250" y1="124" x2="285" y2="152"/>
    <line x1="95" y1="160" x2="75" y2="188"/>
    <line x1="95" y1="160" x2="115" y2="188"/>
    <line x1="165" y1="160" x2="145" y2="188"/>
    <line x1="165" y1="160" x2="185" y2="188"/>
    <line x1="215" y1="160" x2="195" y2="188"/>
    <line x1="215" y1="160" x2="235" y2="188"/>
    <line x1="285" y1="160" x2="265" y2="188"/>
    <line x1="285" y1="160" x2="305" y2="188"/>
    <line x1="75" y1="196" x2="65" y2="222"/>
    <line x1="75" y1="196" x2="85" y2="222"/>
  </g>

  <g>
    <circle cx="190" cy="82" r="11" fill="url(#hp-dary-g)" filter="url(#hp-dary-sh)"/>
    <circle cx="130" cy="120" r="9" fill="url(#hp-dary-g)"/>
    <circle cx="250" cy="120" r="9" fill="url(#hp-dary-g)"/>
    <circle cx="95" cy="156" r="7" fill="url(#hp-dary-g)"/>
    <circle cx="165" cy="156" r="7" fill="url(#hp-dary-g)"/>
    <circle cx="215" cy="156" r="7" fill="url(#hp-dary-g)"/>
    <circle cx="285" cy="156" r="7" fill="url(#hp-dary-g)"/>
    <circle cx="75" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="115" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="145" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="185" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="195" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="235" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="265" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="305" cy="192" r="5" fill="url(#hp-dary-g)"/>
    <circle cx="65" cy="226" r="4" fill="url(#hp-dary-g)"/>
    <circle cx="85" cy="226" r="4" fill="url(#hp-dary-g)"/>
  </g>

  <!-- 구분선 -->
  <line class="hp-dary-div" x1="395" y1="50" x2="395" y2="240" stroke-dasharray="4,4"/>

  <!-- 4-ary -->
  <text class="hp-dary-label" x="590" y="52" text-anchor="middle" font-size="13" font-weight="700">4-ary (d=4)</text>
  <text class="hp-dary-sub" x="590" y="68" text-anchor="middle" font-size="11">높이 2, sift-down 비교 4×log₄16 = 8</text>

  <g stroke-width="1.5" fill="none" stroke="#90a4ae">
    <line x1="590" y1="86" x2="470" y2="126"/>
    <line x1="590" y1="86" x2="550" y2="126"/>
    <line x1="590" y1="86" x2="630" y2="126"/>
    <line x1="590" y1="86" x2="710" y2="126"/>
    <line x1="470" y1="134" x2="440" y2="176"/>
    <line x1="470" y1="134" x2="460" y2="176"/>
    <line x1="470" y1="134" x2="480" y2="176"/>
    <line x1="470" y1="134" x2="500" y2="176"/>
    <line x1="550" y1="134" x2="520" y2="176"/>
    <line x1="550" y1="134" x2="540" y2="176"/>
    <line x1="550" y1="134" x2="560" y2="176"/>
    <line x1="550" y1="134" x2="580" y2="176"/>
    <line x1="630" y1="134" x2="600" y2="176"/>
    <line x1="630" y1="134" x2="620" y2="176"/>
    <line x1="630" y1="134" x2="640" y2="176"/>
    <line x1="630" y1="134" x2="660" y2="176"/>
    <line x1="710" y1="134" x2="680" y2="176"/>
    <line x1="710" y1="134" x2="700" y2="176"/>
    <line x1="710" y1="134" x2="720" y2="176"/>
    <line x1="710" y1="134" x2="740" y2="176"/>
  </g>

  <g>
    <circle cx="590" cy="82" r="11" fill="url(#hp-dary-g)" filter="url(#hp-dary-sh)"/>
    <circle cx="470" cy="130" r="9" fill="url(#hp-dary-g)"/>
    <circle cx="550" cy="130" r="9" fill="url(#hp-dary-g)"/>
    <circle cx="630" cy="130" r="9" fill="url(#hp-dary-g)"/>
    <circle cx="710" cy="130" r="9" fill="url(#hp-dary-g)"/>
  </g>
  <g fill="url(#hp-dary-g)">
    <circle cx="440" cy="180" r="5"/><circle cx="460" cy="180" r="5"/>
    <circle cx="480" cy="180" r="5"/><circle cx="500" cy="180" r="5"/>
    <circle cx="520" cy="180" r="5"/><circle cx="540" cy="180" r="5"/>
    <circle cx="560" cy="180" r="5"/><circle cx="580" cy="180" r="5"/>
    <circle cx="600" cy="180" r="5"/><circle cx="620" cy="180" r="5"/>
    <circle cx="640" cy="180" r="5"/><circle cx="660" cy="180" r="5"/>
    <circle cx="680" cy="180" r="5"/><circle cx="700" cy="180" r="5"/>
    <circle cx="720" cy="180" r="5"/><circle cx="740" cy="180" r="5"/>
  </g>

  <text class="hp-dary-note" x="190" y="240" text-anchor="middle" font-size="10.5">트리가 깊지만 자식 비교 2회</text>
  <text class="hp-dary-note" x="590" y="240" text-anchor="middle" font-size="10.5">트리가 얕지만 자식 비교 4회 — 캐시 라인에 자식들이 몰린다</text>
</svg>
</div>
<style>
.hp-dary-title{fill:#333}.hp-dary-label{fill:#333}
.hp-dary-sub{fill:#666}.hp-dary-note{fill:#555}
.hp-dary-div{stroke:#bbb}
[data-mode="dark"] .hp-dary-title{fill:#e0e0e0}
[data-mode="dark"] .hp-dary-label{fill:#e0e0e0}
[data-mode="dark"] .hp-dary-sub{fill:#aaa}
[data-mode="dark"] .hp-dary-note{fill:#bbb}
[data-mode="dark"] .hp-dary-div{stroke:#555}
@media(max-width:768px){.hp-dary svg{min-width:720px}}
</style>

흥미로운 점: **이론적 비교 횟수는 $d=2$와 $d=4$가 거의 같다** ($2\log_2 n$). 그런데 LaMarca & Ladner(1996)의 실험은 **4-ary heap이 binary heap보다 실제로 빠르다**는 것을 보였다 — 이유는 캐시다.

- Binary heap에서 한 부모의 두 자식은 `2i+1`, `2i+2` — 인접
- 하지만 조부모에서 손자로 내려가려면 두 번의 점프가 필요
- 4-ary heap은 한 부모의 네 자식이 `4i+1, 4i+2, 4i+3, 4i+4` — 캐시 라인에 모두 들어간다

**실무에서 4-ary 또는 8-ary가 binary보다 좋은 경우:**
- 키 크기가 작을 때 (한 캐시 라인에 자식이 모두 들어감)
- sift-down이 sift-up보다 훨씬 많을 때 (extract-min 중심 워크로드)
- 예: 대규모 Dijkstra/A*

### Pairing Heap와 Fibonacci Heap

$O(1)$ **amortized decrease-key**를 제공하는 힙들. Dijkstra의 이론적 복잡도를 $O(E + V \log V)$로 줄인다 (binary heap은 $O((V+E) \log V)$).

| 힙 | insert | extract-min | decrease-key | 구조 |
| --- | --- | --- | --- | --- |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | 배열 |
| **4-ary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | 배열 |
| **Pairing Heap** | $O(1)$ | $O(\log n)$* | $O(\log n)$* | 포인터 트리 |
| **Fibonacci Heap** | $O(1)$ | $O(\log n)$* | $O(1)$* | 포인터 트리 |

*amortized (분할 상환)

**Fibonacci heap**(Fredman & Tarjan 1987)은 이론적 우월성에도 불구하고 실무에서 잘 안 쓰인다:

1. **상수가 크다** — $O(1)$이라도 상수가 커서 $O(\log n)$ binary heap을 실제로 이길 때는 거의 모두 "매우 큰 그래프에서 decrease-key가 많을 때"만
2. **구현이 복잡** — 부모 포인터, 자식 리스트, mark 비트, 랭크, cascading cut 등 관리 포인트가 많다
3. **캐시 재앙** — 포인터 기반 구조라 힙 영역을 돌아다닌다. 1편에서 봤던 linked list의 문제와 같다
4. **decrease-key 자체가 드물다** — A*에서는 lazy deletion으로 회피 가능

**Pairing heap**(Fredman, Sedgewick, Sleator, Tarjan 1986)은 Fibonacci의 단순화 버전. 이론적 보장은 조금 약하지만 상수가 작아 실측 성능은 종종 Fibonacci보다 낫다. Boost, LEDA 같은 고성능 라이브러리에서 선택지로 제공된다.

> **잠깐, 이건 짚고 넘어가자**
>
> **Q. Dijkstra에서 Fibonacci heap을 쓰면 항상 빠른가?**
>
> **아니다.** Chen et al.(2007)과 여러 실측 연구는 **실제 데이터셋에서 binary heap 또는 4-ary heap이 Fibonacci heap보다 빠르다**는 것을 반복해서 보였다. 이론적 $O(V^2)$ dense graph처럼 $E \gg V$인 극단에서만 Fibonacci가 의미 있는 이점을 보인다.
>
> **Q. 그럼 언제 Fibonacci heap을 쓰는가?**
>
> 실무에선 거의 없다. 이론적 분석을 위한 "존재 증명"의 역할이 크다. 연구 논문, 알고리즘 교재, 그리고 특정 amortized 분석이 필요한 경우에만.

---

## Part 6: 게임 개발에서의 힙

### A* open set — decrease-key 문제

[5편 Graph](/posts/Graph/)의 A* 코드를 다시 보자:

```csharp
List<Vector2Int> AStar(Vector2Int start, Vector2Int goal) {
    var openSet = new PriorityQueue<Vector2Int, float>();
    var gScore = new Dictionary<Vector2Int, float>();
    // ...
    while (openSet.Count > 0) {
        var current = openSet.Dequeue();
        // ...
        foreach (var next in GetNeighbors(current)) {
            float tentativeG = gScore[current] + Cost(current, next);
            if (tentativeG < gScore.GetValueOrDefault(next, float.MaxValue)) {
                gScore[next] = tentativeG;
                openSet.Enqueue(next, tentativeG + Heuristic(next, goal));
            }
        }
    }
}
```

문제: 같은 노드 `next`가 **이미 open set에 있는데 더 작은 f값으로 다시 들어가면?**

교과서적 답은 **decrease-key** — open set에서 해당 노드를 찾아 우선순위를 낮춘다. 그런데 binary heap은 이 연산이 $O(n)$이다 (해당 원소를 찾아야 하므로). 노드 위치를 별도 `Dictionary`로 추적하면 $O(\log n)$.

실무적 답은 더 간단하다: **lazy deletion**.

```csharp
// lazy deletion 패턴
while (openSet.Count > 0) {
    var (current, f) = openSet.Dequeue();

    if (f > gScore[current]) continue;  // stale entry — 이미 더 좋은 값 존재

    if (current == goal) return ReconstructPath(...);

    foreach (var next in GetNeighbors(current)) {
        float tentativeG = gScore[current] + Cost(current, next);
        if (tentativeG < gScore.GetValueOrDefault(next, float.MaxValue)) {
            gScore[next] = tentativeG;
            openSet.Enqueue(next, tentativeG + Heuristic(next, goal));
            // 이전의 stale entry는 그대로 둔다 — 꺼낼 때 체크
        }
    }
}
```

- 같은 노드를 여러 번 push해도 문제없다
- 꺼낼 때 `f > gScore[current]`로 "이미 유효하지 않음"을 판별
- 구현 단순, binary heap만으로 충분
- 메모리는 조금 더 쓰지만 대부분 무시 가능

Unity의 A* Pathfinding Project, Recast/Detour 등 실무 라이브러리 대부분이 이 패턴을 쓴다.

### 이벤트 / 타이머 스케줄러

게임 서버나 에디터 툴에서 **"시각 $t$에 이 작업을 실행하라"**를 대량 처리해야 할 때 힙이 적합하다.

```csharp
// 간단한 타이머 큐 — (실행시각, 작업) 페어를 시각 오름차순으로 관리
public class TimerQueue {
    private readonly MinHeap<(float time, Action action)> heap = new();

    public void Schedule(float time, Action action) {
        heap.Push((time, action));       // O(log n)
    }

    public void Tick(float now) {
        while (heap.Count > 0 && heap.Peek().time <= now) {
            var (_, action) = heap.Pop();
            action();                    // O(log n) per dispatch
        }
    }
}
```

이 패턴은 게임 엔진의 애니메이션 이벤트, 쿨다운, 버프/디버프 만료 처리에서 자주 보인다. 단순한 리스트+매 프레임 스캔 방식은 이벤트 수가 늘수록 선형 비용이 되지만, 힙은 실제로 "지금 만료되는 것"만 꺼낸다.

주의: **`heap.Peek()`도 $O(1)$**이므로 "다음 이벤트 시각"을 싸게 알 수 있다. 슬립 타이머를 설정할 때 유용하다.

### AI 행동 점수

유틸리티 AI에서 **가장 점수가 높은 행동 N개**만 고려하고 싶을 때, **크기 $k$로 고정된 min-heap**을 사용한다.

```csharp
// 상위 k개 행동 유지
public class TopKActions {
    private readonly MinHeap<(float score, Action action)> heap = new();
    private readonly int k;

    public TopKActions(int k) { this.k = k; }

    public void Consider(float score, Action action) {
        if (heap.Count < k) {
            heap.Push((score, action));
        } else if (score > heap.Peek().score) {
            heap.Pop();                    // 가장 낮은 점수 제거
            heap.Push((score, action));
        }
    }

    public IEnumerable<Action> GetTopK() =>
        heap.ToArray().OrderByDescending(x => x.score).Select(x => x.action);
}
```

**min**-heap을 쓰는 게 포인트다. 크기 $k$ top-k 문제에서 min-heap의 루트는 **"지금 유지 중인 k개 중 가장 낮은 것"**이다. 새 후보가 이보다 크면 교체하면 된다. 이 기법은 일반적인 top-k 문제에서도 널리 쓰인다.

### Unity NativeContainer 관점

아쉽게도 Unity는 기본 제공 `NativeHeap`을 갖고 있지 않다. [JobSystem 4편 NativeContainer 심화](/posts/NativeContainerDeepDive/)에서 본 패턴으로 **직접 구현**해야 한다.

핵심 고려사항:
- `NativeList<T>`를 내부 저장소로 사용 (배열 기반이니 힙과 궁합 좋음)
- `[NativeContainer]` 속성과 `AtomicSafetyHandle` 연동 — Safety System 통합
- Burst 호환: 제네릭 `IComparable` 대신 `struct IComparer<T>` 전달 방식 고려
- 병렬 삽입은 어려움 — sift-up이 루트까지 경쟁하므로 락이 필요. 보통 **큐로 수집 후 싱글 스레드에서 pour** 패턴

실무에선 [BurstAStarGridExample](https://github.com/Unity-Technologies/com.unity.demoteam.digital-human) 같은 공식/커뮤니티 예제나, Gilzu의 `NativeMinHeap` 같은 공개 구현을 참고하는 것이 빠르다.

---

## Part 7: .NET `PriorityQueue<TElement, TPriority>` 분석

.NET 6부터 `System.Collections.Generic.PriorityQueue<TElement, TPriority>`가 공식 표준으로 추가되었다. 내부는 **4-ary min-heap**이다 — 위에서 본 이유들 때문에 binary가 아닌 4-ary를 선택했다.

```csharp
var pq = new PriorityQueue<string, int>();
pq.Enqueue("task-a", 3);
pq.Enqueue("task-b", 1);       // 우선순위 숫자가 작을수록 먼저
pq.Enqueue("task-c", 2);

while (pq.Count > 0) {
    string task = pq.Dequeue();
    // task-b, task-c, task-a 순으로 나온다
}
```

공식 구현의 주요 특징:

- **TElement와 TPriority 분리** — 큐에 저장되는 값과 정렬 키가 별개 (사용성 향상)
- **4-ary heap** — `dotnet/runtime` 소스에서 `const int Arity = 4`로 확인 가능
- **`EnqueueDequeue`** — push 후 pop을 연달아 할 때의 최적화 (top-k 패턴에 유용)
- **`UnorderedItems`** — 힙을 "보이는 순서로가 아니라" 저장된 순서로 열거
- **`Dictionary<TElement, ...>` 미포함** — decrease-key는 제공하지 않는다. lazy deletion을 써야 한다

**주의사항:**
- **스레드 안전 아님** — 멀티스레드 환경에서는 외부 락 필요
- **중복 키 허용** — 같은 priority로 여러 Enqueue 가능, 순서는 비결정적 (불안정)
- **안정 정렬이 필요**하면 priority를 `(originalPriority, tieBreaker)` 튜플로 만들어야 함

간단한 A* open set이라면 `PriorityQueue<Vector2Int, float>` 한 줄로 끝난다. 직접 구현할 이유는 (1) 커스텀 비교자, (2) 특수 할당 패턴, (3) Burst/Job System 통합 정도만 남는다.

---

## 정리

### 핵심 요약

1. **우선순위 큐는 "최솟값/최댓값만"이라는 부분 문제다** — 완전 정렬은 과잉 사양, 부분 순서로 $O(\log n)$을 얻는다
2. **이진 힙은 완전 이진 트리를 배열에 매핑한 구조** — 포인터 0개, 인덱스 산술만으로 부모/자식을 오간다
3. **sift-up과 sift-down이 전부다** — push, pop, 모든 변형 연산이 이 둘의 조합이다
4. **Floyd의 $O(n)$ build-heap** — 깊은 노드가 많고 얕은 이동만 필요하다는 비대칭성의 귀결
5. **실무에선 4-ary heap이 binary heap을 이긴다** — 캐시 라인에 자식이 몰리는 레이아웃 이점
6. **Fibonacci heap은 이론용** — 실측에서 binary/4-ary에 밀리고 구현 복잡도만 높다
7. **A* decrease-key는 lazy deletion으로 회피** — 꺼낼 때 stale 체크, push는 그냥 중복 허용
8. **.NET `PriorityQueue<TElement, TPriority>`는 4-ary heap** — 직접 구현할 이유가 많지 않다

### 어느 층위의 통찰인가

1편 배열과 연결 리스트에서 봤던 "**캐시가 복잡도보다 중요할 수 있다**"는 명제가 여기서도 반복된다. Fibonacci heap의 이론적 $O(1)$ decrease-key가 실무에서 binary heap에 지는 것은, 우리가 이론과 현실 사이의 상수를 과소평가했기 때문이다.

그리고 힙은 **"BST보다 약한 구조가 특정 문제에선 더 강하다"**는 예시이기도 하다. "부분 순서"만 유지하는 대가로 배열 매핑이라는 공짜 선물을 받는다. 자료구조 설계에서 **"얼마나 적게 약속할 수 있는가"**가 오히려 자유도를 높인다는 관점 — BST보다 힙, 전체 정렬보다 top-k. CS의 많은 아이디어가 이 방향으로 흐른다.

이 외전을 끝으로 1단계(자료구조와 메모리) 주변의 빚을 정리했다. 다음부터는 예정대로 **2단계: OS와 동시성**으로 들어간다. 프로세스, 스레드, 락, 그리고 멀티코어에서의 재난들을 살펴본다.

---

## 참고 자료

**원전 및 주요 논문**
- Williams, J.W.J., "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), pp. 347–348 (1964) — **binary heap의 원전**
- Floyd, R.W., "Algorithm 245: Treesort 3", *Communications of the ACM* 7(12), p. 701 (1964) — **$O(n)$ build-heap**
- Johnson, D.B., "Priority queues with update and finding minimum spanning trees", *Information Processing Letters* 4(3), pp. 53–57 (1975) — **d-ary heap**
- Fredman, M.L., Sedgewick, R., Sleator, D.D., Tarjan, R.E., "The pairing heap: A new form of self-adjusting heap", *Algorithmica* 1(1), pp. 111–129 (1986)
- Fredman, M.L. & Tarjan, R.E., "Fibonacci heaps and their uses in improved network optimization algorithms", *Journal of the ACM* 34(3), pp. 596–615 (1987)
- LaMarca, A. & Ladner, R.E., "The influence of caches on the performance of heaps", *ACM Journal of Experimental Algorithmics* 1, Article 4 (1996) — **4-ary heap이 binary보다 빠른 실증**
- Dutton, R.D., "Weak-heap sort", *BIT Numerical Mathematics* 33(3), pp. 372–381 (1993)
- Brodal, G.S., "Worst-case efficient priority queues", *Proceedings of SODA* (1996)
- Chen, M., Chowdhury, R.A., Ramachandran, V., Roche, D.L., Tong, L., "Priority Queues and Dijkstra's Algorithm", UT Austin Technical Report TR-07-54 (2007) — **Fibonacci vs binary 실측 비교**

**교재**
- Cormen, T.H., Leiserson, C.E., Rivest, R.L., Stein, C., *Introduction to Algorithms (CLRS)*, 4th Edition, MIT Press — Chapter 6 (Heapsort), Chapter 19 (Fibonacci Heaps)
- Sedgewick, R. & Wayne, K., *Algorithms*, 4th Edition, Addison-Wesley — Chapter 2.4 Priority Queues
- Knuth, D., *The Art of Computer Programming Vol. 3: Sorting and Searching*, 2nd Edition, Addison-Wesley — Section 5.2.3 Sorting by Selection (heapsort)
- Weiss, M.A., *Data Structures and Algorithm Analysis in C++*, 4th Edition, Pearson — Chapter 6 Priority Queues

**구현 참고**
- .NET `PriorityQueue<TElement, TPriority>` — [dotnet/runtime 소스](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Collections/src/System/Collections/Generic/PriorityQueue.cs): 4-ary min-heap 공식 구현
- C++ `std::priority_queue` — libstdc++, libc++: binary heap 기반
- Java `java.util.PriorityQueue` — OpenJDK: binary heap 기반
- Python `heapq` — [CPython 소스](https://github.com/python/cpython/blob/main/Lib/heapq.py): binary min-heap, 튜플로 priority 지정
- Boost Heap — [boost.org/libs/heap](https://www.boost.org/doc/libs/release/libs/heap/): binary, d-ary, pairing, Fibonacci, skew heap을 모두 제공

**게임 개발 맥락**
- Millington, I. & Funge, J., *Artificial Intelligence for Games*, 3rd Edition, CRC Press — A*, open set 관리
- Recast & Detour — [github.com/recastnavigation](https://github.com/recastnavigation/recastnavigation): 실무 NavMesh 라이브러리의 힙 활용
- A* Pathfinding Project (Unity) — [arongranberg.com/astar](https://arongranberg.com/astar/): lazy deletion 기반 open set
