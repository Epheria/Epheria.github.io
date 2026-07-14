---
title: "C# はどのように実行され、どのように自分自身を読むのか"
lang: ja
date: 2026-06-02 09:00:00 +0900
categories: [Csharp, internals]
tags: [csharp, dotnet, il, jit, aot, il2cpp, reflection, roslyn, source-generator, metadata]
toc: true
toc_sticky: true
difficulty: advanced
prerequisites:
  - /posts/DotnetEcosystemMap/
  - /posts/DotnetRuntimeVariants/
tldr:
  - C# コードは一気に機械語にはなりません。まず **IL（中間言語）** になり、その IL を**いつ翻訳するか**（実行中 JIT / ビルド時 AOT）によって JIT・NativeAOT・IL2CPP の三分岐に分かれます
  - IL はレジスタのない **スタックマシン** です。Boxing・仮想ディスパッチ・文字列連結のようにソースが隠していたコストが命令として現れ、`if`・`for` は条件分岐に平坦に展開されます
  - コードを「テキストではなく意味として」読むには、コンパイラの段階（**字句解析 → 構文木 → セマンティックモデル → シンボル**）が必要です。grep はトークンすら通っていない生テキストしか見ません。この仕事をライブラリとして切り出したのが **Roslyn** です
  - 決定的な緊張は一つです。**「ランタイムで新しいコードを作れるか。」** JIT はでき、AOT はできません。だから Reflection の動的機能・Roslyn は AOT と衝突し、**Source Generator**（コンパイル時メタプログラミング）がその衝突を避けます
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## この記事が出発した場所

いつか Unity プロジェクトの C# コードを**分析する小さなツール**を作ろうと決めました。「この Presenter のこのメソッドが、実際にどの実装を呼ぶのか」を辿ってくれるツールです。コードを書く前に、二つの問いに行き詰まりました。

1. **このツール自体をどうビルドして配布するか？** — C# で作ったこの実行ファイルを、どんな形で出せば速くて軽いか
2. **このツールが C# コードをどう*読む*ようにするか？** — テキスト検索では無理そうだが、では何で

二つの問いの表面はどちらも「ツール設計」でしたが、答えを探すうち結局 **「C# コードはいったいどう実行され、どう自分自身を理解するのか」** という底まで降りなければなりませんでした。この記事はその一周の記録です。ツールはあくまで**問いを投げたきっかけ**にすぎず、重心はその過程で出会った技術 — IL・JIT・AOT・Reflection・Roslyn — の**動作原理**に置きます。

- **第 1 部**は最初の問いから出発します。C# の一行が CPU に届くまで、何が起きるか。
- **第 2 部**は二つ目の問いです。コードをテキストではなく*意味*として読むとはどういうことか。
- **第 3 部**で二つの問いが衝突します。その衝突がツールの設計を、ひいては現代 .NET の方向を説明します。

> [Foundation シリーズ](/posts/DotnetEcosystemMap/) では .NET スタックの**地図**（言語・IL・ランタイムの層構造）を描きました。この記事はその地図のマスを開き、**実際のメカニズム**に入ります。地図と重なる概要は短く触れ、その下へ掘り下げます。

---

# 第 1 部. コードが機械語になるまで

## 一気に機械語には行かない

C 言語はコンパイラがソースをそのままネイティブコードに翻訳します。`.c` ファイルは Windows x64 用の `.exe` になるか、Linux ARM64 用のバイナリになります。一度コンパイルした結果物は**特定の OS + 特定の CPU の組み合わせ**に縛られます。

C# はこの構造を一度割りました。C# ソースは Roslyn コンパイラを経て、いったん **IL（Intermediate Language）** という中間バイトコードにだけ翻訳されます。IL はハードウェア・OS に独立で、`.dll` や `.exe` の中に収まります。実際のネイティブ翻訳は、**そのコードがどの機械で動くか分かったあと**に別途行われます。

この「別途行われる翻訳」の**時点**が第 1 部の核心です。時点は二つあります。

- **JIT（Just-In-Time）** — プログラムが実行される**その機械で、その瞬間** IL を機械語に翻訳
- **AOT（Ahead-Of-Time）** — アプリを配布する**前にあらかじめ**ネイティブコードに翻訳

同じ IL なのに翻訳時点が違うこと — この一分岐が、後で扱う三つのランタイムを分け、自分のツールをどう配布するかまで決めます。その分岐をきちんと理解するには、まず**翻訳の対象である IL がどうなっているか**を自分の目で見る必要があります。

## IL はスタックマシンである

IL を初めて見るとアセンブリに似て見えますが、決定的に違う点が一つあります。**レジスタがありません。**

x86・ARM のような実際の CPU は**レジスタマシン**です。`add rax, rbx` のように「どのレジスタの値とどのレジスタの値を足してどこに入れろ」を明示します。オペランドの位置を命令が直接指します。

IL は**スタックマシン**です。オペランドを指す代わりに、**評価スタック（evaluation stack）**という一時作業台に値を積み下ろしながら計算します。すべての演算がこの一文に還元されます。

> 必要な値をスタックに**積み（push）**、演算はスタック上の値を**取り出し（pop）計算したあと結果をまた積む。**

`a + b` を IL がどう処理するかを、評価スタックの状態変化で追ってみましょう。

<div class="il-stk">
  <div class="il-stk-title">評価スタック — a + b を計算する三段階</div>
  <div class="il-stk-row">
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.0</div>
      <div class="il-stk-note">a を積む</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.1</div>
      <div class="il-stk-note">b を積む</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">b</div>
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">add</div>
      <div class="il-stk-note">両方取り出して足し、積む</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell il-stk-cell-result">a + b</div>
      </div>
    </div>
  </div>
