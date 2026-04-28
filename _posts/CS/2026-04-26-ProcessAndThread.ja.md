---
title: "CSロードマップ 第8回 — プロセスとスレッド：OSは実行単位をどう抽象化するか"
lang: ja
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
  - プロセスは「独立したアドレス空間 + 資源の束」で、スレッドは「プロセス内の実行フロー」である。スレッドはコード/ヒープ/グローバル変数を共有するが、スタックとレジスタは専用で持つ
  - Unixのfork()はプロセスを複製してexec()で上書きする2段階、WindowsのCreateProcess()は一度に新規作成する。複製は高価に見えるがCopy-on-Writeで実際には速い
  - スレッドモデルは1:1 (Linux NPTL、Windows)、N:1（グリーンスレッド）、M:N（Go goroutine、Erlang）に分かれ、性能と実装複雑度のトレードオフが異なる
  - コンテキストスイッチはレジスタ保存/復元だけでなく、TLBフラッシュとキャッシュ汚染まで引き起こすため、現代のゲームエンジンは「スレッド数を増やす」より「Job/TaskGraph/Fiberで作業を細かく分割してコアに分配する」方向に進んでいる
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## はじめに：地図から本論へ

[前回](/posts/OSArchitecture/)では3つのオペレーティングシステムの血統と骨格をざっと見ました。Linuxはモノリシック、Windows NTはハイブリッド、macOS XNUはMach + BSDの二重構造。これが**地図**だったとすれば、今回からは**本論**です。

ステージ2の核心的な問いをもう一度取り出します。

> **「2つのスレッドが同じ変数を使うと、なぜプログラムは時々だけ死ぬのか？」**

この問いに答えるには、まず**「スレッドとは何か」**を正確に知る必要があります。そしてスレッドを理解するには、その上位概念である**プロセス**を先に知る必要があります。プロセスとスレッドの違い、両者がメモリをどう共有しどう分離するか、そしてOSがそれをどう抽象化するか — これが並行性の全ての問題の出発点です。

今回扱う内容：

- **プロセス**：PCBとアドレス空間レイアウト。Linuxの`task_struct`、Windowsの`EPROCESS`、macOSの`proc`/`task`
- **プロセス生成**：Unixの`fork()`+`exec()`2段階モデル、Windowsの`CreateProcess()`単一呼び出し、そしてCopy-on-Write
- **スレッド**：なぜプロセスだけでは足りないのか、TCB、共有領域と専用領域、TLS
- **スレッドマッピングモデル**：1:1、N:1、M:N — Goのgoroutineがなぜあれほど軽いのか
- **コンテキストスイッチ**：レジスタ・TLB・キャッシュコストの実態
- **ゲームエンジンの実行モデル**：Unityのメインスレッド、Unreal TaskGraph、Naughty DogのFiber

ゲーム開発の視点は保ちつつ、今回は**理論的基礎**が多めです。次回（スケジューリング）、その次（同期）がこの上に積み上がるためです。

---

## Part 1：プロセス — OSが見る実行単位

### プロセスとは何か

教科書的な定義から。**プロセス (Process)**は**実行中のプログラム**です。ハードディスク上の`.exe`ファイルやMach-Oバイナリは**プログラム**で、それがメモリにロードされてCPUで実行されているインスタンスが**プロセス**です。

プロセスが持つもの：

1. **固有のアドレス空間 (Address Space)** — 他のプロセスと隔離されたメモリ
2. **実行状態** — CPUレジスタ値、プログラムカウンタ
3. **開いているファイルのテーブル** — 現在使用中のファイルディスクリプタ一覧
4. **所有者情報** — UID、GIDなどの権限
5. **子プロセス関係** — 誰が誰を作ったか（プロセスツリー）

OSはこれらの情報をすべて1つの**構造体**で管理します。これが**PCB (Process Control Block)**、またはプロセスディスクリプタです。

### PCBの実体 — OS別の構造体

**Linux — `task_struct`**

Linuxカーネルでプロセス（およびスレッド）を表す構造体は`struct task_struct`です。`include/linux/sched.h`で定義されており、**数百個のフィールド**を持つ巨大な構造体です。

```c
/* Linuxカーネルのtask_structの一部 (kernel 6.x基準、極端に単純化) */
struct task_struct {
    /* 状態 */
    unsigned int           __state;          /* TASK_RUNNING など */

    /* 識別子 */
    pid_t                  pid;              /* プロセスID */
    pid_t                  tgid;             /* スレッドグループID */
    struct task_struct    *parent;           /* 親プロセス */
    struct list_head       children;         /* 子のリスト */

    /* メモリ */
    struct mm_struct      *mm;               /* アドレス空間 */

    /* ファイル */
    struct files_struct   *files;            /* 開いているファイルテーブル */

    /* スケジューリング */
    int                    prio;
    struct sched_entity    se;               /* CFSスケジューリングエンティティ */

    /* シグナル、リソース制限など数百フィールド... */
};
```

実際の構造体は700行を超えます。Linuxでは**プロセスとスレッドが同じ構造体**で表現されます — これはLinuxの独特な設計で、後で再度扱います。

**Windows — `EPROCESS`、`KPROCESS`**

Windows NTは2層に分かれます：
- `KPROCESS` (Kernel Process Block) — スケジューリング関連の最小情報
- `EPROCESS` (Executive Process Block) — `KPROCESS`をラップして追加情報を含む

```c
/* 概念的な擬似コード — 実際のWindows内部はWinDbgやNTソース流出版を参照 */
typedef struct _EPROCESS {
    KPROCESS Pcb;                    /* カーネルプロセスブロック (継承) */
    HANDLE UniqueProcessId;          /* PID */
    LIST_ENTRY ActiveProcessLinks;   /* グローバルプロセスリスト */
    PVOID SectionBaseAddress;        /* イメージロードアドレス */
    PVOID Token;                     /* セキュリティトークン */
    /* ... */
} EPROCESS;
```

**macOS — `proc` + `task`**

macOSの二重構造がここにも現れます。**BSDレイヤ**にはUnix伝統の`struct proc`があり、**Machレイヤ**には`struct task`があります。

```c
/* BSD側 — bsd/sys/proc_internal.h */
struct proc {
    pid_t                  p_pid;           /* POSIXプロセスID */
    struct proc           *p_pptr;          /* 親 */
    struct task           *task;            /* Mach taskへのリンク */
    /* ... */
};

/* Mach側 — osfmk/kern/task.h */
struct task {
    queue_head_t           threads;         /* このtaskに属するスレッドたち */
    vm_map_t               map;             /* アドレス空間 */
    ipc_space_t            itk_space;       /* Mach port空間 */
    /* ... */
};
```

つまりmacOSで`fork()`でプロセスを作ると、**BSDの`proc`とMachの`task`がペアで生成**されます。Unixプログラム（`ps`、`top`）は`proc`を見て、Machベースのツール（`lldb`、`Instruments`）は`task`を見ます。

### プロセスのアドレス空間レイアウト

プロセスが持つメモリは**どう配置**されているでしょうか？伝統的なUnix/Linuxプロセスの32ビットアドレス空間レイアウトを見ます。

