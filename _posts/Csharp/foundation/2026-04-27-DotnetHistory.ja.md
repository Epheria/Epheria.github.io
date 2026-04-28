---
title: .NET の歴史 — Framework から一つの .NET へ
lang: ja
date: 2026-04-27 09:00:00 +0900
categories: [Csharp, foundation]
tags: [csharp, dotnet, history, mono, xamarin, dotnet-core]
toc: true
toc_sticky: true
difficulty: beginner
prerequisites:
  - /posts/DotnetEcosystemMap/
tldr:
  - .NET Framework は 2002年に Windows 専用としてスタートし、2022年の 4.8.1 が最終バージョンとして凍結されました
  - .NET Core は 2016年に Windows 依存を断ち切った再出発であり、2020年の .NET 5 で二つの系譜が一つに統合されました
  - Mono は 2001年に Linux で .NET を使いたいという外部プロジェクトとして始まり、Xamarin と Microsoft を経て公式実装として取り込まれ、Unity のランタイム基盤となりました
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論: 歴史を知ることが実用的な理由

この記事は三つの疑問に答えるための内容です。

1. **「.NET 4」はなぜ飛ばされたのか？** — .NET Core 3.1 の次のバージョンがなぜ 4 ではなく 5 なのか？
2. **「Core」はなぜ名前から消えたのか？** — .NET Core 3.1 は存在したのに、.NET Core 5 はなぜ存在しないのか？
3. **Unity はなぜ Mono の上にあるのか？** — Microsoft が作ったランタイムが別にあるのに、Unity はなぜ外部実装を使っているのか？

これらの疑問は**歴史を知らなければ答えられません**。公式ドキュメントは現在の状態を説明するだけで、なぜ今のような姿になったのかは教えてくれません。その空白を埋めることが、この記事の目的です。

歴史は長いので Part に分けて進めます。**四つの時代** — 誕生 (2000〜2004)、成熟 (2005〜2013)、大転換 (2014〜2019)、統合 (2020〜)。各時代の終わりに、ゲームプログラマにとって意味のある点だけを取り上げます。

---

## Part 1. 誕生 (2000〜2004)

### .NET Framework の出発

1990 年代後半、Microsoft は二つの方向からの圧力を受けていました。

- **Sun の Java が急台頭** — 「一度書けばどこでも動く」というスローガンがエンタープライズ市場を揺るがしました。J2EE スタックは銀行・通信会社の標準的な選択肢でした。
- **Windows 開発スタックの断片化** — Visual Basic、MFC、COM、ActiveX が混在しており、互いの互換性が乏しい状態でした。

