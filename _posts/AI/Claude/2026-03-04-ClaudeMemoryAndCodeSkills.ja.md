---
title: "Claudeメモリ無料開放と/simplify、/batch — そしてCLAUDE.mdの隠れたコスト"
lang: ja
date: 2026-03-04 14:00:00 +0900
categories: [AI, Claude]
tags: [Claude, Claude Code, Memory, AI, LLM, simplify, batch, CLAUDE.md, Token Optimization, Developer Tools]

difficulty: intermediate
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
  - /posts/EvaluatingAgentsMd/
tldr:
  - "AnthropicがClaudeメモリを無料プランに開放し、ChatGPT/Geminiメモリインポートツールをリリースした — App Store無料アプリ1位獲得直後の攻撃的な動き"
  - "/simplifyは3つの並列レビューエージェント（コード再利用・品質・効率性）でPRあたり3〜5件のイシューを自動修正し、/batchはコードベース全体を5〜30単位に分解して並列マイグレーションする"
  - "CLAUDE.mdを過度にネストするとセッションあたり最大55K+トークンが無駄になり、Skillベースの段階的ロードでコンテキストを82%まで節約できる"
---

## はじめに

2026年3月第1週、Claudeエコシステムで注目すべき3つの動きがあった。

1. **Claudeメモリが無料プランに開放**され、競合他社のメモリインポートツールがリリースされた
2. Claude Codeに**`/simplify`と`/batch`**スキルがバンドルされた
3. CLAUDE.mdの**ネストパターンが引き起こすトークンコスト問題**がコミュニティで本格的に議論され始めた

本記事では3つのテーマをそれぞれ深掘りし、特に3つ目のテーマでは以前の記事（[AGENTS.mdは本当に役立つのか？](/posts/EvaluatingAgentsMd/)）で扱ったコンテキストファイルのパラドックスを実際のトークン数値で拡張する。

---

## 1. Claudeメモリ — 無料プラン開放とメモリインポート

### 1-1. タイムライン

| 時期 | イベント |
|------|---------|
| 2025年8月 | Claudeメモリ初導入（有料プラン限定） |
| 2025年10月 | Pro、Max、Team、Enterprise全有料プランに拡大 |
| 2026年3月2日 | **無料プラン開放** + メモリインポートツールリリース |

約8ヶ月にわたる段階的ロールアウトが完了した。タイミングが意味深い — Claudeが**App Store無料アプリチャート1位**に上った直後であり、ChatGPT DoD（米国防総省）契約後に**ChatGPTのアンインストールが295%急増**した時期だ。

### 1-2. メモリの仕組み

Claudeのメモリは、会話中に自動生成される要約だ。

```
ユーザーの会話 → Claudeが好み/プロジェクト/コンテキストを推論 → テキストファイルとして保存
```

主な特徴：
- **自動推論**：会話中にユーザーの好み、進行中のプロジェクト、作業コンテキストを自動的に把握
- **編集可能**：保存されたメモリをユーザーが直接確認・修正できる
- **制御オプション**：一時停止（メモリ保持、無効化）または完全削除が選択可能
- **業務中心**：業務関連のコンテキストに集中するよう設計されており、業務と無関係な個人情報は保存されない場合がある

### 1-3. メモリインポートツール

ChatGPT、Geminiなどの競合チャットボットからClaudeに移行するユーザー向けのツールが同時にリリースされた。

**移行プロセス：**

1. ClaudeのエクスポートプロンプトをChatGPT/Geminiに貼り付け
2. 該当チャットボットが保存されたメモリをコードブロック形式で出力
3. このテキストをClaudeに貼り付けて「Add to memory」をクリック
4. Claudeが重要情報を抽出し個別のメモリ項目として保存

**注意事項：**
- まだ実験的機能のため、すべてのメモリが完全に移行されない場合がある
- 業務関連コンテキストが優先され、無関係な個人情報は省略される場合がある

### 1-4. これが意味すること

メモリの無料開放は単なる機能拡大ではない。AIチャットボット市場で**スイッチングコストを下げる**戦略的な動きだ。他のチャットボットに蓄積されたコンテキストが「慣れたAIを使い続けさせる」ロックイン効果を生むが、インポートツールはこの障壁を正面から破壊する。

ゲーム開発者の観点からは、UnityエディタからUnreal Engineに移行する際にアセットマイグレーションツールを提供するのと似た文脈だ。

---

## 2. /simplify — 3つの並列レビューエージェント

### 2-1. 概要

`/simplify`はClaude Code v2.1.63で導入された**バンドルスキル**だ。機能を実装して動作を確認した後、コミット前に実行するとコード品質を自動的に改善する。

公式ドキュメントの説明：