<div class="pt-addr-container">
<svg viewBox="0 0 700 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process address space layout">
  <text x="350" y="28" text-anchor="middle" class="pa-title">プロセスのアドレス空間レイアウト（概念図）</text>

  <g class="pa-layer pa-kernel">
    <rect x="180" y="55" width="340" height="50" rx="4"/>
    <text x="350" y="78" text-anchor="middle" class="pa-label">Kernel Space</text>
    <text x="350" y="95" text-anchor="middle" class="pa-sub">（ユーザープロセスから直接アクセス不可）</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="130" x2="600" y2="105" class="pa-arrow"/>
    <text x="615" y="122" class="pa-addr">高位アドレス</text>
    <text x="615" y="138" class="pa-addr">0xFFFFFFFF</text>
  </g>

  <g class="pa-layer pa-stack">
    <rect x="180" y="120" width="340" height="70" rx="4"/>
    <text x="350" y="145" text-anchor="middle" class="pa-label">Stack</text>
    <text x="350" y="165" text-anchor="middle" class="pa-sub">関数呼び出しフレーム、ローカル変数</text>
    <text x="350" y="180" text-anchor="middle" class="pa-sub pa-emph">↓ 下に伸びる</text>
  </g>

  <g class="pa-layer pa-gap">
    <rect x="180" y="200" width="340" height="120" rx="4"/>
    <text x="350" y="235" text-anchor="middle" class="pa-label pa-gray">未使用領域</text>
    <text x="350" y="258" text-anchor="middle" class="pa-sub pa-gray">Stackが伸びるための空間</text>
    <text x="350" y="280" text-anchor="middle" class="pa-sub pa-gray">mmapされた共有ライブラリがここに配置</text>
    <text x="350" y="300" text-anchor="middle" class="pa-sub pa-gray">（libc、libdl、ヒープ拡張など）</text>
  </g>

  <g class="pa-layer pa-heap">
    <rect x="180" y="330" width="340" height="70" rx="4"/>
    <text x="350" y="355" text-anchor="middle" class="pa-label">Heap</text>
    <text x="350" y="375" text-anchor="middle" class="pa-sub">malloc / newで割り当てられるメモリ</text>
    <text x="350" y="390" text-anchor="middle" class="pa-sub pa-emph">↑ 上に伸びる（brk / sbrk）</text>
  </g>

  <g class="pa-layer pa-bss">
    <rect x="180" y="410" width="340" height="40" rx="4"/>
    <text x="350" y="432" text-anchor="middle" class="pa-label">BSS (Uninitialized Data)</text>
    <text x="350" y="445" text-anchor="middle" class="pa-sub">int x; （0で初期化）</text>
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
    <text x="350" y="583" text-anchor="middle" class="pa-sub">実行可能な機械語</text>
  </g>

  <g class="pa-arrow-grp">
    <line x1="600" y1="568" x2="600" y2="590" class="pa-arrow"/>
    <text x="615" y="583" class="pa-addr">低位アドレス</text>
    <text x="615" y="598" class="pa-addr">0x00400000</text>
  </g>

  <g class="pa-note">
    <text x="40" y="78" class="pa-sectlabel">保護</text>
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

各領域を説明します（低位アドレスから）：

- **Text (`.text`)**：実行可能な機械語。**読み取り + 実行**のみ許可。書き込みを試みるとセグメンテーションフォールト
- **Read-only Data (`.rodata`)**：文字列リテラル（`"Hello"`）、定数配列など。**読み取り専用**
- **Data (`.data`)**：初期化済みグローバル/静的変数（`int x = 42;`）。ファイルに初期値が含まれる
- **BSS (Block Started by Symbol)**：0で初期化されたグローバル変数（`int x;`、`static char buf[1024];`）。ファイルには**サイズのみ**が記録され、実行時にOSが0で埋める — 実行ファイルのサイズを縮めるトリック
- **Heap**：動的割り当て（`malloc`、`new`）。`brk()`システムコールで上に拡張
- **共有ライブラリ領域 (mmap)**：`libc.so`、`libstdc++.so`などが`mmap()`でこの領域にマップされる
- **Stack**：関数呼び出しフレーム、ローカル変数、戻りアドレス。**下向きに**伸びる
- **Kernel Space**：カーネルコードとデータ。ユーザープロセスは直接アクセス不可。32ビットLinuxでは上位1GB、x86-64では上位半分

**WindowsもPEで異なるセクション名を使いますが、構造はほぼ同じ**です（`.text`、`.data`、`.rdata`、`.bss`）。

### プロセスの状態遷移

プロセスは**複数の状態**を行き来します。Silberschatz教科書の標準モデル：

<div class="ps-container">
<svg viewBox="0 0 900 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="プロセス状態遷移図">
  <defs>
    <marker id="ps-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" class="ps-arrowfill"/>
    </marker>
  </defs>

  <text x="450" y="22" text-anchor="middle" class="ps-title">プロセス状態遷移 (Silberschatzモデル)</text>

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

- **New**：プロセスが作られたばかり
- **Ready**：実行可能だがCPUを待っている
- **Running**：CPUで実際に実行中
- **Waiting（またはBlocked）**：I/O完了やイベントを待っている
- **Terminated**：終了

実際のOSは**さらに複雑な状態**を持ちます。Linuxの`task_struct`には`TASK_RUNNING`、`TASK_INTERRUPTIBLE`、`TASK_UNINTERRUPTIBLE`、`TASK_STOPPED`、`TASK_TRACED`、`TASK_DEAD`、`TASK_WAKEKILL`、`TASK_WAKING`、`TASK_PARKED`などがあります。`ps`で見える`S`、`R`、`D`、`Z`といった文字がこれらです。

```bash
$ ps aux
USER  PID  %CPU %MEM  COMMAND
root   1   0.0  0.1   /sbin/init           <- S (sleeping)
www    1234 2.1  1.5   nginx: worker        <- R (running)
root   5678 0.0  0.0   [kworker/u8:2]       <- D (uninterruptible sleep)
```

**D状態（uninterruptible sleep）**はゲーム開発者にも重要です — ディスクI/Oやドライバ要求を待っている状態で、この状態では`kill -9`すら効きません。「応答しないプロセス」のかなりの部分がD状態です。

---

## Part 2：プロセス生成 — fork、exec、CreateProcess

次にプロセスを**どう作るか**を見ます。3つのOSの哲学の違いが最も鮮明に表れる点です。

### Unix：fork() + exec() — 2段階モデル

Unixのアイデアは**「親を複製してから上書きする」**です。

```c
#include <unistd.h>
#include <sys/wait.h>

int main() {
    pid_t pid = fork();   /* 1段階：自分を複製 */

    if (pid == 0) {
        /* 子プロセス */
        execl("/bin/ls", "ls", "-l", NULL);   /* 2段階：新プログラムで上書き */
        /* execlが成功すればここは実行されない */
    } else if (pid > 0) {
        /* 親プロセス */
        int status;
        waitpid(pid, &status, 0);             /* 子の終了を待機 */
    } else {
        perror("fork failed");
    }
    return 0;
}
```

`fork()`ひとつの呼び出しが**2回リターン**します。親には子のPIDを、子には0を返します。独特なAPIです。

**fork()がやること**（naiveな実装）：
1. 新しいPCB（`task_struct`）を作成
2. 親のアドレス空間を**すべてコピー**（text、data、heap、stackすべて）
3. 開いているファイルディスクリプタもコピー
4. 子に新しいPIDを割り当て
5. 子をreadyキューに入れる

問題は2番目です。プロセスのアドレス空間が数百MBのとき**毎回コピーするのは莫大に高価**です。しかも`fork()`直後に`exec()`を呼べばどうせアドレス空間を上書きするわけで、コピーしてすぐ捨てることになります。

### Copy-on-Write — 「本当に書き込むときにコピー」

解決策は**Copy-on-Write (COW)**です。`fork()`時点では**ページテーブルだけをコピー**し、実際のメモリページは親と子が**共有**します。ただしページは**読み取り専用**にマークされます。

どちらかがページに**書き込もうとすると**ハードウェアがpage faultを発生させ、OSはそこで初めて**そのページだけ**コピーします。

