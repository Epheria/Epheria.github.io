---
title: .NET エコシステムマップ — 言語・ランタイム・BCL の関係
lang: ja
date: 2026-04-26 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, clr, bcl, il, runtime, mono, il2cpp]
toc: true
toc_sticky: true
difficulty: beginner
tldr:
  - C# は言語、.NET はプラットフォーム、CLR はランタイムです。同じように聞こえますが、それぞれ異なる層に位置しています
  - C# のコードは IL という中間言語にコンパイルされ、ランタイムがその IL を JIT または AOT でネイティブコードに変換して実行します
  - Unity は Mono または IL2CPP という独自のランタイム上で .NET のサブセットを使用しています。「Unity は .NET ではない」ではなく、「Unity は .NET の特定の実装を使っている」というのが正確です
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 「.NET」という言葉の曖昧さ

開発ドキュメント・履歴書・ブログで「.NET」という単語は、驚くほどさまざまな意味で使われています。

- 「.NET でバックエンドを書いています」
- 「.NET Framework 4.8 専用のプロジェクトです」
- 「.NET 8 に移行しました」
- 「Unity は .NET ではありません」 / 「Unity も実質的に .NET です」

同じ単語が**言語・ランタイム・標準ライブラリ・アプリケーションフレームワーク**を行き来しながら曖昧に使われているからです。一度整理しておかないと、以降の C# シリーズのほぼすべての記事がこの曖昧さの上で揺れてしまいます。

この記事の目標はただひとつです。**.NET という言葉がどの層を指しているかを区別できるようになること**。

歴史 (第 2 回) とランタイムの分岐 (第 3 回) は次回以降に扱います。今回は**地図**を描きます。

---

## Part 1. 6 つのレイヤーに分ける

.NET は単一の技術ではなく、**6 つの層が積み重なったタワー**です。一層ずつ分離して見ると、「.NET」という単語が今どの層を指しているかを言えるようになります。

<div class="dotnet-stack-container">
<svg viewBox="0 0 720 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET スタックレイヤーダイアグラム">
  <defs>
    <linearGradient id="dotnet-stack-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.18"/>
    </linearGradient>
  </defs>

  <text x="360" y="30" text-anchor="middle" class="dotnet-stack-title">.NET 6 つの層 — 上から下へ</text>

  <g class="dotnet-stack-layer" data-layer="6">
    <rect x="60" y="60" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="85" class="dotnet-stack-name">6. Application Framework</text>
    <text x="80" y="106" class="dotnet-stack-desc">ASP.NET Core · WinForms · WPF · MAUI · Unity · Xamarin</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="5">
    <rect x="60" y="128" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="153" class="dotnet-stack-name">5. BCL (Base Class Library)</text>
    <text x="80" y="174" class="dotnet-stack-desc">System.* · System.Collections · System.IO · System.Threading</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="4">
    <rect x="60" y="196" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="221" class="dotnet-stack-name">4. Runtime</text>
    <text x="80" y="242" class="dotnet-stack-desc">CLR · CoreCLR · Mono · IL2CPP · NativeAOT</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="3">
    <rect x="60" y="264" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="289" class="dotnet-stack-name">3. IL (Intermediate Language)</text>
    <text x="80" y="310" class="dotnet-stack-desc">ハードウェア非依存の中間バイトコード · .dll / .exe の中に保存される</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="2">
    <rect x="60" y="332" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="357" class="dotnet-stack-name">2. Compiler</text>
    <text x="80" y="378" class="dotnet-stack-desc">Roslyn (csc) · ソースコードを IL に変換</text>
  </g>

  <g class="dotnet-stack-layer" data-layer="1">
    <rect x="60" y="400" width="600" height="58" rx="6" class="dotnet-stack-box"/>
    <text x="80" y="425" class="dotnet-stack-name">1. Language</text>
    <text x="80" y="446" class="dotnet-stack-desc">C# · F# · VB.NET</text>
  </g>
