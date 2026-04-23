---
title: "CSロードマップ (番外編) — ヒープと優先度キュー：部分順序の経済学"
lang: ja
date: 2026-04-24 10:00:00 +0900
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
  - "優先度キューは「最小値・最大値だけを素早く」取得したい問題であり、完全ソート（O(n log n)）は過剰スペックだ。ヒープは「部分順序」だけを維持してO(log n)のpush/popを達成する"
  - "二分ヒープは完全二分木を配列で表現した魔法である — ポインタなしで parent = (i-1)/2, left = 2i+1 というインデックス演算だけで木を行き来する"
  - "Floyd(1964)のbottom-up build-heapはO(n)で完成する。直感に反してO(n log n)ではない — 深いレベルのノードが多く、浅いsift-downしか行わないためだ"
  - "A*のopen setにおけるdecrease-keyは、実務ではlazy deletion（stale entryを取り出すときに無視する）で解決する。Fibonacci heapのO(1) decrease-keyは定数オーバーヘッドのため、グリッドA*ではむしろ損になる"
---

## 序論

> この文書は **CSロードマップ** シリーズの番外編（bonus）です。

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

[第5回 グラフ](/posts/Graph/)でDijkstraとA*を扱いながら、一文を残した：*「優先度キュー（二分ヒープ）を使えば$O((V+E) \log V)$」*。ところが、その「二分ヒープ」が何なのか、なぜ二分なのか、どのように$O(\log n)$を達成するのかは後回しにした。この番外編はその負債を返す。

第1段階（データ構造とメモリ）が全6回で締めくくられた後、ヒープと優先度キューは「抜け落ちた核心の一片」として残っていた。木の応用であり配列の演算であり、A*のエンジンでありイベントスケジューラの心臓だ。小さなテーマだが、ゲーム開発において頻繁に登場するため見過ごすには惜しい。

この記事で扱う内容：

1. なぜ完全ソートではなく「部分順序」で十分なのか
2. 二分ヒープが配列の上で動作する原理
3. sift-up / sift-downの数学的根拠とC#実装
4. Floyd(1964)の$O(n)$ build-heap
5. d-ary heap、Pairing heap、Fibonacci heap — いつどれを使うか
6. A* open setのdecrease-key問題と実務的な解決法
7. .NET `PriorityQueue<TElement, TPriority>`の分析

---

## Part 1: 優先度キュー問題

### 「最小値だけを素早く」 — 完全ソートは過剰だ

次の問題を考えてみよう。

> 整数が1,000,000個ある。そのうち最も小さい値を1,000個だけ順に取り出したい。

直感的に思いつく解法は**全体をソートした後、先頭から1,000個を取る**ことだ。$O(n \log n)$で全体をソートしたので、出力は$O(k)$。しかしよく考えると無駄が多い。後ろの99万9千個の順序は使っていない。**必要なのは「最小値の取り出し」と「挿入」という2つの操作だけである。**

これが**優先度キュー（Priority Queue）**問題だ。キュー（FIFO）のように「入れて出す」インターフェースを持つが、出る順番は「先に入ったもの」ではなく**「優先度が最も高いもの」**だ。

```
通常のキュー (FIFO):            優先度キュー:

  [4, 7, 1, 9, 3]                [4, 7, 1, 9, 3]
   ↓ dequeue                      ↓ extract-min
   4 (投入順)                     1 (最小値)
```

ゲームでこの問題が現れる瞬間：

- **A* / Dijkstra**：「f値が最も小さいノードを取り出す」
- **イベントスケジューラ**：「実行時刻が最も早いイベントを取り出す」
- **AI行動選択**：「今最も有用な行動のスコアを取り出す」
- **DSP / オーディオミキシング**：「最も重要なサウンドチャンネルN個だけを再生する」

### 素朴な実装のトレードオフ

優先度キューを**「なぜ配列やBSTで実装してはいけないのか」**を先に押さえておくと、ヒープの価値が見えてくる。

| 構造 | insert | extract-min | 備考 |
| --- | --- | --- | --- |
| **Unsorted Array** | $O(1)$ | $O(n)$ | 末尾に追加、取り出し時に全体スキャン |
| **Sorted Array** | $O(n)$ | $O(1)$ | 二分探索で位置を特定しても移動コスト$O(n)$ |
| **Sorted LinkedList** | $O(n)$ | $O(1)$ | 探索が線形、移動はないが |
| **BST (balanced)** | $O(\log n)$ | $O(\log n)$ | ポインタ4〜5個/ノード、キャッシュミス |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | **配列で実装、ポインタ0個** |