<div class="pt-fork-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="fork with COW">
  <text x="450" y="28" text-anchor="middle" class="pf-title">fork() + Copy-on-Writeの実際の動作</text>

  <g class="pf-step">
    <text x="150" y="65" text-anchor="middle" class="pf-step-label">1) fork()呼び出し直後</text>
    <rect x="30" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="80" y="105" text-anchor="middle" class="pf-proc-label">親</text>
    <text x="80" y="125" text-anchor="middle" class="pf-proc-sub">ページテーブル</text>

    <rect x="170" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="220" y="105" text-anchor="middle" class="pf-proc-label">子</text>
    <text x="220" y="125" text-anchor="middle" class="pf-proc-sub">ページテーブル（コピー）</text>

    <rect x="80" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="150" y="194" text-anchor="middle" class="pf-page-label">物理ページ（読み取り専用）</text>

    <line x1="80" y1="140" x2="130" y2="170" class="pf-edge"/>
    <line x1="220" y1="140" x2="170" y2="170" class="pf-edge"/>

    <text x="150" y="235" text-anchor="middle" class="pf-note">ページテーブルだけコピー — 速い</text>
    <text x="150" y="252" text-anchor="middle" class="pf-note">実メモリは共有</text>
  </g>

  <g class="pf-step">
    <text x="450" y="65" text-anchor="middle" class="pf-step-label">2) 子がページへの書き込みを試行</text>
    <rect x="330" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="380" y="105" text-anchor="middle" class="pf-proc-label">親</text>
    <text x="380" y="125" text-anchor="middle" class="pf-proc-sub">ページテーブル</text>

    <rect x="470" y="80" width="100" height="60" rx="4" class="pf-proc pf-proc-active"/>
    <text x="520" y="105" text-anchor="middle" class="pf-proc-label">子</text>
    <text x="520" y="125" text-anchor="middle" class="pf-proc-sub">書き込み試行 ✍️</text>

    <rect x="380" y="170" width="140" height="40" rx="4" class="pf-page"/>
    <text x="450" y="194" text-anchor="middle" class="pf-page-label">物理ページ（読み取り専用）</text>

    <line x1="380" y1="140" x2="430" y2="170" class="pf-edge"/>
    <line x1="520" y1="140" x2="470" y2="170" class="pf-edge pf-edge-fault"/>

    <text x="450" y="235" text-anchor="middle" class="pf-note pf-fault">⚡ Page Fault発生</text>
    <text x="450" y="252" text-anchor="middle" class="pf-note">CPU → OSに処理を要請</text>
  </g>

  <g class="pf-step">
    <text x="750" y="65" text-anchor="middle" class="pf-step-label">3) OSがページをコピー</text>
    <rect x="630" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="680" y="105" text-anchor="middle" class="pf-proc-label">親</text>

    <rect x="770" y="80" width="100" height="60" rx="4" class="pf-proc"/>
    <text x="820" y="105" text-anchor="middle" class="pf-proc-label">子</text>

    <rect x="620" y="170" width="120" height="40" rx="4" class="pf-page pf-page-orig"/>
    <text x="680" y="194" text-anchor="middle" class="pf-page-label">原本（RW復元）</text>

    <rect x="760" y="170" width="120" height="40" rx="4" class="pf-page pf-page-new"/>
    <text x="820" y="194" text-anchor="middle" class="pf-page-label">コピー（子専用）</text>

    <line x1="680" y1="140" x2="680" y2="170" class="pf-edge"/>
    <line x1="820" y1="140" x2="820" y2="170" class="pf-edge"/>

    <text x="750" y="235" text-anchor="middle" class="pf-note">実際に書いたページだけコピー</text>
    <text x="750" y="252" text-anchor="middle" class="pf-note">残りは引き続き共有</text>
  </g>

  <g class="pf-conclusion">
    <rect x="30" y="290" width="840" height="130" rx="8" class="pf-concl-box"/>
    <text x="450" y="315" text-anchor="middle" class="pf-concl-title">結果：fork()は「コピー」ではなく「共有 + 遅延コピー」</text>
    <text x="450" y="343" text-anchor="middle" class="pf-concl-line">• fork()自体はページテーブルのサイズ分だけの作業 — 数マイクロ秒</text>
    <text x="450" y="363" text-anchor="middle" class="pf-concl-line">• 子がほとんどのページを書かずにすぐexec()を呼べばコピーコストはほぼ0</text>
    <text x="450" y="383" text-anchor="middle" class="pf-concl-line">• ページ単位の粒度（通常4KBか16KB） — 1バイト書くとページ全体がコピーされる</text>
    <text x="450" y="403" text-anchor="middle" class="pf-concl-line">• Linuxはこれをタスク生成の基本とし、プロセス生成が非常に速い</text>
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

COWはハードウェアサポートが必要です — CPUのMMU (Memory Management Unit) がページ単位の保護とpage faultを発生させてくれてはじめてOSが介入できます。そのため**ページ単位のMMU**は現代OSのほぼすべてのトリック（COW、スワップ、mmap、共有メモリ）の基盤です。

### Windows：CreateProcess() — 単一呼び出し

Windowsは別の道を選びました。親複製の概念がなく、**新プロセスを最初から作ります**。

```c
#include <windows.h>

int main() {
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    BOOL ok = CreateProcess(
        "C:\\Windows\\System32\\notepad.exe",  /* 実行ファイル */
        NULL,                                   /* コマンドライン */
        NULL, NULL,                             /* プロセス/スレッドセキュリティ属性 */
        FALSE,                                  /* ハンドル継承有無 */
        0,                                      /* 生成フラグ */
        NULL, NULL,                             /* 環境変数、作業ディレクトリ */
        &si, &pi);

    if (ok) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    return 0;
}
```

Unixの`fork()`は引数がないのに、`CreateProcess()`は**10個**の引数を取ります。これは「プロセス生成時に設定可能なすべてのオプションを1つの関数に詰め込む」Windowsの哲学です。

**トレードオフ**：

| 側面 | Unix `fork()+exec()` | Windows `CreateProcess()` |
|------|---------------------|---------------------------|
| **API複雑度** | 2段階だが各々シンプル | 1段階だが引数が多い |
| **プロセス生成コスト** | COWで非常に安い | 相対的に高い |
| **シェル実装** | 自然（fork → リダイレクション設定 → exec） | ShellExecuteのような別APIが必要 |
| **セキュリティ** | 親のハンドルが自動継承（ミスの余地あり） | 明示的に継承指定 |
| **柔軟性** | fork後exec前に任意コードを実行できる | 生成時点だけで設定 |

### macOS — Unix継承 + いくつかのひねり

macOSはBSD継承なので当然`fork()`と`exec()`をサポートします。しかし**XNUの内部実装は少し独特**です。

BSDの`fork()`がMachにマッピングされるとき実際には：
1. 現在の`proc`構造体を複製
2. 現在の`task`をMachレベルで複製（`task_create()`）
3. 初期スレッドを1つ作成（`thread_create()`）
4. アドレス空間も複製（Machのvm_mapをCOWで複製）

つまり、**BSDの`fork()`呼び出し1つがMachレイヤの複数の操作**に分解されます。これがXNU二重構造の実際の姿です。

もう1つ興味深いのはmacOSの**`posix_spawn()`**です。POSIX標準ですがmacOSが積極的に推奨するAPIで、**fork+execを一度に実行**します。

```c
posix_spawn(&pid, "/bin/ls", NULL, NULL, argv, environ);
```

なぜこれを使えと言うのか？**iOSのためです**。iOSでは`fork()`がセキュリティ上禁止されており、`posix_spawn()`のみ許可されます。また内部実装がより効率的な場合もあります（COWのページテーブル複製すら省略できる）。

> ### ちょっと、これは押さえておこう
>
> **「iOSでfork()をなぜ禁止したのか？」**
>
> 3つの理由が重なります。
>
> 1. **サンドボックス侵害リスク**：fork()された子プロセスは親の権限を継承しますが、iOSの厳格なアプリサンドボックスモデルではこの境界を壊しかねない潜在的脆弱性になります
> 2. **Objective-Cランタイムの状態複製問題**：iOSアプリはほとんどがObjective-CやSwiftで書かれ、これらの言語のランタイムは初期化時に多くの状態（スレッド、GCDキュー、IOKit接続など）を生成します。fork()以降これらの状態が整合性を失いがちです
> 3. **メモリ効率**：iOSはメモリが限られており、COWでもページテーブル複製は必要。posix_spawn()はこれすら省略可能
>
> macOSではfork()は依然として許可されていますが、Appleは「可能な限りposix_spawn()を使う」ことを推奨します。

---

## Part 3：スレッド — なぜプロセスだけでは足りないのか

### プロセスベース並行性の限界

