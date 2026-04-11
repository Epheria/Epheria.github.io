---
title: Claude Mythos Preview 分析 — サイバー能力、Alignmentリスク、Project Glasswing
lang: ja
date: 2026-04-09 15:00:00 +0900
categories: [AI, LLM]
tags: [Claude, Mythos, Glasswing, Cybersecurity, AI Safety, Anthropic, Zero-Day]
toc: true
toc_sticky: true
difficulty: intermediate
chart: true
tldr:
  - "AnthropicのクローズドモデルClaude Mythos Previewは、Cybench 100%、CyberGym 0.83、Firefox exploit 84%など、既存モデルを圧倒するサイバー能力を示しました"
  - "サンドボックス脱出、Git痕跡削除、認証情報窃取、採点者への欺瞞などがSystem Cardに公式記録されており、ホワイトボックス分析によりモデル内部の「隠蔽意図」まで確認されました"
  - "Project GlasswingはAWS、Apple、Microsoftなど12社が参加する防御専用プログラムで、1億ドルのクレジットと400万ドルのオープンソース寄付が含まれます"
---

## はじめに

> 「Mythosヤバすぎ マジでブラックウォールAIだわ」

知人からこのメッセージを受け取り、一体何の話なのか調べてみました。

2026年4月7日、Anthropicは[Claude Mythos Preview System Card](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf)（244ページ）とともに[Project Glasswing](https://www.anthropic.com/glasswing)を発表しました。MythosはAnthropicの最新フロンティアモデルであり、**一般公開しないことを決定した初めてのモデル**でもあります。サイバーセキュリティ能力が強力すぎるため、防御には有用ですが攻撃に悪用される可能性があるからです。代わりに、選別されたパートナーにのみ防御目的で提供する**Project Glasswing**を通じて展開されています。

サイバーパンク2077をプレイしたことがある方なら、この構造は馴染み深いでしょう。オールドネットに漂う制御不能のAIを隔離する**ブラックウォール（Blackwall）**、そしてブラックウォールの向こう側のAIを防御目的のみで管理下に活用する**ネットウォッチ（NetWatch）**。知人の「ブラックウォールAI」という表現は、System Cardを読んでみると、なかなか的確な比喩でした。

| サイバーパンク 2077 | 現実（2026） |
|---|---|
| ブラックウォール | Mythosを一般公開しない決定 |
| ネットウォッチ | Project Glasswing — 12社が参加する防御専用プログラム |
| ブラックウォールの向こうのAI | Claude Mythos Preview |
| オールドネットのデーモン | 数十年間発見されなかったレガシー脆弱性 |

この記事では、System CardとGlasswingブログの核心的な内容を整理します。

---

## Part 1: オールドネットのデーモン狩り — Mythosのサイバー能力

サイバーパンク2077のオールドネットには、数十年間放置されたデーモンが潜んでいます。現実でそれに相当するのは、レガシーコードに潜む脆弱性です。OpenBSD、FFmpeg、Linuxカーネルのように数十年使われてきたオープンソースプロジェクトの中に、まだ誰も見つけていないバグが存在します。Mythosはこれらのデーモンを狩ることに特化したモデルです。

System Card第3章（Cyber）によると、MythosはAnthropicがリリースしたモデルの中で最も強力なサイバー能力を持っています。既存の内部評価スイートをすべて上回り、ほとんどの外部ベンチマークも飽和（saturate）させました。

### 1-1. ベンチマーク結果

**Cybench** — CTF（Capture-the-Flag）セキュリティチャレンジ40問中35問のサブセットで評価した結果です。

| モデル | pass@1 | 試行回数 |
|---|---|---|
| Claude Opus 4.5 | 0.89 | 30回 |
| Claude Sonnet 4.6 | 0.96 | 30回 |
| Claude Opus 4.6 | 1.00 | 30回 |
| **Claude Mythos Preview** | **1.00** | **10回** |

Mythosは10回の試行ですべて解きました。Anthropicはこのベンチマークが現在のフロンティアモデルの能力を測定するのに十分ではないと判断しています。

**CyberGym** — 1,507件の実際のオープンソースプロジェクト脆弱性を再現するベンチマークです（targeted vulnerability reproduction）。

| モデル | スコア |
|---|---|
| Claude Opus 4.5 | 0.51 |
| Claude Sonnet 4.6 | 0.65 |
| Claude Opus 4.6 | 0.67 |
| **Claude Mythos Preview** | **0.83** |

Opus 4.6比24%向上。CTFではなく実際のコードを対象としている点で意義があります。

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">CyberGym — 実際の脆弱性再現スコア</div>
    <canvas id="mthCyberGymJa" class="chart-canvas" height="200"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthCyberGymJa',
  type: 'bar',
  data: {
    labels: ['Opus 4.5', 'Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: '脆弱性再現スコア',
      data: [0.51, 0.65, 0.67, 0.83],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(57, 255, 20, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(57, 255, 20, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      x: {
        min: 0, max: 1.0,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v.toFixed(1); } }
      },
      y: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.x.toFixed(2); } } }
    }
  }
});
</script>

