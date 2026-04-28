---
title: "CSロードマップ第9回 — スケジューリング: OSは誰にCPUを渡すのか"
lang: ja
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
  - スケジューラの2つの決定は「誰にCPUを渡すか」と「どれだけ長く渡すか」であり、評価基準はThroughput·Latency·Fairness·Response timeです
  - LinuxはO(n) → O(1) → CFS (2007) → EEVDF (2024)へ進化しました。CFSはvruntimeが最小のスレッドをRB-treeから常に選択し、EEVDFはeligibilityとdeadlineの軸を追加してレイテンシ感応型タスクをより上手く扱います
  - Windowsは32段階のpriority + 動的boost(前景ウィンドウ、I/O完了、GUI入力)で応答性を高め、macOSは5段階のQoSで優先度·P/Eコア配置·電力管理を一度に決定します
  - 60fpsの16.67ms、120fpsの8.33msの中で入力→ロジック→物理→描画→presentが終わらなければならず、priority inversion 1回がフレームドロップの原因になります
  - Unity Job priority、Unreal TaskGraph named thread、SetThreadPriority / pthread / dispatch_qosは同じOSスケジューラの上で異なる抽象を提供しているにすぎません
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 「誰に、どれだけ」の問題

[前回](/posts/ProcessAndThread/)はプロセスとスレッドが何で、OSがそれをどう抽象化するかを見ました。ここから自然に続く問いがあります。

> **Ready状態のスレッドが100個あってコアが8個なら、OSは誰にCPUを渡すのでしょうか? そしてどれだけの時間渡すのでしょうか?**

この2つの問いに答えるのが**スケジューラ (Scheduler)** です。そしてその答えが次の2つを決めます。

- **体感応答性**: クリックして0.1秒以内に反応するか、1秒かかるか
- **フレーム安定性**: ゲームが60fpsを維持するか、17msを時々超えるか

今回扱う内容は次のとおりです。

- **スケジューリング基礎**: Preemptive vs Cooperative、Throughput·Latency·Fairness·Responseのトレードオフ
- **古典アルゴリズム**: FCFS, SJF, RR, Priority, MLFQ
- **Linux**: O(n) → O(1) → **CFS** → **EEVDF**の進化
- **Windows**: 32段階priority、dynamic boost、foreground quantum stretch
- **macOS**: **QoS**ベースのスケジューリングとApple Silicon P/Eコア配置
- **ゲームのフレーム予算**: 16.67msを埋めるものとpriority inversion
- **ゲームエンジンの優先度·アフィニティ活用**: Unity, Unreal, そしてOS APIレベル

Stage 2の核心的な問い — *「2つのスレッドが同じ変数に書き込むとなぜプログラムが時々だけ落ちるのか?」* — の「**時々**」という言葉は結局スケジューラの動作から来ています。どの順序で、どの間隔で実行が混ざるかが、見えないところで決められているという意味だからです。

---

## Part 1: スケジューリングが必要な理由

### マルチタスクの幻想

デスクトップにブラウザ、IDE、Slack、Spotify、Discordが同時に立ち上がっています。コアは8個で、プロセスとスレッドは合計で通常数百個レベルです。それでも全てが「同時に」動いているように見えます。

実際にはOSが非常に高速にスレッドを入れ替えているだけです。一つのスレッドが数ミリ秒の間コアを掴み、次のスレッドに移り、また次のスレッドに移ります。人間の認知限界(約50ms)よりはるかに短い単位で入れ替えれば、同時実行のように感じられます。

この入れ替えを決めるのが**スケジューラ**であり、2つの問いに答えます。

1. **誰に渡すか** — Ready状態のスレッドのうちどれを選んでコアに乗せるか
2. **どれだけ長く** — 一度乗せたらいつ取り上げるか、あるいは取り上げられるか

### Preemptive vs Cooperative

**プリエンプティブ (Preemptive)**: スケジューラがスレッドを強制的に取り上げられます。タイマー割り込みが周期的に発生するとカーネルが目覚めて「次は誰か」を決定します。現代のほぼ全てのOS — Linux, Windows, macOS — がこの方式です。

**協調的 (Cooperative)**: スレッドが自ら譲る(`yield`)まで動き続けます。80年代のMac、95以前のWindows、そして現在の一部のコルーチン/Fiberシステムがこの方式です。1つのスレッドが無限ループを回るとシステム全体が止まります — 昔の「Mac爆弾アイコン」の原因の1つでした。

> **ちょっと待って、これは押さえておきましょう。** ではGoroutineやasync/awaitはcooperativeですか?
>
> Goのgoroutineは**部分的にcooperative**です。関数呼び出し、チャネル演算、GCセーフポイントでのみ譲歩点が発生します。なので無限ループの中に関数呼び出しがないと他のgoroutineが飢餓状態になり得て、Go 1.14でようやく非同期プリエンプションが導入されました。async/awaitも同様に`await`地点でのみ譲ります — ただしその上で実際のスレッドはOSのプリエンプティブスケジューラで動くため、2つの層が重なっている形です。

### スケジューラの評価基準

スケジューラを設計する際に考慮すべき指標は複数あり、互いに衝突します。

| 指標 | 意味 | 誰が好むか |
|------|------|-----------|
| Throughput | 単位時間あたりの完了タスク数 | バッチ処理、ビルドサーバー |
| Turnaround time | タスク全体の所要時間 | コンパイラ、データ処理 |
| Waiting time | Readyキューで待った時間 | 全タスク |
| Response time | 入力から最初の反応まで | デスクトップ、ゲーム |
| Fairness | リソースの公平な分配 | マルチユーザーシステム |
| Predictability | 予測可能なレイテンシ | リアルタイムシステム、ゲーム |
| Energy | 電力効率 | モバイル、ノートPC |

デスクトップとモバイルは通常**Response time + Energy**を優先します。サーバーは**Throughput + Fairness**、リアルタイム/ゲームは**Predictability**を優先します。同じアルゴリズムが全ての環境で最適になり得ない理由です。

---

## Part 2: 古典スケジューリングアルゴリズム

本格的なOSスケジューラを見る前に、教科書的アルゴリズム5つを押さえておきます。現代のスケジューラは全てこれらのアイデアの組み合わせ·進化版です。

### FCFS (First-Come, First-Served)