1970〜80年代のUnixは**プロセス1つ = 実行フロー1つ**でした。複数のことを同時にしたければ`fork()`でプロセスを複数作りました。Webサーバであれば接続ごとにプロセスを1つずつ作る方式（古典的なApacheの`prefork`モード）。

このモデルの問題：

1. **プロセス生成コスト**：COWで安くなったとはいえ、ページテーブル複製、PCB割り当てなど、依然数マイクロ秒〜ミリ秒単位
2. **コンテキストスイッチコスト**：プロセス間切り替え時にアドレス空間も変わるためTLBフラッシュが必要（後で詳述）
3. **プロセス間通信 (IPC) コスト**：プロセス同士はアドレス空間が分離されているため、データをやり取りするにはパイプ、ソケット、共有メモリなど重いメカニズムが必要
4. **共有状態の表現の難しさ**：複数の実行フローが同じデータ構造を扱いたいとき複雑

1990年代に入って解決策が必要になり、それが**スレッド (Thread)**です。

### スレッドの定義

**スレッド**とは**プロセス内部の独立した実行フロー**です。1つのプロセスの中に複数のスレッドがあれば、全員が同じアドレス空間を共有しながら、**それぞれがCPUで同時に実行されえます**。

スレッドが**共有**するもの：
- **Text（コード）**：当然同じコードを実行
- **Heap**：`malloc`で割り当てたメモリ
- **Data / BSS**：グローバル変数、静的変数
- **開いているファイルディスクリプタ**
- **シグナルハンドラ**

スレッドが**別々に持つ**もの：
- **Stack（スタック）**：各スレッドごとに別
- **CPUレジスタ状態**：PC、SP、汎用レジスタなど
- **TLS (Thread-Local Storage)**：スレッド別のグローバル変数
- **エラー状態**：`errno`（POSIXではスレッド別）

<div class="pt-share-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Process vs thread memory sharing">
  <text x="450" y="28" text-anchor="middle" class="ps-title">プロセス間 vs スレッド間のメモリ共有</text>

  <g class="ps-left">
    <text x="225" y="62" text-anchor="middle" class="ps-heading">複数プロセス — 完全分離</text>

    <g class="ps-proc">
      <rect x="40" y="80" width="170" height="330" rx="8"/>
      <text x="125" y="103" text-anchor="middle" class="ps-proc-label">プロセスA</text>
      <rect x="55" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="125" y="137" text-anchor="middle" class="ps-sect-lab">Text（コード）</text>
      <rect x="55" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="125" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="55" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="125" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="55" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="125" y="302" text-anchor="middle" class="ps-sect-lab">Stack（実行フロー1）</text>
      <rect x="55" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="55" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="125" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="55" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <g class="ps-proc">
      <rect x="240" y="80" width="170" height="330" rx="8"/>
      <text x="325" y="103" text-anchor="middle" class="ps-proc-label">プロセスB</text>
      <rect x="255" y="118" width="140" height="28" rx="3" class="ps-sect ps-sect-text"/>
      <text x="325" y="137" text-anchor="middle" class="ps-sect-lab">Text（別）</text>
      <rect x="255" y="152" width="140" height="28" rx="3" class="ps-sect ps-sect-data"/>
      <text x="325" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS</text>
      <rect x="255" y="186" width="140" height="80" rx="3" class="ps-sect ps-sect-heap"/>
      <text x="325" y="227" text-anchor="middle" class="ps-sect-lab">Heap</text>
      <rect x="255" y="272" width="140" height="50" rx="3" class="ps-sect ps-sect-stack"/>
      <text x="325" y="302" text-anchor="middle" class="ps-sect-lab">Stack（実行フロー1）</text>
      <rect x="255" y="328" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="345" text-anchor="middle" class="ps-sect-lab">Registers, PC</text>
      <rect x="255" y="358" width="140" height="24" rx="3" class="ps-sect ps-sect-misc"/>
      <text x="325" y="375" text-anchor="middle" class="ps-sect-lab">File descriptors</text>
      <rect x="255" y="388" width="140" height="14" rx="3" class="ps-sect ps-sect-misc"/>
    </g>

    <text x="225" y="433" text-anchor="middle" class="ps-caption">IPC（パイプ/ソケット/共有メモリ）なしでは会話不可</text>
  </g>

  <g class="ps-right">
    <text x="675" y="62" text-anchor="middle" class="ps-heading">1プロセス内の複数スレッド — ほぼ共有</text>

    <g class="ps-proc ps-proc-big">
      <rect x="470" y="80" width="410" height="330" rx="8"/>
      <text x="675" y="103" text-anchor="middle" class="ps-proc-label">プロセスC（スレッド3つ）</text>

      <rect x="485" y="118" width="380" height="28" rx="3" class="ps-sect ps-sect-text ps-sect-shared"/>
      <text x="675" y="137" text-anchor="middle" class="ps-sect-lab">Text（共有）</text>
      <rect x="485" y="152" width="380" height="28" rx="3" class="ps-sect ps-sect-data ps-sect-shared"/>
      <text x="675" y="171" text-anchor="middle" class="ps-sect-lab">Data / BSS（共有）</text>
      <rect x="485" y="186" width="380" height="60" rx="3" class="ps-sect ps-sect-heap ps-sect-shared"/>
      <text x="675" y="221" text-anchor="middle" class="ps-sect-lab">Heap（共有）</text>

      <g class="ps-thread">
        <rect x="485" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="545" y="272" text-anchor="middle" class="ps-sect-lab">Stack T1</text>
        <text x="545" y="290" text-anchor="middle" class="ps-sect-sub">専用</text>
      </g>
      <g class="ps-thread">
        <rect x="615" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="675" y="272" text-anchor="middle" class="ps-sect-lab">Stack T2</text>
        <text x="675" y="290" text-anchor="middle" class="ps-sect-sub">専用</text>
      </g>
      <g class="ps-thread">
        <rect x="745" y="252" width="120" height="50" rx="3" class="ps-sect ps-sect-stack ps-sect-private"/>
        <text x="805" y="272" text-anchor="middle" class="ps-sect-lab">Stack T3</text>
        <text x="805" y="290" text-anchor="middle" class="ps-sect-sub">専用</text>
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
      <text x="675" y="361" text-anchor="middle" class="ps-sect-lab">File descriptors（共有）</text>

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

    <text x="675" y="433" text-anchor="middle" class="ps-caption">同じheap/dataをそのまま読み書きする — 競合条件の根源</text>
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

この図で重要な点：

1. **スレッド間ではheapとグローバル変数がそのまま共有されます** — 「共有メモリ」が自然に存在する
2. つまりスレッド2つが同じ`int counter`を同時に`counter++`すると**race condition**が生じる
3. 逆にプロセス2つはアドレス空間が分離されていて自然に隔離されている

ステージ2の核心的な問い — 「**スレッド2つが同じ変数を使うとなぜプログラムが時々だけ死ぬのか？**」 — の答えがこの図の中にあります。スレッドは**意図的にメモリを共有する**ため並行性の問題が生じ、それを管理する**同期技法**が必要です。（次回Part 10同期プリミティブで本格的に扱います。）

### TCB — スレッド制御ブロック

プロセスにPCBがあるように、スレッドには**TCB (Thread Control Block)**があります。TCBが持つもの：

- スレッドID
- CPUレジスタ状態（保存されたコンテキスト）
- スレッド状態（Running、Ready、Waiting）
- スタックポインタ、スタックベース
- スケジューリング情報（優先度など）
- 所属プロセスへのポインタ

OS別の実装：

- **Linux**：`task_struct` — プロセスとスレッドを**同じ構造体**で表現。どのフィールドを共有するかで区別する
- **Windows**：`KTHREAD` + `ETHREAD`
- **macOS**：Machの`struct thread`

### Linuxの独特な哲学 — 「プロセスとスレッドは同じ」

Linus Torvaldsは1990年代に大胆な決定をしました。**「プロセスとスレッドを別の概念にせず、1つの『実行単位』として統合しよう。」**

Linuxでは`fork()`の代わりに、より一般的な`clone()`システムコールがあります。`clone()`は**「親と何を共有するか」**をビットフラグで指定します。

