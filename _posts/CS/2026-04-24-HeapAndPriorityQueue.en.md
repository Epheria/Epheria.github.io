---
title: "CS Roadmap (Bonus) — Heaps and Priority Queues: The Economics of Partial Order"
lang: en
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
  - "A priority queue is a problem where only the minimum (or maximum) needs to be fast — a full sort (O(n log n)) is overkill. Heaps maintain only a 'partial order' to achieve O(log n) push/pop"
  - "A binary heap is the magic of representing a complete binary tree as an array — with zero pointers, you navigate the tree using only index arithmetic: parent = (i-1)/2, left = 2i+1"
  - "Floyd's (1964) bottom-up build-heap runs in O(n). Counterintuitively, it's not O(n log n) — deeper levels have many nodes but only shallow sift-downs"
  - "In practice, A* open-set decrease-key is handled via lazy deletion (ignoring stale entries when popped). Fibonacci heap's O(1) decrease-key actually loses to binary heap on grid A* because of the heavy constant factor"
---

## Introduction

> This article is a bonus installment of the **CS Roadmap** series.

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

In [Part 5 on Graphs](/posts/Graph/), when we covered Dijkstra and A*, we left one sentence hanging: *"Using a priority queue (binary heap), we get $O((V+E) \log V)$."* But what that "binary heap" is, why it's binary, and how it achieves $O(\log n)$ — all of that was deferred. This bonus pays back that debt.

After Phase 1 (Data Structures and Memory) wrapped up in six installments, heaps and priority queues remained as "that one core piece we skipped." They're an application of trees and an arithmetic of arrays; they're the engine of A* and the heart of event schedulers. A small topic, but one that shows up too often in game development to skip over.

What this article covers:

1. Why partial order suffices instead of a full sort
2. How a binary heap operates on top of an array
3. The mathematical basis of sift-up / sift-down and a C# implementation
4. Floyd's (1964) $O(n)$ build-heap
5. d-ary heap, pairing heap, Fibonacci heap — when to use which
6. The decrease-key problem in A*'s open set and its practical solution
7. Analysis of .NET's `PriorityQueue<TElement, TPriority>`

---

## Part 1: The Priority Queue Problem

### "Fast minimum only" — A Full Sort Is Overkill

Consider this problem.

> You have 1,000,000 integers. You want to extract only the 1,000 smallest in order.

Intuitively, the solution that comes to mind is **sort everything, then take the first 1,000**. Sorting the whole thing costs $O(n \log n)$, and the output takes $O(k)$. But think about it — that's wasteful. We never use the order of the remaining 999,000 elements. **What we actually need is just two operations: "extract minimum" and "insert."**

This is the **priority queue** problem. Like a regular queue (FIFO), it has a "push and pop" interface, but the pop order is not "first in" — it's **"highest priority first."**

```
Regular queue (FIFO):          Priority queue:

  [4, 7, 1, 9, 3]                [4, 7, 1, 9, 3]
   ↓ dequeue                      ↓ extract-min
   4 (insertion order)            1 (smallest value)
```

Where this problem shows up in games:

- **A* / Dijkstra**: "Pop the node with the smallest f-value"
- **Event scheduler**: "Pop the event with the earliest execution time"
- **AI action selection**: "Pop the action with the highest utility score"
- **DSP / audio mixing**: "Play only the top N most important sound channels"

### Tradeoffs of Naive Implementations

To appreciate heaps, we need to first ask: **"Why not use an array or a BST?"**

| Structure | insert | extract-min | Notes |
| --- | --- | --- | --- |
| **Unsorted Array** | $O(1)$ | $O(n)$ | Append to the end; scan the whole thing on pop |
| **Sorted Array** | $O(n)$ | $O(1)$ | Binary search to find position, but shift cost is $O(n)$ |
| **Sorted Linked List** | $O(n)$ | $O(1)$ | Linear search, no shifting, but still |
| **BST (balanced)** | $O(\log n)$ | $O(\log n)$ | 4–5 pointers/node, cache misses |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | **Implemented as an array, zero pointers** |