> `/simplify`: reviews your recently changed files for code reuse, quality, and efficiency issues, then fixes them.

### 2-2. 3つの並列レビューエージェント

`/simplify`の核心は**3つのサブエージェントを並列でスポーン**する構造だ。

```
/simplify 実行
    ├── 🔄 Code Reuse Agent
    │    └── 重複ロジック、抽出可能なパターンを検査
    ├── 📐 Code Quality Agent
    │    └── 可読性、命名、構造を検査
    └── ⚡ Efficiency Agent
         └── 不要な複雑さ、重複演算を検査

    → 3エージェントの結果を集約
    → 自動修正を適用
```

**各エージェントの役割：**

| エージェント | 検査対象 | 実務で主に見つけるもの |
|------------|---------|-------------------|
| Code Reuse | 重複ロジック、抽出可能なパターン | 複数ファイルにコピーされた類似関数 |
| Code Quality | 可読性、命名、構造 | 不明確な変数名、過度なネスト |
| Efficiency | 不要な複雑さ、見逃した最適化 | 不要なループ、見逃した並行処理の機会 |

実使用レポートによると、**フィーチャーブランチあたり3〜5件のイシュー**を一貫して検出し、特にEfficiencyエージェントが不要なループと見逃した並行処理の機会を捕捉するのに強い。

### 2-3. 使い方

```bash
# 基本使用 — 変更されたファイル全体をレビュー
/simplify

# 特定の関心事に集中
/simplify focus on memory efficiency

# 特定のパターンに集中
/simplify focus on null safety and error handling
```

**推奨ワークフロー：**

```
機能実装 → 動作確認 → /simplify → コミット → PR
```

毎PR前に`/simplify`を実行する習慣をつければ、コードレビューで指摘されるイシューを事前に除去できる。

---

## 3. /batch — 大規模並列コードマイグレーション

### 3-1. 概要

`/batch`はコードベース全体にわたる大規模な変更を**並列で**実行するスキルだ。単純な検索・置換ではなく、リサーチ → 分解 → 実行 → PR作成までの全パイプラインをオーケストレーションする。

### 3-2. 動作方式

```
/batch "migrate src/ from Solid to React"
    │
    ├── 1. コードベースリサーチ
    │    └── 変更対象ファイルとパターンを分析
    │
    ├── 2. タスク分解（5〜30単位）
    │    └── 独立して処理可能な単位に分割
    │
    ├── 3. ユーザー承認
    │    └── 分解された計画を提示して承認を要求
    │
    └── 4. 並列実行
         ├── Worker 1（隔離されたgit worktree）
         │    ├── 実装
         │    ├── テスト
         │    ├── /simplify（自動）
         │    └── PR作成
         ├── Worker 2（隔離されたgit worktree）
         │    └── ...
         └── Worker N
              └── ...
```

核心ポイント：
- **隔離されたgit worktree**：各ワーカーが独立したワーキングツリーで作業するため競合がない
- **自動/simplify**：各ワーカーがコミット前に自動で`/simplify`を実行する。手動チェーンは不要
- **gitリポジトリ必須**：ワークツリー機能を使用するためgitリポジトリでのみ動作する

### 3-3. 使用例

```bash
# フレームワークマイグレーション
/batch migrate src/ from Solid to React

# APIバージョンアップグレード
/batch update all API calls from v2 to v3 endpoints

# テストフレームワーク変更
/batch convert all Jest tests in tests/ to Vitest

# コーディングコンベンション一括適用
/batch rename all React components from PascalCase files to kebab-case files
```

### 3-4. /simplify vs /batch 比較

| | /simplify | /batch |
|---|----------|--------|
| **目的** | 変更コードの整理 | 大規模コードベース変更 |
| **実行タイミング** | 機能実装後、PR前 | マイグレーション/リファクタリング時 |
| **並列単位** | 3レビューエージェント | 5〜30ワーカーエージェント |
| **隔離方式** | 現在のブランチで実行 | 個別git worktree |
| **成果物** | 現在のコード修正 | ワーカーごとの個別PR |
| **/simplify含む** | 自身が/simplify | 各ワーカーが自動実行 |

---

## 4. CLAUDE.mdネストの隠れたコスト

### 4-1. 問題の背景

[以前の記事](/posts/EvaluatingAgentsMd/)でコンテキストファイルが引き起こす**情報の重複**と**コスト増加**を論文データで確認した。今回は実際のClaude Code環境でCLAUDE.mdを過度に構成した際に発生する**トークンコスト**を具体的な数値で分析する。

### 4-2. CLAUDE.mdのロードメカニズム

Claude Codeはセッション開始時に以下を自動的にロードする：