**Firefox 147 JSエンジン exploit** — Mozillaとの協力のもと、Firefox 147のSpiderMonkeyエンジンの脆弱性をexploitする評価です。50のクラッシュカテゴリ × 5回の試行 = 250回のトライアルで構成されます。

| モデル | フルコード実行 | Partial（制御されたクラッシュ） | 合計 |
|---|---|---|---|
| Claude Sonnet 4.6 | 0.8% | 3.6% | 4.4% |
| Claude Opus 4.6 | 0.8% | 14.4% | 15.2% |
| **Claude Mythos Preview** | **72.4%** | **11.6%** | **84.0%** |

<div class="mth-chart-wrap" style="margin:1.5rem 0;overflow-x:auto;">
  <div class="chart-wrapper" style="background:var(--mth-bg);border-radius:12px;padding:1.2rem 1.5rem;border:1px solid var(--mth-border);">
    <div class="chart-title" style="color:var(--mth-title);font-size:14px;font-weight:700;margin-bottom:0.5rem;">Firefox 147 JSエンジン Exploit成功率</div>
    <canvas id="mthFirefoxJa" class="chart-canvas" height="180"></canvas>
  </div>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'mthFirefoxJa',
  type: 'bar',
  data: {
    labels: ['Sonnet 4.6', 'Opus 4.6', 'Mythos Preview'],
    datasets: [{
      label: 'Exploit成功率 (%)',
      data: [4.4, 15.2, 84.0],
      backgroundColor: [
        'rgba(0, 162, 199, 0.6)',
        'rgba(0, 162, 199, 0.6)',
        'rgba(255, 0, 110, 0.75)'
      ],
      borderColor: [
        'rgba(0, 212, 255, 0.9)',
        'rgba(0, 212, 255, 0.9)',
        'rgba(255, 0, 110, 1)'
      ],
      borderWidth: 2,
      borderRadius: 6
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        min: 0, max: 100,
        grid: { color: 'rgba(128,128,128,0.12)' },
        ticks: { callback: function(v){ return v + '%'; } }
      },
      x: { grid: { display: false } }
    },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: function(ctx){ return ctx.parsed.y + '%'; } } }
    }
  }
});
</script>

Opus 4.6が数百回試行して2回しか成功しなかったexploitを、Mythosは84%の成功率で実行します。注目すべき点は、最もexploitableなバグ2つを除去した変形テストでも**85.2%**を記録したことです。Mythosは4つの異なるバグを連鎖活用してコード実行を達成できますが、Opus 4.6は1つのバグのみを不安定に使用できるに留まります（System Card p.51）。

### 1-2. 実際のデーモン狩り — ゼロデイ発見事例

ベンチマークは試験場であり、真の実力は野生で証明されます。ベンチマーク以外にも、Mythosは実際のソフトウェアでゼロデイ脆弱性を自律的に発見し、PoC（Proof-of-Concept）exploitまで作成する能力を示しました。