```c
/* Linux clone() — 概念 */
clone(fn, stack, flags, arg);

/* フラグの例： */
CLONE_VM       /* アドレス空間を共有（trueならスレッド、falseならプロセス） */
CLONE_FS       /* ファイルシステム状態を共有 */
CLONE_FILES    /* ファイルディスクリプタを共有 */
CLONE_SIGHAND  /* シグナルハンドラを共有 */
CLONE_THREAD   /* 同じスレッドグループに所属 */
/* ... */
```

- `fork()` = `clone()` with **すべての共有フラグOFF**
- `pthread_create()` = `clone()` with **すべての共有フラグON**
- その間の**任意の組み合わせ**が可能

これがLinuxの「プロセスとスレッドは連続的」な見方です。実際、Androidのような環境では**「一部だけ共有する」プロセス複製**を有効に使います（Zygoteプロセス）。

### TLS — Thread-Local Storage

スレッドごとに**グローバルに見えるが実際にはスレッドごとに独立した変数**が必要な場合があります。これが**TLS**です。

典型例：`errno`。POSIXで`errno`は「最後のシステムコールのエラーコード」ですが、スレッドごとに別でなければいけません（スレッドAが`read()`に失敗した結果をスレッドBが上書きしてはいけない）。だから`errno`はTLSとして実装されます。

言語別のTLS宣言：

```c
/* C11 */
_Thread_local int counter = 0;

/* GCC/Clang拡張 */
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

// またはより柔軟なThreadLocal<T>
static ThreadLocal<int> counter = new ThreadLocal<int>(() => 0);
```

ゲーム開発での実用例：
- ロギングシステムで各スレッドの**名前**をTLSに保存してログ行に含める
- レンダリングで**スレッド別のコマンドバッファ**を割り当てて後でマージ
- プロファイリングで**現在実行中のスコープスタック**をスレッド別に管理

---

## Part 4：スレッドモデル — 1:1、N:1、M:N

さらに深い問いです。あなたが`pthread_create()`や`new Thread()`を呼ぶとき、**OSカーネルはそのスレッドをどう管理**するのでしょうか？

### なぜこの問いが重要か

CPUで実際に実行可能な単位は**カーネルスレッド (Kernel-level Thread, KLT)**です。カーネルだけがCPUをスケジューリングできるためです。

一方プログラムが作る「スレッド」は単に**ユーザー空間の抽象化**かもしれません。これを**ユーザースレッド (User-level Thread, ULT)**と呼びます。

ユーザースレッドとカーネルスレッドのマッピング方式は3つに分かれます。

<div class="pt-model-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Thread mapping models">
  <text x="450" y="28" text-anchor="middle" class="pm-title">ユーザースレッド ↔ カーネルスレッドのマッピングモデル</text>

  <g class="pm-model">
    <rect x="30" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="165" y="80" text-anchor="middle" class="pm-heading">1:1（一対一）</text>
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
      <text x="165" y="290" text-anchor="middle" class="pm-sec-label">長所</text>
      <text x="165" y="310" text-anchor="middle" class="pm-line">• 実装がシンプル</text>
      <text x="165" y="328" text-anchor="middle" class="pm-line">• 真の並列性（マルチコア）</text>
      <text x="165" y="346" text-anchor="middle" class="pm-line">• カーネルスケジューラ活用</text>
    </g>
    <g class="pm-cons">
      <text x="165" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">短所</text>
      <text x="165" y="400" text-anchor="middle" class="pm-line">• スレッド生成コストが高い</text>
      <text x="165" y="418" text-anchor="middle" class="pm-line">• 数千個でカーネル資源枯渇</text>
      <text x="165" y="436" text-anchor="middle" class="pm-line">• コンテキストスイッチが重い</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="315" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="450" y="80" text-anchor="middle" class="pm-heading">N:1（多対一）</text>
    <text x="450" y="100" text-anchor="middle" class="pm-sub">昔のグリーンスレッド、GNU Pth</text>

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
      <text x="450" y="240" text-anchor="middle" class="pm-klt-label">KLT 1個</text>
    </g>

    <g class="pm-pros">
      <text x="450" y="290" text-anchor="middle" class="pm-sec-label">長所</text>
      <text x="450" y="310" text-anchor="middle" class="pm-line">• スレッド生成が極めて安い</text>
      <text x="450" y="328" text-anchor="middle" class="pm-line">• 数十万個が可能</text>
      <text x="450" y="346" text-anchor="middle" class="pm-line">• ユーザースケジューラの自由</text>
    </g>
    <g class="pm-cons">
      <text x="450" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">短所</text>
      <text x="450" y="400" text-anchor="middle" class="pm-line">• 並列性なし（コア1個のみ）</text>
      <text x="450" y="418" text-anchor="middle" class="pm-line">• ブロッキングsyscall = 全停止</text>
      <text x="450" y="436" text-anchor="middle" class="pm-line">• 現在はほぼ使われない</text>
    </g>
  </g>

  <g class="pm-model">
    <rect x="600" y="55" width="270" height="400" rx="8" class="pm-box"/>
    <text x="735" y="80" text-anchor="middle" class="pm-heading">M:N（多対多）</text>
    <text x="735" y="100" text-anchor="middle" class="pm-sub">Go、Erlang、昔のSolaris</text>

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
      <text x="735" y="290" text-anchor="middle" class="pm-sec-label">長所</text>
      <text x="735" y="310" text-anchor="middle" class="pm-line">• スレッド安い + 並列性</text>
      <text x="735" y="328" text-anchor="middle" class="pm-line">• 両者の長所を結合</text>
      <text x="735" y="346" text-anchor="middle" class="pm-line">• 数百万goroutineが可能</text>
    </g>
    <g class="pm-cons">
      <text x="735" y="380" text-anchor="middle" class="pm-sec-label pm-sec-con">短所</text>
      <text x="735" y="400" text-anchor="middle" class="pm-line">• ランタイム実装が複雑</text>
      <text x="735" y="418" text-anchor="middle" class="pm-line">• スケジューリング公平性課題</text>
      <text x="735" y="436" text-anchor="middle" class="pm-line">• デバッグが難しい</text>
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

### 1:1モデル — 現代のLinux/Windowsの選択

**1:1モデル**ではユーザーが作ったスレッド1つがそのままカーネルスレッド1つです。`pthread_create()`が内部的に`clone()`システムコールを呼び出してカーネルが管理するタスクを直接作ります。

**Linux NPTL (Native POSIX Thread Library)**：
Linux 2.6からglibcのpthread実装はNPTLを使い、NPTLは1:1モデルです。以前は**LinuxThreads**という非標準1:1実装がありましたが、NPTLがPOSIX準拠 + 性能で置き換えました。

**Windows**：
`CreateThread()`はカーネルの`KTHREAD`を直接作ります。やはり1:1。

**長所**：スレッドがブロックされても他のスレッドは動き続ける。マルチコアで自動分散。

**短所**：スレッド生成コストが比較的高く、数万〜数十万個になるとカーネルメモリが圧迫される。

### N:1モデル — 過去の遺産

**N:1モデル**では複数のユーザースレッドがカーネルスレッド1つにマップされます。カーネルは「このプロセスにスレッドが複数ある」ことを知りません — プロセスは1つにしか見えません。

このモデルはJavaの初期「グリーンスレッド」、GNU Pthなどのライブラリで使われました。1990年代初頭には標準でしたが、**致命的な短所**のためにほぼ消えました：

- **ブロッキングシステムコールが全体を止める**：ユーザースレッド1つが`read()`でブロックすると、同じカーネルスレッドを共有するすべてのユーザースレッドが止まる
- **マルチコアが使えない**：カーネルスレッド1つはCPUコア1つにしか割り当てられない

### M:Nモデル — Goの選択

**M:Nモデル**は2つのモデルの長所を合わせます。M個のユーザースレッドがN個のカーネルスレッドプールに動的にマップされます（通常N = CPUコア数）。

