---
title: "CSロードマップ 10話 — 同期プリミティブ: Mutex はどうやって一人だけを通すのか"
lang: ja
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
  - 二つのスレッドが同じ変数を触ると時々だけ落ちる理由は、read-modify-write が原子的ではないからです。ロックは「一度に一つのスレッドだけ」をクリティカルセクションに入れる抽象であり、その抽象の底には常にハードウェアの atomic 命令 (x86 LOCK CMPXCHG、ARM LDXR/STXR) があります
  - Mutex/Semaphore/RWLock/Spinlock/CondVar は、同じ atomic の上に異なるポリシーを提供しているだけです。Linux は futex で fast path をユーザー空間に置き、slow path だけカーネルに渡します。Windows の SRWLock と macOS の os_unfair_lock も同じ思想で設計されています
  - ロックのコストは命令そのものより cache line bouncing にあります。MESI プロトコルでは一つのコアがロックを取ると他のコアの該当 line が Invalidate され、cross-socket では 10 倍以上のコスト差になります。False sharing はこれを意図せず起こす罠です
  - Unity Job System は JobHandle dependency DAG を作り read/write の衝突を防ぎ、AtomicSafetyHandle が Schedule() 時点のランタイムチェックで race を捕まえます (Editor/Development ビルドのみ)。Burst は通常の NativeArray read/write を普通の load/store にコンパイルし、明示的な Interlocked.* 呼び出しだけをハードウェア atomic に emit します。DOTS は ComponentSystem の read/write を解析してロックなしで並列化します
  - Unreal は Game/Render/RHI/Audio Thread を分離し TaskGraph + FRenderCommandFence でコマンドをキューイングします。ENQUEUE_RENDER_COMMAND には見えるロックがなく、Render Thread が FIFO 順に実行するコマンドをキューに入れます
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 「時々落ちる」の意味

Stage 2 を始めるとき、こんな問いを投げかけました。

> **スレッド二つが同じ変数に書き込むと、なぜプログラムが時々だけ落ちるのか?**

[7話 OS アーキテクチャ](/posts/OSArchitecture/)、[8話 プロセスとスレッド](/posts/ProcessAndThread/)、[9話 スケジューリング](/posts/Scheduling/)を経て、答えの半分には辿り着きました。OS が見えないところでスレッドを入れ替えていて、その入れ替えの瞬間は予測不可能 — だから「時々」という言葉が正当化されます。

今回は残り半分に答えます。**読んで・修正して・書く一行のコードが実は原子的ではない**こと、そして OS と CPU が協力してどうやって「一度に一人」という抽象を作り出すのかです。

扱う内容は次の通りです。

- **race condition の正体**: なぜ `counter++` がデータを失うのか
- **ロックの家族**: Mutex / Semaphore / RWLock / Spinlock / CondVar / Monitor / Barrier
- **ロックはどうやって作るか**: Peterson → Test-and-Set → CAS → ハードウェア atomic
- **OS 固有プリミティブ**: Linux futex、Windows SRWLock、macOS os_unfair_lock
- **ハードウェアメカニズム**: CPU キャッシュ階層、MESI、atomic が cache line ownership を掴む原理、false sharing、memory barrier
- **Unity の同期 (深掘り)**: Main Thread モデル、Job System、NativeContainer、AtomicSafetyHandle、Burst、DOTS — データはコア間でどう流れるか
- **Unreal の同期**: Game/Render/RHI Thread の分離、TaskGraph、ENQUEUE_RENDER_COMMAND の内部
- **ゲームエンジンのパターン**: lockless ring buffer、double buffer でロック回避、frame-locked sync

長く見えますが一行に縮めると次の通りです。**ロックは抽象であり、その抽象は atomic 命令の上にあり、atomic 命令は cache line ownership の上にあります。** 上から順に降りていきます。

## Part 1: race condition の正体

### 一行のミステリー

次のコードを見てみましょう。

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
    std::cout << counter << "\n";  /* 期待: 2,000,000 */
}
```

二つのスレッドが百万回ずつ 1 を足したので結果は 200 万のはずです。しかし実際に走らせると毎回違う値が出て、ほとんど常に 200 万より小さい。デスクトップではよく 1,200,000 〜 1,800,000 の間が出ます。

値が消える理由は `counter++` が一行ですが機械語では三段階だという点にあります。次の図は二つのスレッドが同じカウンターを同時に触るときに起こることを時間順に見せます。一度の増加分が消える瞬間がはっきり見えます。

<div class="sy-race">
  <div class="sy-race-title">counter++ — 三段階に分解されて race が発生する瞬間</div>

  <div class="sy-race-grid">
    <div class="sy-race-col sy-race-col-head sy-race-col-time">time →</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-t1">Thread A (Core 0)</div>
    <div class="sy-race-col sy-race-col-head sy-race-col-mem">counter (メモリ)</div>
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
    <div class="sy-race-mem sy-race-mem-change"><span class="sy-race-val">42</span><span class="sy-race-arrow">↑ A の +1</span></div>
    <div class="sy-race-cell sy-race-mod">add eax, 1<br><span>eax = 42</span></div>

    <div class="sy-race-tick">t₃</div>
    <div class="sy-race-cell sy-race-idle">·</div>
    <div class="sy-race-mem sy-race-mem-lost"><span class="sy-race-val">42</span><span class="sy-race-arrow sy-race-arrow-lost">✗ B の +1 が上書き</span></div>
    <div class="sy-race-cell sy-race-store">store [counter] ← eax<br><span>counter = 42</span></div>
  </div>

  <div class="sy-race-foot">
    期待: counter = 43 (A と B それぞれ +1)  ·  実際: counter = 42 — <strong>一度の増加が消えました</strong><br>
    原因: t₁ で B が 41 を読んだとき A の結果 (42) がまだメモリになかった — read-modify-write は原子的ではありません
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

### race condition と data race — 同じ言葉ではありません

> **ちょっと、これは押さえておきましょう。** race condition と data race は同じ言葉ですか?
>
> よく混同されますが学術的には違います。
>
> - **Data race**: 二つのスレッドが同期なしで同じメモリにアクセスし、そのうち少なくとも一つが書き込みの場合。複数の言語のメモリモデルで**明示的に定義された用語**です。**C++/Rust では起こると undefined behavior**、**Java/Go はメモリモデル内で動作が限定的に定義**されていて UB ではないですが、"correctly synchronized" でないプログラムの結果は直感と異なることがあります。
> - **Race condition**: 結果がスレッド実行順序に依存するより広い概念。たとえば二つのスレッドがそれぞれ atomic 変数で安全に通信していても、誰が先に到着するかでビジネスロジックの結果が変わるなら race condition です。
>
> つまりすべての data race は race condition を引き起こしますが、すべての race condition が data race ではありません。ロックは data race を取り除く道具で、race condition はそれより上の層の設計問題です。

### 原子性、可視性、順序 — 三つの保証

同期プリミティブが約束してくれるものは三つです。

1. **原子性 (Atomicity)**: 一つの演算が中間状態を観測されずまるごと起こる
2. **可視性 (Visibility)**: 一つのスレッドが書いた値が他のスレッドに見えることが保証される
3. **順序 (Ordering)**: プログラムが書いたコードの順序通りにメモリ演算が他のスレッドにも見える

`counter++` が壊れた原因は原子性の違反です。しかし可視性と順序も別の問題です — CPU は命令を再配置し、キャッシュは即座に同期されません。この三つは Part 12 (メモリモデルと原子演算)で本格的に扱いますが、今回ずっと背景に敷かれています。

> **ちょっと、これは押さえておきましょう。** 単純な read や単純な write も原子的ではない可能性がありますか?
>
> あります。x86/ARM では自然境界に整列された 4 バイト/8 バイトの read・write は一般的に原子的です(C++ の `std::atomic` 保証とは別)。しかし misaligned アクセス、16 バイト SIMD、32 ビット CPU の 64 ビット値などでは、一度の store が二回に分かれて起こることがあり、その間に他のコアが半分だけ見た値を読むことがあります。だから C++ では単純変数の代わりに `std::atomic<T>` を使ってコンパイラに「この変数は本当に原子的でなければならない」と伝えます。

### ロックの約束

`counter++` を壊さない最も単純な方法は次の通りです。

```cpp
std::mutex m;
/* ... */
{
    std::lock_guard<std::mutex> lk(m);
    counter++;
}
```

`lock_guard` が `m` を持っている間、他のスレッドは同じ `m` に入れません。結果は常に 200 万です。

ここから二つの疑問が自然に続きます。

1. **「一度に一人」という約束を OS はどう作り出すのか?** — Part 3
2. **その約束のコストはいくらか?** — Part 5

まずロックの種類と違いを整理します。

---

## Part 2: ロックの家族

### 一目で見る比較表

| 名前 | 本質 | 誰が解放するか | 待機方式 | 代表的な用途 |
|------|------|-------------|---------|----------|
| **Mutex** | 1 スロットロック | ロックしたスレッド | sleep | クリティカルセクション保護 |
| **Recursive Mutex** | 再入可能 Mutex | ロックしたスレッド | sleep | 同じスレッドの入れ子呼び出し |
| **Spinlock** | 1 スロットロック | ロックしたスレッド | busy-wait | 短いクリティカルセクション、カーネル |
| **Semaphore** | N スロットカウンター | 任意のスレッド | sleep | リソースプール、producer-consumer |
| **RWLock** | 複数 reader / 単一 writer | ロックしたスレッド | sleep | read 比率が高いデータ |
| **Condition Variable** | 待機 + 通知 | 起こすスレッド | sleep | 条件ベース同期 |
| **Monitor** | Mutex + CondVar の束 | (オブジェクト単位) | sleep | Java `synchronized` |
| **Barrier** | N スレッドの到着を待つ | 全員到着したら | sleep | 並列段階の同期 |
| **Latch** | 一回限りのカウントダウン | カウントが 0 になると | sleep | 初期化完了の通知 |

それぞれを簡単に押さえます。

### Mutex (Mutual Exclusion)

最も基本です。**0 または 1 の状態**を持ち、lock に成功したスレッドだけが unlock できます。すでに誰かが持っていれば、入ろうとするスレッドは wait queue に入って sleep します。

```cpp
std::mutex m;
m.lock();
// クリティカルセクション
m.unlock();
```

C++ ではほぼ常に RAII ラッパーの `std::lock_guard` や `std::unique_lock` を使います。例外が出ても unlock が保証されるからです。

> **ちょっと、これは押さえておきましょう。** reentrant、recursive、thread-safe — 混同しがちな三つの用語を整理します。
>
> - **Thread-safe**: ある関数/オブジェクトが複数のスレッドから同時に呼び出されても定義された動作を保証する。*外から見た*性質です。
> - **Reentrant**: 一つのスレッドが関数実行中に (割り込みやシグナルを通じて) 同じ関数に再び入っても安全。グローバル変数使用禁止、静的バッファ禁止などが条件です。
> - **Recursive (ロック)**: 同じスレッドがすでに持っているロックを同じスレッドがまた取れる。カウントが上がり、同じ回数だけ解放しないと本当に解放されません。
>
> Recursive mutex は便利ですが、普通「ロックの構造を間違えて設計したサイン」と見なされます。深く入った関数が自分がロックを持っているか分からない状態でまた取ろうとするなら、それはインターフェース設計でロック地点が明示されていないという意味だからです。

### Spinlock

状態は Mutex と同じですが、ロックに失敗したスレッドが **sleep せずに繰り返し試みます**。

```cpp
while (lock.test_and_set(std::memory_order_acquire)) {
    /* busy-wait */
}
```

いつ Spinlock が Mutex より良いか? **クリティカルセクションが非常に短く、コンテキストスイッチのコストが spin コストより大きいとき**です。代表的にカーネル割り込みハンドラは sleep 自体が禁止されているので spinlock しか使えません。

逆にクリティカルセクションが長かったりスレッド数がコア数より多ければ spinlock は災害です。他のスレッドが sleep すべき時間を CPU サイクルで燃やしてしまいます。

> **ちょっと、これは押さえておきましょう。** Spinlock とただの busy-wait の違いは何ですか?
>
> Spinlock は **atomic primitive の上に作られたロック**で、ただの busy-wait は普通の変数をポーリングするパターンです。普通の変数のポーリングはコンパイラがループを hoist してしまったり (`while(flag);` が無限ループにコンパイル)、他のコアの変更を永久に見られなかったりします。Spinlock は atomic + memory ordering でその二つを両方防ぎます。

### Semaphore

Dijkstra が 1965 年に提案した最も古い同期プリミティブです。**非負整数カウンター**で二つの演算を持ちます。

- **P (wait, acquire)**: カウンターが 0 なら sleep、そうでなければ 1 減少
- **V (signal, release)**: 1 増加、待機者がいれば一人起こす

Mutex は実は「初期値 1 の binary semaphore」です。ただ意味が違います — Mutex はロックしたスレッドが解放しないといけないけれど、Semaphore は誰が release してもいい。だから Semaphore はリソースプール (connection pool の空きスロット数) や producer-consumer キューの「残り枠/項目数」表現に適しています。

### Reader-Writer Lock

読みは複数、書きは一人。読みの比率が圧倒的に高いとき throughput が良くなります。

```cpp
std::shared_mutex m;
{
    std::shared_lock<std::shared_mutex> r(m);  /* 複数 reader 同時可 */
    // read
}
{
    std::unique_lock<std::shared_mutex> w(m);  /* 単独 writer */
    // write
}
```

落とし穴が二つ。第一に、RWLock 自体のコストが普通の Mutex より大きい。クリティカルセクションが非常に短いなら普通の Mutex の方が速いことがあります。第二に、**writer starvation** — reader が絶えず入ってくると writer が無限に待ちます。ほとんどの実装は writer-preferring モードを提供します。

### Condition Variable

「条件が満たされるまで待つ」を表現します。常に **Mutex とペア**で使います。

```cpp
std::mutex m;
std::condition_variable cv;
bool ready = false;