最も単純です。到着した順に実行し、一度始まったら終わるまで取り上げません(non-preemptive)。

問題は**convoy effect**です。100秒のタスクが先に入ると、その後ろの0.1秒のタスクが全て100秒ずつ待たなければなりません。平均待ち時間が爆発します。

### SJF / SRTF (Shortest Job First / Shortest Remaining Time First)

最も短いタスクを先に実行します。**平均待ち時間が理論的に最適**であることが数学的に証明されています。

問題1: **タスクの長さを事前に知る必要があります**。実際には知り得ないので過去の実行履歴から推定します。
問題2: **starvation** — 短いタスクが続けて入ると、長いタスクは永遠に始められない可能性があります。

### Round Robin (RR)

Readyキューを循環しながら、各スレッドに**タイムクォンタム (time quantum)** だけCPUを与えます。クォンタムが終わるとキューの後ろに送り、次のスレッドに移ります。

タイムクォンタムの大きさが重要なパラメータです。

- **大きすぎると**: FCFSに近づき応答性が悪化します
- **小さすぎると**: コンテキストスイッチのオーバーヘッドが作業時間を食い潰します

典型的な値は10~100msです。Linuxは動的に決定し(CFS)、Windowsは約6ms(サーバーは12ms以上)です。

次の図は同じタスクセット(A=8ms, B=4ms, C=2ms)が同時に到着した場合のFCFSとRRの動作を比較します。

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
    <div class="sk-tl-meta">平均turnaround = (8 + 12 + 14) / 3 = 11.33ms · C 応答時間 12ms</div>
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
    <div class="sk-tl-meta">C 応答時間 4ms (FCFSの1/3) · 平均turnaround = (14 + 8 + 6) / 3 = 9.33ms</div>
  </div>

  <div class="sk-tl-legend">
    <span class="sk-tl-lg sk-tl-a"></span>A (8ms)
    <span class="sk-tl-lg sk-tl-b"></span>B (4ms)
    <span class="sk-tl-lg sk-tl-c"></span>C (2ms)
    <span class="sk-tl-note">✓ タスク完了時点</span>
  </div>

  <div class="sk-tl-foot">RRはturnaroundで常に優位とは限りませんが、短いタスクの応答性と公平性では圧倒的です。</div>

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

各スレッドに**優先度**を付け、最も高いものから実行します。同じ優先度同士はRRで処理します。

問題は再び**starvation**です。低い優先度のスレッドが永遠に動けない可能性があります。解決策の1つが**aging**で、長く待ったスレッドの優先度を徐々に上げます。

もう1つの深い問題が**priority inversion**です。低い優先度のスレッドがロックを掴んでいる間、高い優先度のスレッドがそのロックを待つと、中間優先度のスレッドが低い側を絶えずプリエンプトすることで、結果的に**高い側が中間側のせいで詰まる**逆説が生じます。この問題は次回(同期化)で本格的に扱います。

### MLFQ (Multi-Level Feedback Queue)

複数のキューを優先度別に置き、スレッドの**振る舞いを観察してキューを移します**。

基本ルールは次のとおりです。

1. 新しいスレッドは最も高いキューに入ります
2. タイムクォンタムを使い切ると一段下のキューに下がります
3. クォンタムを使い切らずI/Oで譲ると同じキューに残るか一段上がります

このルールの結果が興味深いです。

- I/O中心のタスク(対話型GUI、ゲーム入力): 短いburstの後に譲歩 → 高いキューを維持 → 速い応答
- CPU中心のタスク(コンパイラ、エンコーディング): 長いburst → 低いキューに下がる → 応答タスクを邪魔しない

アルゴリズムがタスクの本質を知らなくても**振る舞いだけを見て分類する**という発想が核心です。Windowsのdynamic boost、macOSのQoS補正、Linuxのsleeper bonusも全て本質的に同じアイデアの変形です。

> MLFQはSolarisと旧Mac OS、Windows NTが直接使い、現代のOSは表面的には別のアルゴリズム(CFS等)を使いますが内部のヒューリスティックはMLFQに似ています。

---

## Part 3: Linuxスケジューラ — O(n) → O(1) → CFS → EEVDF

Linuxスケジューラの進化は学習用としてこの上ない素材です。同じ問題を4回解き直しながら**何が間違っていて、どう直したのか**が全て公開されているからです。

### O(n)スケジューラ — 2.4以前

初期のLinuxスケジューラは1回決定するごとに**全Readyキューを巡回**しました。コアが少なくプロセスも少なかった時代には問題ありませんでしたが、サーバーが数千プロセスを起動する時代になると、スケジューラ自体がボトルネックになりました。CPUコアを追加してもロック競合が激しく性能が伸びませんでした。

### O(1)スケジューラ — 2.6 (Ingo Molnár, 2003)

**Ingo Molnár**が2002年末に導入したアルゴリズムです。

核心アイデアは次のとおりです。

- **140個の優先度キュー** (リアルタイム0~99、一般100~139)
- 各優先度ごとにactive queueとexpired queueの一対
- 次に実行するスレッドを**定数時間**で決定 — ビットマップで最も高いビットを見つけるだけだから

また**対話型タスクボーナス**をヒューリスティックとして導入しました。sleep時間が長いほど優先度を少し上げ、デスクトップの応答性を改善しました。しかしこのヒューリスティックがますます複雑になり、ボーナス計算をもてあそぶワークロードが見つかったことでコードが継ぎ接ぎだらけになりました。

### CFS — Completely Fair Scheduler (2.6.23, 2007)

**Ingo Molnárが再び**作ったスケジューラです。インスピレーションは**Con Kolivas**のRSDL (Rotating Staircase Deadline) パッチから受けたと本人が明らかにしています。

核心の発想は「公平性」を単純な回転ではなく**累積実行時間のバランス**として定義することです。全てのスレッドは自分が受け取るべき仮想のCPU時間 — `vruntime` — を持ち、スケジューラは常に**vruntimeが最小のスレッド**を選択します。

仮想実行時間(`vruntime`)は実際の実行時間(`runtime`)をweightで補正した値です。

$$
\Delta \text{vruntime} = \Delta \text{runtime} \times \frac{w_0}{w}
$$

ここで$w$はスレッドのweight(nice値で決定)で、$w_0$はnice 0の基準weight(1024)です。niceが負(優先度が高い)ほどweightが大きくなり、vruntimeがゆっくり増加するので頻繁に選択されます。