</svg>
</div>

<style>
.dotnet-stack-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-stack-container svg { width: 100%; max-width: 720px; height: auto; display: block; margin: 0 auto; }
.dotnet-stack-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-stack-box { fill: url(#dotnet-stack-grad); stroke: #6366f1; stroke-width: 1.2; }
.dotnet-stack-name { font-size: 15px; font-weight: 700; fill: #1e293b; }
.dotnet-stack-desc { font-size: 13px; fill: #475569; }
[data-mode="dark"] .dotnet-stack-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-stack-box { stroke: #818cf8; }
[data-mode="dark"] .dotnet-stack-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-stack-desc { fill: #94a3b8; }
@media (max-width: 768px) {
  .dotnet-stack-name { font-size: 13px; }
  .dotnet-stack-desc { font-size: 11px; }
}
</style>

各層は**直下の層にのみ依存**します。C# のコードは Roslyn を経て IL になり、IL はランタイムで解釈され、ランタイムは BCL を基本ライブラリとして提供し、その上でアプリケーションフレームワークが動作します。

「.NET」という単語は文脈によってこの中の**どの層**を指しています。以降のすべての議論はこの地図を参照します。

---

## Part 2. C# と .NET の関係

最も混同されやすいところから整理します。

### C# は言語です

C# は **ECMA-334** と **ISO/IEC 23270** で標準化されたプログラミング言語です。文法と型システムを定義するドキュメントがあり、コンパイラ (Roslyn) がそのドキュメントを実装しています。C# は **Java と同じレベルの概念**です。

### .NET はプラットフォームです

.NET は言語・ランタイム・BCL・SDK・アプリケーションフレームワークを**すべて含むエコシステムの名称**です。上記ダイアグラムの第 2 層から第 6 層までを総称します。

### 2 つの組み合わせ

したがって、次の 4 つはすべて**互いに異なる主張**です。

| 主張 | 指す対象 |
|------|---------|
| 「C# で書いた」 | 第 1 層 (言語) — コンパイラ・ランタイムは未指定 |
| 「.NET 8 で書いた」 | 第 2〜6 層全体 — 特定バージョンを指定 |
| 「.NET Framework 4.8 専用だ」 | Windows 専用の .NET 実装 |
| 「Unity の C#」 | C# 言語 + Unity の特定ランタイム (Mono または IL2CPP) |

「C# と .NET は同じものではないですか?」という問いへの答えは、「**C# は .NET の一層 (言語)**」です。

---

## Part 3. IL — 中間層がなぜ必要なのか

ダイアグラムで最も注目すべき層は**第 3 層 IL**です。ここを理解すると、以降のすべてのランタイムに関する議論が楽になります。

### コンパイル・実行パイプライン

<div class="dotnet-pipeline-container">
<svg viewBox="0 0 820 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="C# コンパイルおよび実行パイプライン">
  <defs>
    <marker id="dotnet-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="dotnet-arrow-head"/>
    </marker>
  </defs>

  <text x="410" y="26" text-anchor="middle" class="dotnet-pipeline-title">コンパイル時と実行時の境界</text>

  <g class="dotnet-pipeline-step">
    <rect x="20" y="100" width="120" height="60" rx="8" class="dotnet-step-source"/>
    <text x="80" y="128" text-anchor="middle" class="dotnet-step-name">C# ソース</text>
    <text x="80" y="146" text-anchor="middle" class="dotnet-step-sub">.cs</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="180" y="100" width="120" height="60" rx="8" class="dotnet-step-compiler"/>
    <text x="240" y="128" text-anchor="middle" class="dotnet-step-name">Roslyn (csc)</text>
    <text x="240" y="146" text-anchor="middle" class="dotnet-step-sub">コンパイラ</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="340" y="100" width="120" height="60" rx="8" class="dotnet-step-il"/>
    <text x="400" y="128" text-anchor="middle" class="dotnet-step-name">IL</text>
    <text x="400" y="146" text-anchor="middle" class="dotnet-step-sub">.dll / .exe</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="60" width="140" height="60" rx="8" class="dotnet-step-jit"/>
    <text x="570" y="88" text-anchor="middle" class="dotnet-step-name">JIT</text>
    <text x="570" y="106" text-anchor="middle" class="dotnet-step-sub">実行時に変換</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="500" y="140" width="140" height="60" rx="8" class="dotnet-step-aot"/>
    <text x="570" y="168" text-anchor="middle" class="dotnet-step-name">AOT</text>
    <text x="570" y="186" text-anchor="middle" class="dotnet-step-sub">ビルド時に変換</text>
  </g>

  <g class="dotnet-pipeline-step">
    <rect x="680" y="100" width="120" height="60" rx="8" class="dotnet-step-native"/>
    <text x="740" y="128" text-anchor="middle" class="dotnet-step-name">ネイティブコード</text>
    <text x="740" y="146" text-anchor="middle" class="dotnet-step-sub">x86 / ARM</text>
  </g>

  <line x1="140" y1="130" x2="175" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="300" y1="130" x2="335" y2="130" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="120" x2="495" y2="95" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="460" y1="140" x2="495" y2="165" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="95" x2="680" y2="125" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>
  <line x1="640" y1="165" x2="680" y2="140" class="dotnet-pipeline-line" marker-end="url(#dotnet-arrow)"/>

  <line x1="460" y1="220" x2="460" y2="40" class="dotnet-pipeline-divider"/>
  <text x="240" y="240" text-anchor="middle" class="dotnet-pipeline-label">コンパイル時 (ビルドマシン)</text>
  <text x="650" y="240" text-anchor="middle" class="dotnet-pipeline-label">実行時またはデプロイ前</text>
</svg>
</div>

<style>
.dotnet-pipeline-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-pipeline-container svg { width: 100%; max-width: 820px; height: auto; display: block; margin: 0 auto; }
.dotnet-pipeline-title { font-size: 16px; font-weight: 700; fill: #1f2937; }
.dotnet-step-source { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.2; }
.dotnet-step-compiler { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.dotnet-step-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.dotnet-step-jit { fill: #cffafe; stroke: #06b6d4; stroke-width: 1.2; }
.dotnet-step-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1.2; }
.dotnet-step-native { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.dotnet-step-name { font-size: 14px; font-weight: 700; fill: #1e293b; }
.dotnet-step-sub { font-size: 11px; fill: #475569; }
.dotnet-pipeline-line { stroke: #6366f1; stroke-width: 1.8; fill: none; }
.dotnet-arrow-head { fill: #6366f1; }
.dotnet-pipeline-divider { stroke: #94a3b8; stroke-dasharray: 4 4; stroke-width: 1; }
.dotnet-pipeline-label { font-size: 12px; fill: #64748b; font-style: italic; }
[data-mode="dark"] .dotnet-pipeline-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-step-source { fill: rgba(99,102,241,0.2); stroke: #818cf8; }
[data-mode="dark"] .dotnet-step-compiler { fill: rgba(217,119,6,0.2); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-step-il { fill: rgba(124,58,237,0.2); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-step-jit { fill: rgba(6,182,212,0.2); stroke: #22d3ee; }
[data-mode="dark"] .dotnet-step-aot { fill: rgba(16,185,129,0.2); stroke: #34d399; }
[data-mode="dark"] .dotnet-step-native { fill: rgba(236,72,153,0.2); stroke: #f472b6; }
[data-mode="dark"] .dotnet-step-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-step-sub { fill: #94a3b8; }
[data-mode="dark"] .dotnet-pipeline-line { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .dotnet-pipeline-divider { stroke: #475569; }
[data-mode="dark"] .dotnet-pipeline-label { fill: #94a3b8; }
@media (max-width: 768px) {
  .dotnet-step-name { font-size: 12px; }
  .dotnet-step-sub { font-size: 10px; }
}
</style>

### なぜ中間層 (IL) を挟むのか

C 言語ではコンパイラがソースコードを直接ネイティブコードに変換します。`.c` ファイルは Windows x64 用の `.exe` になるか、Linux ARM64 用のバイナリになります。一度コンパイルした成果物は**特定の OS + 特定の CPU の組み合わせ**に縛られます。

.NET はこの構造を一段階分割しました。C# のソースはまず **IL (Intermediate Language)** という中間バイトコードにのみ変換されます。IL はハードウェアに非依存であり、OS にも非依存です。実際のネイティブ変換は**実行時点** (JIT) または**デプロイ直前** (AOT) に、**そのマシンがどのようなマシンかを知った後**に行われます。

この構造の利点は 3 つあります。

**① プラットフォーム独立性。** 同じ `.dll` が Windows・Linux・macOS のどこでも実行できます。ランタイムがそのマシンのネイティブ命令に変換してくれるからです。

**② 言語独立性。** IL に落とし込めさえすれば、C# 以外に F#・VB.NET も同じランタイム・BCL を使います。言語が変わっても下の層はそのままです。

**③ ランタイム最適化。** JIT は**実際に実行しているハードウェア情報と実行中の統計**を見て最適化できます。静的コンパイラより遅く変換する代わりに、より多くの情報を使えるというトレードオフです。

### JIT と AOT — 同じ IL、異なる変換タイミング

IL をネイティブコードに変換するタイミングは 2 種類あります。

- **JIT (Just-In-Time)**: プログラムが実行される**そのマシンで**、**その瞬間に**変換します。変換コストは実行時に含まれます。代わりにハードウェア情報を正確に知ることができます。デスクトップ .NET・Mono がこの方式です。
- **AOT (Ahead-Of-Time)**: アプリをデプロイする**前に事前に**ネイティブコードに変換しておきます。実行時には JIT がなくても動作します。**iOS のように JIT を許可しないプラットフォーム**では唯一の選択肢です。IL2CPP・NativeAOT がこの方式です。

この境界が、Unity の Mono vs IL2CPP の選択、モバイル・コンソールビルドの落とし穴、`Reflection.Emit` が IL2CPP で壊れる理由をすべて説明します。詳細は第 3 回で扱います。

---

## Part 4. Runtime と BCL — 実行を担う 2 本の柱

第 3 層 (IL) までは「ソースから何が作られるか」の話でした。第 4・5 層は「作られたものがどのように実行されるか」の話です。

### Runtime — IL を実際に動かす主体

**Runtime (ランタイム)** は IL を読んでネイティブに変換し実行するエンジンです。メモリ管理 (GC)、例外処理、型システム、スレッド管理、セキュリティをすべて担当します。Microsoft 公式用語集の定義はこうなっています。

> A CLR handles memory allocation and management. A CLR is also a virtual machine that not only executes apps but also generates and compiles code on-the-fly using a JIT compiler. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

重要な点は、**ランタイムはひとつではないということ**です。

- **CLR** — .NET Framework のランタイム。Windows 専用
- **CoreCLR** — .NET 5+ (旧 .NET Core) のランタイム。クロスプラットフォーム
- **Mono** — オープンソースのクロスプラットフォーム実装。Unity のデフォルトランタイム
- **IL2CPP** — Unity が開発した AOT ランタイム。IL を C++ に変換してネイティブコンパイル
- **NativeAOT** — .NET 公式の AOT デプロイモード

同じ C# コード・同じ IL でも、**どのランタイム上で動くか**によってパフォーマンス・メモリ特性・使用可能な機能が変わります。

### BCL — すべてのランタイムが基本として提供するライブラリ

**BCL (Base Class Library)** は `System.*` 名前空間に属する標準ライブラリです。`Console.WriteLine`、`List<T>`、`Dictionary<K,V>`、`File.ReadAllText`、`Task`、`CancellationToken` — 当然のように使っているほぼすべてが BCL です。

Microsoft 公式用語集の定義:

> A set of libraries that comprise the `System.*` (and to a limited extent `Microsoft.*`) namespaces. The BCL is a general purpose, lower-level framework that higher-level application frameworks, such as ASP.NET Core, build on. ([Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary))

BCL の位置を一文でまとめると、**「ランタイムは IL を動かすエンジンであり、BCL はそのエンジンの上で基本提供される標準ライブラリです。」** エンジンだけあってライブラリがなければ、`Console.WriteLine("hi")` の一行も動きません。

### 3 つの単語の関係整理

| 単語 | 層 | 例 | 役割 |
|------|-----|------|------|
| Assembly | 第 3 層 (IL の束) | `MyApp.dll`、`System.Collections.dll` | IL を格納するファイル単位 |
| Runtime | 第 4 層 | CLR / CoreCLR / Mono / IL2CPP | IL を実際に動かすエンジン |
| BCL | 第 5 層 | `System.*` 名前空間 | ランタイムの上で基本提供されるライブラリ |

「.NET Runtime をインストールする」という言葉は、日常的には**第 4 層 (エンジン) + 第 5 層 (BCL)** のセットをインストールするという意味です。この 2 つはほぼ常にセットで配布されます。

---

## Part 5. SDK vs Runtime — 開発者とユーザーの違い

デプロイの話をすると必ず出てくる質問があります。**「SDK と Runtime のどちらをインストールすればいいですか?」**

答えは役割によります。

- **SDK (Software Development Kit)**: アプリを**作る**人が必要なもの。コンパイラ、CLI ツール (`dotnet`)、ランタイム、BCL、テンプレートがすべて入っています
- **Runtime**: アプリを**実行するだけ**の人が必要なもの。エンジン (第 4 層) と BCL (第 5 層) のみが入っています。コンパイラはありません

確認コマンドはこうなります。

```bash
$ dotnet --list-sdks
8.0.404 [/usr/local/share/dotnet/sdk]
10.0.100 [/usr/local/share/dotnet/sdk]

$ dotnet --list-runtimes
Microsoft.NETCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
Microsoft.AspNetCore.App 8.0.11 [/usr/local/share/dotnet/shared/Microsoft.AspNetCore.App]
Microsoft.NETCore.App 10.0.0 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App]
```

開発者マシンには通常 SDK がインストールされており、SDK の中にランタイムが含まれています。サーバーや一般ユーザーのマシンにはランタイムだけインストールすれば十分です。

ただし、**Self-contained デプロイ**でパッケージングすると、ランタイムをアプリ内に含めて配布できます。この場合、ユーザーのマシンには何もインストールする必要がありません。NativeAOT でビルドすると、単一のネイティブバイナリになります。第 4 層の選択肢はここまで続きます。

---

## Part 6. Unity はどこに位置するのか

このブログの読者の多くはゲームプログラマーです。ですから、地図に **Unity の位置**を示してはじめて絵が完成します。

<div class="dotnet-unity-container">
<svg viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Unity が .NET スタックに位置する場所">
  <text x="380" y="28" text-anchor="middle" class="dotnet-unity-title">Unity と .NET スタック — 3 つの経路</text>

  <g class="dotnet-unity-col" data-col="server">
    <rect x="30" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane"/>
    <text x="140" y="78" text-anchor="middle" class="dotnet-unity-lane-label">サーバー・デスクトップ .NET</text>

    <rect x="50" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="140" y="120" text-anchor="middle" class="dotnet-unity-block-text">ASP.NET Core / WPF</text>

    <rect x="50" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="140" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET)</text>

    <rect x="50" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt"/>
    <text x="140" y="220" text-anchor="middle" class="dotnet-unity-block-text">CoreCLR (JIT)</text>

    <rect x="50" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="140" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="50" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="140" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>

  <g class="dotnet-unity-col" data-col="mono">
    <rect x="270" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane"/>
    <text x="380" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + Mono (Editor/デスクトップ)</text>

    <rect x="290" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="380" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="290" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="380" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard サブセット)</text>

    <rect x="290" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt"/>
    <text x="380" y="220" text-anchor="middle" class="dotnet-unity-block-text">Mono (JIT)</text>

    <rect x="290" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="380" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="290" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="380" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>

  <g class="dotnet-unity-col" data-col="il2cpp">
    <rect x="510" y="55" width="220" height="280" rx="8" class="dotnet-unity-lane dotnet-unity-lane-accent"/>
    <text x="620" y="78" text-anchor="middle" class="dotnet-unity-lane-label">Unity + IL2CPP (iOS/WebGL/コンソール)</text>

    <rect x="530" y="95" width="180" height="40" rx="4" class="dotnet-unity-block-app"/>
    <text x="620" y="120" text-anchor="middle" class="dotnet-unity-block-text">Unity Engine API</text>

    <rect x="530" y="145" width="180" height="40" rx="4" class="dotnet-unity-block-bcl"/>
    <text x="620" y="170" text-anchor="middle" class="dotnet-unity-block-text">BCL (.NET Standard サブセット)</text>

    <rect x="530" y="195" width="180" height="40" rx="4" class="dotnet-unity-block-rt-aot"/>
    <text x="620" y="220" text-anchor="middle" class="dotnet-unity-block-text">IL2CPP (AOT → C++)</text>

    <rect x="530" y="245" width="180" height="40" rx="4" class="dotnet-unity-block-il"/>
    <text x="620" y="270" text-anchor="middle" class="dotnet-unity-block-text">IL</text>

    <rect x="530" y="295" width="180" height="30" rx="4" class="dotnet-unity-block-lang"/>
    <text x="620" y="315" text-anchor="middle" class="dotnet-unity-block-text-sm">C# + Roslyn</text>
  </g>
</svg>
</div>

<style>
.dotnet-unity-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-unity-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.dotnet-unity-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-unity-lane { fill: rgba(99,102,241,0.05); stroke: #cbd5e1; stroke-width: 1; }
.dotnet-unity-lane-accent { fill: rgba(236,72,153,0.06); stroke: #f472b6; }
.dotnet-unity-lane-label { font-size: 13px; font-weight: 700; fill: #475569; }
.dotnet-unity-block-app { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1; }
.dotnet-unity-block-bcl { fill: #fef3c7; stroke: #d97706; stroke-width: 1; }
.dotnet-unity-block-rt { fill: #cffafe; stroke: #06b6d4; stroke-width: 1; }
.dotnet-unity-block-rt-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1; }
.dotnet-unity-block-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1; }
.dotnet-unity-block-lang { fill: #f1f5f9; stroke: #94a3b8; stroke-width: 1; }
.dotnet-unity-block-text { font-size: 12px; font-weight: 600; fill: #1e293b; }
.dotnet-unity-block-text-sm { font-size: 11px; fill: #475569; }
[data-mode="dark"] .dotnet-unity-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-unity-lane { fill: rgba(99,102,241,0.1); stroke: #475569; }
[data-mode="dark"] .dotnet-unity-lane-accent { fill: rgba(236,72,153,0.12); stroke: #f472b6; }
[data-mode="dark"] .dotnet-unity-lane-label { fill: #cbd5e1; }
[data-mode="dark"] .dotnet-unity-block-app { fill: rgba(99,102,241,0.25); stroke: #818cf8; }
[data-mode="dark"] .dotnet-unity-block-bcl { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-unity-block-rt { fill: rgba(6,182,212,0.25); stroke: #22d3ee; }
[data-mode="dark"] .dotnet-unity-block-rt-aot { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .dotnet-unity-block-il { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-unity-block-lang { fill: rgba(148,163,184,0.15); stroke: #64748b; }
[data-mode="dark"] .dotnet-unity-block-text { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-unity-block-text-sm { fill: #cbd5e1; }
@media (max-width: 768px) {
  .dotnet-unity-block-text { font-size: 10px; }
  .dotnet-unity-block-text-sm { font-size: 9px; }
  .dotnet-unity-lane-label { font-size: 11px; }
}
</style>

3 つの経路が**同じ C#・同じ IL を共有**しています。変わる層は**第 4 層 (ランタイム) と第 6 層 (アプリケーションフレームワーク)**だけです。Unity が「.NET ではないもの」に見える理由は単純に**異なるランタイムを使っているから**です。

### Unity の 2 つのランタイム

- **Mono (JIT)** — Unity エディターとデスクトップビルドのデフォルト。ビルドが速く、反復開発に有利です。Mono は Microsoft 公式用語集でも「.NET の実装のひとつ」として明記されています。[Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations)

- **IL2CPP (AOT)** — iOS・WebGL・コンソールターゲットのデフォルトかつ強制選択。IL を **C++ ソースに変換**した後、各プラットフォームのネイティブツールチェーン (Xcode、Emscripten、コンソール SDK) でネイティブバイナリを生成します。iOS は OS が JIT を許可しないため、Mono はそもそも選択肢になりません。[Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)

### ゲームプログラマーがこの地図から得るべきもの

この地図が示す実用的な結論を 3 つだけ挙げます。

**① `Reflection.Emit` が IL2CPP で壊れる**という事実の**本質**は、IL2CPP が**実行時に IL を新しく生成する JIT を持たないから**です。第 4 層が変わった結果が上の層の API の動作にまで伝播します。

**② Unity の「C#」は Unity が選んだランタイム・BCL の組み合わせに縛られます。** サーバー .NET で使える API が Unity では使えないことがあり、逆もまた然りです。`.csproj` の **API Compatibility Level** 設定がまさに第 5 層の範囲を決めるスイッチです。

**③ 「Unity は .NET エコシステムに属するか?」という問いへの答えは明確です。** 第 1〜3 層 (C#・Roslyn・IL) をそのまま使い、第 4 層 (ランタイム) だけ Unity 専用のものを使います。**同じエコシステム内の異なる実装**にすぎません。

---

## まとめ

今回描いた地図の結論を 3 行で整理します。

1. **C# は第 1 層の言語**であり、**.NET は第 2〜6 層全体のプラットフォーム**です。両者は同じ層ではありません。
2. **IL という中間層**が言語独立性・プラットフォーム独立性・ランタイム最適化を生み出すトレードオフの中心です。
3. **ランタイム** (CLR・CoreCLR・Mono・IL2CPP・NativeAOT) は複数が共存しており、**どのランタイム上で動くか**が同じコードのパフォーマンス・制約・利用可能な API を決定します。

この地図は以降のシリーズの**すべての記事**が参照する座標系です。どの記事でも「この話はどの層の話か?」をまず問うことをお勧めします。

---

## 次回予告

- **第 2 回。.NET の歴史 — Framework から一本の .NET へ** — 2002 年の .NET Framework 1.0 から 2020 年の .NET 5 統合、そして現在の .NET 10 までの系譜。なぜ「Core」が名前から消えたのか、なぜ .NET 4 が飛ばされたのかもここで解説します。
- **第 3 回。CLR・Mono・IL2CPP・NativeAOT — ランタイム分岐の比較** — 第 4 層の 5 つの実装を JIT/AOT・メモリ・リフレクション・ジェネリクスの観点から比較します。ゲームプログラマーにとって最も実用的な回になる予定です。

---

## 参考資料

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · 公式用語集
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · 実装概要
- [Microsoft Learn — Common Language Runtime (CLR) overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR 概要
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · Unity IL2CPP ドキュメント
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP の背景