/* Waiter */
{
    std::unique_lock<std::mutex> lk(m);
    cv.wait(lk, []{ return ready; });
    // 起きた、ready == true
}

/* Notifier */
{
    std::lock_guard<std::mutex> lk(m);
    ready = true;
}
cv.notify_one();
```

`cv.wait` が「ロックを解放して sleep、起きたら再びロック取得」を原子的に実行する点が核心です。そうでないと notify が wait の直前に届いて永久に起きない **lost wakeup** 問題が発生します。

また wait の述語をラムダで渡す理由は **spurious wakeup** のためです。CV は条件を満たさなくても起きることが標準で許容されているので、起きた後で再びチェックする必要があります。

### Monitor

Mutex + Condition Variable をオブジェクト単位で束ねた抽象です。Java の `synchronized` キーワードと、すべてのオブジェクトに付いている `wait/notify` がまさにこのパターン。C# の `lock` ブロックも同じです。

```csharp
lock (gameState) {
    while (!gameState.Ready)
        Monitor.Wait(gameState);
    /* 作業 */
    Monitor.PulseAll(gameState);
}
```

`gameState` オブジェクトのヘッダーに monitor が埋め込まれているので別途 mutex を宣言しなくてもいい。便利ですがその分一つのオブジェクトにロックが強く結びついていてロック粒度の調整が難しいです。

### Barrier / Latch

**Barrier**: N 個のスレッドが全員一つの地点に到着するまで待ちます。ゲームの frame-locked 並列処理 — 「物理更新の N 個のジョブが全部終わったら次の段階に進む」 — が典型例。再利用可能 (cyclic barrier)。

**Latch**: カウンターが 0 になるまで全員待ちます。一回限り。初期化が終わったことをすべての開始スレッドに一度に知らせるときに使います。

### まとめ: どのロックをいつ使うか

次のマトリクスはロックを二つの軸 — クリティカルセクションの長さ (横) と read/write 比率 (縦) — に並べて適切なプリミティブを示します。同じ atomic の上にポリシーだけ異なる道具たちがどんな状況で自分の場所を見つけるかが一目で分かります。

<div class="sy-locks">
  <div class="sy-locks-title">状況別に適切な同期プリミティブ</div>

  <div class="sy-locks-axis-y">read/write バランス</div>

  <div class="sy-locks-grid">
    <div class="sy-locks-corner"></div>
    <div class="sy-locks-xh">短い (&lt; 1μs)</div>
    <div class="sy-locks-xh">中 (1〜100μs)</div>
    <div class="sy-locks-xh">長い / I/O を含む</div>

    <div class="sy-locks-yh">read ≈ write</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Spinlock</div>
      <div class="sy-locks-note">カーネル・割り込み限定。ユーザーはほぼ禁止</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex</div>
      <div class="sy-locks-note">基本選択。futex/SRWLock/os_unfair_lock</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Mutex + CondVar</div>
      <div class="sy-locks-note">長い待機は sleep + 条件通知</div>
    </div>

    <div class="sy-locks-yh">read ≫ write</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Mutex / atomic</div>
      <div class="sy-locks-note">RWLock のオーバーヘッドが大きいことがある</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RWLock (Shared)</div>
      <div class="sy-locks-note">writer starvation に注意</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">RCU / Seqlock</div>
      <div class="sy-locks-note">読みは lock-free、書きは保護</div>
    </div>

    <div class="sy-locks-yh">リソースプール / Queue</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">Semaphore</div>
      <div class="sy-locks-note">スロット数 = カウンター</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Semaphore + CondVar</div>
      <div class="sy-locks-note">producer-consumer の標準</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Lock-free Queue</div>
      <div class="sy-locks-note">SPSC ring / Vyukov MPSC</div>
    </div>

    <div class="sy-locks-yh">段階同期</div>
    <div class="sy-locks-cell sy-locks-cell-warm">
      <div class="sy-locks-name">atomic flag</div>
      <div class="sy-locks-note">短い phase 通知</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">Barrier / Latch</div>
      <div class="sy-locks-note">N スレッド一斉 sync</div>
    </div>
    <div class="sy-locks-cell sy-locks-cell-good">
      <div class="sy-locks-name">JobHandle / Fence</div>
      <div class="sy-locks-note">エンジン単位の dependency</div>
    </div>
  </div>

  <div class="sy-locks-legend">
    <span class="sy-locks-lg sy-locks-cell-good"></span>適切
    <span class="sy-locks-lg sy-locks-cell-warm"></span>可能だが注意 (オーバーヘッド/禁忌)
    <span class="sy-locks-foot">— すべてのセルの底には同じ atomic CAS があります。ポリシーだけが変わります。</span>
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

ここまでがユーザーから見えるインターフェース層です。次は一層下に降りて、OS とコンパイラがこの約束をどう作り出すかを見ます。

---

## Part 3: ロックはどうやって作るか

### 試み 1 — ソフトウェアだけで可能か?

まず最も素朴な試みから見ます。二つのスレッドのためのロックを変数一つで作れるでしょうか?

```c
int locked = 0;

void lock() {
    while (locked) ;       /* spin */
    locked = 1;            /* 取った! */
}
```

明らかに壊れます。`while(locked)` を通過した二つのスレッドが同時に `locked = 1` を実行すると両方がクリティカルセクションに入ります。read と write の間が空いているので race が発生します。

### Peterson のアルゴリズム (1981)

ソフトウェアだけでロックを作ることはできます。二つのスレッドに限定すれば、**Gary Peterson** が 1981 年に示したアルゴリズムが最もエレガントです。

<div class="sy-pt">
  <div class="sy-pt-title">Peterson アルゴリズム — 二つのスレッドが同時に進入を試みる</div>

  <div class="sy-pt-vars">
    <span class="sy-pt-tag">共有変数</span>
    <code>flag[2] = {0, 0}</code>
    <code>turn = 0</code>
    <span class="sy-pt-meaning">flag[i] = 「私は入りたい」、turn = 「次に譲る対象」</span>
  </div>

  <div class="sy-pt-cols">
    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-a">Thread A (self=0)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[0] = 1</code><span class="sy-pt-cmt">入りたい意思を宣言</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 1</code><span class="sy-pt-cmt">B に譲る</span></div>
      <div class="sy-pt-step sy-pt-pass"><span class="sy-pt-num">3</span><code>while (flag[1] &amp;&amp; turn == 1) ;</code><span class="sy-pt-cmt">B も入りたく、turn が B なら待機</span></div>
      <div class="sy-pt-step sy-pt-enter"><span class="sy-pt-num">4</span><strong>クリティカルセクション進入</strong></div>
      <div class="sy-pt-step"><span class="sy-pt-num">5</span><code>flag[0] = 0</code><span class="sy-pt-cmt">unlock</span></div>
    </div>

    <div class="sy-pt-col">
      <div class="sy-pt-head sy-pt-head-b">Thread B (self=1)</div>
      <div class="sy-pt-step"><span class="sy-pt-num">1</span><code>flag[1] = 1</code><span class="sy-pt-cmt">入りたい意思を宣言</span></div>
      <div class="sy-pt-step"><span class="sy-pt-num">2</span><code>turn = 0</code><span class="sy-pt-cmt">A に譲る</span></div>
      <div class="sy-pt-step sy-pt-wait"><span class="sy-pt-num">3</span><code>while (flag[0] &amp;&amp; turn == 0) ;</code><span class="sy-pt-cmt">spinning ...</span></div>
      <div class="sy-pt-step sy-pt-idle"><span class="sy-pt-num">4</span>(A が unlock するまで待機)</div>
      <div class="sy-pt-step sy-pt-enter-late"><span class="sy-pt-num">5</span><strong>その後クリティカルセクション進入</strong></div>
    </div>
  </div>

  <div class="sy-pt-key">
    <strong>なぜ一人だけが通るのか?</strong> 二つのスレッドが step 2 をほぼ同時に実行しても <code>turn</code> はたった一つの値しか持てません (最後の write が勝ちます)。その値が 0 なら A が譲ったことになって B が通り、1 なら逆 — どちらにせよ正確に一人だけが step 3 の while を抜けます。
  </div>

  <div class="sy-pt-warn">
    <strong>しかし実際の CPU では動作しません。</strong> step 1 と step 2 が他のコアから見て順序が入れ替わって見えることがあり (memory reorder)、store buffer のせいで自分のコアの書き込みが他のコアに即座に見えないからです。結局 memory barrier — ハードウェア命令 — が必要です。
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

原理は**「私が譲る」という意思表示と「今誰の順番か」という合意**を組み合わせたものです。二つのスレッドが同時に入ってきても `turn` 変数はたった一つの値しか持てないので一人だけが通ります。

このアルゴリズムは本当に動くのか? **理論的にはそうですが、実際の CPU ではそうではありません。**

理由は二つ。

1. **CPU の命令再配置**: `flag[self] = 1; turn = other;` がメモリに到達する順序がコードの順序と異なることがあります。他のコアでは `turn` の変更を先に見て `flag[self]` はまだ 0 に見えることがあります。
2. **Store buffer**: 各コアが持つ書き込みバッファのせいで自分が書いた値が他のコアに即座に見えません。

この二つの問題を解決するには **memory barrier** が必要ですが、barrier は事実上ハードウェア命令です。結局ソフトウェアだけでは無理です。

### 試み 2 — ハードウェアが助ける

根本的に必要なのは**「読んで・比較して・書く」を原子的に行う単一命令**です。CPU メーカーがこのために特別な命令を提供します。最もよく使われる三つの家族を一つの図にまとめると次の通り。

<div class="sy-cas">
  <div class="sy-cas-title">ハードウェア atomic primitive — 三つの家族</div>

  <div class="sy-cas-fams">

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Test-and-Set (TAS)</div>
      <div class="sy-cas-fsub">「値を書いて以前の値を得る」</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">読み<br><span>old = *X</span></div>
        <div class="sy-cas-amp">∧</div>
        <div class="sy-cas-box sy-cas-out">書き<br><span>*X = true</span></div>
      </div>
      <div class="sy-cas-bracket">一度に — 分離不可</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>XCHG</code> · <code>LOCK BTS</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> ペア
      </div>
    </div>

    <div class="sy-cas-fam sy-cas-fam-hi">
      <div class="sy-cas-fname">Compare-and-Swap (CAS)</div>
      <div class="sy-cas-fsub">「期待値と同じなら新しい値に変える」</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">読み<br><span>cur = *X</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-cmp">比較<br><span>cur == exp ?</span></div>
        <div class="sy-cas-amp">→</div>
        <div class="sy-cas-box sy-cas-out">条件付き書き<br><span>*X = desired</span></div>
      </div>
      <div class="sy-cas-bracket">成功/失敗 boolean を返す</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK CMPXCHG</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDXR / STXR</code> · <code>CAS</code> (v8.1+)
      </div>
    </div>

    <div class="sy-cas-fam">
      <div class="sy-cas-fname">Fetch-and-Add (FAA)</div>
      <div class="sy-cas-fsub">「足して以前の値を得る」</div>
      <div class="sy-cas-flow">
        <div class="sy-cas-box sy-cas-in">読み<br><span>old = *X</span></div>
        <div class="sy-cas-amp">+</div>
        <div class="sy-cas-box sy-cas-out">足して書き<br><span>*X = old + δ</span></div>
      </div>
      <div class="sy-cas-bracket">old を返す</div>
      <div class="sy-cas-isa">
        <span class="sy-cas-arch">x86</span><code>LOCK XADD</code><br>
        <span class="sy-cas-arch">ARM</span><code>LDADD</code> (v8.1+)
      </div>
    </div>

  </div>

  <div class="sy-cas-sep">↓ この上に spinlock を作ると</div>

  <div class="sy-cas-spin">
    <div class="sy-cas-spin-title">CAS 一回が作る Spinlock の一サイクル</div>
    <div class="sy-cas-spin-flow">
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">1</div>
        <div class="sy-cas-step-name">acquire 試行</div>
        <div class="sy-cas-step-desc"><code>CAS(lock, 0, 1)</code></div>
      </div>
      <div class="sy-cas-spin-branch">
        <div class="sy-cas-branch sy-cas-branch-ok">
          <div class="sy-cas-branch-h">✓ 成功</div>
          <div class="sy-cas-branch-d">lock = 1<br>クリティカルセクション進入</div>
        </div>
        <div class="sy-cas-branch sy-cas-branch-no">
          <div class="sy-cas-branch-h">✗ 失敗 (すでに 1)</div>
          <div class="sy-cas-branch-d">PAUSE ヒント<br>再試行</div>
        </div>
      </div>
      <div class="sy-cas-spin-step">
        <div class="sy-cas-step-num">2</div>
        <div class="sy-cas-step-name">クリティカルセクション</div>
        <div class="sy-cas-step-desc">acquire-release<br>memory barrier 含む</div>
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

CAS が最も一般的で強力です。**lock-free データ構造の基本単位**になるからです (Part 13 で本格的に)。TAS は spinlock のような単純な mutual exclusion に十分で、FAA はカウンター増加や ticket lock の核心演算です。

> **ちょっと、これは押さえておきましょう。** 「CAS」と「atomic」は同じ言葉ですか?
>
> 違います。**Atomic operation** は「一段階で分離不可能に起こるすべての演算」の一般概念です。**CAS は atomic operation の一種**にすぎず、兄弟として TAS、FAA、LL/SC、atomic load/store があります。C++ の `std::atomic<T>` はこの命令を抽象化したインターフェースで、`compare_exchange_weak` が CAS、`fetch_add` が FAA に対応します。

### Spinlock の CAS ベース実装

CAS で spinlock を作ると次のようになります。

```cpp
struct Spinlock {
    std::atomic<bool> locked{false};