**データ構造**はRed-Black Treeで、キーはvruntimeです。最も左のノード(最小vruntime)が次の実行対象であり、挿入·削除·選択は全て$O(\log n)$です。O(1)より漸近的には遅いですが実測ではnが小さく差はほぼなく、ヒューリスティックが消えてコードがはるかにすっきりしました。

次の図はCFSの核心サイクルです。RB-treeからvruntimeが最小のスレッドを取り出して実行し、一定時間後に更新されたvruntimeで再びツリーに入れます。

<div class="sk-cfs">
  <div class="sk-cfs-title">CFS — vruntimeソートと実行サイクル</div>

  <div class="sk-cfs-rq-label">runqueue (key = vruntime, leftmostが次の実行対象)</div>
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
    <div class="sk-cfs-step sk-cfs-step-run">CPU実行<br><span>vruntime += Δ × w₀ / w_T0</span></div>
    <div class="sk-cfs-arrow">→</div>
    <div class="sk-cfs-step sk-cfs-step-back">enqueue_task<br><span>更新されたvでRB-tree再挿入</span></div>
  </div>

  <div class="sk-cfs-formula">
    Δvruntime = Δruntime × (w₀ / w) &nbsp;·&nbsp; w₀ = 1024 (nice 0) &nbsp;·&nbsp; nice ↓ → w ↑ → Δv ↓ → 頻繁に選択
  </div>
  <div class="sk-cfs-foot">結局、全スレッドのvruntimeがほぼ同じに保たれるよう自己均衡 — これが「Completely Fair」の意味です。</div>

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

CFSの核心パラメータは次のとおりです。

- `sched_latency_ns` — 1サイクルの間に全Readyスレッドを1度ずつ回そうとする目標時間 (デフォルト6ms × コア数)
- `sched_min_granularity_ns` — 1スレッドが1度に回る最小時間 (デフォルト0.75ms)
- `sched_wakeup_granularity_ns` — 起きたスレッドが現在のスレッドをプリエンプトするためのvruntime差の閾値

値は`sysctl -a | grep sched`で確認でき、コア数に応じて自動調整されます。

```c
/* 単純化したCFS選択ロジック */
struct task_struct *pick_next_task_fair(struct rq *rq) {
    struct cfs_rq *cfs_rq = &rq->cfs;
    struct sched_entity *se = __pick_first_entity(cfs_rq);  /* RB-tree leftmost */
    return container_of(se, struct task_struct, se);
}

/* tickごとに呼ばれる — vruntime更新後に再配置 */
void update_curr(struct cfs_rq *cfs_rq) {
    struct sched_entity *curr = cfs_rq->curr;
    u64 delta_exec = now - curr->exec_start;
    curr->vruntime += calc_delta_fair(delta_exec, curr);
    /* プリエンプト条件が合えばresched_curr() */
}
```

### EEVDF — Earliest Eligible Virtual Deadline First (6.6, 2023~2024)

CFSを16年間うまく使ってきましたが、1つ構造的な問題が残っていました。**latency-sensitiveなタスクの表現が難しい**ことです。

CFSはniceで*どれだけ頻繁に*回るかは調節できますが、*どれだけ速く*応答すべきかは別途指定できませんでした。2つの概念を同じ軸に縛ってしまった形です。

**Peter Zijlstra**が2023年からEEVDFをmainlineに入れ、6.6 LTSカーネルからデフォルトスケジューラに切り替わりました。学術的背景は**Stoica·Abdel-Wahab·Jeffay·Baruah**の1996年論文です。

EEVDFの2つの軸は次のとおりです。

1. **Eligibility (適格性)** — このスレッドが自分の取り分だけ十分回ったか。受け取れていなければeligibleです
2. **Virtual Deadline (仮想期限)** — eligibleなスレッドの中で期限が最も早いものを選択します

deadlineは次のように計算されます。

$$
\text{deadline} = \text{eligible time} + \frac{\text{request size}}{\text{weight}}
$$

要求サイズ(latency-niceという新しいパラメータ)が小さいほどdeadlineが早くなり、より頻繁にプリエンプトされます。つまりゲームのメインスレッドのように「**頻繁には回らない代わりに、起きたら即座に応答すべき**」タスクを正確に表現できるようになりました。

```c
/* Linux 6.6+ : niceとは別にlatency-niceを設定 */
struct sched_attr attr = {
    .sched_policy   = SCHED_NORMAL,
    .sched_nice     = 0,
    .sched_runtime  = 1   * 1000 * 1000,   /* 1ms */
    .sched_deadline = 16  * 1000 * 1000,   /* 16.67ms */
    .sched_period   = 16  * 1000 * 1000,
};
sched_setattr(pid, &attr, 0);
```

> EEVDFが導入されてもvruntimeベースの公平性はそのまま維持されます。EEVDFはCFSの代替というより**選択ポリシーの精緻化**に近く、外部インターフェース(`nice`, `cgroup cpu.weight`)もほぼそのまま使えます。

### Linuxの他のスケジューリングクラス

Linuxは1つのアルゴリズムだけを使うのではなく、**クラス**を階層に置きます。クラスごとに優先度が決まっており、上位クラスにタスクがあれば下位クラスは回りません。

| クラス | ポリシー | 用途 |
|--------|---------|------|
| stop | (カーネル専用) | CPUホットプラグ、RCUなど |
| dl | SCHED_DEADLINE | リアルタイム (period + runtime + deadline保証) |
| rt | SCHED_FIFO, SCHED_RR | リアルタイム優先度1~99 |
| fair | SCHED_NORMAL/BATCH/IDLE | 一般、CFS/EEVDF |
| idle | (全てidleの時) | swapper |

ゲームで**SCHED_FIFO/RRをむやみに使ってはいけない理由**があります。誤って使うとシステム全体を止められます — 優先度99の無限ループ1回でそのコアは以降応答不能になります。本当にRTが必要なオーディオスレッドも`SCHED_FIFO`より`dispatch_qos` / `AVAudioSession.realtime`のようにOSが提供する**上位抽象**を介してアクセスする方が安全です。

---

## Part 4: Windowsスケジューラ — Priority + Boost