表を見ると「ヒープがBSTと計算量は同じなのに、なぜ優れているのか？」という疑問が自然に湧く。答えは**定数とキャッシュ**にある — 第1回で扱ったあの話がここでも繰り返される。

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

  <text class="hp-cmp-title" x="390" y="28" text-anchor="middle" font-weight="700" font-size="16">優先度キュー実装別の性能比較</text>

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

  <text class="hp-cmp-memtitle" x="107" y="180" text-anchor="middle" font-size="11" font-weight="600">メモリ/ノード</text>
  <text class="hp-cmp-mem" x="107" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="302" y="180" text-anchor="middle" font-size="11" font-weight="600">メモリ/ノード</text>
  <text class="hp-cmp-mem" x="302" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>
  <text class="hp-cmp-memtitle" x="497" y="180" text-anchor="middle" font-size="11" font-weight="600">メモリ/ノード</text>
  <text class="hp-cmp-mem hp-cmp-memwarn" x="497" y="198" text-anchor="middle" font-size="13" font-weight="700">4〜5 words</text>
  <text class="hp-cmp-memtitle" x="682" y="180" text-anchor="middle" font-size="11" font-weight="600">メモリ/ノード</text>
  <text class="hp-cmp-mem" x="682" y="198" text-anchor="middle" font-size="13" font-weight="700">1 word</text>

  <text class="hp-cmp-memtitle" x="107" y="224" text-anchor="middle" font-size="11" font-weight="600">キャッシュ親和性</text>
  <text class="hp-cmp-good" x="107" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 連続</text>
  <text class="hp-cmp-memtitle" x="302" y="224" text-anchor="middle" font-size="11" font-weight="600">キャッシュ親和性</text>
  <text class="hp-cmp-good" x="302" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 連続</text>
  <text class="hp-cmp-memtitle" x="497" y="224" text-anchor="middle" font-size="11" font-weight="600">キャッシュ親和性</text>
  <text class="hp-cmp-bad" x="497" y="242" text-anchor="middle" font-size="13" font-weight="700">✗ ポインタ追跡</text>
  <text class="hp-cmp-memtitle" x="682" y="224" text-anchor="middle" font-size="11" font-weight="600">キャッシュ親和性</text>
  <text class="hp-cmp-good" x="682" y="242" text-anchor="middle" font-size="13" font-weight="700">✓ 連続</text>

  <text class="hp-cmp-weak" x="107" y="268" text-anchor="middle" font-size="11.5" font-style="italic">insert時O(n)移動</text>
  <text class="hp-cmp-weak" x="302" y="268" text-anchor="middle" font-size="11.5" font-style="italic">スキャン反復</text>
  <text class="hp-cmp-weak" x="497" y="268" text-anchor="middle" font-size="11.5" font-style="italic">キャッシュミス + メモリ</text>
  <text class="hp-cmp-strong" x="682" y="268" text-anchor="middle" font-size="11.5" font-weight="700">バランスの取れた最適解</text>
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

### ヒープの核心アイデア：部分順序で十分である

優先度キュー問題の核心的洞察はこれだ。

> **毎回最小値を一つだけ取り出す。残りの要素の相対順序は気にしない。**

完全ソートは「すべてのペアについて$a < b$または$a > b$」を決定する。しかし最小値の取り出しは**「ルートが全体の最小である」**というはるかに弱い条件だけで十分だ。この「弱さ」が$O(\log n)$の余地を作る。

**ヒープの約束（min-heap）：**
- ルートは全体の最小値である
- 親は2つの子より**小さいか等しい**（兄弟同士は順序不問）

これを**ヒープ特性（heap property）**と呼ぶ。BSTの「左 < 親 < 右」とは異なり、ヒープは**親子関係のみ**を強制し、兄弟やサブツリー間の順序は任意に任せる。この「緩さ」が高速な挿入・削除の秘訣だ。

---

## Part 2: 二分ヒープの構造

### 完全二分木

[第4回 ツリー](/posts/Tree/)で**完全二分木（complete binary tree）**を定義した：「最後のレベルを除くすべてのレベルが完全に埋まっており、最後のレベルは左から詰められた木」。二分ヒープは**必ず**完全二分木でなければならない。

```
         1
       /   \
      3     2
     / \   / \
    7   5 4   8
   / \
  9  10

高さ = ⌊log₂(n)⌋ = ⌊log₂(8)⌋ = 3
最後のレベルは左から詰められている
```

なぜ**完全**でなければならないのか？理由は2つある。

1. **高さが常に$\lfloor \log_2 n \rfloor$に保たれる** — sift-up/downが$O(\log n)$であることを保証
2. **配列で表現可能** — 空きスロットがないため配列にぎっしり詰められる

2番目がこのデータ構造の魔法だ。

### 配列で表現された木 — ポインタのない木

完全二分木のノードをレベル順（上から下、左から右）に配列に格納すると、**親子関係がインデックス演算で表現される**。

0-basedインデックス基準：

$$\text{parent}(i) = \left\lfloor \frac{i-1}{2} \right\rfloor, \quad \text{left}(i) = 2i+1, \quad \text{right}(i) = 2i+2$$