</div>

<style>
.il-stk { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.il-stk-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.il-stk-row { display: flex; align-items: stretch; justify-content: center; gap: 0.5rem; flex-wrap: nowrap; }
.il-stk-step { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: center; padding: 0.75rem 0.5rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.5); }
.il-stk-instr { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 15px; font-weight: 700; color: #6366f1; }
.il-stk-note { font-size: 11px; color: #64748b; margin: 0.25rem 0 0.75rem; text-align: center; }
.il-stk-stack { display: flex; flex-direction: column; justify-content: flex-end; gap: 4px; min-height: 92px; width: 100%; max-width: 130px; }
.il-stk-cell { padding: 7px 0; text-align: center; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 600; color: #1e293b; background: #e0e7ff; border: 1.2px solid #6366f1; border-radius: 4px; }
.il-stk-cell-result { background: #d1fae5; border-color: #10b981; }
.il-stk-arrow { display: flex; align-items: center; color: #94a3b8; font-size: 22px; font-weight: 700; }
[data-mode="dark"] .il-stk { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .il-stk-title { color: #e5e7eb; }
[data-mode="dark"] .il-stk-step { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .il-stk-instr { color: #a5b4fc; }
[data-mode="dark"] .il-stk-note { color: #94a3b8; }
[data-mode="dark"] .il-stk-cell { color: #f1f5f9; background: rgba(99,102,241,0.25); border-color: #818cf8; }
[data-mode="dark"] .il-stk-cell-result { background: rgba(16,185,129,0.25); border-color: #34d399; }
[data-mode="dark"] .il-stk-arrow { color: #64748b; }
@media (max-width: 768px) {
  .il-stk-instr { font-size: 12px; }
  .il-stk-note { font-size: 9px; }
  .il-stk-cell { font-size: 11px; padding: 5px 0; }
  .il-stk-stack { min-height: 72px; }
  .il-stk-arrow { font-size: 16px; }
}
</style>

レジスタマシンなら `add r2, r0, r1` の一行で済むところを、IL は `ldarg.0` / `ldarg.1` / `add` の三行で解きます。非効率に見えますが、これが IL の核心設計です。**オペランドの物理的な位置（どのレジスタ、何個のレジスタ）を命令から消してしまったため**、IL はレジスタが 16 個の CPU でも 32 個の CPU でも気にしません。「スタックから二つ取り出して足す」という抽象的な約束だけを残し、実際のレジスタ割り当ては翻訳器（JIT または AOT コンパイラ）がその機械に合わせて後から決めます。IL がプラットフォーム独立であり得る理由は、まさにこの「位置を消す」にあります。

## 最初のメソッドを読む

抽象的な説明はここまでです。実際の C# メソッド一つを IL に翻訳し、一行ずつ読んでみましょう。[sharplab.io](https://sharplab.io) で出力モードを `IL` にすれば、誰でも同じ結果を見られます。

```csharp
static int Add(int a, int b)
{
    return a + b;
}
```

```
.method private hidebysig static int32 Add(int32 a, int32 b) cil managed
{
    .maxstack 2
    ldarg.0      // a を評価スタックに積む
    ldarg.1      // b を評価スタックに積む
    add          // 両方取り出して足した結果を積む
    ret          // スタック最上位の値を戻り値として返す
}
```

四行がすべてです。

- **`ldarg.0`** — load argument 0。0 番引数（`a`）を評価スタックに積みます。`static` メソッドなので 0 番が最初のパラメータです。（インスタンスメソッドなら 0 番は `this` で、`a` は 1 番になります — この一マスの差が、IL を初めて読むときに一番つまずく点です。）
- **`ldarg.1`** — 1 番引数（`b`）を積みます。いまスタックには二つの値が積まれています。
- **`add`** — スタック上の二つの値を取り出して足し、結果一つをまた積みます。オペランドを明示しない点に注目してください。常に「スタック上の二つ」です。
- **`ret`** — スタック最上位の値をメソッドの戻り値とし、呼び出し元に戻ります。

`.maxstack 2` はこのメソッドが実行中に評価スタックへ**最大 2 個**まで積むという宣言です。翻訳器はこの数字を見てスタック検証とコード生成を準備します。

## 制御フローは分岐で消える

`Add` は一行なのでスタックマシンの形だけを見せました。実際のコードには局所変数があり、`if`・`for`・`while` のような制御フローがあります。ここで IL を読む最初の大きな跳躍が来ます。**IL には `if` も `for` もありません。** すべて条件分岐とジャンプラベルに平坦に展開されます。

```csharp
static int Max(int a, int b)
{
    if (a > b)
        return a;
    return b;
}
```

Release ビルドの IL はだいたいこうなります。（ラベル名・正確な命令はコンパイラのバージョンごとに少し違います。）

```
ldarg.0
ldarg.1
ble.s      IL_0006     // a <= b なら IL_0006 へジャンプ
ldarg.0                 // (a > b の場合) a を積んで
ret
IL_0006:
ldarg.1                 // b を積んで
ret
```

読むときに一番混乱する点は、**条件がひっくり返っている**ことです。ソースの `if (a > b)` なのに、IL は `ble`（「小さいか等しければ分岐」）を使います。コンパイラは「条件が真なら本体を実行」する代わりに、**「条件が偽なら本体を飛ばす」**と翻訳する方が分岐一回で終わり効率的だからです。`if` の条件と IL の分岐条件が正反対に見えたら、間違いではなく、このひっくり返しのせいです。

ループはさらに劇的です。

```csharp
static int Sum(int n)
{
    int total = 0;
    for (int i = 0; i < n; i++)
        total += i;
    return total;
}
```

```
.locals init (int32 total, int32 i)
    ldc.i4.0
    stloc.0            // total = 0
    ldc.i4.0
    stloc.1            // i = 0
    br.s      CHECK    // すぐ条件検査へジャンプ
LOOP:
    ldloc.0
    ldloc.1
    add
    stloc.0            // total = total + i
    ldloc.1
    ldc.i4.1
    add
    stloc.1            // i = i + 1
CHECK:
    ldloc.1
    ldarg.0
    blt.s     LOOP     // i < n なら LOOP へ戻る
    ldloc.0
    ret
```

`.locals init` はメソッドが使う局所変数（`total`、`i`）をあらかじめ宣言します。以降 `stloc.0` は「0 番局所変数に保存」、`ldloc.0` は「0 番局所変数を積む」で、引数を扱う `ldarg` と対になります。そしてループ進入時に `br.s CHECK` で**条件検査から**ジャンプしたあと、本体 → 増加 → 条件の順で回り、条件が真なら `blt.s LOOP` で上へ戻ります。`n` が 0 なら本体を一度も回らない動作が、この構造から自然に出ます。

`if` と `for` を総合すると一文が残ります。**C# のすべての制御フローは結局「条件を評価してスタックに積み、その結果でどこへジャンプするかを決める」分岐命令に還元されます。** `while` で同じコードを書いても IL はほぼ同じになります。高水準構文の差は IL 段階でほとんど消えます。

ちなみにこれまでの IL はすべて **Release** 基準です。Debug でビルドすると行ごとに `nop` が入り、戻り値を局所変数に入れてまた取り出す往復が生まれます（デバッガがブレークポイントを張り、値を覗くためです）。だから性能を分析するときは**常に Release IL** を見ないと、実際の配布物と合いません。

## ソースには見えなかったコストが IL で現れる

IL を読む本当のやりがいはここにあります。C# ソースでは平凡に見えたコードが、IL まで降りると**隠れていたコスト**を命令として露出します。

**① Boxing — `box`。** [メモリシリーズ](/posts/ValueTypeBoxing/) では Boxing が「値型が参照契約と出会う瞬間」に起きると書きました。その瞬間が IL では一行です。

```csharp
object o = 42;
```
```
ldc.i4.s   42
box        [System.Runtime]System.Int32   // ヒープにボックスを作り、参照を積む
stloc.0
```

`box` の一行がすなわち**ヒープアロケーション一回**です。取り出すときは `unbox.any` が登場します。ループの中でこの二つの語が見えたら、フレームスパイクの候補です。

**② 仮想ディスパッチ — `call` vs `callvirt`。** `call` は呼び出し対象がコンパイル時に確定している場合（`static`・`struct` メソッド）、`callvirt` はランタイムに実際の型を見て決める場合（クラスのインスタンスメソッド）です。興味深いのは、C# が **`virtual` でないインスタンスメソッドも通常 `callvirt` で呼ぶ**ことです。`callvirt` が呼び出し直前の **null チェックを兼ねるため**です。「非仮想メソッドなのになぜ callvirt？」は、IL を初めて読む人が必ず一度ぶつかる点です。

**③ 文字列連結 — 消えた `+`。** `"Hi, " + name` の IL には `+` も `add` もありません。代わりに `call ... System.String::Concat(string, string)` があります。文字列は不変なので `+` が算術になり得ず、コンパイラがメソッド呼び出しに翻訳するからです。ループ内の文字列 `+` がなぜ `StringBuilder` より遅いかの根拠が、IL にそのままあります。

三つの事例の共通点ははっきりしています。**C# 構文の便利さ（`object` 代入、ドット呼び出し、`+`）がランタイムコストを隠します。** IL はその便利さを剥ぎ取り、実際に実行される命令を見せます。反対方向の発見もあります。`static int Const() => 1 + 2;` の IL は `ldc.i4.3 / ret` — `add` がありません。`1 + 2` が**コンパイル時にすでに `3` に畳まれた**（constant folding）からです。だから IL を実験するときは定数の代わりに引数・フィールドを使わないと、コンパイラの畳み込みに隠されます。

## 同じ IL、三つの運命 — JIT · NativeAOT · IL2CPP

いま最初の問いに戻ります。これまで見た IL は**まだ機械語ではありません。** 誰かがこの IL を CPU 命令に翻訳してくれないと実行されません。その翻訳を**いつ・どう**するかが三分岐に分かれます。

<div class="path3">
  <div class="path3-title">C# → IL までは同じ。その先が分かれる</div>
  <div class="path3-row">
    <div class="path3-col">
      <div class="path3-head path3-head-jit">JIT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ 実行その瞬間</div>
      <div class="path3-box path3-box-end">機械語</div>
      <div class="path3-foot">ランタイム必要 · 初回呼び出しだけ遅い</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-aot">NativeAOT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ ビルド時 (ILC)</div>
      <div class="path3-box path3-box-end">機械語</div>
      <div class="path3-foot">ランタイム不要 · 単一バイナリ</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-il2cpp">IL2CPP</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ ビルド時 (il2cpp)</div>
      <div class="path3-box">C++</div>
      <div class="path3-down">↓ プラットフォームのツールチェーン</div>
      <div class="path3-box path3-box-end">機械語</div>
      <div class="path3-foot">iOS・コンソールが JIT 禁止 → AOT 強制</div>
    </div>
  </div>
</div>

<style>
.path3 { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.path3-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.path3-row { display: flex; gap: 0.75rem; justify-content: center; align-items: flex-start; flex-wrap: wrap; }
.path3-col { flex: 1 1 180px; max-width: 230px; display: flex; flex-direction: column; align-items: center; padding: 0.75rem 0.5rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.5); }
.path3-head { font-weight: 700; font-size: 14px; padding: 4px 14px; border-radius: 999px; margin-bottom: 0.75rem; }
.path3-head-jit { background: #cffafe; color: #0e7490; }
.path3-head-aot { background: #d1fae5; color: #047857; }
.path3-head-il2cpp { background: #ecfccb; color: #4d7c0f; }
.path3-box { width: 100%; max-width: 130px; padding: 6px 0; text-align: center; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 600; color: #1e293b; background: #e0e7ff; border: 1.2px solid #818cf8; border-radius: 5px; }
.path3-box-end { background: #fce7f3; border-color: #ec4899; }
.path3-down { font-size: 11px; color: #64748b; margin: 4px 0; }
.path3-foot { margin-top: 0.75rem; font-size: 11px; color: #475569; text-align: center; line-height: 1.4; }
[data-mode="dark"] .path3 { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .path3-title { color: #e5e7eb; }
[data-mode="dark"] .path3-col { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .path3-head-jit { background: rgba(6,182,212,0.25); color: #67e8f9; }
[data-mode="dark"] .path3-head-aot { background: rgba(16,185,129,0.25); color: #6ee7b7; }
[data-mode="dark"] .path3-head-il2cpp { background: rgba(101,163,13,0.25); color: #bef264; }
[data-mode="dark"] .path3-box { color: #f1f5f9; background: rgba(99,102,241,0.25); border-color: #818cf8; }
[data-mode="dark"] .path3-box-end { background: rgba(236,72,153,0.25); border-color: #f472b6; }
[data-mode="dark"] .path3-down { color: #94a3b8; }
[data-mode="dark"] .path3-foot { color: #cbd5e1; }
@media (max-width: 768px) {
  .path3-box { font-size: 11px; }
  .path3-down, .path3-foot { font-size: 9px; }
}
</style>

- **JIT** — IL を持ったまま、メソッドが**初めて呼ばれる瞬間**に機械語へ翻訳します。その機械の CPU・実行統計を見て最適化できる代わりに、初回呼び出しに翻訳コスト（cold start）を払います。一般の .NET サーバ・デスクトップ、Unity エディタの Mono がこの方式です。
- **NativeAOT** — ビルド時に IL を**ネイティブへ直接**翻訳し、単一バイナリに固めます。実行時に翻訳器がなくても動き、cold start はほぼ 0 です。CLI ツール・サーバレスが主なターゲットです。
- **IL2CPP** — Unity が作った AOT です。IL を**いったん C++ に変換**したあと、プラットフォーム別の C++ ツールチェーン（Xcode・NDK・コンソール SDK）でネイティブビルドします。iOS・コンソールがセキュリティ上 JIT を禁止するため、モバイルビルドでは強制です。

### 決定的な差は一行 — 「ランタイムで新しいコードを作れるか」

三分岐の表面は「翻訳時点」ですが、より深い差は一つです。**JIT は実行中でも IL を受け取り機械語に作るエンジンを持っており、AOT にはそのエンジンがありません。** ビルド時にすべて固めてしまったからです。

この一行を覚えておいてください。第 2 部と第 3 部の全体が、この一文一つでつながります。「ランタイムで新しいコードを作る」とはすなわち **Reflection の動的機能**とメタプログラミングを意味し、それがまさに自分のツールが依存することになる能力であり、同時に AOT が許さない能力だからです。

### では自分のツールはどこにあるか

ここで最初の問いに答える座標が取れます。自分のツールは**二つのまったく違うビルド**と混同しやすいです。

- **[A] 分析*対象*であるゲームのビルド** — Unity C# が IL2CPP を経て `.ipa`/`.apk` になります。プレイヤーの手元に入り、IL2CPP の AOT 制約を受けます。
- **[B] 自分の分析*ツール*自体のビルド** — 開発者 PC のターミナルで動く別の .NET プログラムです。ゲームの中に入らないので **IL2CPP・AOT 制約とは無関係**です。

ツールは [B] なのでゲームの IL2CPP 制約を気にする必要はなく、JIT で配布するか NativeAOT で固めるかを**純粋にツールの使い勝手** — 特に cold start — を基準に選べます。コード分析ツールはある作業の中で無数に繰り返し呼ばれることが多いので、呼び出しごとの起動時間が積み上がります。だから「AOT で固めて cold start を消そうか？」が自然な誘惑になります。しかしその誘惑には罠があります。さきほど強調した一行 — **AOT はランタイムでコードを作れない** — がツールの核心機能と衝突し得るからです。その衝突を見るには、二つ目の問いへ進まなければなりません。

## IL は半分にすぎない — メタデータという相棒

第 2 部へ進む前に橋を一つ架けます。さきほど見た IL を改めて見ると、命令が**名前とシグネチャをそのまま引用**しています。

```
box   [System.Runtime]System.Int32
call  string [System.Runtime]System.String::Concat(string, string)
```

`System.Int32` が値型かどうか、`String.Concat` がどのアセンブリの何番目のメソッドか — この情報は **IL 命令ストリームの中にはありません。** IL は「何番トークンを呼べ」と指すだけで、そのトークンが実際にどの型・メソッド・フィールドかは **メタデータテーブル（metadata tables）** という別のデータ構造が持っています。`.dll` ファイルは事実上 **IL ストリーム + メタデータテーブル**の束です。

このメタデータが第 2 部の出発点です。ランタイムが `typeof(int)` や `obj.GetType()` で型情報を返せるのも、Roslyn がコードを意味として読むのも、結局このテーブルの上で起きます。

---

# 第 2 部. コードを意味として読む

## 二つ目の問い — grep ではなぜだめか

自分のツールがやるべき仕事はこういうものです。`HouseEditPresenter` の `OnTapFooter` メソッドが `_model.UpdateFloor()` を呼ぶとき、**その呼び出しが実際にどの実装へ向かうか**を辿ること。

```csharp
public class HouseEditPresenter
{
    private IHouseEditModel _model;

    public void OnTapFooter()
    {
        _model.UpdateFloor();
    }
}
```

最初に思い浮かぶ方法はテキスト検索（grep）です。`"UpdateFloor"` をプロジェクト全体で探せばよいのではないか。しかし grep はすぐに壁にぶつかります。`UpdateFloor` という文字列が出てきても、それが

- 実際の**メソッド呼び出し**なのか
- コメント `// UpdateFloor 呼び出し注意` の中の文字なのか
- `UpdateFloor` という名前の**変数**なのか
- まったく別クラスの**同名メソッド**なのか

grep は区別できません。さらに決定的なのは、`_model` の型がインターフェース `IHouseEditModel` で、その実際の実装が `HouseEditModel` だという**接続**を、grep は作れないことです。テキスト検索にとってコードはただの**文字の並び**です。私たちが必要なのは文字ではなく**意味**です。

意味を得るには、テキストを一段ずつ解釈して上がらなければなりません。その解釈の段階がまさに**コンパイラがコードを理解する過程**です。

## コンパイラはコードをどう理解するか

コンパイラのフロントエンドはソーステキストを三段階で引き上げます。この三段階がコンパイラ理論の核心であり、「意味として読む」の正体です。

<div class="sem">
  <div class="sem-title">grep が止まる場所、コンパイラが上がる場所</div>
  <div class="sem-row">
    <div class="sem-stage sem-stage-dim">
      <div class="sem-stage-name">元のテキスト</div>
      <div class="sem-stage-ex">_model.UpdateFloor()</div>
      <div class="sem-stage-desc">文字の並び。grep はここだけを見る</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">① 字句解析<br><span>トークン</span></div>
      <div class="sem-stage-ex">[_model] [.] [UpdateFloor] [(] [)]</div>
      <div class="sem-stage-desc">空白・コメント除去。コメント内の文字が落とされる</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">② 構文解析<br><span>構文木</span></div>
      <div class="sem-stage-ex">メンバ呼び出し( 対象=_model, 名前=UpdateFloor )</div>
      <div class="sem-stage-desc">構造を知る。「呼び出しか変数か」を区別</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage sem-stage-goal">
      <div class="sem-stage-name">③ 意味解析<br><span>セマンティックモデル</span></div>
      <div class="sem-stage-ex">_model : IHouseEditModel<br>→ 実装 HouseEditModel.UpdateFloor</div>
      <div class="sem-stage-desc">意味を知る。型・シンボル接続が完成</div>
    </div>
  </div>
</div>

<style>
.sem { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(16,185,129,0.04); }
.sem-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.sem-row { display: flex; gap: 0.4rem; justify-content: center; align-items: stretch; flex-wrap: wrap; }
.sem-stage { flex: 1 1 150px; max-width: 210px; display: flex; flex-direction: column; padding: 0.7rem 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.6); }
.sem-stage-dim { background: rgba(148,163,184,0.12); }
.sem-stage-goal { border-color: #10b981; background: rgba(16,185,129,0.1); }
.sem-stage-name { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 0.4rem; line-height: 1.3; }
.sem-stage-name span { font-weight: 600; color: #6366f1; font-size: 12px; }
.sem-stage-ex { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px; color: #334155; background: rgba(99,102,241,0.08); border-radius: 4px; padding: 5px 6px; margin-bottom: 0.4rem; line-height: 1.4; word-break: break-all; }
.sem-stage-desc { font-size: 11px; color: #64748b; margin-top: auto; line-height: 1.4; }
.sem-arrow { display: flex; align-items: center; color: #94a3b8; font-size: 20px; font-weight: 700; }
[data-mode="dark"] .sem { border-color: #334155; background: rgba(16,185,129,0.08); }
[data-mode="dark"] .sem-title { color: #e5e7eb; }
[data-mode="dark"] .sem-stage { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .sem-stage-dim { background: rgba(148,163,184,0.12); }
[data-mode="dark"] .sem-stage-goal { border-color: #34d399; background: rgba(16,185,129,0.15); }
[data-mode="dark"] .sem-stage-name { color: #f1f5f9; }
[data-mode="dark"] .sem-stage-name span { color: #a5b4fc; }
[data-mode="dark"] .sem-stage-ex { color: #cbd5e1; background: rgba(99,102,241,0.18); }
[data-mode="dark"] .sem-stage-desc { color: #94a3b8; }
[data-mode="dark"] .sem-arrow { color: #64748b; }
@media (max-width: 768px) {
  .sem-arrow { transform: rotate(90deg); }
  .sem-stage { max-width: none; }
}
</style>

**① 字句解析（Lexing）。** ソース文字列を**トークン**の並びに分割します。`_model.UpdateFloor()` は `[識別子 _model]` `[ドット]` `[識別子 UpdateFloor]` `[開き括弧]` `[閉じ括弧]` になります。この段階で空白とコメントが除去されます。つまり、grep が落とせなかった**コメント内の `UpdateFloor` がここですでに脱落**します。

**② 構文解析（Parsing）。** トークンを文法規則に合わせて**構文木（Syntax Tree）**に組み立てます。「これはメンバアクセス式で、その中にメソッド呼び出しがある」という**構造**が作られます。いまや「`UpdateFloor` が呼び出しか変数か」を区別できます。ただし構文木はまだ**構造だけ**を知ります。`_model` が何の型かは知りません。

**③ 意味解析（Semantic Analysis）。** 構文木に**型とシンボル情報**を載せます。`_model` の宣言を探し、型が `IHouseEditModel` だと知り（symbol binding）、`UpdateFloor` がそのインターフェースのどのメンバを指すかをつなぎ、そのインターフェースの実装が `HouseEditModel` だと辿ります。この段階の成果物が**セマンティックモデル（Semantic Model）**です。ようやく「この呼び出しが実際にどの実装へ向かうか」に答えられます。

三段階を貫く一文はこれです。**grep は 0 段階（生テキスト）に留まり、自分のツールが必要な答えは 3 段階（セマンティックモデル）にあります。** その間を自分で実装するというのは、C# コンパイラのフロントエンドを丸ごと作り直すという意味です — C# 言語仕様はジェネリック・async・ラムダ・パターンマッチングまで毎年増える 1,500 ページの文書です。一人で追いつける規模ではありません。

## Reflection — すでにコンパイルされたコードの意味をランタイムで読む

ここで一つの疑問が生まれます。.NET にはすでに **Reflection** という、型とメンバを覗く機能があるのではないか？ `obj.GetType()`、`type.GetMethods()` — これではだめか？

Reflection の正体は、第 1 部の終わりで見た**メタデータテーブルをランタイムで読む API**です。ランタイムは `.dll` をロードするとき、その中のメタデータテーブルをパースして `Type` オブジェクトを作っておきます。`typeof(int)` が返すその `Type` がまさにメタデータの一行のランタイム表現です。`GetMethods()` はその型に付いたメソッドテーブルをなめるものです。つまり **Reflection = コンパイルが終わった成果物（IL + メタデータ）を逆向きに覗くこと**です。

しかし Reflection では自分のツールの仕事はできません。決定的な限界があるからです。

- Reflection が見るのは**すでにコンパイルされたアセンブリ**です。メソッドが**何を呼ぶか**（メソッド本体の中の `_model.UpdateFloor()`）はメタデータではなく **IL 本体**の中にあり、一般的な Reflection API では辿りにくいです。
- コメント・局所変数名・「この呼び出しがソース何行目か」のような**ソース水準の情報**は、コンパイル過程でほとんど消え、メタデータにありません。

まとめると、Reflection は「**何が存在するか**」（この型にどんなメソッドがあるか）には強いですが、「**ソースで何が何を呼ぶか**」には弱いです。自分のツールが欲しいのは後者 — ソースコードの意味構造です。だから答えはメタデータを読む Reflection ではなく、ソースを①②③段階で解釈する**コンパイラそのもの**でなければなりません。

## だから Roslyn — コンパイラをライブラリとして

**Roslyn** は Microsoft が作った C# の公式コンパイラです。しかし単なるコンパイラではなく、さきほどの①②③段階を**外部プログラムが呼べるライブラリ（API）として公開**したことが核心です。`dotnet build` が内部で回すそのコンパイラを、私たちがコードで呼び出せるという意味です。

Roslyn がくれるのは、まさに私たちが 1〜3 段階で必要としていたものです。

- **SyntaxTree** — ② 構文木。ソースの構造をノードとして巡回
- **SemanticModel** — ③ セマンティックモデル。「このノードの型は何か」「このシンボルはどこで宣言されたか」に答える
- **ISymbol** — 型・メソッド・フィールドの意味単位。インターフェースと実装、呼び出しと宣言をつなぐ結び目

自分のツールが `_model.UpdateFloor()` を辿るとき、Roslyn に「この呼び出しノードのシンボルをくれ」と聞けば `IHouseEditModel.UpdateFloor` というシンボルが出て、「このインターフェースメンバの実装を探してくれ」と聞けば `HouseEditModel.UpdateFloor` が出ます。自分で実装すればコンパイラフロントエンド全体だった仕事が、**API 呼び出し数行**で終わります。これがコード分析ツールを C# で作るときに Roslyn を使う理由です。

### なぜ Roslyn は重いのか（50MB+）

代償があります。Roslyn 依存は数十 MB に達します。軽いライブラリではありません。その重さの正体は、Roslyn が**コンパイラ一式を丸ごと**抱えているからです。

- C# 言語の**すべてのバージョンの構文**（毎年追加される機能を含む）
- **MSBuild 統合** — `.csproj` を読み、NuGet パッケージを解釈し、プロジェクト間参照を解決
- **Workspace** 抽象化 — ソリューションの複数プロジェクトを同時に分析
- 標準ライブラリ全体の**メタデータキャッシュ**

つまり Roslyn の 50MB は「機能が多いから」ではなく、**C# コードを意味として理解するという仕事自体がそれだけの知識を要求するから**です。意味解析は一つのファイルだけを見ていてはだめで、そのファイルが参照するすべての型・アセンブリ・プロジェクトを知らなければなりません。Roslyn の重さは、その「知らなければならないもの」の重さです。

そしてここで、第 1 部で強調しておいた一行が再び登場します。Roslyn はユーザープロジェクトのアナライザ（analyzer）とソースジェネレータを**ランタイムで動的にロード**し、内部で **Reflection を広範に**使います。つまり Roslyn は「ランタイムでコードを動的に扱う」側に深く足を踏み入れています。まさにその地点で、最初の問い（速い起動のための AOT）と二つ目の問い（Roslyn でコードを読むこと）が正面からぶつかります。

---

# 第 3 部. 二つの世界が衝突するところ

## Reflection.Emit — ランタイムで IL を打ち出す

衝突の正体を見るには、Reflection の残りの半分を知る必要があります。第 2 部で見た Reflection は**読み取り**（introspection）でした。Reflection には**書き込み**もあります。`System.Reflection.Emit` は、プログラムが**実行中に新しいメソッドの IL をバイト単位で生成**し、ランタイムに「これを機械語にして実行してくれ」と渡す API です。

なぜこんなものを使うのか。**性能**のためです。代表例がシリアライズです。ある型を JSON にするコードを、毎回 Reflection でフィールドを一つずつ読みながら処理すると遅いです。代わりにその型専用のシリアライズコードを**ランタイムで一度 IL として生成**しておけば、以降は手書きコードと同じくらい速くなります。DI コンテナの動的コンストラクタ注入、動的プロキシ、`Expression.Compile()` — すべて同じ原理でランタイムにコードを作り、速度を稼ぎます。

## だから AOT と本質的に衝突する

いま第 1 部の一行が完全に回収されます。**AOT はビルド時にすべての IL をあらかじめ機械語に固めたため、ランタイムで IL を受け取って翻訳する JIT エンジンがありません。**

だから `Reflection.Emit` がランタイムで IL をいくら上手に作り出しても、それを機械語に変えて実行する場所がありません。コードが壊れます。これは IL2CPP と NativeAOT が**共有する**制約です（どちらも AOT だからです）。[Foundation 第 3 篇](/posts/DotnetRuntimeVariants/) で表にまとめた「AOT で壊れるもの」の根本原因が、まさにこの一行でした。

連鎖してもう一つ壊れます。AOT 配布は通常 **トリミング**（使わないコード除去によるバイナリ縮小）を伴いますが、`type.GetMethod("UpdateFloor")` のように**文字列でメンバを探す** Reflection は静的分析が不可能です。トリマーはそのメソッドが使われていないと判断して消し、ランタイムで Reflection がそれを探すと失敗します。

## ツールのジレンマ、そして動作原理としての結論

二つの問いが出会う場所がいま見えます。

- **最初の問いの魅力的な答え**: ツールを NativeAOT で固めれば cold start が消える。繰り返し呼ばれる分析ツールに理想的だ。
- **二つ目の問いの必然的な答え**: ツールは Roslyn に依存する。しかし Roslyn は動的ロードと Reflection に深く依存する。

二つを重ねると、**Roslyn を丸ごと NativeAOT で固めるのは本質的に難しいです。** 「コードを意味として読む能力」と「速い起動」が、互いに違うランタイム仮定の上に立っているからです。前者はランタイムの動的能力を要求し、後者はその能力を諦める代償として得られます。一つのツールが両方を同時に最大限持つことはできません。

ここで重要なのは「だからツールをどのオプションでパッケージしたか」という細部ではありません。それはプロジェクトごとに違う選択にすぎません。核心はその選択を強制する**構造的な緊張**です — メタプログラミング（ランタイムでコードを扱う力）と AOT（ランタイムのその力をあらかじめ諦めて得る速度）は**同じ資源をめぐって競争**します。この緊張を理解すれば、なぜある .NET ツールは軽く AOT に落ち、あるツールはそうできないのかが一目で説明できます。

## Source Generator — 衝突を避ける道

ではメタプログラミングを諦めるべきでしょうか。現代 .NET の答えは「諦め」ではなく**時点を移すこと**です。

`Reflection.Emit` がコードを**ランタイムで**作るなら、**Source Generator** は同じ仕事を**コンパイル時に**します。

<div class="emit">
  <div class="emit-title">コードを作る時点を移す</div>
  <div class="emit-row">
    <div class="emit-card emit-card-bad">
      <div class="emit-card-head">Reflection.Emit</div>
      <div class="emit-flow">コンパイル → 実行 → <b>ランタイムで IL 生成</b> → JIT が翻訳</div>
      <div class="emit-verdict">JIT 必要 · AOT で壊れる</div>
    </div>
    <div class="emit-card emit-card-good">
      <div class="emit-card-head">Source Generator</div>
      <div class="emit-flow"><b>コンパイル中に C# 生成</b> → 一緒にコンパイル → IL にすでに含まれる</div>
      <div class="emit-verdict">ランタイム生成不要 · AOT 親和</div>
    </div>
  </div>
</div>

<style>
.emit { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.emit-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.emit-row { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.emit-card { flex: 1 1 240px; max-width: 340px; padding: 0.9rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.6); }
.emit-card-bad { border-color: #f59e0b; }
.emit-card-good { border-color: #10b981; }
.emit-card-head { font-family: ui-monospace, SFMono-Regular, monospace; font-weight: 700; font-size: 14px; color: #1e293b; margin-bottom: 0.6rem; }
.emit-flow { font-size: 12.5px; color: #334155; line-height: 1.6; margin-bottom: 0.6rem; }
.emit-flow b { color: #6366f1; }
.emit-verdict { font-size: 12px; font-weight: 600; }
.emit-card-bad .emit-verdict { color: #b45309; }
.emit-card-good .emit-verdict { color: #047857; }
[data-mode="dark"] .emit { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .emit-title { color: #e5e7eb; }
[data-mode="dark"] .emit-card { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .emit-card-bad { border-color: #d97706; }
[data-mode="dark"] .emit-card-good { border-color: #34d399; }
[data-mode="dark"] .emit-card-head { color: #f1f5f9; }
[data-mode="dark"] .emit-flow { color: #cbd5e1; }
[data-mode="dark"] .emit-flow b { color: #a5b4fc; }
[data-mode="dark"] .emit-card-bad .emit-verdict { color: #fbbf24; }
[data-mode="dark"] .emit-card-good .emit-verdict { color: #6ee7b7; }
@media (max-width: 768px) {
  .emit-flow { font-size: 11.5px; }
}
</style>

Source Generator は Roslyn の上で動作します。コンパイルが進むあいだ、第 2 部で見た構文木・セマンティックモデルを覗き、**追加の C# ソースコードを生成**してコンパイルに差し込みます。その生成されたコードは本来のコードと一緒に IL に翻訳されるので、**結果の IL には必要なコードがすでにすべて入っています。** ランタイムで `Emit` で作るものはありません。だから AOT と衝突しません。

`System.Text.Json` がこの方向へ転換したのが代表的です。かつてはランタイム Reflection でシリアライズコードを作っていましたが、いまは Source Generator でコンパイル時に生成し、AOT でもきちんと動作します。**メタプログラミングの時点をランタイムからコンパイル時へ移したこと** — これが現代 .NET が「動的な便利さ」と「AOT の速度」を和解させた方式です。

## 総合 — 小さなツール一つが触った五つのドメイン

最初の二つの問いに戻ります。「ツールをどう配布するか」「ツールがコードをどう読むか」 — 表面は素朴でしたが、答えを辿ると五つの知識ドメインを順に通らなければなりませんでした。

- **バイトコード仮想マシン** — IL とスタックマシン（第 1 部）
- **ランタイムシステム** — JIT・AOT の翻訳時点とその代償（第 1 部）
- **コンパイラ理論** — 字句解析・構文解析・意味解析（第 2 部）
- **メタプログラミングと Reflection** — メタデータ、`Emit`、Source Generator（第 2・3 部）
- **静的プログラム解析** — ソースの意味構造を読んで問いに答えること、すなわちツールがやろうとしていたこと（全体）

この五つが別々に遊ぶ知識ではなく**一つの問いの中で互いに噛み合う**こと — それがこの一周の結論です。IL を知らなければメタデータを知らず、メタデータを知らなければ Reflection を知らず、Reflection と JIT/AOT の関係を知らなければ Roslyn がなぜ重いのか、なぜ AOT と衝突するのか、Source Generator がなぜ登場したのかを説明できません。小さな分析ツール一つをきちんと作ろうとした試みが、結局「C# はどう実行され、どう自分自身を読むのか」全体を問わせたわけです。

---

## 要約

1. **C# は一気に機械語にはなりません。** まず IL になり、翻訳時点（実行中 JIT / ビルド時 AOT）が JIT・NativeAOT・IL2CPP を分けます。IL はレジスタのないスタックマシンなので、Boxing・仮想ディスパッチのような隠れたコストと制御フローの分岐構造が命令として現れます。
2. **コードを意味として読むにはコンパイラの三段階**（字句解析 → 構文木 → セマンティックモデル）が必要です。grep は生テキストに留まり、Reflection はすでにコンパイルされた成果物だけを見ます。ソースの意味構造はコンパイラ自身、すなわち **Roslyn** がくれます。Roslyn が重い（50MB+）理由は、「意味を知る」という仕事がそれだけの知識を要求するからです。
3. **すべてをつなぐ一行は「ランタイムで新しいコードを作れるか」**です。JIT はでき、AOT はできません。だから `Reflection.Emit` と動的ロードに依存する Roslyn は AOT と衝突し、**Source Generator** がコード生成時点をコンパイル時へ移してその衝突を避けます。
4. **小さなツール一つが五つのドメイン**（バイトコード VM・ランタイム・コンパイラ理論・メタプログラミング・静的解析）を貫きます。これらは分離された知識ではなく、一つの問いの中で噛み合っています。

---

## 参考資料

### 一次出典

- [ECMA-335 — Common Language Infrastructure (CLI)](https://ecma-international.org/publications-and-standards/standards/ecma-335/) · IL 命令セットとメタデータ構造の標準仕様
- [Roslyn (dotnet/roslyn) GitHub](https://github.com/dotnet/roslyn) · C# コンパイラ・分析 API の公式実装
- [Microsoft Learn — Source Generators](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/source-generators-overview) · コンパイル時コード生成の概要
- [Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · AOT が壊す機能の公式一覧
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · IL → C++ 変換の実際の生成コード

### ツール

- [SharpLab](https://sharplab.io) · C# ↔ IL ↔ JIT アセンブリのリアルタイム変換
- [ILSpy](https://github.com/icsharpcode/ILSpy) · .dll ディスアセンブラ・デコンパイラ

### 書籍

- 『CLR via C#』 (Jeffrey Richter) · IL・メタデータ・Reflection・JIT 動作の決定版
- 『Crafting Interpreters』 (Robert Nystrom) · 字句解析・構文解析・木巡回を手で実装する入門書。コンパイラフロントエンドの動作原理を理解する土台（オンライン無料公開）
- 『C# in Depth』 (Jon Skeet) · C# 言語機能が IL へどう翻訳されるかの動作原理