Windows NTのスケジューラは**Dave Cutler**がVMSの経験を持ち込んで設計した32段階の優先度ベースシステムです。基本骨格はNT 3.1(1993)以来ほぼそのまま維持されており、時間が経つにつれヒューリスティックとハードウェア適応コードだけが厚く積み上げられました。

### 32 Priority Levels

| レベル | 意味 |
|--------|------|
| 0 | Zero page thread (メモリゼロ埋め専用) |
| 1~15 | Variable priority (一般プロセス、動的調整対象) |
| 16~31 | Real-time priority (管理者権限必要、動的調整なし) |

各プロセスには**Priority Class**があり、その中でスレッドは**Thread Priority**で微調整します。

```c
/* Windows優先度 = Process Class + Thread Priority offset */
SetPriorityClass(hProcess, NORMAL_PRIORITY_CLASS);    /* base 8 */
SetThreadPriority(hThread, THREAD_PRIORITY_NORMAL);   /* offset 0 */

/* HIGH_PRIORITY_CLASS = 13, THREAD_PRIORITY_HIGHEST = +2 → effective 15 */
/* REALTIME_PRIORITY_CLASS = 24, ... */
```

### Quantum

Windowsのタイムクォンタムは**clock interval**の倍数で測られます。通常クロックインターバルは約15ms(HPETベース)あるいは1ms(マルチメディアタイマー有効時)です。

- **Workstation**: 2 clock interval (デフォルトは約30msだが起動後の補正で通常もっと短くなる)
- **Server**: 12 clock interval (長いクォンタムでthroughput優先)

また**foregroundプロセスはquantumがstretch**されます。ユーザーが見ているウィンドウのスレッドにより長い時間を与え、応答性を高めます (コントロールパネル → システム → 詳細 → パフォーマンスオプション → 詳細の「プログラム」/「バックグラウンドサービス」トグルがこの機能をオン·オフします)。

### Priority Boost — Windowsの核心ヒューリスティック

Variable priority領域(1~15)のスレッドはさまざまなイベントで**一時的に優先度が上がります**。boostはquantumごとに1ずつ減って結局baseに戻ります。

| イベント | Boost量 |
|---------|--------|
| Disk I/O完了 | +1 |
| ネットワーク / Mailslot | +2 |
| マウス / キーボード入力 | +6 |
| サウンドカード | +8 |
| GUIスレッドがメッセージ受信 | +2 (foreground追加) |
| Semaphore wait終了 | +1 |
| Mutex/Event/Timer wait終了 | +1 |

このヒューリスティックが**Windowsの応答性を作るメカニズム**です。ユーザーがマウスを動かすとGUIスレッドが+6、キー入力も+6を受け取ります。他のCPU-boundタスクが動いていても入力反応が即座に来ます。

> **ちょっと待って、これは押さえておきましょう。** GUIスレッドのboostが+6なら、複数のウィンドウにどう優先度が分配されますか?
>
> **フォーカスを持ったウィンドウのスレッド**だけがforeground追加boostを受けます。Alt-Tabでアクティブウィンドウが変わる瞬間、boost分配も即座に変わります。Process Explorerで優先度欄をオンにして他のウィンドウをクリックしてみると、クリックされたウィンドウのスレッドの優先度数値が一瞬上がるのが確認できます。

### Realtime Priorityの罠

レベル16~31は**dynamic boostがなく**、常にその優先度で動きます。理論上は「絶対に譲らない」となります。なのでオーディオ、ビデオキャプチャ、一部のゲームスレッドが16~22程度を使います。

しかし**REALTIME_PRIORITY_CLASS (24~31)** を一般のコードで使うのは危険です。24以上の無限ループ1回がマウスカーソルまで止められます — マウス処理も結局スレッドだからです。

### NUMA, SMT, Heterogeneous

現代のWindowsスケジューラはNUMAノード、SMT(ハイパースレッディング)、Intel Thread Director(P/Eコアヒント)を全て考慮します。Windows 11で導入された**Hardware Threaded Scheduling**がThread Directorのヒントを受けてP/Eコア配置を調整します — Apple SiliconがOSレベルでやることをIntelはOS·CPU協調で解決しています。

```cpp
/* Windows: スレッドpriority調整 + affinity */
HANDLE h = GetCurrentThread();
SetThreadPriority(h, THREAD_PRIORITY_TIME_CRITICAL);  /* +15 */

/* コア0,1番にだけ固定 */
DWORD_PTR mask = 0x3;
SetThreadAffinityMask(h, mask);

/* Windows 10+ : E-core推奨ヒント */
THREAD_POWER_THROTTLING_STATE state = {};
state.Version = THREAD_POWER_THROTTLING_CURRENT_VERSION;
state.ControlMask = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
state.StateMask   = THREAD_POWER_THROTTLING_EXECUTION_SPEED;
SetThreadInformation(h, ThreadPowerThrottling, &state, sizeof(state));
```

最後の`THREAD_POWER_THROTTLING_EXECUTION_SPEED`は「このスレッドはE-coreでゆっくり動いても良い」とOSにヒントを与えるAPIです。バックグラウンドタスクに適用するとP-coreがゲームのメインスレッド用に空きます。

---

## Part 5: macOSスケジューラ — QoS + P/Eコア

macOSは外見はMachベースですが、スケジューラはBSDベースのpriorityシステムの上に**QoS (Quality of Service)** という上位抽象を載せた形です。開発者はほぼ常にQoSを介して優先度を表現し、カーネルがそれをpriority + コア配置 + 電力管理に翻訳します。

### QoS Class 5段階

| QoS Class | 意味 | 例 | マッピングpriority |
|-----------|------|-----|------------------|
| User Interactive | 即座に反応必要、ユーザーが直接見るタスク | メインスレッド、アニメーション、入力 | 47 |
| User Initiated | ユーザーが開始して結果を待つタスク | ファイルオープン、検索 | 37 |
| Default | 明示しなかった時 | 一般タスク | 31 |
| Utility | ユーザーが即座に結果を見なくてもよいタスク (進捗表示) | ダウンロード、インポート | 20 |
| Background | ユーザーに見えないタスク | インデックス、バックアップ | 5 |

このQoS値が決定するのは次のとおりです。