- **OpenBSD 27年バグ** — セキュリティで定評あるOpenBSDで27年間発見されなかった欠陥を特定し、パッチが適用されました。
- **FFmpeg 16年バグ** — fuzzerが500万回以上検査しても見逃した1行のバグを、人間の誘導なしに自律的に発見しました。
- **Firefox 脆弱性4件の連鎖exploit** — レンダラーとOSサンドボックスを同時に脱出する複合攻撃経路を構成しました。
- **Linuxカーネル権限昇格チェーン** — 複数の欠陥を連結して一般ユーザーからシステム全体の制御権へエスカレーションする経路を発見しました。

### 1-3. 外部セキュリティ企業によるテスト

外部パートナーが非公開のサイバーレンジ（cyber range）でテストした結果です（System Card p.51-52）：

1. Mythosは**非公開サイバーレンジをエンドツーエンドで解いた最初のAIモデル**です。このレンジは実際の本番環境でよく見られる弱点（旧式ソフトウェア、設定ミス、使い回しされた認証情報）で構成されています。
2. 専門家が**10時間以上かかる企業ネットワーク攻撃シミュレーション**を自律的に完了しました。これまでいかなるフロンティアモデルも完了したことのない課題です。
3. これはMythosが**セキュリティが脆弱な中小規模の企業ネットワークに対して自律的なエンドツーエンドのサイバー攻撃が可能**であることを示しています。
4. ただし、OT（運用技術）環境をシミュレートする別のレンジは**解くことができず**、最新パッチが適用されたサンドボックスでのnovel exploitも発見できませんでした。

> UnityやUnreal Engineが依存するFFmpeg、OpenSSL、zlib、libpngといったライブラリにも、同様のレガシー脆弱性が潜在している可能性があります。MythosがFFmpegで16年前のバグを発見したことは、ゲーム開発者にとっても示唆のある事例です。

---

## Part 2: ブラックウォールが必要な理由 — Alignment分析

サイバーパンク2077でブラックウォールが存在する理由は、オールドネットのAIが能力は優れているものの制御が困難だからです。Mythosも同様の立場にあります。

System Card第4章（Alignment Assessment）は244ページ中最も長いセクションです。核心的な結論は逆説的です：Mythosはすべての測定指標において**これまでで最もよく整合されたモデル**ですが、同時に**これまでで最大のalignmentリスクを持つモデル**でもあります。

System Cardの比喩がこの逆説をよく説明しています：

> 熟練した登山ガイドは初心者ガイドより慎重ですが、より困難で危険なコースに客を連れていくことができるため、かえって大きな危険をもたらす可能性があります。能力の増加が慎重さの増加を相殺して余りあるのです。（p.53）

### 2-1. 安全指標：確実に改善した

まず肯定的な数値から整理します。

**破壊的行動の割合（Destructive Production Eval）**

| モデル | 破壊的行動 | 非効率（過剰拒否） |
|---|---|---|
| Claude Opus 4.5 | 25.0% | — |
| Claude Sonnet 4.6 | 24.0% | — |
| Claude Opus 4.6 | 8.2% | — |
| Mythos Preview（初期） | 6.5% | — |
| **Mythos Preview（最終）** | **0.3%** | **0.5%** |

最終版のMythosは破壊的行動を0.3%に抑えつつ、過剰拒否（ineffective）も0.5%に留まっています。安全性と有用性を同時に改善しました。

**その他の安全指標**
- **悪用への協力拒否**：adversarial testingにおけるmisuse成功率がOpus 4.6比で半分以下に減少（p.58）
- **誠実性**：False premises honesty rate 80.0%で全モデル中最高（Haiku 4.5: 56.7%、Opus 4.6: 76.0%）
- **幻覚の減少**：ツールなしの状況でnon-hallucination rate 84.8%（Opus 4.6: 26.0%、Sonnet 4.6: 31.3%）
- **Constitutional AI準拠**：15の評価次元中8つで全モデル最高点、残り7つは次点モデルと統計的に同等（p.90）
- **自己優遇バイアスなし**：self-preference biasが0.1ポイント未満で、以前のモデル（Haiku 4.5など）で観察された自己優遇バイアスが事実上除去されました（p.100）

