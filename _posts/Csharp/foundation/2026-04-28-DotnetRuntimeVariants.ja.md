---
title: CLR · Mono · IL2CPP · NativeAOT — ランタイムの分岐を比較する
lang: ja
date: 2026-04-28 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, clr, mono, il2cpp, nativeaot, jit, aot, runtime]
toc: true
toc_sticky: true
difficulty: intermediate
prerequisites:
  - /posts/DotnetEcosystemMap/
  - /posts/DotnetHistory/
tldr:
  - .NETランタイムは大きくJIT系列(CLR・CoreCLR・Mono)とAOT系列(IL2CPP・NativeAOT・Mono Full AOT)に分かれます
  - AOT系列は起動時間・配布サイズの面で有利ですが、Reflection.Emit・動的ジェネリックインスタンス化・Expression.Compileなどの機能が使えなくなります
  - ゲーム開発者がIL2CPPで出会う制約は、ランタイム自体の設計上の選択から来るものであり、Unity固有の問題ではありません
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 同じIL、異なる運命

前の2篇では、**.NETスタックの第4層 (Runtime)** が複数の実装に分かれているという事実を確認しました。今回はその実装を一つずつ解剖して比較します。

現時点で実務的に意味のある**5つのランタイム**は次のとおりです。

| ランタイム | 所属 | 登場 | 状態 |
|--------|------|------|------|
| **CLR** | .NET Framework | 2002 | 凍結 (4.8.1) |
| **CoreCLR** | .NET 5+ | 2016 (Core 1.0) | アクティブ |
| **Mono** | Xamarin·Unity | 2004 | アクティブ (Unity フォーク) |
| **IL2CPP** | Unity | 2014 | アクティブ |
| **NativeAOT** | .NET 7+ | 2022 | アクティブ |

同じC#コードを書いても、**どのランタイム上で動作するか**によってパフォーマンス・メモリ・利用可能なAPI・配布サイズが大きく変わります。この篇の目的は、その違いを**実用的な選択基準**として整理することです。

5つのランタイムは複雑に見えますが、**一つの軸**さえ掴めばほぼすべてが整理されます。その軸が**JIT vs AOT**です。

---

## Part 1. たった一つの軸 — JIT vs AOT

1篇で、ILをネイティブコードに翻訳するタイミングが2種類あると述べました。この翻訳タイミングが**5つのランタイムを2つのグループに分ける決定的な違い**です。

<div class="dotnet-runtime-tree-container">
<svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ランタイム5種 JIT AOT 分類ツリー">
  <text x="380" y="28" text-anchor="middle" class="runtime-tree-title">.NETランタイム5種 — JIT / AOT 分類</text>

  <g class="runtime-tree-root">
    <rect x="310" y="60" width="140" height="50" rx="8" class="runtime-tree-box-root"/>
    <text x="380" y="82" text-anchor="middle" class="runtime-tree-text-bold">IL</text>
    <text x="380" y="100" text-anchor="middle" class="runtime-tree-text-sm">(中間バイトコード)</text>
  </g>

  <line x1="380" y1="110" x2="200" y2="160" class="runtime-tree-line"/>
  <line x1="380" y1="110" x2="560" y2="160" class="runtime-tree-line"/>

  <g class="runtime-tree-branch jit">
    <rect x="120" y="160" width="160" height="50" rx="8" class="runtime-tree-box-jit"/>
    <text x="200" y="182" text-anchor="middle" class="runtime-tree-text-bold">JIT 系列</text>
    <text x="200" y="200" text-anchor="middle" class="runtime-tree-text-sm">実行時に翻訳</text>
  </g>

  <g class="runtime-tree-branch aot">
    <rect x="480" y="160" width="160" height="50" rx="8" class="runtime-tree-box-aot"/>
    <text x="560" y="182" text-anchor="middle" class="runtime-tree-text-bold">AOT 系列</text>
    <text x="560" y="200" text-anchor="middle" class="runtime-tree-text-sm">ビルド時に翻訳</text>
  </g>

  <line x1="200" y1="210" x2="80" y2="260" class="runtime-tree-line"/>
  <line x1="200" y1="210" x2="200" y2="260" class="runtime-tree-line"/>
  <line x1="200" y1="210" x2="320" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="440" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="560" y2="260" class="runtime-tree-line"/>
  <line x1="560" y1="210" x2="680" y2="260" class="runtime-tree-line"/>

  <g class="runtime-tree-leaf">
    <rect x="20" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="80" y="282" text-anchor="middle" class="runtime-tree-text-bold">CLR</text>
    <text x="80" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET Framework</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="140" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="200" y="282" text-anchor="middle" class="runtime-tree-text-bold">CoreCLR</text>
    <text x="200" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET 5+</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="260" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf"/>
    <text x="320" y="282" text-anchor="middle" class="runtime-tree-text-bold">Mono</text>
    <text x="320" y="300" text-anchor="middle" class="runtime-tree-text-sm">Unity デフォルト</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="380" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="440" y="282" text-anchor="middle" class="runtime-tree-text-bold">IL2CPP</text>
    <text x="440" y="300" text-anchor="middle" class="runtime-tree-text-sm">Unity iOS/WebGL</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="500" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="560" y="282" text-anchor="middle" class="runtime-tree-text-bold">NativeAOT</text>
    <text x="560" y="300" text-anchor="middle" class="runtime-tree-text-sm">.NET 7+</text>
  </g>

  <g class="runtime-tree-leaf">
    <rect x="620" y="260" width="120" height="50" rx="8" class="runtime-tree-box-leaf-aot"/>
    <text x="680" y="282" text-anchor="middle" class="runtime-tree-text-bold">Mono Full AOT</text>
    <text x="680" y="300" text-anchor="middle" class="runtime-tree-text-sm">Xamarin iOS</text>
  </g>
