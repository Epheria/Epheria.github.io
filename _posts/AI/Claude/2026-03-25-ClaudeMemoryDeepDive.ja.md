---
title: "Claudeの記憶システム徹底解析 — Auto Memory、Auto Dream、そしてSleep-time Compute"
lang: ja
date: 2026-03-25 11:00:00 +0900
categories: [AI, Claude]
tags: [Claude, Claude Code, Memory, Auto Memory, Auto Dream, Sleep-time Compute, LLM, AI Agent, CLAUDE.md, Memory Architecture]

difficulty: advanced
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeMemoryAndCodeSkills/
  - /posts/ClaudeCodeInsights/
tldr:
  - "Claude Codeのメモリは、CLAUDE.md（明示的ルール）+ Auto Memory（自動学習）+ Auto Dream（睡眠整理）の3段階に進化し、人間の「書く→寝る→整理する→記憶する」サイクルを模倣している"
  - "Auto Dreamは、Sleep-time Compute論文（2025年）の理論的根拠に基づいて設計されている — ユーザーの質問前に事前計算すれば、テスト時の計算量を約5倍削減できる"
  - "最新の研究（2025〜2026年）は、エージェントメモリを事実的（Factual）・経験的（Experiential）・作業（Working）メモリに分類し、形成→進化→検索のライフサイクルで管理する"
---

## はじめに

AIエージェントが単一の対話を超えて**長期的に学習し記憶する**能力は、2025〜2026年のAI研究の核心テーマである。Claude Codeはこの分野で最も積極的に実験しているプロダクトの一つであり、最近コードから発見された未公開機能**Auto Dream**は、その方向性を鮮明に示している。

本記事では、3つの軸でClaudeの記憶システムを解剖する：

1. **プロダクトレベル**：Claude Codeのメモリアーキテクチャ（CLAUDE.md → Auto Memory → Auto Dream）
2. **理論レベル**：Sleep-time Compute論文が提示する「睡眠中の事前計算」パラダイム
3. **研究レベル**：2025〜2026年のエージェントメモリ分類体系と最新サーベイ論文

---

## 1. Claude Codeメモリアーキテクチャの全体像

### 1-1. 3層メモリシステム

Claude Codeのメモリは、**誰が書くか**と**いつロードされるか**によって3層に分かれる。

| 層 | 作成者 | 内容 | ロード時点 | スコープ |
|----|--------|------|-----------|---------|
| **CLAUDE.md** | ユーザー | 明示的ルール・規約 | 毎セッション開始時（全体） | プロジェクト/ユーザー/組織 |
| **Auto Memory** | Claude | 学習したパターン・好み | 毎セッション開始時（200行） | gitリポジトリ単位 |
| **Auto Dream** | Claude（バックグラウンド） | 整理された記憶 | 条件充足時に自動 | gitリポジトリ単位 |

#### CLAUDE.md — 宣言的ルールの階層構造

CLAUDE.mdはプロジェクトレベルの指示ファイルである。最も狭いスコープ（プロジェクト）が最も広いスコープ（組織）よりも優先される。

```
優先順位（高→低）：
1. Managed Policy — /Library/Application Support/ClaudeCode/CLAUDE.md（IT管理者）
2. Project       — ./CLAUDE.md または ./.claude/CLAUDE.md（チーム共有）
3. User          — ~/.claude/CLAUDE.md（個人グローバル）
```

**効果的なCLAUDE.mdの条件：**
- **200行以下**でルール遵守率92%以上、400行を超えると71%に急落
- 曖昧な指示（「コードをきれいに」）より検証可能な指示（「2スペースインデント使用」）が効果的
- `.claude/rules/`ディレクトリでモジュール化し、globパターンで条件付きロードが可能

#### Auto Memory — Claudeが自分で書くノート