    void acquire() {
        bool expected = false;
        while (!locked.compare_exchange_weak(
                expected, true,
                std::memory_order_acquire)) {
            expected = false;       /* CAS 失敗時に変形される */
            while (locked.load(std::memory_order_relaxed))
                __builtin_ia32_pause();  /* x86 PAUSE ヒント */
        }
    }

    void release() {
        locked.store(false, std::memory_order_release);
    }
};
```

ここで二つ押さえておくべきことがあります。

1. **acquire / release メモリ順序**: ロックを取った後に書いた値が、他のスレッドがロックを再び取った後にも見えるよう保証します。詳細は Part 12。
2. **`PAUSE` ヒント**: x86 は spin ループに PAUSE を挟むと電力消費を減らしメモリ順序違反のペナルティを避けます。ARM では `YIELD` が同様の役割。

### Spin か Sleep か — 決定ルール

同じ atomic の上にポリシーだけ変えれば spinlock と mutex ができます。どちらを使うかはクリティカルセクションの長さとコンテキストスイッチコストの比較です。

| 条件 | Spin が有利 | Sleep が有利 |
|------|-----------|-----------|
| クリティカルセクションの長さ | < 1μs | > 10μs |
| スレッド数 vs コア数 | ≤ | > |
| 環境 | 割り込みハンドラ、RT カーネル | ユーザー空間の一般コード |

現代の mutex 実装はそのため **adaptive** です。短く spin した後でも取れなければ sleep に切り替えます。Linux glibc の NPTL もそうですし、Windows の SRWLock もそうです。

---

## Part 4: OS 固有プリミティブ

### Linux futex — fast userspace mutex (2002)

`pthread_mutex_lock` を呼ぶたびにシステムコールが起こる必要があるか? ロックが空いているならわざわざカーネルを呼ぶ理由がない。この洞察から出てきたのが **futex** です。

Hubertus Franke、Rusty Russell、Matthew Kirkwood が 2002 年に Linux に導入しました。核心アイデア:

よく引用されるのは **3-state mutex 実装例** (0 unlocked、1 locked-no-waiters、2 locked-with-waiters) です。ただしこの状態エンコーディングは**ユーザー空間ライブラリのポリシー選択**であって futex そのものの意味ではありません — futex はカーネルが提供する一般的な **wait/wake 構成要素**であり、その上に mutex/semaphore/condvar などの抽象がそれぞれ異なる状態エンコーディングで作られます。上の実装は unlock 時に待機者の有無を知って wake システムコールを呼ぶか決めるため、二ビットが必要です。

futex 一回のコスト — ロックが空いているとき — は約 10〜20ns で、システムコール (〜数百 ns) の 1/10 以下です。これが Linux の**ほとんどの user-space blocking lock 実装** (`pthread_mutex`、`sem_t`、glibc の `std::mutex` など) が futex の上に作られた理由です。

<div class="sy-futex">
  <div class="sy-futex-title">futex — fast path vs slow path の分岐</div>

  <div class="sy-futex-states">
    <span class="sy-futex-stag">状態</span>
    <span class="sy-futex-st sy-futex-st-0">0 unlocked</span>
    <span class="sy-futex-st sy-futex-st-1">1 locked · 待機者なし</span>
    <span class="sy-futex-st sy-futex-st-2">2 locked · 待機者あり</span>
  </div>

  <div class="sy-futex-cols">
    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_lock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>CAS(m, 0, 1)</code></div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ 成功: lock 取得、終了</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ 失敗: 誰かがすでに保持</div>
        </div>
        <div class="sy-futex-cost">~10ns · CAS 1 回 · syscall なし</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>atomic_xchg(m, 2)</code> · 状態を「待機者あり」に</div>
        <div class="sy-futex-line"><code>futex_wait(m, 2)</code> syscall · カーネル wait queue に入って sleep</div>
        <div class="sy-futex-cost">~数百 ns + context switch · sleep 時間追加</div>
      </div>
    </div>

    <div class="sy-futex-col">
      <div class="sy-futex-ch">mutex_unlock()</div>
      <div class="sy-futex-step sy-futex-step-fast">
        <div class="sy-futex-zone">USER SPACE — fast path</div>
        <div class="sy-futex-line"><code>fetch_sub(m, 1)</code> → 以前の値を確認</div>
        <div class="sy-futex-branch">
          <div class="sy-futex-arrow sy-futex-arrow-ok">→ 以前が 1: 待機者なし、終了</div>
          <div class="sy-futex-arrow sy-futex-arrow-no">→ 以前が 2: 待機者あり</div>
        </div>
        <div class="sy-futex-cost">~10ns · atomic 1 回 · syscall なし</div>
      </div>
      <div class="sy-futex-step sy-futex-step-slow">
        <div class="sy-futex-zone sy-futex-zone-kernel">KERNEL — slow path</div>
        <div class="sy-futex-line"><code>store(m, 0)</code> · unlock</div>
        <div class="sy-futex-line"><code>futex_wake(m, 1)</code> syscall · 待機者を一人起こす</div>
        <div class="sy-futex-cost">~数百 ns · 起こされたスレッドは再び lock 試行</div>
      </div>
    </div>
  </div>

  <div class="sy-futex-key">
    <strong>核心の洞察</strong> — 90%+ の時間ロックが空いているという統計的事実に依存します。ロックが空いていればすべてが user space の atomic 命令一回で終わり — kernel を呼ぶコストを避けます。競合があるときだけ kernel に入って wait queue に登録します。
    Windows SRWLock も、macOS os_unfair_lock も同じ思想の変形です。
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

> **ちょっと、これは押さえておきましょう。** 「fast path」と「slow path」は一般的にどう分かれますか?
>
> ロック実装で fast path は**競合がないときに可能な限り早く終える経路**で、slow path は**競合があるときに補助作業が必要な経路**です。ほぼすべての現代の同期プリミティブ — futex、SRWLock、os_unfair_lock、parking_lot — がこのパターンに従います。Fast path は CAS 1〜2 個、slow path はカーネル進入や別途 wait queue 管理。90% 以上の時間ロックが空いているという統計的事実に依存する設計です。

### Windows SRWLock と CRITICAL_SECTION

Windows には同期プリミティブが複数世代あり、時期ごとにトレードオフが違います。

**Mutex (カーネルオブジェクト)**: 最も古い。ハンドルベースでプロセス間共有が可能。しかしすべての lock/unlock がシステムコールで遅い。〜数百 ns。

**CRITICAL_SECTION**: NT 4 時代 (1996) に導入。ユーザー空間 atomic で fast path を処理し、待機時のみ `WaitForSingleObject` カーネルイベントで sleep。futex より 5 年早い同じ思想。欠点は構造体が重い (約 40 バイト、内部カウンター・ハンドル含む) こととプロセス内部でのみ動作すること。

**SRWLock (Slim Reader/Writer Lock)**: Windows Vista (2007) 導入。8 バイトポインタサイズ、futex とほぼ同じ fast/slow path 設計、RWLock 意味。初期化関数も不要 (`= SRWLOCK_INIT`)。新規コードではほぼ常に SRWLock が答え。

```c
SRWLOCK lock = SRWLOCK_INIT;

AcquireSRWLockExclusive(&lock);   /* writer lock */
/* ... */
ReleaseSRWLockExclusive(&lock);

AcquireSRWLockShared(&lock);      /* reader lock */
/* ... */
ReleaseSRWLockShared(&lock);
```

内部的に SRWLock は 8 バイト atomic 一つに次をパッキング: locked bit、waiting bit、waking bit、reader count、そして wait queue head pointer の上位ビット。CAS 一回で fast path を処理するためのビットパッキングです。

**Condition Variable**: SRWLock とペアの `CONDITION_VARIABLE` も同時期に導入。

> **ちょっと、これは押さえておきましょう。** `CRITICAL_SECTION` と `Mutex` のどちらを使うべきか?
>
> 単一プロセス内で新規コードなら **SRWLock** が答え。より軽量で RWLock までできます。`CRITICAL_SECTION` は古いコードとの互換のためだけに、`Mutex` (カーネルオブジェクト) はプロセス間同期や named mutex が必要なときだけ使います。

### macOS os_unfair_lock とその家族

macOS は BSD pthread ベースですが、追加で Mach ポートベースの同期と Apple 固有のロックがあります。

**pthread_mutex_t**: 標準。内部的に Mach `__ulock_wait` / `__ulock_wake` システムコールを使います (Linux futex の macOS 等価物)。fast/slow path 構造は同一。

**os_unfair_lock**: macOS 10.12 / iOS 10 (2016) 導入。**`OSSpinLock` を置き換えるため**に作られました。OSSpinLock は priority inversion に脆弱でした — 低優先度スレッドがロックを持ったまま P/E コアに降格されると高優先度スレッドが永遠に spin することがあります。

```c
os_unfair_lock lock = OS_UNFAIR_LOCK_INIT;