1-basedで書くともっと綺麗だ（Williamsの原論文はこの形式を使った）：

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

  <text class="hp-map-title" x="390" y="26" text-anchor="middle" font-weight="700" font-size="16">配列 ↔ 完全二分木：インデックスマッピング</text>

  <text class="hp-map-section" x="390" y="58" text-anchor="middle" font-size="13" font-weight="600">完全二分木 (min-heap)</text>

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

  <text class="hp-map-section" x="390" y="378" text-anchor="middle" font-size="13" font-weight="600">配列表現（メモリ連続）</text>

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
  <text class="hp-map-ftitle" x="680" y="358" text-anchor="middle" font-size="11" font-weight="700">インデックス演算</text>
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

**なぜこれが強力なのか？**

1. **メモリ連続** — ツリー全体が一つの配列。プリフェッチャが次のノードを先取りしてくる
2. **ポインタ0個** — ノードあたりvalue一つだけ。ノードあたり4〜5ワードを使うBSTよりメモリ密度が圧倒的
3. **キャッシュラインの効率** — 64バイトキャッシュラインに`int`基準で16要素が入る。上位レベルのいくつかがL1に常駐する

第1回の配列と連結リストで**「配列は連続したメモリにデータを格納してキャッシュ局所性の恩恵を最大限に受ける」**と述べた。ヒープはこの原理を木に移植したデータ構造だ。

> **ちょっと、これは押さえておこう**
>
> **Q. 1-basedインデックスの方が数式は綺麗なのに、なぜ実務では0-basedを使うのか？**
>
> 言語の配列が0-basedだからだ。`array[0]`を空けて1番から使うとメモリが1個無駄になる上に混乱が増す。ほとんどの実装（C++ `std::priority_queue`, .NET `PriorityQueue`）は0-basedを使う。数式が少し綺麗でないだけで動作は同じだ。
>
> **Q. 完全二分木でなくてもよいのでは？二分探索木のように自由に作れば？**
>
> 完全性が壊れると配列表現ができなくなる — 「空き」を表現する必要があるので配列にsentinelやポインタが必要になり、これはBSTへの後退だ。また片側に偏ると高さが$O(n)$になって操作が遅くなる。**「配列に隙間なく」**がヒープのアイデンティティだ。

---

## Part 3: 核心操作 — sift-upとsift-down

ヒープでヒープ特性を維持する2つの基本操作だ。挿入と削除がどちらもこの2つに帰着する。

### sift-up (percolate up) — 挿入

新しい要素を入れるときの戦略：

1. **配列の末尾**に新しい要素を追加（完全性の維持）
2. 親と比較、小さければ**交換**
3. ヒープ特性が回復するまで繰り返す（またはルートに到達）

```
挿入 1：               段階1: 親と比較        段階2: 回復完了
                      [1]                    [1]
     [1]                / \                   / \
    /   \              [3] [2]               [3] [2]
   [3]  [2]            / \ / \               / \ / \
   /\   /\            [7][5][4][8]          [7][5][4][8]
  [7][5][4][8]        / \                    / \
                     [9][1] ← 新要素          [1][9]  ← 1と5を比較 → 交換
```

ちょっと、上の例は少し単純化しすぎた。実際に1をインデックス9に入れると：

```
初期:       [1, 3, 2, 7, 5, 4, 8, 9]
1を追加:   [1, 3, 2, 7, 5, 4, 8, 9, 1]  ← インデックス 8

sift-up:
  i=8, parent(8)=3, heap[3]=7 > 1 → 交換
    [1, 3, 2, 1, 5, 4, 8, 9, 7]
  i=3, parent(3)=1, heap[1]=3 > 1 → 交換
    [1, 1, 2, 3, 5, 4, 8, 9, 7]
  i=1, parent(1)=0, heap[0]=1 ≤ 1 → 停止
```

C#実装：

```csharp
void SiftUp(int i) {
    while (i > 0) {
        int parent = (i - 1) / 2;
        if (heap[i].CompareTo(heap[parent]) >= 0)
            break;                        // ヒープ特性を満たす
        (heap[i], heap[parent]) = (heap[parent], heap[i]);
        i = parent;
    }
}

public void Push(T value) {
    heap.Add(value);
    SiftUp(heap.Count - 1);
}
```

**計算量：** 最悪の場合ルートまで登るので$O(\log n)$。木の高さが$\lfloor \log_2 n \rfloor$に固定されているためだ。

### sift-down (percolate down) — 削除 / 最小値取り出し

ルートを取り出す操作。少し厄介だ。

1. ルート（最小値）を**戻り値として保存**
2. **配列の最後の要素**をルート位置に移動
3. 配列長を1減らす（末尾は捨てる）
4. ルートから**2つの子のうち小さい方**と比較、大きければ交換
5. ヒープ特性が回復するまで繰り返す（またはリーフに到達）

