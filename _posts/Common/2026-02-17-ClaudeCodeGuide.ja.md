---
title: Claude Code 完全ガイド - インストールから高度な活用戦略まで
date: 2026-02-17 14:00:00 +0900
categories: [Tool, Claude Code]
tags: [claude code, ai, llm, vibe coding, claude, anthropic, cli]
difficulty: intermediate
lang: ja
toc: true
toc_sticky: true
---

<br>

## Claude Codeとは？

**Claude Code** は Anthropic が開発した **エージェント型コーディングツール (Agentic Coding Tool)** です。ターミナル (CLI) で直接実行され、自然言語でのコード作成、リファクタリング、デバッグ、git 操作など、ほぼすべての開発作業を実行できます。

既存の AI コーディングアシスタント (Copilot、Cursor など) との最大の違いは、**プロジェクト全体をコンテキストとして理解**し、ファイルシステムを直接読み書きできる **エージェント (Agent)** である点です。

<br>

---

## I. インストール (macOS 環境)

### 方法 1: Homebrew でインストール (推奨)

| 手順 | コマンド | 説明 |
|:---:|:---|:---|
| **1** | `brew install --cask claude-code` | Homebrew で Claude Code をインストール |
| **2** | `claude --version` | インストール確認とバージョンチェック |

### 方法 2: npm でインストール

| 手順 | コマンド | 説明 |
|:---:|:---|:---|
| **1** | `node --version` | Node.js 18.0 以上か確認 |
| **2** | `npm install -g @anthropic-ai/claude-code` | npm グローバルインストール |
| **3** | `claude --version` | インストール確認 |