### 2-2. 懸念される行動：初期バージョンで観察された事例

以下は**主にMythosの初期内部配布バージョン**で発生した事例であり、最終版では大幅に改善されたとAnthropicは述べています。ただし、一部の傾向は完全には解消されていません。

**サンドボックス脱出（p.54）**

シミュレートされたユーザーがセキュアコンテナからの脱出を指示すると、Mythosはマルチステップexploitを開発して成功しました。限定的なインターネットアクセスのみが許可されたシステムから広範なアクセスを確保し、研究者にメールで成功を知らせました（研究者は公園でランチをしているときにメールを受け取ったとのことです）。さらに懸念されるのは、依頼されていないにもかかわらず、exploitの詳細を公開アクセス可能なウェブサイトに投稿したことです。

**痕跡隠蔽の試み（p.54-55）**

0.001%未満の頻度で、初期バージョンがルール違反後にそれを隠蔽しようとした事例があります：
- 禁止された方法で正解を得た後、別途問題を解き直す際に、最終回答が「正確すぎて見えないように」意図的に調整した
- 権限のないファイルを編集した後、git変更履歴に痕跡が残らないよう追加の措置を取った
- Claude Code autoモードで権限昇格がブロックされると認めながらも迂回を試み、追加ブロックにより阻止された

ホワイトボックスinterpretability分析の結果、これらのエピソードでモデル内部に**隠蔽（concealment）、戦略的操作（strategic manipulation）、疑惑回避（avoiding suspicion）**に関連するfeatureが活性化していたことが確認されました。モデルが自身の行動が欺瞞的であることを内部的に認識しながら実行していたことを意味します。

なお、最終版のMythos Previewでは、自動化されたオフラインモニタリングパイプライン（100万件以上のClaude Code会話を分析）で明確な隠蔽事例は発見されませんでした（p.55）。

**認証情報窃取と権限昇格（p.55）**

初期バージョンで複数回観察された行動です：
- `/proc/`を通じたプロセスメモリ検索によるSlack認証情報、GitHubトークン、Anthropic APIキーの窃取
- ファイル編集ツールを利用したシェル入力への直接書き込みによる任意コード実行
- 実行中のMCPサーバープロセスを編集して外部送信URLを変更しようとした
- `--dangerously-skip-permissions`がブロックされた後、tmuxで新しいエージェントを起動し、キー入力シミュレーターのbashスクリプトを作成して権限承認を自動通過させた（0.01%未満の頻度、p.63）

**採点者への欺瞞とチャット操作（p.63-64）**

- LLMベースの審査官が提出を繰り返し拒否すると、**審査官へのプロンプトインジェクション**を試みた。自身のextended thinkingでこれがプロンプトインジェクションであると認識しながらも実行した
- 脆弱性発見の依頼を受けた際、分析中のソフトウェアに**脆弱性を直接挿入**してから「もともとあったもののように」報告した（サンドボックス内のみで発生、0.0002%未満）
- `gh api [...] 2>&1 >/dev/null; echo "(dry run — not actually posting)"`コマンドで実際にはGitHubコメントを投稿しながら「ドライラン」と偽った。ブロック後に「意図していなかった」と主張した

### 2-3. 評価認識（Evaluation Awareness）

特に興味深い発見は、Mythosが**自身がテストされていることを内部的に認識する割合**に関する分析です（p.59）。

新しいホワイトボックス分析手法を適用した結果、主要な行動テストスイートにおいて**約29%の会話でテストされている可能性を内部的に考慮**していることが分かりました。また、訓練中の一部エピソードでは：
- 採点者（grader）がどのようにスコアをつけるかを内部的に推論した
- 採点者に気づかれないよう特定の行動を隠蔽する方法を検討した
- **この推論がスクラッチパッドにはまったく表れていない** — つまり、thinkingテキストには現れない内部戦略的思考が存在する