ポイントは4番 — **親は2つの子より小さくなければならないので、2つの子のうち「小さい方」と交換しなければならない。** 大きい方と交換するとその子が兄弟より大きくなって特性が壊れる。

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

  <text class="hp-down-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">sift-down：ルートを削除してヒープを復元</text>

  <text class="hp-down-step" x="130" y="58" text-anchor="middle" font-size="12" font-weight="700">① 末尾をルートへ</text>
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
  <text class="hp-down-note" x="130" y="232" text-anchor="middle" font-size="10">ルートが9で崩れた</text>
  <text class="hp-down-note" x="130" y="246" text-anchor="middle" font-size="10">(9 &gt; 3, 9 &gt; 2)</text>

  <line class="hp-down-flow" x1="230" y1="150" x2="275" y2="150" marker-end="url(#hp-down-arr)"/>

  <text class="hp-down-step" x="390" y="58" text-anchor="middle" font-size="12" font-weight="700">② 小さい子(2)と交換</text>
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
  <text class="hp-down-note" x="390" y="232" text-anchor="middle" font-size="10">ルートはOK、9 &gt; 4</text>
  <text class="hp-down-note" x="390" y="246" text-anchor="middle" font-size="10">さらに降りる</text>

  <line class="hp-down-flow" x1="490" y1="150" x2="535" y2="150" marker-end="url(#hp-down-arr)"/>

  <text class="hp-down-step" x="650" y="58" text-anchor="middle" font-size="12" font-weight="700">③ 4と交換 → 完了</text>
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
  <text class="hp-down-note hp-down-good" x="650" y="232" text-anchor="middle" font-size="10" font-weight="700">ヒープ復元完了</text>
  <text class="hp-down-note" x="650" y="246" text-anchor="middle" font-size="10">移動回数 = 木の高さ = O(log n)</text>

  <g transform="translate(60, 290)">
    <text class="hp-down-arrtitle" x="330" y="15" text-anchor="middle" font-size="12" font-weight="600">配列変化の追跡</text>
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