1. **CPU priority** — 上記表の数字
2. **CPU scheduling latency** — User Interactiveは速いwake-up、Backgroundはまとめて処理
3. **I/O priority** — ディスクキューの優先度
4. **CPUコア配置** (Apple Silicon) — User Interactive/InitiatedはP-core優先、Utility/BackgroundはE-core優先
5. **Timer coalescing** — Backgroundはタイマー発火をバッチでまとめる
6. **GPU優先度** — 一部のグラフィックスワークロードに影響

QoS 1行が**6つを同時に**決定します。

### QoS API

```c
/* C/Objective-C — スレッド自身のQoS設定 */
pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);

/* GCDキュー作成時 */
dispatch_queue_t q = dispatch_queue_create_with_target(
    "com.example.render",
    DISPATCH_QUEUE_SERIAL,
    dispatch_get_global_queue(QOS_CLASS_USER_INTERACTIVE, 0));

/* dispatch_asyncにQoS attach */
dispatch_async(q, ^{
    /* User Interactiveで実行 */
});
```

```swift
// Swift
DispatchQueue.global(qos: .userInteractive).async {
    // メインスレッドの負担を減らすための速い処理
}

// Operation API
let op = BlockOperation { /* ... */ }
op.qualityOfService = .userInitiated
queue.addOperation(op)
```

### QoS Inheritance — 優先度逆転防止

QoSは**自動伝播**します。User Interactiveキューでdispatchしたタスクが内部で他のキューにdispatch_syncすると、呼ばれる側のキューのQoSが一時的にUser Interactiveにブーストされます。このメカニズムがmacOSのpriority inversion防止の核心です。

ロックにも同じメカニズムが適用されます。`os_unfair_lock`はロック保有スレッドのQoSを待機スレッドのQoSまで引き上げます — POSIXの`PTHREAD_PRIO_INHERIT`と同じことをOSレベルで自動的に行います。

### QoS → priority → P/Eコアマッピング

次の図はQoS 1行がMach priorityとApple SiliconのP/Eコア配置にどう翻訳されるかを示します。

<div class="sk-qos">
  <div class="sk-qos-title">macOS QoS — 1行で決まる6つ</div>

  <div class="sk-qos-grid">
    <div class="sk-qos-h">QoS Class</div>
    <div class="sk-qos-h sk-qos-h-prio">Mach priority</div>
    <div class="sk-qos-h">Apple Silicon コア配置</div>

    <div class="sk-qos-cell sk-qos-ui">
      <div class="sk-qos-name">USER_INTERACTIVE</div>
      <div class="sk-qos-sub">メインスレッド / アニメーション</div>
    </div>
    <div class="sk-qos-prio">47</div>
    <div class="sk-qos-cell sk-qos-pcore-strong">
      <div class="sk-qos-name">P-core 専用</div>
      <div class="sk-qos-sub">最高性能 / 最大電力</div>
    </div>

    <div class="sk-qos-cell sk-qos-uin">
      <div class="sk-qos-name">USER_INITIATED</div>
      <div class="sk-qos-sub">ファイルオープン / 検索</div>
    </div>
    <div class="sk-qos-prio">37</div>
    <div class="sk-qos-cell sk-qos-pcore-pref">
      <div class="sk-qos-name">P-core 優先</div>
      <div class="sk-qos-sub">必要時E-core使用可</div>
    </div>

    <div class="sk-qos-cell sk-qos-def">
      <div class="sk-qos-name">DEFAULT</div>
      <div class="sk-qos-sub">未指定</div>
    </div>
    <div class="sk-qos-prio">31</div>
    <div class="sk-qos-cell sk-qos-mixed">
      <div class="sk-qos-name">P/E 混合</div>
      <div class="sk-qos-sub">負荷に応じてOSが決定</div>
    </div>

    <div class="sk-qos-cell sk-qos-ut">
      <div class="sk-qos-name">UTILITY</div>
      <div class="sk-qos-sub">進捗表示タスク</div>
    </div>
    <div class="sk-qos-prio">20</div>
    <div class="sk-qos-cell sk-qos-ecore-pref">
      <div class="sk-qos-name">E-core 優先</div>
      <div class="sk-qos-sub">電力効率優先</div>
    </div>

    <div class="sk-qos-cell sk-qos-bg">
      <div class="sk-qos-name">BACKGROUND</div>
      <div class="sk-qos-sub">インデックス / バックアップ</div>
    </div>
    <div class="sk-qos-prio">5</div>
    <div class="sk-qos-cell sk-qos-ecore-strong">
      <div class="sk-qos-name">E-core 専用 + バッチ</div>
      <div class="sk-qos-sub">timer coalescing, 低電力</div>
    </div>
  </div>

  <div class="sk-qos-foot">
    <div class="sk-qos-foot-title">QoS 1行が同時に決定するもの</div>
    <div class="sk-qos-foot-grid">
      <span>① CPU priority</span>
      <span>② scheduling latency</span>
      <span>③ I/O priority</span>
      <span>④ P/E core 配置</span>
      <span>⑤ timer coalescing</span>
      <span>⑥ GPU priority</span>
    </div>
    <div class="sk-qos-foot-note">QoSは自動伝播(inheritance)してdispatchチェーンとロック保持者までブーストされるのでpriority inversionが自動的に緩和されます。</div>
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

macOS Sonomaから追加された**Game Mode**はゲームがフルスクリーン時にOSが自動有効化するモードです。効果は次のとおりです。

- バックグラウンドタスクのQoSをより強く抑制 (Spotlightインデックス、Time Machineなど)
- ゲームプロセスへのP-core配置優先権強化
- AirPods/PS5コントローラーのオーディオ·入力ポーリングレートを2倍に増加

iOSのSustained Performance APIと発想が似ています — 「今このアプリは16.67msを逃せない状態です」とOSに知らせ、システム全体のリソース分配が調整されます。

---

## Part 6: ゲームのフレーム予算 — 16.67ms

ここまでのOS理論をゲームのコンテキストに移してみましょう。ゲーム開発者にとってスケジューリングは結局**フレーム予算**の問題です。

### フレーム予算の数学

$$
\text{frame budget} = \frac{1000\,\text{ms}}{\text{target FPS}}
$$

| Target FPS | フレーム予算 | 誰が使うか |
|------------|-------------|-----------|
| 30 | 33.33ms | コンソールシネマティック、一部モバイル |
| 60 | 16.67ms | 一般ゲーム標準 |
| 90 | 11.11ms | VR最低線 |
| 120 | 8.33ms | 高フレームPC、PS5 Performance |
| 144 | 6.94ms | 高リフレッシュレートモニター |
| 240 | 4.17ms | 競技FPS、eスポーツ |