os_unfair_lock_lock(&lock);
/* ... */
os_unfair_lock_unlock(&lock);
```

名前の "unfair" は意図的です。**FIFO 公平性を放棄し**代わりにロックを持っているスレッドの情報をロックに記録しておきます。そのため priority inversion が検知されると持っているスレッドの priority を**一時的に上げます (priority donation)**。これを可能にしたのが 4 バイト atomic に owner thread ID をエンコードした設計です。

> os_unfair_lock の 4 バイトの中には owner thread の mach thread port id が入っています。これによってカーネルは contended path で誰がロックを持っているか分かり、QoS 継承 (boost) を自動実行します。9 話で扱った QoS と直接つながります。

**OSSpinLock**: deprecated。新規コードでは絶対に使ってはいけません。

**NSLock / @synchronized**: Objective-C のオブジェクト単位 monitor。すべての NSObject が潜在的にロックを持てます。Java の `synchronized` と同じ思想ですがコストが大きい。

**Dispatch semaphore (`dispatch_semaphore_t`)**: GCD のカウンティング semaphore。P/V 意味。

### 三つの OS の同じ思想

| OS | uncontended (fast) | contended (slow) | 推奨新規ロック |
|------|------------------|------------------|--------------|
| Linux | atomic CAS | `futex(WAIT/WAKE)` syscall | `pthread_mutex`、`std::mutex` |
| Windows | atomic CAS | `NtWaitForAlertByThreadId` (Win8+) | `SRWLock` |
| macOS | atomic CAS | `__ulock_wait/wake` syscall | `os_unfair_lock` |

三つの OS が異なる名前の異なる API を提供しますが共通点は次の通り。

1. fast path は user space atomic 一二個
2. slow path だけ kernel wait queue
3. RWLock が必要ならビットパッキングで reader count 追加

ただし **priority inheritance/donation の処理は OS ごとに違います。** macOS `os_unfair_lock` は 4 バイトの中に owner thread ID をエンコードしてカーネルが boost 対象を即座に分かるようにし、Linux は別途 `PI_futex` モード (PTHREAD_PRIO_INHERIT 属性で活性化) でのみ owner を記録して RT 作業の priority inheritance をサポートします。Windows の SRWLock と CRITICAL_SECTION は基本的に priority inheritance を保証しません — この部分は Part 11 (デッドロックと priority inversion) で再び扱います。

C++ 標準ライブラリ、Rust `parking_lot`、Java `j.u.c.locks` はすべてこの OS API の上に作られます。

---

## Part 5: ハードウェアがロックを実現する方法

ここまで「CAS は atomic に起こる」と言ってきました。しかしそれは実際どうやって可能か? **複数のコアが同時に同じアドレスを触るとき、一つのコアだけを通すメカニズム**が CPU 内部になければいけません。そのメカニズムが **cache coherence** で、その上で atomic 命令が動きます。

### CPU キャッシュ階層 — なぜ複数段階か

現代の CPU はメモリに直接アクセスしません。コアと DRAM の間に複数段階のキャッシュがあります。

| 階層 | サイズ (コアごと/共有) | アクセス時間 | 誰が持つか |
|------|------------------|---------|-----------|
| Register | ~32 個 | 0 cycle | コア単独 |
| L1 D-cache | 32~48KB | 4~5 cycle | コア単独 |
| L1 I-cache | 32~48KB | 4~5 cycle | コア単独 |
| L2 | 256KB~1MB | 12~15 cycle | コア単独 (通常) |
| L3 (LLC) | 4~64MB | 30~50 cycle | 同じソケットのコア間で共有 |
| DRAM | GB | 100~300 cycle (200~400ns) | 全員 |
| 別ソケットの DRAM | GB | 200~600 cycle | NUMA |

キャッシュの単位は **cache line** で、ほぼすべての現代 x86/ARM で **64 バイト**です。CPU がメモリから 1 バイトを読んでも 64 バイトをまるごと取ってきます。

> **ちょっと、これは押さえておきましょう。** コアがそれぞれ L1 を持つと、同じ変数の値がコアごとに違うことがあり得ませんか?
>
> まさにその問題を解くのが **cache coherence protocol** です。複数のコアが同じ cache line のコピーを持てますが、一つのコアがその line に書く瞬間、他のコアのコピーを無効化したり更新したりして矛盾を防ぎます。最も広く使われるプロトコルが MESI (Intel) とその変種 MOESI (AMD) です。

### MESI プロトコル

各 cache line は 4 つの状態のいずれかを持ちます。

| 状態 | 意味 | 他のコア |
|------|------|---------|
| **M (Modified)** | このコアだけが持っていて、DRAM と異なる (dirty) | コピーなし |
| **E (Exclusive)** | このコアだけが持っていて、DRAM と同じ (clean) | コピーなし |
| **S (Shared)** | 複数のコアが同じ値を持っている (clean) | 同じ値あり |
| **I (Invalid)** | このコアのコピーは無効 | (他にある) |

核心ルールはたった一つ。

> **一つの cache line が M 状態ならそのコアだけがその line を持ちます。**

書き込みが起こると他のコアのその line はすべて I に落ちます。これを可能にするためコア同士は **coherence message** をやり取りします。

| メッセージ | 意味 |
|---------|------|
| Read | 「この line をください (読み込み目的)」 |
| Read-for-Ownership (RFO) | 「この line をください (書き込み目的)」 — 他のコアのコピー無効化要求 |
| Invalidate | 「この line のコピーを捨ててください」 |
| Read-Response | 「ここにその line があります」 |

一行に要約すると — **一つの cache line が誰のもので、誰のコピーがまだ有効かを追跡する 4 状態 (M/E/S/I) 機械**です。一つのコアが line に書くと他のコピーはすべて I に落ち、これが atomic 命令が「一度に一人」を作り出すメカニズムです。

次の可視化は一つの cache line が二つのコアの間を行き来する様子を 7 ステップで追跡します。深く入る付録なので折りたたんでおきました — 必要なときに開いてください。

<details class="sy-fold" markdown="1">
<summary>▸ MESI 状態遷移を詳しく見る — 一つの cache line がコア間を移動するすべての段階</summary>

<div class="sy-mesi">
  <div class="sy-mesi-title">一つの cache line の MESI 遷移 — 二つのコアが同じ line にアクセスするとき</div>

  <div class="sy-mesi-states">
    <span class="sy-mesi-stag">状態</span>
    <span class="sy-mesi-state sy-mesi-m">M Modified</span>
    <span class="sy-mesi-state sy-mesi-e">E Exclusive</span>
    <span class="sy-mesi-state sy-mesi-s">S Shared</span>
    <span class="sy-mesi-state sy-mesi-i">I Invalid</span>
  </div>

  <div class="sy-mesi-grid">
    <div class="sy-mesi-h">イベント</div>
    <div class="sy-mesi-h sy-mesi-h-c0">Core 0 line 状態</div>
    <div class="sy-mesi-h sy-mesi-h-c1">Core 1 line 状態</div>
    <div class="sy-mesi-h">coherence メッセージ</div>

    <div class="sy-mesi-evt"><strong>t₀</strong> 初期: 誰も持っていない</div>
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
    <div class="sy-mesi-msg">ローカル — メッセージなし (すでに Exclusive)</div>

    <div class="sy-mesi-evt"><strong>t₃</strong> Core 1 read 試行</div>
    <div class="sy-mesi-cell sy-mesi-s">M → S</div>
    <div class="sy-mesi-cell sy-mesi-s">I → S</div>
    <div class="sy-mesi-msg"><code>Read</code> → Core 0 が dirty data 供給、DRAM 更新</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₄</strong> Core 1 write (atomic CAS) — bouncing 開始</div>
    <div class="sy-mesi-cell sy-mesi-i">S → I</div>
    <div class="sy-mesi-cell sy-mesi-m">S → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO (Read-for-Ownership)</code> → Core 0 のコピーを無効化</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₅</strong> Core 0 が再び write</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → Core 1 から dirty data を取って Core 1 を無効化</div>

    <div class="sy-mesi-evt sy-mesi-evt-hi"><strong>t₆</strong> Core 1 が再び write</div>
    <div class="sy-mesi-cell sy-mesi-i">M → I</div>
    <div class="sy-mesi-cell sy-mesi-m">I → M</div>
    <div class="sy-mesi-msg sy-mesi-msg-hi"><code>RFO</code> → また ping-pong</div>
  </div>

  <div class="sy-mesi-key">
    <strong>同じ line の M-I トグルが cache line bouncing です。</strong> intra-socket なら 30~50ns/回、cross-socket なら 150~300ns/回。<code>LOCK CMPXCHG</code> 命令自体は cache line が M 状態のとき ~10ns ですが、RFO を経由しなければならないと 30~100 倍高くなります。<strong>これが lock contention の本当のコストです。</strong>
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

### atomic 命令が実際にすること

x86 で `LOCK CMPXCHG` が実行されると次のことが起こります。

1. CPU がそのメモリアドレスの cache line を **Modified 状態で**取ってきます (RFO メッセージで他のコアのコピーを無効化)
2. その line が M 状態の間 — **他のコアが同時に RFO を送っても cache coherence メカニズムが直列化** — compare と swap を実行します
3. line は M 状態のまま残るか、後で evict されます

要点は atomic の "atomicity" が**ハードウェアの cache coherence が RFO 要求を直列化するという事実**から出てくることです。ロックが別途あるのではなく、cache line 自体が一瞬に一つのコアだけが M 状態で持てるという cache プロトコルの不変式がそのまま lock です。

ARM では少し違います。ARM は **LL/SC (Load-Linked / Store-Conditional)** ペアです。

```asm
loop:
    LDXR  w0, [x1]        ; load-exclusive, x1 アドレスを追跡
    CMP   w0, w_expected
    B.NE  fail
    STXR  w2, w_desired, [x1]  ; store-exclusive, x1 がその間変更されたら失敗
    CBNZ  w2, loop        ; 失敗ならまた試行
```

LL/SC の利点は CAS の ABA 問題の一部に免疫な点、欠点は fail が可能でループが必要な点です。

### cache line bouncing — ロックの本当のコスト

二つのコアが同じロックを交代で取ると何が起こるか?

コア A がロックを取る → cache line が A で M 状態
コア B がロックを取ろうと CAS → cache line が A から B に移って A は I、B は M
コア A が再びロックを取る → cache line が B から A に移って B は I、A は M

この ping-pong が **cache line bouncing** です。一度の bounce コストは:

| シナリオ | コスト |
|---------|------|
| 同じ L3 を共有するコア間 (intra-socket) | ~30~50ns |
| 別ソケットコア間 (NUMA, cross-socket) | ~150~300ns |
| 別 NUMA ノード | ~数百~1000ns |

`LOCK CMPXCHG` 命令自体のコストは cache line がすでに M 状態のとき ~10ns 程度。**bouncing があれば 30~100 倍高くなります。**これが lock contention の本当のコストで、ロックそのものより cache 効果が大きい理由です。

> **ちょっと、これは押さえておきましょう。** cache coherence が自動で一貫性を保証するなら、ロックはなぜまた必要なのか?
>
> 二つは違う保証です。
>
> - **Cache coherence** は「一つの cache line のすべてのコピーが結局一貫します」を約束します。単一メモリ位置単位。
> - **Lock** は「複数のメモリ位置にまたがるクリティカルセクションを単一トランザクションにします」を約束します。意味単位。
>
> たとえば `account_a -= x; account_b += x;` は二つの cache line にまたがる作業です。coherence は各 line の一貫性を保証しますが、二つが同時に見えるのはロックが保証します。

### False sharing — 意図しない cache line bouncing

次の構造体を考えてみましょう。

```cpp
struct Counters {
    std::atomic<int> threadA_count;  /* offset 0  */
    std::atomic<int> threadB_count;  /* offset 4  */
};
```

スレッド A は自分のカウンターだけ、スレッド B は自分のカウンターだけ触ります。論理的には共有するデータがありません。しかし二つの atomic が**同じ 64 バイト cache line に入っていれば**、A の書き込みが B の line を I にし、B の書き込みが A の line を I にします。二つは無意味な ping-pong をします。この現象が **false sharing** です。

解決策は **cache line アライメント**です。

```cpp
struct Counters {
    alignas(64) std::atomic<int> threadA_count;  /* line 0 */
    alignas(64) std::atomic<int> threadB_count;  /* line 1 */
};
```

C++17 は `std::hardware_destructive_interference_size` 定数を提供してコンパイル時に cache line サイズを知れるようにしました。

ゲームエンジンコードで false sharing は普通次に現れます。

- スレッドごとの統計配列 — `int hits[NUM_THREADS]` の隣接スロット
- producer/consumer ring buffer の head/tail ポインタ
- 小さな Job 構造体が配列にぎっしり詰まっているとき

測定は難しい。CPU カウンター `mem_load_uops_l3_hit_retired.xsnp_hitm` (Intel) が false sharing を捕まえる指標の一つです。Linux `perf c2c` がこれを自動化します。

### Memory barrier — 順序保証のハードウェア側

cache coherence は「値」を一貫させますが、**「順序」**は別問題です。CPU は命令を再配置し、store buffer は自分のコアの書き込みを少し閉じ込めるからです。

```cpp
/* Thread A */
data = 42;
ready = true;       /* この二つの store の順序が他のコアに保証されるか? */

/* Thread B */
if (ready)
    use(data);      /* data は本当に 42 か? */