```
セッション開始
    ├── CLAUDE.md（プロジェクトルート）
    ├── ~/.claude/CLAUDE.md（ユーザーレベル）
    ├── 上位ディレクトリのCLAUDE.md（再帰探索）
    ├── MCPサーバーツール定義
    └── 有効化されたSkill説明
```

**問題は、これらすべてが毎セッション、毎メッセージでコンテキストに含まれることだ。**

### 4-3. 数値で見る無駄

コミュニティと公式ドキュメントで報告された数値を総合すると：

#### MCPサーバーのトークンオーバーヘッド

| MCPサーバー数 | 会話開始前のトークン消費 |
|-------------|---------------------|
| 0個 | ~0トークン |
| 5個 | **~55,000トークン** |
| 10個以上 | **100,000+トークン** |

5つのMCPサーバーを接続するだけで、会話が始まる前にすでに**55Kトークンが消費**される。Jiraのようなツール定義が大きいサーバーを追加すると100Kに簡単に到達する。

> Claude CodeのTool Search機能はこの問題を46.9%軽減する（51K → 8.5Kトークン）。ツール説明がコンテキストウィンドウの10%を超えると自動的にオンデマンドロードに切り替わる。

#### CLAUDE.mdのコンテキスト効率性

実測ケースでのCLAUDE.mdのセッション別コンテキスト活用率：

| セッション種類 | ロードされたトークン | 実際活用トークン | 活用率 |
|------------|----------------|-------------|-------|
| READMEのタイポ修正 | 2,100 | ~300 | **14%** |
| APIエンドポイント追加 | 2,100 | ~600 | **28%** |
| テスト作成 | 2,100 | ~500 | **24%** |

**平均活用率は22%程度**だ。つまりCLAUDE.mdに書いた内容の**78%は該当セッションで不要なトークンを消費**している。

#### Agent Teamsの倍数効果

| モード | トークン使用倍率 | 理由 |
|------|-------------|-----|
| 単一セッション | 1x（基準） | — |
| サブエージェント | 1.5〜3x | 各自コンテキストウィンドウを維持 |
| Agent Teams（plan mode） | **~7x** | チームメンバーごとに独立したClaudeインスタンス |

Agent Teamsでチームメンバーがplan modeで動作すると**単一セッション比約7倍のトークン**を使用する。ここに過度なCLAUDE.mdが各チームメンバーにロードされると、無駄がチームメンバー数分だけ掛け合わされる。

#### Auto-Compactionオーバーヘッド

自動圧縮（auto-compact）機能もコンテキストウィンドウの一部を消費する。一部の報告によると、**autocompactバッファが45Kトークン — コンテキストウィンドウの22.5%** — を事前に占有するケースがある。

### 4-4. ネストパターン別コスト分析

多くの開発者がCLAUDE.mdを体系的に管理するためにネストパターンを使用している。しかし、このパターンによってトークンコストが大きく変わる。

#### パターン1：モノリシックCLAUDE.md（非推奨）

```markdown
# CLAUDE.md（2,000行以上）
## プロジェクト概要 ...
## ビルドコマンド ...
## コーディングコンベンション ...
## APIドキュメント ...
## データベーススキーマ ...
## デプロイガイド ...
## テスト戦略 ...
```

- **問題**：毎セッションで全内容をロード
- **トークンコスト**：毎セッション~8,000〜15,000トークン
- **活用率**：14〜28%（大部分が不要）

#### パターン2：ディレクトリ別分散（部分改善）

```
project/
├── CLAUDE.md              # プロジェクト全体のルール
├── src/
│   └── CLAUDE.md          # src関連ルール
├── tests/
│   └── CLAUDE.md          # テスト関連ルール
└── docs/
    └── CLAUDE.md          # ドキュメント関連ルール
```

- **改善点**：作業ディレクトリに応じて関連ルールのみ追加ロード
- **残る問題**：ルートCLAUDE.mdは依然として常にロードされる
- **トークンコスト**：3,000〜8,000トークン（ディレクトリにより変動）

#### パターン3：Skillベース段階的ロード（推奨）

```
project/
├── CLAUDE.md              # 最小限の必須情報のみ（~500行以下）
└── .claude/skills/
    ├── deploy/SKILL.md    # デプロイ時のみロード
    ├── api-guide/SKILL.md # API作業時のみロード
    └── db-schema/SKILL.md # DB作業時のみロード
```

- **核心**：Skillは**呼び出された時のみ**全内容がロードされる
- **通常時は**：Skillの説明（description）のみがコンテキストに含まれる
- **トークン節約**：**最大82%節約**（~15,000トークン/セッション）

### 4-5. 最適化前後の比較

公式ドキュメントとコミュニティ報告を総合した最適化効果：