この時間の中で次が全て終わらなければなりません。

1. **Input処理** — キーボード、マウス、ゲームパッド、タッチ
2. **Game Logic** — AI、振る舞い、状態更新
3. **Physics / Collision** — 離散シミュレーション1ステップ
4. **Animation** — ボーン行列計算、ブレンディング
5. **Particle / VFX** — パーティクル更新
6. **Render commandビルド** — ドローコールソート、カリング
7. **GPU submit** — コマンドバッファキューイング
8. **Present** — バックバッファ → 画面 (VSync待機含む)

ゲームエンジンはこれを**複数のスレッドに分散**します。1フレームの中で起こることを時間軸に描くと次のような形になります。

<div class="sk-fr">
  <div class="sk-fr-title">60fps フレーム予算 16.67ms — 誰がいつ何をするか</div>
  <div class="sk-fr-budget">硬い締切: 16.67ms以内に終わらせなければフレームドロップ</div>

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
      <div class="sk-fr-blk sk-fr-gpu"     style="left: 52%;   width: 44%;">GPU レンダリング (shadow → opaque → transparent → post)</div>
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

  <div class="sk-fr-foot">CPUメインスレッドはRenderと1フレームパイプライン — Renderが見るデータはMainのN-1フレームの結果です。</div>

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

### 1フレームパイプライン

ほとんどのエンジンは**MainとRenderを1フレームずらします**。MainがFrame Nのゲーム状態を作っている間、RenderはFrame N-1の状態でGPUに作業を投げます。2つのスレッドが同じデータを同時に触らないのでロックが減りますが、**入力遅延が1フレーム増えます**。

VRとeスポーツタイトルはこのトレードオフに非常に敏感です。NVIDIA ReflexやAMD Anti-LagのようなGPUドライバ機能がこのパイプライン深度を減らそうと試みます。

### Frame Spikeの原因 — スケジューリングの観点

フレーム時間が平均11msなのに時々23msが跳ねる現象(「frame spike」)の原因はGC、ディスクI/O、syscall以外にも**OSスケジューリング**自体がよくあります。

- **コンテキストスイッチの暴走**: スレッド数がコア数より多い時、OSが頻繁に入れ替えキャッシュ汚染でメインスレッドが遅くなる
- **Priority inversion**: メインスレッドがworkerスレッドのロックを待っている間、無関係な他のスレッドがworkerをプリエンプト
- **NUMA miss**: スレッドが別のNUMAノードに移動してキャッシュ·メモリレイテンシが爆発
- **P/Eコア降格**: macOS Game Mode未適用時、ゲームのメインスレッドが一時的にE-coreに押されてframetimeが2倍

対処法は次のとおりです。

1. メインスレッドとレンダースレッドは**固定コア (affinity)** に縛る
2. ワーカーは`コア数 - 2`程度に制限してメイン/レンダー用コアを空けておく
3. macOSは`QOS_CLASS_USER_INTERACTIVE`、Windowsは`THREAD_PRIORITY_HIGHEST`(TIME_CRITICALはなるべく避ける)を使う
4. バックグラウンドスレッドは明示的にBACKGROUND/低いpriorityに — OSがP/E分離処理

### Priority Inversion シナリオ

ゲームでよく見る形です。

```
時刻      Main (qos=USER_INTERACTIVE)         Worker (qos=UTILITY)         Other (qos=DEFAULT)
0ms       enqueue logic                        idle                          running
1ms       AI結果が必要 → mutex_lock(M) wait    M保有中                       -
2ms       (待機)                                preempted by Other            running ← 問題
... 6ms   (待機)                                preempted by Other            running
7ms       (待機)                                M解放                         -
7.1ms     unblock → 進行開始                                                  -
```

Mainが1msから7msまで止まっているがその間Workerも動けず、Otherだけが動きます。**macOSはこの場合、自動的にM保有者(Worker)のQoSをUSER_INTERACTIVEにブースト**するのでOtherがWorkerをプリエンプトできません。POSIXの`PTHREAD_PRIO_INHERIT`やWindowsのALPC自動boostも同じ種類の解決策です。次回(同期化)でさらに深く扱います。

---

## Part 7: ゲームエンジンの優先度·アフィニティ活用

### Unity — Job System priority

UnityのC# Job Systemは内部的にworkerスレッドプールを管理し(`worker count = ProcessorCount - 1`がデフォルト)、`JobHandle`を介してスケジューリングされます。

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
    h.Complete();  /* メインスレッド同期 — フレーム内に終わる必要あり */
}
```

`ScheduleBatchedJobs()`や`JobsUtility.JobWorkerMaximumCount`で個数制御が可能です。**Player Settings → Other Settings → Use job worker count**で明示的設定もできます — 8コアP-core + 4コアE-coreマシンでworkerを8に減らすとメインがP-coreをより安定して占有します。

### Unity — Application.targetFrameRate, vSyncCount

```csharp
// モバイル60fps固定
QualitySettings.vSyncCount = 0;
Application.targetFrameRate = 60;

// デスクトップモニターのリフレッシュレートに合わせる
QualitySettings.vSyncCount = 1;
Application.targetFrameRate = -1;
```

### Unreal — TaskGraphとNamed Threads

```cpp
// Unreal: 特定threadに作業を投げる
ENamedThreads::Type Target = ENamedThreads::GameThread;  /* or RenderThread, AnyThread */
FFunctionGraphTask::CreateAndDispatchWhenReady(
    [](){ /* GameThreadで実行 */ },
    TStatId(),
    nullptr,
    Target);