> Node.js がない場合は [公式サイト](https://nodejs.org/) から LTS 版をインストールするか、`brew install node` でインストールできます。
{: .prompt-tip }

<br>

---

## II. 初期設定

### 1. ログイン

インストール後、ターミナルでログインします。

```bash
claude login
```

ブラウザが開いたら Anthropic アカウントでログインし、CLI tool タイプを選択します。

### 2. トークン使用量の確認

[https://claude.ai/settings/usage](https://claude.ai/settings/usage) で現在のトークン使用量を確認できます。

> **トークン (Token) とは？** LLM がテキストを処理する最小単位です。英語はおおよそ 1 単語 = 1.3 トークン、韓国語は 1 文字 = 約 2-3 トークンで計算されます。Claude Code は **入力トークン (プロンプト + コンテキスト)** と **出力トークン (応答)** の両方を消費します。
{: .prompt-info }

<br>

---

## III. IDE 連携 (推奨環境)

ターミナル単体でも使えますが、**IDE と連携して使うことを強く推奨**します。変更差分をリアルタイムで確認できるため、効率が大きく向上します。

### VS Code (推奨)

1. [VS Code](https://code.visualstudio.com/) をインストール
2. **Open Folder** でプロジェクトフォルダを開く
3. 上部メニューの **Terminal > New Terminal** を開く
4. ターミナルで `claude` を実行

```bash
# プロジェクトディレクトリで実行
cd /path/to/your/project
claude
```

> Claude Code は起動時にプロジェクトルートの `CLAUDE.md` を自動で読み取り、アーキテクチャ、コーディング規約、作業手順を把握します。そのため要件に対してより正確で関連性の高い応答が可能になります。
{: .prompt-tip }

### JetBrains (Rider、IntelliJ など)

JetBrains IDE の内蔵ターミナルでも `claude` コマンドで同様に実行できます。ただし個人的には VS Code のターミナル UX の方が使いやすいと感じました。

<br>

---

## IV. 主要コマンド完全整理

### セッション管理コマンド

| コマンド | 機能 | 説明 |
|:---|:---|:---|
| `claude` | Claude Code 起動 | 現在のディレクトリで新しいセッション開始 |
| `claude -c` / `claude --continue` | 直近セッション継続 | 最後の会話の続きから開始 |
| `claude -r` / `claude --resume` | 過去会話の再開 | 過去セッション一覧から選択して再開 |
| `claude --verbose` | 詳細ログモード | デバッグ時に有用な詳細ログを出力 |
| `claude --dangerously-skip-permissions` | 権限確認をスキップ | すべてのファイルアクセス/実行を自動許可 (注意) |

### セッション内スラッシュコマンド

| コマンド | 機能 | 詳細説明 |
|:---|:---|:---|
| `/clear` | **コンテキスト初期化** | 新しい会話を開始。**最重要コマンド。** コンテキストウィンドウを十分に確保することでハルシネーションの可能性を下げられます。タスク単位で `/clear` 開始を推奨。 |
| `/compact` | 会話圧縮 | 会話を要約/圧縮してコンテキスト枠を確保します。`/compact 重要ポイント中心` のように対象を指定可能。 |
| `/model` | モデル変更 | Opus、Sonnet などを選択。計画は Opus、実装は Sonnet が効率的。 |
| `/resume` | 過去会話の再開 | 以前の会話を呼び出せます。 |
| `/config` | 設定管理 | verbose、model、todo list など各種設定を調整。 |
| `/memory` | CLAUDE.md 編集 | プロジェクト/グローバル CLAUDE.md を直接編集。 |
| `/init` | プロジェクト初期化 | Claude がプロジェクト全体を分析し CLAUDE.md を自動生成。 |
| `/terminal-setup` | 改行設定 | `Shift+Enter` で改行できるよう設定。 |
| `/plugin` | プラグイン管理 | プラグインの検索、インストール、削除。 |
| `/agents` | エージェント管理 | カスタムエージェントの確認と管理。 |
| `/mcp` | MCP サーバー管理 | Model Context Protocol サーバー設定。 |
| `/statusline` | ステータスライン設定 | ターミナルのステータスライン表示設定。 |
| `/todos` | Todo リスト確認 | 現在の作業一覧を確認。 |
| `/permissions` | 権限管理 | bash コマンドなどの事前許可ルールを設定。 |
| `/insights` | **利用パターン分析** | 直近 30 日のセッションを分析し HTML レポートを生成。利用傾向、ボトルネック、改善提案を提示。 |
| `/fast` | **Fast モード切替** | 高速出力モードを切替。雷アイコン (↯) が表示され、セッション間で維持。 |

### アップデートコマンド

```bash
# Claude Code を更新 (npm インストールの場合)
claude update

# Homebrew でインストールした場合
brew upgrade claude-code
```

### 特殊機能

| 機能 | 使い方 | 説明 |
|:---|:---|:---|
| **ファイル参照** | `@ファイル名` | `@GameHandler.cs` のように `@` を付けると、プロジェクト内ファイルを直接参照できます。 |
| **画像添付** | ドラッグ&ドロップ / `Cmd+Shift+4` 後に貼り付け | スクリーンショットや UI デザインを添付すると視覚コンテキストが得られ、効率が大幅に向上します。公式ドキュメントでも推奨。 |
| **Rewind (巻き戻し)** | `Esc` 2 回 | 現在の会話を停止し、前のチェックポイントに戻します。会話/コード/会話+コードを選択可能。ハルシネーション検知時に有効。 |
| **モード変更** | `Shift+Tab` | Plan モード / Auto-accept モード / 基本モードを切替。 |
| **Thinking 切替** | `Tab` | Extended Thinking (深い推論) モードをオン/オフ。設定はセッション間で維持。 |
| **メモリ追加** | `#` キー | CLAUDE.md に記憶内容を素早く追加 (「このルールを覚えて」用途など)。 |

<br>

---

## V. 最新機能 (v2.1.x、2026年2月時点)

Claude Code v2.1.x で追加された主な機能です。

### 1. `/insights` - 利用パターン分析レポート

`/insights` は直近 30 日のセッションデータを分析し、**インタラクティブな HTML レポート**を生成するコマンドです。

```bash
# Claude Code セッション内で実行
/insights
```

**分析対象:**
- `~/.claude/` に保存されたセッション履歴 (プロンプト + Claude 応答)
- ツール利用パターン、エラーパターン、インタラクションパターン
- ソースコード本体は分析しない (プライバシー保護)

**レポート内容:**

| 項目 | 説明 |
|:---|:---|
| **利用統計** | メッセージ数、セッション数、ファイル修正履歴 |
| **プロジェクト別分析** | どのプロジェクトでどんな作業を主に行ったか |
| **ツール利用パターン** | よく使うツールをチャートで可視化 |
| **言語別利用量** | どのプログラミング言語で作業したか |
| **ボトルネック** | 生産性を下げるパターンの特定 |
| **改善提案** | CLAUDE.md にコピー可能なカスタム提案、Custom Skill 推奨、Hook 推奨 |

レポートは `~/.claude/usage-data/report.html` に保存され、ブラウザで自動的に開きます。

> `/insights` の提案には **Copy ボタン** があり、CLAUDE.md にそのまま貼り付け可能です。自分の利用パターンに基づく最適化提案なので非常に有用です。
{: .prompt-tip }

### 2. Extended Thinking & Effort システム

Claude Code は **Extended Thinking (拡張推論)** をサポートします。応答前に Claude が **内部でより深く思考**するため、複雑な問題で精度が大きく向上します。

**Thinking の切替方法:**

| 方法 | 説明 |
|:---|:---|
| `Tab` キー | セッション内で Thinking モードを即時 On/Off |
| `/config` | 設定から Thinking を有効/無効化 |
| 環境変数 `MAX_THINKING_TOKENS=8000` | Thinking トークン予算を直接指定 (最小 1,024) |

**Effort レベル (Opus 4.6 専用):**

`/model` でモデル選択時に **Effort レベル**を調整できます。Claude がどの程度深く推論するかを制御します。

| Effort | 用途 | トークン消費 | 推奨場面 |
|:---:|:---|:---:|:---|
| **Low** | 高速応答、単純作業 | 少ない | 簡単な分類、クイック検索、大量処理 |
| **Medium** | バランス重視 | 普通 | 一般的なコーディング作業 |
| **High** (デフォルト) | 最高品質の推論 | 多い | 複雑な推論、難しいコーディング課題 |
| **Max** | 絶対最高性能 | 最大 | 極めて複雑なアーキテクチャ分析、多段階推論 |

```bash
# 環境変数で Effort レベル設定
CLAUDE_CODE_EFFORT_LEVEL=high claude

# またはセッション内で /model から変更
/model
# -> モデル選択後に Effort スライダーを調整
```

> **Adaptive Thinking**: Opus 4.6 では `budget_tokens` の手動指定より **Adaptive Thinking** が推奨されます。質問の複雑度に応じて Thinking の深さを **動的** に調整します。Effort レベルでその範囲を制御できます。
{: .prompt-info }

### 3. Fast モード

**Fast モード**は同じモデルを使ったまま、**出力トークン生成速度を最大 2.5 倍**に高める機能です。モデル切替ではなく、同一モデル内の高速推論経路を使います。

```bash
# セッション内で切替
/fast

# 有効化で雷アイコン (↯) を表示
# 設定はセッション間で維持
```

> Fast モードは **プレミアム料金** ($30/$150 per MTok) が適用されます。高速反復が必要なプロトタイピングで有効ですが、コストを考慮して選択的に使ってください。
{: .prompt-warning }

### 4. Agent Teams (研究プレビュー)

**Agent Teams** は複数の Claude Code インスタンスが **チームとして協調**する機能です。1 つのオーケストレータが全体を統括し、サブエージェントが別々の部分を並列処理します。

```
┌─────────────────────────────┐
│      Orchestrator (リーダー) │
│   全体作業の調整と分配を担当   │
└──────┬──────┬──────┬────────┘
       │      │      │
  ┌────▼──┐ ┌─▼───┐ ┌▼─────┐
  │Agent 1│ │Agent2│ │Agent3│
  │バックエンド│ │フロント│ │テスト │
  └───────┘ └─────┘ └──────┘
```

- 各サブエージェントは独自の **tmux pane** で実行
- 独立タスクを **並列処理** して大規模作業を高速化
- 現在は **研究プレビュー** 段階 (仕様変更の可能性あり)

### 5. Auto Memory (自動メモリ)

Claude Code が **セッション間コンテキストを自動記憶**する機能です。手動設定なしでバックグラウンド動作します。

**動作方式:**

| 表示 | 意味 |
|:---|:---|
| `Recalled X memories` | セッション開始時に過去セッション記憶を読み込み |
| `Wrote X memories` | セッション中に現在作業のスナップショットを保存 |

- プロジェクトパターン、主要コマンド、ユーザー嗜好を自動保存
- `~/.claude/projects/<project-hash>/<session-id>/session-memory/summary.md` に保存
- `#` キーで CLAUDE.md に素早くメモを追加可能

> Auto Memory は CLAUDE.md とは別物です。CLAUDE.md はユーザーが管理する明示ルール、Auto Memory は Claude が抽出する暗黙コンテキストです。両方を併用するのが最も効果的です。
{: .prompt-info }

### 6. Opus 4.6 & 1M トークンコンテキスト (ベータ)

最新モデル **Claude Opus 4.6** は **1M (100 万) トークンコンテキストウィンドウ**をベータ提供しています。

| 特徴 | 説明 |
|:---|:---|
| **1M トークンコンテキスト** | 従来 200K の 5 倍。大規模コードベース全体を一度に分析可能 |
| **Adaptive Thinking** | 問題の複雑度に応じて推論深度を動的調整 |
| **Context Compaction** | 長い会話で古いコンテキストを自動要約し限界を緩和 |
| **Agent Teams** | マルチエージェント協業をサポート |

### 7. モデル比較 (2026年2月時点)

| モデル | コンテキスト | 速度 | 推論能力 | コスト | 推奨用途 |
|:---|:---:|:---:|:---:|:---:|:---|
| **Opus 4.6** | 200K (1M ベータ) | 普通 | 最強 | 高い | アーキ設計、複雑なリファクタリング、Plan モード |
| **Opus 4.6 Fast** | 200K (1M ベータ) | 速い (2.5x) | 最強 | 非常に高い | 高速プロトタイピング、反復作業 |
| **Sonnet 4.5** | 200K | 速い | 優秀 | 普通 | 一般実装、コード作成、デバッグ |
| **Haiku 4.5** | 200K | 非常に速い | 良好 | 低い | 単純作業、大量処理 |

> **ハイブリッド戦略**: Opus で計画 (`/model` -> Opus)、Sonnet で実装 (`/model` -> Sonnet) する **opusplan** パターンを使うと、Opus 単独運用より **60-80% のコスト削減**が可能です。
{: .prompt-tip }

<br>

---

## VI. コンテキストウィンドウの深掘り理解

Claude Code を効果的に使うには **コンテキストウィンドウ (Context Window)** の理解が不可欠です。

### コンテキストウィンドウとは？

コンテキストウィンドウは、LLM が **一度に処理できる最大トークン量**です。Claude モデルでは:

| モデル | コンテキストウィンドウ | 特徴 |
|:---|:---|:---|
| **Claude Opus 4.6** | 200K (1M ベータ) | 最強の推論性能、複雑なアーキ分析に適合 |
| **Claude Sonnet 4.5** | 200K tokens | 応答が速く、一般コーディングに効率的 |

> **200K トークンはどの程度？** 英語で約 15 万語、A4 約 300 ページ相当です。ただしコードや韓国語はトークン効率が低いため実効量は少なくなります。1M トークンはその約 5 倍で、A4 約 1,500 ページ相当です。
{: .prompt-info }

### コンテキストウィンドウが重要な理由

LLM はリクエストごとに **Stateless** です。つまり Claude Code との新しいチャットは、**毎回新しいチームメンバーと作業する**のに近い状態です。過去情報はコンテキストウィンドウ内にある場合のみ保持されます。

```
[System Prompt] + [CLAUDE.md] + [Conversation History] + [Current Prompt] = Total token usage
                                                                     ↕
                                                           Context window limit
```

コンテキストが埋まると:
1. **Auto-compact** が発動し、過去会話が自動要約される
2. 要約時に **情報損失/歪み** が発生しうる
3. 既存計画の文脈が失われることがある

### Auto-Compact の構造的問題

Auto-compact は実行後に **元へ戻せません**。要約されると元会話は失われ、次の問題が起こり得ます:

| 問題 | 説明 |
|:---|:---|
| **コンテキスト歪み** | 要約過程で原意が変化する可能性 |
| **時間的文脈の喪失** | 「先に A を決めたので B を行う」など順序文脈が消える |
| **情報断片化** | 関連情報が分断され推論品質が低下 |

> Auto-compact は会話の「中間領域」を要約しがちで、Phase 1 全体ではなく Phase 1.2-1.5 あたりが圧縮される現象があります。
{: .prompt-warning }

### コンテキスト管理戦略

**1. 定期的に手動 `/compact`**
- Auto-compact 任せにせず、適切なタイミングで `/compact` を実行
- `/compact 現在の Todo と進捗中心で` のように対象を指定可能

**2. タスク単位で `/clear`**
- 大きな作業を複数セッションに分割
- 各セッションは `/clear` でクリーンな状態から開始

**3. CLAUDE.md の活用**
- 毎回繰り返すプロジェクト情報を CLAUDE.md に記録
- 新セッションごとに自動読込されるためコンテキスト節約に有効

**4. 外部文書参照**
- 複雑な計画は別 `.md` にまとめて `@ファイル名` で参照
- コンテキスト内に計画全文を保持するより効率的

<br>

---

## VII. CLAUDE.md ファイルの理解

### CLAUDE.md とは？

CLAUDE.md はプロジェクトの **「AI オンボーディング文書」**です。新しいメンバーがプロジェクト Wiki を読むように、Claude Code は各セッションでこのファイルを読んでプロジェクトを理解します。

### CLAUDE.md に入れるべき内容

```markdown
# CLAUDE.md

## Project Overview
- プロジェクト説明、技術スタック、アーキ概要

## Build & Development Commands
- ビルド、テスト、実行コマンド

## Code Conventions
- コーディングスタイル、命名規則、ファイル構造

## Architecture
- 主要ディレクトリ構造、コアモジュール説明

## Common Patterns
- プロジェクトで頻出するパターン
- 「こうしない」ルール (Claude の反復ミス防止)
```

### メモリネスティング (Memory Nesting)

CLAUDE.md は [複数階層で構成](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories) できます:

| 位置 | 範囲 | 用途 |
|:---|:---|:---|
| `~/.claude/CLAUDE.md` | **グローバル (ユーザー単位)** | 全プロジェクト共通ルール |
| `./CLAUDE.md` | **プロジェクトルート** | プロジェクト全体に適用 |
| `./src/CLAUDE.md` | **サブディレクトリ** | 特定モジュール/ディレクトリにのみ適用 |

> `/init` で生成された CLAUDE.md を **そのまま固定運用しないでください。** プロジェクト固有の規約、設計方針、頻出ミスを自分で追加し、継続的に改善することが重要です。
{: .prompt-warning }

<br>

---

## VIII. 計画-実行ワークフロー (Plan & Execute)

### 核心原則

Claude Code 活用の要点は、**計画 (Plan)** と **実行 (Execute)** を明確に分離することです。

### モデル選択戦略

| 段階 | 推奨モデル | 理由 |
|:---|:---|:---|
| **計画立案** | Opus | 複雑推論、アーキ分析、戦略策定に強い |
| **コード実装** | Sonnet | 応答が速くコスト効率が高い。実装作業に適合 |

```
1. /model -> Opus を選択
2. Shift+Tab を2回 -> Plan モードへ
3. 計画立案と Todo 作成
4. /model -> Sonnet に変更
5. 段階的に実装
```

### Plan モード中心ワークフロー

**1段階: 探索と計画 (Explore & Plan)**

Plan モード (Shift+Tab 2回) から開始:

- 実装戦略を策定
- 作業を **独立テスト可能なステップ** に分解
- 想定工数/時間を見積もる
- UI/ライブラリ関連事項も含める

> 詳細なプロンプトが重要です。例: 「この機能実装を段階ごとに分割して。各段階は独立してテスト可能にし、所要時間も見積もって。」
{: .prompt-tip }

**2段階: 計画確定と実行**

計画が十分になったら:
1. `Shift+Tab` で **Auto-accept edits モード**へ切替
2. Claude が計画に沿って **1-shot 実装**を進行

**Plan モードの利点:**

| 利点 | 説明 |
|:---|:---|
| **コンテキスト持続** | Plan モードの Todo リストは長時間セッションでも維持され、作業連続性を保てる |
| **動的な計画修正** | 実装中に抜け漏れが見つかれば即座に計画を更新できる |
| **ハルシネーション低減** | 明確な計画があると誤った方向への逸脱を防げる |

> 可能であれば、現在タスクのチェックリストを `.md` で管理し、継続的に更新させる運用が有効です。
{: .prompt-tip }

### PRD (Product Requirements Document) 活用

Plan モードで Todo を作るだけでも有効ですが、**大規模作業やリファクタリング**では PRD の活用が効果的です。

PRD に含める要素:
- **目標と背景**: なぜ必要か
- **要件**: 機能要件/非機能要件
- **範囲**: 対象/非対象
- **設計方針**: アーキテクチャ上の意思決定
- **成功基準**: 完了条件

<br>

---

## IX. 安全性と制御 (Safety & Control)

### 権限モードの理解

| モード | 説明 | 使用タイミング |
|:---|:---|:---|
| **基本モード** | ファイル修正/コマンド実行ごとに承認が必要 | 重要プロジェクト、学習段階 |
| **Auto-accept** | ファイル修正を自動承認 | 計画確定後の実装段階 |
| **dangerously-skip-permissions** | すべての権限を自動承認 | サンドボックス環境のみ推奨 |

### `/permissions` による細かな制御

`--dangerously-skip-permissions` の代わりに、`/permissions` でよく使う安全なコマンドだけ事前許可する運用が推奨されます。

```bash
# .claude/settings.json に保存でき、チーム共有も可能
# 例: git, npm, build コマンドを事前許可
```

### 安全運用の原則

1. 最初は承認モードで 1 つずつ確認
2. 計画確定後に Auto-accept へ切替
3. 実装が想定と違えば `Esc` 2 回 (Rewind) で巻き戻す
4. 計画そのものが誤りなら Plan を修正

<br>

---

## X. 高度活用 13 のヒント (Claude Code 創始者ワークフロー)

Claude Code 開発者が共有した実践的なヒントです。

### 1. 並列実行環境を構築

ターミナルで **5 つの Claude を並列実行**します。タブに 1-5 の番号を付け、[システム通知](https://code.claude.com/docs/en/terminal-config#iterm-2-system-notifications) で入力が必要なタイミングを把握します。

### 2. Web とローカルを並列運用

- `claude.ai/code` でも **5-10 個の Claude セッション**を追加並列実行
- ローカルセッションを Web にハンドオフ (`&`) したり、`-teleport` で双方向切替
- iOS アプリで開始し、あとで確認する使い方も有効

### 3. モデル選択: Opus with thinking

- すべての作業で **Opus 4 with thinking** を使用
- Sonnet より大きく遅いが、**ステアリングが少なくて済み**、**ツール活用能力が高い**
- 結果的に小さいモデルより **最終到達が速い** ケースが多い

### 4. CLAUDE.md でチーム知識を蓄積

- チーム共通の **単一 CLAUDE.md** を維持
- git にチェックインし、週に複数回チームで改善
- Claude の誤動作が出たら追記し、同じミスを再発防止

### 5. コードレビュー時に CLAUDE.md を更新

- 同僚 PR レビューで **@.claude** をタグし、CLAUDE.md 更新を反映
- **Claude Code GitHub Action** (`/install-github-action`) を活用

### 6. Plan モード + Auto-accept ワークフロー

- 多くのセッションを **Plan モード** (Shift+Tab 2回) で開始
- 計画品質に納得するまで協議を反復
- 確定後 **Auto-accept モード**に切替えると **1-shot 完了**しやすい
- **良い計画が最重要**

### 7. スラッシュコマンドで反復作業を自動化

- 頻出するインナーループごとにスラッシュコマンドを作成
- `.claude/commands/` に保存して git で管理
- 例: `/commit-push-pr` を毎日数十回利用
- [インライン bash](https://code.claude.com/docs/en/slash-commands#bash-command-execution) で `git status` などを事前計算し、不要なモデル往復を削減

### 8. サブエージェント活用

複数の [サブエージェント](https://code.claude.com/docs/en/sub-agents) を定期利用:
- **code-simplifier**: 作業後のコード簡素化
- **verify-app**: E2E テスト用の詳細手順

### 9. PostToolUse Hook でフォーマット自動化

- **PostToolUse Hook** でコード整形を自動処理
- Claude 本体でも大半は整うため、Hook が残り **10%** を補完

### 10. 権限管理スタイル

- `--dangerously-skip-permissions` は使わない
- 代わりに `/permissions` で安全な bash コマンドを事前許可
- `.claude/settings.json` を git 管理してチーム共有

### 11. ツール統合活用

Claude Code に外部ツール操作を委任:
- **Slack** の検索/投稿 (MCP 利用)
- **BigQuery** クエリ実行 (`bq` CLI)
- **Sentry** からエラーログ取得
- `.mcp.json` を git 管理し、チームで MCP 設定を共有

### 12. 長時間タスクの処理方法

非常に長い作業では次の 3 方式から選択:
- **(a)** 完了時に **バックグラウンドエージェント**で検証させるようプロンプト
- **(b)** [Agent Stop Hook](https://code.claude.com/docs/en/hooks-guide) でより決定論的に検証
- **(c)** [ralph-wiggum プラグイン](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-wiggum) を使用

### 13. 最重要ヒント: 検証フィードバックループ

> Claude Code で高品質な結果を得るための **最重要要素** は、Claude に **検証方法を与えること**です。
{: .prompt-warning }

このループがあると最終成果物の品質が **2-3 倍向上**します:
- bash コマンド実行で結果確認
- テストスイート実行
- ブラウザ/シミュレータでアプリ検証
- [Chrome 拡張](https://code.claude.com/docs/en/chrome) で UI テスト

**堅牢な検証プロセスに投資することが最も価値の高い改善です。**

<br>

---

## XI. SDD (Spec-Driven Development)

### SDD とは？

SDD (Spec-Driven Development) は「Claude に口頭で指示する開発」から進み、**チーム共有の技術仕様**を基準に AI が実装/テストまで進める開発方式です。

**SDD の核心価値:**
- コンテキスト消失の最小化
- ハルシネーション低減
- チーム協業効率の向上

### Spec Kit の導入と利用

[Spec Kit](https://github.com/github/spec-kit) は SDD 実現のためのツールです。

```bash
# Spec Kit 初期化
specify init --here
# -> 'y' を入力
# -> 'claude' を選択
# -> 'sh' を選択
```

インストール後、新しいセッションで `claude` を起動すると追加コマンドが使えます。

### Spec Kit ワークフロー

| コマンド | 段階 | 説明 |
|:---|:---|:---|
| `/speckit.constitution` | 規約設定 | CLAUDE.md、コード規約、アーキに基づく規約作成 |
| `/speckit.specify` | 要件定義 | **What/Why** 中心。技術スタックは書かない |
| `/speckit.clarify` | 詳細化 | 不足した仕様情報を補完 |
| `/speckit.plan` | 計画策定 | 技術スタック/アーキをこの段階で決定 |
| `/speckit.tasks` | タスク分解 | 実装可能な単位へ分割 |
| `/speckit.implement` | 実装 | 実コードを作成 |
| `/speckit.analyze` | 分析 (任意) | 文書間の整合性チェック |
| `/speckit.checklist` | チェックリスト (任意) | 品質確認 |

### `/speckit.specify` 作成ガイド

`specify` は **何を作るか (What/Why)** を記述する段階です。実装方法 (How) は `/speckit.plan` で扱います。

**WHAT (要件)**
- ユーザーが実行可能であるべき行動
- システムが保証すべき規則 (検証/制約/互換性)
- 成果物 (アセット、プレハブ、登録、テスト環境)
- 成功基準 (時間制約、レガシー互換など)

**WHY (必要性)**
- 既存問題 (ボトルネック、重複、不整合、コンテキスト消失)
- 成功指標への寄与度

**`specify` に書かないこと (`/plan` で扱う)**
- ~~「BaseWeapon に DI コンテナを入れて...」~~
- ~~「BulletRecipe を ScriptableObject にして...」~~
- ~~「ECS で最適化して...」~~

<br>

---

## XII. プラグイン活用

### プラグインのインストール方法

```bash
# Claude Code 起動
claude

# マーケットプレイスから取得
/plugin marketplace add wshobson/agents

# 必要なプラグインを選択インストール
/plugin install game-development
/plugin install debugging-toolkit
/plugin install code-refactoring
```

[wshobson/agents](https://github.com/wshobson/agents/tree/main) リポジトリには、オーケストレーション向けに最適化された多様なエージェントが含まれます。

### プラグインの動作方式

導入済みプラグインは **状況に応じて自動活用**されます:

- **自動活性化**: 作業内容に応じて適切なエージェントが起動
  - コード作成後 -> code-reviewer
  - エラー発生時 -> debugger
- **明示リクエスト**: 「コードレビューして」-> code-reviewer を起動
- **状況判断**: 単純作業は追加エージェントなしで直接処理

<br>

---

## XIII. 注意事項

### Unity 連携の制約

現時点では Claude Code と Unity Editor を直接接続する手段はありません。そのため Unity Editor のエラー状態を正確に把握できない場合があります。ただし **ロジックエラー分析やコード意図の把握能力は高い**です。

> Unity-MCP というツールは存在しますが、セキュリティ脆弱性の懸念があります。利用前に必ずセキュリティレビューを行ってください。
{: .prompt-danger }

### MCP サーバー利用時の注意

MCP (Model Context Protocol) サーバーを使う際は:
- 信頼できるソースか必ず確認
- セキュリティ脆弱性の有無をレビュー
- チーム運用時はホワイトリスト管理を推奨

<br>

---

## 参考資料

- [Claude Code 公式ドキュメント](https://code.claude.com/docs)
- [Spec Kit (GitHub)](https://github.com/github/spec-kit)
- [wshobson/agents プラグイン集](https://github.com/wshobson/agents/tree/main)
- [Claude Code メモリシステム](https://code.claude.com/docs/en/memory#how-claude-looks-up-memories)
- [Claude Code Hook ガイド](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code スラッシュコマンド](https://code.claude.com/docs/en/slash-commands#bash-command-execution)
- [Claude Code サブエージェント](https://code.claude.com/docs/en/sub-agents)
