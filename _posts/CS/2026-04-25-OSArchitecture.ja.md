---
title: "CSロードマップ 第7回 — OSアーキテクチャ入門：Unix、NT、XNUの分かれ道"
lang: ja
date: 2026-04-25 09:00:00 +0900
categories: [AI, CS]
tags: [cs, os, unix, linux, windows, macos, xnu, kernel, architecture]
toc: true
toc_sticky: true
math: true
difficulty: intermediate
prerequisites:
  - /posts/MemoryManagement/
tldr:
  - 3つのOSの違いは「技術選択」ではなく「歴史的な経路依存性」である — 1970〜80年代のUnix、VMS、NeXTSTEPにまつわる決定が今日のLinux、Windows、macOSを形づくった
  - カーネル構造が異なる（Linuxはモノリシック、Windows NTはハイブリッド、macOS XNUはMachマイクロカーネルの上にBSDを重ねた二重構造）
  - macOSはGrand Central Dispatchでスレッド抽象化を、Apple SiliconでP/E異種コアと16KBページを、Rosetta 2でハードウェアTSOモードを導入した
  - 実行バイナリ形式（ELF/PE/Mach-O）がそもそも違うため、ゲームのマルチプラットフォームビルドではクロスコンパイルが複雑になる
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## はじめに：なぜOSから始めるのか

ステージ1ではデータ構造とメモリを扱いました。配列と連結リスト、ハッシュテーブル、木とグラフ、そしてヒープまで — すべて**「データをどう整理するか」**の話でした。

ステージ2の問いは少し違います。

> **「2つのスレッドが同じ変数を使うと、なぜプログラムは時々だけ死ぬのか？」**

この問いに答えるには、プログラムがどう実行され、誰がCPUを分け与え、メモリがどう保護されるかを知る必要があります。それが**オペレーティングシステム（OS）**の役割です。

ところがOSの勉強を始めるとすぐに奇妙な壁に当たります。教科書には「プロセスはPCBを持つ」というような抽象的な説明が書かれています。しかし実際にmacOSで`ps`を打ち、Windowsでタスクマネージャーを開いてみると、3つのOSの世界はまったく違って見えます。

- Linuxではプロセス生成が`fork()`の2文字で終わります
- Windowsでは`CreateProcess()`に12個のパラメータが並びます
- macOSでは同じ`fork()`を使っても、その下にはMachカーネルというまったく別のものがあります

この**3つのOSの違い**は技術的な選択ではなく、**歴史の産物**です。1969年のUnixの誕生、1977年のBerkeleyの分岐、1989年のNeXTSTEPの賭け、1993年のWindows NTの設計 — これらの決定が、今日あなたがUnityゲームをビルドするときに`.exe`が出るか`.app`が出るかを決めています。

ステージ2の最初の回は**本格的な理論に入る前に地図を描く作業**です。各OSがどういう血統から来て、なぜ互いに違う姿になり、ゲーム開発者にとってどんな違いがあるかをざっと見ます。次の回からはプロセス、スレッド、スケジューリングといった具体的なテーマに入っていきますが、そのたびに**「この概念はLinuxではA、WindowsではB」**と比較できるようにするには、まず3つのOSの**骨格**を知る必要があります。

とくにMacユーザーの読者のために、**macOS固有のセクション**を詳しく扱います。XNUカーネルの独特な二重構造、Grand Central Dispatchの設計思想、Apple Siliconのハードウェア上の仕掛けまで — 他のOS本では周辺に追いやられる話題が、ここでは主役です。

---

## Part 1：3つのOSの血統 — 1969年の決定が2026年をつくる

### Unixの誕生 (1969)

![Ken ThompsonとDennis Ritchie (1973)](/assets/img/post/cs/os-thompson-ritchie-1973.jpg){: width="500" }
_Ken Thompson（左）とDennis Ritchie（右）、1973年。UnixとC言語の創始者たち。出典：Jargon File (Public Domain)_

すべての物語は1969年、アメリカ・ニュージャージー州のAT&T Bell Labsで始まります。**Ken Thompson**と**Dennis Ritchie**は、GE-645というメインフレーム上で走るMulticsという巨大なOSプロジェクトで挫折を味わっていました。Multicsは野心的すぎて、遅すぎて、複雑すぎたのです。

Bell Labsの片隅で放置されていたPDP-7というコンピュータをThompsonは見つけ、そこで**Multicsの不要な複雑さを削ぎ落とした単純なOS**を趣味で作り始めました。名前は「Multi-」の代わりに「Uni-」を付けて **UNICS (Uniplexed Information and Computing Service)**。のちに名前が**Unix**に落ち着きます。

Unixの設計原則は後に**「Unix哲学」**と呼ばれるようになります：

1. **1つのことだけをうまくやれ (Do one thing and do it well)**
2. **すべてはファイルである (Everything is a file)**
3. **プログラムを組み合わせよ（パイプ`|`で出力を次の入力に）**
4. **テキストが汎用インターフェースである**

1973年、RitchieはUnixを**C言語**で書き直します。これが決定打でした。それまでOSはアセンブリ言語でしか書けず、他のハードウェアに移植できなかったのですが、Cで書かれたUnixは**移植可能なOSの時代**を開きました。

1970年代後半、UnixのソースコードはAT&Tが低価格のライセンスで大学に配布します。特に**UC Berkeley**が熱心に受け入れ、学生たちはUnixを修正して配布し始めます。ここが分岐点です。

### BSD分岐：Berkeleyの学生たち

1977年からBerkeleyが配布したUnix派生版を**Berkeley Software Distribution (BSD)**と呼びます。BSDは既存のUnixにはなかった多くの機能を追加しました：

- **TCP/IPネットワークスタック**（1983、インターネットの基礎）
- **Berkeley Sockets API**（今でもネットワークプログラミングの標準）
- **仮想メモリの改善**
- **Fast File System (FFS)**

1980年代半ばにはBSDはUnixの事実上の標準の1つになります。しかしAT&Tがライセンス訴訟を起こしBerkeleyは長い法廷闘争に巻き込まれ、その結果**AT&Tコードを完全に排除した自由なBSD**が生まれます。これがFreeBSD、NetBSD、OpenBSDのルーツです。

**重要な点**：BSDは完全にオープンソースで、ライセンスがGPL（Linux）よりはるかに自由です。このため後に**AppleがmacOSの基盤としてBSDを選ぶ**ことになります。GPLならAppleは自社の修正内容をすべて公開しなければならなかったはずですが、BSDライセンスにはその義務がなかったからです。

### NeXTSTEP → macOS：Steve Jobsの帰還

![NeXTcubeコンピュータ (1990)](/assets/img/post/cs/os-next-cube.jpg){: width="600" }
_NeXTcube (1990)、Computer History Museum所蔵。このコンピュータに搭載されたNeXTSTEPが今日のmacOSのルーツだ。写真：Michael Hicks, CC BY 2.0_

1985年、Appleを追い出されたSteve Jobsは**NeXT**という会社を立ち上げます。NeXTの目標は「大学と研究者のための高級ワークステーション」でした。そのコンピュータに搭載するOSが**NeXTSTEP** (1989) です。

NeXTSTEPの設計は独特でした：

- カーネルは**Machマイクロカーネル**（Carnegie Mellon Universityで開発）
- その上に**BSD Unixレイヤ**を重ねてPOSIX互換性を提供
- アプリケーションフレームワークは**Objective-C**で書かれた**Cocoa**（当時の名前はAppKit）

当時この構造は学界で流行していた「マイクロカーネルが未来だ」という思想の実践でした。しかしNeXTコンピュータは商業的に失敗し、会社は生き残るためにハードウェアを諦め、**NeXTSTEPを他のハードウェアに移植**する方向に転換します（1993〜）。

1996年、驚くべきことが起こります。**AppleがNeXTを買収**したのです。当時Appleは Mac OS 9の後継となる次世代OSを作ろうとした「Copland」プロジェクトが失敗し、基盤技術がありませんでした。Appleは外部からOSを買うことにし、BeOSとNeXTSTEPで迷った末にNeXTSTEPを選びます。金額はおよそ**4億ドル**。

Steve JobsはNeXTとともにAppleに戻り、1997年に暫定CEOに復帰します。そして**NeXTSTEPがmacOSの基盤**になりました。

- 1999：**Mac OS X Server 1.0**（NeXTSTEPベース）
- 2001：**Mac OS X 10.0 Cheetah** — 一般ユーザー向け
- 2007：**iPhone OS**（Mac OS Xの縮小版）
- 2016：「Mac OS X」から「**macOS**」に改名

つまり、**今日あなたのMacBookで動いているmacOSのカーネルは、1980年代のNeXTが1990年代のAppleに売ったもので、そのルーツはCarnegie Mellon Universityで行われていたMach研究プロジェクトまで遡ります**。30年以上前の設計がまだ生きているのです。

### Linux：フィンランドの大学生の趣味プロジェクト (1991)

![LinuxCon Europe 2014でのLinus Torvalds](/assets/img/post/cs/os-linus-torvalds.jpg){: width="400" }
_Linus Torvalds、LinuxCon Europe 2014。23年前の趣味プロジェクトが世界のインフラの基盤になったことを振り返っている最中。写真：Krd, CC BY-SA 4.0_

1991年、フィンランドのヘルシンキ大学の**Linus Torvalds**は、学校でOSの講義を受けながらAndrew Tanenbaumが教育用に作った**Minix**を使っていました。Minixは優れた教育用OSでしたが、商用ライセンスで利用が制限されており、Linusは自宅の386 PCでもっと自由に使えるものが必要でした。

それで**趣味で**OSを作り始めます。8月25日、comp.os.minixニュースグループに投げたメッセージが有名です：

> *"Hello everybody out there using minix — I'm doing a (free) operating system (just a hobby, won't be big and professional like gnu)..."*

*「大きくもなく、プロフェッショナルでもないだろう」*と言っていたその趣味プロジェクトが、30年後に世界の大多数のサーバー、スマートフォン、スーパーコンピュータで動いています。

Linuxは最初から**GPLライセンス**を採用し、世界中の開発者が貢献できるモデルを築きました。そしてGNUプロジェクトのユーザーランドツール（gcc、bash、coreutilsなど）と組み合わさって完全なOSになりました — 厳密には**GNU/Linux**と呼びます。

**Linuxの決定的な特徴** — カーネル構造の面で：

- **モノリシックカーネル**：Unixの伝統に従い、カーネルにすべての機能（ファイルシステム、ネットワーク、ドライバ、メモリ管理）を詰め込む
- Tanenbaumが「マイクロカーネルが優れている」と批判し、Linusが反論した1992年の論争はOSの歴史上有名です
- 30年が経った今、Linuxは**部分的にモジュール化されたモノリシックカーネル**に進化しました（カーネルモジュール機能）

### VMS → Windows NT：Dave Cutlerの逆襲

ここまでの話はすべてUnix系です。ところがWindowsはUnixとまったく違う血統です。

1970年代、**Digital Equipment Corporation (DEC)** はミニコンピュータ市場の強者でした。彼らのOSは**VMS (Virtual Memory System)** で、大型サーバ向けの高信頼性OSでした。VMSの主任設計者が**Dave Cutler**です。

1988年、DECで新プロジェクトが中止になると、Dave Cutlerはチームを率いて**Microsoftに移籍**します。Microsoftのビル・ゲイツから「OS/2の次の32ビットOSを作ってほしい」と提案があったからです。

Cutlerは**Windows NT** (NT = New Technology) を設計します。内部的にVMSの多くのアイデアを持ち込みました — VMSの各文字を1つずつ後ろにずらすとWNTになるというジョークがあるほどです（V→W、M→N、S→T）。

Windows NTの主な特徴：

- **ハイブリッドカーネル**：マイクロカーネルのようにサブシステムを分けたが、性能のために多くをカーネル空間に置いた
- **POSIXサブシステム、OS/2サブシステム、Win32サブシステム**が分離 — 理論上、他のOSのAPIを同時に支援できた
- **ユニコード優先**：設計段階からUnicode（UTF-16）を前提
- **マルチアーキテクチャ対応**：x86、MIPS、Alpha、PowerPC（初期は）

1993年にWindows NT 3.1がリリースされ、NT 4.0、Windows 2000、XP、7、10、11まですべて**同じNTカーネル系譜**に属します。つまり、あなたがWindows 11でUnityをビルドするときに走っているカーネルのルーツは**DEC VMS（1977）**に連なります。

一方、Windows 95、98、MEは**まったく別の血統**でした — MS-DOSベースのWindows 1.0〜3.1系譜。Microsoftは2001年のWindows XPでこの2つの系譜をNT側に統合し、DOS系譜を終わらせます。

### 血統ツリー

ここまでの話を可視化すると以下のようになります。