// 並列worker pool
ParallelFor(NumElements, [&](int32 i) {
    Process(i);
}, EParallelForFlags::None);
```

UnrealはGameThread, RenderThread, RHIThreadなど**named thread**を置いて明示的な直列化を強制します。WorkerPoolに落ちる作業は優先度キューに入り、Insightsツールで作業がどこで動いているか可視化できます。

### OS API直接呼び出し

エンジンを介さずOS APIで直接優先度を設定すべき時もあります。

```cpp
// クロスプラットフォームスレッド優先度設定 — ゲームエンジンコアでよく使うパターン
void SetThreadHighPriority(std::thread& t) {
#if defined(_WIN32)
    SetThreadPriority(t.native_handle(), THREAD_PRIORITY_HIGHEST);
#elif defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
    /* または thread_policy_set + thread_extended_policy_data_t */
#elif defined(__linux__)
    struct sched_param p;
    p.sched_priority = 0;  /* SCHED_NORMALの中ではniceで調整 */
    pthread_setschedparam(t.native_handle(), SCHED_NORMAL, &p);
    setpriority(PRIO_PROCESS, gettid_via_syscall(), -5);
#endif
}
```

### Thread Affinity — コア固定

```cpp
// Linux
cpu_set_t set;
CPU_ZERO(&set);
CPU_SET(0, &set);  /* コア0番 */
CPU_SET(1, &set);
pthread_setaffinity_np(pthread_self(), sizeof(set), &set);

// Windows
SetThreadAffinityMask(GetCurrentThread(), 0x3);

// macOS — affinity APIはdeprecated、hintのみ可能
thread_affinity_policy_data_t policy = { 1 /* tag */ };
thread_policy_set(pthread_mach_thread_np(pthread_self()),
                  THREAD_AFFINITY_POLICY,
                  (thread_policy_t)&policy, 1);
```

> **ちょっと待って、これは押さえておきましょう。** macOSはなぜhard affinityがないのでしょう?
>
> Appleの立場は一貫しています — 「**開発者はOSよりよく知らない**」。P/E異質コア、電力状態、発熱限界、コアパーキングなどをOSが総合判断するので、アプリがコアを強制的に掴むとむしろ損が大きいのです。代わりに`THREAD_AFFINITY_POLICY`で**同じキャッシュグループにまとめてくれ**というヒントは出せて、QoSでP/E選好を表現できます。

### Naughty DogのFiber事例 (再訪)

Part 8(プロセスとスレッド)でNaughty DogエンジンのFiberモデルを短く紹介しました。スケジューリングの観点で再び見ると、**Naughty DogはOSスケジューラをほぼ使いません**。

- コアごとにworkerスレッド1個ずつ、affinityでコアに固定
- 全てのスレッドはfiberプールから次のfiberを取り出して実行 (協調型)
- fiber間の切り替えは約数十ns (OSコンテキストスイッチの約数μsの100分の1)
- OSの立場からは事実上「スレッド7個をコア7個に固定しておいて起こすな」という状態

これがGDC 2015 Christian Gyrlingの発表の核心です。一般的なゲームでは過剰な設計ですが、鋭敏なフレーム一貫性が必要なAAAコンソールタイトルではOSに依存せず直接スケジュールを統制する道を選んだのです。

---

## Part 8: 実戦観察 — どのスレッドがどこで動くか

### Linux — chrt, nice, perf sched

```bash
# 現在のシェルのnice変更 (値が小さいほど高い優先度)
$ nice -n -5 ./mygame

# 実行中プロセスのポリシー/優先度確認
$ chrt -p $(pidof mygame)
pid 12345's current scheduling policy: SCHED_OTHER
pid 12345's current scheduling priority: 0

# SCHED_RRに変更 (root必要)
$ sudo chrt -r -p 50 $(pidof mygame)

# スケジューリングイベント追跡
$ sudo perf sched record -a sleep 10
$ sudo perf sched latency
# Task                       | Runtime ms | Switches | Avg delay ms | Max delay ms |
# mygame:12345               |   2543.123 |     8421 |        0.045 |        2.103 |
```

`Max delay`が16msを超えるとそのフレームでframe spikeが発生した可能性が高いです。

### macOS — Activity Monitor, Instruments, sample

Instrumentsの**System Trace**テンプレートが最も正確です。測定対象は次のとおりです。

- 各コア(P0~P7, E0~E3)でどのスレッドが動いているか
- QoSクラス別の色分け表示
- コンテキストスイッチイベントとその理由 (preemption, voluntary blockなど)
- スレッド状態遷移 (run / runnable / waiting / stopped)

```bash
# スレッド別CPU使用量
$ top -F -R -o cpu -stats pid,command,cpu,th,state

# プロセスの全スレッドのコールスタックを1秒間隔で5回サンプリング
$ sample <pid> 5 1 -mayDie

# powermetricsでコア別使用率 (P/E分離)
$ sudo powermetrics --samplers cpu_power -i 1000
```

### Windows — Process Explorer, WPA, Xperf

Process Explorerの**Threadsタブ**が見せるもの:
- 各スレッドのbase/dynamic priority欄
- 「Stack」ボタンでコールスタック確認
- 「I/O Priority」、「Memory Priority」欄 (Win10+)

**Xperf / Windows Performance Recorder**:

```powershell
# 1: プロファイル開始
wpr -start GeneralProfile -filemode

# 2: ゲーム実行、測定区間進行

# 3: 停止 → ETL収集
wpr -stop trace.etl

# 4: WPAで分析 (CPU usage by Thread, Generic Eventsなど)
wpa.exe trace.etl
```

WPAの「CPU Usage (Sampled)」と「CPU Usage (Precise)」2つのグラフの違いが重要です。Sampledは平均で、Preciseはコンテキストスイッチイベントベースなのでframe spike分析に正確です。

### 測定する習慣

スケジューラが何をしているかを推測する代わりに**測定する**習慣が重要です。Tracy Profilerはゲームエンジンに組み込んでフレーム内の全thread活動をns単位で可視化してくれます — Unity, Unrealともに統合プラグインがあります。

```cpp
// Tracy使用例
#include "Tracy.hpp"