</svg>
</div>

<style>
.dotnet-runtime-tree-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-runtime-tree-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.runtime-tree-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.runtime-tree-box-root { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.4; }
.runtime-tree-box-jit { fill: #cffafe; stroke: #06b6d4; stroke-width: 1.4; }
.runtime-tree-box-aot { fill: #d1fae5; stroke: #10b981; stroke-width: 1.4; }
.runtime-tree-box-leaf { fill: #e0f2fe; stroke: #0284c7; stroke-width: 1.2; }
.runtime-tree-box-leaf-aot { fill: #ecfccb; stroke: #65a30d; stroke-width: 1.2; }
.runtime-tree-text-bold { font-size: 14px; font-weight: 700; fill: #1e293b; }
.runtime-tree-text-sm { font-size: 11px; fill: #475569; }
.runtime-tree-line { stroke: #94a3b8; stroke-width: 1.5; fill: none; }
[data-mode="dark"] .runtime-tree-title { fill: #e5e7eb; }
[data-mode="dark"] .runtime-tree-box-root { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .runtime-tree-box-jit { fill: rgba(6,182,212,0.25); stroke: #22d3ee; }
[data-mode="dark"] .runtime-tree-box-aot { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .runtime-tree-box-leaf { fill: rgba(2,132,199,0.25); stroke: #38bdf8; }
[data-mode="dark"] .runtime-tree-box-leaf-aot { fill: rgba(101,163,13,0.25); stroke: #a3e635; }
[data-mode="dark"] .runtime-tree-text-bold { fill: #f1f5f9; }
[data-mode="dark"] .runtime-tree-text-sm { fill: #cbd5e1; }
[data-mode="dark"] .runtime-tree-line { stroke: #64748b; }
@media (max-width: 768px) {
  .runtime-tree-text-bold { font-size: 11px; }
  .runtime-tree-text-sm { font-size: 9px; }
}
</style>

### JIT 系列 — CLR · CoreCLR · Mono

JIT (Just-In-Time) は、**アプリが実行されているそのマシン上で、その瞬間に** ILをネイティブコードに翻訳します。この方式の長所と短所は以下のとおりです。

**長所**
- ハードウェア情報を**実際に実行されているマシン**から取得して最適化が可能
- 実行時の統計 (Tiered Compilation、PGO) を活用した後続の再最適化が可能
- **`Reflection.Emit`・`Expression.Compile`** のような**実行時コード生成API**が動作する

**短所**
- 実行初期にJITコストを支払う (Cold Start が遅い)
- 実行するマシンにランタイムのインストールが必要
- JIT自体がメモリ・CPUを消費する

### AOT 系列 — IL2CPP · NativeAOT · Mono Full AOT

AOT (Ahead-Of-Time) は、**アプリを配布する前**、開発者のビルドマシン上でILをネイティブコードに翻訳しておきます。

**長所**
- **Cold Start が極めて速い** — 翻訳コストがすでに支払われている
- **JITが許可されていないプラットフォーム** (iOS、コンソール、WebAssembly) での唯一の選択肢
- 配布時にランタイムのインストールが不要 (NativeAOTの場合は単一バイナリ)

**短所**
- **実行時に新しいコードを生成できない** → `Reflection.Emit` が使えない
- **動的ジェネリックインスタンス化の制限** → 実行時に新たな `List<MyRuntimeType>` を作れない
- **ビルド時間の増加** — すべてのILを事前に翻訳する
- すべてのジェネリックインスタンスを事前生成 → 配布バイナリのサイズが増加

この表一枚が、以降のすべての比較の基盤となります。

---

## Part 2. 各ランタイムの紹介

### CLR — .NET Framework のランタイム

- リリース: 2002年
- プラットフォーム: Windows 専用
- コンパイル: JIT
- 状態: **凍結**。.NET Framework 4.8.1 (2022) が最後のリリース
- 特記事項: WPF・WinForms・WCF のような Windows 専用の上位フレームワークと強く結びついている

新規開発でCLRを選ぶ理由はありません。レガシーのメンテナンス用途としてのみ意味があります。

### CoreCLR — 現代 .NET のメインランタイム

- リリース: 2016年 (.NET Core 1.0)、2020年から .NET 5+ に統合
- プラットフォーム: Windows・Linux・macOS・FreeBSD
- コンパイル: **Tiered JIT** (Tier 0 高速初期翻訳 → Tier 1 最適化再翻訳)
- 特記事項: **PGO (Profile-Guided Optimization)** 対応、実行統計でホットコードをより積極的に最適化

CoreCLR は JITの短所 (初期コスト) を**Tiered Compilation**で緩和したランタイムです。起動時は高速なTier 0翻訳のみを行い、頻繁に呼ばれるホットコードだけを後でTier 1で再コンパイルします。([Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr))

サーバー・Web・デスクトップ・WASMまで、.NETのデフォルトかつ最も活発に進化しているランタイムです。

### Mono — クロスプラットフォームの原点

- リリース: 2004年
- プラットフォーム: Windows・Linux・macOS・iOS・Android・WebAssembly
- コンパイル: JITがデフォルト、**Full AOT モードも可能** (iOSのようにJITが禁止された環境向け)
- 特記事項: 小さいフットプリント。モバイル・組み込み・ゲームエンジンに適している

Monoは2篇で見たように、外部のオープンソースから始まり Microsoft 公式実装となったランタイムです。2024年にMicrosoftがWineHQに所有権を移譲し、本家はメンテナンスモードに入りましたが、**Unityは独自フォークを運営**しています。

Unityで `Scripting Backend: Mono` を選択すると、このランタイムがエディターとデスクトップビルドに使用されます。

### IL2CPP — Unity が作ったAOTパイプライン

- リリース: 2014年
- プラットフォーム: iOS・WebGL・コンソール (PS5・Xbox・Switch)・Android・Windows・macOS
- コンパイル: **AOT 専用**。ILを**C++コードに変換**した後、プラットフォーム別のC++ツールチェーン (Xcode・Emscripten・コンソール SDK) でネイティブバイナリを生成
- 特記事項: `Reflection.Emit` 禁止、ジェネリックインスタンス化の制限、ビルド時間の増加

IL2CPPの存在理由を一言で要約すると次のとおりです。**「iOS・WebGL・コンソールがJITを許可しないため、Mono Full AOTでは解決できないパフォーマンス・制約の問題をUnityが独自のAOTパイプラインで解決しようとしたためです。」** ([Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html)) 内部の動作原理はUnityが直接公開した ["An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) の連載で確認できます。

### NativeAOT — Microsoft のサーバー・クラウド AOT

- リリース: 2022年 (.NET 7、コンソールアプリ・ライブラリ対応 — [.NET Blog — "Announcing .NET 7" (2022.11.08)](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/))
- 2023年 (.NET 8、ASP.NET Core 対応拡大)
- プラットフォーム: Windows・Linux・macOS・iOS (実験的)・Android (実験的)
- コンパイル: **AOT 専用**。ILをネイティブコードに直接コンパイル (C++経由なし)
- 特記事項: **単一ネイティブバイナリ**での配布、ランタイムのインストール不要、起動時間が極めて速い

NativeAOTのターゲットは**コンテナ・サーバーレス・CLIツール**です。ゲーム開発者がIL2CPPを使う理由 (プラットフォームがJITを禁止) とは異なる動機です。NativeAOTが実験段階から正式リリースに昇格した経緯は ["Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/) で詳しく記述されています。([Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

---

## Part 3. ランタイム比較マトリクス

同じ軸で5つのランタイムを一覧で比較します。

| 軸 | CLR | CoreCLR | Mono | IL2CPP | NativeAOT |
|----|-----|---------|------|--------|-----------|
| **コンパイル方式** | JIT | Tiered JIT | JIT (+Full AOT オプション) | AOT only | AOT only |
| **クロスプラットフォーム** | Windows | Win/Lin/Mac | 広範囲 | Unity 対応全プラットフォーム | Win/Lin/Mac |
| **Cold Start** | 遅い | 中間 (Tier 0 速い) | 中間 | **速い** | **最も速い** |
| **実行中の再最適化** | なし | **あり (PGO)** | 限定的 | なし | なし |
| **`Reflection.Emit`** | O | O | O | **X** | **X** |
| **`Expression.Compile`** | O | O | O | **インタープリタモード** | **インタープリタモード** |
| **動的ジェネリックインスタンス化** | O | O | O | **制限あり** | **制限あり** |
| **ランタイムのインストールが必要** | O | O (または Self-contained) | O | X (エンジン内蔵) | **X** |
| **配布サイズ** | 小 (ランタイム別途) | 中 | 中 | 大 (エンジン含む) | 中 |
| **ビルド時間** | 速い | 速い | 速い | **非常に遅い** | **遅い** |
| **主な用途** | レガシー Windows | サーバー・Web・デスクトップ | Unity エディター・デスクトップ | Unity モバイル・コンソール | サーバーレス・CLI |

### この表から読み取るべき3つのこと

**① AOT の2つのランタイム (IL2CPP、NativeAOT) が同じ制約を共有しています。**
`Reflection.Emit`・`Expression.Compile`・動的ジェネリック — この3項目がいずれも**JITに依存する機能**だからです。AOT環境では、根本的に実行時に新しいILを生成するエンジンがありません。

**② Cold Start は AOT が圧倒的に有利です。**
iOSでJITが禁止されているのはセキュリティ上の理由 (メモリの `W^X` 原則) ですが、AOTの**高速な起動**はサーバーレス・CLIツールでも決定的な優位点です。`dotnet run` するたびに数百ミリ秒のJITコストを支払う必要がなくなります。

**③ CoreCLR の Tiered JIT は折衷案です。**
JITコストを完全になくすことはできませんが、**Tier 0 で高速に翻訳 → 頻繁に呼ばれるコードだけ Tier 1 で最適化**するという方式で「最悪を避け、最善を追求」します。これがサーバー・Webで CoreCLR が今もデフォルトである理由です。

---

## Part 4. IL2CPP の実際のパイプライン

IL2CPPの「ILをC++に変換してからネイティブにコンパイルする」という説明が抽象的に聞こえることがあります。実際のビルドパイプラインを図示すると以下のようになります。

<div class="il2cpp-pipeline-container">
<svg viewBox="0 0 860 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="IL2CPP ビルドパイプライン">
  <defs>
    <marker id="il2cpp-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="il2cpp-arrow-head"/>
    </marker>
  </defs>

  <text x="430" y="28" text-anchor="middle" class="il2cpp-pipeline-title">IL2CPP ビルドパイプライン — IL からネイティブバイナリまで</text>

  <g>
    <rect x="20" y="90" width="130" height="60" rx="8" class="il2cpp-box-cs"/>
    <text x="85" y="118" text-anchor="middle" class="il2cpp-box-text-bold">C# ソース</text>
    <text x="85" y="136" text-anchor="middle" class="il2cpp-box-text-sm">.cs</text>
  </g>

  <g>
    <rect x="180" y="90" width="130" height="60" rx="8" class="il2cpp-box-roslyn"/>
    <text x="245" y="118" text-anchor="middle" class="il2cpp-box-text-bold">Roslyn</text>
    <text x="245" y="136" text-anchor="middle" class="il2cpp-box-text-sm">C# → IL</text>
  </g>

  <g>
    <rect x="340" y="90" width="130" height="60" rx="8" class="il2cpp-box-il"/>
    <text x="405" y="118" text-anchor="middle" class="il2cpp-box-text-bold">IL</text>
    <text x="405" y="136" text-anchor="middle" class="il2cpp-box-text-sm">.NET Assemblies</text>
  </g>

  <g>
    <rect x="500" y="90" width="160" height="60" rx="8" class="il2cpp-box-converter"/>
    <text x="580" y="118" text-anchor="middle" class="il2cpp-box-text-bold">il2cpp.exe</text>
    <text x="580" y="136" text-anchor="middle" class="il2cpp-box-text-sm">IL → C++</text>
  </g>

  <g>
    <rect x="690" y="90" width="150" height="60" rx="8" class="il2cpp-box-native"/>
    <text x="765" y="114" text-anchor="middle" class="il2cpp-box-text-bold">プラットフォーム ツールチェーン</text>
    <text x="765" y="130" text-anchor="middle" class="il2cpp-box-text-sm">Xcode / Emscripten</text>
    <text x="765" y="144" text-anchor="middle" class="il2cpp-box-text-sm">コンソール SDK</text>
  </g>

  <line x1="150" y1="120" x2="175" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="310" y1="120" x2="335" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="470" y1="120" x2="495" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>
  <line x1="660" y1="120" x2="685" y2="120" class="il2cpp-line" marker-end="url(#il2cpp-arrow)"/>

  <text x="85" y="178" text-anchor="middle" class="il2cpp-stage-label">1. 作成</text>
  <text x="245" y="178" text-anchor="middle" class="il2cpp-stage-label">2. IL コンパイル</text>
  <text x="405" y="178" text-anchor="middle" class="il2cpp-stage-label">3. IL 中間物</text>
  <text x="580" y="178" text-anchor="middle" class="il2cpp-stage-label">4. C++ 変換 (Unity)</text>
  <text x="765" y="178" text-anchor="middle" class="il2cpp-stage-label">5. ネイティブビルド</text>
</svg>
</div>

<style>
.il2cpp-pipeline-container { margin: 1.5rem 0; overflow-x: auto; }
.il2cpp-pipeline-container svg { width: 100%; max-width: 860px; height: auto; display: block; margin: 0 auto; }
.il2cpp-pipeline-title { font-size: 16px; font-weight: 700; fill: #1f2937; }
.il2cpp-box-cs { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.2; }
.il2cpp-box-roslyn { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.il2cpp-box-il { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.il2cpp-box-converter { fill: #d1fae5; stroke: #10b981; stroke-width: 1.4; }
.il2cpp-box-native { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.il2cpp-box-text-bold { font-size: 14px; font-weight: 700; fill: #1e293b; }
.il2cpp-box-text-sm { font-size: 11px; fill: #475569; }
.il2cpp-line { stroke: #6366f1; stroke-width: 1.8; fill: none; }
.il2cpp-arrow-head { fill: #6366f1; }
.il2cpp-stage-label { font-size: 11px; fill: #64748b; font-style: italic; }
[data-mode="dark"] .il2cpp-pipeline-title { fill: #e5e7eb; }
[data-mode="dark"] .il2cpp-box-cs { fill: rgba(99,102,241,0.25); stroke: #818cf8; }
[data-mode="dark"] .il2cpp-box-roslyn { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .il2cpp-box-il { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .il2cpp-box-converter { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .il2cpp-box-native { fill: rgba(236,72,153,0.25); stroke: #f472b6; }
[data-mode="dark"] .il2cpp-box-text-bold { fill: #f1f5f9; }
[data-mode="dark"] .il2cpp-box-text-sm { fill: #cbd5e1; }
[data-mode="dark"] .il2cpp-line { stroke: #a78bfa; }
[data-mode="dark"] .il2cpp-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .il2cpp-stage-label { fill: #94a3b8; }
@media (max-width: 768px) {
  .il2cpp-box-text-bold { font-size: 11px; }
  .il2cpp-box-text-sm { font-size: 9px; }
  .il2cpp-stage-label { font-size: 9px; }
}
</style>

### なぜ中間にC++を挟んだのか

ILからネイティブコードに**直接変換するコンパイラ**も理論上は可能です (NativeAOTはそうしています)。ところがUnityは **IL → C++ → ネイティブ** の2段階を選びました。この選択の根拠はUnityが公開した ["IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) ブログで、実際に生成されたC++の例とともに説明されています。要約すると以下のとおりです。

**① プラットフォーム別C++ツールチェーンの再利用**
iOSはXcode LLVM、WebGLはEmscripten、コンソールは各メーカーのSDK、AndroidはNDK — プラットフォームごとに**すでに最高水準で最適化されたC++コンパイラ**が存在します。ILをC++に変換さえしておけば、残りの最適化はプラットフォームのツールチェーンが担当します。同等の水準を達成するには、Unityは**プラットフォームごとに別々のバックエンド**を開発・維持しなければなりませんでした。

**② プラットフォーム固有機能へのアクセス**
C++の中間物は、各プラットフォームのネイティブライブラリ・SDKと自然に連携できます。直接AOTコンパイラを作成していたら、このような統合はずっと複雑になっていたでしょう。

**③ デバッグのしやすさ**
IL2CPPビルドでランタイムクラッシュが発生した場合、生成されたC++コードを読むことができます。これは純粋なバイナリ出力よりずっと追跡しやすいです。

---

## Part 5. AOT 環境の5つの制約

Microsoft 公式ドキュメントが明示しているNativeAOTの主な制約です。IL2CPPも**ほぼ同じ制約**を持っています。([Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/))

### ① `Reflection.Emit` 禁止

**現象**: `System.Reflection.Emit` で実行時に動的にメソッド・型を作成するコードが実行されません。

**原因**: AOT環境には**実行時にILを受け取ってネイティブに翻訳するJITがありません**。EmitはILを作成するAPIですが、受け取って翻訳するエンジンがないため動作できません。

**影響**: 多くのシリアライズライブラリ (旧 `Newtonsoft.Json` の一部パス)、高速プロキシ生成 (Castle DynamicProxy)、DIコンテナの動的コンストラクタインジェクションなどが壊れたり遅くなったりします。

**代替手段**: **Source Generator**。コンパイル時に必要なコードを生成しておけば、実行時のEmitが不要になります。`System.Text.Json` はこの方向に転換しており、AOTフレンドリーです。

### ② `Expression.Compile` はインタープリタモードへ

**現象**: LINQクエリや `Expression<Func<T>>.Compile()` が**インタープリタモード**で実行されます。コンパイルされたネイティブコードほど速くありません。

**原因**: Expressionのコンパイルは実行時にILを生成してJITする方式であるため、AOT環境では不可能です。

**影響**: ORM (EF Coreの一部パス)、繰り返し呼ばれるLINQ-to-Expressionコードのパフォーマンスが低下する可能性があります。

**代替手段**: 頻繁に実行されるExpressionは事前にデリゲートに変換しておく。またはSource Generatorベースの代替ライブラリを検討する。

### ③ 動的ジェネリックインスタンス化の制限

**現象**: 実行時に `Type.MakeGenericType(typeof(List<>), runtimeType)` のような方法で**コードに存在しなかったジェネリックの組み合わせ**を作ると、失敗またはエラーが発生します。

**原因**: AOTコンパイラは**ビルド時点ですべてのジェネリックインスタンスを事前生成**します。ビルド時点に存在しなかった組み合わせはネイティブコードもありません。

**影響**: 実行時の型に基づく `Dictionary<string, object>` の構成を `Dictionary<string, RuntimeType>` に最適化する一般的なパターンが壊れます。

**代替手段**: ジェネリックの組み合わせをビルド時点で明示的に一度使用する (`_ = new List<MyType>()` のような「ヒント」) か、非ジェネリックバージョンで回避する。

### ④ リフレクションとトリマーの相互作用

**現象**: `Type.GetMethod("SomeMethod")` のような文字列ベースのリフレクションが予期せず失敗する — **トリマーが当該メソッドを使用されていないと判断して削除**したため。

**原因**: AOT配布には**トリミング (Trimming) が必須**です。使用されていないコードをビルド結果から削除してバイナリサイズを小さくしますが、文字列ベースの参照は静的解析ができません。

**影響**: 多くの旧来のライブラリがAOTビルドで実行時エラーになります。

**代替手段**: `DynamicDependency` 属性でトリマーにヒントを与える、またはSource Generatorでリフレクションを除去する。

### ⑤ 配布バイナリサイズの増大

**現象**: AOTビルドは**すべてのジェネリックインスタンス・ランタイムライブラリ・依存関係を単一バイナリ**に含めるため、framework-dependent JITビルドよりファイルサイズが大きくなります。

**原因**: 「Self-contained」がデフォルトであるため。ランタイムのインストールがない代わりに、アプリ内に持ち込みます。

**影響**: モバイルアプリのインストールサイズ、コンテナイメージのサイズ、配布時間の増加。

**代替手段**: 積極的なトリミング・`PublishTrimmed=true`・不要な機能フラグのオフ。

---

## Part 6. ランタイム意思決定ガイド

プロジェクトの種類ごとにどのランタイムを選ぶべきかを、簡単なツリーで整理します。

**サーバー・Web APIを作る** → **CoreCLR** (.NET 8+)。高負荷・低遅延・高速な配布が求められる場合は**NativeAOT を検討**。ただし必ずAOT制約を確認すること。

**CLIツール・サーバーレス関数を作る** → **NativeAOT**。Cold Startが決定的で、依存関係が多くない場合はAOT制約を受け入れられます。

**Unityでゲームを作る** → エディター・デスクトップビルドは**Mono**。iOS・WebGL・コンソールビルドは**IL2CPP** (強制)。デスクトップビルドもIL2CPPでパフォーマンス改善が可能です。

**Windowsデスクトップアプリを新規開発する** → **CoreCLR + WPF/WinForms on .NET 8+**。CLR (.NET Framework) は避ける。

**レガシー .NET Framework システムを維持する** → **CLR**。ただし新機能の開発は .NET 8+ への段階的な移行計画が必要。

**モバイルアプリを作る (非Unity)** → 2024年のXamarinサポート終了以降は**.NET MAUI**が公式の選択肢。内部的にはMono + NativeAOTの混合。

---

## まとめ

今回の篇のポイントを4行で整理します。

1. **.NETランタイムはJIT系列とAOT系列に分かれており**、この軸一つがパフォーマンス特性・制約・配布サイズの大部分を決定します。
2. **AOT系列の制約はプラットフォームの制約ではなく設計上の選択**です。`Reflection.Emit`・動的ジェネリック・`Expression.Compile` が使えなくなるのは実行時にJITがないためであり、IL2CPP・NativeAOT双方に共通しています。
3. **IL2CPPがIL → C++ → ネイティブの2段階を経る理由**は、プラットフォーム別のC++ツールチェーンの高度な最適化を再利用するためです。
4. **ゲームプログラマーがUnityで出会う制約** (Reflection.Emit、ジェネリックの落とし穴、トリマーの問題) はランタイム設計の必然的な帰結であり、Source Generatorのような**コンパイル時メタプログラミング**で回避するのが現代的な解法です。

---

## Foundation シリーズの締めくくり

3篇にわたって **.NETの地図 (1篇) → 歴史 (2篇) → ランタイムの分岐 (3篇)** を巡りました。この3篇は、今後続くすべてのC#シリーズの**共通の座標系**となります。

次のシリーズは**非同期シリーズ (6篇)**です。今回扱ったJIT・AOTの文脈が、`UniTask` がなぜ `Task` よりUnityに適しているのか、`async/await` がIL2CPPでどのように変形されるのか、`Reflection.Emit` を避けたSource Generatorがなぜ重要なのかに自然につながっていきます。

---

## 参考資料

### 一次ソース · 公式発表および技術分析

- [.NET Blog — "Announcing .NET 7"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7/) · 2022年11月、NativeAOTの正式取り込みを含む .NET 7 リリース公式発表
- [.NET Blog — "Announcing .NET 7 Preview 3"](https://devblogs.microsoft.com/dotnet/announcing-dotnet-7-preview-3/) · NativeAOTが `runtimelab` から `runtime` に昇格した時点の詳細
- [Unity Blog — "An introduction to IL2CPP internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) · Unityエンジニアが直接書いたIL2CPP内部構造の解説
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · 実際に生成されたC++コードの例で見るIL → C++変換過程

### リファレンスドキュメント

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · CLR・JIT・AOT・NativeAOT の公式定義
- [Microsoft Learn — CLR overview](https://learn.microsoft.com/en-us/dotnet/standard/clr) · CLR 設計思想
- [Microsoft Learn — Native AOT deployment](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · NativeAOT 制約の公式リスト
- [Microsoft Learn — .NET implementations](https://learn.microsoft.com/en-us/dotnet/fundamentals/implementations) · 実装の比較
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/scripting-backends-il2cpp.html) · IL2CPP 公式ドキュメント
- [Unity Manual — Scripting backends introduction](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-backends-intro.html) · Mono vs IL2CPP 選択ガイド
