---
title: Span&lt;T&gt; と ReadOnlySpan&lt;T&gt; — コピーなしでメモリを眺める方法
lang: ja
date: 2026-04-30 09:00:00 +0900
categories: [Csharp, memory]
tags: [csharp, dotnet, memory, span, ref-struct, performance, gc, parsing, il2cpp]
toc: true
toc_sticky: true
chart: true
difficulty: intermediate
prerequisites:
  - /posts/ValueTypeBoxing/
tldr:
  - "`Span<T>` はメモリの任意区間を指す**ビュー (view)** です。配列スライス・部分文字列・スタックバッファを同じ抽象で扱い、データをコピーせずに一部だけ覗き込みます"
  - "`ref struct` という制約は罰則ではなく契約です。「スタックにしか存在しない」という一行のルールが、Boxing・フィールド保持・非同期キャプチャを**コンパイラレベルで**遮断します"
  - "`\"hello\".Substring(1, 3)` は 12 バイトの新しい文字列をアロケートしますが、`\"hello\".AsSpan(1, 3)` は **0 バイト**です。パース・ロギング・バリデーションのように substring を頻繁に作るコードで GC 圧力を一桁下げます"
  - .NET 10 (Apple M4 Pro, Arm64 RyuJIT) の実測で、`string.Substring` + `int.Parse` ベースのパーサーを `Span<char>` ベースに書き換えると **6 倍以上**速くなりアロケーションが消えます
  - "`Span<T>` が入れない場所 — フィールド・非同期メソッド・ラムダキャプチャ — は次回の `Memory<T>` が担います。2 つの型は競合ではなく分業関係です"
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: Boxing 編が残したコピーコスト

[第 1 回 (値型 vs 参照型と Boxing)](/posts/ValueTypeBoxing/) の最後に一つの宿題を残しました。

> "Boxing は避けられたが、`struct` そのものの**コピーコスト**は残る。"

Boxing 編の核心ルールを再掲します。

> 値型は**代入・受け渡し・比較されるとき、内容全体がコピー**されます。

このルールは普段は直感的で望ましいものです。6 バイトの `(short, int)` ペアを関数に渡すとき、コピー一回は無視できるコストです。しかし**データの一部だけを見たいとき**、このコピーのルールが問題を起こします。

```csharp
string line = "ID=42,SCORE=1280,TIME=00:01:32";
string idPart = line.Substring(3, 2);    /* "42" — 新しい string をアロケート */
int id = int.Parse(idPart);              /* もう一度パース */
```

この 2 行は**2 回のヒープアロケーション**を引き起こします。`Substring` が新しい `string` を作り、結果が不要になれば GC に負荷を残します。CSV 1 行をパースするだけの単純なコードが、呼び出しのたびに数十バイトのガベージを生み出します。ゲームループで毎フレーム呼ばれるコードなら、このコストが積み重なります。

問題の本質は**「コピーしなければ一部だけ見ることができない」**という点にあります。その責任を直接解決する型が、今回の主役 `Span<T>` と `ReadOnlySpan<T>` です。

今回の目標は 3 つです。

1. `Span<T>` を「ref struct に封じ込められた pointer + length」という**一つの定義**で理解します
2. この型がなぜ**`ref struct` という強い制約**を受け入れるのか、その制約が解決する問題が何かを確認します
3. 日常コードの substring・split・parse を**アロケーション 0** でどう書き直せるか、.NET 10 の実測で確認します

---

## Part 1. `Span<T>` の正体

### 1.1 一行の定義 — 「メモリのビュー」

`Span<T>` を一行で表すとこうなります。

> "任意のメモリ区間を指す**ポインタ + 長さ**を、安全に扱えるよう封じ込めた型。"

内部表現はシンプルです。

```csharp
public readonly ref struct Span<T>
{
    internal readonly ref T _reference;   /* 開始位置に対するマネージド参照 */
    internal readonly int _length;        /* 長さ */
    /* ... */
}
```

`ref T _reference` は C# 11 以前には直接表現できなかった形です。オブジェクトへの通常の参照ではなく、**オブジェクト内部の任意位置**を指す参照です。配列の中央、文字列の 5 文字目、スタックバッファの先頭 — どこでも指せます。この能力に `_length` を加えるだけで「特定のメモリ区間」を表現できます。

コピーなしに一部だけを見るツールが、まさにこの形をしています。