```

x86 は **TSO (Total Store Order)** なので store-store 再配置が起こりませんが、ARM は weak ordering なので上のコードは壊れる可能性があります。ARM では二つの store の間に **memory barrier (`DMB ST`)** が必要です。

ロックが我々に約束するものの一つがこの順序です。`mutex.unlock()` が内部的に `release` 意味の barrier を含み、`mutex.lock()` が `acquire` 意味の barrier を含むため、ロックの中で書いた値がロックの外でも一貫して見えます。

| Barrier | x86 | ARM | 意味 |
|---------|-----|-----|------|
| store-store | (自動) | DMB ST | 以前の store が終わった後にその後の store |
| load-load | (自動) | DMB LD | 以前の load が終わった後にその後の load |
| store-load | MFENCE | DMB SY | 以前の store が globally visible になってからその後の load |
| full | MFENCE | DMB SY | すべてのメモリ op を直列化 |

Part 12 でこの部分を本格的に扱いますが、**ロックが atomic 命令 + barrier の束**であるという点だけ押さえておきます。

### まとめ: 一回の lock が起こすこと

`mutex.lock()` / `mutex.unlock()` 一対が user space からハードウェア cache までどの段階を経るかを一つの図にまとめると次の通り。

<div class="sy-mflow">
  <div class="sy-mflow-title">mutex.lock() → critical section → mutex.unlock() — すべての階層</div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-lock">mutex.lock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">1</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>cache line ownership を要求</strong><br>
          <span>RFO メッセージを他のコアに送信</span>
        </div>
        <div class="sy-mflow-cost">~30~300ns</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">2</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-hw">HW</div>
        <div class="sy-mflow-stbody">
          <strong>他のコアのコピーを無効化</strong><br>
          <span>その line を I 状態にしてデータを取ってくる (M 状態に)</span>
        </div>
        <div class="sy-mflow-cost">RFO 応答</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">3</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>atomic 命令の実行</strong><br>
          <span><code>LOCK CMPXCHG</code> (x86) · <code>LDXR/STXR</code> (ARM): 0 → 1 を試行</span>
        </div>
        <div class="sy-mflow-cost">~10ns</div>
      </div>
      <div class="sy-mflow-branch">
        <div class="sy-mflow-bok"><strong>✓ 成功</strong> — fast path 終了、クリティカルセクション進入</div>
        <div class="sy-mflow-bno"><strong>✗ 失敗</strong> — slow path へ</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">4</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>kernel wait queue 進入</strong><br>
          <span><code>futex_wait</code> / <code>NtWaitForAlertByThreadId</code> / <code>__ulock_wait</code> — wait queue に登録して sleep</span>
        </div>
        <div class="sy-mflow-cost">~数百 ns + sleep</div>
      </div>
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">5</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>acquire 順序制約</strong><br>
          <span>この atomic 以降のメモリ演算が atomic より前に reorder されないように — ARM は <code>DMB ISH</code> または <code>LDA*</code>、x86 は普通の load で十分</span>
        </div>
        <div class="sy-mflow-cost">~数 ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-cs">
    <span class="sy-mflow-cs-h">— クリティカルセクション (critical section) —</span>
    <span class="sy-mflow-cs-d">この間、他の誰も同じロックの上に入れません</span>
  </div>

  <div class="sy-mflow-section">
    <div class="sy-mflow-sh sy-mflow-sh-unlock">mutex.unlock()</div>
    <div class="sy-mflow-steps">
      <div class="sy-mflow-step">
        <div class="sy-mflow-stnum">6</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>release 順序制約</strong><br>
          <span>ロックの中で書いた値が unlock store より後に reorder されないように — ARM は <code>DMB ISH</code> または <code>STL*</code>、x86 は普通の store で十分</span>
        </div>
        <div class="sy-mflow-cost">~数 ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-pivot">
        <div class="sy-mflow-stnum">7</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-cpu">CPU</div>
        <div class="sy-mflow-stbody">
          <strong>atomic store</strong><br>
          <span>lock 変数を 0 に設定 (待機者ビットチェック含む)</span>
        </div>
        <div class="sy-mflow-cost">~5ns</div>
      </div>
      <div class="sy-mflow-step sy-mflow-step-slow">
        <div class="sy-mflow-stnum">8</div>
        <div class="sy-mflow-stlayer sy-mflow-layer-os">OS</div>
        <div class="sy-mflow-stbody">
          <strong>待機者を起こす (いるときだけ)</strong><br>
          <span><code>futex_wake</code> / <code>NtAlertThreadByThreadId</code> / <code>__ulock_wake</code></span>
        </div>
        <div class="sy-mflow-cost">~数百 ns</div>
      </div>
    </div>
  </div>

  <div class="sy-mflow-legend">
    <span class="sy-mflow-lg sy-mflow-layer-hw">HW</span>cache coherence / MESI
    <span class="sy-mflow-lg sy-mflow-layer-cpu">CPU</span>atomic 命令 + barrier
    <span class="sy-mflow-lg sy-mflow-layer-os">OS</span>kernel wait queue (slow path だけ)
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

ここまでがロックの底です。次はこれらすべてのメカニズムの上でゲームエンジンが同期問題をどう解くかを見ます。

---

## Part 6: Unity の同期 — Main Thread、Job System、DOTS

ゲームエンジンはロックをそのまま使いません。60fps ゲームで一フレームは 16.67ms で、lock contention 一回が 100~300ns ~ 数 μs まで入ります。ロックが 1000 個起こればそれだけで 1ms を食います。だからエンジンは**ロックを避ける構造**を選びます。その構造の核心が二つ。

1. **Thread affinity**: あるデータは一つのスレッドだけが触ります (そうすればロックは全く必要ありません)
2. **Dependency-based parallelism**: ロックの代わりに dependency graph を作って read/write 衝突をスケジューリング時点で防ぎます

Unity はまさにこの二つをやります。

### Main Thread モデル

Unity のすべての `MonoBehaviour` コールバック — `Update`、`LateUpdate`、`FixedUpdate`、`OnGUI`、`OnTriggerEnter` など — は**ただ一つのスレッド、Main Thread で実行されます。**そしてほぼすべての Unity API (`Transform.position`、`GameObject.Find`、`Component.GetComponent` など) は main thread からのみ呼び出せます。他のスレッドから呼ぶと `UnityException: ... can only be called from the main thread.` が投げられます。

これはものすごい単純化です。Scene graph 全体にロックが一つもありません — すべてのアクセスが一つのスレッドだからです。

> **ちょっと、これは押さえておきましょう。** Unity の main thread は OS スレッド 1 番ですか?
>
> 「1 番」というのは OS の観点では無意味です。main thread は Unity プロセスが始まるとき最初に作られるスレッドで、OS の立場では普通の pthread/Win32 thread の一つです。ただ Unity ランタイムがこの特定のスレッドの ID を記録しておいて `IsMainThread()` チェックに使います。macOS では main thread が NSRunLoop と結合されていて UI イベントと一緒に動きます。

main thread モデルの落とし穴は一つ。**重い作業を main thread でやるとそのままフレームドロップになります。**だから Unity はワーカースレッドを別途立ち上げて、その上に **Job System** という抽象を提供します。

### Unity Job System

Job System は二つのことを同時にやります。

1. **Native メモリに対する並列処理**: managed heap を触らないので GC と無関係
2. **schedule 時点の race 検知**: dependency graph と NativeContainer safety で read/write 衝突をチェック。属性 (`[ReadOnly]`/`[WriteOnly]`/`[NativeDisableContainerSafetyRestriction]`) はコンパイラが読みますが、**実際の衝突チェックは `Schedule()` 呼び出し時点のランタイムチェック**で、`ENABLE_UNITY_COLLECTIONS_CHECKS` マクロ (Editor/Development ビルド) でのみ有効化されます

基本使用は次の通り。

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

ここで `Schedule` は job を即座に実行せず**dependency graph に登録**します。`JobHandle` はその job の完了を追跡するハンドルです。

#### 内部動作 — 一回の呼び出しはどこへ行くか

`Schedule()` 一行が起こすことを段階的に追跡してみます。

1. **コンパイル時点**: `[ReadOnly]`、`[WriteOnly]` 属性を IL2CPP/Burst が読んで `velocities` は read のみ、`positions` は write のみと表示
2. **Schedule 呼び出し (main thread)**:
   - JobHandle を生成し dependency を登録
   - Job 構造体を unmanaged メモリにコピー (worker が main heap を触らないように)
   - NativeContainer の AtomicSafetyHandle をチェック — 他の進行中の job が同じコンテナを write 中なら、コンパイルではなくランタイム例外
3. **ワーカースレッド (`Unity Job Worker N`)**:
   - 自身の wait-list から job を取り出す (work-stealing deque)
   - `IJobParallelFor` なら batch (64 個ずつ) でインデックス範囲を切って分散
   - 各 batch に対して `Execute(index)` を呼び出す
4. **Complete 呼び出し (main thread)**:
   - `handle.Complete()` が dependency graph ですべての transitively dependent job が終わったか確認
   - 終わっていなければ main thread もワーカーのように job を盗んで実行 (work-stealing、main thread も働き手になる)

#### データがコア間でどう流れるか

`positionBuffer` がワーカースレッドでどう触られるかを cache 単位で追跡してみましょう。

1. **Schedule 時点**: `positionBuffer` の最初の 64 スロット (16 バイト × 64 = 1024 バイト = 16 個の cache line) が main thread CPU の L1/L2 にあります (前のフレームで触ったので)。
2. **ワーカースレッド開始**: ワーカー N が `Execute(0)` ~ `Execute(63)` を受け取ります。このワーカーが他のコアにあるなら、64 スロットの cache line に対する **RFO メッセージ**が発送されます。main thread の L1 からワーカーコアの L1 に line が移動 — intra-socket 30~50ns ずつ、16 line なら最初の batch のウォームアップに ~600ns。
3. **Batch 実行**: ワーカーが 64 個を順次処理する間、cache line はすべてワーカーコアの L1 に留まります。16 バイトスロット 4 個が 1 line なので 1 line につき 4 回触る間 line は M 状態維持 — cache hit。
4. **次の batch (64~127 番)**: また 16 line が新たにワーカー L1 に。前の 16 line は evict されるかワーカー L2/L3 に残る。
5. **Complete 時点**: main thread が結果を再び読むと、すべての line が再び main thread CPU 側に RFO されます。

ここで見えるコストは二つ。

- **最初の batch ウォームアップ**: cache line が main → ワーカーへ移動するコスト
- **結果回収**: ワーカー → main へ再び移動するコスト

だから Job の入力/出力サイズが小さいと Job スケジューリング自体のコストが作業コストを超えることがあります。`IJobParallelFor` の `batchCount` パラメータ (上の例の 64) はこのトレードオフを調整します。小さすぎると batch 境界ごとに cache miss と dispatch オーバーヘッド、大きすぎると load balancing が崩れます。Unity ドキュメントが「1 よりは 16~64 が普通良い」とガイドする理由です。

次の図は Job dependency DAG とワーカーマッピングを見せます。上が dependency graph (論理的順序)、下が実際の worker thread マッピング (時間軸) です。

<div class="sy-unity">
  <div class="sy-unity-title">Unity Job System — dependency DAG と worker mapping</div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">dependency DAG (論理的順序)</div>
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
      <div class="sy-unity-deplabel">read-after-write — dependency が自動追加</div>
    </div>
  </div>

  <div class="sy-unity-block">
    <div class="sy-unity-sec">worker thread マッピング (実際の実行、time →)</div>
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
    <div class="sy-unity-sec">データの流れ — Worker 1 が ApplyVel[0..15] を実行する間</div>
    <div class="sy-unity-cacheflow">
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">①</div>
        <div class="sy-unity-cstep-t">Schedule 時点</div>
        <div class="sy-unity-cstep-d">positionBuffer[0..15] cache line が main CPU L1 にある</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-rfo">
        <div class="sy-unity-cstep-i">②</div>
        <div class="sy-unity-cstep-t">ワーカー開始</div>
        <div class="sy-unity-cstep-d">RFO メッセージで line が worker CPU L1 に移動 (~30~50ns × 4 lines)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep sy-unity-cstep-hot">
        <div class="sy-unity-cstep-i">③</div>
        <div class="sy-unity-cstep-t">Batch 実行</div>
        <div class="sy-unity-cstep-d">16 スロット = 4 line、すべて worker L1 に留まる (cache hit、M 状態)</div>
      </div>
      <div class="sy-unity-carrow">→</div>
      <div class="sy-unity-cstep">
        <div class="sy-unity-cstep-i">④</div>
        <div class="sy-unity-cstep-t">Complete</div>
        <div class="sy-unity-cstep-d">結果 line が再び main CPU に RFO される (read 時点)</div>
      </div>
    </div>
  </div>

  <div class="sy-unity-key">
    <strong>ロックが一度もありません。</strong> Job 間の dependency を graph で表現して read-after-write 衝突を schedule 時点で直列化し、同じ read 権限を持つ job たちは自由に並列に流します。AtomicSafetyHandle が <code>Schedule()</code> 呼び出し時点のランタイムチェックで (Editor/Development ビルド限定) コンテナ使用権限を検査して race があれば例外を投げます。
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
.sy-unity-key code { background: #fff; padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 11px; }

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
[data-mode="dark"] .sy-unity-key code { background: #2d3748; color: #90cdf4; }

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

#### NativeContainer と AtomicSafetyHandle

Unity は GC ヒープではない native メモリに対しても race を捕まえます。どうやって?

`NativeArray<T>`、`NativeList<T>`、`NativeQueue<T>` のような NativeContainer は内部に **AtomicSafetyHandle** を持ちます。Editor ビルドと Development ビルドでのみ活性化されるデバッグメタです。構造はだいたい:

```csharp
struct AtomicSafetyHandle {
    int version;          /* コンテナが dispose されたか */
    AtomicSafetyNodePtr nodePtr;  /* read/write reader list 管理 */
}
```

このハンドルは次を追跡します。

- **現在このコンテナを write している job**: 0 または 1 個 (いれば他の誰も read すらできない)
- **現在このコンテナを read している job たち**: N 個 (writer は遮断される)
- **コンテナが生きているか (DisposeSentinel)**: dispose されたコンテナアクセス時に即座に例外

Schedule 時点で Unity が job の `[ReadOnly]/[WriteOnly]` 表示と AtomicSafetyHandle 状態を比較して**衝突可能性を発見すると例外**を投げます。Job を schedule すらできないようにブロックする形です。

```csharp
var a = new NativeArray<int>(100, Allocator.TempJob);
var jobA = new WriteJob { data = a }.Schedule();          /* a を write */
var jobB = new ReadJob  { data = a }.Schedule();          /* a を read — 衝突! */
/* InvalidOperationException: The previously scheduled job WriteJob writes
   to the NativeArray a. You must call JobHandle.Complete() on the job
   before you can read from the NativeArray safely. */