Microsoft の回答が **.NET Framework** でした。複数の言語 (C#・VB.NET・C++/CLI) が一つのランタイム (CLR) と一つの標準ライブラリ (BCL) を共有する設計。Java の「write once, run anywhere」を言語軸で「write in any .NET language, run on any Windows」に変えたものと言えます。

**2002 年 2 月 13 日、.NET Framework 1.0** リリース。このとき C# 1.0 も同時に登場しました。

一つの核心的な制約がありました。**Windows 専用**であったということです。Java が JVM を通じて OS 独立性を確保したのとは異なり、.NET Framework の CLR は Windows 上でしか動作しませんでした。この制約が、その後 20 年の歴史を引っ張る主要な軸となります。

### Mono — Linux で .NET を使いたかった人

同じ時期、スペイン出身の開発者 **Miguel de Icaza** は GNOME デスクトッププロジェクトを率いていました。彼は .NET の仕様が **ECMA に公開標準として提出されたこと**を見て、同じランタイムを **Linux 上で実装できないか**と考えました。

- **2001 年 7 月 19 日** — O'Reilly カンファレンスで **Mono** プロジェクトを発表。彼の会社 Ximian が主導。
- **2003 年** — Novell が Ximian を買収。Mono は Novell の資産となります。
- **2004 年 6 月 30 日** — Mono 1.0 リリース。C# 1.x と CLR を Linux・macOS で動作させることに成功。

この時点で Microsoft は Mono に対して友好的でも敵対的でもありませんでした。「自分たちが作ったものではないが、阻止もしない」という状態でした。([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

### 意味

Part 1 が生み出したものは**二つの系譜**です。

- **.NET Framework 系譜** — Microsoft 公式、Windows 専用、商用
- **Mono 系譜** — 外部オープンソース、クロスプラットフォーム、Linux/macOS

この二つが一つに合わさるまでには、さらに **15 年**かかります。

---

## Part 2. 成熟 (2005〜2013)

### .NET Framework の言語進化

2005 年から 2010 年にかけて、.NET Framework は言語と BCL を急速に拡張します。

| 年 | バージョン | 主な追加内容 |
|------|------|----------|
| 2005 | 2.0 | **ジェネリクス (Generics)** — C# の核心機能 |
| 2006 | 3.0 | WPF、WCF、WF (Windows 統合フレームワーク群) |
| 2008 | 3.5 | **LINQ** — クエリ表現の言語化 |
| 2010 | 4.0 | TPL (Task Parallel Library)、`dynamic` |
| 2012 | 4.5 | **`async/await`** — 非同期の言語化 |
| 2015 | 4.6 | RyuJIT (新 JIT)、パフォーマンス改善 |
| 2017 | 4.7 | 高 DPI 改善 |
| 2019 | 4.8 | JIT 最適化、最後のメジャーバージョン |
| 2022 | 4.8.1 | 最終リリース — **事実上の凍結** |

.NET Framework はここで止まります。**4.8.1 が最終バージョン**であり、以降はセキュリティパッチのみ提供されます。Microsoft は「.NET Framework は継続サポートするが、新機能は追加しない」という立場を公式化しました。([Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies))

### Mono の拡張と Xamarin 設立

Mono も同時期に成熟します。

- **2011 年 4 月** — Attachmate が Novell を買収し、Mono チームが解雇される危機に。
- **2011 年 5 月 16 日** — Miguel de Icaza が **Xamarin** という会社を設立し、Mono を引き継ぎます。
- Xamarin は Mono を商業製品化 — **iOS・Android 向け C# 開発ツール** (MonoTouch、Mono for Android) で収益を生み出します。

### Unity の Mono 採用

Unity Technologies は 2005 年にゲームエンジン Unity をリリースし、スクリプト言語として **Mono ベースの C# (および初期の UnityScript・Boo)** を採用します。その理由はシンプルです。

- **クロスプラットフォーム**: Unity は最初から Mac・Windows・コンソールをターゲットとしており、.NET Framework は Windows 上でしか動作しませんでした。Mono だけが選択肢でした。
- **小さなフットプリント**: Mono はモバイル・組み込み向けに設計されており、メモリ使用量が少なかったです。
- **ライセンスの柔軟性**: 商用ライセンスの交渉が可能な構造でした。

この決定が**今日の Unity ゲームの C# コードが Mono ランタイム上で動く理由**です。20 年前のエンジニアリングの選択が今でも続いています。

### 意味

Part 2 において .NET Framework は**完成度の高い商用 Windows スタック**となり、Mono は**クロスプラットフォーム .NET の唯一の実用的選択肢**となりました。二つの系譜はますます異なる道を歩みました。

---

## Part 3. 大転換 (2014〜2019)

### Microsoft の戦略転換

**2014 年 4 月**、Microsoft は開発者カンファレンス Build で二つのことを発表します。

1. **.NET Foundation 設立** ([Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation)) — .NET エコシステムのオープンソース運営を管理する非営利財団。Miguel de Icaza (当時 Xamarin CTO) が初期理事会に参加
2. **.NET Core プロジェクト公開** — Windows 依存を断ち切った**新しい .NET 実装**の開発を宣言

同年 **2014 年 11 月**、Microsoft は Connect() カンファレンスで **.NET サーバースタック全体をオープンソースに転換**し、Linux・macOS へ拡張すると公式発表します。([Microsoft News — .NET open source and cross-platform (2014.11.12)](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/)、[".NET Core is Open Source" — .NET Blog](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/))

これは Microsoft の歴史的な転換点です。それまで Microsoft は Windows を中心に据えてすべてを設計していました。しかしこの時点でゲームの様相が変わっていました。

- サーバー市場は **Linux が圧倒的**になっていました。
- クラウド (Azure) 戦略上、Linux サポートは選択肢ではなく必須となっていました。
- 開発者たちは Mac を使っていました。

この流れに追いつくためには **.NET を Windows から分離**する必要がありました。.NET Framework のコードベースは Windows API と深く絡み合っており移植が不可能だったため、**一から書き直すことを決定**します。それが .NET Core です。

### Xamarin 買収

**2016 年 2 月 24 日**、Microsoft は **Xamarin を買収**すると公式発表します。([Microsoft Blog — "Microsoft to acquire Xamarin" (2016.02.24)](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/)) この決定の意味は二つありました。

- Mono が **Microsoft の公式資産**となりました。外部のオープンソース実装が本家に取り込まれたのです。
- **2016 年 3 月**、Mono は **MIT ライセンスで再配布**されます。商用 Xamarin ライセンスなしに誰でも自由に使えるようになりました。

Unity 開発者にとってこの出来事は静かな変化でしたが、**.NET エコシステムの境界が再び引き直された時点**でした。14 年間、外部から Linux・macOS の .NET を支え続けてきたプロジェクトが Microsoft の傘下に入りました。

### .NET Core 1.0〜3.1

- **2016 年 6 月 27 日 — .NET Core 1.0** リリース。Windows・Linux・macOS で動作する最初の公式 .NET 実装
- **2017 年 — .NET Core 2.0**。.NET Standard 2.0 サポートにより Framework との API 互換性が大幅に改善
- **2019 年 12 月 — .NET Core 3.1 LTS**。安定版。ここまでが「.NET Core」ブランディングの最後

この時期、**.NET エコシステムには三つの実装が共存**していました。

- **.NET Framework 4.x** — Windows 商用スタック (レガシー維持)
- **.NET Core 3.1** — クロスプラットフォーム新スタック (新規開発推奨)
- **Mono (+ Xamarin)** — モバイル・ゲーム (Xamarin はモバイル、Mono は Unity)

**同じ C# コードを三か所で動かさなければならない状況**になったのです。開発者やライブラリ作者たちは .NET Standard という API 契約で三つの実装を束ねようとしましたが、根本的には三つのランタイム・三つの BCL が存在する状態でした。

### 意味

Part 3 が生み出したものは**三つの実装の乱立**と**統合の予告**でした。Microsoft はこの混乱を .NET 5 で終わらせると発表します。

---

## Part 4. 統合 (2020〜現在)

### .NET 5 — 二つの名前が解かれる

**2020 年 11 月、.NET 5** リリース。([".NET Blog — Announcing .NET 5.0" (2020.11.10)](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/)) ここで二つの決定が下されました。

**① バージョン番号 4 を飛ばす。**
.NET Core 3.1 の次のバージョンがなぜ 4 ではなく 5 だったのでしょうか？理由は **.NET Framework 4.x との混同を避けるため**でした。([Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET))

同じ会社が作った二つの「.NET 4」が存在する状況はおかしいです。一方は Windows 専用のレガシー、もう一方はクロスプラットフォームの未来。バージョン番号の衝突を避けるためにはどちらかが譲らなければならず、Core 側が 4 を飛ばします。

**② 「Core」を名前から外す。**
.NET Core は **.NET** になりました。理由は**アイデンティティの宣言**でした。

> 「.NET Core」は「.NET の縮小版」という印象を与えます。しかし今や .NET Core が機能・パフォーマンス・エコシステムの面で Framework を超えたのだから、これが**正式な .NET** です。

以降は `.NET 5`、`.NET 6`、`.NET 7` という形で呼びます。公式ドキュメントでも **「.NET Core」という言葉は 3.1 以下を指す場合にのみ**使います。

### バージョンの流れ

| 年 | バージョン | 種類 | 主なトピック |
|------|------|------|----------|
| 2020.11 | .NET 5 | STS | 統合の出発 |
| 2021.11 | .NET 6 | **LTS** | Hot Reload、Minimal API |
| 2022.11 | .NET 7 | STS | **NativeAOT 初導入** (コンソールアプリ・ライブラリ) |
| 2023.11 | .NET 8 | **LTS** | NativeAOT 拡大、ASP.NET Core AOT |
| 2024.11 | .NET 9 | STS | パフォーマンス改善 |
| 2025.11 | .NET 10 | **LTS** | 現在の安定版 |

LTS (Long Term Support) は 3 年サポート、STS (Standard Term Support) は 1.5 年サポートです。偶数バージョンが LTS という慣例があります。

### Mono の最終章

**2024 年 8 月 27 日**、Microsoft は **Mono プロジェクトの所有権を WineHQ に移管**すると発表します。WineHQ は Linux で Windows プログラムを動かす Wine の開発チームです。([Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)))

この決定の意味は明確です。Microsoft が注目するランタイムは **CoreCLR (.NET 8+) と NativeAOT** です。Mono はもはや Microsoft の戦略的資産ではありません。

ただし Unity の Mono は**別途維持**されます。Unity Technologies は独自に Mono のフォークを管理してきており、エンジンのビルドパイプラインに深く統合されているため、本家 (WineHQ) とは分離した状態で引き続き発展します。

### 意味

Part 4 が生み出したものは**名前の整理**でした。現時点で「.NET」という言葉の現代的な用法はこのように確定しました。

- **.NET** (バージョン番号なし) = 2020 年以降の統合 .NET 実装 (CoreCLR ベース)
- **.NET Framework** = 2002 年から 2022 年までの Windows 専用レガシー (4.8.1 で凍結)
- **Mono** = モバイル・ゲーム向け実装 (Unity・WineHQ が管理)
- **.NET Core** = 2016〜2019 年の過渡期の名称 (現在は使わない)

---

## .NET 系譜タイムライン

四つの時代を一枚の図で要約します。

<div class="dotnet-lineage-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label=".NET 歴史系譜タイムライン 2001-2025">
  <text x="450" y="28" text-anchor="middle" class="dotnet-lineage-title">.NET 系譜 — 2001年から2025年まで</text>

  <g class="dotnet-lineage-axis">
    <line x1="60" y1="400" x2="860" y2="400" class="dotnet-lineage-axis-line"/>
    <text x="60" y="420" text-anchor="middle" class="dotnet-lineage-year">2001</text>
    <text x="180" y="420" text-anchor="middle" class="dotnet-lineage-year">2005</text>
    <text x="340" y="420" text-anchor="middle" class="dotnet-lineage-year">2011</text>
    <text x="500" y="420" text-anchor="middle" class="dotnet-lineage-year">2016</text>
    <text x="660" y="420" text-anchor="middle" class="dotnet-lineage-year">2020</text>
    <text x="820" y="420" text-anchor="middle" class="dotnet-lineage-year">2025</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="framework">
    <rect x="60" y="70" width="640" height="40" rx="6" class="dotnet-lane-framework"/>
    <text x="70" y="95" class="dotnet-lane-name">.NET Framework (2002〜2022、Windows 専用)</text>
    <text x="700" y="95" text-anchor="end" class="dotnet-lane-tag">4.8.1 で凍結</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="mono">
    <rect x="80" y="130" width="780" height="40" rx="6" class="dotnet-lane-mono"/>
    <text x="90" y="155" class="dotnet-lane-name">Mono (2001〜、クロスプラットフォーム、2016 Microsoft 編入、2024 WineHQ 移管)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="xamarin">
    <rect x="340" y="190" width="280" height="40" rx="6" class="dotnet-lane-xamarin"/>
    <text x="350" y="215" class="dotnet-lane-name">Xamarin (2011〜2024)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="core">
    <rect x="500" y="250" width="180" height="40" rx="6" class="dotnet-lane-core"/>
    <text x="510" y="275" class="dotnet-lane-name">.NET Core (2016〜2019)</text>
  </g>

  <g class="dotnet-lineage-lane" data-lane="dotnet">
    <rect x="680" y="310" width="180" height="40" rx="6" class="dotnet-lane-dotnet"/>
    <text x="690" y="335" class="dotnet-lane-name">.NET (2020〜)</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="500" y1="250" x2="500" y2="350" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="510" y="340" class="dotnet-event-label">統合の流れ</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="680" y1="110" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <line x1="680" y1="290" x2="680" y2="310" class="dotnet-event-line-solid"/>
    <text x="688" y="306" class="dotnet-event-label">.NET 5 統合</text>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="620" y1="230" x2="680" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
  </g>

  <g class="dotnet-lineage-event">
    <line x1="860" y1="170" x2="860" y2="310" class="dotnet-event-line" stroke-dasharray="4 3"/>
    <text x="835" y="302" text-anchor="end" class="dotnet-event-label">Unity Mono は維持</text>
  </g>
</svg>
</div>

<style>
.dotnet-lineage-container { margin: 1.5rem 0; overflow-x: auto; }
.dotnet-lineage-container svg { width: 100%; max-width: 900px; height: auto; display: block; margin: 0 auto; }
.dotnet-lineage-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.dotnet-lineage-axis-line { stroke: #94a3b8; stroke-width: 1.5; }
.dotnet-lineage-year { font-size: 12px; fill: #64748b; }
.dotnet-lane-framework { fill: #dbeafe; stroke: #2563eb; stroke-width: 1.2; }
.dotnet-lane-mono { fill: #fef3c7; stroke: #d97706; stroke-width: 1.2; }
.dotnet-lane-xamarin { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.2; }
.dotnet-lane-core { fill: #d1fae5; stroke: #10b981; stroke-width: 1.2; }
.dotnet-lane-dotnet { fill: #ddd6fe; stroke: #7c3aed; stroke-width: 1.2; }
.dotnet-lane-name { font-size: 13px; font-weight: 600; fill: #1e293b; }
.dotnet-lane-tag { font-size: 11px; fill: #475569; font-style: italic; }
.dotnet-event-line { stroke: #6366f1; stroke-width: 1.5; fill: none; }
.dotnet-event-line-solid { stroke: #6366f1; stroke-width: 1.5; fill: none; }
.dotnet-event-label { font-size: 11px; fill: #475569; font-style: italic; }
[data-mode="dark"] .dotnet-lineage-title { fill: #e5e7eb; }
[data-mode="dark"] .dotnet-lineage-axis-line { stroke: #64748b; }
[data-mode="dark"] .dotnet-lineage-year { fill: #94a3b8; }
[data-mode="dark"] .dotnet-lane-framework { fill: rgba(37,99,235,0.25); stroke: #60a5fa; }
[data-mode="dark"] .dotnet-lane-mono { fill: rgba(217,119,6,0.25); stroke: #fbbf24; }
[data-mode="dark"] .dotnet-lane-xamarin { fill: rgba(236,72,153,0.25); stroke: #f472b6; }
[data-mode="dark"] .dotnet-lane-core { fill: rgba(16,185,129,0.25); stroke: #34d399; }
[data-mode="dark"] .dotnet-lane-dotnet { fill: rgba(124,58,237,0.25); stroke: #a78bfa; }
[data-mode="dark"] .dotnet-lane-name { fill: #f1f5f9; }
[data-mode="dark"] .dotnet-lane-tag { fill: #cbd5e1; }
[data-mode="dark"] .dotnet-event-line { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-event-line-solid { stroke: #a78bfa; }
[data-mode="dark"] .dotnet-event-label { fill: #cbd5e1; }
@media (max-width: 768px) {
  .dotnet-lane-name { font-size: 10px; }
  .dotnet-lane-tag { font-size: 9px; }
  .dotnet-event-label { font-size: 9px; }
  .dotnet-lineage-year { font-size: 10px; }
}
</style>

---

## 序論の三つの疑問に答える

最初に投げかけた三つの疑問に答えることができます。

### Q1. なぜ .NET 4 は飛ばされたのか？

.NET Core 3.1 の次のバージョンが 4 になっていたとしたら、**.NET Framework 4.x と名前が被って**大きな混乱を招いたでしょう。同じ会社が「4」という名前で二つの異なる .NET を同時に持つことはできないため、Core 側が 5 に飛ばしました。

### Q2. なぜ「Core」が名前から消えたのか？

.NET Core が完成度の面で .NET Framework を超えた時点で、Microsoft は**「Core」というサブタイトルがむしろ下位互換の縮小版という印象**を与えると判断しました。2020 年の .NET 5 から Core が消え、それが**「本物の .NET」**となりました。Framework は 4.8.1 で凍結されたレガシーとなりました。

### Q3. Unity はなぜ Mono の上にあるのか？

2005 年に Unity がエンジンをリリースした時点では、**.NET Framework が Windows 専用**でした。Mac・Linux・コンソールをターゲットとするゲームエンジンの観点から、Mono が唯一の実用的な選択肢でした。その決定が 20 年間維持されてきた結果、Unity のエンジンビルドパイプライン、エディター、プラグインエコシステムがすべて Mono の上に積み上がり、変更が難しい基盤となりました。2014 年に登場した Unity の **IL2CPP** は、この制約を部分的に回避する代替手段です (第 3 編で詳しく扱います)。

---

## ゲームプログラマにとってこの歴史が意味すること

歴史を整理した後に残る**実用的な結論四つ**です。

**① Unity の Mono は本家と分離されています。**
2024 年に Microsoft が Mono を WineHQ に移管した以降、**Unity の Mono は Unity が自体管理**します。Mono 本家のアップデートを待つ関係ではありません。

**② `.NET Standard` は統合以前の遺産です。**
.NET Core 時代に Framework・Mono・Core の三つの実装の API を束ねるために作られた契約です。今では .NET 5+ に統合されているため、新規ライブラリでは `.NET Standard` の代わりに**具体的な .NET バージョンのターゲティング**が推奨されます。ただし Unity が使用する API 互換レベルが依然として `.NET Standard 2.1` ベースであるため、この遺産は生き続けています。

**③ 「.NET Framework プロジェクト」を今から始めないでください。**
4.8.1 で凍結されており、新機能はありません。レガシーのメンテナンスでない限り、すべての新規開発は .NET 8+ (または Unity の Mono/IL2CPP) の上で始めます。

**④ 「.NET Core」という言葉を見たときの時代感覚。**
「We use .NET Core 3.1」と書かれていたら、**2019 年以降アップデートがないプロジェクト**である可能性が高いです。技術ブログや Stack Overflow の回答の日付を確認する際も、「Core」という言葉が含まれていれば 2019 年以前の資料として判断します。

---

## まとめ

今回の記事の核心を三行に圧縮します。

1. **.NET Framework (2002) と Mono (2001) が 15 年間平行線をたどりながら発展**し、2014 年の Microsoft の戦略転換により **2020 年の .NET 5 で統合**されました。
2. **「Core」は過渡期の名称**であり、今は単に **.NET** です。バージョンは 5・6・7・8・9・10 と続き、偶数が LTS です。
3. **Unity の Mono は独自に**維持され、Microsoft の関心は **CoreCLR と NativeAOT** へ移っています。

---

## 次回予告

第 3 編では時間軸ではなく**空間軸**で .NET を見ます。現時点で存在する**五つのランタイム実装** — CLR・CoreCLR・Mono・IL2CPP・NativeAOT — を JIT/AOT・メモリ・リフレクション・ジェネリクス・デプロイの観点から比較します。ゲームプログラマにとって最も実用的な記事になるでしょう。

---

## 参考資料

### Microsoft 公式一次資料

- [.NET Blog — "Announcing .NET 5.0"](https://devblogs.microsoft.com/dotnet/announcing-net-5-0/) · 2020 年 11 月 10 日、.NET 5 統合公式発表ポスト
- [Microsoft Blog — "Microsoft to acquire Xamarin"](https://blogs.microsoft.com/blog/2016/02/24/microsoft-to-acquire-xamarin-and-empower-more-developers-to-build-apps-on-any-device/) · 2016 年 2 月 24 日、Xamarin 買収公式発表
- [.NET Blog — ".NET Core is Open Source"](https://devblogs.microsoft.com/dotnet/net-core-is-open-source/) · 2014 年、.NET Core オープンソース宣言
- [Microsoft News — "Microsoft takes .NET open source and cross-platform"](https://news.microsoft.com/source/2014/11/12/microsoft-takes-net-open-source-and-cross-platform-adds-new-development-capabilities-with-visual-studio-2015-net-2015-and-visual-studio-online/) · 2014 年 11 月 12 日、Connect() イベントでのクロスプラットフォーム転換公式ニュースルーム

### 参考資料

- [Microsoft Learn — .NET glossary](https://learn.microsoft.com/en-us/dotnet/standard/glossary) · 公式用語集
- [Microsoft Learn — .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies) · Framework バージョン公式記録
- [Wikipedia — .NET Framework version history](https://en.wikipedia.org/wiki/.NET_Framework_version_history) · バージョン別沿革
- [Wikipedia — Mono (software)](https://en.wikipedia.org/wiki/Mono_(software)) · Mono の歴史
- [Wikipedia — .NET](https://en.wikipedia.org/wiki/.NET) · 統合およびバージョン番号ポリシー
- [Wikipedia — .NET Foundation](https://en.wikipedia.org/wiki/.NET_Foundation) · 2014 年 Build で設立
- [endoflife.date — Microsoft .NET](https://endoflife.date/dotnet) · サポート終了スケジュール