Auto Memoryは、ユーザーが何も書かなくても、Claudeがセッション中に発見したパターンを自動的に記録するシステムである。

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # インデックス（毎セッション200行ロード）
├── debugging.md       # デバッグパターン
├── api-conventions.md # API設計決定
└── ...                # Claudeが自由に作成
```

**動作原理：**
1. セッション開始時に`MEMORY.md`の最初の200行をコンテキストに注入
2. 対話中にユーザーの修正、好み、繰り返しパターンを検出
3. 「この情報は将来の対話で有用か？」を判断して選択的に保存
4. 詳細内容はトピックファイルに分離、`MEMORY.md`はインデックスのみ維持

### 1-2. Auto Memoryの根本的問題

Auto Memoryは強力だが、**時間が経つと混乱に陥る。**

20以上のセッションが蓄積すると：
- **矛盾した項目**が累積する（「pnpm使用」vs「npm使用」）
- **相対日付**が意味を失う（「昨日修正したバグ」が3ヶ月前の記録）
- **一時的メモと本質的学習**が同じレベルで保存される
- **200行制限**内で重要度の競争が発生

これは単純な実装バグではなく、**書くだけで整理しないシステム**の構造的限界である。

---

## 2. Auto Dream — 「眠っている間に記憶を整理する」AI

### 2-1. 発見の経緯

Auto Dreamは2026年3月、日本の開発者灯里（akari）がClaude Codeの`/memory`コマンドで発見した**未公開機能**である。UIに表示されるが有効化できない — サーバー側のフィーチャーフラグで制御されている。

```
コードネーム：tengu_onyx_plover
デフォルト設定：
  enabled: false
  minHours: 24        # 最低24時間間隔
  minSessions: 5      # 5セッション蓄積後に実行
```

このデュアルゲート設計は意図的である — 軽い使用ではトリガーされず、活発な開発プロジェクトでのみ定期的に整理が実行される。

### 2-2. Auto Dreamの4段階プロセス

Auto Dreamは**人間のREM睡眠**に例えられる。覚醒中（セッション）に収集した情報を、睡眠中（バックグラウンド）に整理・統合する。

**Phase 1 — Orientation（方向設定）**

メモリディレクトリをスキャンし、現在の状態を把握する。どのトピックファイルがあるか、`MEMORY.md`の現在のサイズ、最後の整理からどれくらい経過したかを確認する。

**Phase 2 — Gather Signal（信号収集）**

セッショントランスクリプトから重要な情報を選択的に抽出する。全ファイルを読まず、**狭い範囲のgrep検索**を実行：
- ユーザーの修正事項（「いや、そうじゃなくて…」）
- 明示的な保存コマンド（「これを覚えて」）
- 繰り返されるテーマとパターン
- 重要な技術的決定

**Phase 3 — Consolidation（統合）**

新しい情報を既存ファイルにマージしながら：
- 相対日付（「昨日」）を絶対日付（「2026-03-24」）に変換
- 矛盾する事実の中で最新のものだけを保持
- 古くなって有効でないメモリを削除
- 重複項目を一つに統合

**Phase 4 — Prune and Index（整理とインデックス）**

`MEMORY.md`インデックスを200行以下に維持しながら最新状態に更新する。

### 2-3. Auto Memory + Auto Dream = 記憶の完成

```
  Auto Memory（覚醒時）              Auto Dream（睡眠時）
  ┌─────────────────────┐         ┌─────────────────────┐
  │  経験を収集          │         │  信号を抽出          │
  │  パターンを検出       │  ───▶   │  矛盾を解決          │
  │  ノートを作成         │         │  統合・整理           │
  │  トピックファイル分離  │         │  インデックス更新      │
  └─────────────────────┘         └─────────────────────┘
           ↑                                │
           └────────────────────────────────┘
                    次のセッションに反映