```

解決は dependency を明示することです。

```csharp
var handleA = jobA.Schedule();
var handleB = jobB.Schedule(handleA);   /* B は A 後に */
handleB.Complete();
```

これをやらないようにするには `[NativeDisableContainerSafetyRestriction]` を付けますが、それは「race は私が責任を負う」という宣言です。本当に安全な場合 — 例: index range が重ならない二つの job — にのみ使うべきです。

> **ちょっと、これは押さえておきましょう。** AtomicSafetyHandle は production build でも動作しますか?
>
> いいえ。`ENABLE_UNITY_COLLECTIONS_CHECKS` マクロが定義された Editor と Development ビルドでのみ活性化されます。Release ビルドではコンパイラがすべての safety check コードを除去します。**これが静的保証ではありません** — Editor で捕まらなかったというのは*そのとき実行されたコード経路で* safety system が衝突を見なかったという意味だけで、別の入力・別のタイミングで race が起こらないという証明ではありません。だから production に出す前に可能なすべての経路を通すテストが必要で、`[NativeDisableContainerSafetyRestriction]` を使った経路はその検査すら回避するのでさらに注意が必要です。

#### Burst — atomic はどう保証されますか

要約すると — **Burst は IL を LLVM で native code にコンパイルしますが、普通の array アクセスを atomic に変えてはくれません。** atomic が必要なら `Interlocked.*` を明示的に呼び出さなければならず、それだけがハードウェア atomic 命令として emit されます。これが核心で、その下の 4~5 段階はコンパイラ内部詳細なので折りたたんでおきます。

<details class="sy-fold" markdown="1">
<summary>▸ Burst がコンパイルする段階を詳しく — IL → native、atomic emit、NoAlias、SIMD マッピング</summary>

`[BurstCompile]` を付けた job は IL ではなく native code にコンパイルされます (LLVM バックエンド)。Burst が NativeArray アクセスをコンパイルするとき起こること:

1. **普通の `array[i]` read/write は普通の load/store** — atomic ではありません。race が可能で、衝突防止は schedule 時点の dependency・safety system に依存します
2. **`Interlocked.*` のような明示的 atomic 呼び出しのみ** x86 `LOCK XADD` / `LOCK CMPXCHG`、ARM `LDADD` / `LDXR-STXR` などハードウェア atomic 命令として直接 emit
3. Bounds check を SIMD-friendly な形で維持するか、Editor でのみ活性化
4. `[NoAlias]` 表示を活用して ptr aliasing を仮定 — コンパイラがより積極的に最適化
5. SIMD intrinsic (`Unity.Mathematics.float4`) を SSE/AVX/NEON にマッピング

```csharp
[BurstCompile]
public struct CountJob : IJobParallelFor {
    [NativeDisableContainerSafetyRestriction]
    public NativeArray<int> counter;   /* 長さ 1、すべての job が同じスロット */

    public void Execute(int i) {
        unsafe {
            Interlocked.Increment(ref UnsafeUtility.As<int, int>(
                ref counter.GetUnsafePtrReadOnly()[0]));
        }
    }
}
```

Burst が `Interlocked.Increment` を見た瞬間、それが x86 なら `LOCK INC` または `LOCK XADD` で直接 emit されます。つまり Part 5 で見たハードウェア atomic 命令がそのまま発生します。cache line bouncing コストもそのままかかります。

> **ちょっと、これは押さえておきましょう。** Job が同じ cache line のスロットに同時に書くとどうなりますか?
>
> それがまさに **false sharing** です。上の例のように長さ 1 の counter にすべての job が atomic increment をすると、その 1 バイト (実際は 4 バイト、line 1 個) がコア間を絶え間なく ping-pong します。百万回呼び出すと cache bounce だけで 50~100ms が消えます。解決策はスレッドローカルカウンターをそれぞれ別の cache line に置いて最後に合算すること — `[ThreadStatic]` または `NativeQueue<int>.Concurrent` の enqueue パターン。

</details>

#### DOTS / ECS — システム単位の dependency

`SystemBase` や `ISystem` ベースの ECS は上のメカニズムをさらに一段引き上げます。

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

`IJobEntity` はどの Component を read/write するかをシグネチャから自動抽出します (`ref` = write、`in` = read)。この情報をソースジェネレーターがコンパイル時にメタデータとして作っておけば、World scheduler がランタイムにそれを読んで次を自動で処理します。

- 同じ Component を write する二つの System は**自動で順序が付きます**
- 異なる Component を触る System たちは**自動で並列で回ります**

これがロックではなく dependency graph で同期を解く最も極端な例です。プログラマが lock を一度も取らないのに、scheduler が schedule 時点で read/write 権限を検査して衝突を直列化します (Editor/Development ビルドでは safety system が追加で動きます)。

内部的に ECS は Component ごとに ReaderWriterLock 意味の dependency 情報を維持します。これが Burst と合わさると次の図のようになります。

<div class="sy-ecs">
  <div class="sy-ecs-title">DOTS ECS scheduler — Component 権限解析による自動並列化</div>

  <div class="sy-ecs-comp">
    <div class="sy-ecs-comp-h">Component 権限解析 (コンパイル時点)</div>
    <div class="sy-ecs-comp-grid">
      <div class="sy-ecs-comp-cell">
        <div class="sy-ecs-sys">SpawnSystem</div>
        <div class="sy-ecs-perm"><span class="sy-ecs-w">write</span> Entity 追加/削除</div>
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
    <div class="sy-ecs-note">scheduler が read/write パターンを見て自動で dependency edge を追加します</div>
  </div>

  <div class="sy-ecs-tl">
    <div class="sy-ecs-tl-h">実行タイムライン (Frame N)</div>
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
      <span class="sy-ecs-arrow-h">↑ 同じ時刻 — 異なる Component を触るのでロックなしで同時実行</span>
      <span class="sy-ecs-arrow-d">↑ Position read は MoveJob 完了を待つ (自動 dependency)</span>
    </div>
  </div>

  <div class="sy-ecs-key">
    <strong>開発者がロックも dependency も明示しません。</strong> ECS scheduler が各 job/system の Component 権限 (<code>ref</code>=write、<code>in</code>=read) を読んで read-after-write 衝突だけ直列化します。結果: 異なる Component を触る作業は自由に並列、同じ Component を触ると自動順序保証。
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

ここで RenderBoundsJob が MoveJob 完了を待つ依存性は**開発者が明示しなくても** ECS が自動推論します。二つの job がともに `LocalTransform.Position` を触り、MoveJob が write、RenderBoundsJob が read なので、ECS scheduler が自動で dependency edge を追加します。

#### 一フレームのメモリの流れ — まとめ

Unity が一フレーム (16.67ms) の中で起こす同期関連のことを時間順にまとめると:

| 時点 | 場所 | 起こること |
|------|------|-----------|
| 0ms | Main | Input/MonoBehaviour Update — main thread only、ロックなし |
| 2ms | Main | Job を schedule、dependency graph 生成 |
| 2~10ms | Worker 1~N | ワーカーが dependency 順に job 実行、NativeArray cache line がワーカーコアに RFO 移動 |
| 10ms | Main | `JobHandle.Complete()` または sync point — main も働き手として work-stealing |
| 12ms | Render thread | command buffer を GPU に submit (次のセクション) |
| 16ms | GPU | present、次フレーム開始 |

ここまでが Unity 側です。Unreal は似た思想ですがスレッド分離がより強いです。

---

## Part 7: Unreal Engine の同期

Unreal は Unity より明示的な **multi-thread モデル**を持ちます。エンジン自体が複数の named thread に分かれていて、thread 間通信はほぼすべて lock-free queue の上に作られています。

### 四つの Named Thread

基本的な Unreal ゲームは次のスレッドが常に動く構造です。

| スレッド | 責任 | OS スレッド |
|--------|------|----------|
| **Game Thread** | Tick、ゲームプレイロジック、Blueprint、AI | main thread (Unity の main に相当) |
| **Render Thread** | high-level レンダーコマンド生成 (FRDG、RHI command 作成) | 別 OS スレッド |
| **RHI Thread** | GPU API 呼び出し (D3D12/Vulkan/Metal/Mantle) | 別 OS スレッド |
| **Audio Thread** | サウンドミキシング、voice 管理 | 別 OS スレッド |
| **Worker Threads** | TaskGraph job 実行 | コア数だけ |

核心の発想は**各スレッドが自分だけ触るデータを持ち、他のスレッドとの通信は明示的なコマンドキューを経由する**ことです。ロックを取る代わりにデータの所有権を thread に強く結びつけます。

### Game Thread → Render Thread — 一フレームの流れ

Unreal の Render Thread は普通 Game Thread より**一フレーム後ろで動作**します (Epic 公式ドキュメントは 0 または 1 frame behind と説明 — Game が早く終われば Render が追いつくこともあり、Render が重ければ Game が次のフレームで sync で詰まることもあり)。この記事では通常負荷状態の「1 フレーム遅れ」ケースを基準に説明します。Game が N 番目のフレームのロジックを回すとき、Render は N-1 のレンダーコマンドを作り、RHI は N-2 を GPU に提出します。

<div class="sy-upipe">
  <div class="sy-upipe-title">Unreal 4-thread パイプライン — 同じ時刻、異なるフレーム</div>

  <div class="sy-upipe-grid">
    <div class="sy-upipe-corner">スレッド ↓ / フレーム →</div>
    <div class="sy-upipe-fh">Frame N</div>
    <div class="sy-upipe-fh">Frame N+1</div>
    <div class="sy-upipe-fh">Frame N+2</div>

    <div class="sy-upipe-th sy-upipe-th-game">Game Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active">N ロジック<br><span>Tick, AI, Physics, Blueprint</span></div>
    <div class="sy-upipe-cell">N+1 ロジック</div>
    <div class="sy-upipe-cell">N+2 ロジック</div>

    <div class="sy-upipe-th sy-upipe-th-render">Render Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-r">N-1 レンダー<br><span>RDG ビルド、FMeshBatch 生成</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N レンダー</div>
    <div class="sy-upipe-cell sy-upipe-cell-r">N+1 レンダー</div>

    <div class="sy-upipe-th sy-upipe-th-rhi">RHI Thread</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-h">N-2 submit<br><span>D3D12/Vulkan/Metal API</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N-1 submit</div>
    <div class="sy-upipe-cell sy-upipe-cell-h">N submit</div>

    <div class="sy-upipe-th sy-upipe-th-gpu">GPU</div>
    <div class="sy-upipe-cell sy-upipe-cell-active sy-upipe-cell-g">N-3 draw + present<br><span>実際のピクセル表示</span></div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-2 draw + present</div>
    <div class="sy-upipe-cell sy-upipe-cell-g">N-1 draw + present</div>
  </div>

  <div class="sy-upipe-flow">
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ ENQUEUE_RENDER_COMMAND</div>
      <div class="sy-upipe-fl-d">Game が Render にデータ push (lock-free MPSC queue)</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ RHI command list</div>
      <div class="sy-upipe-fl-d">Render が RHI に GPU コマンド dispatch</div>
    </div>
    <div class="sy-upipe-fl">
      <div class="sy-upipe-fl-h">→ GPU submit</div>
      <div class="sy-upipe-fl-d">RHI が GPU に提出、fence で追跡</div>
    </div>
    <div class="sy-upipe-fl sy-upipe-fl-back">
      <div class="sy-upipe-fl-h">← FRenderCommandFence</div>
      <div class="sy-upipe-fl-d">Game が Render 完了を待つ必要があるときのみ (まれ)</div>
    </div>
  </div>

  <div class="sy-upipe-key">
    <strong>同じ時刻に同じデータを触るスレッドはただ一つです。</strong> Game が N を作る間に Render は N-1 を、RHI は N-2 を処理するのでロックがほぼ必要ありません。トレードオフは入力遅延 +1 フレーム — 9 話で見た 1 フレームパイプライニングの正確な実装です。
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

このパイプライニングのおかげでロックがほぼ必要ありません。一時点で同じデータを触るスレッドが一つだけだからです。

### TaskGraph — Unreal の Job System

`FTaskGraphInterface` が Unity Job System の等価物です。

```cpp
FGraphEventRef MyTask = FFunctionGraphTask::CreateAndDispatchWhenReady(
    [Data]() {
        // ワーカースレッドで実行
        ProcessData(Data);
    },
    TStatId(),
    nullptr,                      /* dependency prerequisite */
    ENamedThreads::AnyThread      /* どのスレッドで実行するか */
);