**代表的な実装**：
- **Go goroutine**：Goランタイムが M:Nスケジューラ。数百万goroutineを数個のOSスレッドで動かす
- **Erlang/Elixir**：BEAM VMが独自のスケジューラを実装
- **昔のSolaris**（Solaris 2〜8）：標準POSIX pthreadsをM:Nで実装したが、複雑性のためSolaris 9で1:1に転換

**理論的背景** — Andersonらの1991年SOSP論文 [Scheduler Activations](https://dl.acm.org/doi/10.1145/121132.121151)：「ユーザーレベルスレッドライブラリがカーネルと協力してM:Nを効率的に実装するには、どんなカーネルサポートが必要か」を扱いました。核心は**ブロッキングシステムコール時にカーネルがユーザースケジューラを起こし、別のユーザースレッドを別のカーネルスレッドに割り当てさせるべき**ということ。

Goランタイムはこれに似たアイデアを実装します。goroutineがblocking syscallを呼ぼうとするとランタイムがそれを検知して**そのgoroutineを別のカーネルスレッドに移植**するか、新しいカーネルスレッドを作ります。だから`net.Listen`がブロックしても他のgoroutineは影響を受けません。

### ゲーム開発の立場から

Unity、Unrealが使うスレッドは**C++/C#レベルでは1:1モデル**です。`new Thread()`や`std::thread`がカーネルスレッドを直接作ります。

ただし**エンジン内部のJobシステムやTaskグラフは事実上M:Nスケジューラ**です。プログラマが数千個の「Job」を発行しても実際にはエンジンが作った数個のワーカースレッドで動きます。これはPart 13 Lock-freeと構造的解決で詳しく扱うUnity Job System設計と直結します。

---

## Part 5：3-OSスレッドAPI比較

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

POSIX標準API。内部的に`clone()`システムコールを呼び出す。公式な名前は「pthread」ですが、Linuxのmanページを見ると実際にはNPTL（glibc実装）のドキュメントです。

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

**なぜ`CreateThread`ではなく`_beginthreadex`なのか？** `CreateThread`はCRT (C Runtime Library) の初期化状態をスキップします — `errno`、`strtok`のようなスレッド別の状態が初期化されず問題が起きます。`_beginthreadex`はCRTと一緒に正しく初期化されるので、C/C++コードではこちらを使うべきです。

### macOS — pthreads + libdispatch

```c
/* POSIX方式 — Linuxと同じ */
#include <pthread.h>
/* ... */

/* libdispatch (GCD) 方式 — macOS推奨 */
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

macOSでもpthreadsはサポートされますが、Appleは**GCD (Grand Central Dispatch)**を推奨します。理由はPart 7で扱いました — スレッド寿命を手動管理しなくてよい、QoSクラスでP/Eコアを自動活用、予測可能なキュー抽象化など。

### C# — 言語レベルの抽象化

C#は上記3つのOSすべてで動きます。.NETランタイム（CLRまたはCoreCLR）がOSの違いを隠してくれます。

```csharp
using System;
using System.Threading;
using System.Threading.Tasks;

// 1) 最も原始的な方法 — ほぼ使われない
Thread t = new Thread(() => Console.WriteLine("Hello"));
t.Start();
t.Join();

// 2) ThreadPool — スレッド再利用
ThreadPool.QueueUserWorkItem(_ => Console.WriteLine("Hello"));

// 3) Task / async-await — 現代の推奨
await Task.Run(() => HeavyComputation());

// 4) Parallel — データ並列性
Parallel.For(0, 100, i => ProcessItem(i));
```

内部的には：
- Linux：libcoreclrが`pthread_create()`使用
- Windows：`CreateThread()`使用
- macOS：`pthread_create()`使用（GCDは直接使わない）

**Unityの特殊性**：Unityは`Thread`使用を制限的に推奨します。代わりにJob SystemとUniTask、Coroutineを使えと言います。理由はUnity Engine APIのほとんどが**メインスレッド以外で呼び出すとクラッシュ**するからです。（Part 13で詳述）

---

## Part 6：コンテキストスイッチ — なぜ高価か

### コンテキストスイッチとは

CPUコア1つでスレッド複数個を順繰りに実行するには、現在のスレッドの状態を保存して次のスレッドの状態を復元する必要があります。これが**コンテキストスイッチ**です。

保存すべきもの：
- **CPUレジスタ**：RAX、RBX、…、RIP（プログラムカウンタ）、RSP（スタックポインタ）、フラグレジスタ
- **浮動小数点レジスタ**：XMM、YMM、ZMM（AVX時代には数十KB）
- **MMU状態**：プロセスが変わると**ページテーブルポインタ**（x86のCR3レジスタ）の入れ替えが必要

### コンテキストスイッチの「隠れたコスト」

レジスタの保存/復元は実は**氷山の一角**です。本当に高価なのは間接効果です。

<div class="pt-ctx-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Context switch cost breakdown">
  <text x="450" y="28" text-anchor="middle" class="pc-title">コンテキストスイッチ — 直接コスト vs 隠れたコスト</text>

  <g class="pc-timeline">
    <line x1="60" y1="80" x2="840" y2="80" class="pc-line"/>
    <rect x="60" y="65" width="120" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="120" y="85" text-anchor="middle" class="pc-block-label">Thread A実行</text>

    <rect x="180" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="220" y="80" text-anchor="middle" class="pc-block-label">スイッチ</text>
    <text x="220" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="260" y="65" width="260" height="30" rx="3" class="pc-block pc-block-b"/>
    <text x="390" y="85" text-anchor="middle" class="pc-block-label">Thread B実行（キャッシュ再構築中）</text>

    <rect x="520" y="60" width="80" height="40" rx="3" class="pc-block pc-block-switch"/>
    <text x="560" y="80" text-anchor="middle" class="pc-block-label">スイッチ</text>
    <text x="560" y="95" text-anchor="middle" class="pc-block-sub">~1-10μs</text>

    <rect x="600" y="65" width="240" height="30" rx="3" class="pc-block pc-block-a"/>
    <text x="720" y="85" text-anchor="middle" class="pc-block-label">Thread A実行（キャッシュ再構築）</text>
  </g>

  <g class="pc-direct">
    <rect x="40" y="140" width="400" height="140" rx="8" class="pc-box pc-box-direct"/>
    <text x="240" y="162" text-anchor="middle" class="pc-box-heading">直接コスト（視覚的に見える部分）</text>
    <text x="55" y="190" class="pc-box-line">• レジスタ保存（~30個、~数百バイト）</text>
    <text x="55" y="210" class="pc-box-line">• SIMDレジスタ保存（AVX-512時は数KB）</text>
    <text x="55" y="230" class="pc-box-line">• カーネルに入る → スケジューラ実行 → 復帰</text>
    <text x="55" y="250" class="pc-box-line">• MMUポインタ入れ替え（プロセス間スイッチ時）</text>
    <text x="55" y="270" class="pc-box-line pc-box-sum">合計おおよそ <tspan class="pc-emph">1〜10マイクロ秒</tspan>（ハードウェア依存）</text>
  </g>

  <g class="pc-hidden">
    <rect x="460" y="140" width="400" height="200" rx="8" class="pc-box pc-box-hidden"/>
    <text x="660" y="162" text-anchor="middle" class="pc-box-heading">隠れたコスト（見えない部分）</text>
    <text x="475" y="190" class="pc-box-line">• <tspan class="pc-emph">TLB flush</tspan>：プロセス転換時にアドレス変換キャッシュが空に</text>
    <text x="475" y="205" class="pc-box-line-sub">→ 数百〜数千サイクルで再構築</text>
    <text x="475" y="225" class="pc-box-line">• <tspan class="pc-emph">CPUキャッシュ汚染</tspan>：Thread Aが使っていたL1/L2データが</text>
    <text x="475" y="240" class="pc-box-line-sub">Thread Bの実行で押し出される</text>
    <text x="475" y="260" class="pc-box-line">• <tspan class="pc-emph">分岐予測器汚染</tspan>：ブランチ履歴がごちゃ混ぜに</text>
    <text x="475" y="280" class="pc-box-line">• <tspan class="pc-emph">プリフェッチャ状態リセット</tspan></text>
    <text x="475" y="300" class="pc-box-line pc-box-sum">合計 <tspan class="pc-emph">数十マイクロ秒〜数ミリ秒</tspan>の</text>
    <text x="475" y="318" class="pc-box-line pc-box-sum">「その後の性能低下」として現れる</text>
  </g>

  <g class="pc-conclusion">
    <rect x="40" y="360" width="820" height="60" rx="8" class="pc-concl"/>
    <text x="450" y="385" text-anchor="middle" class="pc-concl-title">結論：スレッドを作りすぎるとCPUはずっとスイッチするだけで有用な仕事をしない</text>
    <text x="450" y="405" text-anchor="middle" class="pc-concl-sub">防止策：(1) スレッド数をコア数近辺に保つ、(2) Job/Taskで作業単位を細かく刻んでキューイング</text>
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

### TLBとプロセス間スイッチ

**TLB (Translation Lookaside Buffer)**はCPU内部の小さなキャッシュで、「仮想アドレス → 物理アドレス」変換結果を保存します。L1 TLBは通常**64〜128エントリ**程度です。

プロセスが変わるとCR3レジスタ（ページテーブルベース）が変わり、TLBは**完全にflush**されます（PCID/ASID最適化がなければ）。するとその後のメモリアクセスのたびにページテーブルを再度たどる必要があります。

**スレッド間スイッチはより安いです** — 同じアドレス空間を共有するのでCR3が変わらずTLB flushもありません。これが「プロセスよりスレッドが軽い」という言葉の**具体的な根拠**の1つです。

### 測定する

Linuxでは`perf stat`で測定できます：

```bash
$ perf stat -e context-switches,cpu-migrations,cache-misses -p <PID> sleep 10

Performance counter stats for process id '1234':

     12,345      context-switches
        567      cpu-migrations
 10,234,567      cache-misses
```

macOSでは**Instruments**の**System Trace**テンプレートでスレッドスケジューリングとコンテキストスイッチをマイクロ秒単位で観察できます。

Windowsでは**Xperf**または**Windows Performance Analyzer**が同じ役割。

### LaMarca & Ladnerの観察

キャッシュ親和性の観点で、[LaMarca & Ladner 1996 — "The Influence of Caches on the Performance of Heaps"](https://dl.acm.org/doi/10.1145/244851.244933)のような研究が扱ったように、アルゴリズムの**理論的複雑度だけでは**実際の性能を予測できません。同じ理由で、**スレッドを多く作るほど速くなる**という素朴な期待はキャッシュ/TLBコストのために崩れやすいです。

「最適スレッド数 = コア数」というルールはこの観察から来ます。それ以上はコンテキストスイッチが利得を食いつぶします。

---

## Part 7：ゲームエンジンの実行モデル

いよいよ理論を**ゲームエンジン**につなげます。

### Unity — メインスレッドの強い制約

Unity開発者なら「このAPIはメインスレッドでのみ呼び出せる」という警告を一度は見たことがあるでしょう。`Transform.position`、`GameObject.Instantiate()`、`Renderer.sharedMaterial`など、Unity Engine APIのほとんどがメインスレッド専用です。

**なぜか？**

Unity EngineはC++で書かれており、内部データ構造に**ロックがありません**。Unityチームが「すべてのエンジン呼び出しはメインスレッドから来る」という前提で設計したため、ロック取得オーバーヘッドをなくしました。

これは**意図的なトレードオフ**です：
- ✅ エンジン呼び出しが非常に速い（ロックなし）
- ❌ マルチスレッド活用が難しい

Unityの解決策：**Job System + Burst + Native Containers**。メインスレッドはそのままにして、**データ処理だけを並列化**する別のレイヤを提供します。（Part 13で詳述）

### Unreal Engine — Task Graph

Unreal Engineは**Task Graph**システムを使います。ゲームコードが発行した「タスク」たちが依存性DAGをなし、エンジンがワーカースレッドプールに分配します。

Unrealのワーカースレッドプール：
- **Game Thread**：ゲームロジック（Unityのメインスレッドに相当）
- **Render Thread**：レンダリングコマンドのビルド
- **RHI Thread**：GPUドライバ呼び出し
- **Worker Threads**：その他汎用作業

タスクは`ENamedThreads`で実行するスレッドを指定します。例：`ENamedThreads::GameThread`、`ENamedThreads::AnyBackgroundHiPriTask`。

### Fiber — Naughty Dogのアプローチ

[Christian GyrlingのGDC 2015講演 "Parallelizing the Naughty Dog Engine Using Fibers"](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)は**Fiber**ベースのエンジン設計で有名です。

**Fiber**は協調的ユーザーレベルスレッドです。OSが関与せずアプリケーションが自らスイッチします。カーネルスレッドが**1人の働き手**だとすれば、その働き手が持っている**複数の仕事**がFiberです。

- Fiber生成コスト：極めて安い（数ナノ秒）
- Fiberスイッチ：レジスタだけ保存/復元、カーネル介入なし
- 数千個発行可能

Naughty DogのThe Last of Us 2はこのシステムでPS4の7コアを安定的に活用しました。Fiberは**M:Nモデルの1形態**と見なせます（Fiber = ユーザースレッド、カーネルスレッド = ワーカー）。

**WindowsのFiber API**：`CreateFiber`、`SwitchToFiber`。macOS/Linuxでは`ucontext.h`の`makecontext/swapcontext`（レガシー、推奨されない）、またはBoost.Context、`libco`のようなライブラリを使わなければなりません。

### エンジン実行モデル比較

<div class="pt-engine-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Game engine execution models">
  <text x="450" y="28" text-anchor="middle" class="pe-title">主要エンジンのスレッド実行モデル</text>

  <g class="pe-unity">
    <rect x="30" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="165" y="85" text-anchor="middle" class="pe-heading">Unity</text>
    <rect x="50" y="105" width="230" height="40" rx="4" class="pe-main"/>
    <text x="165" y="128" text-anchor="middle" class="pe-main-label">Main Thread（固定）</text>
    <text x="165" y="168" text-anchor="middle" class="pe-note">大部分のEngine API</text>
    <text x="165" y="185" text-anchor="middle" class="pe-note">Transform、GameObjectなど</text>

    <line x1="50" y1="210" x2="280" y2="210" class="pe-sep"/>

    <text x="165" y="235" text-anchor="middle" class="pe-sub-label">Job System（別レイヤ）</text>
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
    <text x="165" y="370" text-anchor="middle" class="pe-key">哲学：Engine維持 + データ並列</text>
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

    <text x="450" y="290" text-anchor="middle" class="pe-note">Task Graph：依存性DAG</text>
    <text x="450" y="307" text-anchor="middle" class="pe-note">ENamedThreadsでターゲット指定</text>
    <text x="450" y="370" text-anchor="middle" class="pe-key">哲学：複数Named Thread + 汎用プール</text>
  </g>

  <g class="pe-fiber">
    <rect x="600" y="60" width="270" height="340" rx="8" class="pe-box"/>
    <text x="735" y="85" text-anchor="middle" class="pe-heading">Fiber (Naughty Dog)</text>

    <text x="735" y="115" text-anchor="middle" class="pe-sub-label">ワーカースレッド（コア数分）</text>
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

    <text x="735" y="205" text-anchor="middle" class="pe-sub-label">Fiberプール（数千個）</text>
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

    <text x="735" y="275" text-anchor="middle" class="pe-note">Job = Fiberで実行</text>
    <text x="735" y="292" text-anchor="middle" class="pe-note">協調的スイッチ、カーネル介入なし</text>
    <text x="735" y="309" text-anchor="middle" class="pe-note">待機時はFiber入れ替えだけ</text>
    <text x="735" y="370" text-anchor="middle" class="pe-key">哲学：ユーザーレベル協調スケジューリング</text>
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

## Part 8：実戦観察 — 私のスレッドはどう動いているか

理論を知った後は**実際に見ます**。3つのOSすべてがプロセスとスレッドを観察する豊富なツールを提供します。

### Linux — /proc、ps、top

Linuxではすべてが`/proc`仮想ファイルシステムに露出されます。

```bash
# 特定プロセスのスレッド一覧
$ ls /proc/<PID>/task/
1234  1235  1236  ...

# 各スレッドの状態
$ cat /proc/1234/task/1234/status
Name:   myapp
State:  R (running)
Tgid:   1234
Pid:    1234
Threads: 8

# アドレス空間マッピング
$ cat /proc/1234/maps
00400000-00452000 r-xp 00000000 08:01 12345 /usr/bin/myapp
00651000-00652000 r--p 00051000 08:01 12345 /usr/bin/myapp
7f1234000000-7f1234021000 r-xp 00000000 08:01 54321 /lib/x86_64-linux-gnu/libc.so.6
...
```

`top -H`でスレッド単位のCPU使用率を見られます。

### macOS — Activity Monitor、ps、Instruments

Activity MonitorはGUIツールですが、より精密なデータはCLIツールにあります。

```bash
# プロセスのスレッド数確認
$ ps -M <PID>

# 詳細情報
$ sample <PID> 5 -mayDie
```

**Instruments**の**System Trace**テンプレートが最も強力です。P/Eコア別の実行タイムライン、コンテキストスイッチイベント、ブロック原因まですべて見せてくれます。Apple Silicon環境で特に有用 — どのスレッドがP-coreで動いていてどのスレッドがE-coreに押しやられたかが可視化されます。

### Windows — Process Explorer、WPA

**Process Explorer** (Sysinternals) はタスクマネージャーの強化版：
- プロセスツリーの可視化
- 各プロセスのスレッド一覧 + スタックトレース
- ハンドル、DLL、メモリ詳細

**Windows Performance Analyzer (WPA)**はInstrumentsに相当。Xperfで収集したETWイベントを分析します。

### C#でスレッドを扱う — コード例

```csharp
using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;

class ThreadInspector {
    static void Main() {
        Console.WriteLine($"現在のプロセスID: {Process.GetCurrentProcess().Id}");
        Console.WriteLine($"管理スレッドID: {Thread.CurrentThread.ManagedThreadId}");
        Console.WriteLine($"CPUコア数: {Environment.ProcessorCount}");

        // スレッド生成コスト測定
        var sw = Stopwatch.StartNew();
        var threads = new Thread[100];
        for (int i = 0; i < 100; i++) {
            threads[i] = new Thread(() => Thread.Sleep(1));
            threads[i].Start();
        }
        foreach (var t in threads) t.Join();
        sw.Stop();
        Console.WriteLine($"100個スレッド生成+終了: {sw.ElapsedMilliseconds}ms");

        // ThreadPool.Queueはずっと速い
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
        Console.WriteLine($"100個ThreadPool作業: {sw.ElapsedMilliseconds}ms");
    }
}
```

実行結果（筆者マシンでおおよそ）：
```
現在のプロセスID: 12345
管理スレッドID: 1
CPUコア数: 8
100個スレッド生成+終了: 85ms
100個ThreadPool作業: 8ms
```

**10倍の差**。これがスレッドプールを使う実用的な理由です。.NETの`ThreadPool`、Javaの`ExecutorService`、C++の`std::async`すべて同じアイデアです — スレッドを再利用して生成コストを分割償還。

---

## まとめ

この回で扱ったこと：

**プロセス**：
- PCB（`task_struct`、`EPROCESS`、`proc`+`task`） — OSがプロセスを追跡する構造
- アドレス空間レイアウト：Text、Data、BSS、Heap、Stack、Kernel
- プロセス状態遷移：New、Ready、Running、Waiting、Terminated

**プロセス生成**：
- Unixの`fork() + exec()` — 2段階、Copy-on-Writeで実際には速い
- Windowsの`CreateProcess()` — 1段階、引数が多い
- macOSの`posix_spawn()` — iOS互換 + より効率的
- fork()時のCOWはハードウェアMMUサポートに基づく

**スレッド**：
- プロセス vs スレッド：アドレス空間を共有するかどうかが核心
- 共有：Text、Data、Heap、ファイルディスクリプタ
- 専用：Stack、レジスタ、TLS
- Linuxの独特な哲学：プロセスとスレッドを同じ構造体で表現（`clone()`）

**スレッドマッピングモデル**：
- 1:1（Linux NPTL、Windows）：標準、真の並列
- N:1（昔のグリーンスレッド）：ほぼ衰退
- M:N（Go goroutine、Erlang）：数百万の同時スレッド、ランタイム実装が複雑

**コンテキストスイッチ**：
- 直接コスト：レジスタ保存/復元 ~1-10μs
- 隠れたコスト：TLB flush、キャッシュ汚染、分岐予測器汚染
- プロセス間スイッチがスレッド間スイッチより高価（CR3入れ替え）
- 「スレッド数 = コア数」原則

**ゲームエンジン実行モデル**：
- Unity：Main Thread制約 + Job System（データ並列化）
- Unreal：複数Named Thread + Task Graph
- Naughty Dogエンジン：Fiberベース協調的スケジューリング

次回は**Part 9 スケジューリング** — 複数のスレッドが準備状態のとき、OSは誰にCPUを渡すでしょうか？LinuxのCFS → EEVDF、Windowsのpriority boost、macOSのQoSベーススケジューリングを見ます。ゲームのフレーム予算16.67msとpriority inversion問題も扱います。

---

## References

### 教科書
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.3 (Processes)、Ch.4 (Threads)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — `task_struct`とプロセス管理 Ch.3
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — 現代のLinuxカーネル内部
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — EPROCESS/ETHREAD詳細
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNUのtask/proc二重構造
- Butenhof — *Programming with POSIX Threads*, Addison-Wesley, 1997 — pthreadsの古典
- Stevens, Rago — *Advanced Programming in the UNIX Environment*, 3rd ed., Addison-Wesley, 2013 — fork/execの実践
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 マルチプロセッサエンジン設計

### 論文
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — [DOI](https://dl.acm.org/doi/10.1145/121132.121151) — M:Nモデルの理論的基礎
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — コンテキストスイッチの隠れたコストの測定
- Engelschall — "Portable Multithreading: The Signal Stack Trick for User-Space Thread Creation", USENIX 2000 — ユーザーレベルスレッド実装
- Kleiman, Smaalders — "The LWP Framework: Building and Debugging Mach Tasks and Threads", Mach Workshop 1990 — Machのスレッドモデル

### 公式ドキュメント
- Linux man pages — `clone(2)`、`fork(2)`、`pthread_create(3)`、`proc(5)` — [man7.org](https://man7.org/linux/man-pages/)
- Apple Developer — *Threading Programming Guide* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/Introduction/Introduction.html)
- Apple Developer — *Dispatch* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Microsoft Docs — *Processes and Threads* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/processes-and-threads)
- Microsoft Docs — *Fibers* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/fibers)
- Go Runtime — *The Go Scheduler* (Dmitry Vyukov) — [morsmachine.dk/go-scheduler](https://morsmachine.dk/go-scheduler)

### ゲーム開発 / GDC資料
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Unity Technologies — *C# Job System manual* — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Unreal Engine Documentation — *Task Graph System* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)

### ブログ / 記事
- Raymond Chen — *The Old New Thing* — Win32 CreateProcessの内部
- Linus Torvalds — comp.os.minixのスレッド関連の初期議論（1992）
- Dmitry Vyukov — *1024cores.net* — ロックフリー並行性の資料（Goスケジューラ内部を含む）
- Howard Oakley — *The Eclectic Light Company* — macOSスレッド観察テクニック

### ツール
- Linux：`ps`、`top`、`htop`、`strace`、`perf`、`ftrace`
- macOS：Activity Monitor、`ps`、`sample`、Instruments（System Trace、Time Profiler）
- Windows：Task Manager、Process Explorer、WPA、PerfView
- クロスプラットフォーム：Tracy Profiler — ゲームへの組み込みに向く