```

このサイクルは、人間の**「経験→睡眠→記憶強化」**パターンを直接的に模倣している。神経科学では、睡眠中に海馬が昼間の経験を再生（replay）し、大脳皮質に転移するプロセスを**記憶固定化（memory consolidation）**と呼ぶが、Auto Dreamはまさにこの役割を果たす。

### 2-4. なぜまだリリースされていないのか？

技術的には即座にリリース可能だが、3つのビジネス判断が残っている：

1. **コスト**：ユーザーが要求していないサブエージェントがバックグラウンドでトークンを消費する
2. **透明性**：ユーザーに知らせずメモリを再構成することへの信頼の問題
3. **デフォルト**：opt-in vs opt-out、どちらが正しいデフォルト動作か？

---

## 3. 理論的基盤 — Sleep-time Compute

### 3-1. 論文概要

Auto Dreamの理論的根拠は、2025年4月に発表された**「Sleep-time Compute: Beyond Inference Scaling at Test-time」**論文である。

> **著者**：Kevin Lin, Charlie Snell, Yu Wang, Charles Packer, Sarah Wooders, Ion Stoica, Joseph E. Gonzalez
> **arXiv**：[2504.13171](https://arxiv.org/abs/2504.13171)
> **核心アイデア**：ユーザーが質問する**前に**事前計算しておけば、実際の推論時に必要な計算量を大幅に削減できる。

![Sleep-time Compute概念図](/assets/img/post/AI/memory-deep-dive/sleep-time-concept.png)
_Figure 1：Sleep-time computeは元のコンテキストを事前処理し、将来のクエリに有用な追加計算を実行する。（Lin et al., 2025）_

### 3-2. 主要結果

論文は2つの修正された推論タスク（Stateful GSM-Symbolic, Stateful AIME）で印象的な効率改善を実証している。

![Sleep-time vs Test-time accuracy tradeoff](/assets/img/post/AI/memory-deep-dive/sleep-time-accuracy.png)
_Figure 3：Stateful GSM-Symbolicにおけるテスト時計算量 vs 精度のトレードオフ。陰影部分がsleep-time computeがパレート最適境界を改善する区間。_

**主要な数値：**
- **テスト時計算量を約5倍削減**：同じ精度を達成するために必要な推論時間の計算量を約1/5に
- **精度最大13%向上**：sleep-time computeを拡張すると、従来方式より最大13ポイント高い精度を達成
- **クエリ当たり平均コスト2.5倍削減**：同じコンテキストに対する複数クエリを共有するとコスト削減

![クエリ共有によるコスト削減](/assets/img/post/AI/memory-deep-dive/sleep-time-amortize.png)
_Figure 9：Multi-Query GSM-Symbolicで、コンテキスト当たりの質問数が増加するほど、sleep-time computeのコスト-精度パレートが改善される。_

### 3-3. 予測可能性と効果の相関

特に興味深い発見は、**ユーザーの質問がコンテキストから予測可能であるほど、sleep-time computeの効果が大きくなる**という点である。

![予測可能性とsleep-time効果](/assets/img/post/AI/memory-deep-dive/sleep-time-predictability.png)
_Figure 10：質問の予測可能性が高いほど、sleep-time computeと標準推論のパフォーマンス差が広がる。_

これがAuto Dreamに示唆するところは明確である：

- 開発プロジェクトで繰り返されるパターン（ビルドコマンド、コーディングスタイル、アーキテクチャ決定）は**高い予測可能性**を持つ
- したがって、これらのパターンを事前に整理しておけば、次のセッションでClaudeはより少ないトークンでより正確な応答を生成できる
- Auto Dreamは結局、**開発コンテキストに特化したsleep-time compute**である

### 3-4. 実際のソフトウェアエンジニアリングへの適用

論文はSWE-Featuresという実際のソフトウェアエンジニアリングタスクでも検証している。

![SWE-Features結果](/assets/img/post/AI/memory-deep-dive/sleep-time-swe.png)
_Figure 11：SWE-Featuresで低テスト時間予算において、sleep-time computeが標準方式より高いF1スコアを示す。_

---

## 4. 学術的文脈 — エージェントメモリ研究の現在

Claudeのメモリシステムは、より広い学術研究の流れの中に位置する。2025〜2026年に発表された主要なサーベイ論文を通じてこの文脈を理解しよう。

### 4-1. 人間の記憶→AIメモリへのマッピング

**「From Human Memory to AI Memory」**（Wu et al., 2025）は、人間の記憶分類体系をAIメモリシステムにマッピングするフレームワークを提案した。

![人間の記憶とAIメモリの対応関係](/assets/img/post/AI/memory-deep-dive/human-ai-memory.png)
_Figure 1：人間の記憶（感覚記憶、作業記憶、明示的/暗黙的記憶）とLLMベースAIシステムメモリの対応関係。（Wu et al., 2025）_

この論文は**3次元（対象・形態・時間）と8つの象限**でメモリを分類する：

| 次元 | 説明 | 例 |
|------|------|-----|
| **対象（Object）** | 誰のメモリか | 個人 vs 集団 |
| **形態（Form）** | どんな形で保存されるか | テキスト、ベクトル、パラメータ |
| **時間（Time）** | どれくらい持続するか | 短期 vs 長期 |

Claude Codeに当てはめると：
- **CLAUDE.md** = 明示的長期記憶（ユーザーが宣言したルール）
- **Auto Memory** = 暗黙的長期記憶（経験から自動抽出）
- **コンテキストウィンドウ** = 作業記憶（現在のセッション）
- **Auto Dream** = 記憶固定化（睡眠中の整理）

### 4-2. AIエージェント時代のメモリ分類体系

**「Memory in the Age of AI Agents」**（Hu, Liu et al., 2025/2026）は、47名の著者が参加した大規模サーベイで、従来の単純な「長期/短期メモリ」分類を超える新しい体系を提案している。

> **arXiv**：[2512.13564](https://arxiv.org/abs/2512.13564)（2025年12月、v2：2026年1月）

#### エージェントメモリ vs 関連概念

まずこの論文は、エージェントメモリをLLMメモリ、RAG、コンテキストエンジニアリングと区別する。

![エージェントメモリ概念比較](/assets/img/post/AI/memory-deep-dive/agent-memory-concept.png)
_Figure 1：エージェントメモリとLLMメモリ、RAG、コンテキストエンジニアリングの概念的比較。（Hu et al., 2025）_

#### 形態（Forms）次元 — メモリの物理的構造

エージェントメモリの物理的形態は3種類に分類される。

![メモリ形態比較](/assets/img/post/AI/memory-deep-dive/agent-memory-forms.png)
_Figure 4：トークンレベル、パラメトリック、潜在的（Latent）メモリの3形態比較。_

**トークンレベルメモリ**は最も直感的な形態で、情報をテキストトークンとして保存する。位相的複雑度によって細分化される：

![トークンレベルメモリの位相的分類](/assets/img/post/AI/memory-deep-dive/agent-memory-token-level.png)
_Figure 2：トークンレベルメモリの位相的分類 — 平面（1D）、平面型（2Dグラフ/ツリー）、階層型（3D多層構造）。_

| 形態 | 構造 | 例 | Claude Code対応 |
|------|------|-----|---------------|
| **Flat（1D）** | 線形シーケンス | 単純テキストログ | `MEMORY.md`項目列挙 |
| **Planar（2D）** | ツリー/グラフ | 知識グラフ | トピックファイル間参照 |
| **Hierarchical（3D）** | 多層構造 | ピラミッドメモリ | `MEMORY.md`→トピックファイル階層 |

**パラメトリックメモリ**はモデルの重み自体に情報をエンコードする方式である。Fine-tuningやLoRAが代表的。Claude Codeでは使用しない。

**潜在的（Latent）メモリ**は隠れ状態やKVキャッシュに情報を保存する方式である。Anthropicのプロンプトキャッシュがこのカテゴリに近い。

#### 機能（Functions）次元 — メモリの認知的役割

![機能的分類体系](/assets/img/post/AI/memory-deep-dive/agent-memory-taxonomy.png)
_Figure 6：エージェントメモリの機能的分類 — 事実的（Factual）、経験的（Experiential）、作業（Working）メモリ。_

**事実的メモリ（Factual Memory）**

エージェントの宣言的知識基盤である。2つのサブタイプに分かれる：
- **ユーザー事実メモリ**：ユーザーとのインタラクションで一貫性を維持するための情報（「このプロジェクトはpnpmを使用する」）
- **環境事実メモリ**：外部世界の知識との一貫性保証（「Node.js 20でこのAPIがdeprecatedになった」）

Claude Codeでは**CLAUDE.md**が事実的メモリの主要な保存先である。

**経験的メモリ（Experiential Memory）**

過去の経験から抽出した学習。3つのサブタイプ：
- **ケースベース（Case-based）**：過去のエピソードの記録（「前回のビルドエラーはこう解決した」）
- **戦略ベース（Strategy-based）**：推論パターンの学習（「このプロジェクトでは常にタイプチェックを先に行う」）
- **スキルベース（Skill-based）**：手続き的能力（「テスト→ビルド→デプロイパイプライン」）

Claude Codeでは**Auto Memory**が経験的メモリを担当する。

**作業メモリ（Working Memory）**

容量が限られた活性コンテキスト。現在のセッションで進行中のタスクの状態を維持する。

Claude Codeでは**コンテキストウィンドウ**自体が作業メモリであり、`MEMORY.md`の200行制限は人間の作業記憶の容量制限（ミラーの7±2法則）を連想させる。

#### 動力学（Dynamics）次元 — メモリのライフサイクル

![メモリライフサイクル](/assets/img/post/AI/memory-deep-dive/agent-memory-lifecycle.png)
_Figure 8：エージェントメモリのライフサイクル — 形成（Formation）、進化（Evolution）、検索（Retrieval）。_

| 段階 | 説明 | Claude Code対応 |
|------|------|---------------|
| **形成（Formation）** | 新しい情報をメモリに記録 | Auto Memoryがセッション中にパターン検出・保存 |
| **進化（Evolution）** | 既存メモリの更新・変換・削除 | Auto Dreamが矛盾解決・統合・精製 |
| **検索（Retrieval）** | 必要な時点でメモリにアクセス | セッション開始時200行ロード＋オンデマンドトピックファイル読み込み |

![メモリ進化プロセス](/assets/img/post/AI/memory-deep-dive/agent-memory-evolution.png)
_Figure 7：メモリ進化の詳細メカニズム — 更新、強化、忘却、再構造化。_

### 4-3. Write–Manage–Readループ

**「Memory for Autonomous LLM Agents」**（2026）は、エージェントメモリを**Write–Manage–Readループ**として形式化した。

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Write   │───▶│  Manage  │───▶│   Read   │
│（記録）   │    │（管理）   │    │（検索）   │
└──────────┘    └──────────┘    └──────────┘
     ↑                                │
     └────────────────────────────────┘
              フィードバックループ
```