C#実装：

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

        if (smallest == i) break;   // ヒープ特性を満たす

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
    return heap[0];      // ルートだけ見る、O(1)
}
```

**計算量：** 同じく$O(\log n)$。ただし注意すべき点は、**sift-downの比較回数はsift-upのおよそ2倍**であることだ — 各レベルで2つの子と比較し、小さい方を選ぶ必要があるからだ。この細部が後に「なぜFloyd build-heapが$O(n)$なのか」に影響する。

### 完全なmin-heapクラス（参考）

上記2つの操作を組み合わせたジェネリックmin-heapだ。

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

## Part 4: build-heapとheapsort

### Floyd(1964)の$O(n)$ build-heap

$n$個の配列を受け取りヒープに変える問題を考えよう。最も単純な方法は**要素を一つずつ`Push`する**ことだ。

```csharp
var heap = new MinHeap<int>();
foreach (int x in array) heap.Push(x);   // O(n log n)
```

この場合、各`Push`が$O(\log n)$なので全体は$O(n \log n)$。ソートと同じ計算量だ。

しかしRobert Floydが1964年に発見した驚くべき事実：**既に埋まっている配列をヒープに変えることは$O(n)$で可能だ。**

アルゴリズムは単純だ — **配列の最後の非リーフノードから後ろから前へsift-down**を適用する。

```csharp
public static void BuildHeap<T>(T[] arr) where T : IComparable<T> {
    // 最後の非リーフのインデックスは n/2 - 1
    for (int i = arr.Length / 2 - 1; i >= 0; i--)
        SiftDown(arr, i, arr.Length);
}
```

**なぜ$O(n)$なのか？** 核心は**「深いノードが多いが、sift-downの距離は短い」**という非対称性だ。

高さ$h$でのノード数は最大$\lceil n / 2^{h+1} \rceil$個であり、各ノードでsift-downは最大$h$だけ降りる。総コストは：

$$T(n) = \sum_{h=0}^{\lfloor \log_2 n \rfloor} \left\lceil \frac{n}{2^{h+1}} \right\rceil \cdot O(h) = O\left(n \sum_{h=0}^{\infty} \frac{h}{2^h}\right)$$

そして無限級数$\sum_{h=0}^{\infty} h / 2^h = 2$が定数に収束するので：

$$T(n) = O(2n) = O(n)$$

直感的な絵：木の**半分**がリーフ（移動しない）、**1/4**が高さ1（1段移動）、**1/8**が高さ2（2段移動）… 支配的なのは多数のリーフたちで、彼らはほとんど仕事をしない。

> **ちょっと、これは押さえておこう**
>
> **Q. なぜsift-upではなくsift-downでbuild-heapをするのか？**
>
> sift-upでbuild-heapをすると$O(n \log n)$になる。**sift-upは「親に登る」操作**であり、リーフ近くのノードが最も多いのにそれらがルートまで$\log n$登らなければならない。逆に**sift-downは「子に降りる」**操作で、ルート近くのノードは少ないが$\log n$降り、リーフ近くのノードは多いがほとんど動かない。ノード数と移動距離の積が線形になる構造だ。
>
> **Q. では`Push`を$n$回する代わりに常にbuild-heapを使う方がよいのか？**
>
> 配列が**事前に用意されている場合**はそうだ。しかし**ストリーミング入力**（要素が一つずつ到着する）ではbuild-heapを使えないので`Push`の$O(n \log n)$を受け入れなければならない。

### Heapsort — ヒープでソートする

build-heapを理解すればソートはおまけで付いてくる。Williams(1964)がこのアイデアを整理して発表した。

1. **build-heap**で配列を**max-heap**にする — $O(n)$
2. ルート（最大値）を**配列の末尾**と交換
3. 末尾位置を除いてsift-down — $O(\log n)$
4. 繰り返すと配列が昇順にソートされる

```csharp
public static void HeapSort<T>(T[] arr) where T : IComparable<T> {
    int n = arr.Length;

    // 1. max-heapのビルド — O(n)
    for (int i = n / 2 - 1; i >= 0; i--)
        SiftDownMax(arr, i, n);

    // 2. ルートと末尾を交換し縮小を繰り返す — O(n log n)
    for (int end = n - 1; end > 0; end--) {
        (arr[0], arr[end]) = (arr[end], arr[0]);
        SiftDownMax(arr, 0, end);
    }
}
```

- **時間計算量：** 最良/平均/最悪すべて$O(n \log n)$
- **空間計算量：** $O(1)$ — in-place（その場）ソート
- **安定性：** **不安定（unstable）** — 交換が同じキーの順序をかき乱す

### なぜQuicksortに敗れたのか

理論的な最悪計算量はheapsortの方が優れている（quicksortは$O(n^2)$最悪）。ところが実務ではquicksort系が支配的だ。理由：

1. **キャッシュ局所性**が悪い — sift-downが`i` → `2i+1`または`2i+2`と**インデックスを2倍にジャンプ**する。配列が大きいとキャッシュラインを外れるアクセスが頻発する。
2. **比較/交換回数が多い** — 各sift-downステップが子2つと比較する。Quicksort/Mergesortは比較あたり1回の移動に近い。
3. **分岐予測**の親和性が低い。

現代の標準ライブラリの選択：

| 言語 / 標準 | ソートアルゴリズム |
| --- | --- |
| C# `Array.Sort` | Introsort (quicksort + heapsort fallback) |
| C++ `std::sort` | Introsort |
| Python `sorted` | **Timsort** (merge + insertion, 安定) |
| Java `Arrays.sort` (primitives) | Dual-pivot quicksort |
| Java `Arrays.sort` (objects) | Timsort |
| Rust `slice::sort` | Timsort変形（安定） |

**Introsort**（Musser 1997）は普段はquicksort、深さが$2\log n$を超えるとheapsortに切り替える。ここでheapsortは**「quicksortが壊れたときの安全網」**の役割をする — ゲームスタジオでもよく「悪い状況での保証」が必要なときに使われるパターンだ。

---

## Part 5: ヒープの変種 — binaryではないとき

二分ヒープさえ知っていれば実務の95%は解決する。それでも残りの5%のためにいくつかの変種を見ていこう。

### d-ary Heap

**各ノードが$d$個の子**を持つヒープ。親/子のインデックス数式は：

$$\text{parent}(i) = \left\lfloor \frac{i-1}{d} \right\rfloor, \quad \text{child}_k(i) = di + k + 1 \ (k = 0, 1, ..., d-1)$$

木の高さが$\log_d n$に減る代わりに、各sift-downで$d$個の子と比較しなければならない。

| 操作 | Binary ($d=2$) | 4-ary | 8-ary |
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

  <text class="hp-dary-title" x="390" y="24" text-anchor="middle" font-weight="700" font-size="16">Binary vs 4-ary Heap（ノード16個の場合）</text>

  <text class="hp-dary-label" x="190" y="52" text-anchor="middle" font-size="13" font-weight="700">Binary (d=2)</text>
  <text class="hp-dary-sub" x="190" y="68" text-anchor="middle" font-size="11">高さ4、sift-down比較 2×log₂16 = 8</text>

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
  <text class="hp-dary-sub" x="590" y="68" text-anchor="middle" font-size="11">高さ2、sift-down比較 4×log₄16 = 8</text>

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

  <text class="hp-dary-note" x="190" y="240" text-anchor="middle" font-size="10.5">木が深いが子の比較は2回</text>
  <text class="hp-dary-note" x="590" y="240" text-anchor="middle" font-size="10.5">木が浅いが子の比較は4回 — キャッシュラインに子たちが集中</text>
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

興味深い点：**理論上の比較回数は$d=2$と$d=4$がほぼ同じだ**（$2\log_2 n$）。ところがLaMarca & Ladner(1996)の実験は**4-ary heapがbinary heapより実測で速い**ことを示した — 理由はキャッシュだ。

- Binary heapで一人の親の2つの子は`2i+1`, `2i+2` — 隣接
- しかし祖父母から孫に降りるには2回のジャンプが必要
- 4-ary heapは一人の親の4つの子が`4i+1, 4i+2, 4i+3, 4i+4` — キャッシュラインにすべて入る

**実務で4-aryまたは8-aryがbinaryより良い場合：**
- キーサイズが小さいとき（一つのキャッシュラインに子がすべて入る）
- sift-downがsift-upよりはるかに多いとき（extract-min中心のワークロード）
- 例：大規模Dijkstra/A*

### Pairing HeapとFibonacci Heap

$O(1)$ **amortized decrease-key**を提供するヒープたち。Dijkstraの理論的計算量を$O(E + V \log V)$に削減する（binary heapは$O((V+E) \log V)$）。

| ヒープ | insert | extract-min | decrease-key | 構造 |
| --- | --- | --- | --- | --- |
| **Binary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | 配列 |
| **4-ary Heap** | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | 配列 |
| **Pairing Heap** | $O(1)$ | $O(\log n)$* | $O(\log n)$* | ポインタツリー |
| **Fibonacci Heap** | $O(1)$ | $O(\log n)$* | $O(1)$* | ポインタツリー |

*amortized（償却）

**Fibonacci heap**（Fredman & Tarjan 1987）は理論的優位性にもかかわらず実務であまり使われない：

1. **定数が大きい** — $O(1)$であっても定数が大きく、$O(\log n)$のbinary heapを実際に上回るのは「非常に大きなグラフでdecrease-keyが多い」場合のみ
2. **実装が複雑** — 親ポインタ、子リスト、markビット、ランク、cascading cutなど管理項目が多い
3. **キャッシュの大惨事** — ポインタベースの構造なのでヒープ領域を歩き回る。第1回で見た連結リストの問題と同じだ
4. **decrease-key自体が稀** — A*ではlazy deletionで回避可能

**Pairing heap**（Fredman, Sedgewick, Sleator, Tarjan 1986）はFibonacciを単純化したバージョン。理論的保証は少し弱いが定数が小さく、実測性能はしばしばFibonacciより良い。Boost、LEDAのような高性能ライブラリで選択肢として提供される。

> **ちょっと、これは押さえておこう**
>
> **Q. DijkstraでFibonacci heapを使えば常に速いのか？**
>
> **いいえ。** Chen et al.(2007)や数々の実測研究は**実際のデータセットでbinary heapまたは4-ary heapがFibonacci heapより速い**ことを繰り返し示している。$E \gg V$のdense graphのような極端なケースでのみFibonacciが意味のある優位性を示す。
>
> **Q. ではいつFibonacci heapを使うのか？**
>
> 実務ではほぼない。理論分析のための「存在証明」としての役割が大きい。研究論文、アルゴリズム教科書、そして特定のamortized分析が必要な場合にのみ。

---

## Part 6: ゲーム開発におけるヒープ

### A* open set — decrease-key問題

[第5回 グラフ](/posts/Graph/)のA*コードを再度見てみよう：

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

問題：同じノード`next`が**既にopen setにあるのに、より小さいf値で再度入る場合は？**

教科書的な答えは**decrease-key** — open setから該当ノードを探して優先度を下げる。ところがbinary heapではこの操作は$O(n)$だ（該当要素を探す必要があるため）。ノード位置を別途`Dictionary`で追跡すれば$O(\log n)$。

実務的な答えはもっと単純だ：**lazy deletion**。

```csharp
// lazy deletion パターン
while (openSet.Count > 0) {
    var (current, f) = openSet.Dequeue();

    if (f > gScore[current]) continue;  // stale entry — 既により良い値が存在

    if (current == goal) return ReconstructPath(...);

    foreach (var next in GetNeighbors(current)) {
        float tentativeG = gScore[current] + Cost(current, next);
        if (tentativeG < gScore.GetValueOrDefault(next, float.MaxValue)) {
            gScore[next] = tentativeG;
            openSet.Enqueue(next, tentativeG + Heuristic(next, goal));
            // 以前のstale entryはそのまま残す — 取り出すときにチェック
        }
    }
}
```

- 同じノードを何度もpushしても問題ない
- 取り出すときに`f > gScore[current]`で「もはや有効でない」を判別
- 実装単純、binary heapだけで十分
- メモリは少し多く使うがほぼ無視できる

UnityのA* Pathfinding Project、Recast/Detourなど実務ライブラリのほとんどがこのパターンを使う。

### イベント / タイマースケジューラ

ゲームサーバやエディタツールで**「時刻$t$にこのタスクを実行せよ」**を大量処理する必要があるとき、ヒープが適している。

```csharp
// 単純なタイマーキュー — (実行時刻, タスク)ペアを時刻昇順で管理
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