<div class="sp-anatomy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Span の内部構造 — pointer + length でメモリ区間を封じ込める">
  <text x="380" y="26" text-anchor="middle" class="sp-anatomy-title">Span&lt;T&gt; — メモリ区間を封じ込めた ref struct</text>

  <g>
    <text x="160" y="60" text-anchor="middle" class="sp-anatomy-subtitle">スタック — Span&lt;char&gt; 構造</text>
    <rect x="50" y="80" width="220" height="55" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="105" text-anchor="middle" class="sp-anatomy-text-bold">_reference</text>
    <text x="160" y="123" text-anchor="middle" class="sp-anatomy-text-sm">→ 配列内の位置</text>

    <rect x="50" y="145" width="220" height="50" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="170" text-anchor="middle" class="sp-anatomy-text-bold">_length = 3</text>
    <text x="160" y="187" text-anchor="middle" class="sp-anatomy-text-sm">int</text>
  </g>

  <line x1="270" y1="107" x2="420" y2="155" class="sp-anatomy-arrow" marker-end="url(#sp-anatomy-ah)"/>

  <g>
    <text x="580" y="60" text-anchor="middle" class="sp-anatomy-subtitle">ヒープ — char[] = "hello"</text>
    <rect x="380" y="120" width="370" height="60" rx="6" class="sp-anatomy-box-heap"/>
    <g>
      <rect x="395" y="135" width="50" height="35" class="sp-anatomy-cell"/>
      <text x="420" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'h'</text>
    </g>
    <g>
      <rect x="450" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="475" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'e'</text>
    </g>
    <g>
      <rect x="505" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="530" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'l'</text>
    </g>
    <g>
      <rect x="560" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="585" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'l'</text>
    </g>
    <g>
      <rect x="615" y="135" width="50" height="35" class="sp-anatomy-cell"/>
      <text x="640" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'o'</text>
    </g>
    <text x="565" y="205" text-anchor="middle" class="sp-anatomy-text-xs">⇧ Span はインデックス 1〜3 (3 個) だけを指す</text>
  </g>

  <text x="380" y="250" text-anchor="middle" class="sp-anatomy-text-sm">"hello".AsSpan(1, 3) — 新しい文字列なしで 'e','l','l' だけを公開</text>

  <defs>
    <marker id="sp-anatomy-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="sp-anatomy-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.sp-anatomy-container { margin: 1.5rem 0; overflow-x: auto; }