<div class="os-lineage-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three OS lineage tree">
  <defs>
    <marker id="os-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="os-arrow-head" />
    </marker>
  </defs>

  <text x="450" y="28" text-anchor="middle" class="os-title">3つのオペレーティングシステムの血統 — 1969〜2026</text>

  <g class="os-lane os-unix-lane">
    <rect x="20" y="55" width="600" height="340" rx="8" class="os-lane-bg"/>
    <text x="320" y="78" text-anchor="middle" class="os-lane-label">Unix系</text>
  </g>

  <g class="os-lane os-vms-lane">
    <rect x="640" y="55" width="240" height="340" rx="8" class="os-lane-bg"/>
    <text x="760" y="78" text-anchor="middle" class="os-lane-label">VMS系</text>
  </g>

  <g class="os-node os-node-root">
    <rect x="230" y="100" width="180" height="40" rx="6"/>
    <text x="320" y="125" text-anchor="middle">Unix (1969)</text>
  </g>

  <g class="os-node os-node-root">
    <rect x="680" y="100" width="160" height="40" rx="6"/>
    <text x="760" y="125" text-anchor="middle">VMS (1977)</text>
  </g>

  <g class="os-node">
    <rect x="50" y="175" width="160" height="36" rx="6"/>
    <text x="130" y="198" text-anchor="middle">BSD (1977)</text>
  </g>

  <g class="os-node">
    <rect x="230" y="175" width="160" height="36" rx="6"/>
    <text x="310" y="198" text-anchor="middle">Minix (1987)</text>
  </g>

  <g class="os-node">
    <rect x="410" y="175" width="200" height="36" rx="6"/>
    <text x="510" y="198" text-anchor="middle">System V (1983)</text>
  </g>

  <g class="os-node">
    <rect x="50" y="240" width="160" height="36" rx="6"/>
    <text x="130" y="263" text-anchor="middle">NeXTSTEP (1989)</text>
  </g>

  <g class="os-node">
    <rect x="230" y="240" width="160" height="36" rx="6"/>
    <text x="310" y="263" text-anchor="middle">Linux (1991)</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="50" y="315" width="160" height="40" rx="6"/>
    <text x="130" y="340" text-anchor="middle">macOS (2001)</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="230" y="315" width="160" height="40" rx="6"/>
    <text x="310" y="340" text-anchor="middle">Android / Server</text>
  </g>

  <g class="os-node os-node-current">
    <rect x="680" y="315" width="160" height="40" rx="6"/>
    <text x="760" y="340" text-anchor="middle">Windows 11</text>
  </g>

  <g class="os-node">
    <rect x="680" y="175" width="160" height="36" rx="6"/>
    <text x="760" y="198" text-anchor="middle">Windows NT (1993)</text>
  </g>

  <g class="os-node os-node-subtle">
    <rect x="680" y="240" width="160" height="36" rx="6"/>
    <text x="760" y="263" text-anchor="middle">Windows 2000 / XP</text>
  </g>

  <path d="M 280 140 L 150 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 320 140 L 310 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 360 140 L 510 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 130 211 L 130 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 310 211 L 310 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 130 276 L 130 315" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 310 276 L 310 315" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 140 L 760 175" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 211 L 760 240" class="os-edge" marker-end="url(#os-arrow)"/>
  <path d="M 760 276 L 760 315" class="os-edge" marker-end="url(#os-arrow)"/>

  <text x="450" y="430" text-anchor="middle" class="os-caption">macOSはBSD → NeXTSTEP経路で、LinuxはMinixの影響で、Windowsはまったく別のVMS経路で。</text>
  <text x="450" y="455" text-anchor="middle" class="os-caption">Unixは技術ではなく <tspan class="os-emph">思想とAPI</tspan> を残した。VMSはDave Cutlerとともに Microsoft へ移った。</text>
</svg>
</div>

<style>
.os-lineage-container { margin: 2rem 0; text-align: center; }
.os-lineage-container svg { max-width: 100%; height: auto; }
.os-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.os-lane-bg { fill: #f7fafc; stroke: #cbd5e0; stroke-width: 1; }
.os-lane-label { font-size: 13px; fill: #4a5568; font-weight: 600; }
.os-node rect { fill: #edf2f7; stroke: #718096; stroke-width: 1.5; }
.os-node text { font-size: 13px; fill: #1a202c; font-weight: 500; }
.os-node-root rect { fill: #fef5e7; stroke: #d69e2e; stroke-width: 2; }
.os-node-current rect { fill: #d6e6ff; stroke: #3182ce; stroke-width: 2; }
.os-node-subtle rect { fill: #f7fafc; stroke: #a0aec0; stroke-dasharray: 3 3; }
.os-edge { fill: none; stroke: #4a5568; stroke-width: 1.5; }
.os-arrow-head { fill: #4a5568; }
.os-caption { font-size: 12px; fill: #4a5568; }
.os-emph { font-weight: 700; fill: #2b6cb0; }

[data-mode="dark"] .os-title { fill: #e2e8f0; }
[data-mode="dark"] .os-lane-bg { fill: #1a202c; stroke: #4a5568; }
[data-mode="dark"] .os-lane-label { fill: #a0aec0; }
[data-mode="dark"] .os-node rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .os-node text { fill: #e2e8f0; }
[data-mode="dark"] .os-node-root rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .os-node-current rect { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .os-node-subtle rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .os-edge { stroke: #a0aec0; }
[data-mode="dark"] .os-arrow-head { fill: #a0aec0; }
[data-mode="dark"] .os-caption { fill: #a0aec0; }
[data-mode="dark"] .os-emph { fill: #63b3ed; }

@media (max-width: 768px) {
  .os-title { font-size: 14px; }
  .os-node text { font-size: 11px; }
  .os-caption { font-size: 10px; }
}
</style>

---

## Part 2：3つのOSの設計思想

血統が違えば思想も違います。同じ問題 — 「メモリ不足時にどう処理するか」 — に対して3つのOSが違う反応をする理由はここにあります。

### Linux：開放性と性能

Linuxの文化は**「ハック可能性」**に最高の価値を置きます。

- **すべてが公開**：カーネルソース全体がGPLで公開され、誰でも読んで修正できる
- **ファイルシステムを通した制御**：`/proc`、`/sys`ファイルシステムでカーネル状態をファイルのように読み書きできる
  - 例：`cat /proc/meminfo`でメモリ状態確認、`echo 3 > /proc/sys/vm/drop_caches`でキャッシュクリア
- **テキスト優先**：設定ファイルはほぼすべてテキスト。バイナリ設定DB（レジストリ）がない
- **性能優先**：互換性より性能。例えば**ABI互換性は保証するがカーネル内部APIはいつでも変わりうる**
- **多様性の受容**：ディストリ（Ubuntu、Arch、Fedora、Alpine…）ごとに違う思想を許容

**短所**：断片化。「Linux」と一括りにするが、UbuntuとAlpineは別のOSに近いほど違います。またデスクトップUXは相対的に弱い。

### Windows：下位互換性の極致

Microsoftの文化は**「お客が10年前にお金を払ったプログラムが今日も動かなければならない」**です。

- **下位互換性がほぼ神聖不可侵**：Windows 95用プログラムがWindows 11でもほぼ実行できる
  - 有名な逸話：Windowsには特定の有名ゲーム（SimCity）のバグを回避するコードがカーネルに入っています。ゲームが解放済みのメモリを読むバグがあり、Windows 95からWindows NTへ移行した際にそのメモリが即座に回収されるとSimCityがクラッシュしたため、Microsoftは**「SimCityが実行中ならメモリ解放を遅らせるコード」**をWindowsに追加しました（Raymond Chenのブログに記録あり）
- **強力なバイナリAPI**：Win32 APIは30年間事実上そのまま。COM、.NETなどの上位レイヤも下位互換を維持
- **レジストリ**：システム全体の設定DB。テキストファイルではなく構造化されたキー・値ストア
- **GUI優先**：コマンドラインよりGUIが先に設計された。PowerShellは後発
- **エンタープライズ中心**：Active Directory、Group Policyなど大規模組織管理機能が非常に強力

**短所**：下位互換性のためのコードが累積してカーネルが重くなり、セキュリティ面が広がります。30年前のAPIのバグが2025年にも消えない理由です。

### macOS：統制された体験とハードウェア統合

Appleの文化は**「ハードウェアとソフトウェアを一緒に設計する」**です。

- **垂直統合**：AppleはCPU（Apple Silicon）、OS（macOS）、GUI（Aqua）、アプリケーションフレームワーク（Cocoa）、開発ツール（Xcode）をすべて自社で作る
- **単一の公式経路**：Linuxのような多数のディストリもなく、Windowsのような複数のサブシステム共存もない。公式のやり方が1つ
- **急進的な切り替えの受容**：Appleは思い切って旧バージョンを捨てる
  - PowerPC → Intel（2006、Rosetta 1で移行）
  - 32ビット → 64ビット（2019 macOS Catalinaで32ビットアプリサポート完全撤去）
  - Intel → Apple Silicon（2020、Rosetta 2で移行）
- **ユーザー体験優先**：アニメーション、フォントレンダリング、カラー管理などがOSレベルで一貫
- **セキュリティ統制**：Gatekeeper、notarization、SIPなど階層的なセキュリティ体系ですべてのアプリをAppleの検証下に置く

**短所**：自由度が低く、Appleがサポートを打ち切ると手立てがありません（例：7年以上前のMacは最新のmacOSをインストール不可）。またAppleエコシステム外との互換性は副次的。

### 思想比較表

| 基準 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **中核価値** | 開放性、性能 | 互換性、エンタープライズ | 統合、体験 |
| **カーネル修正** | 誰でも可能 | Microsoftのみ | Appleのみ |
| **バイナリ互換性** | カーネルABIのみ保証 | 30年維持 | 大転換時Rosettaで |
| **ユーザーインターフェース** | 選択肢多（GNOME、KDE…） | Windows Shell固定 | Aqua固定 |
| **設定保存** | テキストファイル | レジストリ | plist（XML/バイナリ） |
| **パッケージ管理** | ディストリ別（apt、dnf、pacman） | MSI/EXE/Store | App Store / Homebrew / dmg |
| **主な用途** | サーバ、組み込み、開発者 | 企業、ゲーム、一般消費者 | クリエイティブ、開発者、一般 |
| **ゲーム** | 貧弱（Protonで改善中） | 最高 | 中程度（Metal + Apple Silicon） |

---

## Part 3：カーネル構造 — モノリシック、マイクロ、ハイブリッド

OSの心臓は**カーネル**です。カーネルはハードウェアとアプリの間で資源を管理します。ところがカーネルを**どう構成するか**は1980年代以来OS設計者たちの長年の論争の的でした。

### 3つの構造

**1. モノリシックカーネル (Monolithic Kernel)**

カーネル全体が**1つの大きなプログラム**です。ファイルシステム、ネットワークスタック、ドライバ、メモリ管理などがすべて同じアドレス空間で実行されます。

- **長所**：速い。カーネル内部呼び出しが通常の関数呼び出し
- **短所**：ドライバ1つのバグで全体カーネルがクラッシュ、カーネルが巨大化
- **代表**：Linux、伝統的なUnix、FreeBSD

**2. マイクロカーネル (Microkernel)**

カーネルは最小限の機能だけを持ちます — プロセス、メモリ、IPC（プロセス間通信）。ファイルシステム、ドライバなどは**ユーザー空間のサーバープロセス**に分離されます。

- **長所**：モジュール化、安定性、セキュリティ
- **短所**：IPCコストで遅い（メッセージ伝達がカーネルをもう一度経由）
- **代表**：純粋Mach、MINIX 3、QNX、L4、seL4

**3. ハイブリッドカーネル (Hybrid Kernel)**

マイクロカーネルのモジュール化を追求するが、性能のために多くを**カーネル空間**に置きます。

- **長所**：2つの構造の妥協
- **短所**：「本物のマイクロカーネルではない」という批判
- **代表**：Windows NT、macOS (XNU)

### Linux — モノリシックの頂点

Linuxカーネルは巨大です。2024年基準でソースコード**3000万行以上**。しかし内部的にはモジュール化されていてドライバやファイルシステムを**カーネルモジュール**としてロード/アンロードできます。

```bash
# Linuxで現在ロードされているモジュールを見る
lsmod

# モジュールロード
sudo modprobe nvidia

# モジュールアンロード
sudo rmmod nvidia
```

これらのモジュールは**同じカーネルアドレス空間**で実行されます。つまり、悪意あるモジュールやバグのあるドライバは全体システムを倒せます。そのためLinuxカーネルモジュールには署名検証、SecureBootといったセキュリティ層が追加されます。

### Windows NT — ハイブリッドの実例

Windows NTは**Executive**と呼ばれるカーネル上位層と**Microkernel**と呼ばれる下位層に分かれます。ただ「Microkernel」という名前とは裏腹に、実際にはドライバ、ファイルシステム、ネットワークスタックがすべてカーネル空間で実行されます。

Windows NTの階層：

<div class="nt-container">
<svg viewBox="0 0 860 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Windows NT 階層構造">
  <text x="430" y="24" text-anchor="middle" class="nt-title">Windows NT 階層構造</text>

  <rect x="40" y="44" width="780" height="70" rx="4" class="nt-user"/>
  <text x="60" y="68" class="nt-layer">User Mode</text>
  <text x="60" y="92" class="nt-sub">Win32 アプリ · POSIX サブシステム · .NET</text>

  <rect x="40" y="130" width="780" height="216" rx="4" class="nt-kernel"/>
  <text x="60" y="154" class="nt-layer">Kernel Mode</text>

  <rect x="60" y="166" width="740" height="92" rx="3" class="nt-inner"/>
  <text x="76" y="184" class="nt-component">Executive</text>
  <text x="76" y="204" class="nt-item">· Object Manager · Process Manager</text>
  <text x="76" y="222" class="nt-item">· Memory Manager · I/O Manager</text>
  <text x="76" y="240" class="nt-item">· Security Reference Monitor</text>

  <rect x="60" y="268" width="740" height="42" rx="3" class="nt-inner"/>
  <text x="76" y="286" class="nt-component">Microkernel</text>
  <text x="76" y="303" class="nt-item">· Thread Scheduler · Interrupt Handler</text>

  <rect x="60" y="318" width="740" height="28" rx="3" class="nt-hal"/>
  <text x="76" y="337" class="nt-component">HAL (Hardware Abstraction Layer)</text>

  <rect x="40" y="362" width="780" height="58" rx="4" class="nt-hw"/>
  <text x="60" y="386" class="nt-layer">Hardware</text>
  <text x="60" y="406" class="nt-sub">CPU · メモリ · ディスク · ネットワークカード</text>
</svg>
</div>

<style>
.nt-container { margin: 2rem 0; text-align: center; }
.nt-container svg { max-width: 100%; height: auto; }
.nt-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.nt-user { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.nt-kernel { fill: #e9d8fd; stroke: #805ad5; stroke-width: 1.5; }
.nt-inner { fill: #faf5ff; stroke: #805ad5; stroke-width: 1; stroke-dasharray: 3 2; }
.nt-hal { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1; stroke-dasharray: 3 2; }
.nt-hw { fill: #edf2f7; stroke: #4a5568; stroke-width: 1.5; }
.nt-layer { font-size: 14px; font-weight: 700; fill: #1a202c; }
.nt-sub { font-size: 12px; fill: #4a5568; }
.nt-component { font-size: 13px; font-weight: 600; fill: #1a202c; }
.nt-item { font-size: 11px; fill: #2d3748; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

[data-mode="dark"] .nt-title { fill: #e2e8f0; }
[data-mode="dark"] .nt-user { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .nt-kernel { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .nt-inner { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .nt-hal { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .nt-hw { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .nt-layer { fill: #e2e8f0; }
[data-mode="dark"] .nt-sub { fill: #cbd5e0; }
[data-mode="dark"] .nt-component { fill: #e2e8f0; }
[data-mode="dark"] .nt-item { fill: #cbd5e0; }

@media (max-width: 768px) {
  .nt-title { font-size: 13px; }
  .nt-layer { font-size: 12px; }
  .nt-sub { font-size: 10px; }
  .nt-component { font-size: 11px; }
  .nt-item { font-size: 9.5px; }
}
</style>

**特殊な点**：Windows NTは初期に**POSIXサブシステム**と**OS/2サブシステム**を持っていました。理論的にはPOSIXプログラムがWindowsで修正なしに動けました。しかし実用性が低くPOSIXサブシステムはWindows 8で除去され、代わりに**WSL (Windows Subsystem for Linux)**がまったく別の方式（Linuxカーネル自体をVMで走らせる）で実装されました。

### XNU — Mach + BSD の二重構造

macOSのカーネルは**XNU**と呼ばれます（"X is Not Unix"）。XNUは2つのレイヤで構成されます：

1. **Mach 3.0 マイクロカーネル**（下位）：Carnegie Mellon研究由来。タスク、スレッド、メッセージ伝達（Machポート）、仮想メモリを担当
2. **BSDレイヤ**（上位）：FreeBSDから移植されたUnix実装。プロセスモデル（POSIX）、ネットワークスタック、ファイルシステム（HFS+/APFS）
3. **I/O Kit**：ドライバフレームワーク（C++で書かれている）

**なぜこんな奇妙な構造なのか？**

元々NeXTSTEPは「純粋マイクロカーネル = Mach」の上に「サーバープロセスとしてのBSD」を重ねる構造を試みました。しかしこの方式は**とても遅かった**のです。ファイルを読むことすらユーザー空間のBSDサーバーとMachカーネルの間のIPCを何度も経由する必要があったからです。

そこで妥協しました：**BSDコードをMachと同じカーネル空間に移植**。「マイクロカーネル」という建築哲学は破れましたが、性能が確保されました。これが今のXNU — **理論上はマイクロカーネルだが実際にはハイブリッド**。

<div class="os-kernel-container">
<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three kernel architectures">
  <text x="450" y="28" text-anchor="middle" class="ok-title">3つのカーネル構造の比較</text>

  <g class="ok-box">
    <rect x="30" y="60" width="270" height="320" rx="8"/>
    <text x="165" y="82" text-anchor="middle" class="ok-heading">Linux モノリシック</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="50" y="100" width="230" height="50" rx="4"/>
    <text x="165" y="130" text-anchor="middle">ユーザー空間</text>
  </g>
  <g class="ok-layer ok-layer-kernel">
    <rect x="50" y="160" width="230" height="180" rx="4"/>
    <text x="165" y="185" text-anchor="middle">カーネル空間（1つの巨大なプログラム）</text>
    <text x="165" y="215" text-anchor="middle" class="ok-sublabel">ファイルシステム</text>
    <text x="165" y="235" text-anchor="middle" class="ok-sublabel">ネットワークスタック</text>
    <text x="165" y="255" text-anchor="middle" class="ok-sublabel">ドライバ</text>
    <text x="165" y="275" text-anchor="middle" class="ok-sublabel">メモリ管理</text>
    <text x="165" y="295" text-anchor="middle" class="ok-sublabel">スケジューラ</text>
    <text x="165" y="315" text-anchor="middle" class="ok-sublabel">IPC</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="50" y="350" width="230" height="20" rx="4"/>
    <text x="165" y="365" text-anchor="middle">ハードウェア</text>
  </g>

  <g class="ok-box">
    <rect x="315" y="60" width="270" height="320" rx="8"/>
    <text x="450" y="82" text-anchor="middle" class="ok-heading">Windows NT ハイブリッド</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="335" y="100" width="230" height="50" rx="4"/>
    <text x="450" y="130" text-anchor="middle">ユーザー空間 (Win32, .NET)</text>
  </g>
  <g class="ok-layer ok-layer-kernel">
    <rect x="335" y="160" width="230" height="80" rx="4"/>
    <text x="450" y="180" text-anchor="middle">Executive</text>
    <text x="450" y="200" text-anchor="middle" class="ok-sublabel">Object / Memory / I/O Manager</text>
    <text x="450" y="220" text-anchor="middle" class="ok-sublabel">Security Reference Monitor</text>
  </g>
  <g class="ok-layer ok-layer-micro">
    <rect x="335" y="250" width="230" height="60" rx="4"/>
    <text x="450" y="275" text-anchor="middle">Microkernel Layer</text>
    <text x="450" y="295" text-anchor="middle" class="ok-sublabel">スケジューラ、割り込み</text>
  </g>
  <g class="ok-layer ok-layer-hal">
    <rect x="335" y="320" width="230" height="30" rx="4"/>
    <text x="450" y="340" text-anchor="middle">HAL</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="335" y="355" width="230" height="20" rx="4"/>
    <text x="450" y="370" text-anchor="middle">ハードウェア</text>
  </g>

  <g class="ok-box">
    <rect x="600" y="60" width="270" height="320" rx="8"/>
    <text x="735" y="82" text-anchor="middle" class="ok-heading">macOS XNU (Mach+BSD)</text>
  </g>
  <g class="ok-layer ok-layer-user">
    <rect x="620" y="100" width="230" height="50" rx="4"/>
    <text x="735" y="130" text-anchor="middle">ユーザー空間 (Cocoa, UIKit)</text>
  </g>
  <g class="ok-layer ok-layer-bsd">
    <rect x="620" y="160" width="230" height="70" rx="4"/>
    <text x="735" y="185" text-anchor="middle">BSD Layer</text>
    <text x="735" y="205" text-anchor="middle" class="ok-sublabel">POSIX、ネットワーク、ファイルシステム</text>
    <text x="735" y="220" text-anchor="middle" class="ok-sublabel">プロセスモデル</text>
  </g>
  <g class="ok-layer ok-layer-mach">
    <rect x="620" y="240" width="230" height="70" rx="4"/>
    <text x="735" y="265" text-anchor="middle">Mach Microkernel</text>
    <text x="735" y="285" text-anchor="middle" class="ok-sublabel">Task, Thread, Mach Port</text>
    <text x="735" y="300" text-anchor="middle" class="ok-sublabel">VM、スケジューラ</text>
  </g>
  <g class="ok-layer ok-layer-iokit">
    <rect x="620" y="320" width="230" height="30" rx="4"/>
    <text x="735" y="340" text-anchor="middle">I/O Kit（ドライバ C++）</text>
  </g>
  <g class="ok-layer ok-layer-hw">
    <rect x="620" y="355" width="230" height="20" rx="4"/>
    <text x="735" y="370" text-anchor="middle">ハードウェア</text>
  </g>

  <text x="450" y="405" text-anchor="middle" class="ok-caption">3つの構造すべてでユーザー/カーネル境界は同じだが、カーネル内部の分割方式が違う。</text>
</svg>
</div>

<style>
.os-kernel-container { margin: 2rem 0; text-align: center; }
.os-kernel-container svg { max-width: 100%; height: auto; }
.ok-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.ok-box rect { fill: none; stroke: #cbd5e0; stroke-width: 1.5; stroke-dasharray: 4 4; }
.ok-heading { font-size: 14px; font-weight: 600; fill: #2d3748; }
.ok-layer rect { stroke-width: 1.5; }
.ok-layer text { font-size: 12px; fill: #1a202c; font-weight: 500; }
.ok-sublabel { font-size: 10.5px !important; fill: #4a5568 !important; font-weight: 400 !important; }
.ok-layer-user rect { fill: #e6fffa; stroke: #319795; }
.ok-layer-kernel rect { fill: #fef5e7; stroke: #d69e2e; }
.ok-layer-bsd rect { fill: #e6fffa; stroke: #38b2ac; }
.ok-layer-mach rect { fill: #fed7d7; stroke: #e53e3e; }
.ok-layer-micro rect { fill: #fed7d7; stroke: #e53e3e; }
.ok-layer-iokit rect { fill: #fefcbf; stroke: #d69e2e; }
.ok-layer-hal rect { fill: #f7fafc; stroke: #a0aec0; }
.ok-layer-hw rect { fill: #edf2f7; stroke: #718096; }
.ok-caption { font-size: 12px; fill: #4a5568; }

[data-mode="dark"] .ok-title { fill: #e2e8f0; }
[data-mode="dark"] .ok-box rect { stroke: #4a5568; }
[data-mode="dark"] .ok-heading { fill: #cbd5e0; }
[data-mode="dark"] .ok-layer text { fill: #e2e8f0; }
[data-mode="dark"] .ok-sublabel { fill: #a0aec0 !important; }
[data-mode="dark"] .ok-layer-user rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .ok-layer-kernel rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .ok-layer-bsd rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .ok-layer-mach rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .ok-layer-micro rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .ok-layer-iokit rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .ok-layer-hal rect { fill: #2d3748; stroke: #718096; }
[data-mode="dark"] .ok-layer-hw rect { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .ok-caption { fill: #a0aec0; }

@media (max-width: 768px) {
  .ok-title { font-size: 14px; }
  .ok-heading { font-size: 12px; }
  .ok-layer text { font-size: 10px; }
  .ok-sublabel { font-size: 9px !important; }
}
</style>

> ### ちょっと、これは押さえておこう
>
> **「マイクロカーネルが理論的に良いのなら、なぜ誰も純粋なマイクロカーネルを使わないのか？」**
>
> 答えは**IPCコスト**です。マイクロカーネルでファイルを読むには次のような手順になります：
>
> 1. アプリが「ファイルを読んで」というメッセージをカーネルに送る
> 2. カーネルがそのメッセージをファイルシステムサーバープロセスに転送
> 3. ファイルシステムサーバーがディスクドライバサーバーにメッセージを送る
> 4. ディスクドライバが実際にディスクを読み、結果をファイルシステムサーバーに返す
> 5. ファイルシステムサーバーがアプリに結果を返す
>
> 各ステップごとに**コンテキストスイッチ + メッセージコピー**が発生します。1980〜90年代のハードウェアではこのコストが耐え難いほどでした。
>
> モノリシックカーネルでは同じ作業が**関数呼び出し1回**で終わります。
>
> だからほとんどの実用OSは**「マイクロカーネル設計思想は受け入れつつ、性能のために妥協」**するハイブリッドに収束しました。純粋なマイクロカーネルはリアルタイムシステム（QNX）、セキュリティ重要システム（seL4 — 数学的に検証されたカーネル）のように**特殊分野**でしか生き残っていません。

---

## Part 4：実行バイナリ形式 — 同じCコード、違う成果物

あなたがC++で書かれたUnityゲームをビルドすると、3つのOSで違うバイナリが出ます：

- Linux：**ELF (Executable and Linkable Format)**
- Windows：**PE / PE32+ (Portable Executable)**
- macOS：**Mach-O**

これらの形式は**まったく違います**。単に拡張子の違いではなく、ファイル内部構造が違うため、あるOSのバイナリを他のOSで実行することはできません（エミュレータを使わない限り）。

### ELF — Linuxの標準 (1988〜)

<div class="oe-elf-container">
<svg viewBox="0 0 900 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELF file layout">
  <text x="450" y="28" text-anchor="middle" class="oe-title">ELFファイルレイアウト — Linking View vs Execution View</text>

  <text x="180" y="60" text-anchor="middle" class="oe-heading">Linking View（セクション）</text>
  <text x="180" y="78" text-anchor="middle" class="oe-sub">リンカ / コンパイラが使用</text>

  <text x="720" y="60" text-anchor="middle" class="oe-heading">Execution View（セグメント）</text>
  <text x="720" y="78" text-anchor="middle" class="oe-sub">ランタイムにローダが使用</text>

  <g class="oe-left">
    <rect x="60" y="95" width="240" height="30" rx="3" class="oe-sect oe-sect-header"/>
    <text x="180" y="115" text-anchor="middle" class="oe-sect-label">ELF Header</text>
    <rect x="60" y="130" width="240" height="30" rx="3" class="oe-sect oe-sect-prog"/>
    <text x="180" y="150" text-anchor="middle" class="oe-sect-label">Program Header Table</text>
    <rect x="60" y="170" width="240" height="30" rx="3" class="oe-sect oe-sect-text"/>
    <text x="180" y="190" text-anchor="middle" class="oe-sect-label">.text（実行コード）</text>
    <rect x="60" y="205" width="240" height="30" rx="3" class="oe-sect oe-sect-ro"/>
    <text x="180" y="225" text-anchor="middle" class="oe-sect-label">.rodata（定数 / 文字列）</text>
    <rect x="60" y="245" width="240" height="30" rx="3" class="oe-sect oe-sect-data"/>
    <text x="180" y="265" text-anchor="middle" class="oe-sect-label">.data（初期化グローバル）</text>
    <rect x="60" y="280" width="240" height="30" rx="3" class="oe-sect oe-sect-bss"/>
    <text x="180" y="300" text-anchor="middle" class="oe-sect-label">.bss（0初期化、サイズのみ）</text>
    <rect x="60" y="320" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="337" text-anchor="middle" class="oe-sect-label-sm">.symtab（シンボルテーブル）</text>
    <rect x="60" y="350" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="367" text-anchor="middle" class="oe-sect-label-sm">.strtab（文字列テーブル）</text>
    <rect x="60" y="380" width="240" height="26" rx="3" class="oe-sect oe-sect-meta"/>
    <text x="180" y="397" text-anchor="middle" class="oe-sect-label-sm">.debug_* (DWARF)</text>
    <rect x="60" y="410" width="240" height="30" rx="3" class="oe-sect oe-sect-shdr"/>
    <text x="180" y="430" text-anchor="middle" class="oe-sect-label">Section Header Table</text>
  </g>

  <g class="oe-right">
    <rect x="600" y="95" width="240" height="30" rx="3" class="oe-seg oe-seg-header"/>
    <text x="720" y="115" text-anchor="middle" class="oe-seg-label">ELF Header</text>
    <rect x="600" y="130" width="240" height="30" rx="3" class="oe-seg oe-seg-prog"/>
    <text x="720" y="150" text-anchor="middle" class="oe-seg-label">Program Header Table</text>
    <rect x="600" y="170" width="240" height="65" rx="3" class="oe-seg oe-seg-loadrx"/>
    <text x="720" y="195" text-anchor="middle" class="oe-seg-label">LOAD Segment #1</text>
    <text x="720" y="212" text-anchor="middle" class="oe-seg-sub">Read + Execute</text>
    <text x="720" y="228" text-anchor="middle" class="oe-seg-sub">.text + .rodata</text>
    <rect x="600" y="245" width="240" height="65" rx="3" class="oe-seg oe-seg-loadrw"/>
    <text x="720" y="270" text-anchor="middle" class="oe-seg-label">LOAD Segment #2</text>
    <text x="720" y="287" text-anchor="middle" class="oe-seg-sub">Read + Write</text>
    <text x="720" y="303" text-anchor="middle" class="oe-seg-sub">.data + .bss</text>
    <rect x="600" y="320" width="240" height="85" rx="3" class="oe-seg oe-seg-ignored"/>
    <text x="720" y="345" text-anchor="middle" class="oe-seg-label">（ロードされない）</text>
    <text x="720" y="362" text-anchor="middle" class="oe-seg-sub">シンボルテーブル、デバッグ情報</text>
    <text x="720" y="378" text-anchor="middle" class="oe-seg-sub">プロダクションビルドではstrip</text>
    <text x="720" y="395" text-anchor="middle" class="oe-seg-sub">またはデバッグ用に保持</text>
    <rect x="600" y="410" width="240" height="30" rx="3" class="oe-seg oe-seg-meta"/>
    <text x="720" y="430" text-anchor="middle" class="oe-seg-label-sm">Section Header Table（ランタイムでは任意）</text>
  </g>

  <g class="oe-conn">
    <line x1="300" y1="185" x2="600" y2="195" class="oe-line oe-line-rx"/>
    <line x1="300" y1="220" x2="600" y2="210" class="oe-line oe-line-rx"/>
    <line x1="300" y1="260" x2="600" y2="270" class="oe-line oe-line-rw"/>
    <line x1="300" y1="295" x2="600" y2="285" class="oe-line oe-line-rw"/>
    <line x1="300" y1="333" x2="600" y2="360" class="oe-line oe-line-ignored"/>
    <line x1="300" y1="363" x2="600" y2="372" class="oe-line oe-line-ignored"/>
    <line x1="300" y1="393" x2="600" y2="384" class="oe-line oe-line-ignored"/>
  </g>

  <text x="450" y="480" text-anchor="middle" class="oe-note">同じファイルでもリンカはセクション単位、ローダはセグメント（権限）単位で見る。</text>
  <text x="450" y="500" text-anchor="middle" class="oe-note">プロダクションバイナリはSection Header Tableを省略し、.symtab / .debug_*をstripしてサイズを縮められる。</text>
</svg>
</div>

<style>
.oe-elf-container { margin: 2rem 0; text-align: center; }
.oe-elf-container svg { max-width: 100%; height: auto; }
.oe-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.oe-heading { font-size: 13px; font-weight: 700; fill: #2d3748; }
.oe-sub { font-size: 11px; fill: #4a5568; font-style: italic; }
.oe-sect, .oe-seg { stroke-width: 1.5; }
.oe-sect-header, .oe-seg-header { fill: #e9d8fd; stroke: #805ad5; }
.oe-sect-prog, .oe-seg-prog { fill: #bee3f8; stroke: #3182ce; }
.oe-sect-text { fill: #faf5ff; stroke: #553c9a; }
.oe-sect-ro { fill: #e9d8fd; stroke: #805ad5; }
.oe-sect-data { fill: #c6f6d5; stroke: #38a169; }
.oe-sect-bss { fill: #c6f6d5; stroke: #38a169; stroke-dasharray: 4 3; }
.oe-sect-meta, .oe-seg-meta { fill: #edf2f7; stroke: #718096; }
.oe-sect-shdr { fill: #fed7d7; stroke: #e53e3e; }
.oe-seg-loadrx { fill: #bee3f8; stroke: #3182ce; }
.oe-seg-loadrw { fill: #c6f6d5; stroke: #38a169; }
.oe-seg-ignored { fill: #f7fafc; stroke: #a0aec0; stroke-dasharray: 4 4; }
.oe-sect-label, .oe-seg-label { font-size: 11px; font-weight: 600; fill: #1a202c; }
.oe-sect-label-sm, .oe-seg-label-sm { font-size: 10px; fill: #2d3748; }
.oe-seg-sub { font-size: 10px; fill: #4a5568; }
.oe-line { stroke-width: 1.2; fill: none; }
.oe-line-rx { stroke: #3182ce; opacity: 0.6; }
.oe-line-rw { stroke: #38a169; opacity: 0.6; }
.oe-line-ignored { stroke: #a0aec0; opacity: 0.5; stroke-dasharray: 3 2; }
.oe-note { font-size: 11px; fill: #4a5568; font-style: italic; }

[data-mode="dark"] .oe-title { fill: #e2e8f0; }
[data-mode="dark"] .oe-heading { fill: #cbd5e0; }
[data-mode="dark"] .oe-sub { fill: #a0aec0; }
[data-mode="dark"] .oe-sect-header, [data-mode="dark"] .oe-seg-header { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-prog, [data-mode="dark"] .oe-seg-prog { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .oe-sect-text { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-ro { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .oe-sect-data { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .oe-sect-bss { fill: #22543d; stroke: #68d391; stroke-dasharray: 4 3; }
[data-mode="dark"] .oe-sect-meta, [data-mode="dark"] .oe-seg-meta { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .oe-sect-shdr { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .oe-seg-loadrx { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .oe-seg-loadrw { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .oe-seg-ignored { fill: #1a202c; stroke: #718096; stroke-dasharray: 4 4; }
[data-mode="dark"] .oe-sect-label, [data-mode="dark"] .oe-seg-label { fill: #e2e8f0; }
[data-mode="dark"] .oe-sect-label-sm, [data-mode="dark"] .oe-seg-label-sm { fill: #cbd5e0; }
[data-mode="dark"] .oe-seg-sub { fill: #cbd5e0; }
[data-mode="dark"] .oe-line-rx { stroke: #63b3ed; }
[data-mode="dark"] .oe-line-rw { stroke: #68d391; }
[data-mode="dark"] .oe-line-ignored { stroke: #a0aec0; }
[data-mode="dark"] .oe-note { fill: #a0aec0; }

@media (max-width: 768px) {
  .oe-title { font-size: 13px; }
  .oe-heading { font-size: 11px; }
  .oe-sub { font-size: 9.5px; }
  .oe-sect-label, .oe-seg-label { font-size: 9.5px; }
  .oe-sect-label-sm, .oe-seg-label-sm { font-size: 8.5px; }
  .oe-seg-sub { font-size: 8.5px; }
  .oe-note { font-size: 9.5px; }
}
</style>

**Executable and Linkable Format**はSystem Vで導入された形式で、今ではほとんどのUnix系（Linux、FreeBSD、Solaris）が使います。

ELFファイルの構造：

<div class="bf-container">
<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ELFファイル構造">
  <text x="450" y="30" text-anchor="middle" class="bf-title">ELFファイル構造 (Linux)</text>

  <rect x="160" y="56" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="77" text-anchor="middle" class="bf-label">ELF Header</text>
  <text x="480" y="77" class="bf-note">マジックナンバー 0x7f 'E' 'L' 'F'</text>

  <rect x="160" y="102" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="123" text-anchor="middle" class="bf-label">Program Header Table</text>
  <text x="480" y="123" class="bf-note">実行時のメモリマッピング情報</text>

  <rect x="160" y="148" width="300" height="258" rx="3" class="bf-group"/>
  <text x="170" y="166" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="176" width="276" height="28" rx="2" class="bf-text"/>
  <text x="310" y="194" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="194" class="bf-note">実行コード</text>

  <rect x="172" y="208" width="276" height="28" rx="2" class="bf-ro"/>
  <text x="310" y="226" text-anchor="middle" class="bf-sect">.rodata</text>
  <text x="480" y="226" class="bf-note">読み取り専用データ（文字列リテラルなど）</text>

  <rect x="172" y="240" width="276" height="28" rx="2" class="bf-data"/>
  <text x="310" y="258" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="258" class="bf-note">初期化済みグローバル変数</text>

  <rect x="172" y="272" width="276" height="28" rx="2" class="bf-bss"/>
  <text x="310" y="290" text-anchor="middle" class="bf-sect">.bss</text>
  <text x="480" y="290" class="bf-note">0初期化グローバル変数（ファイルにはサイズのみ）</text>

  <rect x="172" y="304" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="322" text-anchor="middle" class="bf-sect">.symtab</text>
  <text x="480" y="322" class="bf-note">シンボルテーブル</text>

  <rect x="172" y="336" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="354" text-anchor="middle" class="bf-sect">.strtab</text>
  <text x="480" y="354" class="bf-note">文字列テーブル</text>

  <rect x="172" y="368" width="276" height="28" rx="2" class="bf-aux"/>
  <text x="310" y="386" text-anchor="middle" class="bf-sect">.debug_*</text>
  <text x="480" y="386" class="bf-note">DWARFデバッグ情報</text>

  <rect x="160" y="420" width="300" height="34" rx="3" class="bf-meta"/>
  <text x="310" y="441" text-anchor="middle" class="bf-label">Section Header Table</text>
  <text x="480" y="441" class="bf-note">セクション位置 / 属性情報</text>
</svg>
</div>

<style>
.bf-container { margin: 2rem 0; text-align: center; }
.bf-container svg { max-width: 100%; height: auto; }
.bf-title { font-size: 15px; font-weight: 700; fill: #1a202c; }
.bf-meta { fill: #e9d8fd; stroke: #805ad5; stroke-width: 1.5; }
.bf-group { fill: none; stroke: #805ad5; stroke-width: 1; stroke-dasharray: 4 3; }
.bf-group-label { font-size: 11px; font-weight: 700; fill: #805ad5; letter-spacing: 0.5px; }
.bf-text { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.2; }
.bf-ro { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.2; }
.bf-data { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.2; }
.bf-bss { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.2; stroke-dasharray: 4 3; }
.bf-aux { fill: #edf2f7; stroke: #718096; stroke-width: 1; }
.bf-rsrc { fill: #fefcbf; stroke: #d69e2e; stroke-width: 1.2; }
.bf-reloc { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1.2; stroke-dasharray: 4 3; }
.bf-dos { fill: #fbd38d; stroke: #c05621; stroke-width: 1.5; }
.bf-stub { fill: #feebc8; stroke: #c05621; stroke-width: 1; stroke-dasharray: 3 2; }
.bf-load { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.2; }
.bf-seg { fill: none; stroke: #3182ce; stroke-width: 1; stroke-dasharray: 4 3; }
.bf-linkedit { fill: #e6fffa; stroke: #319795; stroke-width: 1.2; }
.bf-arch-x86 { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.bf-arch-arm { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.bf-label { font-size: 12px; font-weight: 600; fill: #1a202c; }
.bf-sect { font-size: 11.5px; fill: #1a202c; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.bf-sub { font-size: 10.5px; fill: #4a5568; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.bf-note { font-size: 11px; fill: #4a5568; }

[data-mode="dark"] .bf-title { fill: #e2e8f0; }
[data-mode="dark"] .bf-meta { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .bf-group { stroke: #b794f4; }
[data-mode="dark"] .bf-group-label { fill: #b794f4; }
[data-mode="dark"] .bf-text { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-ro { fill: #44337a; stroke: #b794f4; }
[data-mode="dark"] .bf-data { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .bf-bss { fill: #22543d; stroke: #68d391; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-aux { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .bf-rsrc { fill: #5c4a10; stroke: #ecc94b; }
[data-mode="dark"] .bf-reloc { fill: #742a2a; stroke: #fc8181; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-dos { fill: #5c2f0c; stroke: #dd6b20; }
[data-mode="dark"] .bf-stub { fill: #5c2f0c; stroke: #dd6b20; stroke-dasharray: 3 2; }
[data-mode="dark"] .bf-load { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-seg { stroke: #63b3ed; stroke-dasharray: 4 3; }
[data-mode="dark"] .bf-linkedit { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .bf-arch-x86 { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .bf-arch-arm { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .bf-label { fill: #e2e8f0; }
[data-mode="dark"] .bf-sect { fill: #e2e8f0; }
[data-mode="dark"] .bf-sub { fill: #cbd5e0; }
[data-mode="dark"] .bf-note { fill: #cbd5e0; }

@media (max-width: 768px) {
  .bf-title { font-size: 12px; }
  .bf-label { font-size: 10px; }
  .bf-sect { font-size: 9.5px; }
  .bf-sub { font-size: 9px; }
  .bf-note { font-size: 9px; }
  .bf-group-label { font-size: 9.5px; }
}
</style>

ELF確認：

```bash
$ file /bin/ls
/bin/ls: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), ...

$ readelf -h /bin/ls
ELF Header:
  Magic:   7f 45 4c 46 02 01 01 00 00 00 00 00 00 00 00 00
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           Advanced Micro Devices X86-64
```

### PE — Windowsの系譜 (1993〜)

**Portable Executable**はWindows NTで導入された形式です。UnixのCOFF（Common Object File Format）から派生しましたが、Microsoft固有の拡張が多くあります。

PEファイルの構造：

<div class="bf-container">
<svg viewBox="0 0 900 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PEファイル構造">
  <text x="450" y="30" text-anchor="middle" class="bf-title">PEファイル構造 (Windows)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-dos"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">DOS Header (MZ)</text>
  <text x="480" y="75" class="bf-note">16ビット時代の互換性遺産</text>

  <rect x="160" y="90" width="300" height="30" rx="3" class="bf-stub"/>
  <text x="310" y="109" text-anchor="middle" class="bf-label">DOS Stub</text>
  <text x="480" y="109" class="bf-note">"This program cannot be run in DOS mode"</text>

  <rect x="160" y="124" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="143" text-anchor="middle" class="bf-label">PE Signature "PE\0\0"</text>

  <rect x="160" y="158" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="177" text-anchor="middle" class="bf-label">COFF Header</text>
  <text x="480" y="177" class="bf-note">CPUアーキテクチャ · セクション数</text>

  <rect x="160" y="192" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="211" text-anchor="middle" class="bf-label">Optional Header</text>
  <text x="480" y="211" class="bf-note">エントリポイント · イメージベース · サブシステム</text>

  <rect x="160" y="226" width="300" height="30" rx="3" class="bf-aux"/>
  <text x="310" y="245" text-anchor="middle" class="bf-label">Section Headers</text>

  <rect x="160" y="266" width="300" height="174" rx="3" class="bf-group"/>
  <text x="170" y="284" class="bf-group-label">SECTIONS</text>

  <rect x="172" y="292" width="276" height="26" rx="2" class="bf-text"/>
  <text x="310" y="309" text-anchor="middle" class="bf-sect">.text</text>
  <text x="480" y="309" class="bf-note">実行コード</text>

  <rect x="172" y="322" width="276" height="26" rx="2" class="bf-ro"/>
  <text x="310" y="339" text-anchor="middle" class="bf-sect">.rdata</text>
  <text x="480" y="339" class="bf-note">読み取り専用データ · インポートテーブル</text>

  <rect x="172" y="352" width="276" height="26" rx="2" class="bf-data"/>
  <text x="310" y="369" text-anchor="middle" class="bf-sect">.data</text>
  <text x="480" y="369" class="bf-note">初期化済みグローバル変数</text>

  <rect x="172" y="382" width="276" height="26" rx="2" class="bf-rsrc"/>
  <text x="310" y="399" text-anchor="middle" class="bf-sect">.rsrc</text>
  <text x="480" y="399" class="bf-note">アイコン · バージョン情報などリソース</text>

  <rect x="172" y="412" width="276" height="26" rx="2" class="bf-reloc"/>
  <text x="310" y="429" text-anchor="middle" class="bf-sect">.reloc</text>
  <text x="480" y="429" class="bf-note">再配置情報</text>
</svg>
</div>

面白い点：PEファイルの先頭には今なお**DOS互換用「MZ」マジックナンバー**があります（MZはDOSの開発者Mark Zbikowskiのイニシャル）。1993年に設計された形式が**1981年のDOS互換性文字列を今も持っています**。これがWindowsの下位互換性文化を示す代表例です。

### Mach-O — macOSの形式

**Mach-O (Mach Object)**はMachカーネルとともに設計された形式です。NeXTSTEPで始まり、今もmacOS/iOSが使います。

Mach-Oファイルの構造：

<div class="bf-container">
<svg viewBox="0 0 900 490" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mach-Oファイル構造">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Mach-Oファイル構造 (macOS / iOS)</text>

  <rect x="160" y="56" width="300" height="30" rx="3" class="bf-meta"/>
  <text x="310" y="75" text-anchor="middle" class="bf-label">Header</text>
  <text x="480" y="75" class="bf-note">マジック 0xFEEDFACE (32) / 0xFEEDFACF (64)</text>

  <rect x="160" y="98" width="300" height="134" rx="3" class="bf-meta"/>
  <text x="310" y="116" text-anchor="middle" class="bf-label">Load Commands</text>
  <text x="480" y="116" class="bf-note">ローダへの指示</text>
  <text x="176" y="140" class="bf-sub">LC_SEGMENT</text>
  <text x="306" y="140" class="bf-sub">メモリセグメント定義</text>
  <text x="176" y="160" class="bf-sub">LC_DYLD_INFO</text>
  <text x="306" y="160" class="bf-sub">動的リンカ情報</text>
  <text x="176" y="180" class="bf-sub">LC_SYMTAB</text>
  <text x="306" y="180" class="bf-sub">シンボルテーブル</text>
  <text x="176" y="200" class="bf-sub">LC_LOAD_DYLIB</text>
  <text x="306" y="200" class="bf-sub">必要なライブラリ</text>
  <text x="176" y="220" class="bf-sub">LC_CODE_SIGNATURE</text>
  <text x="306" y="220" class="bf-sub">コード署名</text>

  <rect x="160" y="244" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="262" class="bf-group-label">SEGMENT · __TEXT</text>
  <rect x="172" y="272" width="276" height="24" rx="2" class="bf-text"/>
  <text x="310" y="289" text-anchor="middle" class="bf-sect">__text</text>
  <text x="480" y="289" class="bf-note">実行コード</text>
  <rect x="172" y="300" width="276" height="24" rx="2" class="bf-ro"/>
  <text x="310" y="317" text-anchor="middle" class="bf-sect">__cstring</text>
  <text x="480" y="317" class="bf-note">C文字列定数</text>

  <rect x="160" y="340" width="300" height="84" rx="3" class="bf-seg"/>
  <text x="176" y="358" class="bf-group-label">SEGMENT · __DATA</text>
  <rect x="172" y="368" width="276" height="24" rx="2" class="bf-data"/>
  <text x="310" y="385" text-anchor="middle" class="bf-sect">__data</text>
  <text x="480" y="385" class="bf-note">初期化済みグローバル変数</text>
  <rect x="172" y="396" width="276" height="24" rx="2" class="bf-bss"/>
  <text x="310" y="413" text-anchor="middle" class="bf-sect">__bss</text>
  <text x="480" y="413" class="bf-note">0初期化グローバル変数</text>

  <rect x="160" y="436" width="300" height="30" rx="3" class="bf-linkedit"/>
  <text x="310" y="455" text-anchor="middle" class="bf-label">Segment: __LINKEDIT</text>
  <text x="480" y="455" class="bf-note">シンボル · 再配置 · 署名</text>
</svg>
</div>

**Universal Binary (Fat Binary)**：1つのファイルに複数のアーキテクチャのMach-Oをすべて収められます。

<div class="bf-container">
<svg viewBox="0 0 900 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Universal Binary (Fat Binary) 構造">
  <text x="450" y="30" text-anchor="middle" class="bf-title">Universal Binary (Fat Binary)</text>

  <rect x="160" y="50" width="300" height="32" rx="3" class="bf-meta"/>
  <text x="310" y="71" text-anchor="middle" class="bf-label">Fat Header</text>
  <text x="480" y="71" class="bf-note">内蔵アーキテクチャ一覧 · 各オフセット</text>

  <rect x="160" y="90" width="300" height="46" rx="3" class="bf-arch-x86"/>
  <text x="310" y="110" text-anchor="middle" class="bf-label">Arch 0: x86_64</text>
  <text x="310" y="128" text-anchor="middle" class="bf-sub">(完全なMach-O)</text>
  <text x="480" y="119" class="bf-note">Intel Mac用</text>

  <rect x="160" y="144" width="300" height="46" rx="3" class="bf-arch-arm"/>
  <text x="310" y="164" text-anchor="middle" class="bf-label">Arch 1: arm64</text>
  <text x="310" y="182" text-anchor="middle" class="bf-sub">(完全なMach-O)</text>
  <text x="480" y="173" class="bf-note">Apple Silicon用</text>
</svg>
</div>

これが**「同一のアプリがIntel MacとM1 Mac両方でネイティブに動く」**構造です。2006年のPowerPC→Intel移行でも、2020年のIntel→Apple Silicon移行でも同じ方式で移植が行われました。

### マルチプラットフォームビルドでの意味

Unity、Unrealのようなエンジンが「一度作れば複数プラットフォームで動く」と宣伝しますが、実際にはエンジンが内部的に**3つの形式に合わせて作り直し**ます。あなたがBuild Settingsでプラットフォームを変えるときエンジンがやっていること：

- **Windows**：MSVCまたはclang-clでコンパイル → PE32+生成、Windows SDKリンク
- **macOS**：clang/xcodeツールチェーン → Mach-O生成、Cocoaフレームワークリンク（Universal BinaryでIntel+ARM同時）
- **Linux**：gccまたはclang → ELF生成、glibcリンク

同じC++コードでも**最終バイナリはまったく違うファイル**です。そのためWindowsでビルドした`.exe`をmacOSに持っていっても動きません。

**もう1つの落とし穴**：ゲームエンジンは動的ライブラリを多用します。

- Windows：`.dll`
- macOS：`.dylib`または`.framework`（バンドル形式）
- Linux：`.so`

各プラットフォーム別に**全部別々にビルド**する必要があります。Unityネイティブプラグインが Windowsだけ対応するケースが多い理由です。

---

## Part 5：macOS固有の話 — Appleが積み上げたもの

ここからはMacユーザーに特に面白いセクションです。macOSが他のOSと異なる**Apple固有のシステム**たちを深く見ていきます。

### XNU誕生の裏話

前でXNUがMach + BSDの二重構造だと言いましたが、その過程には**失敗と妥協の歴史**があります。

**第1段階 (1985〜88) — 純粋Machの夢**
Carnegie Mellon UniversityのMachプロジェクトは*「BSD Unix機能をマイクロカーネルで再実装する」*学術実験でした。Rashid教授と学生たちがMach 2.0を出しましたが、これは「Mach + BSDサーバー」が1つのカーネルに混在した**混成構造**でした。

**第2段階 (1990) — Mach 3.0の試み**
Mach 3.0は純粋なマイクロカーネルを志向してBSDコードを完全に**ユーザー空間サーバー**に分離しました。理論的には完璧でしたが性能が酷いものでした。OSF/1という商用OSがMach 3.0で出ましたが市場で失敗しました。

**第3段階 (1989〜96) — NeXTSTEPの実用的選択**
NeXTは最初にMach 2.0をベースにNeXTSTEPを作りました。一部のBSD機能をMachカーネルに直接マージして性能を確保。これがNeXTSTEPのカーネル基盤です。

**第4段階 (2000〜) — XNU**
AppleがNeXTSTEPを取ってmacOSとして作る際、BSD側を**FreeBSD 5.x**から大幅に更新して持ってきました。この結果がXNU。そのためmacOSで`uname -a`を打つと"Darwin"が出ますが、**Darwin = XNU + BSDユーザーランド = macOSのオープンソース部分**です。

```bash
$ uname -a
Darwin MacBook.local 23.0.0 Darwin Kernel Version 23.0.0: ...
```

AppleはDarwinをオープンソースで公開しています。あなたも[opensource.apple.com](https://opensource.apple.com)でXNUソースを受け取ってビルドできます。

### Machポート — すべての根源

Machマイクロカーネルの中核的抽象化は**ポート (port)**です。MachポートはUnixのファイル記述子（file descriptor）に似た役割ですが、はるかに広範です。

- **プロセス間通信**：メッセージをポートでやり取り
- **シグナル処理**：UnixシグナルがMachポートメッセージに変換される
- **IOKitドライバ**：ユーザー空間アプリがドライバとポートで通信
- **Bootstrap**：ネームサービス（`launchd`が提供）もポートベース

**なぜ重要か？** macOSのセキュリティモデルとIPCがすべてポートの上に築かれています。例えばアプリサンドボックスは「このアプリはこの特定のポートだけ使える」で実装されます。iOSの厳格なアプリ隔離も根本的にMachポートベースです。

```c
/* Machポートでメッセージを送る（極端に簡略化） */
mach_port_t target_port = ...;
mach_msg_send(&msg_header);
```

開発者が直接使うことはほぼありませんが、デバッガ（lldb）やXcode Instrumentsのようなツールの内部で動作しています。

### Grand Central Dispatch (2009)

**2009年のmacOS 10.6 Snow Leopard**でAppleはGrand Central Dispatch (GCD、libdispatch) を導入しました。これはマルチコア時代に対するAppleの答えでした。

**従来のスレッドモデルの問題**：
```c
/* 伝統的なC/Unixスタイル */
pthread_t thread;
pthread_create(&thread, NULL, worker_function, arg);
pthread_join(thread, NULL);
```
- 開発者がスレッド数、寿命、同期を直接管理
- CPUコア数がわからなければ過剰または不足する
- 同期プリミティブ使用にミスが多い

**GCDの解決**：スレッドではなく**キュー**に作業を放る。

```swift
/* Swift */
DispatchQueue.global(qos: .userInitiated).async {
    /* ここの作業がバックグラウンドで実行される */
    let result = heavyComputation()
    DispatchQueue.main.async {
        updateUI(result)
    }
}
```

OSがCPUコア数、システム負荷などを考慮してスレッドを**自動で**生成/再利用します。開発者は「どの優先度で実行するか」だけを指定します（QoS：User Interactive、User Initiated、Utility、Background）。

**GCDはオープンソースlibdispatchとして公開**され、Swift on Linuxでも使われています。つまり、他の言語やプラットフォームでもGCDスタイルのプログラミングが可能です。

**ゲーム開発の視点から**：Unity Job SystemはGCDと思想が非常に似ています — 「スレッドではなく作業をスケジューラに任せる」。Part 13で詳しく扱います。

### launchd — systemdより先に

2005年のmacOS 10.4 TigerでAppleは**launchd**を導入しました。これはUnixの伝統的なinitシステム（SysVinit、cron、xinetd、inetd、atdなど複数のデーモンが分散していた役割）を**1つのプロセスに統合**したものです。

launchd以前のUnix：
- `init` (PID 1)：起動時のシステム初期化
- `cron`：定期的な作業
- `atd`：一度だけの予約作業
- `inetd`：ネットワーク要求時にデーモン起動
- 各デーモンが別々に実行

launchdはこれらすべてを統合した**万能デーモン管理者**です：
- PID 1として実行、システム全体のプロセス管理
- XMLベースのplistファイルでサービス定義
- ファイルアクセス、ネットワーク接続などの**オンデマンド実行**対応
- 失敗時に自動再起動

**歴史的意義**：Linuxの**systemd**（2010年Lennart Poettering）がlaunchdからインスピレーションを受けました。systemdが導入されたときLinuxコミュニティで「Unix哲学に反する」という批判が大きかったですが、すでにlaunchdが5年前に同じアプローチをしていて、macOSで何の問題もなく動いていました。

`launchctl`コマンドで管理：

```bash
# 実行中のサービス一覧
launchctl list

# 特定のサービス開始
launchctl load ~/Library/LaunchAgents/com.example.myservice.plist

# 停止
launchctl unload ~/Library/LaunchAgents/com.example.myservice.plist
```

### Apple Silicon — P/Eコアの異種構造

2020年Appleは自社設計CPU **M1 (Apple Silicon)**をMacに導入しました。M1はARM64ベースですが**一般的なARMサーバとは異なる独特な構造**を持ちます。

**Pコア (Performance) とEコア (Efficiency)**

M1は同じARM ISAを実行する**2種類のコア**を持ちます：

- **Pコア "Firestorm"**：高性能、高電力。ゲーム、コンパイル、レンダリングなどの重い作業
- **Eコア "Icestorm"**：低性能、低電力。バックグラウンド作業、システムデーモン、バッテリ節約

| スペック | Pコア | Eコア |
|---------|------|------|
| クロック | 3.2 GHz | 2.0 GHz |
| L1キャッシュ | 192KB | 128KB |
| L2キャッシュ | 共有12MB | 共有4MB |
| 電力 | 〜15W | 〜1W |
| 性能比 | 〜100% | 〜25% |
| M1構成 | 4個 | 4個 |

**macOSのQoSベーススケジューリング**：前述のGCDのQoSクラスがここで再登場します。

- **User Interactive / User Initiated** QoS → 主にPコア
- **Utility** QoS → 状況次第
- **Background** QoS → 主にEコア

開発者が`DispatchQueue.global(qos: .userInitiated)`と書くだけで、OSが**どのコアで実行するか決めます**。これがAppleの「開発者がハードウェアの詳細を知らなくていい」哲学です。

**16KBページサイズ**

Apple Siliconのもう1つの特異点は**ページサイズが16KB**であることです。Linux/Windowsの標準は**4KB**。

- **長所**：TLB (Translation Lookaside Buffer) のミスが減り、大容量メモリアプリの性能が向上
- **短所**：メモリアラインメント要求事項の変更。4KBページを前提とした古いアプリが動かないことがある

2020年Apple Silicon移行初期に**Homebrew、Docker、一部のバイナリ互換性ツール**が16KBページ問題で苦労しました。今はほとんど解決していますが、Unityネイティブプラグイン開発時に`mprotect()`呼び出しのようなものでページアラインメントに注意する必要があります。

### Rosetta 2 — エミュレータではなく翻訳機

Apple Silicon移行の成功要因の1つは**Rosetta 2**です。これはx86_64 Mach-OバイナリをARM64で実行します。驚くべきことに**ネイティブ性能の70〜80%**が出ます。

**Rosetta 2はJITエミュレータではありません**。アプリをインストールするとき（または最初の実行時）にx86命令をARMに**AOT（Ahead-of-Time）翻訳**してファイルとして保存します。以降の実行はすでに翻訳されたARMバイナリを動かすことになるので速いのです。

**決定的なトリック — ハードウェアTSOモード**：この部分が最も興味深いです。

x86は**強いメモリモデル (TSO、Total Store Order)**を持ちます。あるCPUが書いた値が他のCPUに見える順序がプログラミング順序とほぼ同じです。

ARMは**弱いメモリモデル**を持ちます。CPUが性能のためにメモリ書き込み/読み出し順序を**勝手に並べ替え**られます。プログラマが明示的にメモリバリアを入れなければ順序は保証されません。

問題は**x86用に書かれたプログラム**がTSOを暗黙に仮定しているときに起こります。こういうプログラムを単純にARM命令に翻訳するとARMの並べ替えのせいで**race conditionが新しく発生します**。

Appleの解決：**M1 CPUに「TSOモード」ハードウェアを入れました**。Rosetta 2が翻訳したバイナリが実行されるとき、CPUに「このスレッドはTSOモードで動かせ」というフラグを立てます。するとARM CPUが**x86と同じ強いメモリ順序**で動作します。

> 💡 このテーマはPart 12（メモリモデルと原子演算）で再登場します。今は「Appleがハードウェアレベルで互換性トリックを使った」という点だけ覚えておけば十分です。

**Rosetta 2の限界**：
- AVX-512のような最新のx86拡張命令は翻訳されない
- カーネル拡張（.kext）はRosettaで動かせない — OS自体はネイティブでなければならない
- JITコンパイラ内蔵プログラム（Chrome V8エンジンなど）はRosetta + JITの二重翻訳になり遅くなる可能性

### XNU内部構造

<div class="os-xnu-container">
<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="XNU kernel internals">
  <text x="450" y="28" text-anchor="middle" class="xu-title">XNUカーネル内部 — Mach + BSD + I/O Kit</text>

  <g class="xu-user">
    <rect x="60" y="60" width="780" height="70" rx="8"/>
    <text x="450" y="88" text-anchor="middle" class="xu-heading">ユーザー空間 (User Space)</text>
    <text x="210" y="112" text-anchor="middle" class="xu-sub">Cocoa / UIKit</text>
    <text x="380" y="112" text-anchor="middle" class="xu-sub">Swift / Objective-C</text>
    <text x="550" y="112" text-anchor="middle" class="xu-sub">POSIX アプリ (bash, ls)</text>
    <text x="730" y="112" text-anchor="middle" class="xu-sub">システムデーモン (launchd)</text>
  </g>

  <path d="M 450 130 L 450 155" class="xu-syscall" stroke-dasharray="4 4"/>
  <text x="500" y="148" class="xu-sc-label">syscall / Mach trap</text>

  <g class="xu-boundary">
    <line x1="60" y1="160" x2="840" y2="160"/>
    <text x="840" y="155" text-anchor="end" class="xu-bd-label">Kernel Space ↓</text>
  </g>

  <g class="xu-bsd">
    <rect x="60" y="175" width="780" height="80" rx="8"/>
    <text x="450" y="200" text-anchor="middle" class="xu-heading">BSD Layer</text>
    <text x="180" y="225" text-anchor="middle" class="xu-sub">プロセスモデル (POSIX)</text>
    <text x="380" y="225" text-anchor="middle" class="xu-sub">ファイルシステム (APFS/HFS+)</text>
    <text x="560" y="225" text-anchor="middle" class="xu-sub">ネットワーク (BSD sockets)</text>
    <text x="730" y="225" text-anchor="middle" class="xu-sub">シグナル、権限</text>
    <text x="450" y="245" text-anchor="middle" class="xu-note">「私たちが見るUnixの顔」</text>
  </g>

  <g class="xu-mach">
    <rect x="60" y="270" width="780" height="90" rx="8"/>
    <text x="450" y="295" text-anchor="middle" class="xu-heading">Mach Microkernel</text>
    <text x="200" y="320" text-anchor="middle" class="xu-sub">Task（プロセス）</text>
    <text x="380" y="320" text-anchor="middle" class="xu-sub">Thread（スレッド）</text>
    <text x="560" y="320" text-anchor="middle" class="xu-sub">Mach Port (IPC)</text>
    <text x="730" y="320" text-anchor="middle" class="xu-sub">VM、スケジューラ</text>
    <text x="450" y="345" text-anchor="middle" class="xu-note">「CMU 1985〜91年の研究の産物」</text>
  </g>

  <g class="xu-iokit">
    <rect x="60" y="375" width="780" height="50" rx="8"/>
    <text x="450" y="395" text-anchor="middle" class="xu-heading">I/O Kit（C++で書かれたドライバフレームワーク）</text>
    <text x="450" y="415" text-anchor="middle" class="xu-sub">GPU、USB、センサ、電源管理</text>
  </g>

  <g class="xu-hw">
    <rect x="60" y="430" width="780" height="24" rx="4"/>
    <text x="450" y="447" text-anchor="middle" class="xu-hwtext">Hardware (Apple Silicon / Intel)</text>
  </g>
</svg>
</div>

<style>
.os-xnu-container { margin: 2rem 0; text-align: center; }
.os-xnu-container svg { max-width: 100%; height: auto; }
.xu-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.xu-heading { font-size: 13px; font-weight: 700; fill: #2d3748; }
.xu-sub { font-size: 11px; fill: #2d3748; }
.xu-note { font-size: 10px; fill: #4a5568; font-style: italic; }
.xu-sc-label { font-size: 10px; fill: #718096; }
.xu-bd-label { font-size: 11px; fill: #718096; font-weight: 600; }
.xu-user rect { fill: #e6fffa; stroke: #319795; stroke-width: 1.5; }
.xu-bsd rect { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.xu-mach rect { fill: #fed7d7; stroke: #e53e3e; stroke-width: 1.5; }
.xu-iokit rect { fill: #fefcbf; stroke: #d69e2e; stroke-width: 1.5; }
.xu-hw rect { fill: #edf2f7; stroke: #718096; stroke-width: 1; }
.xu-hwtext { font-size: 11px; fill: #2d3748; font-weight: 500; }
.xu-syscall { fill: none; stroke: #805ad5; stroke-width: 2; }
.xu-boundary line { stroke: #4a5568; stroke-width: 2; stroke-dasharray: 6 3; }

[data-mode="dark"] .xu-title { fill: #e2e8f0; }
[data-mode="dark"] .xu-heading { fill: #cbd5e0; }
[data-mode="dark"] .xu-sub { fill: #e2e8f0; }
[data-mode="dark"] .xu-note { fill: #a0aec0; }
[data-mode="dark"] .xu-sc-label { fill: #a0aec0; }
[data-mode="dark"] .xu-bd-label { fill: #a0aec0; }
[data-mode="dark"] .xu-user rect { fill: #234e52; stroke: #4fd1c5; }
[data-mode="dark"] .xu-bsd rect { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .xu-mach rect { fill: #742a2a; stroke: #fc8181; }
[data-mode="dark"] .xu-iokit rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .xu-hw rect { fill: #2d3748; stroke: #a0aec0; }
[data-mode="dark"] .xu-hwtext { fill: #e2e8f0; }
[data-mode="dark"] .xu-syscall { stroke: #b794f4; }
[data-mode="dark"] .xu-boundary line { stroke: #a0aec0; }

@media (max-width: 768px) {
  .xu-title { font-size: 14px; }
  .xu-heading { font-size: 11px; }
  .xu-sub { font-size: 9.5px; }
  .xu-note { font-size: 9px; }
}
</style>

### Apple Silicon異種コア構造

<div class="os-silicon-container">
<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Apple Silicon heterogeneous cores">
  <text x="450" y="28" text-anchor="middle" class="si-title">Apple Silicon M1 — P/EコアとQoSマッピング</text>

  <g class="si-chip">
    <rect x="60" y="60" width="780" height="260" rx="12"/>
    <text x="450" y="85" text-anchor="middle" class="si-chip-label">M1 SoC (System on Chip)</text>
  </g>

  <g class="si-pcluster">
    <rect x="100" y="110" width="340" height="100" rx="8"/>
    <text x="270" y="130" text-anchor="middle" class="si-cluster-label">Pクラスタ (Firestorm × 4)</text>
    <g class="si-core si-pcore">
      <rect x="115" y="145" width="75" height="55" rx="4"/>
      <text x="152" y="168" text-anchor="middle" class="si-corename">P0</text>
      <text x="152" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="195" y="145" width="75" height="55" rx="4"/>
      <text x="232" y="168" text-anchor="middle" class="si-corename">P1</text>
      <text x="232" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="275" y="145" width="75" height="55" rx="4"/>
      <text x="312" y="168" text-anchor="middle" class="si-corename">P2</text>
      <text x="312" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
    <g class="si-core si-pcore">
      <rect x="355" y="145" width="75" height="55" rx="4"/>
      <text x="392" y="168" text-anchor="middle" class="si-corename">P3</text>
      <text x="392" y="185" text-anchor="middle" class="si-coreghz">3.2 GHz</text>
    </g>
  </g>

  <g class="si-ecluster">
    <rect x="460" y="110" width="340" height="100" rx="8"/>
    <text x="630" y="130" text-anchor="middle" class="si-cluster-label">Eクラスタ (Icestorm × 4)</text>
    <g class="si-core si-ecore">
      <rect x="475" y="145" width="75" height="55" rx="4"/>
      <text x="512" y="168" text-anchor="middle" class="si-corename">E0</text>
      <text x="512" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="555" y="145" width="75" height="55" rx="4"/>
      <text x="592" y="168" text-anchor="middle" class="si-corename">E1</text>
      <text x="592" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="635" y="145" width="75" height="55" rx="4"/>
      <text x="672" y="168" text-anchor="middle" class="si-corename">E2</text>
      <text x="672" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
    <g class="si-core si-ecore">
      <rect x="715" y="145" width="75" height="55" rx="4"/>
      <text x="752" y="168" text-anchor="middle" class="si-corename">E3</text>
      <text x="752" y="185" text-anchor="middle" class="si-coreghz">2.0 GHz</text>
    </g>
  </g>

  <g class="si-uma">
    <rect x="100" y="230" width="700" height="60" rx="8"/>
    <text x="450" y="252" text-anchor="middle" class="si-uma-label">Unified Memory (16KBページ)</text>
    <text x="450" y="275" text-anchor="middle" class="si-uma-sub">CPU、GPU、Neural Engineが同じメモリプールを共有</text>
  </g>

  <g class="si-qos">
    <rect x="60" y="340" width="780" height="80" rx="8"/>
    <text x="450" y="362" text-anchor="middle" class="si-qos-title">macOS QoS → コアマッピング</text>
    <line x1="140" y1="380" x2="270" y2="380" class="si-qos-arrow" marker-end="url(#si-arr-p)"/>
    <text x="205" y="402" text-anchor="middle" class="si-qos-label">User Interactive / User Initiated → Pクラスタ</text>
    <line x1="560" y1="380" x2="700" y2="380" class="si-qos-arrow" marker-end="url(#si-arr-e)"/>
    <text x="630" y="402" text-anchor="middle" class="si-qos-label">Utility / Background → Eクラスタ</text>
  </g>

  <defs>
    <marker id="si-arr-p" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#3182ce"/>
    </marker>
    <marker id="si-arr-e" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#38a169"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.os-silicon-container { margin: 2rem 0; text-align: center; }
.os-silicon-container svg { max-width: 100%; height: auto; }
.si-title { font-size: 16px; font-weight: 700; fill: #1a202c; }
.si-chip rect { fill: #f7fafc; stroke: #4a5568; stroke-width: 2; stroke-dasharray: 5 5; }
.si-chip-label { font-size: 13px; font-weight: 600; fill: #2d3748; }
.si-pcluster rect { fill: #bee3f8; stroke: #3182ce; stroke-width: 1.5; }
.si-ecluster rect { fill: #c6f6d5; stroke: #38a169; stroke-width: 1.5; }
.si-cluster-label { font-size: 12px; font-weight: 600; fill: #1a202c; }
.si-pcore rect { fill: #3182ce; stroke: #2c5282; stroke-width: 1; }
.si-ecore rect { fill: #38a169; stroke: #276749; stroke-width: 1; }
.si-corename { font-size: 13px; font-weight: 700; fill: white; }
.si-coreghz { font-size: 10px; fill: white; }
.si-uma rect { fill: #feebc8; stroke: #d69e2e; stroke-width: 1.5; }
.si-uma-label { font-size: 13px; font-weight: 600; fill: #2d3748; }
.si-uma-sub { font-size: 11px; fill: #4a5568; }
.si-qos rect { fill: #faf5ff; stroke: #805ad5; stroke-width: 1.5; }
.si-qos-title { font-size: 13px; font-weight: 700; fill: #553c9a; }
.si-qos-arrow { stroke-width: 2; }
.si-qos-label { font-size: 11px; fill: #2d3748; }

[data-mode="dark"] .si-title { fill: #e2e8f0; }
[data-mode="dark"] .si-chip rect { fill: #1a202c; stroke: #a0aec0; }
[data-mode="dark"] .si-chip-label { fill: #cbd5e0; }
[data-mode="dark"] .si-pcluster rect { fill: #2a4365; stroke: #63b3ed; }
[data-mode="dark"] .si-ecluster rect { fill: #22543d; stroke: #68d391; }
[data-mode="dark"] .si-cluster-label { fill: #e2e8f0; }
[data-mode="dark"] .si-pcore rect { fill: #63b3ed; stroke: #2c5282; }
[data-mode="dark"] .si-ecore rect { fill: #68d391; stroke: #276749; }
[data-mode="dark"] .si-corename { fill: #1a202c; }
[data-mode="dark"] .si-coreghz { fill: #1a202c; }
[data-mode="dark"] .si-uma rect { fill: #744210; stroke: #ecc94b; }
[data-mode="dark"] .si-uma-label { fill: #e2e8f0; }
[data-mode="dark"] .si-uma-sub { fill: #a0aec0; }
[data-mode="dark"] .si-qos rect { fill: #322659; stroke: #b794f4; }
[data-mode="dark"] .si-qos-title { fill: #d6bcfa; }
[data-mode="dark"] .si-qos-label { fill: #e2e8f0; }

@media (max-width: 768px) {
  .si-title { font-size: 14px; }
  .si-cluster-label { font-size: 10px; }
  .si-uma-label { font-size: 11px; }
  .si-qos-title { font-size: 11px; }
  .si-qos-label { font-size: 9px; }
}
</style>

> ### ちょっと、これは押さえておこう
>
> **「Rosetta 2はなぜ速いのか？ エミュレータなのにネイティブ性能の70%は無茶苦茶では？」**
>
> 3つの理由が重なっているからです。
>
> 1. **AOT翻訳（事前翻訳）**：エミュレータではありません。アプリをインストールするときや初回実行時にx86バイナリをARMに**完全に翻訳してキャッシュ**します。以降はネイティブARMを実行するだけです。
> 2. **M1がそもそもx86よりはるかに速い**：M1のシングルコア性能が同世代のIntel CPUより優れています。70%に落ちても絶対性能は悪くありません。
> 3. **ハードウェアTSOモード**：x86のメモリモデルをARMに強制するためのソフトウェアエミュレーションは高価です。Appleはこれを**ハードウェアに入れて**タダにしました。
>
> **限界**：ハードウェアTSOモードはx86バイナリが実行されるときだけオンになります。ネイティブARMアプリは弱いメモリモデルをそのまま使います。

---

## Part 6：3つのOSの長所短所表

これまでの内容を1枚の表にまとめます。各OSの強みと弱みを客観的に並べました。

### 開発者視点

| 領域 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **カーネルソースアクセス** | ✅ 完全公開 | ❌ 非公開 | 🟡 Darwinのみ公開（GUI/Cocoa非公開） |
| **CLI エコシステム** | ✅ 最高 (bash、coreutilsネイティブ) | 🟡 PowerShell優秀、WSL必要 | ✅ Unix標準ツール基本搭載 |
| **パッケージ管理** | ✅ apt/dnf/pacman | 🟡 winget/choco（後発） | 🟡 Homebrew（非公式） |
| **仮想化/コンテナ** | ✅ Dockerネイティブ | 🟡 WSL 2 / Hyper-V | 🟡 Docker Desktop（VM経由） |
| **言語対応** | ✅ すべての言語 | ✅ すべての言語（特に.NET） | ✅ すべての言語（Swiftが1級） |
| **IDE** | 🟡 VS Code、CLion | ✅ Visual Studio最高 | ✅ Xcode、JetBrains |
| **ドキュメント** | 🟡 分散、manページ | ✅ MSDN体系的 | ✅ Apple Developerドキュメント |
| **コミュニティ** | ✅ 巨大、開放的 | 🟡 エンタープライズ中心 | 🟡 Appleエコシステム中心 |

### ゲーム開発視点

| 領域 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **主要グラフィックAPI** | Vulkan、OpenGL | DirectX 11/12、Vulkan | Metal（OpenGL/Vulkan対応終了中） |
| **ゲームエンジン対応** | 🟡 Unity/Unrealビルドターゲットのみ | ✅ 最高（エディタ含む） | 🟡 Unity/Unrealエディタ対応改善中 |
| **オーディオAPI** | ALSA、PulseAudio、PipeWire | XAudio2、WASAPI | Core Audio |
| **デバッガ/プロファイラ** | 🟡 GDB、Valgrind | ✅ Visual Studio | ✅ Instruments、Xcode |
| **Steamゲームプレイ** | 🟡 Proton（改善中） | ✅ ネイティブ | 🟡 制限的 |
| **VR/AR対応** | 🟡 SteamVR | ✅ WMR、SteamVR | 🟡 Vision Proエコシステム |

### サーバ運用視点

| 領域 | Linux | Windows | macOS |
|------|-------|---------|-------|
| **Webサーバシェア** | 〜75% | 〜20% | 〜0%（サーバ用ではない） |
| **コンテナネイティブ** | ✅ | 🟡 LCOW（LinuxコンテナをWSLで） | ❌ |
| **低資源運用** | ✅ 最小数百MBで動作 | 🟡 数GB必要 | 🟡 サーバ用途はほぼない |
| **ライセンス費用** | ✅ 無料 | 💰 有料 (Windows Server) | 🟡 Appleハードウェア必要 |

### 核心結論

- **「最高のOS」は存在しない** — 用途によって違います
- **サーバ/開発**：Linuxが支配的
- **企業/ゲームクライアント**：Windowsが支配的
- **クリエイティブ作業/個人開発**：macOSが強い
- **すべてのOSがお互いの強みを借りてきている**：
  - WindowsがWSLでLinux互換
  - macOSがHomebrewでLinuxツールエコシステムを活用
  - Linuxがデスクトップ UXの改善に投資

---

## Part 7：セキュリティとサンドボックス — 簡潔に

OSごとにセキュリティモデルが違います。ゲーム開発視点で関連する部分だけ簡潔に。

### macOS — 多層セキュリティ

**SIP (System Integrity Protection)**：システムファイル保護。`/System`、`/bin`などはrootでも修正不可。2015年のEl Capitanで導入。

**Gatekeeper**：署名されていないアプリの実行を遮断。「Appleで身元が確認されていない開発者」警告がこれ。

**Notarization（公証）**：Appleにバイナリを提出してマルウェア検証を受けないとGatekeeper警告なしに実行不可。2019年義務化。

**App Sandbox**：Mac App Storeアプリは義務的にサンドボックス。一般アプリは選択的。ファイルシステム、ネットワーク、カメラなどをentitlementで明示。

**Hardened Runtime**：JIT、ライブラリ注入などを遮断する追加セキュリティ層。

開発者視点：Mac用商用アプリ配布時は**Apple Developerアカウント（99ドル/年）**で署名 + 公証必須。ゲーム配布時に重要。

### Windows — UACとDefender

**UAC (User Account Control)**：管理者権限が必要な作業にユーザー確認。Vistaのときに導入され、悪評が立ちましたが今では必須のセキュリティモデル。

**Windows Defender**：基本内蔵アンチウイルス。Windows 10以降、サードパーティAVはほぼ不要なレベル。

**Code Signing**：Authenticode署名。EV証明書はSmartScreen警告なしに実行。ゲーム配布時に推奨。

**AppContainer**：UWPアプリ隔離。Mac App Sandboxと類似の概念ですが使用範囲が狭い。

### Linux — 柔軟なツール群

**User/Group権限**：Unixの伝統。rwxビット、UID/GID。

**Capabilities**：rootの権限を分割して付与（`CAP_NET_BIND_SERVICE`、`CAP_SYS_ADMIN`など）。

**SELinux / AppArmor**：Mandatory Access Control。より細かいポリシー強制。

**cgroups + namespaces**：Dockerの基盤技術。プロセスグループに資源制限と隔離。

**seccomp**：システムコールフィルタリング。特定のシステムコールだけ許可するサンドボックス。

ゲーム開発時に**AppImage、Flatpak、Snap**のような配布形式は内部的にこれらの技術を使っています。

---

## Part 8：ゲーム開発者の視点から

最後に、**ゲーム開発者の立場から**3つのOSの違いがどう現れるかを見ます。

### プラットフォーム別ゲーム開発の考慮事項

**1. Unityエディタ**
- Windows：フル機能、推奨プラットフォーム
- macOS：対応良好、Apple Siliconネイティブビルド可能
- Linux：限定的対応（公式Editorあり、プラグイン互換性は低下）

**2. Unreal Engineエディタ**
- Windows：フル機能、基本対応
- macOS：対応されるが一部機能制限（Vulkan対応など）
- Linux：公式対応あり、エディタもビルド可能

**3. グラフィックAPI選択**
- クロスプラットフォームが目標なら**Vulkan + DirectX 12**抽象化
- Appleプラットフォームターゲットなら**Metal**検討（AppleがOpenGL/Vulkan対応を中断中）
- Unity/Unrealのようなエンジンがこの抽象化を提供するが、ネイティブ最適化時は直接関与が必要

**4. クラッシュハンドラ**
- Windows：**SEH (Structured Exception Handling)**、`SetUnhandledExceptionFilter`
- Linux/macOS：**POSIXシグナル**（`SIGSEGV`、`SIGABRT`）、`signal()`または`sigaction()`
- 2つのアプローチが違うため、クロスプラットフォームクラッシュレポータ（Sentry、Crashlytics）が複雑になる

**5. ファイルパス**
- Windows：`C:\Users\name\AppData\...`、バックスラッシュ
- macOS：`/Users/name/Library/Application Support/...`、スラッシュ
- Linux：`/home/name/.local/share/...`（XDG標準）、スラッシュ
- エンジンの`Application.persistentDataPath`のような抽象化を使いつつ、直接扱うときは注意

**6. スレッド優先度**
- Windows：`SetThreadPriority`、7段階（IDLE〜TIME_CRITICAL）
- macOS：QoSクラス（4段階） + pthread優先度
- Linux：nice値（-20〜19） + pthread SCHED_FIFO/RR
- ゲームでオーディオスレッドのようなものに高い優先度を付ける必要があるときAPIが違う

### クロスプラットフォームエンジンの抽象化

エンジンはOSの違いを**隠すためのレイヤ**を持ちます。Unreal Engineの場合：

```cpp
/* UE のプラットフォーム抽象化（概念的な例） */
#if PLATFORM_WINDOWS
#include "Windows/WindowsPlatformFile.h"
typedef FWindowsPlatformFile FPlatformFile;
#elif PLATFORM_MAC
#include "Apple/ApplePlatformFile.h"
typedef FApplePlatformFile FPlatformFile;
#elif PLATFORM_LINUX
#include "Unix/UnixPlatformFile.h"
typedef FUnixPlatformFile FPlatformFile;
#endif
```

そのためエンジン開発者（エンジンを修正するプログラマ）は**3つのOSのAPIをすべて理解**する必要があります。ゲームプログラマ（エンジンを消費する立場）は`FPlatformFile`のような抽象レイヤだけを見ればよいのです。

### ツールチェーン互換性

| ツール | Linux | Windows | macOS |
|-------|-------|---------|-------|
| **主コンパイラ** | gcc/clang | MSVC/clang-cl | clang |
| **標準ライブラリ** | glibc/libstdc++/libc++ | MSVC STL | libc++ |
| **リンカ** | ld/lld | link.exe/lld-link | ld64 |
| **デバッガ** | gdb、lldb | Visual Studio、WinDbg | lldb、Xcode |
| **プロファイラ** | perf、Tracy | Visual Studio Profiler、PIX | Instruments |
| **CI/CD可能性** | ✅ 最高 | ✅ GitHub Actions Windows Runner | 🟡 Mac Runnerは有料/制限 |

**Appleの落とし穴**：iOS/macOSアプリをビルドするには**Xcodeが必要**で、Xcodeは**macOSでしか動きません**。つまりAppleプラットフォームターゲットゲームを作るには必ずMacビルドマシンが必要です。CI/CDでMac Runnerが高価な理由です。

### プラットフォーム別デバッグ体験比較

**Windows (Visual Studio)**
- 最高レベルのIDE + デバッガ統合
- Edit and Continue、条件付きブレークポイント、Data Breakpointすべてが滑らか
- PIXでGPUプロファイリング

**macOS (Xcode + Instruments)**
- Instrumentsは世界最高レベルのプロファイラの1つ（System Trace、Time Profiler、Allocations）
- Apple SiliconのP/Eコアタイムラインを可視化してくれる
- Metal Frame Debugger

**Linux (gdb/lldb + Tracy)**
- コマンドラインツールが主。VS CodeがUXを大きく改善
- Valgrind (Memcheck) は強力だが遅い
- Tracy Profilerはクロスプラットフォーム最高オプションの1つ

---

## まとめ

この回で扱った内容を1ページに要約します。

**血統**：
- Unix (1969) → BSD (1977) → NeXTSTEP (1989) → **macOS (2001)**
- Unix → Minix → **Linux (1991)**
- VMS (1977) + Dave Cutler → **Windows NT (1993)**

**設計思想**：
- Linux：開放性 + 性能
- Windows：下位互換性
- macOS：垂直統合 + 体験

**カーネル構造**：
- Linux：モノリシック
- Windows NT：ハイブリッド
- macOS XNU：Machマイクロカーネル + BSDレイヤ（二重構造）

**バイナリ形式**：
- Linux：ELF
- Windows：PE（1981年のDOS互換MZヘッダを維持）
- macOS：Mach-O（Universal Binaryで多重アーキテクチャ）

**macOS特有のもの**：
- XNU：理論はマイクロカーネル、実際はハイブリッド
- Machポート：macOSのIPCとセキュリティのルーツ
- Grand Central Dispatch (2009)：「スレッドの代わりにキュー」抽象化
- launchd (2005)：systemdの5年前の原型
- Apple Silicon：P/E異種コア + 16KBページ
- Rosetta 2：AOT翻訳 + ハードウェアTSOモード

**ゲーム開発時に覚えておく点**：
- 実行バイナリ形式が違うため、マルチプラットフォームビルドは**各OS別のビルド**
- クラッシュハンドラ、スレッド優先度、ファイルパスなど些細に見えるものもAPIが違う
- エンジン抽象化レイヤを信じつつ、性能が重要な部分はプラットフォーム別最適化が必要
- Appleプラットフォームターゲットなら必ずMacビルドマシンが必要

次の回からはこの地図をベースに**具体的な理論**に入ります。Part 8は**プロセスとスレッド** — PCB/TCB構造、`fork()`と`CreateProcess()`の実際の違い、スレッドマッピングモデル、コンテキストスイッチコストまでをゲームエンジンの実行モデルと結びつけて見ていきます。

---

## References

### 教科書
- Silberschatz, Galvin, Gagne — *Operating System Concepts*, 10th ed., Wiley, 2018 — OS標準教科書、3章 (Processes)、4章 (Threads) 参照
- Tanenbaum, Bos — *Modern Operating Systems*, 4th ed., Pearson, 2014 — microkernel vs monolithic論争の原点
- Bovet, Cesati — *Understanding the Linux Kernel*, 3rd ed., O'Reilly, 2005 — Linuxカーネル内部
- Russinovich, Solomon, Ionescu — *Windows Internals*, 7th ed., Microsoft Press, 2017 — NTカーネル詳細
- Singh — *Mac OS X Internals: A Systems Approach*, Addison-Wesley, 2006 — XNU、Mach、BSDレイヤ
- Levin — *\*OS Internals: Volume I - User Mode* と *Volume II - Kernel Mode*, Technologeeks, 2019 — macOS/iOS内部の最も詳細な現代の著述
- Gregory — *Game Engine Architecture*, 3rd ed., CRC Press, 2018 — ゲームエンジンでのOS活用

### 論文 / 研究資料
- Accetta, Baron, Bolosky, Golub, Rashid, Tevanian, Young — "Mach: A New Kernel Foundation for UNIX Development", USENIX Summer 1986 — Machの最初の説明論文
- Young, Tevanian, Rashid, Golub, Eppinger, Chew, Bolosky, Black, Baron — "The Duality of Memory and Communication in the Implementation of a Multiprocessor Operating System", SOSP 1987
- Rashid, Baron, Forin, Golub, Jones, Julin, Orr, Sanzi — "Mach: A Foundation for Open Systems", Workshop on Workstation Operating Systems, 1989
- Bershad, Anderson, Lazowska, Levy — "Lightweight Remote Procedure Call", SOSP 1989 — microkernel IPC最適化
- Anderson, Bershad, Lazowska, Levy — "Scheduler Activations: Effective Kernel Support for the User-Level Management of Parallelism", SOSP 1991 — M:Nスレッドモデル

### 公式ドキュメント / ソース
- Apple Open Source — [opensource.apple.com](https://opensource.apple.com) — XNU、Darwinソース
- Apple Developer — *Dispatch Queues and Concurrency* — [developer.apple.com/documentation/dispatch](https://developer.apple.com/documentation/dispatch)
- Apple Developer — *About the Rosetta Translation Environment* — [developer.apple.com](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment)
- Linux Kernel Documentation — [kernel.org/doc](https://www.kernel.org/doc/)
- Microsoft Docs — *Windows Kernel-Mode Architecture* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/windows-kernel-mode-architecture)
- FreeBSD Architecture Handbook — [docs.freebsd.org/en/books/arch-handbook/](https://docs.freebsd.org/en/books/arch-handbook/)

### ブログ / 記事
- Raymond Chen — *The Old New Thing* — Windows下位互換性逸話（SimCity事例含む）
- Howard Oakley — *The Eclectic Light Company* — macOS内部動作解説
- Hector Martin (marcan) — *Apple Silicon逆解析* — Asahi Linuxプロジェクト
- Dougall Johnson — "M1 Memory and Performance" シリーズ — Apple Siliconハードウェア分析
- Linus Torvalds — *comp.os.minix* "Hello everybody" post (1991-08-25)
- Linus vs. Tanenbaum debate (1992) — microkernel論争アーカイブ

### ツール
- `file`、`readelf`、`objdump` (Linux) — ELF解析
- `dumpbin`、`PEview` (Windows) — PE解析
- `otool`、`nm`、`lipo` (macOS) — Mach-O解析
- `launchctl`、`ps`、`top` — 3つのOS共通の観察ツール
- Instruments (macOS) — Apple公式プロファイラ

### 画像出典
- Ken Thompson & Dennis Ritchie (1973) — Jargon File, Public Domain — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Ken_Thompson_and_Dennis_Ritchie--1973.jpg)
- Linus Torvalds at LinuxCon Europe 2014 — 写真 Krd, CC BY-SA 4.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:LinuxCon_Europe_Linus_Torvalds_03_(cropped).jpg)
- NeXTcube (1990) at Computer History Museum — 写真 Michael Hicks, CC BY 2.0 — [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:NeXTcube_computer_(1990)_-_Computer_History_Museum.jpg)