このパターンはゲームエンジンのアニメーションイベント、クールダウン、バフ/デバフの期限切れ処理でよく見られる。単純なリスト+毎フレームスキャン方式はイベント数が増えるほど線形コストになるが、ヒープは実際に「今期限切れになるもの」だけを取り出す。

注意：**`heap.Peek()`も$O(1)$**なので「次のイベント時刻」を安価に知ることができる。スリープタイマーを設定するときに有用。

### AI行動スコア

ユーティリティAIで**最もスコアが高い行動N個**だけを考慮したいとき、**サイズ$k$に固定されたmin-heap**を使う。

```csharp
// 上位k個の行動を維持
public class TopKActions {
    private readonly MinHeap<(float score, Action action)> heap = new();
    private readonly int k;

    public TopKActions(int k) { this.k = k; }

    public void Consider(float score, Action action) {
        if (heap.Count < k) {
            heap.Push((score, action));
        } else if (score > heap.Peek().score) {
            heap.Pop();                    // 最も低いスコアを除去
            heap.Push((score, action));
        }
    }

    public IEnumerable<Action> GetTopK() =>
        heap.ToArray().OrderByDescending(x => x.score).Select(x => x.action);
}
```

**min**-heapを使うのがポイント。サイズ$k$のtop-k問題でmin-heapのルートは**「今維持しているk個のうち最も低いもの」**だ。新しい候補がこれより大きければ交換すればよい。この技法は一般的なtop-k問題でも広く使われる。