/* 後で結果を待つ */
FTaskGraphInterface::Get().WaitUntilTaskCompletes(MyTask);
```

特徴:

- **Named thread の選択可能**: `GameThread`、`RenderThread`、`RHIThread`、`AnyThread` の中から選んで dispatch
- **Dependency edge の表現**: prerequisite array を渡すとそれらが終わった後に開始
- **自動 work-stealing**: AnyThread は最も暇な worker が持っていく
- **階層的 task**: task の中で子 task を spawn 可能

### ENQUEUE_RENDER_COMMAND — ロックが見えないコマンドキュー

Game Thread から Render Thread にデータを渡す最も一般的なマクロです。

```cpp
FVector NewPos = Actor->GetActorLocation();
FRHICommandListImmediate& RHICmdList = ...;

ENQUEUE_RENDER_COMMAND(UpdateActorPos)(
    [NewPos](FRHICommandListImmediate& RHICmdList) {
        /* このラムダは Render Thread で実行されます */
        UpdateConstantBuffer(RHICmdList, NewPos);
    });
```

このマクロの意味は次の通り — **ラムダをコマンドオブジェクトにして Render Thread のコマンドキューに enqueue すると、Render Thread が自分のキューから FIFO 順に取り出して実行します。** Epic 公式ドキュメントは内部キューの実装を lock-free MPSC として保証するとは明示しておらず (バージョンごとに変わり得る実装詳細)、このマクロの契約は *「順序保証 + Render Thread で実行」* までです。概念的に multi-producer (worker thread も enqueue 可能) single-consumer (Render Thread だけ pop) パターンで、だから一般的に lock-free MPSC が適した場所です。

> **ちょっと、これは押さえておきましょう。** lock-free MPSC queue はどうやってロックなしで動作するのか?
>
> 核心は **producer は atomic CAS または atomic exchange でキュー tail にノードを append** し、**consumer は単一スレッドなので同期が必要ない**という非対称を利用することです。最も有名なデザインが **Vyukov MPSC queue** です — atomic exchange 一回で prev tail を掴み、prev tail の next ポインタを新しいノードに更新。再試行 (retry) ループなしで contention をほぼなくします。

次のコードが Vyukov MPSC の核心です。

```cpp
struct Node { std::atomic<Node*> next; T payload; };
std::atomic<Node*> tail;

void push(Node* node) {
    node->next.store(nullptr, std::memory_order_relaxed);
    Node* prev = tail.exchange(node, std::memory_order_acq_rel);
    prev->next.store(node, std::memory_order_release);
}
/* pop は single-consumer なので atomic がほぼ不要 */
```

このパターンが Unreal のほぼすべての inter-thread 通信に敷かれています。だから ENQUEUE_RENDER_COMMAND が毎フレーム数百回呼び出されても lock contention がありません。

### FRenderCommandFence — Game が Render を待つとき

たまには Game Thread が「Render Thread に送ったコマンドが本当に終わったか」を知る必要があります。たとえば GPU リソースを安全に destroy するには Render Thread がそれをもう触らないことを保証する必要があります。

```cpp
FRenderCommandFence Fence;
Fence.BeginFence();      /* この時点までのすべての render command を mark */
Fence.Wait();            /* mark された command がすべて終わるまで block */
```

`BeginFence` は Render Thread のキューに fence マーカーを enqueue します。`Wait` は Game Thread が fence が処理されるまで sleep (FEvent で wait)。これが Game ↔ Render の間でほぼ唯一の明示的同期ポイントです。

### FCriticalSection / FRWLock — 明示的ロック

もちろんたまには明示的ロックが必要です。Unreal は次を提供します。

- **`FCriticalSection`**: Windows の `CRITICAL_SECTION` を抽象化 (他の OS は pthread_mutex)。普通の mutex。
- **`FRWLock`**: Reader-Writer lock。macOS は `os_unfair_lock` の代わりに pthread_rwlock にマッピング。
- **`FScopeLock`**: RAII ヘルパー (`std::lock_guard` 等価物)。
- **`TQueue<T, EQueueMode::Spsc>`**: lock-free single-producer single-consumer queue。
- **`TQueue<T, EQueueMode::Mpsc>`**: lock-free multi-producer single-consumer。

エンジンコード自体は lock-free queue と TaskGraph dependency をより好み、ゲームプレイコード (gameplay framework の上で) で `FCriticalSection` がたまに使われます。

### Unity と Unreal の比較

| 項目 | Unity | Unreal |
|------|-------|--------|
| Main thread | 一つ、すべての API がここを通る | Game Thread、ゲームプレイ限定 |
| Render 分離 | あり (Render Thread、明示的 API は少ない) | 強い (Render Thread + RHI Thread + RDG) |
| Job 抽象 | Job System + DOTS | TaskGraph + Async Tasks |
| コンパイル時 race 検知 | NativeContainer + AtomicSafetyHandle | なし (ランタイム assert 中心) |
| ロック回避思想 | dependency graph + main thread affinity | named thread + lock-free queue |
| ECS | DOTS / Entities (公式) | Mass Entity (5.x)、非公式 ECS も多数 |

Unity は **dependency を安全に表現できるようにして schedule 時点で (Editor/Development で) 検証**する方へ行きます (safety on by default)。Unreal は **データを thread に縛ってコマンドキューで通信**する方です (performance by convention)。両方とも結局ロック自体はほぼ取らないですが、その理由と検証時点が違います。

---

## Part 8: ロックを避けるゲームエンジンパターン

エンジン内部でロックがほぼ使われない分、ロックを迂回するパターンが発達しています。ゲームコードで直接活用できるものを整理します。

### Double Buffering

最も単純でよく使われます。**二つのバッファを交互に使うこと**です。ただし安全に使うには **read と write が時間的に重ならない前提** — 普通フレーム境界や fence — が必要です。

```cpp
/* 前提: GameTick と PhysicsTick がフレーム境界で順次呼び出される。
   一フレーム内では read が終わった後に worker が次の write を始める */

struct PhysicsState {
    std::vector<Transform> transforms;
};

PhysicsState buffers[2];
std::atomic<int> readIdx{0};   /* main が読む */

/* Frame N — Worker が次に write するバッファを決定 (read 終了時点の保証必要) */
void PhysicsTick() {
    int w = 1 - readIdx.load(std::memory_order_acquire);
    UpdatePhysics(buffers[w]);
    readIdx.store(w, std::memory_order_release);  /* publish */
}

