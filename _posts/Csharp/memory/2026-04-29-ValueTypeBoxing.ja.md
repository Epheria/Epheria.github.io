---
title: 値型 vs 参照型 — スタック・ヒープと Boxing の隠れたコスト
lang: ja
date: 2026-04-29 09:00:00 +0900
categories: [Csharp, memory]
tags: [csharp, dotnet, memory, value-type, boxing, performance, gc, il2cpp]
toc: true
toc_sticky: true
chart: true
difficulty: intermediate
prerequisites:
  - /posts/DotnetRuntimeVariants/
tldr:
  - 値型が「スタックに置かれる」という説明は半分しか正しくありません。フィールドの配置先は**そのフィールドを保持するコンテナ**が決定します。クラスフィールド内の値型はヒープに存在し、配列要素の値型もヒープに存在し、ラムダがキャプチャした値型もヒープに存在します
  - Boxing は「object に変換される瞬間」ではなく、**値型が参照契約 (object・非ジェネリックインターフェース) と出会う瞬間**に発生します。`string.Format`・`Dictionary`・`IEnumerable` に対する `foreach` まで、日常コードのあらゆる場所に潜んでいます
  - Boxing された値は元の値の**コピー**であるため、元の値を変更しても Box は変わりません。この非対称性がデバッグしにくいバグを生み出します
  - .NET 10 (Apple M4 Pro, Arm64 RyuJIT) での実測結果、値型の `Equals` は `IEquatable<T>` の実装有無によって**95倍以上の速度差**が生じます。Boxing は単純な GC の問題ではなく、**CPU パフォーマンスの問題**でもあります
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 「スタック vs ヒープ」という説明が食い違う理由

C# の教科書の最初のページで、私たちはこう学びます。

> "値型 (struct) はスタックに、参照型 (class) はヒープに格納されます。"

この文章は**間違いではないのですが**、実務で直面するほぼすべての反例を覆い隠してしまいます。クラスのフィールドとして `int` を宣言すると、その `int` はスタックではなく**オブジェクトが存在するヒープ内**に存在します。ラムダがローカルの `struct` 変数をキャプチャすると、その `struct` も**ヒープに置かれたクロージャ内**に存在することになります。JIT が `struct` を**レジスタのみで扱う**場合、スタックにもヒープにも「格納」されません。

「スタック vs ヒープ」という言葉が登場するたびに注意すべきことがあります。**「どのコンテナの中にあるか」が本質的な問い**だということです。

この記事の目的は2つです。

1. **値型と参照型を「格納場所」ではなく「コピーのルール」として再定義する**
2. **値型が Boxing される瞬間**がどこなのか、なぜコストが高いのか、どう回避するかを具体的に示す

計測は .NET 10 上で BenchmarkDotNet により実測し、IL は RyuJIT が実際に出力するものをそのまま引用しています。ゲームプログラマが IL2CPP で遭遇する Boxing の落とし穴も最後のセクションでまとめます。

---

## Part 1. 値型と参照型の真の違い

### 1.1 「スタック/ヒープ」ではなく「コピーのルール」

値型と参照型を分ける決定的な違いは、**アロケーションされたときに起きること**ではなく、**代入・受け渡し・比較されたときに起きること**です。

- **値型**: 代入時に**内容全体がコピー**されます。新しい変数は独立したコピーを持ちます。
- **参照型**: 代入時に**オブジェクトを指すポインタ (参照) のみコピー**されます。元の変数とコピーは同じオブジェクトを参照します。

<div class="vt-copy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="値型と参照型のコピーセマンティクス比較">
  <text x="380" y="26" text-anchor="middle" class="vt-copy-title">値型 vs 参照型 — コピーの意味</text>

  <g class="vt-copy-left">
    <text x="180" y="60" text-anchor="middle" class="vt-copy-subtitle">struct Position — 値型</text>

    <rect x="40" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="105" text-anchor="middle" class="vt-copy-text-bold">a</text>
    <text x="100" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <rect x="200" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="260" y="105" text-anchor="middle" class="vt-copy-text-bold">b = a</text>
    <text x="260" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>
    <text x="260" y="143" text-anchor="middle" class="vt-copy-text-xs">(独立コピー)</text>

    <text x="180" y="180" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒</text>
    <rect x="40" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="215" text-anchor="middle" class="vt-copy-text-sm">a.X = 1 (変化なし)</text>
    <rect x="200" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct-alt"/>
    <text x="260" y="215" text-anchor="middle" class="vt-copy-text-sm">b.X = 999</text>
  </g>

  <g class="vt-copy-right">
    <text x="580" y="60" text-anchor="middle" class="vt-copy-subtitle">class Player — 参照型</text>

    <rect x="420" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="470" y="110" text-anchor="middle" class="vt-copy-text-bold">a = 0x00AF</text>

    <rect x="540" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="590" y="110" text-anchor="middle" class="vt-copy-text-bold">b = 0x00AF</text>

    <rect x="620" y="150" width="120" height="70" rx="6" class="vt-copy-box-heap"/>
    <text x="680" y="175" text-anchor="middle" class="vt-copy-text-bold">ヒープ 0x00AF</text>
    <text x="680" y="195" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <line x1="520" y1="130" x2="620" y2="155" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>
    <line x1="640" y1="130" x2="670" y2="150" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>

    <text x="580" y="250" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒ a.X も 999</text>
  </g>

  <defs>
    <marker id="vt-copy-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-copy-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-copy-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-copy-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.vt-copy-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-copy-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.vt-copy-box-struct { fill: #dbeafe; stroke: #3b82f6; stroke-width: 1.3; }