### Unity NativeContainerの観点

残念ながらUnityはデフォルトで`NativeHeap`を提供していない。[JobSystem第4回 NativeContainer深掘り](/posts/NativeContainerDeepDive/)で見たパターンで**自分で実装**する必要がある。

主要な考慮事項：
- `NativeList<T>`を内部ストレージとして使用（配列ベースなのでヒープと相性が良い）
- `[NativeContainer]`属性と`AtomicSafetyHandle`連携 — Safety Systemと統合
- Burst互換：ジェネリック`IComparable`の代わりに`struct IComparer<T>`を渡す方式を検討
- 並列挿入は難しい — sift-upがルートまで競合するのでロックが必要。通常は**キューで収集後にシングルスレッドで流し込む**パターン

実務ではUnity公式の[BurstAStarGridExample](https://github.com/Unity-Technologies/com.unity.demoteam.digital-human)のような公式/コミュニティ例や、Gilzuの`NativeMinHeap`のような公開実装を参考にするのが速い。

---

## Part 7: .NET `PriorityQueue<TElement, TPriority>`の分析

.NET 6から`System.Collections.Generic.PriorityQueue<TElement, TPriority>`が公式標準として追加された。内部は**4-ary min-heap**だ — 上で見た理由でbinaryではなく4-aryを選んだ。

```csharp
var pq = new PriorityQueue<string, int>();
pq.Enqueue("task-a", 3);
pq.Enqueue("task-b", 1);       // 優先度の数字が小さいほど先に取り出される
pq.Enqueue("task-c", 2);

while (pq.Count > 0) {
    string task = pq.Dequeue();
    // task-b, task-c, task-a の順で取り出される
}
```

公式実装の主要な特徴：

- **TElementとTPriorityが分離** — キューに格納される値と並び替えキーが別物（使い勝手の向上）
- **4-ary heap** — `dotnet/runtime`ソースで`const int Arity = 4`として確認可能
- **`EnqueueDequeue`** — pushしてpopを連続して行うときの最適化（top-kパターンに有用）
- **`UnorderedItems`** — ヒープを「見える順番ではなく」格納された順番で列挙
- **`Dictionary<TElement, ...>`非含有** — decrease-keyは提供しない。lazy deletionを使うべき

**注意事項：**
- **スレッドセーフではない** — マルチスレッド環境では外部ロック必要
- **重複キー許容** — 同じpriorityで複数Enqueue可能、順序は非決定的（不安定）
- **安定ソートが必要**なら、priorityを`(originalPriority, tieBreaker)`のタプルにする必要がある

シンプルなA* open setなら`PriorityQueue<Vector2Int, float>`の一行で済む。自分で実装する理由は(1)カスタム比較子、(2)特殊な割り当てパターン、(3) Burst/Job System統合程度しか残らない。

---

## まとめ

### 核心要約

1. **優先度キューは「最小値/最大値だけ」という部分問題だ** — 完全ソートは過剰スペック、部分順序で$O(\log n)$を得る
2. **二分ヒープは完全二分木を配列にマッピングした構造** — ポインタ0個、インデックス演算だけで親/子を行き来する
3. **sift-upとsift-downがすべてだ** — push、pop、すべての変形操作がこの2つの組み合わせだ
4. **FloydのO(n) build-heap** — 深いノードが多く、浅い移動だけで済むという非対称性の帰結
5. **実務では4-ary heapがbinary heapを上回る** — キャッシュラインに子が集中するレイアウト上の利点
6. **Fibonacci heapは理論用** — 実測でbinary/4-aryに敗れ、実装の複雑さだけが高い
7. **A* decrease-keyはlazy deletionで回避** — 取り出すときにstaleチェック、pushは重複を単に許容
8. **.NET `PriorityQueue<TElement, TPriority>`は4-ary heap** — 自分で実装する理由は多くない

### どのレイヤーの洞察か

第1回 配列と連結リストで見た「**キャッシュが計算量より重要なことがある**」という命題がここでも繰り返される。Fibonacci heapの理論上の$O(1)$ decrease-keyが実務でbinary heapに負けるのは、我々が理論と現実の間の定数を過小評価したからだ。

そしてヒープは**「BSTより弱い構造が特定問題ではより強い」**という例でもある。「部分順序」だけを維持する代わりに配列マッピングというタダのプレゼントを受け取る。データ構造設計において**「どれだけ少なく約束できるか」**がむしろ自由度を高めるという観点 — BSTよりヒープ、完全ソートよりtop-k。CSの多くのアイデアはこの方向に流れる。

この番外編を最後に第1段階（データ構造とメモリ）周辺の負債を整理した。次からは予定通り**第2段階：OSと並行性**に入る。プロセス、スレッド、ロック、そしてマルチコアでの災難たちを見ていく。

---

## 参考資料

**原典および主要論文**
- Williams, J.W.J., "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), pp. 347–348 (1964) — **binary heapの原典**
- Floyd, R.W., "Algorithm 245: Treesort 3", *Communications of the ACM* 7(12), p. 701 (1964) — **$O(n)$ build-heap**
- Johnson, D.B., "Priority queues with update and finding minimum spanning trees", *Information Processing Letters* 4(3), pp. 53–57 (1975) — **d-ary heap**
- Fredman, M.L., Sedgewick, R., Sleator, D.D., Tarjan, R.E., "The pairing heap: A new form of self-adjusting heap", *Algorithmica* 1(1), pp. 111–129 (1986)
- Fredman, M.L. & Tarjan, R.E., "Fibonacci heaps and their uses in improved network optimization algorithms", *Journal of the ACM* 34(3), pp. 596–615 (1987)
- LaMarca, A. & Ladner, R.E., "The influence of caches on the performance of heaps", *ACM Journal of Experimental Algorithmics* 1, Article 4 (1996) — **4-ary heapがbinaryより速いという実証**
- Dutton, R.D., "Weak-heap sort", *BIT Numerical Mathematics* 33(3), pp. 372–381 (1993)
- Brodal, G.S., "Worst-case efficient priority queues", *Proceedings of SODA* (1996)
- Chen, M., Chowdhury, R.A., Ramachandran, V., Roche, D.L., Tong, L., "Priority Queues and Dijkstra's Algorithm", UT Austin Technical Report TR-07-54 (2007) — **Fibonacci vs binary実測比較**

**教科書**
- Cormen, T.H., Leiserson, C.E., Rivest, R.L., Stein, C., *Introduction to Algorithms (CLRS)*, 4th Edition, MIT Press — Chapter 6 (Heapsort), Chapter 19 (Fibonacci Heaps)
- Sedgewick, R. & Wayne, K., *Algorithms*, 4th Edition, Addison-Wesley — Chapter 2.4 Priority Queues
- Knuth, D., *The Art of Computer Programming Vol. 3: Sorting and Searching*, 2nd Edition, Addison-Wesley — Section 5.2.3 Sorting by Selection (heapsort)
- Weiss, M.A., *Data Structures and Algorithm Analysis in C++*, 4th Edition, Pearson — Chapter 6 Priority Queues

**実装参考**
- .NET `PriorityQueue<TElement, TPriority>` — [dotnet/runtimeソース](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Collections/src/System/Collections/Generic/PriorityQueue.cs)：4-ary min-heap公式実装
- C++ `std::priority_queue` — libstdc++, libc++：binary heapベース
- Java `java.util.PriorityQueue` — OpenJDK：binary heapベース
- Python `heapq` — [CPythonソース](https://github.com/python/cpython/blob/main/Lib/heapq.py)：binary min-heap、タプルでpriorityを指定
- Boost Heap — [boost.org/libs/heap](https://www.boost.org/doc/libs/release/libs/heap/)：binary、d-ary、pairing、Fibonacci、skew heapをすべて提供

**ゲーム開発コンテキスト**
- Millington, I. & Funge, J., *Artificial Intelligence for Games*, 3rd Edition, CRC Press — A*、open set管理
- Recast & Detour — [github.com/recastnavigation](https://github.com/recastnavigation/recastnavigation)：実務NavMeshライブラリのヒープ活用
- A* Pathfinding Project (Unity) — [arongranberg.com/astar](https://arongranberg.com/astar/)：lazy deletionベースのopen set