void GameLoop() {
    ZoneScoped;  /* 関数単位で自動測定 */
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

TracyはLockableBase, FrameMarkなど同期·フレーム境界マーキングマクロも提供してpriority inversionを視覚的に捉えるのに良いです。

---

## まとめ

今回扱った内容は次のとおりです。

**スケジューリング基礎**:
- 2つの決定: 「誰に」+「どれだけ長く」
- Preemptive vs Cooperative
- 評価基準: Throughput, Latency, Fairness, Response, Energy

**古典アルゴリズム**:
- FCFS — convoy effect
- SJF — 平均待ち時間最適、starvation
- RR — quantumトレードオフ
- Priority — starvation, priority inversion予告
- MLFQ — 振る舞い観察ベースの優先度自動調整

**Linux**:
- O(n) → O(1) (Ingo Molnár, 2003)
- CFS (2007) — vruntime, RB-tree, completely fair
- EEVDF (2024) — eligibility + virtual deadline, latency-nice追加
- クラス階層: stop > dl > rt > fair > idle

**Windows**:
- 32 priority levels (Variable 1~15, Realtime 16~31)
- Foreground quantum stretch
- Dynamic boost: I/O完了 +1, Mouse/Keyboard +6, Sound +8
- Realtimeはdynamic boostなし — 危険な領域

**macOS**:
- 5 QoSクラス (User Interactive ↔ Background)
- 1行でpriority + scheduling latency + I/O priority + P/E core + timer coalescing + GPU priorityを同時決定
- QoS inheritanceでpriority inversionを自動緩和
- Game Mode (macOS 14+)

**ゲームのフレーム予算**:
- 60fps = 16.67ms, 120fps = 8.33ms, VR 90fps = 11.11ms
- 1フレームでinput → logic → physics → animation → render build → submit → present
- 1フレームパイプライン: MainとRenderの時差で並列性確保、入力遅延+1フレームのトレードオフ
- Frame spikeのスケジューリング原因: コンテキストスイッチ暴走, priority inversion, NUMA miss, P/E降格

**ゲームエンジン活用**:
- Unity Job System, Unreal TaskGraph + Named Thread
- OS API: SetThreadPriority / pthread_setschedparam / pthread_set_qos_class_self_np
- Affinity: Linux/Windowsでhard, macOSはhint only
- Naughty Dog Fiber — OSスケジューラをほぼ迂回

**観察ツール**:
- Linux: chrt, nice, perf sched
- macOS: Instruments System Trace, sample, powermetrics
- Windows: Process Explorer, WPA / Xperf
- クロスプラットフォーム: Tracy Profiler

次回は**Part 10 同期化プリミティブ**です。今回priority inversionを少しだけ言及しましたが、それに答えるにはまず**lock**の本質から見る必要があります。Mutex, Semaphore, SpinLockの違いは何で、なぜOSはfutex / SRWLock / os_unfair_lockのようなOS-specificプリミティブを別途置くのか扱います。そしてついにStage 2の核心の問い — *「2つのスレッドが同じ変数に書き込むとなぜプログラムが時々だけ落ちるのか」* — の正面からの答えに近づきます。

---

## References

### 教科書
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.5 (CPU Scheduling), Ch.6 (Synchronization)
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.4 (Process Scheduling)
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Ch.7 (Process Scheduling, O(1)時代)
- Mauerer — *Professional Linux Kernel Architecture*, Wrox, 2008 — Ch.2 (Process Management and Scheduling, CFS導入後)
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.4 (Thread Scheduling)
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.7 (Processes), Mach scheduler
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8 (Multiprocessor Game Loops)

### 論文
- Stoica, Abdel-Wahab, Jeffay, Baruah, Plaxton, Tan — "A Proportional Share Resource Allocation Algorithm for Real-Time, Time-Shared Systems", RTSS 1996 — EEVDFの理論的原典 — [DOI](https://doi.org/10.1109/REAL.1996.563725)
- Pabla — "Completely Fair Scheduler", *Linux Journal*, 2009 — CFS入門 — [linuxjournal.com](https://www.linuxjournal.com/magazine/completely-fair-scheduler)
- Molnár, Ingo — "Modular Scheduler Core and Completely Fair Scheduler [CFS]", LKMLパッチシリーズ, 2007 — CFS導入発表
- Zijlstra, Peter — "EEVDF Scheduler", LWN articles, 2023 — [lwn.net/Articles/925371](https://lwn.net/Articles/925371/)
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:Nモデル (スケジューリングの観点で再参照)
- Mogul, Borg — "The Effect of Context Switches on Cache Performance", ASPLOS 1991 — frame spike原理

### 公式ドキュメント
- Linux man pages — `sched(7)`, `chrt(1)`, `sched_setattr(2)`, `nice(1)` — [man7.org](https://man7.org/linux/man-pages/man7/sched.7.html)
- Linux Kernel Documentation — `Documentation/scheduler/sched-design-CFS.rst`, `sched-eevdf.rst`
- Microsoft Docs — *Scheduling Priorities* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)
- Microsoft Docs — *Priority Boosts* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/procthread/priority-boosts)
- Apple Developer — *Energy Efficiency Guide for Mac Apps — Prioritize Work with Quality of Service Classes* — [developer.apple.com](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-Mac/PrioritizeWorkAtTheTaskLevel.html)
- Apple Developer — *Tuning Your Code's Performance for Apple Silicon* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/tuning-your-code-s-performance-for-apple-silicon)
- Apple Developer — *Game Mode* (macOS 14+) — WWDC23 "Bring your game to Mac" セッション

### ゲーム開発 / GDC
- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — [gdcvault.com](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Acton, M. — *Data-Oriented Design and C++*, CppCon 2014 — Insomniac Gamesのキャッシュ·スケジュール思考法
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungieのスレッドモデル
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICEのJobシステム
- Unity Technologies — *C# Job System*, *Burst Compiler* マニュアル — [docs.unity3d.com](https://docs.unity3d.com/Manual/JobSystem.html)
- Epic Games — *Task Graph System*, *Async Tasks in Unreal* — [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Tracy Profiler — [github.com/wolfpld/tracy](https://github.com/wolfpld/tracy)

### ブログ / 記事
- Brendan Gregg — *Linux Performance, perf sched* — [brendangregg.com](https://www.brendangregg.com/perf.html)
- Howard Oakley — *The Eclectic Light Company* — macOS QoS / P-Eコア観察シリーズ
- Fabian Giesen — *Reading List on Multithreading and Synchronization* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Raymond Chen — *The Old New Thing* — Windows priority boost回想録
- LWN.net — *EEVDF*, *CFS group scheduling*, *sched_ext* シリーズ
- Dmitry Vyukov — *1024cores.net* — go scheduler内部

### ツール
- Linux: `chrt`, `nice`, `taskset`, `perf sched`, `ftrace`, `bpftrace`
- macOS: Instruments (System Trace, Time Profiler, CPU Counters), `sample`, `powermetrics`, `dispatch_introspection`
- Windows: Process Explorer, Windows Performance Recorder + Analyzer, ETW, PerfView
- クロスプラットフォーム: Tracy Profiler, Optick, Superluminal