Claude Codeにこのフレームワークを適用すると：

| 段階 | 実装 | 担当 |
|------|------|------|
| **Write** | セッション中にメモリファイルに記録 | Auto Memory |
| **Manage** | 定期的な整理・統合・精製 | Auto Dream |
| **Read** | セッション開始時200行ロード＋必要時トピックファイルアクセス | Claude Codeランタイム |

---

## 5. Claudeのメモリをより広い文脈で見る

### 5-1. Chat Memory vs Claude Code Memory

Claudeのメモリシステムは、ユーザータイプに応じて異なる層を提供する。

| 層 | 対象 | 動作方式 | 整理周期 |
|----|------|---------|---------|
| **Chat Memory** | 全Claudeユーザー | 対話から自動抽出（Memory Synthesis） | 約24時間 |
| **CLAUDE.md + Auto Memory** | Claude Code開発者 | 明示的ルール＋自動学習 | 手動 / Auto Dream |
| **API Memory Tool** | アプリビルダー | プログラマティックCRUD | アプリロジックに従う |

Chat Memoryは最もシンプルな形態で、約24時間ごとに対話内容から長期的に有用な情報を抽出する**抽出的要約（extractive summarization）**方式である。Claude CodeのAuto Memory + Auto Dreamの組み合わせは、これをはるかに精巧に発展させたものである。