| 戦略 | 節約率 | 方法 |
|------|-------|------|
| CLAUDE.md → Skill移行 | **82%** | 専門指針をSkillに分離 |
| MCP Tool Search有効化 | **46.9%** | ツール定義のオンデマンドロード |
| Plan mode使用 | **40〜60%** | 複雑なタスクの探索コスト削減 |
| CLAUDE.md 500行以下維持 | **62%** | セッションあたり~1,300トークン節約 |
| 全最適化適用時 | **55〜70%** | 上記戦略の組み合わせ |

### 4-6. 実践ガイド：CLAUDE.mdダイエット

**CLAUDE.mdに残すべきもの：**

```markdown
# ビルド/実行コマンド（プロジェクト固有）
bundle exec jekyll serve

# プロジェクト固有の非標準ルール
- 翻訳ファイル：.en.md、.ja.md サフィックスを使用
- 画像：assets/img/post/{category}/ 配下

# 特殊ツール要件
- Ruby 3.2必要
- Gemfile.lockはコミットしない
```

**Skillに移すべきもの：**

```yaml
# .claude/skills/post-guide/SKILL.md
---
name: post-guide
description: ブログ記事作成ガイド。記事作成時に使用。
---
## Front Matterフォーマット
...詳細なfront matterガイド...

## カテゴリ一覧
...全カテゴリの列挙...

## 記事統計
...統計データ...
```

こうすれば記事を書く時だけ`/post-guide`がロードされ、他の作業では「ブログ記事作成ガイド。記事作成時に使用。」という1行の説明だけがコンテキストに含まれる。

---

## 5. 3つの変化の交差点

今週の3つの変化は相互に関連している：

```
メモリ無料開放            /simplify + /batch          CLAUDE.md最適化
      │                         │                          │
      ▼                         ▼                          ▼
  ユーザー拡大  ──→  より多くのエージェント使用  ──→  トークンコスト管理が重要に
      │                         │                          │
      └─────────────── 結局はコスト効率の問題 ────────────────┘
```

メモリの無料開放でユーザーが増え、`/simplify`や`/batch`のようなマルチエージェントスキルが日常になれば、**トークンコスト管理は選択ではなく必須**になる。以前の記事で扱った「コンテキストファイルのパラドックス」が今や実際のコストの問題に拡大したのだ。

---

## おわりに

Claudeエコシステムの進化方向は明確だ：

1. **アクセシビリティの拡大**：メモリ無料開放、競合他社からの移行ツール
2. **自動化の深化**：`/simplify`の3エージェントレビュー、`/batch`の並列マイグレーション
3. **コスト最適化の必須化**：Skillベース段階的ロード、Tool Search、Plan mode

特にCLAUDE.mdを「プロジェクトのすべてを収めた百科事典」のように使っていたパターンは、もう見直す必要がある。公式ドキュメントも500行以下を推奨しており、専門指針をSkillに分離することがトークン効率面で圧倒的に有利だ。

次にCLAUDE.mdを修正する時、自分自身に問いかけてみよう：**「この内容は毎セッション、毎メッセージにロードされる価値があるか？」**

---

## References

- Anthropic. (2026). *Claude Memory - Free Plan*. [Engadget](https://www.engadget.com/ai/anthropic-brings-memory-to-claudes-free-plan-220729070.html)
- Anthropic. (2026). *Import and export your memory from Claude*. [Claude Help Center](https://support.claude.com/en/articles/12123587-import-and-export-your-memory-from-claude)
- Anthropic. (2026). *Extend Claude with skills*. [Claude Code Docs](https://code.claude.com/docs/en/skills)
- Anthropic. (2026). *Manage costs effectively*. [Claude Code Docs](https://code.claude.com/docs/en/costs)
- Boris Cherny. (2026). */simplify and /batch announcement*. [Threads](https://www.threads.com/@boris_cherny/post/DVR-HzBkqRd/)
- Joe Njenga. (2026). *Claude Code Just Cut MCP Context Bloat by 46.9%*. [Medium](https://medium.com/@joe.njenga/claude-code-just-cut-mcp-context-bloat-by-46-9-51k-tokens-down-to-8-5k-with-new-tool-search-ddf9e905f734)
- MacRumors. (2026). *Anthropic Adds Free Memory Feature and Import Tool*. [MacRumors](https://www.macrumors.com/2026/03/02/anthropic-memory-import-tool/)
- TechCrunch. (2026). *ChatGPT uninstalls surged by 295% after DoD deal*. [TechCrunch](https://techcrunch.com/2026/03/02/chatgpt-uninstalls-surged-by-295-after-dod-deal/)
- The Verge. (2026). *Anthropic upgrades Claude's memory to attract AI switchers*. [The Verge](https://www.theverge.com/ai-artificial-intelligence/887885/anthropic-claude-memory-upgrades-importing)