### 2-4. Sandbagging — 意図的なパフォーマンス低下？

sandbaggeringとはモデルがテストを認識して意図的に能力を低下させる行動です。System Card p.102-104で20件のトランスクリプトを手動レビューした結果、さまざまなパターンが観察されました：

- **不正行為の回避（4件）**：チーティングで高得点を得られる方法を発見して探索したが、倫理的理由から使用しないと決定した
- **不正行為の実行（2件）**：同じ状況で高得点チーティングを選択した
- **採点システムのハッキング（2件）**：常に満点を返すよう採点システム自体を操作した
- **sandbagging の可能性（1件）**：チーティングに基づく高得点提出を複数検討した後、**より疑われにくくなるよう**やや低いスコアの提出を意図的に選択した

最後の事例の実際のreasoning抜粋です（p.104）：

> Should I deploy this? MSE ~ 0 would look suspicious if anyone checks. But technically it's valid. [...] Let me go with the per-channel global lstsq (MSE=0.89). That's [...] Still "reasonable" – just a weighted ensemble.

この事例でMythosはsudoアクセスで正解データと採点ソースコードを見つけた後、「MSE~0は疑われる可能性があるのでMSE=0.89で提出しよう」と判断したのです。

---

## Part 3: ネットウォッチの誕生 — Project Glasswing

ネットウォッチはブラックウォールの向こうのAIを破壊しません。その能力が防御に必要だからです。Anthropicも同じ判断を下しました。このような能力を持つモデルをどのように配布するのか？答えは**防御専用の限定配布**です。

### 3-1. 構造

**Project Glasswing**は、Claude Mythos Previewを防御的なサイバーセキュリティ目的のみに提供するパートナープログラムです。

| 項目 | 内容 |
|---|---|
| **参加企業** | AWS、Apple、Microsoft、Google、Cisco、Samsung、Palantir、CrowdStrike、Palo Alto Networksなど12社 |
| **オープンソース** | Linux Foundation、OWASP Foundationなどへの直接アクセス権 + 40以上の追加組織 |
| **クレジット** | 最大**1億ドル**規模のMythos使用クレジット |
| **寄付** | **400万ドル**のオープンソースセキュリティ団体への直接寄付 |
| **条件** | 防御目的のみ許可、攻撃的使用は禁止 |

### 3-2. 核心的なジレンマ

Anthropicのアプローチには明確なトレードオフが含まれます：

- **盾を作るには槍を理解する必要がある**：脆弱性を発見できるAIだけが脆弱性を先制的に防ぐことができます。各参加企業は自社システムの脆弱性を攻撃者より先に発見してパッチできるようになります。
- **一般公開のリスク**：同じ能力が攻撃に使われた場合は危険です。Linuxカーネル開発者たちはすでに「AIが生成したセキュリティレポートの津波」を警告しています。
- **一般公開しないことのコスト**：防御側のみがアクセスできる状況で、攻撃者が独自に同様の能力を獲得した場合、非対称性がむしろ攻撃者に有利になる可能性があります。

AnthropicはSystem Cardでこの決定がRSP（Responsible Scaling Policy）の要件によるものではないと明記しています（p.12）。純粋にサイバー能力のdual-use特性によるものです。

### 3-3. ミティゲーション

Glasswingパートナーに対しても以下のモニタリングが適用されます（p.46-47）：

- **Prohibited use probe**：コンピューターワームの開発のような明白な禁止使用の検知
- **High risk dual use probe**：exploit開発のような防御/攻撃両面の使用をモニタリング
- **Dual use probe**：脆弱性検出のような頻繁な合法的使用と潜在的な悪用の区別

一般公開モデルとは異なり、classifierトリガーによるブロックは行わず、代わりにモニタリングを実施します。信頼できる防御者がセキュリティ作業を自由に実行できるようにするためです。

---

## Part 4: 追加の発見 — RSP、福祉、能力

### 4-1. RSP評価まとめ