### 5-2. インフラスケジューリングの3層

Auto Dreamの実行インフラも3段階で発展している：

| 層 | スコープ | 持続性 | 例 |
|----|---------|--------|-----|
| **CLI `/loop`** | セッション中のみ有効 | セッション終了時に消滅 | `loop 10m /simplify` |
| **Desktop Scheduled Tasks** | ローカルマシン持続 | マシンシャットダウン時に消滅 | crontabベース |
| **Cloud Scheduled Tasks** | Anthropicインフラ | 常時実行 | サーバーレス実行 |

Auto DreamがCloud Scheduled Tasksに移行すると、**ユーザーのコンピューターが電源オフでも**メモリ整理が進行できる。2026年3月にAnthropicがClaude Partner Networkに1億ドルを投資したことと合致する方向性である。

### 5-3. 競争環境での位置づけ

| 製品 | メモリ形態 | 整理メカニズム | 開発者統合 |
|------|----------|-------------|-----------|
| **Claude Code** | ファイルベース（CLAUDE.md + MEMORY.md） | Auto Dream（予定） | gitリポジトリ単位 |
| **ChatGPT** | サーバー側キーバリュー | 自動要約 | 限定的 |
| **GitHub Copilot** | `.github/copilot-instructions.md` | なし | リポジトリ単位 |
| **Cursor** | `.cursorrules` | なし | プロジェクト単位 |