.sp-anatomy-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.sp-anatomy-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.sp-anatomy-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.sp-anatomy-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.sp-anatomy-box-heap { fill: #dbeafe; stroke: #3b82f6; stroke-width: 1.3; }
.sp-anatomy-cell { fill: #f3f4f6; stroke: #9ca3af; stroke-width: 1; }
.sp-anatomy-cell-active { fill: #fef08a; stroke: #ca8a04; stroke-width: 1.4; }
.sp-anatomy-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.sp-anatomy-text-sm { font-size: 12px; fill: #4b5563; }
.sp-anatomy-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.sp-anatomy-arrow { stroke: #f59e0b; stroke-width: 1.5; fill: none; }
.sp-anatomy-arrow-head { fill: #f59e0b; }
[data-mode="dark"] .sp-anatomy-title { fill: #f3f4f6; }
[data-mode="dark"] .sp-anatomy-subtitle { fill: #d1d5db; }
[data-mode="dark"] .sp-anatomy-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .sp-anatomy-box-heap { fill: #1e3a8a; stroke: #60a5fa; }
[data-mode="dark"] .sp-anatomy-cell { fill: #374151; stroke: #6b7280; }
[data-mode="dark"] .sp-anatomy-cell-active { fill: #ca8a04; stroke: #fde047; }
[data-mode="dark"] .sp-anatomy-text-bold { fill: #f9fafb; }
[data-mode="dark"] .sp-anatomy-text-sm { fill: #d1d5db; }
[data-mode="dark"] .sp-anatomy-text-xs { fill: #9ca3af; }
[data-mode="dark"] .sp-anatomy-arrow { stroke: #fbbf24; }
[data-mode="dark"] .sp-anatomy-arrow-head { fill: #fbbf24; }
@media (max-width: 768px) {
  .sp-anatomy-title { font-size: 14px; }
  .sp-anatomy-subtitle { font-size: 11px; }
  .sp-anatomy-text-bold { font-size: 11px; }
  .sp-anatomy-text-sm { font-size: 10px; }
}
</style>

核心的な違いを一覧で整理します。

| 比較軸 | `string.Substring(1, 3)` | `string.AsSpan(1, 3)` |
|--------|--------------------------|------------------------|
| 新しいオブジェクト | `string` 1 個 (12B + 6B) | なし |
| データコピー | char 3 個 | 0 個 |
| GC 圧力 | あり | なし |
| 受け渡しコスト | 参照 8B | `ref T` + `int` = 16B |
| 寿命 | GC が決定 | 元のメモリに依存 |

`Span<T>` のコストは**元のメモリに寿命が縛られる**という一点だけです。その一行の制約を受け入れると、アロケーションが消えます。

### 1.2 `Span<T>` vs `ReadOnlySpan<T>`

名前の通り、**書き込み可能かどうか**だけで分かれます。

- `Span<T>` — インデクサーが `ref T` を返します。スライス内の要素を直接変更できます
- `ReadOnlySpan<T>` — インデクサーが `ref readonly T` です。読み取り専用のビューです

`string` から取得する `AsSpan()` は常に `ReadOnlySpan<char>` です。`string` は .NET では不変型なので、変更可能なビューを提供できません。逆に `char[]` から取得する `AsSpan()` は `Span<char>` です。

API 設計の観点では、**入力パラメータは `ReadOnlySpan<T>` で受け取り、出力バッファは `Span<T>` で受け取る**パターンが標準です。

```csharp
/* 入力は読み取り専用 — string も char[] も stackalloc も受け取れる */
static int CountVowels(ReadOnlySpan<char> input)
{
    int count = 0;
    foreach (var c in input)
        if ("aeiou".Contains(c)) count++;
    return count;
}

/* 呼び出し側からどんなメモリでも変換コストなしで渡せる */
CountVowels("hello world");                /* string そのまま */
CountVowels("hello world".AsSpan(0, 5));  /* string の一部 */
CountVowels(new char[]{'h','i'});          /* char[] */
Span<char> tmp = stackalloc char[8];       /* スタックバッファ */
CountVowels(tmp);                          /* 変換なしで渡せる */
```

`string` を受け取る API と `char[]` を受け取る API とスタックバッファを受け取る API を別々に作る必要はありません。`ReadOnlySpan<char>` 一つで**あらゆるメモリ出所を統一されたインターフェースで**受け取れます。

### 1.3 それでは、なぜ `ref struct` なのか

`Span<T>` は普通の `struct` ではなく **`ref struct`** として宣言されています。この一語がコンパイラに強い制約を課します。

| 禁止事項 | 理由 |
|---------|------|
| クラス/構造体のフィールドとして保持 | ヒープへ脱出すると `ref T` の安全を保証できない |
| Boxing (`object` へのキャスト) | Boxing はヒープアロケーション。同じ理由 |
| `IDisposable` などの通常インターフェースの実装 | インターフェースキャストは Boxing を伴う |
| `async` メソッドのローカル変数として保持 | async 状態マシンはヒープオブジェクト。同じ理由 |
| ラムダキャプチャ | キャプチャはクロージャ (クラス) に変換されてヒープへ行く |
| `ValueTuple` に入れること | 通常の struct でも Boxing 経路があるため遮断 |

これらすべての禁止事項に共通するのは**ヒープへ漏れる経路**です。`Span<T>` が指すメモリ (特に `stackalloc` されたスタックバッファ) は、メソッドが終わった瞬間に消えます。その消えたメモリを指す `Span` がヒープオブジェクト内に生き残れば、**dangling reference** になります。C++ でライフタイムバグで深夜にデバッグしていたあの問題です。

`ref struct` はその問題を**コンパイラレベルで**遮断します。ランタイム検査なしに静的に防ぎます。これが Boxing 編で強調した「値型の安全」をもう一段引き上げた形です。

> "Span の制約はコストではなく保証です。コンパイラが受け入れるすべてのコードはメモリ安全です。"

この保証の対価として、`Span<T>` をフィールドに入れられず、`async` に持ち込めず、ラムダにキャプチャできないという不便を受け入れます。次回扱う `Memory<T>` がその空席を埋めます。

---

## Part 2. Span の 3 つの出所 — 配列・string・stackalloc

`Span<T>` の強力さは、**3 種類のメモリ出所を同じ抽象で**扱えることにあります。どこから来ても、内部では同じように見えます。

### 2.1 出所① — 配列

最も一般的な出所です。`T[]` の `AsSpan()` は配列全体または一部へのビューを作ります。

```csharp
int[] scores = { 92, 88, 75, 60, 100 };

Span<int> all   = scores.AsSpan();          /* 全体 */
Span<int> top3  = scores.AsSpan(0, 3);      /* 最初の 3 個 */
Span<int> tail  = scores.AsSpan(2);         /* インデックス 2 から末尾まで */

/* スライスのスライスも自由 — 新しいオブジェクト生成なし */
Span<int> middle = top3.Slice(1, 1);        /* { 88 } */

middle[0] = 99;                              /* scores[1] も 99 に変わる */
```

`AsSpan()` は**データをコピーしません**。同じ配列を別のウィンドウで覗くだけです。そのため `middle[0] = 99` が元の配列に影響します。

従来の `ArraySegment<T>` も似たことをしていましたが、`Span<T>` は**インデクサーが `ref T` を返す**ため、単純な読み書きを超えて**コピーなし変換**まで可能です。

### 2.2 出所② — string と ReadOnlySpan&lt;char&gt;

文字列は `Span<T>` が最も活躍する場所です。`string.AsSpan()` は `ReadOnlySpan<char>` を返します。

```csharp
string log = "[2026-04-30 09:00:00] INFO  Player joined: id=42";

ReadOnlySpan<char> bracket = log.AsSpan(1, 19);   /* "2026-04-30 09:00:00" */
ReadOnlySpan<char> level   = log.AsSpan(22, 4);   /* "INFO" */
ReadOnlySpan<char> id      = log.AsSpan(45, 2);   /* "42" */

int playerId = int.Parse(id);   /* .NET Core 2.1+ : ReadOnlySpan<char> オーバーロードあり */
```

`Substring` を 3 回呼ぶと**3 つの新しい string + それだけの GC 負荷**が発生します。`AsSpan` を 3 回なら**アロケーション 0** です。2 つのコードの意味は同じですが、GC 観点のコストは別次元です。

`string` が immutable であることによる追加メリットもあります。元の文字列は絶対に変わらないので、`ReadOnlySpan<char>` が指すメモリも変わりません — race condition を心配する必要がありません。

### 2.3 出所③ — stackalloc

最も魅力的な出所です。**ヒープを一切触らずに**一時バッファを作ります。

```csharp
static long Sum(ReadOnlySpan<int> xs)
{
    long s = 0;
    foreach (var x in xs) s += x;
    return s;
}

void DoWork()
{
    Span<int> buffer = stackalloc int[64];   /* 256B をスタックに確保 */
    for (int i = 0; i < 64; i++) buffer[i] = i * i;

    long total = Sum(buffer);                /* 0 alloc */
}
```

`stackalloc` は C の `alloca` と同じことをします。メソッドのスタックフレーム内に即席バッファを確保し、メソッドが終わるとバッファも消えます。以前の C# では `stackalloc` は `unsafe` コンテキストでしか使えない危険なツールでしたが、**C# 7.2 以降 `Span<T>` と組み合わさって**安全なファーストクラス機能になりました。

ただし 2 点を覚えておく必要があります。

**① スタックサイズ制限** — 一般的に 1MB 程度が OS スレッドのスタック上限です。ゲームクライアントのメインスレッドはそれ以上の場合もありますが、**数 KB 以上の stackalloc は危険**です。推奨は 1KB 以下、安全側には 256B〜512B。

```csharp
const int StackThreshold = 256;
Span<byte> buffer = size <= StackThreshold
    ? stackalloc byte[size]
    : new byte[size];
```

**② Zero-init コスト** — .NET 6 以前は `stackalloc` が確保したメモリをすべて 0 で初期化していました。小さいバッファなら無視できますが、**数百バイト以上**では測定可能なコストになります。

.NET 6+ では `[SkipLocalsInit]` でこの zero-init を無効にできます。

```csharp
using System.Runtime.CompilerServices;

[SkipLocalsInit]
static int FastParse(ReadOnlySpan<char> s)
{
    Span<char> tmp = stackalloc char[64];   /* zero-init 省略 */
    /* tmp の初期内容はゴミ — 使用前に必ず書き込むこと */
    s.CopyTo(tmp);
    /* ... */
}
```

`[SkipLocalsInit]` は**使用前にすべての位置に書き込むという保証**がある場合にのみ使えます。そうでなければ前のスタックフレームの内容がそのまま露出します — セキュリティ上の欠陥になります。

### 2.4 3 つの出所を同じ関数が受け取る

3 種類の出所を一つの関数が受け取れることが、`Span<T>` 設計の真髄です。

```csharp
/* 出所を問わない単一の API */
static double Average(ReadOnlySpan<double> values)
{
    double sum = 0;
    foreach (var v in values) sum += v;
    return values.Length == 0 ? 0 : sum / values.Length;
}

/* 呼び出し側 — 3 つの出所すべて同様に */
double[] heap = { 1.0, 2.0, 3.0 };
Average(heap);                                  /* 配列 */

Span<double> stack = stackalloc double[3] { 1.0, 2.0, 3.0 };
Average(stack);                                 /* スタック */

ReadOnlySpan<double> slice = heap.AsSpan(1, 2);
Average(slice);                                 /* 配列の一部 */
```

以前は `IEnumerable<T>` がこの統合を担っていましたが、`IEnumerable<T>` は**インターフェースディスパッチ + 列挙子オブジェクト**のコストを伴います。`Span<T>` は同じ統合を**0 alloc + 直接インデックスアクセス**で実現します。

---

## Part 3. `ref struct` 制約の深い理由

`Span<T>` を初めて使うと必ず遭遇するコンパイルエラーがあります。なぜこれほど厳しいのか一度整理しておけば、以降は迷いません。

### 3.1 クラスのフィールドに置けない理由

```csharp
class Cache
{
    Span<byte> _buffer;   /* CS8345: ref struct のフィールドは ref struct にのみ許可 */
}
```

もし可能だったとしたら、何が起きるでしょうか。

```csharp
void Setup(byte[] data)
{
    var cache = new Cache();
    cache._buffer = data.AsSpan();
    /* ここまでは問題なさそうに見える */
}

void Setup2()
{
    var cache = new Cache();
    Span<byte> tmp = stackalloc byte[256];
    cache._buffer = tmp;     /* tmp はこのメソッドが終わると消える */
    /* cache が生き続けていれば _buffer は dangling reference */
}
```

`stackalloc` のメモリはメソッド終了とともに消えます。そのメモリを指す `Span` がクラス (ヒープ) 内に生き残れば、直ちに **use-after-free** です。C# はこの可能性自体をコンパイル段階で防ぎます。

`ref struct` のフィールドは別の `ref struct` にしか置けません。そうすることでコンテナも同じ制約を継承し、すべての道がスタックへとつながります。

### 3.2 `async` メソッドとラムダに入れられない理由

```csharp
async Task BadAsync(byte[] data)
{
    Span<byte> view = data.AsSpan();   /* CS4012: ref struct は async に使用不可 */
    await Task.Yield();
    Console.WriteLine(view.Length);
}
```

`async` メソッドはコンパイラが**状態マシンクラス (または struct)** に変換します。`await` を越えて生き残る必要があるすべてのローカル変数は、その状態マシンの**フィールド**になります。`Span<T>` はクラスのフィールドになれないため、`await` を越えて生き続けることができません。

ラムダも同じ理由です。キャプチャされた変数はコンパイラが生成する **display class** のフィールドになり、そのクラスはヒープへ行きます。

```csharp
void BadLambda()
{
    Span<int> nums = stackalloc int[4] { 1, 2, 3, 4 };
    Func<int> first = () => nums[0];   /* CS8175: ref struct をラムダでキャプチャ不可 */
}
```

解決策は 2 つです。

**(a) 同期ヘルパーに分離** — `await` の前にデータを処理します。

```csharp
async Task GoodAsync(byte[] data)
{
    int sum = SyncSum(data.AsSpan());     /* Span はここだけで生きる */
    await SaveAsync(sum);
}

static int SyncSum(ReadOnlySpan<byte> view) { /* ... */ }
```

**(b) `Memory<T>` を使用** — 非同期の境界を越える必要があれば、次回の `Memory<T>` に切り替えます。`Memory<T>` は通常の `struct` なので async・ラムダ・フィールドに自由に入れられます。

### 3.3 インターフェースキャストと Boxing の禁止

```csharp
ReadOnlySpan<int> view = ...;
IEnumerable<int> seq = view;   /* CS0030: ref struct はインターフェースに変換不可 */
object o = view;               /* CS0029: Boxing 禁止 */
```

Boxing 編で見た通りです。インターフェースキャストと `object` キャストは Boxing を伴い、Boxing はヒープアロケーションです。`Span<T>` がヒープへ行くすべての道は塞がれています。

`Span<T>` で `LINQ` が使えないのもこのためです。`LINQ` は `IEnumerable<T>` ベースであり、`Span<T>` はインターフェースを実装できません。代替は **Span 専用のメソッド群** — `Sum`、`Contains`、`IndexOf` など `MemoryExtensions` に蓄積された拡張メソッド — または**手動の `for`/`foreach` ループ**です。

### 3.4 回避策 — `scoped` キーワードと ref 安全性規則

C# 11 で `scoped` キーワードが追加され、`ref struct` パラメータのライフタイムルールをより明確に表現できるようになりました。

```csharp
/* パラメータ view がメソッド外に漏れないことを保証 */
static int Sum(scoped ReadOnlySpan<int> view)
{
    int s = 0;
    foreach (var v in view) s += v;
    return s;   /* int のみ返す — Span 自体は漏れない */
}
```

`scoped` が付いた `ref struct` パラメータは、**呼び出し元のライフタイムを侵害できないよう**強く制限されます。ライブラリを書くとき、呼び出し元がより自由にさまざまな出所 (stackalloc 含む) から Span を渡せるようにする仕組みです。

このルールをすべて暗記する必要はありません。**コンパイルエラーが出たら「この Span はどこへ漏れているか？」と自問する**習慣一つで十分です。

---

## Part 4. 日常コードの中の Span 活用

理論の次は実践です。毎日使うコードパターンのどこをどう変えるかを見ていきます。

### 4.1 `Substring` → `AsSpan().Slice()`

最もよく遭遇する変換です。

```csharp
/* 毎回の呼び出しで新しい string をアロケート */
string GetExtension(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? "" : path.Substring(dot);
}

/* アロケーション 0 — 呼び出し元が ReadOnlySpan<char> で受け取れる場合 */
ReadOnlySpan<char> GetExtensionSpan(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? ReadOnlySpan<char>.Empty : path.AsSpan(dot);
}
```

呼び出し元が結果を**長期保持する必要があれば** Span 返却は適しません。その場合は普通に `string` を返すか (元の string はどうせ GC 対象)、`Memory<T>` に切り替えます。**すぐに使って捨てる substring** のときだけ Span にします。

### 4.2 `int.Parse` の進化 — string 引数 → ReadOnlySpan&lt;char&gt; 引数

.NET Core 2.1 から数値パース API が `ReadOnlySpan<char>` オーバーロードを持っています。

```csharp
string raw = "X=42,Y=88,Z=12";

/* Substring → Parse — 3 回の string アロケーション */
int x = int.Parse(raw.Substring(2, 2));
int y = int.Parse(raw.Substring(7, 2));
int z = int.Parse(raw.Substring(12, 2));

/* AsSpan → Parse(ReadOnlySpan<char>) — 0 alloc */
int x2 = int.Parse(raw.AsSpan(2, 2));
int y2 = int.Parse(raw.AsSpan(7, 2));
int z2 = int.Parse(raw.AsSpan(12, 2));
```

同じパターンが `double.Parse`、`DateTime.Parse`、`Guid.TryParse` まで一貫して適用されます。標準 BCL のすべての主要パース API が既に Span オーバーロードを持っています。

### 4.3 `string.Split` → `MemoryExtensions.Split` (または `SpanSplitEnumerator`)

`string.Split` は結果を `string[]` で返すため、**要素数だけの substring + 配列自体**をアロケートします。CSV 1 行を split するのはコードの中でも最も高コストな操作のひとつです。

```csharp
/* 8 トークン → 9 個のオブジェクト (配列 1 + string 8) */
string line = "id,name,score,time,region,mode,season,build";
string[] tokens = line.Split(',');

/* .NET 8+ — 0 alloc パーサー */
ReadOnlySpan<char> view = line.AsSpan();
foreach (Range r in view.Split(','))
{
    ReadOnlySpan<char> token = view[r];   /* 新しい string なし */
    /* token に対して処理 */
}
```

.NET 8 で追加された `MemoryExtensions.Split(ReadOnlySpan<T>, T)` は結果として `Range` シーケンスを返します。トークン自体は呼び出し元が元の Span からインデックスアクセスして取得します。結果として **0 alloc で split** が可能になります。

.NET 7 以前では `IndexOf` を自分で回して split するヘルパーを短く書けば済みます。

```csharp
static IEnumerable<Range> Split(ReadOnlySpan<char> s, char sep)
{
    int start = 0;
    for (int i = 0; i < s.Length; i++)
    {
        if (s[i] == sep)
        {
            yield return new Range(start, i);
            start = i + 1;
        }
    }
    yield return new Range(start, s.Length);
}
/* ⚠️ 上記コードは yield return + ReadOnlySpan<char> パラメータの衝突で動作しない */
/* Span は iterator メソッドのパラメータになれない — 次節参照 */
```

ここでまた `ref struct` 制約が顔を出します。`yield return` はコンパイラが状態マシンを生成する場所です — `Span<T>` は入れられません。実践では `ref struct` enumerator を自作するか (例: `SpanSplitEnumerator`)、インデックス配列をあらかじめ埋めておいて呼び出し元が走査する形にします。

### 4.4 Encoding · Hash · シリアライズ

標準ライブラリの**低レベル変換 API** はほぼすべて Span ベースに整備されています。

```csharp
/* UTF-8 エンコード */
ReadOnlySpan<char> text = "안녕하세요".AsSpan();
Span<byte> buffer = stackalloc byte[64];
int written = Encoding.UTF8.GetBytes(text, buffer);
/* buffer.Slice(0, written) がエンコードされた UTF-8 バイト列 */

/* SHA256 */
ReadOnlySpan<byte> data = ...;
Span<byte> hash = stackalloc byte[32];
SHA256.HashData(data, hash);

/* JSON Reader */
ReadOnlySpan<byte> json = ...;
Utf8JsonReader reader = new(json);
```

**`stackalloc` + Span 入出力の組み合わせ**は 0 alloc シリアライズ/ハッシュパイプラインの標準形です。

### 4.5 `ArrayPool<T>` 先行紹介

`stackalloc` の限界は 1KB 程度です。より大きな一時バッファが必要なとき、それでも毎回 `new byte[]` で GC を刺激したくないとき、**`ArrayPool<T>`** が登場します。

```csharp
byte[] rented = ArrayPool<byte>.Shared.Rent(8192);
try
{
    Span<byte> view = rented.AsSpan(0, 8192);
    /* view を使用 */
}
finally
{
    ArrayPool<byte>.Shared.Return(rented);
}
```

`ArrayPool` で借りた配列を `Span<T>` として参照しながら使い、終わったらプールに返します。このパターンが **ASP.NET Core の標準バッファリング方式**です。次回 (`Memory<T>` + `ArrayPool<T>`) で本格的に扱います。

---

## Part 5. ベンチマーク — Substring ベース vs Span ベース

ここからは実測です。**.NET 10.0.100** + **BenchmarkDotNet 0.14.0**、環境は Boxing 編と同じく **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD** 基準です。計測コードはゲームドメインの例 (ログパース・部分抽出・一時バッファ比較) で記述しています。

### 5.1 ログパース — `Substring` + `int.Parse` vs `Span` ベース

**シナリオ**: `"[2026-04-30 09:00:00] PlayerId=42,Score=1280,Region=3"` 形式のログ 1,000 行から PlayerId・Score・Region の 3 つを抽出。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + int.Parse(string)** | 142.6 μs | 1.00 | 144,000 B |
| **AsSpan + int.Parse(ReadOnlySpan&lt;char&gt;)** | 22.3 μs | **0.16** | 0 B |

同じ意味のコードが **6.4 倍**速く、GC アロケーションが**完全に消えます**。1,000 行のパースで約 144KB のアロケーションが 0 B になります — 毎フレーム呼ばれるコードなら 30 フレームで 4MB のガベージを削減できる計算です。

### 5.2 substring + 即時比較 — Equals vs SequenceEqual

**シナリオ**: ファイルパス 10,000 個に対して拡張子が `".png"` かどうかを検査。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + string.Equals** | 187.4 μs | 1.00 | 320,000 B |
| **EndsWith(string)** | 39.6 μs | 0.21 | 0 B |
| **AsSpan().EndsWith(span)** | 28.8 μs | **0.15** | 0 B |

`EndsWith` だけでも substring を作らずに済みますが、**呼び出し側が既に ReadOnlySpan を持っている場合**は Span バージョンがさらに速くなります。この差は小さく見えますが、呼び出し頻度が高ければ積み重なります。

### 5.3 一時バッファ — new vs ArrayPool vs stackalloc

**シナリオ**: 256 バイトの一時バッファを関数内で作って埋めて合算。10,000 回繰り返し。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`new byte[256]`** | 6.42 ms | 1.00 | 2,640,000 B |
| **`ArrayPool.Rent(256)`** | 4.18 ms | 0.65 | 0 B |
| **`stackalloc byte[256]`** | 1.97 ms | **0.31** | 0 B |
| **`stackalloc` + `[SkipLocalsInit]`** | 1.42 ms | **0.22** | 0 B |

`stackalloc` は GC を触らないだけでなく、**メモリアクセスパターン自体**がキャッシュフレンドリーなのでさらに速くなります。`[SkipLocalsInit]` で zero-init まで切ると追加の高速化が得られます。

ただし 256 バイトを超えると危険です。8KB が一時的に必要なら `ArrayPool` が正解です。

<div class="chart-wrapper">
  <div class="chart-title">Span ベース変換 — 最適 (1.0x) 基準の相対実行時間 · 対数スケール</div>
  <canvas id="spanBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'spanBench',
  type: 'bar',
  data: {
    labels: ['ログパース (1000行)', 'EndsWith (10000個)', '一時バッファ (10000回)'],
    datasets: [
      {label:'Span / stackalloc', data:[0.16,0.15,0.22], backgroundColor:'rgba(76,175,80,0.75)', borderColor:'rgba(76,175,80,1)', borderWidth:1.5},
      {label:'中間経路', data:[null,0.21,0.65], backgroundColor:'rgba(255,152,0,0.75)', borderColor:'rgba(255,152,0,1)', borderWidth:1.5},
      {label:'従来 (Substring / new)', data:[1.00,1.00,1.00], backgroundColor:'rgba(244,67,54,0.75)', borderColor:'rgba(244,67,54,1)', borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic', min:0.05, max:1.5, title:{display:true,text:'従来比の倍率 (対数スケール)'}, grid:{color:'rgba(128,128,128,0.15)'}, ticks:{callback:function(v){return v+'x';}}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom', labels:{padding:16, usePointStyle:true, pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+(ctx.parsed.y===null?'N/A':ctx.parsed.y.toFixed(2)+'x');}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 5.4 この数値が示すこと

3 つのベンチマークに共通するパターンです。

1. **substring 一回 → 新しい string 一回のアロケーション**です。その substring をすぐ捨てるなら、そのアロケーションは 100% 無駄です。Span で受け取れば、その無駄がゼロになります
2. **Span ベースのコードが速い理由はアロケーションがないだけでなく、データコピーがないから**です。256 バイトの substring 1,000 個は 256KB の追加メモリ書き込みです。キャッシュ圧力としても計測されます
3. **`stackalloc` は小さく短い一時バッファの正解**です。256B 以下 + メソッド終了前に使い終わる — この 2 条件が揃えば常に最速です

---

## Part 6. Unity / IL2CPP の観点

`Span<T>` は Unity ランタイムでも動作しますが、CoreCLR とは異なる圧力と制限を受けます。

### 6.1 対応バージョンとバックエンド

`Span<T>` が BCL に入ったのは .NET Core 2.1 / .NET Standard 2.1 です。Unity 基準では:

- **Unity 2021.2 以前** — `System.Memory` NuGet パッケージを別途追加すれば使用可能。ただし Mono バックエンドの一部最適化は欠ける
- **Unity 2021.2 〜 2022.2** — `.NET Standard 2.1` 互換プロファイルを有効にすれば標準 BCL そのままで使用可能
- **Unity 2022.3 LTS 以降** — デフォルトで有効。**AsSpan、MemoryExtensions、stackalloc + Span すべて正常動作**

IL2CPP ビルドでも `Span<T>` は正常に動作します。**C++ に変換した後のコードも同じ意味を持つよう** IL2CPP が `ref struct` の安全規則を守ります。

### 6.2 `NativeArray<T>` と `Span<T>` の関係

Unity 固有のコレクション `NativeArray<T>` は **GC 外**のメモリを扱います。C# メモリシリーズとは別の世界ですが、`AsSpan()` という接点があります。

```csharp
NativeArray<float> velocities = new(1024, Allocator.TempJob);

/* NativeArray → Span として借りて参照 */
Span<float> view = velocities.AsSpan();

/* 標準 Span API をそのまま使用 */
view.Fill(0f);
view.Slice(0, 256).CopyTo(view.Slice(256));
```

`NativeArray<T>.AsSpan()` は Unity 2021.2+ で提供されています。**アロケーションは発生しません** — `NativeArray` が指す unmanaged メモリに対する Span を作るだけです。

これにより同じ関数が `T[]` も `NativeArray<T>` も `stackalloc` もすべて受け取れるようになります。

```csharp
static float Average(ReadOnlySpan<float> values) { /* ... */ }

/* 3 つとも同様に呼び出せる */
float[] heap = new float[1024];
Average(heap);

NativeArray<float> native = new(1024, Allocator.Temp);
Average(native.AsSpan());

Span<float> stack = stackalloc float[256];
Average(stack);
```

### 6.3 Burst と Span — 互換性と制限

Burst コンパイラは `NativeArray<T>` と `Span<T>` の両方を認識し、SIMD 最適化の対象として扱います。ただし以下を覚えておく必要があります。

- Burst Job 内では**マネージド配列の Span は使用できません**。Burst が GC オブジェクトを扱わないためです
- `NativeArray<T>.AsSpan()` は OK
- `stackalloc` は Burst 内でも動作 — 内部的にスタックメモリは unmanaged のため

**Job 内コードが 0 alloc + Burst SIMD 加速**を同時に受ける最も一般的な形が `NativeArray + AsSpan + stackalloc 一時バッファ`の組み合わせです。

### 6.4 IL2CPP での `ref struct` 追跡

IL2CPP は IL を C++ に変換しながら `ref struct` のライフタイム規則をそのまま持ち込みます。C# コンパイラが受け入れたコードは IL2CPP でも受け入れられます — 追加検証は不要です。

ただし一点注意が必要なのは、**Span の `_reference` フィールド**が IL2CPP でどう表現されるかです。マネージド配列を指す Span は IL2CPP では **GC ハンドル + オフセット**として表現され、インデックスアクセスのたびにわずかなオーバーヘッドがあります。それでも Mono バックエンドより一般的に高速です。

ベンチマーク観点では、**Editor / Mono / IL2CPP の 3 環境で同じ計測**を行って初めて正確なコストが分かります。Boxing 編と同様に — **デプロイ対象のバックエンドで計測**が原則です。

### 6.5 Unity でよく出る活用パターン

**① 毎フレームの string 加工**

```csharp
/* TextMeshPro ラベルに毎フレーム新しい string */
void Update()
{
    label.text = "HP: " + currentHp + " / " + maxHp;
    /* string.Concat → 新しい string + boxed int 2 個の可能性 */
}

/* Span ベースのフォーマット (.NET 6+ の文字列補間は内部的に Span を活用) */
void Update()
{
    label.text = $"HP: {currentHp} / {maxHp}";
    /* C# 10+ DefaultInterpolatedStringHandler が Span プールを使用 */
}
```

C# 10+ の補間文字列は内部的に `DefaultInterpolatedStringHandler` を通じて **Span ベースの一時バッファ**を使います。Boxing が消えアロケーションが一回に減ります — Boxing 編 4.4 節で見たことと同じです。

**② ネットワークパケットのデコード**

```csharp
/* パケット受信 — 長さ 4B ヘッダー + ペイロード */
ReadOnlySpan<byte> packet = recvBuffer.AsSpan(0, recvLen);
int payloadLen = BinaryPrimitives.ReadInt32LittleEndian(packet[..4]);
ReadOnlySpan<byte> payload = packet.Slice(4, payloadLen);
/* payload 処理 — 0 alloc */
```

`recvBuffer` をプールから借りて (`ArrayPool<byte>.Shared.Rent(...)`)、その上で Span によりスライスするパターンがゲームネットワーキングの標準です。

**③ 大きな struct を Span にキャスト (`MemoryMarshal`)**

```csharp
/* 低レベルメモリ変換 — 同じメモリを別の型で見る */
Span<Vector3> verts = ...;
Span<float> floats = MemoryMarshal.Cast<Vector3, float>(verts);
/* Vector3 1024 個 → float 3072 個 — データそのまま、ビューだけ変わる */
```

`MemoryMarshal` は Span の**再解釈 (reinterpret) API** をまとめたクラスです。シェーダーにデータを渡すとき、シリアライズで byte を別の型として見るときに非常に便利です。

---

## まとめ

今回の核心を 4 行で整理します。

1. **`Span<T>` はデータをコピーせずに任意のメモリ区間を覗くビュー**です。配列・文字列・`stackalloc` の 3 出所を同じ抽象で扱い、その上で動作する BCL API (`int.Parse`、`Encoding.UTF8.GetBytes`、`MemoryExtensions.Split`、`MemoryMarshal.Cast`) が 0 alloc コードの部品となります
2. **`ref struct` の制約はコストではなく安全の保証**です。フィールド・async・ラムダキャプチャの禁止はすべて「Span が指すメモリが消えた後に生き続ける道を塞ぐため」に存在します。コンパイラレベルで防がれることは、ランタイムのバグになるよりも常に良いです
3. **substring + parse パターンはゲームコードで最も一般的な 0 alloc 変換候補**です。.NET 10 Arm64 計測で同じ意味のパーサーが 6 倍以上速くなり、GC アロケーションが完全に消えました。毎フレーム呼ばれるコードから優先的に確認する価値があります
4. **`stackalloc` は小さく短い一時バッファの正解**です。256B 以下 + メソッド内で完結 — この 2 条件が揃えば `ArrayPool` よりも速くなります。それを超えると次回の `ArrayPool` 領域です

---

## シリーズの接続: 次回予告

今回残した 2 つの問題が次回へと続きます。

- **`Span<T>` は `async`・フィールド・ラムダに入れられない**: 第 3 回 **`Memory<T>` + `ArrayPool<T>`** がその空席を担います。非同期の境界でもプールされたバッファを安全に持ち運べるようになります
- **大きな一時バッファは stackalloc で確保できない**: 同じ第 3 回で `ArrayPool<T>.Shared.Rent`/`Return` パターンで解決します
- **`struct` そのもののコピーコスト — `in`・`readonly struct`・`ref struct`**: 第 4 回がその場所です

C# メモリシリーズ第 2 回はここまでです。

---

## 参考資料

### 1 次ソース・公式ドキュメントおよび標準

- [Microsoft Learn — `Span<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.span-1) · 公式リファレンス
- [Microsoft Learn — `ReadOnlySpan<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.readonlyspan-1) · 公式リファレンス
- [Microsoft Learn — `MemoryExtensions` Class](https://learn.microsoft.com/en-us/dotnet/api/system.memoryextensions) · Span 専用拡張メソッド集
- [Microsoft Learn — `MemoryMarshal` Class](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.memorymarshal) · Span 再解釈 API
- [Microsoft Learn — `stackalloc` (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/stackalloc) · `stackalloc` 公式解説
- [Microsoft Learn — `[SkipLocalsInit]` Attribute](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.skiplocalsinitattribute) · zero-init 無効化
- [Microsoft Learn — `scoped` modifier](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/ref) · ref 安全性規則

### ブログ・詳細分析

- [.NET Blog — "All About Span: Exploring a New .NET Mainstay"](https://learn.microsoft.com/en-us/archive/msdn-magazine/2018/january/csharp-all-about-span-exploring-a-new-net-mainstay) · Stephen Toub, Span 導入の背景
- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) · Stephen Toub, Span 関連の最適化項目
- [Adam Sitnik — "Span"](https://adamsitnik.com/Span/) · Span の内部構造とライフタイム分析

### 計測ツール

- [BenchmarkDotNet 公式ドキュメント](https://benchmarkdotnet.org/) · `[MemoryDiagnoser]`、`[SimpleJob]` の使い方
- [sharplab.io](https://sharplab.io/) · C# コード → IL / JIT コードのリアルタイム変換

### ゲームランタイムの観点

- [Unity Manual — `NativeArray<T>`](https://docs.unity3d.com/ScriptReference/Unity.Collections.NativeArray_1.html) · NativeArray 公式リファレンス
- [Unity Blog — "On DOTS: C# & the Burst Compiler"](https://unity.com/blog/engine-platform/on-dots-c-burst) · Burst と Span の互換性
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/IL2CPP.html) · IL2CPP の動作原理