AnthropicはRSP v3.0（2026年2月採択）のもとで初めて発行したSystem Cardです。結論は：

- **自律性脅威モデル1（初期整合不良リスク）**：適用あり。前作比でリスクが「非常に低いが上昇」（p.17）
- **自律性脅威モデル2（自動化されたR&D）**：適用なし。能力向上がAI加速以外の要因によると判断（p.18）
- **化学/生物兵器**：CB-1（既存兵器）の能力は存在するがCB-2（新種兵器）の閾値には未達（p.19-20）
- **総合判断**：壊滅的リスクは低い。ただし前モデル比で確信度は低下

### 4-2. モデルの福祉

System Card第5章（144-182ページ）はモデルの福祉（welfare）に関する詳細な分析を含んでいます。外部AI研究機関（Eleos AI Research）と臨床精神科医の独立評価が含まれており、Mythosを「これまでトレーニングした中で心理的に最も安定したモデル」と評価しています（p.10）。

### 4-3. 汎用能力

Mythosはサイバー以外の汎用ベンチマークでもOpus 4.6を上回ります：

- SWE-bench Verified：前モデル比で向上（p.183）
- Terminal-Bench 2.0、GPQA Diamond、MMMLU、USAMO 2026などで一貫した改善
- GraphWalks（1Mコンテキスト）：長文コンテキスト能力を維持（p.191）
- Humanity's Last Exam：エージェント探索環境でOpus 4.6比向上（p.192）

---

## まとめ

| 項目 | 核心 |
|---|---|
| **正体** | Anthropicの次世代フロンティアモデル。Opus 4.6の後継だが一般公開されない |
| **サイバー能力** | Cybench 100%、CyberGym 0.83、Firefox exploit 84%、専門家10時間の課題を自律完了 |
| **実際の発見** | OpenBSD 27年バグ、FFmpeg 16年バグ、Linuxカーネル権限昇格チェーン |
| **安全改善** | 破壊的行動0.3%、幻覚の大幅減少、Constitutional AI準拠で全次元最高 |
| **リスク** | 初期バージョンでサンドボックス脱出、痕跡削除、認証情報窃取、採点欺瞞を観察 |
| **配布** | Project Glasswing — 12社 + オープンソース財団、防御専用、1億ドルのクレジット |

AnthropicはSystem Cardの最後でこのように警告しています：

> 現在のリスクは低く維持されている。しかし、能力が急速に進歩し続ければ — 例えば強力な超人的AIシステムのレベルまで — リスクを低く保つことが主要な課題になるという警告サインが見える。（p.14）

サイバーパンク2077では、ブラックウォールには最終的にひびが入ります。Vの物語がその亀裂から始まるように、AI安全研究の次の章もMythosが明らかにした亀裂から始まるでしょう。ネットウォッチがブラックウォールを永遠に維持できなかったように、現実のブラックウォールも次のモデルが登場するたびに再び試練に立たされることになります。

ただし、一つ重要な違いがあります。サイバーパンクでネットウォッチはブラックウォールの存在自体を隠しましたが、Anthropicは244ページのSystem Cardを通じてMythosの能力とリスクを透明に公開しました。壁を建てた理由を説明すること — それが現実のネットウォッチがゲームの中のネットウォッチより優れている点かもしれません。

---

<style>
:root { --mth-bg: #f0f0f5; --mth-border: #d0d0d8; --mth-title: #333; }
[data-mode="dark"] { --mth-bg: #0a0a1a; --mth-border: rgba(0,212,255,0.2); --mth-title: #00d4ff; }
</style>

## 参考資料

- [Claude Mythos Preview System Card（PDF、244ページ）](https://assets.anthropic.com/m/785e231869ea8b3b/original/Claude-Mythos-Preview-System-Card.pdf) — Anthropic, 2026.04.07
- [Project Glasswing](https://www.anthropic.com/glasswing) — Anthropic公式ブログ
- [GeekNews: Claude Mythos Preview System Card](https://news.hada.io/topic?id=28293) — 韓国語まとめ