Claude Codeの差別化ポイントは**整理段階（Auto Dream）の存在**である。他のツールが「書くだけ」のメモリを提供する中、Claude Codeは「書いて、寝て、整理して、記憶する」完全なサイクルの実装を目指している。

---

## 6. 実践：効果的なメモリ管理戦略

### 6-1. CLAUDE.md記述の原則

```markdown
# 良い例：具体的で検証可能
- 2スペースインデント使用
- コミット前に`npm test`実行
- APIハンドラは`src/api/handlers/`に配置

# 悪い例：曖昧で検証不可能
- コードをきれいに書く
- 適切にテストする
- ファイルを整理する
```

### 6-2. Auto Memory活用のコツ

1. **定期的に`/memory`で確認**：Claudeが何を記憶しているか随時チェック
2. **矛盾発見時は即座に修正**：「それはもう正しくない」と言えばClaudeが更新
3. **200行を超えたらトピックファイル分離を誘導**：「メモリを整理して」とリクエスト
4. **機密情報に注意**：APIキー、パスワードなどが保存されないことを確認

### 6-3. Auto Dream対応戦略

Auto Dreamが正式リリースされると、以下が期待できる：

- **自動矛盾解決**：同じ設定に対する相反する記録が最新のものに統合
- **相対日付変換**：「昨日」が絶対日付に自動変換
- **重要度ベースの整理**：一時的メモより繰り返しパターンに高い重み付け
- **手動トリガー**：`/dream`コマンドで大規模リファクタリング後の即時整理が可能

---

## まとめ — AIが夢を見る時代

Claudeのメモリシステム進化を一言でまとめると：

> **「書くだけ（Auto Memory）では不十分。寝て整理してこそ（Auto Dream）、本当の記憶になる。」**

これは単なる機能追加ではなく、LLMエージェントが**人間の認知の根本的メカニズム**を模倣し始めたというシグナルである。Sleep-time Compute論文が理論を提供し、エージェントメモリサーベイが分類体系を提供し、Claude CodeのAuto Dreamがこれをプロダクトとして実装する。

ゲーム開発者としての例えで言えば、NPCのAIが単純なステートマシン（FSM）からビヘイビアツリーへ、さらにユーティリティAIへと進化したのと同じ軌跡である。各段階でエージェントが処理できる状況の複雑さが質的に変わったように、AIの記憶システムも「単純な保存→自動学習→睡眠整理」の軌跡に沿って質的飛躍を準備している。

---

## 参考文献

### 論文
1. Kevin Lin et al., **"Sleep-time Compute: Beyond Inference Scaling at Test-time"**, arXiv:2504.13171, 2025.
2. Yuyang Hu, Shichun Liu et al., **"Memory in the Age of AI Agents: A Survey"**, arXiv:2512.13564, 2025/2026.
3. Yaxiong Wu et al., **"From Human Memory to AI Memory: A Survey on Memory Mechanisms in the Era of LLMs"**, arXiv:2504.15965, 2025.
4. **"Memory for Autonomous LLM Agents"**, arXiv:2603.07670, 2026.
5. **"A Survey on the Memory Mechanism of Large Language Model-based Agents"**, ACM TOIS, 2025.

### 記事・ドキュメント
6. 灯里（akari）, **「Claudeに『いい夢みてね』を言う日がくるかもしれない」**, Zenn, 2026-03-24.
7. Anthropic, **"How Claude remembers your project"**, [Claude Code Docs](https://code.claude.com/docs/en/memory).
8. **"Claude Memory Guide: Understanding the 3-Layer Architecture"**, [ShareUHack](https://www.shareuhack.com/en/posts/claude-memory-feature-guide-2026), 2026.
9. **"Claude Code Auto Dream: Memory Consolidation Feature Explained"**, [ClaudeFast](https://claudefa.st/blog/guide/mechanics/auto-dream).