Looking at the table, a natural question arises: "If the heap has the same complexity as a BST, why is it better?" The answer lies in **constants and cache** — the same story from Part 1.

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

  <text class="hp-cmp-title" x="390" y="28" text-anchor="middle" font-weight="700" font-size="16">Priority Queue Implementations Compared</text>

  <rect x="20" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g1)" filter="url(#hp-cmp-sh)"/>
  <rect x="215" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g2)" filter="url(#hp-cmp-sh)"/>
  <rect x="410" y="60" width="175" height="220" rx="12" fill="url(#hp-cmp-g3)" filter="url(#hp-cmp-sh)"/>
  <rect x="605" y="60" width="155" height="220" rx="12" fill="url(#hp-cmp-g4)" filter="url(#hp-cmp-sh)" stroke="#2e7d32" stroke-width="2"/>

  <text class="hp-cmp-name" x="107" y="88" text-anchor="middle" font-weight="700" font-size="14">Sorted Array</text>
  <text class="hp-cmp-name" x="302" y="88" text-anchor="middle" font-weight="700" font-size="14">Unsorted Array</text>
  <text class="hp-cmp-name" x="497" y="88" text-anchor="middle" font-weight="700" font-size="14">BST (balanced)</text>
  <text class="hp-cmp-name hp-cmp-best" x="682" y="88" text-anchor="middle" font-weight="700" font-size="14">Binary Heap</text>

  <text class="hp-cmp-label" x="35" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-bad" x="180" y="118" text-anchor="end" font-size="13" font-weight="700">O(n)</text>
  <text class="hp-cmp-label" x="230" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-good" x="375" y="118" text-anchor="end" font-size="13" font-weight="700">O(1)</text>
  <text class="hp-cmp-label" x="425" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-mid" x="570" y="118" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>
  <text class="hp-cmp-label" x="620" y="118" font-size="11.5" font-weight="600">insert</text>
  <text class="hp-cmp-mid" x="745" y="118" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>

  <text class="hp-cmp-label" x="35" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-good" x="180" y="145" text-anchor="end" font-size="13" font-weight="700">O(1)</text>
  <text class="hp-cmp-label" x="230" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-bad" x="375" y="145" text-anchor="end" font-size="13" font-weight="700">O(n)</text>
  <text class="hp-cmp-label" x="425" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-mid" x="570" y="145" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>
  <text class="hp-cmp-label" x="620" y="145" font-size="11.5" font-weight="600">extract-min</text>
  <text class="hp-cmp-mid" x="745" y="145" text-anchor="end" font-size="13" font-weight="700">O(log n)</text>

  <line class="hp-cmp-div" x1="35" y1="160" x2="180" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="230" y1="160" x2="375" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="425" y1="160" x2="570" y2="160" stroke-dasharray="3,3"/>
  <line class="hp-cmp-div" x1="620" y1="160" x2="745" y2="160" stroke-dasharray="3,3"/>

  <text class="hp-cmp-memtitle" x="107" y="180" text-anchor="middle" font-size="11" font-weight="600">Memory/node</text>
  <text class="hp-cmp-mem" x="107" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="302" y="180" text-anchor="middle" font-size="11" font-weight="600">Memory/node</text>
  <text class="hp-cmp-mem" x="302" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="497" y="180" text-anchor="middle" font-size="11" font-weight="600">Memory/node</text>
  <text class="hp-cmp-mem hp-cmp-memwarn" x="497" y="198" text-anchor="middle" font-size="13" font-weight="700">4–5 words</text>
  <text class="hp-cmp-memtitle" x="682" y="180" text-anchor="middle" font-size="11" font-weight="600">Memory/node</text>
  <text class="hp-cmp-mem" x="682" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>

  <text class="hp-cmp-memtitle" x="107" y="224" text-anchor="middle" font-size="11" font-weight="600">Cache friendly</text>
  <text class="hp-cmp-good" x="107" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ contiguous</text>
  <text class="hp-cmp-memtitle" x="302" y="224" text-anchor="middle" font-size="11" font-weight="600">Cache friendly</text>
  <text class="hp-cmp-good" x="302" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ contiguous</text>
  <text class="hp-cmp-memtitle" x="497" y="224" text-anchor="middle" font-size="11" font-weight="600">Cache friendly</text>
  <text class="hp-cmp-bad" x="497" y="242" text-anchor="middle" font-size="13" font-weight="700">✗ pointer chasing</text>
  <text class="hp-cmp-memtitle" x="682" y="224" text-anchor="middle" font-size="11" font-weight="600">Cache friendly</text>
  <text class="hp-cmp-good" x="682" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ contiguous</text>

  <text class="hp-cmp-weak" x="107" y="268" text-anchor="middle" font-size="11.5" font-style="italic">O(n) shift on insert</text>
  <text class="hp-cmp-weak" x="302" y="268" text-anchor="middle" font-size="11.5" font-style="italic">repeated scans</text>
  <text class="hp-cmp-weak" x="497" y="268" text-anchor="middle" font-size="11.5" font-style="italic">cache miss + memory</text>
  <text class="hp-cmp-strong" x="682" y="268" text-anchor="middle" font-size="11.5" font-weight="700">balanced optimum</text>
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

### The Heap's Core Idea: Partial Order Is Enough

The key insight in the priority queue problem is this.

> **We only extract one minimum at a time. We don't care about the relative order of the remaining elements.**

A full sort determines "$a < b$ or $a > b$" for every pair. But extracting the minimum only requires the far weaker condition: **"the root is the overall minimum."** This "weakness" is what gives room for $O(\log n)$.

**The heap's promise (min-heap):**
- The root is the overall minimum
- Each parent is **less than or equal to** both of its children (no order enforced between siblings)

This is called the **heap property**. Unlike the BST's "left < parent < right," a heap only enforces **the parent-child relation**, leaving sibling and subtree ordering arbitrary. This "looseness" is the secret behind fast insert/delete.

---

## Part 2: The Structure of a Binary Heap

### Complete Binary Trees

In [Part 4 on Trees](/posts/Tree/), we defined a **complete binary tree**: "a tree where every level except possibly the last is completely filled, and the last level is filled from the left." A binary heap **must** be a complete binary tree.

```
         1
       /   \
      3     2
     / \   / \
    7   5 4   8
   / \
  9  10

height = ⌊log₂(n)⌋ = ⌊log₂(8)⌋ = 3
the last level is filled from the left
```

Why **complete**? There are two reasons.

1. **Height is always $\lfloor \log_2 n \rfloor$** — ensures sift-up/down is $O(\log n)$
2. **It can be represented as an array** — no empty slots, so the array packs tightly

The second reason is the magic of this data structure.

### A Tree Represented as an Array — A Tree Without Pointers

If you store the nodes of a complete binary tree in level order (top-to-bottom, left-to-right) in an array, **parent-child relations become index arithmetic**.

Using 0-based indexing:

$$\text{parent}(i) = \left\lfloor \frac{i-1}{2} \right\rfloor, \quad \text{left}(i) = 2i+1, \quad \text{right}(i) = 2i+2$$

The 1-based form is prettier (Williams's original paper used it):

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

  <text class="hp-map-title" x="390" y="26" text-anchor="middle" font-weight="700" font-size="16">Array ↔ Complete Binary Tree: Index Mapping</text>

  <text class="hp-map-section" x="390" y="58" text-anchor="middle" font-size="13" font-weight="600">Complete Binary Tree (min-heap)</text>

  <line class="hp-map-edge" x1="390" y1="95" x2="250" y2="155"/>
  <line class="hp-map-edge" x1="390" y1="95" x2="530" y2="155"/>
  <line class="hp-map-edge" x1="250" y1="175" x2="170" y2="235"/>
  <line class="hp-map-edge" x1="250" y1="175" x2="330" y2="235"/>
  <line class="hp-map-edge" x1="530" y1="175" x2="450" y2="235"/>
  <line class="hp-map-edge" x1="530" y1="175" x2="610" y2="235"/>
  <line class="hp-map-edge" x1="170" y1="255" x2="130" y2="315"/>

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

  <text class="hp-map-section" x="390" y="378" text-anchor="middle" font-size="13" font-weight="600">Array representation (contiguous memory)</text>

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

  <rect class="hp-map-formula" x="600" y="340" width="160" height="70" rx="8"/>
  <text class="hp-map-ftitle" x="680" y="358" text-anchor="middle" font-size="11" font-weight="700">Index arithmetic</text>
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

**Why is this so powerful?**

1. **Contiguous memory** — the entire tree is a single array. The prefetcher pulls in the next nodes ahead of time
2. **Zero pointers** — one value per node. Memory density far exceeds a BST that uses 4–5 words per node
3. **Cache line efficiency** — 16 `int` elements fit in a 64-byte cache line. The top few levels stay resident in L1

In Part 1 on arrays and linked lists, we said **"arrays store data in contiguous memory and enjoy the maximum benefit of cache locality."** A heap is a data structure that transplants this principle into a tree.

> **Wait, let's clarify this**
>
> **Q. The 1-based index has prettier formulas, so why does everyone use 0-based in practice?**
>
> Because arrays are 0-based in most languages. Leaving `array[0]` empty and starting at 1 wastes one cell and causes confusion. Most implementations (C++ `std::priority_queue`, .NET `PriorityQueue`) use 0-based. The formulas are just slightly less elegant — the behavior is the same.
>
> **Q. Does it have to be a complete binary tree? Why not build it freely like a BST?**
>
> Breaking completeness kills the array representation — you'd need to express "empty slots," which means sentinels or pointers in the array, which is essentially retreating back to a BST. Also, if the tree leans to one side, the height becomes $O(n)$ and operations slow down. **"Packed into an array with no gaps"** is the heap's identity.

---

## Part 3: Core Operations — sift-up and sift-down

These are the two fundamental operations for preserving the heap property. Both insertion and deletion reduce to these.

### sift-up (percolate up) — Insertion

The strategy when inserting a new element:

1. **Append to the end** of the array (preserving completeness)
2. Compare with the parent; if smaller, **swap**
3. Repeat until the heap property is restored (or the root is reached)

```
Insert 1:              Step 1: compare       Step 2: restored
                      [1]                    [1]
     [1]                / \                   / \
    /   \              [3] [2]               [3] [2]
   [3]  [2]            / \ / \               / \ / \
   /\   /\            [7][5][4][8]          [7][5][4][8]
  [7][5][4][8]        / \                    / \
                     [9][1] ← new            [1][9]  ← compare 1 with 5 → swap
```

Hold on, the above example is a bit simplified. When we actually insert 1 at index 9:

```
Initial:    [1, 3, 2, 7, 5, 4, 8, 9]
Add 1:      [1, 3, 2, 7, 5, 4, 8, 9, 1]  ← index 8

sift-up:
  i=8, parent(8)=3, heap[3]=7 > 1 → swap
    [1, 3, 2, 1, 5, 4, 8, 9, 7]
  i=3, parent(3)=1, heap[1]=3 > 1 → swap
    [1, 1, 2, 3, 5, 4, 8, 9, 7]
  i=1, parent(1)=0, heap[0]=1 ≤ 1 → stop
```

C# implementation:

```csharp
void SiftUp(int i) {
    while (i > 0) {
        int parent = (i - 1) / 2;
        if (heap[i].CompareTo(heap[parent]) >= 0)
            break;                        // heap property satisfied
        (heap[i], heap[parent]) = (heap[parent], heap[i]);
        i = parent;
    }
}

public void Push(T value) {
    heap.Add(value);
    SiftUp(heap.Count - 1);
}
```

**Time complexity:** In the worst case, we climb all the way to the root: $O(\log n)$. The tree's height is fixed at $\lfloor \log_2 n \rfloor$.

### sift-down (percolate down) — Deletion / Extract-Min

The operation that pops the root. A bit trickier.

1. **Save the root (minimum) as the return value**
2. Move **the last array element** to the root position
3. Decrement the array length (discard the tail)
4. From the root, compare with **the smaller of the two children** and swap if larger
5. Repeat until the heap property is restored (or a leaf is reached)

Step 4 is the key — **since the parent must be smaller than both children, we must swap with the "smaller child."** Swapping with the larger one would make that child exceed its sibling and break the property.

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

  <text class="hp-down-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">sift-down: remove the root and restore the heap</text>

  <text class="hp-down-step" x="130" y="58" text-anchor="middle" font-size="12" font-weight="700">① Move last to root</text>
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
  <text class="hp-down-note" x="130" y="232" text-anchor="middle" font-size="10">Root broken with 9</text>
  <text class="hp-down-note" x="130" y="246" text-anchor="middle" font-size="10">(9 &gt; 3, 9 &gt; 2)</text>

  <line class="hp-down-flow" x1="230" y1="150" x2="275" y2="150" marker-end="url(#hp-down-arr)"/>

  <text class="hp-down-step" x="390" y="58" text-anchor="middle" font-size="12" font-weight="700">② Swap with smaller child (2)</text>
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
  <text class="hp-down-note" x="390" y="232" text-anchor="middle" font-size="10">Root OK, but 9 &gt; 4</text>
  <text class="hp-down-note" x="390" y="246" text-anchor="middle" font-size="10">descend further</text>

  <line class="hp-down-flow" x1="490" y1="150" x2="535" y2="150" marker-end="url(#hp-down-arr)"/>

  <text class="hp-down-step" x="650" y="58" text-anchor="middle" font-size="12" font-weight="700">③ Swap with 4 → done</text>
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
  <text class="hp-down-note hp-down-good" x="650" y="232" text-anchor="middle" font-size="10" font-weight="700">Heap restored</text>
  <text class="hp-down-note" x="650" y="246" text-anchor="middle" font-size="10">moves = tree height = O(log n)</text>

  <g transform="translate(60, 290)">
    <text class="hp-down-arrtitle" x="330" y="15" text-anchor="middle" font-size="12" font-weight="600">Array trace</text>
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

C# implementation:

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

        if (smallest == i) break;   // heap property satisfied

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
    return heap[0];      // just look at the root, O(1)
}
```

**Time complexity:** Also $O(\log n)$. One detail worth noting: **sift-down performs roughly twice as many comparisons as sift-up** — at each level, you must compare both children before picking the smaller one. This subtlety affects "why Floyd's build-heap is $O(n)$" later on.

### Full min-heap class (for reference)

A generic min-heap combining the two operations above.

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

## Part 4: build-heap and heapsort

### Floyd's (1964) $O(n)$ build-heap

Consider the problem of taking an array of $n$ elements and turning it into a heap. The simplest approach is to **`Push` elements one by one**.

```csharp
var heap = new MinHeap<int>();
foreach (int x in array) heap.Push(x);   // O(n log n)
```

Each `Push` costs $O(\log n)$, so the total is $O(n \log n)$. Same as sorting.

But Robert Floyd's surprising 1964 discovery: **turning an already-populated array into a heap can be done in $O(n)$.**

The algorithm is simple — **apply sift-down to each non-leaf node from back to front, starting from the last non-leaf**.

```csharp
public static void BuildHeap<T>(T[] arr) where T : IComparable<T> {
    // Index of the last non-leaf is n/2 - 1
    for (int i = arr.Length / 2 - 1; i >= 0; i--)
        SiftDown(arr, i, arr.Length);
}
```

**Why is it $O(n)$?** The key is the asymmetry: **"deeper nodes are numerous but their sift-down distance is short."**

At height $h$, there are at most $\lceil n / 2^{h+1} \rceil$ nodes, and each sift-down can descend at most $h$ levels. The total cost is:

$$T(n) = \sum_{h=0}^{\lfloor \log_2 n \rfloor} \left\lceil \frac{n}{2^{h+1}} \right\rceil \cdot O(h) = O\left(n \sum_{h=0}^{\infty} \frac{h}{2^h}\right)$$

And since the infinite series $\sum_{h=0}^{\infty} h / 2^h = 2$ converges to a constant:

$$T(n) = O(2n) = O(n)$$

Intuitive picture: **half** of the tree consists of leaves (no movement), **1/4** at height 1 (moves one step), **1/8** at height 2 (moves two steps)… The dominant contributors are the many leaves, and they do almost no work.

> **Wait, let's clarify this**
>
> **Q. Why do we build the heap with sift-down instead of sift-up?**
>
> Building the heap with sift-up gives $O(n \log n)$. **Sift-up "climbs to the parent"**, and nodes near the leaves — which are the most numerous — have to climb all the way up to the root, $\log n$ steps. Conversely, **sift-down "descends to children"**: nodes near the root are few but go $\log n$ down, while nodes near the leaves are many but hardly move. The product of node count and travel distance stays linear.
>
> **Q. Then should we always use build-heap instead of `Push`ing $n$ times?**
>
> If the array is **prepared in advance**, yes. But with **streaming input** (elements arrive one at a time), you can't use build-heap, so you have to accept the $O(n \log n)$ from `Push`.

### Heapsort — Sorting with a Heap

Once you understand build-heap, sorting comes for free. Williams (1964) published this idea.

1. **build-heap** turns the array into a **max-heap** — $O(n)$
2. Swap the root (maximum) with **the last array element**
3. Sift-down excluding the last position — $O(\log n)$
4. Repeat, and the array is sorted in ascending order

```csharp
public static void HeapSort<T>(T[] arr) where T : IComparable<T> {
    int n = arr.Length;

    // 1. Build a max-heap — O(n)
    for (int i = n / 2 - 1; i >= 0; i--)
        SiftDownMax(arr, i, n);

    // 2. Swap root with end, then shrink — O(n log n)
    for (int end = n - 1; end > 0; end--) {
        (arr[0], arr[end]) = (arr[end], arr[0]);
        SiftDownMax(arr, 0, end);
    }
}
```

- **Time complexity:** best/average/worst all $O(n \log n)$
- **Space complexity:** $O(1)$ — in-place sort
- **Stability:** **unstable** — swaps scramble the order of equal keys

### Why It Lost to Quicksort

Theoretically, heapsort's worst case is better (quicksort's worst is $O(n^2)$). Yet quicksort variants dominate in practice. Reasons:

1. **Cache locality is bad** — sift-down jumps from `i` to `2i+1` or `2i+2`, **doubling the index**. For large arrays, these accesses leave the cache line frequently.
2. **More comparisons and swaps** — each sift-down step compares two children. Quicksort/mergesort move roughly once per comparison.
3. **Branch prediction** friendliness is lower.

Choices by modern standard libraries:

| Language / Standard | Sort algorithm |
| --- | --- |
| C# `Array.Sort` | Introsort (quicksort + heapsort fallback) |
| C++ `std::sort` | Introsort |
| Python `sorted` | **Timsort** (merge + insertion, stable) |
| Java `Arrays.sort` (primitives) | Dual-pivot quicksort |
| Java `Arrays.sort` (objects) | Timsort |
| Rust `slice::sort` | Timsort variant (stable) |

**Introsort** (Musser 1997) runs as quicksort normally, but switches to heapsort when recursion depth exceeds $2\log n$. Heapsort plays the role of **"safety net for when quicksort breaks down"** — a role familiar to game studios when "guaranteed behavior in bad cases" is needed.

---

## Part 5: Heap Variants — When Not Binary

If you know binary heaps, you've solved 95% of practical problems. Still, let's look at a few variants for the remaining 5%.

### d-ary Heap

A heap where **each node has $d$ children**. The parent/child index formulas become:

$$\text{parent}(i) = \left\lfloor \frac{i-1}{d} \right\rfloor, \quad \text{child}_k(i) = di + k + 1 \ (k = 0, 1, ..., d-1)$$

The tree height drops to $\log_d n$, but each sift-down must compare $d$ children.

| Operation | Binary ($d=2$) | 4-ary | 8-ary |
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

  <text class="hp-dary-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">Binary vs 4-ary Heap (16 nodes)</text>

  <text class="hp-dary-label" x="190" y="52" text-anchor="middle" font-size="13" font-weight="700">Binary (d=2)</text>
  <text class="hp-dary-sub" x="190" y="68" text-anchor="middle" font-size="11">height 4, sift-down comparisons 2×log₂16 = 8</text>

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

  <line class="hp-dary-div" x1="395" y1="50" x2="395" y2="240" stroke-dasharray="4,4"/>

  <text class="hp-dary-label" x="590" y="52" text-anchor="middle" font-size="13" font-weight="700">4-ary (d=4)</text>
  <text class="hp-dary-sub" x="590" y="68" text-anchor="middle" font-size="11">height 2, sift-down comparisons 4×log₄16 = 8</text>

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

  <text class="hp-dary-note" x="190" y="240" text-anchor="middle" font-size="10.5">deeper tree, 2 child comparisons</text>
  <text class="hp-dary-note" x="590" y="240" text-anchor="middle" font-size="10.5">shallower tree, 4 child comparisons — all children in one cache line</text>
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

Interesting observation: **theoretical comparison counts for $d=2$ and $d=4$ are essentially equal** ($2\log_2 n$). Yet LaMarca & Ladner's (1996) experiments show that **4-ary heaps are actually faster than binary heaps** — the reason is cache.

- In a binary heap, a parent's two children are at `2i+1`, `2i+2` — adjacent
- But going from grandparent to grandchild requires two jumps
- A 4-ary heap's four children are at `4i+1, 4i+2, 4i+3, 4i+4` — all within one cache line

**When 4-ary or 8-ary beats binary in practice:**
- When keys are small (all children fit in one cache line)
- When sift-downs vastly outnumber sift-ups (extract-min-heavy workloads)
- Example: large-scale Dijkstra/A*

### Pairing Heap and Fibonacci Heap

Heaps that offer $O(1)$ **amortized decrease-key**. They improve Dijkstra's theoretical complexity to $O(E + V \log V)$ (vs $O((V+E) \log V)$ for binary heap).

| Heap | insert | extract-min | decrease-key | Structure |
| --- | --- | --- | --- | --- |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | array |
| **4-ary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | array |
| **Pairing Heap** | $O(1)$ | $O(\log n)$* | $O(\log n)$* | pointer tree |
| **Fibonacci Heap** | $O(1)$ | $O(\log n)$* | $O(1)$* | pointer tree |

*amortized

**Fibonacci heap** (Fredman & Tarjan 1987) is rarely used in practice despite its theoretical superiority:

1. **Large constants** — even $O(1)$ amortized, the constant factor is large. Binary heap's $O(\log n)$ beats it almost always except when "the graph is huge and decrease-keys are frequent"
2. **Complex implementation** — many things to manage: parent pointers, child lists, mark bits, rank, cascading cuts
3. **Cache disaster** — pointer-based structures wander the heap area, same issue as linked lists from Part 1
4. **decrease-key itself is rare** — in A*, it can be avoided with lazy deletion

**Pairing heap** (Fredman, Sedgewick, Sleator, Tarjan 1986) is a simplified version of Fibonacci. Its theoretical guarantees are slightly weaker but its constants are smaller, so measured performance often beats Fibonacci. High-performance libraries like Boost and LEDA offer it as an option.

> **Wait, let's clarify this**
>
> **Q. Is Fibonacci heap always faster for Dijkstra?**
>
> **No.** Chen et al. (2007) and numerous empirical studies have repeatedly shown that **on real datasets, binary heaps or 4-ary heaps outperform Fibonacci heaps**. Only in extreme cases where $E \gg V$ (dense graphs near $O(V^2)$) does Fibonacci show meaningful benefits.
>
> **Q. So when is a Fibonacci heap actually used?**
>
> Almost never in practice. It mostly plays the role of an "existence proof" for theoretical analysis. You'll see it in research papers, algorithm textbooks, and specific cases where amortized analysis is needed.

---

## Part 6: Heaps in Game Development

### A* open set — The decrease-key Problem

Let's revisit the A* code from [Part 5 on Graphs](/posts/Graph/):

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

The problem: what if the same node `next` is **already in the open set, but we want to add it with a smaller f-value?**

The textbook answer is **decrease-key** — find the node in the open set and lower its priority. But this is $O(n)$ in a binary heap (you have to find the element). Tracking node positions in a separate `Dictionary` makes it $O(\log n)$.

The practical answer is simpler: **lazy deletion**.

```csharp
// lazy deletion pattern
while (openSet.Count > 0) {
    var (current, f) = openSet.Dequeue();

    if (f > gScore[current]) continue;  // stale entry — a better value already exists

    if (current == goal) return ReconstructPath(...);

    foreach (var next in GetNeighbors(current)) {
        float tentativeG = gScore[current] + Cost(current, next);
        if (tentativeG < gScore.GetValueOrDefault(next, float.MaxValue)) {
            gScore[next] = tentativeG;
            openSet.Enqueue(next, tentativeG + Heuristic(next, goal));
            // leave the previous stale entry alone — check when popping
        }
    }
}
```

- Pushing the same node multiple times is fine
- On pop, check `f > gScore[current]` to detect "no longer valid"
- Simple implementation, a binary heap alone is enough
- Uses a bit more memory, but mostly negligible

Most practical libraries — Unity's A* Pathfinding Project, Recast/Detour, etc. — use this pattern.

### Event / Timer Scheduler

In a game server or editor tooling, when you need to process **"execute this task at time $t$"** at scale, a heap is a good fit.

```csharp
// Simple timer queue — keeps (time, task) pairs ordered by time ascending
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

This pattern shows up in game engine animation events, cooldowns, and buff/debuff expiration handling. A naive list-and-scan approach grows linearly with event count; a heap only pops "what's actually expiring now."

Note: **`heap.Peek()` is also $O(1)$**, so you can cheaply query "when is the next event?" Useful for configuring sleep timers.

### AI Action Scores

In utility AI, when you want to consider **only the top N highest-scoring actions**, a **fixed-size-$k$ min-heap** does the job.

```csharp
// Keep the top k actions
public class TopKActions {
    private readonly MinHeap<(float score, Action action)> heap = new();
    private readonly int k;

    public TopKActions(int k) { this.k = k; }

    public void Consider(float score, Action action) {
        if (heap.Count < k) {
            heap.Push((score, action));
        } else if (score > heap.Peek().score) {
            heap.Pop();                    // remove the lowest-scoring
            heap.Push((score, action));
        }
    }

    public IEnumerable<Action> GetTopK() =>
        heap.ToArray().OrderByDescending(x => x.score).Select(x => x.action);
}
```

The point is using a **min**-heap. For a size-$k$ top-k problem, the min-heap's root is **"the lowest among the current k."** When a new candidate beats it, swap. This technique is broadly used for general top-k problems.

### Unity NativeContainer Perspective

Unfortunately, Unity doesn't ship a built-in `NativeHeap`. You have to **implement one yourself** using the patterns from [JobSystem Part 4: NativeContainer Deep Dive](/posts/NativeContainerDeepDive/).

Key considerations:
- Use `NativeList<T>` as the underlying storage (array-based, pairs well with a heap)
- The `[NativeContainer]` attribute and `AtomicSafetyHandle` integration — tie into the Safety System
- Burst compatibility: consider passing a `struct IComparer<T>` instead of generic `IComparable`
- Parallel insert is hard — sift-up races toward the root, so locking is needed. A common pattern is **collect into a queue, then pour in single-threaded**

In practice, official/community examples like Unity's BurstAStarGridExample, or public implementations like Gilzu's `NativeMinHeap`, are faster to reach for.

---

## Part 7: Analyzing .NET's `PriorityQueue<TElement, TPriority>`

From .NET 6, `System.Collections.Generic.PriorityQueue<TElement, TPriority>` became the official standard. Internally, it's a **4-ary min-heap** — chosen over binary for the reasons we just discussed.

```csharp
var pq = new PriorityQueue<string, int>();
pq.Enqueue("task-a", 3);
pq.Enqueue("task-b", 1);       // lower priority number = earlier pop
pq.Enqueue("task-c", 2);

while (pq.Count > 0) {
    string task = pq.Dequeue();
    // pops in order: task-b, task-c, task-a
}
```

Key features of the official implementation:

- **TElement and TPriority are separate** — the stored value and the sort key are decoupled (better ergonomics)
- **4-ary heap** — confirmed by `const int Arity = 4` in the `dotnet/runtime` source
- **`EnqueueDequeue`** — optimized push-then-pop (useful for top-k patterns)
- **`UnorderedItems`** — enumerates the heap in storage order, not sorted order
- **No `Dictionary<TElement, ...>`** — does not provide decrease-key. Use lazy deletion

**Caveats:**
- **Not thread-safe** — external locking is required for multi-threaded use
- **Duplicate keys allowed** — multiple Enqueues with the same priority yield non-deterministic order (unstable)
- If you need **stable sort**, make priority a tuple: `(originalPriority, tieBreaker)`

For a simple A* open set, `PriorityQueue<Vector2Int, float>` is a one-liner. Reasons left to roll your own: (1) custom comparer, (2) special allocation patterns, (3) Burst / Job System integration.

---

## Closing Thoughts

### Core Summary

1. **A priority queue is the partial problem "only min/max matters"** — a full sort is overkill; partial order yields $O(\log n)$
2. **A binary heap is a complete binary tree mapped to an array** — zero pointers, navigate parents/children with index arithmetic
3. **sift-up and sift-down are everything** — push, pop, every variant operation is a combination of these two
4. **Floyd's $O(n)$ build-heap** — follows from the asymmetry of "many deep nodes, shallow moves"
5. **4-ary heaps beat binary heaps in practice** — the layout advantage of clustering children in a cache line
6. **Fibonacci heaps are theoretical** — beaten by binary/4-ary in measurements, only implementation complexity is high
7. **A* decrease-key is sidestepped by lazy deletion** — check staleness on pop, allow duplicates on push
8. **.NET `PriorityQueue<TElement, TPriority>` is a 4-ary heap** — not many reasons to roll your own

### What Layer of Insight Is This

The proposition from Part 1 — **"cache can matter more than complexity"** — resurfaces here. Fibonacci heap's theoretical $O(1)$ decrease-key loses to binary heap in practice because we underestimated the constants between theory and reality.

And heaps are an example of **"a weaker structure than BST being stronger for specific problems."** You pay only for partial order, and in return you get free array mapping. In data structure design, **"how little can we promise"** actually expands your design freedom — heap over BST, top-k over full sort. Many CS ideas flow in this direction.

With this bonus, the remaining debts around Phase 1 (Data Structures and Memory) are cleared. From here, we return to the original plan: **Phase 2 — OS and Concurrency.** Processes, threads, locks, and the many disasters that appear on multi-core systems.

---

## References

**Primary sources and key papers**
- Williams, J.W.J., "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), pp. 347–348 (1964) — **the original binary heap paper**
- Floyd, R.W., "Algorithm 245: Treesort 3", *Communications of the ACM* 7(12), p. 701 (1964) — **$O(n)$ build-heap**
- Johnson, D.B., "Priority queues with update and finding minimum spanning trees", *Information Processing Letters* 4(3), pp. 53–57 (1975) — **d-ary heap**
- Fredman, M.L., Sedgewick, R., Sleator, D.D., Tarjan, R.E., "The pairing heap: A new form of self-adjusting heap", *Algorithmica* 1(1), pp. 111–129 (1986)
- Fredman, M.L. & Tarjan, R.E., "Fibonacci heaps and their uses in improved network optimization algorithms", *Journal of the ACM* 34(3), pp. 596–615 (1987)
- LaMarca, A. & Ladner, R.E., "The influence of caches on the performance of heaps", *ACM Journal of Experimental Algorithmics* 1, Article 4 (1996) — **empirical evidence that 4-ary beats binary**
- Dutton, R.D., "Weak-heap sort", *BIT Numerical Mathematics* 33(3), pp. 372–381 (1993)
- Brodal, G.S., "Worst-case efficient priority queues", *Proceedings of SODA* (1996)
- Chen, M., Chowdhury, R.A., Ramachandran, V., Roche, D.L., Tong, L., "Priority Queues and Dijkstra's Algorithm", UT Austin Technical Report TR-07-54 (2007) — **empirical Fibonacci vs binary comparison**

**Textbooks**
- Cormen, T.H., Leiserson, C.E., Rivest, R.L., Stein, C., *Introduction to Algorithms (CLRS)*, 4th Edition, MIT Press — Chapter 6 (Heapsort), Chapter 19 (Fibonacci Heaps)
- Sedgewick, R. & Wayne, K., *Algorithms*, 4th Edition, Addison-Wesley — Chapter 2.4 Priority Queues
- Knuth, D., *The Art of Computer Programming Vol. 3: Sorting and Searching*, 2nd Edition, Addison-Wesley — Section 5.2.3 Sorting by Selection (heapsort)
- Weiss, M.A., *Data Structures and Algorithm Analysis in C++*, 4th Edition, Pearson — Chapter 6 Priority Queues

**Implementation references**
- .NET `PriorityQueue<TElement, TPriority>` — [dotnet/runtime source](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Collections/src/System/Collections/Generic/PriorityQueue.cs): official 4-ary min-heap implementation
- C++ `std::priority_queue` — libstdc++, libc++: binary heap based
- Java `java.util.PriorityQueue` — OpenJDK: binary heap based
- Python `heapq` — [CPython source](https://github.com/python/cpython/blob/main/Lib/heapq.py): binary min-heap, priority encoded via tuples
- Boost Heap — [boost.org/libs/heap](https://www.boost.org/doc/libs/release/libs/heap/): offers binary, d-ary, pairing, Fibonacci, skew heap

**Game development context**
- Millington, I. & Funge, J., *Artificial Intelligence for Games*, 3rd Edition, CRC Press — A*, open set management
- Recast & Detour — [github.com/recastnavigation](https://github.com/recastnavigation/recastnavigation): heap usage in a production NavMesh library
- A* Pathfinding Project (Unity) — [arongranberg.com/astar](https://arongranberg.com/astar/): lazy-deletion-based open set