.vt-copy-box-struct-alt { fill: #fde68a; stroke: #f59e0b; stroke-width: 1.3; }
.vt-copy-box-ref { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.3; }
.vt-copy-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-copy-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-copy-text-sm { font-size: 12px; fill: #4b5563; }
.vt-copy-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-copy-arrow { stroke: #6366f1; stroke-width: 1.4; fill: none; }
.vt-copy-arrow-head { fill: #6366f1; }
[data-mode="dark"] .vt-copy-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-copy-subtitle { fill: #d1d5db; }
[data-mode="dark"] .vt-copy-box-struct { fill: #1e3a8a; stroke: #60a5fa; }
[data-mode="dark"] .vt-copy-box-struct-alt { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-copy-box-ref { fill: #312e81; stroke: #a78bfa; }
[data-mode="dark"] .vt-copy-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-copy-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-copy-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-copy-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-copy-arrow { stroke: #a78bfa; }
[data-mode="dark"] .vt-copy-arrow-head { fill: #a78bfa; }
@media (max-width: 768px) {
  .vt-copy-title { font-size: 14px; }
  .vt-copy-subtitle { font-size: 11px; }
  .vt-copy-text-bold { font-size: 11px; }
  .vt-copy-text-sm { font-size: 10px; }
}
</style>

「格納場所がどこか」は、このコピーセマンティクスの**結果**に過ぎません。値型はコピーが軽量であるべきなので主にスタック (またはインライン) に置かれ、参照型は寿命が不確定なのでヒープに置いて参照で管理されます。**原因と結果を逆に覚えると、反例に直面したときに対処できなくなります。**

### 1.2 同等性比較も異なります

コピーのルールが異なる以上、同等性の判定も異なります。

- **値型の `Equals`**: デフォルト実装は**リフレクションでフィールドを1つずつ比較**します (`ValueType.Equals(object)`)。Boxing + リフレクションの二重コスト
- **参照型の `Equals`**: デフォルト実装は**参照同一性** (`ReferenceEquals`) を確認します — 同じオブジェクトを指しているかどうかのみを判定

この違いは Part 5 のベンチマークで数値として確認します。値型を `Dictionary` のキーとして使ったり `List.Contains` で検索したりするとき、`IEquatable<T>` を直接実装しないと、比較のたびに**Boxing とリフレクションの両方のコストを支払う**ことになります。

### 1.3 可変性の落とし穴

値型がコピーされるというルールから最も頻繁に発生するバグは、**可変 `struct` をコレクションに入れた後で変更しようとする試み**です。

```csharp
/* 可変 struct の落とし穴 */
struct Counter
{
    public int Value;
    public void Increment() => Value++;
}

var list = new List<Counter> { new Counter() };
list[0].Increment();        /* コンパイルエラー: list[0] は値 (コピー) なので変更不可 */

var copy = list[0];
copy.Increment();            /* copy のみが変わり、リスト内の元の値はそのまま */
```

多くの C# スタイルガイドが **`struct` は不変 (`readonly struct`) として**使うよう推奨している理由がここにあります。可変 `struct` は「値」という本質とプログラマの直感が衝突し、不具合を生みます。このテーマは第4回の `readonly struct` と `ref struct` で改めて取り上げます。

---

## Part 2. 「値型はスタック」が間違っている3つのケース

教科書の一文を少し言い換えてみましょう。

> "値型は**自身を保持するコンテナと同じ場所**に格納されます。"

この一文の方がはるかに正確です。ローカル変数として宣言された `struct` のみがスタックに置かれ、それ以外の場合はコンテナに従います。

### 2.1 クラスフィールド内の値型 → ヒープ

```csharp
class Enemy
{
    public Vector3 Position;   /* 値型だがヒープに存在 */
    public int Hp;              /* 同じくヒープ */
}

var e = new Enemy();            /* e はヒープに Enemy オブジェクトをアロケート */
                                /* Position と Hp はそのオブジェクト内にインライン格納 */
```

<div class="vt-inline-container">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="クラスフィールド内の値型はヒープに存在する">
  <text x="360" y="26" text-anchor="middle" class="vt-inline-title">class Enemy のメモリレイアウト</text>

  <g>
    <rect x="40" y="70" width="160" height="50" rx="6" class="vt-inline-box-stack"/>
    <text x="120" y="95" text-anchor="middle" class="vt-inline-text-bold">スタック</text>
    <text x="120" y="112" text-anchor="middle" class="vt-inline-text-sm">e (参照, 8バイト)</text>
  </g>

  <line x1="200" y1="95" x2="340" y2="140" class="vt-inline-arrow" marker-end="url(#vt-inline-ah)"/>

  <g>
    <rect x="340" y="70" width="340" height="200" rx="8" class="vt-inline-box-heap"/>
    <text x="510" y="98" text-anchor="middle" class="vt-inline-text-bold">ヒープ — Enemy オブジェクト</text>

    <rect x="360" y="115" width="300" height="40" rx="4" class="vt-inline-box-header"/>
    <text x="510" y="140" text-anchor="middle" class="vt-inline-text-sm">ObjectHeader + MethodTable (16バイト)</text>

    <rect x="360" y="160" width="300" height="50" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="180" text-anchor="middle" class="vt-inline-text-sm">Position (struct Vector3)</text>
    <text x="510" y="198" text-anchor="middle" class="vt-inline-text-xs">X, Y, Z — ヒープにインライン</text>

    <rect x="360" y="215" width="300" height="45" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="240" text-anchor="middle" class="vt-inline-text-sm">Hp — ヒープにインライン</text>
  </g>

  <defs>
    <marker id="vt-inline-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-inline-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-inline-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-inline-container svg { width: 100%; max-width: 720px; height: auto; display: block; margin: 0 auto; }
.vt-inline-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-inline-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.vt-inline-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-inline-box-header { fill: #fbcfe8; stroke: #db2777; stroke-width: 1; }
.vt-inline-box-field { fill: #fde2e8; stroke: #f472b6; stroke-width: 1; }
.vt-inline-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-inline-text-sm { font-size: 12px; fill: #4b5563; }
.vt-inline-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-inline-arrow { stroke: #ec4899; stroke-width: 1.4; fill: none; }
.vt-inline-arrow-head { fill: #ec4899; }
[data-mode="dark"] .vt-inline-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-inline-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-inline-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-inline-box-header { fill: #9d174d; stroke: #f9a8d4; }
[data-mode="dark"] .vt-inline-box-field { fill: #9f1239; stroke: #fda4af; }
[data-mode="dark"] .vt-inline-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-inline-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-inline-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-inline-arrow { stroke: #f472b6; }
[data-mode="dark"] .vt-inline-arrow-head { fill: #f472b6; }
@media (max-width: 768px) {
  .vt-inline-title { font-size: 14px; }
  .vt-inline-text-bold { font-size: 11px; }
  .vt-inline-text-sm { font-size: 10px; }
}
</style>

`Position` は **`Vector3` という値型**ですが、`Enemy` という**参照型の中にインライン**されているため、ヒープ上に置かれます。ここで「値型はスタック」というルールは崩れます。

### 2.2 配列要素 → ヒープ

```csharp
var positions = new Vector3[1000];
positions[0] = new Vector3(1, 2, 3);    /* 値 1000個がヒープ上の配列にインライン */
```

配列は参照型です (`T[]`)。したがって配列要素はヒープ上の配列オブジェクト内にインライン格納されます。`Vector3[1000]` は**スタックバッファではなく、ヒープ上の 12KB の連続領域**です。この**ヒープ上の連続レイアウト**こそが、第3回で登場する `Span<T>` が活躍する基盤となります。

### 2.3 ラムダキャプチャ → ヒープ (クロージャ)

```csharp
void Setup()
{
    var count = new Counter();              /* ローカル値型 */
    Action handler = () => count.Value++;   /* count をキャプチャ */
                                             /* コンパイラが秘密のクラスを生成し count をそこに格納 */
                                             /* 結果: count はヒープ上のクロージャオブジェクト内に */
}
```

ラムダがローカル変数をキャプチャすると、コンパイラは**キャプチャされた変数をフィールドとして持つ秘密のクラス** (display class) を生成します。そのクラスは当然参照型でありヒープにアロケートされるため、元はスタックにあったはずの `struct` もヒープに移動します。

これら3つのケースを理解すれば、「値型はスタック」が繰り返し食い違う理由が見えてきます。**「自身を保持するコンテナと同じ場所」**というルール1つの方がはるかに一貫しています。

### 2.4 JIT の最終反転 — Escape Analysis とスタックアロケーション

ここまでは**ソースレベルのルール**です。実際の実行時には JIT がさらに一段ひっくり返します。

.NET の RyuJIT は **Escape Analysis** で「このオブジェクトがメソッドの外に脱出するか」を判定します。脱出しない場合はヒープアロケーションを省略し、**スタックにアロケート**します。.NET 9 から本格導入されたこの最適化は .NET 10 でジェネリック・仮想呼び出し境界まで拡張されました。

つまりソースに `new SomeClass()` と書いても、そのオブジェクトがメソッド内でのみ使われ他の場所に漏れ出さなければ、**実際にはスタックにアロケートされる**可能性があります。逆に値型を Boxing した瞬間、Boxing されたオブジェクトは必ずヒープに行かなければなりません — 参照が脱出するためです。

**「ソースコードだけを見てアロケーション場所を断定できない」**というのが現代の .NET の現実です。信頼できるのは**計測**だけです。BenchmarkDotNet の `[MemoryDiagnoser]` が必須である理由がここにあります。

---

## Part 3. Boxing メカニズム

値型と参照型の境界を**強引に越えるとき**に何が起きるかを見ていきます。その出来事を **Boxing** と呼びます。

### 3.1 Boxing の定義

Boxing は**値型のコピーを新しいヒープオブジェクトの中に包む**操作です。逆は **Unboxing** — ヒープに Boxing された値を取り出してスタック (またはレジスタ) に持ってくる操作です。

<div class="vt-box-container">
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Boxing シーケンス図">
  <text x="380" y="26" text-anchor="middle" class="vt-box-title">Boxing — スタックの値がヒープのオブジェクトにコピーされる過程</text>

  <g>
    <text x="130" y="70" text-anchor="middle" class="vt-box-subtitle">① スタックの値型</text>
    <rect x="60" y="85" width="140" height="55" rx="6" class="vt-box-stack"/>
    <text x="130" y="108" text-anchor="middle" class="vt-box-text-bold">int i = 42</text>
    <text x="130" y="126" text-anchor="middle" class="vt-box-text-sm">スタック, 4バイト</text>
  </g>

  <g>
    <text x="380" y="70" text-anchor="middle" class="vt-box-subtitle">② object 参照が必要</text>
    <rect x="290" y="85" width="180" height="55" rx="6" class="vt-box-stack"/>
    <text x="380" y="108" text-anchor="middle" class="vt-box-text-bold">object o = i;</text>
    <text x="380" y="126" text-anchor="middle" class="vt-box-text-xs">コンパイラが box 命令を挿入</text>
  </g>

  <g>
    <text x="630" y="70" text-anchor="middle" class="vt-box-subtitle">③ ヒープに Box 生成</text>
    <rect x="540" y="85" width="180" height="55" rx="6" class="vt-box-heap"/>
    <text x="630" y="106" text-anchor="middle" class="vt-box-text-bold">ヒープ: Box&lt;int&gt; = 42</text>
    <text x="630" y="124" text-anchor="middle" class="vt-box-text-sm">ヘッダ 16B + 値 4B ≈ 24B</text>
  </g>

  <line x1="200" y1="110" x2="290" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>
  <line x1="470" y1="110" x2="540" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>

  <g>
    <text x="380" y="190" text-anchor="middle" class="vt-box-subtitle">④ Boxing 後に元の値を変更すると?</text>

    <rect x="60" y="210" width="180" height="60" rx="6" class="vt-box-stack"/>
    <text x="150" y="235" text-anchor="middle" class="vt-box-text-bold">i = 999 (スタック)</text>
    <text x="150" y="255" text-anchor="middle" class="vt-box-text-xs">元の値のみ変わる</text>

    <rect x="520" y="210" width="200" height="60" rx="6" class="vt-box-heap"/>
    <text x="620" y="235" text-anchor="middle" class="vt-box-text-bold">Box&lt;int&gt; = 42 (ヒープ)</text>
    <text x="620" y="255" text-anchor="middle" class="vt-box-text-xs">Box はそのまま (コピー)</text>

    <line x1="240" y1="240" x2="520" y2="240" class="vt-box-arrow-dotted"/>
    <text x="380" y="235" text-anchor="middle" class="vt-box-text-xs">独立</text>
  </g>

  <defs>
    <marker id="vt-box-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-box-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-box-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-box-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.vt-box-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-box-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.vt-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.vt-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-box-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-box-text-sm { font-size: 12px; fill: #4b5563; }
.vt-box-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-box-arrow { stroke: #6366f1; stroke-width: 1.4; fill: none; }
.vt-box-arrow-head { fill: #6366f1; }
.vt-box-arrow-dotted { stroke: #9ca3af; stroke-width: 1.2; fill: none; stroke-dasharray: 4 3; }
[data-mode="dark"] .vt-box-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-box-subtitle { fill: #d1d5db; }
[data-mode="dark"] .vt-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-box-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-box-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-box-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-box-arrow { stroke: #a78bfa; }
[data-mode="dark"] .vt-box-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .vt-box-arrow-dotted { stroke: #6b7280; }
@media (max-width: 768px) {
  .vt-box-title { font-size: 14px; }
  .vt-box-subtitle { font-size: 11px; }
  .vt-box-text-bold { font-size: 11px; }
  .vt-box-text-sm { font-size: 10px; }
}
</style>

図の要点は④ のステップです。**Boxing された値は元の値と独立したコピー**です。元の値を変更しても Box は変わらず、Box を変更しても (可能であれば) 元の値は変わりません。この非対称性が次のセクションで扱う微妙なバグの根源です。

### 3.2 IL レベルでの確認

C# が生成した IL には、Boxing が **`box`** と **`unbox.any`** という2つの命令として明示的に残ります。次の2つのメソッドをコンパイルすると、IL はこのようになります (.NET 10 Release ビルド基準)。

```csharp
public static object BoxInt(int value) => value;
public static int UnboxInt(object boxed) => (int)boxed;
```

```text
BoxInt:
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32
  IL_0006: ret

UnboxInt:
  IL_0000: ldarg.0
  IL_0001: unbox.any [System.Runtime]System.Int32
  IL_0006: ret
```

- **`box [T]`**: スタックの値を取り出してヒープに `T` 用の Box オブジェクトをアロケートし、値をコピーして格納した後、Box の参照をスタックに積みます
- **`unbox.any [T]`**: ヒープの Box オブジェクトから `T` の値を取り出してスタックに積みます (型が異なる場合は `InvalidCastException`)

「object にキャストすると Boxing される」という説明は正しいですが、**正確にどの IL 命令がそれを行うか**を把握することで、Boxing が「おそらく起きる」ではなく「必ず起きる」と確信できます。

### 3.3 隠れた Boxing — `Equals(object)`

Boxing がより暗黙的に見える例をもう一つ示します。

```csharp
public static bool CompareViaObject(int a, int b)
{
    object oa = a;
    object ob = b;
    return oa.Equals(ob);
}
```

IL を見ると Boxing が**2回**発生しています。

```text
CompareViaObject:
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32    /* a をヒープに Boxing */
  IL_0006: ldarg.1
  IL_0007: box [System.Runtime]System.Int32    /* b をヒープに Boxing */
  IL_000c: stloc.0
  IL_000d: ldloc.0
  IL_000e: callvirt instance bool [System.Runtime]System.Object::Equals(object)
  IL_0013: ret
```

2つの `int` を比較するだけで **24バイト × 2 = 48バイトのヒープアロケーション**が発生します。さらに `Equals(object)` 呼び出し時に内部で Unboxing + 比較ルーティンが実行されるため、**CPU コストも伴います**。このコストは Part 5 のベンチマークで具体的な数値として再び登場します。

### 3.4 Boxing されたコピーは独立している

Boxing がコピーを生成するという事実を IL で確認します。

```csharp
public static object MutateAfterBox()
{
    var p = new Point2D(1, 2);
    object boxed = p;
    p.X = 999;
    return boxed;           /* boxed.X は 1 か 999 か? */
}
```

```text
IL_0000: ldloca.s 0                          /* &p (スタックアドレス) */
IL_0004: call Point2D::.ctor(int32, int32)   /* スタックの p を初期化 */
IL_0009: ldloc.0                             /* p の値をスタックトップへ */
IL_000a: box BoxingIL.Point2D                /* ヒープにコピーの Box を生成 */
IL_000f: ldloca.s 0                          /* &p (再びスタックアドレス) */
IL_0011: stfld int32 Point2D::X              /* スタックの p.X = 999 */
IL_001b: ret                                 /* Box (ヒープ) を返す */
```

`p.X = 999` の代入は**スタックの `p`**にのみ作用します (`ldloca.s 0` でスタックアドレスを取得)。ヒープの Box は `box` 命令の直後から**完全に独立**しているため、`boxed.X` は依然として `1` です。

このルールが微妙なバグを生み出します。

```csharp
/* アンチパターン */
var state = new GameState();
RegisterInterface((IStatefulObject)state);   /* Boxing 発生 (struct state → interface) */
state.Score = 100;                           /* スタックの state のみ変わる */
                                              /* Register に渡した Box は Score=0 のまま */
```

インターフェースへのキャストは Boxing を引き起こし、その瞬間に値のコピーが独立します。`struct` をインターフェースコレクションに入れた瞬間、元の変更が反映されない「凍結されたコピー」が生まれます。**この問題が第4回の `readonly struct`・`ref struct` へと続きます。**

---

## Part 4. 日常コードの中の Boxing 落とし穴

Boxing は明示的な `object` キャストより**はるかに日常的な場所**に潜んでいます。頻繁に遭遇する5つのパターンを整理します。

### 4.1 `Dictionary<TKey, TValue>` — キーが `Equals(object)` 経路を通るケース

`Dictionary` はキーの比較を `EqualityComparer<TKey>.Default` で処理します。`TKey` が `IEquatable<TKey>` を実装していれば `Equals(TKey)` の直接呼び出し — **Boxing なし**。実装していなければ `ValueType.Equals(object)` 経路 — **Boxing + リフレクション基準の比較**。

リーダーボードキャッシュのように**複数の enum を組み合わせた複合キー**がよく登場するパターンです。同じキャッシュをフィルタ軸ごとに保持したい場合、enum 3〜4個をフィールドとして持つ `struct` キーが自然な選択です。

```csharp
/* Unity/クライアントでよく使うリーダーボードキャッシュキー — 3軸 enum の組み合わせ */
public enum Region : byte { NA, EU, APAC, SA }
public enum Season : byte { Spring, Summer, Autumn, Winter }
public enum Mode : byte { Solo, Duo, Squad }

/* IEquatable なし — 検索のたびに ValueType.Equals(object) → Boxing + リフレクション */
public readonly struct LeaderboardKeyBad
{
    public readonly Region Region;
    public readonly Season Season;
    public readonly Mode Mode;
}

/* IEquatable + GetHashCode オーバーライド — Boxing を完全排除 */
public readonly struct LeaderboardKey : IEquatable<LeaderboardKey>
{
    public readonly Region Region;
    public readonly Season Season;
    public readonly Mode Mode;

    public LeaderboardKey(Region r, Season s, Mode m) { Region = r; Season = s; Mode = m; }

    public bool Equals(LeaderboardKey other) =>
        Region == other.Region && Season == other.Season && Mode == other.Mode;

    public override bool Equals(object obj) => obj is LeaderboardKey o && Equals(o);
    public override int GetHashCode() => HashCode.Combine((int)Region, (int)Season, (int)Mode);
}

/* 使用例 — 検索経路が完全に Boxing フリー */
Dictionary<LeaderboardKey, LeaderboardCache> _caches;
var key = new LeaderboardKey(Region.APAC, Season.Summer, Mode.Squad);
if (_caches.TryGetValue(key, out var cache)) { /* ... */ }
```

値型を `Dictionary` のキーとして使う場合は、**`IEquatable<T>` の実装が基本**です。struct フィールドを `readonly` にすると防御コピーも合わせて排除されます (第4回の `readonly struct` で詳述)。`GetHashCode` も一貫してオーバーライドする必要がありますが、`HashCode.Combine` がある以上、手動のシフト・XOR を書く理由はありません。

### 4.2 非ジェネリック `IEnumerable` に対する `foreach`

ジェネリック導入以前のコレクション (`ArrayList`、`Hashtable`) を `foreach` で反復すると、すべての要素が `object` として扱われ、**反復のたびに Boxing・Unboxing** が発生します。

```csharp
var list = new ArrayList { 1, 2, 3 };
foreach (int i in list)          /* 反復ごとに unbox.any が発生 */
    Console.WriteLine(i);
```

ジェネリック `List<int>` に変えれば Unboxing がなくなり、JIT は int 専用のループをインライニングします。現代のコードに `ArrayList`・`Hashtable`・`Queue` (非ジェネリック) を使う理由はありませんが、**古いライブラリの境界でこれらのコレクションが渡ってくる場合は、一度にジェネリック版に昇格させる**のが最も簡単な最適化です。

### 4.3 `string.Format` と補間文字列

```csharp
Console.WriteLine(string.Format("Score: {0}, Time: {1}", score, time));
/* score, time が値型の場合は両方 Boxing (object[] で渡されるため) */

Console.WriteLine($"Score: {score}, Time: {time}");
/* C# 10 以前: string.Format と同等 → Boxing */
/* C# 10+: DefaultInterpolatedStringHandler がジェネリック Append<T> を使用 → Boxing なし */
```

C# 10 (.NET 6) から導入された**補間文字列ハンドラー** (`DefaultInterpolatedStringHandler`) は Boxing を完全に排除します。この機能はコンパイラバージョンに依存するため、`LangVersion` 設定を合わせるだけですべてのプロジェクトで自動的に恩恵を受けられます。ただし **`string.Format` を直接呼び出した場合**は引き続き `object[]` 経路を通るため、Boxing が残ります。

### 4.4 ログ・トレースにおける Boxing の連鎖

ロギングライブラリが `params object[]` を受け取ると、ログ1行あたり値型の数だけ Boxing が発生します。

```csharp
logger.LogInformation("Player {PlayerId} scored {Score} at {Time}", playerId, score, time);
```

ASP.NET 系であれば **Source Generator ベースの `LoggerMessage`** を使えば Boxing が排除されます。

```csharp
[LoggerMessage(Level = LogLevel.Information,
    Message = "Player {PlayerId} scored {Score} at {Time}")]
partial void LogPlayerScore(long playerId, int score, DateTime time);
```

**Unity の場合は事情が異なります。** `Debug.Log`/`Debug.LogFormat` は内部的に `string.Format` 系を通るため、それ自体が Boxing + ヒープ文字列アロケーションの発生源です。

```csharp
/* Unity — score が float の場合は Boxing、文字列も毎回アロケート */
Debug.LogFormat("Damage dealt: {0}", damageAmount);

/* Unity 2022 LTS 以下 — 補間文字列も string.Format にリライト → 同等のコスト */
Debug.Log($"Damage dealt: {damageAmount}");

/* Unity 6 (C# 11 LangVersion) — DefaultInterpolatedStringHandler 経路で Boxing 排除 */
Debug.Log($"Damage dealt: {damageAmount}");   /* 内部実装が異なる */

/* 最も安全 — リリースビルドでコンパイルアウト */
[System.Diagnostics.Conditional("UNITY_EDITOR"), System.Diagnostics.Conditional("DEVELOPMENT_BUILD")]
static void DevLog(string msg) => UnityEngine.Debug.Log(msg);
```

ゲームランタイムが毎秒数千行のログを出力する場合、この差が Profiler に現れる GC.Alloc を有意に削減します。リリースビルドでは `[Conditional]` 属性で**呼び出し自体をコンパイラが除去**するのが最善です。

### 4.5 `List<T>.Contains` — デフォルト比較子経路

`List<T>.Contains` は内部で `EqualityComparer<T>.Default` を使用します。`T` が `IEquatable<T>` を実装していない値型の場合、やはり **Boxing 経路**を通ります。`Dictionary` キーのケースとまったく同じ話です。

より広く見ると、**値型が「ジェネリックだが比較が必要なコレクション」の要素またはキーになるすべてのケース**が該当します。`HashSet<T>`、`Dictionary<TKey,TValue>`、`SortedSet<T>`、`List<T>.Contains/IndexOf/Remove`… すべてが対象です。

### 4.6 ゲームイベント構造体と `in` パラメータ

リアルタイムゲームではイベントバス (オブザーバー・メッセージパイプ等) を通じて毎秒数百〜数千のイベントが流れます。こうしたイベントを `class` で作るとその発生頻度だけ GC.Alloc が生じ、`struct` で作っても**フィールドが増えるとコピーコストが Boxing コストを超える**ことがあります。答えは `readonly struct` + `in` パラメータの組み合わせです。

```csharp
/* 入力イベント — 6フィールド、毎フレーム複数回発行される可能性あり */
public readonly struct DragEvent
{
    public readonly int PointerId;
    public readonly Vector2 ScreenPosition;
    public readonly Vector2 Delta;
    public readonly Vector2 TotalDelta;
    public readonly DragPhase Phase;        /* enum */
    public readonly float Timestamp;

    public DragEvent(int pid, Vector2 pos, Vector2 delta, Vector2 total, DragPhase phase, float ts)
    {
        PointerId = pid; ScreenPosition = pos; Delta = delta;
        TotalDelta = total; Phase = phase; Timestamp = ts;
    }
}

/* 値渡し — 6フィールド (約 36バイト) が呼び出しのたびにコピー */
public interface IDragSubscriber { void OnDrag(DragEvent evt); }

/* in 渡し — 参照で読み取り専用渡し、コピーなし */
public interface IDragSubscriber { void OnDrag(in DragEvent evt); }
```

イベント**本体がない**シグナルのみ必要な場合 (状態変更通知等) は 0バイトのマーカー構造体を使います。`class` シングルトンや `static event` を使わずにも型ベースのディスパッチが可能です。

```csharp
/* 0バイトマーカー — Boxing なしでもイベントバスで型識別のみでディスパッチ */
public readonly struct StaminaChangedSignal { }
public readonly struct MatchEndedSignal { }

/* データを持つマーカーは readonly struct で */
public readonly struct ItemStockChanged
{
    public readonly int ItemId;
    public readonly int NewStock;
    public ItemStockChanged(int id, int stock) { ItemId = id; NewStock = stock; }
}

/* MessagePipe のようなジェネリックイベントバスで使えば Boxing 経路が一切ない */
_bus.Publish(new StaminaChangedSignal());
_bus.Publish(new ItemStockChanged(itemId, stock));
```

このパターンの核心は、**「値型 = 速い」ではなく「フィールドが増えるまでは値型、それ以降は `in` で参照渡し」**という段階的な戦略です。`in` パラメータと `readonly struct` の相互作用は第4回でベンチマークとともに再び登場します。

---

## Part 5. ベンチマーク — Boxing の実際のコスト

ここからは実測データです。**.NET 10.0.100** + **BenchmarkDotNet 0.14.0** で3つのシナリオを計測しました。環境は **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD** 基準で、計測コードはそれぞれ独立したゲームドメインの例 (リーダーボードキャッシュキー、リスト合算、3D座標比較) として記述しています。元の計測結果とソースはこの記事と同じコミットのベンチマークプロジェクトで確認できます。

### 5.1 `Dictionary` 検索 — `IEquatable<T>` vs デフォルト比較

**シナリオ**: `Region × Season × Mode` 3軸 enum をフィールドとして持つ `readonly struct` をキーとするリーダーボードキャッシュ。48個のキーをすべて検索するコストを計測。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **IEquatable 実装あり** | 208.2 ns | 1.00 | 0 B |
| **IEquatable なし (ValueType.Equals)** | 988.8 ns | 4.79 | 3,456 B |

`IEquatable<T>` を実装しない場合、`Dictionary` はキーを **Boxing** した上で `ValueType.Equals(object)` をリフレクション基準で呼び出します。結果は 48個のキー検索単位で**4.79倍遅く**、3.4KB のヒープアロケーションが追加で発生します。検索頻度が高くなるほど差は線形に拡大します。

### 5.2 `List<int>` vs `ArrayList` — 反復と Unboxing

**シナリオ**: 整数 10,000個をコレクションに格納して `foreach` で合算。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`List<int>` foreach** | 3.604 μs | 1.00 | 0 B |
| **`ArrayList` foreach** | 13.320 μs | 3.70 | 48 B |
| **`ArrayList` for ループ** | 10.943 μs | 3.04 | 0 B |

`ArrayList` の Boxing コストは**値そのものにだけかかるわけではありません**。`foreach` は `IEnumerator` を経由することで列挙子の Box (48バイト) を追加でアロケートし、反復のたびに型チェックと Unboxing を行います。`for` ループに変えると列挙子の Boxing はなくなりますが要素の Unboxing は残るため、依然として3倍遅くなります。**ジェネリックコレクションに切り替える**ことが `ArrayList` から脱出する唯一の正しい方向です。

### 5.3 値型の `Equals` — `IEquatable<T>` の効果

**シナリオ**: `Point3` (X, Y, Z float) 1,000個の配列からターゲットと同じ要素を数える。3つのバリエーション。

| メソッド | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **デフォルト `ValueType.Equals(object)`** | 30,540 ns | 1.00 | 160,096 B |
| **`override Equals` (object 引数)** | 2,883 ns | 0.09 | 32,000 B |
| **`IEquatable<T>` 実装** | 321.4 ns | **0.01** | 0 B |

3段階の差が値型パフォーマンスの本質をそのまま示しています。

- **デフォルト `ValueType.Equals(object)`**: リフレクションでフィールドを比較しながら引数はもちろん内部比較ルーティンまで Boxing — 1,000回の比較で 160KB アロケート
- **`override Equals(object)`**: リフレクションはなくなりますが引数が `object` のため **Boxing はそのまま** — 32KB (値 32B × 1,000)、パフォーマンスは 10倍改善
- **`IEquatable<T>.Equals(T)`**: Boxing が完全に消えることで**デフォルト比で 95倍**、`override` 比でさらに 9倍の追加改善。JIT によるインライニングも可能に

10行程度の `IEquatable<T>` 実装が値型パフォーマンスの上限を決定します。

<div class="chart-wrapper">
  <div class="chart-title">Boxing コスト 3シナリオ — 最適 (1.0x) 基準の相対実行時間・対数スケール</div>
  <canvas id="boxingBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'boxingBench',
  type: 'bar',
  data: {
    labels: ['Dictionary 検索 (IEquatable キー)', 'List<int> vs ArrayList', 'struct Equals 3段階'],
    datasets: [
      {label:'最適',data:[1.00,1.00,1.00],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5},
      {label:'中間',data:[null,3.04,8.97],backgroundColor:'rgba(255,152,0,0.75)',borderColor:'rgba(255,152,0,1)',borderWidth:1.5},
      {label:'最悪 (Boxing 経路)',data:[4.79,3.70,95.02],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic',min:0.9,max:120,title:{display:true,text:'基準に対する倍率 (対数スケール)'},grid:{color:'rgba(128,128,128,0.15)'},ticks:{callback:function(v){return v+'x';}}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom',labels:{padding:16,usePointStyle:true,pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+(ctx.parsed.y===null?'N/A':ctx.parsed.y.toFixed(2)+'x');}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 5.4 この数値が示すこと

3つのベンチマークに共通するパターンです。

1. **Boxing は GC の問題であると同時に CPU の問題**です。ヒープアロケーションが増え、ポインタのデリファレンスが増え、`callvirt` が型チェックを伴うため、CPU サイクルも線形に増加します
2. **`IEquatable<T>` の実装は「後で最適化するもの」ではなく「値型のデフォルト」**です。10行にも満たないコードが数倍のパフォーマンス差を生み出します
3. **コレクションに値型を入れる前に**「このコレクションは要素・キーをどのように比較・ハッシュ・反復するか」を一度は確認する必要があります

---

## Part 6. Unity / IL2CPP の視点 — ゲームプログラマの視点から

値型と Boxing は Unity ランタイム (Mono・IL2CPP) において **CoreCLR とは異なる圧力**を受けます。同じコードが同じ意味で動作しますが、ボトルネックの生じ方が異なります。

### 6.1 Boxing は IL2CPP でも依然として `GC Alloc`

IL2CPP は IL を C++ に変換してネイティブコンパイルしますが、**GC は依然として保守的 GC** (Boehm ベース) を使用します。Boxing されたオブジェクトはヒープアロケーションの対象であり、Unity Profiler では **`GC.Alloc` として計上**されます。

問題はモバイルの GC です。Unity のデフォルト GC は **Stop-the-world** 方式のため、コレクションがトリガーされるとフレーム全体が停止します。iOS・Android の実機でフレームスパイクが発生する典型的な原因が**毎フレーム発生する Boxing** です。

### 6.2 Unity でよく見られる Boxing パターン

Unity プロジェクトで `Profiler → GC Alloc` を開いたときに上位に頻繁に現れる原因と、それぞれの修正パターンです。

**① ユーザー定義 struct キーに `IEquatable<T>` が未実装**

```csharp
/* Profiler で Hashtable.Equals → ValueType.Equals → Boxing が検出される */
public struct EnemyKey { public int Id; public int Level; }
Dictionary<EnemyKey, EnemyStats> _stats;

/* IEquatable<T> + HashCode.Combine */
public readonly struct EnemyKey : IEquatable<EnemyKey>
{
    public readonly int Id;
    public readonly int Level;
    public EnemyKey(int id, int lv) { Id = id; Level = lv; }
    public bool Equals(EnemyKey other) => Id == other.Id && Level == other.Level;
    public override bool Equals(object obj) => obj is EnemyKey o && Equals(o);
    public override int GetHashCode() => HashCode.Combine(Id, Level);
}
```

**② `UnityEvent<T>` の引数に値型**

`UnityEvent<T>` はインスペクタバインディングのために内部的に `object[]` 経路を混在させます。値型の引数を使うたびに Boxing が発生する可能性があります。

```csharp
/* UnityEvent<int> に Invoke → Boxing 発生の可能性 */
public UnityEvent<int> OnScoreChanged;
OnScoreChanged.Invoke(currentScore);

/* ジェネリックイベントバス (MessagePipe, UniRx Subject<T> 等) — Boxing なし */
readonly Subject<int> _scoreChanged = new();
_scoreChanged.OnNext(currentScore);
```

**③ `Debug.LogFormat` と高頻度ロギング**

4.4 で扱ったパターンの Unity 版。リリースビルドでは `[Conditional("UNITY_EDITOR")]` ラッパーで呼び出し自体をコンパイルアウト。

**④ 旧 Mono の `foreach` Boxing**

Unity 2020 以前の Mono では、`List<T>.Enumerator` が構造体でも特定の経路で `foreach` が Boxing を引き起こすバージョンがありました。Unity 2022.3 LTS 以降の Mono ではほぼ解決されていますが、**サードパーティコレクション** (Unity 以外の dll として配布されるデータ構造等) では依然として発生する可能性があります。疑わしい場合は Deep Profile で `System.Collections.IEnumerator.MoveNext` のコールスタックを確認するのが早道です。

**⑤ `struct` のインターフェースへのキャスト**

3.4節で見た「凍結されたコピー」パターン。Unity では `IEnumerable`・`IComparable` 等に値型を暗黙的にキャストするコードが残りやすく、その瞬間に Boxing が発生し、コピー独立性のバグも伴います。

### 6.3 Profiler での Boxing 探索方法

Unity Profiler で Boxing を発見するための実務手順です。

```csharp
/* ProfilerMarker で疑わしい区間を分離 — Editor・Development Build で動作 */
using Unity.Profiling;

static readonly ProfilerMarker s_TickEnemies = new("Gameplay.TickEnemies");

void Update()
{
    using (s_TickEnemies.Auto())
    {
        foreach (var e in _enemies) e.Tick();
    }
}
```

このマーカーを付けると Profiler で該当区間の **GC.Alloc バイト数とコールスタック**を一緒に確認できます。次のオプションを有効にすると Boxing 探索の効率が大幅に向上します。

- **Deep Profile + GC.Alloc フィルタ** — Boxing の直接原因となるコールスタックを追跡。ただし Deep Profile 自体のオーバーヘッドが大きいため、**疑わしいシーン・機能にのみ限定**して有効化
- **Allocation Callstacks** — GC.Alloc がどのメソッドで何バイトアロケートしたかをスタック全体で記録。Unity 2020.2+ で提供
- **Memory Profiler パッケージ** — スナップショット間の差分で特定フレームに発生した Boxing オブジェクトの種類 (Boxing された `Int32`・`Vector3` 等) を直接確認可能
- **IL2CPP ビルド vs Mono ビルド の比較** — 同じ Boxing でもバックエンドごとにコスト差があるため、最適化の検証は**デプロイ対象のバックエンドで**直接計測して実際の効果を確認する必要があります

### 6.4 `readonly struct` と `in` パラメータ — 次の記事の予告

Unity コードで大きな `struct` (例: 6〜10フィールドのイベントデータ) を毎フレームハンドラーに渡す際、**コピーコストが Boxing コストを超える**ことがあります。このコストは `in` パラメータ (.NET の**参照で読み取り専用渡し**) で排除します。

```csharp
/* 値コピー — 6フィールドが呼び出しのたびにコピー */
void OnDrag(DragEventData data) { ... }

/* 参照渡し — コピーなし、読み取り専用 */
void OnDrag(in DragEventData data) { ... }
```

`in` は第4回で `readonly struct`・`ref struct` とともに本格的に取り上げます。この記事の目標は **Boxing を認識して IL レベルで確認する**ところまでです。

---

## まとめ

この記事の要点を4つに整理します。

1. **「値型 = スタック」ではなく「値型 = コンテナに従う」**と覚えることで、反例に直面しても揺らぎません。クラスフィールド・配列要素・ラムダキャプチャにおいて値型はヒープに存在し、JIT の escape analysis はその逆方向にも作用します
2. **Boxing は `box` / `unbox.any` という IL 命令**として明示的に発生します。C# ソースで「object にキャスト」といった曖昧な表現よりも、**IL で実際に何が挿入されるか**を基準に判断する方が確実です
3. **Boxing された値は元の値と独立したコピー**であるという事実が微妙なバグを生み出します。元の変更が Box に反映されないため、`struct` をインターフェースコレクションに入れるパターンは**凍結されたコピー**を生み出します
4. **`IEquatable<T>` の実装は値型における選択肢ではなくデフォルト**です。これ一つが `Dictionary`・`HashSet`・`List.Contains` のパフォーマンスを**数倍単位**で左右します

---

## シリーズの接続: 次の記事の予告

この記事で残した2つの問題が次の記事へと続きます。

- **Boxing は避けたが `struct` 自体のコピーコスト**: 第3回 **`Span<T>` / `ReadOnlySpan<T>`** で「コピーではなくビュー」として解決します
- **長期保持が必要なバッファ、非同期境界**: 第4回 **`Memory<T>` + `ArrayPool<T>`** でプーリングと非同期互換を扱います
- **コピーコスト自体をなくすパラダイム**: 第5回 **`readonly struct` / `ref struct` / `in` パラメータ**

C# メモリシリーズ第1回はここまでです。

---

## 参考資料

### 1次ソース・公式ドキュメントおよび標準

- [ECMA-335 — Common Language Infrastructure (CLI) Partition III Section 4](https://ecma-international.org/publications-and-standards/standards/ecma-335/) · `box` / `unbox.any` IL 命令の公式定義
- [Microsoft Learn — box (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/user-defined-conversion-operators) · 値型と Boxing の公式解説
- [Microsoft Learn — IEquatable<T> Interface](https://learn.microsoft.com/en-us/dotnet/api/system.iequatable-1) · `IEquatable<T>` 公式リファレンス
- [Microsoft Learn — EqualityComparer<T>.Default](https://learn.microsoft.com/en-us/dotnet/api/system.collections.generic.equalitycomparer-1.default) · `Dictionary`/`HashSet` が使用するデフォルト比較子

### ブログ・詳細分析

- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) · Stephen Toub、escape analysis の拡張を含む
- [.NET Blog — "Performance Improvements in .NET 9"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-9/) · スタックアロケーション初期導入の分析
- [Microsoft Learn — "DefaultInterpolatedStringHandler"](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.defaultinterpolatedstringhandler) · C# 10 補間文字列ハンドラー

### 測定ツール

- [BenchmarkDotNet 公式ドキュメント](https://benchmarkdotnet.org/) · `[MemoryDiagnoser]`、`[SimpleJob]` の使い方
- [sharplab.io](https://sharplab.io/) · C# コード → IL / JIT コードのリアルタイム変換

### ゲームランタイムの視点

- [Unity Manual — Understanding automatic memory management](https://docs.unity3d.com/Manual/performance-managed-memory.html) · Unity GC の動作原理
- [Unity Manual — Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@1.0/manual/) · Boxing 追跡用ツール
- [Unity Blog — "IL2CPP Internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) · IL2CPP の Boxing 処理実装