/* Frame N — Main が最も最近 publish されたバッファを read */
void GameTick() {
    int r = readIdx.load(std::memory_order_acquire);
    Render(buffers[r]);
}
```

ロックが一度もありません。atomic 一個で「今読み込み可能なバッファインデックス」だけを交換します。メモリコストはバッファの二倍。**ただし writer と reader が独立して非同期ループを回すと上のコードは安全ではありません。** publish 直後 reader がまだそのバッファを読んでいる間に worker が次の tick で*別の*バッファを書こうとしたとき、インデックスが同じになることがあるからです。ゲームエンジンは普通**フレーム境界で sync** して read 段階と write 段階が時間的に分離されるように設計します — その前提の上でだけ double buffer が安全です。そうでないパターンなら triple buffer または明示的な sequence handoff が必要です。

ゲームエンジンでこのパターンが使われる場所:

- **物理 → レンダー**: フレーム境界で buffer swap、render thread が N を描く間に physics が N+1 準備
- **AI tick**: 次のフレームの行動を先に計算してフレーム境界で swap
- **ネットワーク入力**: 受け取ったパケットを一フレーム分溜めてフレーム境界で swap

### Triple Buffering

writer と reader が独立ループを回って read・write が時間的に重なり得るなら double buffer だけでは足りません。三つを置けば OK — 「今描いているもの」、「ちょうど作ったもの」、「次に書くもの」。OS グラフィックスタックの swap chain、V-sync queue、ゲームエンジンの ring buffer などで使われます。三つのバッファがあれば writer は常に reader が使っていないスロットを選んで書けます。

### Lock-free SPSC Ring Buffer

Single-producer single-consumer キューは atomic 二つでロックなしで実装できます。

```cpp
template<typename T, size_t N>
struct SpscRing {
    T buf[N];
    alignas(64) std::atomic<size_t> head{0};  /* producer が書く */
    alignas(64) std::atomic<size_t> tail{0};  /* consumer が書く */

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

`alignas(64)` で head と tail が別の cache line にあるようにします — false sharing 防止。producer と consumer が別のコアで回っても contention がありません。

この構造が game ↔ render command queue、audio sample buffer、log queue などほぼすべての 1:1 通信に敷かれています。

### Per-thread accumulation

複数のスレッドがカウンターを増加させるべきなら false sharing の罠に陥りやすい。解決は**各スレッドが自分のスロットを持ち最後に合算すること**です。

```cpp
struct alignas(64) Slot { int64_t v = 0; };
Slot per_thread[NUM_THREADS];

/* 各スレッド */
per_thread[tid].v++;        /* atomic ではない普通の store */

/* 合算 (一つのスレッドで) */
int64_t total = 0;
for (auto& s : per_thread) total += s.v;
```

`alignas(64)` のおかげで各スロットが自分の cache line を独占します。100 万回の増加が false-sharing lock-free counter より 50~100 倍速いです。

### Frame-locked sync — 明示的同期点

Job 単位で絶え間なくロックを取る代わりに、**フレーム境界でのみ同期**します。一フレームの中では一つのスレッドが自分のデータだけ触り、フレーム終了時にすべてのスレッドの結果を main が一度に統合します。

Naughty Dog の fiber システム (9 話参照) もこの思想の極端です — 一フレームを数千個の fiber で切り分けますが、すべての fiber が終わる sync point でのみ次のフレームに進みます。

### まとめ: ロック回避の考え方

エンジン内部でロックの代わりに使われるパターンの共通点は:

1. **データを thread に縛る** — 一つのスレッドが自分のデータを単独で触れば lock 不要
2. **明示的通信チャネル** — lock-free queue で thread 間データを渡す
3. **時間分離** — double/triple buffer で read と write を時間的に分離
4. **空間分離** — per-thread slot で false sharing 回避
5. **まれにのみ sync** — frame boundary のような自然な sync point にコストを集中

ロックが悪いのではなく **lock contention と cache bouncing** が高いのであり、上のパターンはその二つを自然に回避します。

---

## Part 9: ロックのコスト — 測定する

推測の代わりに測定です。ロックが本当に高いのか、どこでコストが発生するのかを確認するツールです。

### Linux — perf と perf c2c

```bash
# システムコール (futex_wait/wake) の頻度
$ perf stat -e syscalls:sys_enter_futex ./game

# cache miss、hitm (他のコアの modified line hit)
$ perf stat -e mem_load_uops_l3_hit_retired.xsnp_hitm ./game

# false sharing 検知 (Cache-to-Cache analysis)
$ perf c2c record ./game
$ perf c2c report
```

`perf c2c` は false sharing の標準診断ツールです。HITM (Hit Modified) イベントが同じ cache line で頻発すればその line が疑い対象です。

### Windows — Concurrency Visualizer、ETW

Visual Studio Concurrency Visualizer は thread ごとの CPU usage、lock contention block、I/O wait を可視化します。WPA の "Wait Analysis" ページも同じ情報をもっと詳しく見せます。

```powershell
# lock contention 追跡
wpr -start LockHeldTimes -filemode
# (ゲーム実行)
wpr -stop trace.etl
```

### macOS — Instruments System Trace

System Trace template の "Thread State" トラックが thread blocking を可視化します。"Pthread mutex contention" マーカーが別途表示されてどの mutex が contended かすぐに分かります。

```bash
# または dtrace で即席測定
$ sudo dtrace -n 'pid$target:libsystem_pthread:_pthread_mutex_lock:entry {@[ustack()]=count();}' -p <pid>
```

### クロスプラットフォーム — Tracy Profiler

Tracy は mutex 使用を直接追跡できるマクロを提供します。

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

`LockableBase` で包んだ mutex の lock/unlock 時点と contention 時間が Tracy のタイムラインに可視化されます。どの mutex が hot かが一目で分かります。

### ゲームエンジン内蔵プロファイラ

- **Unity Profiler**: Job System タブで worker thread の活用度、dependency wait time 表示
- **Unreal Insights**: TaskGraph の可視化、fence wait time、ENQUEUE_RENDER_COMMAND 呼び出し頻度
- **PIX (Xbox/PC)**: D3D12 fence wait、RHI thread blocking 表示

### 一行診断

「私のゲームが遅いのにロックが原因ですか?」の一行答えは**「thread state の可視化で spinning または wait が見えればその時間だけコスト」**です。コード一行見ずに thread state graph だけ見ればロックが本当の問題かすぐに分かります。

---

## まとめ

この記事で扱った内容を一度にまとめると次の通り。

**race condition の正体**:
- `counter++` が load/modify/store の 3 段階に分解されて原子性が崩れる
- data race (undefined behavior) と race condition (実行順序依存) は異なる概念
- ロックは原子性・可視性・順序の三つを一緒に保証

**ロックの家族**:
- Mutex、Spinlock、Semaphore、RWLock、CondVar、Monitor、Barrier、Latch
- 同じ atomic の上に異なるポリシーがあるだけ

**ロックの実装**:
- Peterson は理論的にだけ動作、実際の CPU は memory barrier が必要
- ハードウェア atomic: x86 LOCK CMPXCHG、ARM LDXR/STXR
- Spin vs Sleep はクリティカルセクションの長さ vs コンテキストスイッチコストの比較

**OS プリミティブ**:
- Linux futex (2002)、Windows SRWLock (Vista、2007)、macOS os_unfair_lock (2016)
- すべて同じ思想: fast path は user-space atomic、slow path のみ kernel
- macOS os_unfair_lock は owner thread ID エンコーディングで QoS donation 可能

**ハードウェアメカニズム**:
- CPU キャッシュ: L1 (4 cycle) ~ L3 (50 cycle) ~ DRAM (300 cycle)
- MESI プロトコル: 一つの cache line はたった一つのコアだけが Modified 可能
- atomic の atomicity は cache coherence が RFO を直列化することから出てくる
- Cache line bouncing: intra-socket 30~50ns、cross-socket 150~300ns
- False sharing: 異なる変数が同じ cache line にあれば意図しない contention

**Unity の同期**:
- Main thread モデル: すべての Unity API が main のみ
- Job System: JobHandle dependency graph、batch 64、work-stealing
- NativeContainer + AtomicSafetyHandle: schedule 時点のランタイム race 検査 (Editor/Development 限定)
- Burst: 普通の read/write は普通の load/store、`Interlocked.*` 呼び出しのみハードウェア atomic として emit
- DOTS: Component read/write を自動解析、scheduler が schedule 時点で dependency edge を自動生成

**Unreal の同期**:
- Game / Render / RHI / Audio Thread の分離
- TaskGraph + Named Thread + dependency
- ENQUEUE_RENDER_COMMAND は lock-free MPSC queue で動作 (概念的に)
- FRenderCommandFence が Game ↔ Render の明示的 sync point

**ロックを避けるパターン**:
- Double/Triple buffer、lock-free SPSC ring、per-thread slot
- Frame-locked sync で同期コストを一点に集中

次回の **Part 11 — デッドロックと飢餓**では、ロックが正常に動作するのにプログラムが止まる場合 — 二つのロックの循環待機、priority inversion、livelock — を扱います。その後 Part 12 で memory model と atomic ordering、Part 13 で lock-free データ構造と Unity Job System のさらに深い内部に続きます。

Stage 2 の原典の問いにこれで答えられます。

> **スレッド二つが同じ変数に書き込むと、なぜプログラムが時々だけ落ちるのか?**

- 「書く」という行為が load/modify/store の 3 段階なので途中で他のスレッドが割り込めて
- 「割り込む」ことはスケジューラが任意の瞬間に決めるので「時々」で
- 「防ぐには」cache coherence と atomic 命令の上に作った lock という抽象が必要だ。

---

## References

### 教材

- Herlihy, M., Shavit, N. — *The Art of Multiprocessor Programming*, 2nd ed., Morgan Kaufmann, 2020 — Ch.2~7 (Mutex algorithms, lock-free, hardware foundations) — マルチスレッド同期の正典
- Silberschatz, A., Galvin, P. B., Gagne, G. — *Operating System Concepts*, 10th ed., Wiley, 2018 — Ch.6 (Synchronization Tools), Ch.7 (Synchronization Examples)
- Tanenbaum, A. S., Bos, H. — *Modern Operating Systems*, 4th ed., Pearson, 2014 — Ch.2.3 (Interprocess Communication)
- Russinovich, M., Solomon, D., Ionescu, A. — *Windows Internals*, 7th ed., Microsoft Press, 2017 — Ch.8 (System Mechanisms, SRWLock / pushlock の内部)
- Singh, A. — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — Ch.10 (Mach IPC, locks)
- Drepper, U. — *What Every Programmer Should Know About Memory*, Red Hat, 2007 — cache coherence 入門の決定版 — [people.freebsd.org/~lstewart/articles/cpumemory.pdf](https://people.freebsd.org/~lstewart/articles/cpumemory.pdf)
- Gregory, J. — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — Ch.8.6~8.7 (Multithreading, Job systems)
- McKenney, P. E. — *Is Parallel Programming Hard, And, If So, What Can You Do About It?*, 2024 ed. — [kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) — RCU 著者の無料書籍

### 論文

- Peterson, G. L. — "Myths About the Mutual Exclusion Problem", *Information Processing Letters*, 1981 — Peterson アルゴリズム原典
- Dijkstra, E. W. — "Cooperating Sequential Processes", *Programming Languages*, 1968 — Semaphore 導入
- Lamport, L. — "A New Solution of Dijkstra's Concurrent Programming Problem", *CACM*, 1974 — bakery algorithm
- Lamport, L. — "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs", *IEEE TC*, 1979 — sequential consistency の定義
- Franke, H., Russell, R., Kirkwood, M. — "Fuss, Futexes and Furwocks: Fast Userlevel Locking in Linux", *OLS 2002* — futex の導入 — [kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf](https://www.kernel.org/doc/ols/2002/ols2002-pages-479-495.pdf)
- Drepper, U. — "Futexes Are Tricky", Red Hat, 2011 — futex 実装の落とし穴 — [akkadia.org/drepper/futex.pdf](https://www.akkadia.org/drepper/futex.pdf)
- Sweeney, T. et al. — "Concurrent Programming in Unreal Engine" (GDC, EpicGames Dev) — TaskGraph の設計
- Boehm, H.-J. — "Threads Cannot Be Implemented as a Library", *PLDI 2005* — C++ memory model の動機
- Adve, S. V., Gharachorloo, K. — "Shared Memory Consistency Models: A Tutorial", *IEEE Computer*, 1996 — memory model 比較

### 公式ドキュメント

- Linux man pages — `futex(2)`, `futex(7)`, `pthread_mutex_lock(3)`, `pthread_rwlock_rdlock(3)` — [man7.org/linux/man-pages/man2/futex.2.html](https://man7.org/linux/man-pages/man2/futex.2.html)
- Linux Kernel Documentation — `Documentation/locking/futex2.rst`, `mutex-design.rst`, `lockdep-design.rst`
- Microsoft Docs — *Slim Reader/Writer (SRW) Locks*, *Critical Section Objects* — [learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks](https://learn.microsoft.com/en-us/windows/win32/sync/slim-reader-writer--srw--locks)
- Apple Developer — *Threading Programming Guide*, `os_unfair_lock(3)` — [developer.apple.com/documentation/os/os_unfair_lock](https://developer.apple.com/documentation/os/os_unfair_lock)
- Intel — *Intel 64 and IA-32 Architectures Software Developer's Manual*, Vol. 3A — Ch.8 (Multiple-Processor Management), LOCK prefix
- ARM — *ARM Architecture Reference Manual ARMv8-A*, B2 (Memory Model), C6 (Load-Acquire / Store-Release)

### Unity 公式

- Unity Manual — *C# Job System* — [docs.unity3d.com/Manual/JobSystem.html](https://docs.unity3d.com/Manual/JobSystem.html)
- Unity Manual — *Native Containers* — [docs.unity3d.com/Manual/JobSystemNativeContainer.html](https://docs.unity3d.com/Manual/JobSystemNativeContainer.html)
- Unity Manual — *Burst Compiler* — [docs.unity3d.com/Packages/com.unity.burst@latest](https://docs.unity3d.com/Packages/com.unity.burst@latest)
- Unity Manual — *Entities (DOTS)* — [docs.unity3d.com/Packages/com.unity.entities@latest](https://docs.unity3d.com/Packages/com.unity.entities@latest)
- Joachim Ante — *C# Job System and ECS — Unite LA 2018* — Job System の設計発表
- Lucas Meijer — *On DOTS: Entity Component System — Unity Blog*, 2019

### Unreal 公式

- Epic Games — *Threading in Unreal Engine* — [dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/threading-in-unreal-engine)
- Epic Games — *Task Graph System* — [dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph](https://dev.epicgames.com/documentation/en-us/unreal-engine/the-task-graph)
- Epic Games — *Rendering and the Game Thread* — RDG、ENQUEUE_RENDER_COMMAND 説明
- Tim Sweeney — *The Next Mainstream Programming Language*, POPL 2006 — Unreal のマルチスレッドビジョン

### ゲーム開発 / GDC

- Gyrling, C. — *Parallelizing the Naughty Dog Engine Using Fibers*, GDC 2015 — fiber ベース sync — [gdcvault.com/play/1022186](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine)
- Schreiber, B. — *Multithreading the Entire Destiny Engine*, GDC 2015 — Bungie の lock-free 設計
- Boulton, M. — *Threading the Frostbite Engine*, GDC 2009 — DICE の Job system
- Reinders, J., Roberts, B. — *Multithreading for Visual Effects*, A K Peters, 2014 — 映画エンジンの lock-free パターン
- Vyukov, D. — *Lock-Free / 1024cores* — Vyukov MPSC、scalability の資料 — [1024cores.net](https://www.1024cores.net/)

### ブログ / 記事

- Preshing, J. — *Preshing on Programming* — atomic、memory ordering シリーズ — [preshing.com](https://preshing.com/)
- Howells, D. et al. — *Linux Kernel Memory Barriers (`memory-barriers.txt`)* — kernel 公式メモリモデルガイド
- Chen, R. — *The Old New Thing* — Windows critical section/SRWLock 回顧
- Giesen, F. — *Reading List on Multithreading* — [fgiesen.wordpress.com](https://fgiesen.wordpress.com/)
- Oakley, H. — *The Eclectic Light Company* — macOS os_unfair_lock、QoS 観察
- Bonzini, P. — "QEMU and lock-free RCU" — RCU の実用適用

### ツール

- Linux: `perf c2c`, `perf lock`, `bpftrace`, `lockstat`
- Windows: Concurrency Visualizer (VS), WPA Wait Analysis, PIX (ゲーム用)
- macOS: Instruments System Trace, `dtrace`, `sample`
- クロスプラットフォーム: Tracy Profiler (LockableBase), Intel VTune, AMD μProf
- ThreadSanitizer (TSan): GCC/Clang の data race 静的・動的検知器









<div class="sy-guide">
  <div class="sy-guide-h">
    <span class="sy-guide-icon">⛟</span>
    読む方向のガイド
  </div>
  <div class="sy-guide-body">
    <p>この記事は長いです。一気に読まなくても大丈夫です。</p>
    <ul class="sy-guide-list">
      <li><strong>初めて読む方は</strong> — Part 1 (race condition) → Part 2 (ロックの家族) → Part 8 (ロックを避けるパターン) だけでも全体像が掴めます</li>
      <li><strong>Stage 2 の核心の答え — 「なぜ時々だけ落ちるか」</strong> — を正面から見たいなら、Part 5 (ハードウェアと MESI) まで読むことをお勧めします</li>
      <li><strong>エンジンの動作原理が気になる方は</strong> — Part 6 (Unity)、Part 7 (Unreal) がメイン</li>
      <li><strong>OS 内部実装は必要なときに</strong> — Part 3 (ロックの作り方)、Part 4 (futex/SRWLock/os_unfair_lock) はリファレンスとして戻ってこられます</li>
    </ul>
    <p class="sy-guide-note">最も深い二箇所 — MESI の状態遷移と Burst のコンパイル 4 段階 — は折りたたみにしてあります。必要なときだけ展開してください。</p>
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
