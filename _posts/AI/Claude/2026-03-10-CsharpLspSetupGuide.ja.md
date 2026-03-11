---
title: "macOSでClaude Code C# LSPを完全セットアップするガイド — csharp-lsのインストールからトラブルシューティングまで"
lang: ja
date: 2026-03-10 10:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, C#, LSP, csharp-ls, dotnet, macOS, 開発環境, AI]
difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "Claude CodeでC# LSPを使うには、.NET SDK + csharp-ls + 環境変数2行 + プラグイン有効化の4つだけ揃えればよい"
  - "インストール失敗の90%はDOTNET_ROOT環境変数の未設定が原因 — Apple SiliconとIntel Macでパスが異なる"
  - "プロジェクトルートに.slnファイルがなければcsharp-lsはシンボルをインデキシングできない"
---

## はじめに

Claude Codeは様々な言語のLSP（Language Server Protocol）をサポートし、コード分析、シンボル検索、リファクタリングなどを実行できる。その中でも**C# LSPはUnityや.NETプロジェクトでコード品質を高めるための重要なツール**だ。

しかし、macOSでのC# LSPのセットアップはWindowsより難しい。.NET SDKのパス、環境変数、プラグインの有効化など、**つまずく可能性のあるポイントが複数存在する**。

本記事は、macOSでClaude CodeのC# LSP（csharp-ls）をセットアップする際に**実際に遭遇した問題とその解決方法**をまとめた実践ガイドだ。Quick Startで素早くインストールするか、問題が発生したら手動セットアップガイドを参照してほしい。

---

## 1. 検証済み環境

| 項目 | 値 |
|------|-----|
| macOS | Sequoia 26.1 |
| アーキテクチャ | arm64（Apple Silicon） |
| Rosetta | インストール済み |
| .NET SDK | 10.0.101（Homebrew） |
| csharp-ls | 0.22.0 |
| Claude Code | 最新バージョン |

---

## 2. Quick Start（6ステップ）

すでにHomebrewがインストールされていれば、以下の6ステップですぐにセットアップできる。問題が発生した場合は[手動セットアップガイド](#4-手動セットアップガイド)を参照しよう。

### 事前確認

ターミナルを開き、現在の状態を確認する：

```bash
dotnet --version     # バージョンが表示されれば → Step 1をスキップ
csharp-ls --version  # バージョンが表示されれば → Step 2をスキップ
echo $DOTNET_ROOT    # パスが表示されれば → Step 3をスキップ
```

### Step 1. .NET SDKのインストール

```bash
brew install dotnet
```

インストール後の確認：

```bash
dotnet --version
# 出力: 10.0.101
```

### Step 2. csharp-lsのインストール

```bash
dotnet tool install --global csharp-ls
```

インストール後の確認：

```bash
csharp-ls --version
# 出力: 0.22.0
```

> `csharp-ls: command not found`が出た場合は、先にStep 3のPATH設定を行おう。
{: .prompt-tip }

### Step 3. 環境変数の設定（.zshrc）

**このステップが最も重要だ。** `~/.zshrc`ファイルに以下の2行を追加する：

```bash
# Apple Silicon Mac（M1/M2/M3/M4）
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"
export PATH="$PATH:$HOME/.dotnet/tools"
```

シェルをリロード：

```bash
source ~/.zshrc
```

> **Intel Macの場合**、DOTNET_ROOTのパスが異なる：
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

### Step 4. Claude Codeプラグインの有効化

`~/.claude/settings.json`に追加：

```json
{
  "enabledPlugins": {
    "csharp-lsp@claude-plugins-official": true
  }
}
```

プロジェクトごとに有効化するには、`<プロジェクト>/.claude/settings.json`にも同様に追加する。

### Step 5. プロジェクトの.slnファイルを確認

csharp-lsは`.sln` → `.csproj`のパスを通じてシンボルをインデキシングする。プロジェクトルートに`.sln`ファイルが必ず必要だ。

```bash
ls *.sln
# 出力例: MyProject.sln
```

`.sln`ファイルがなければ作成する：

```bash
dotnet new sln -n MyProject
dotnet sln add path/to/MyProject.csproj
```

### Step 6. インストールの確認

すべての設定が終わったら、以下のコマンドで最終確認する：

```bash
# すべて正常に出力されれば成功
dotnet --version          # .NET SDKバージョン
which csharp-ls           # ~/.dotnet/tools/csharp-ls
csharp-ls --version       # 0.22.0
echo $DOTNET_ROOT         # /opt/homebrew/opt/dotnet/libexec
```

Claude Codeを起動し、C#プロジェクトディレクトリでLSP機能が動作するか確認する。

---

## 3. アーキテクチャの理解

Quick Startだけで十分だが、問題が発生した際に原因を把握するには全体構造を理解しておくとよい。

### コンポーネント関係図

```
Claude Code
    │
    ├── csharp-lspプラグイン（settings.jsonで有効化）
    │       │
    │       └── csharp-ls（LSPサーバー）
    │               │
    │               ├── DOTNET_ROOT → .NET SDKの場所を参照
    │               │
    │               └── .slnファイル → .csproj → シンボルインデキシング
    │
    └── PATH → ~/.dotnet/tools（csharp-lsバイナリの場所）
```

### 各コンポーネントの役割

| コンポーネント | 役割 | インストールパス |
|----------------|------|------------------|
| .NET SDK | C#コンパイラおよびランタイム | `/opt/homebrew/Cellar/dotnet/10.0.101/` |
| csharp-ls | LSPサーバー（シンボル検索、自動補完など） | `~/.dotnet/tools/csharp-ls` |
| DOTNET_ROOT | csharp-lsがSDKを見つけるための環境変数 | `/opt/homebrew/opt/dotnet/libexec` |
| .slnファイル | プロジェクト構造の定義（インデキシングのエントリポイント） | プロジェクトルート |
| プラグイン | Claude Codeとcsharp-lsを接続 | `~/.claude/plugins/` |

### プラグインのファイル構造

プラグイン有効化時に自動生成されるファイル：

```
~/.claude/plugins/
├── cache/claude-plugins-official/csharp-lsp/1.0.0/README.md
└── marketplaces/claude-plugins-official/plugins/csharp-lsp/
    ├── LICENSE
    └── README.md
```

---

## 4. 手動セットアップガイド

Quick Startで問題が発生した場合に参照する、ステップごとの詳細ガイドだ。

### 4-1. .NET SDKの手動インストールと検証

Homebrewでインストールできない場合は、Microsoft公式インストールスクリプトを使用する：

```bash
# 公式インストールスクリプト
curl -sSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --channel LTS
```

この場合、インストールパスが`~/.dotnet`になるため、環境変数を合わせる必要がある：

```bash
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"
```

インストールの確認：

```bash
dotnet --info
```

`dotnet --info`の出力で以下の項目を確認する：
- **Base Path** — SDKが実際にインストールされたパス
- **Runtime Environment: OS** — アーキテクチャが`arm64`（Apple Silicon）か`x64`（Intel）かを確認

### 4-2. csharp-lsの手動インストールと検証

デフォルトインストールが失敗した場合：

```bash
# キャッシュクリア後に再インストール
dotnet nuget locals all --clear
dotnet tool install --global csharp-ls

# 特定バージョンを指定してインストール
dotnet tool install --global csharp-ls --version 0.22.0
```

すでにインストール済みの場合はアップデート：

```bash
dotnet tool update --global csharp-ls
```

バイナリを直接確認：

```bash
# ファイルの存在確認
ls -la ~/.dotnet/tools/csharp-ls

# アーキテクチャ確認（arm64であること）
file ~/.dotnet/tools/csharp-ls
# 出力例: Mach-O 64-bit executable arm64
```

### 4-3. 環境変数のデバッグ

環境変数の問題が疑われるときに一つずつ確認する方法：

```bash
# 1. DOTNET_ROOTの確認
echo $DOTNET_ROOT
# 空文字列なら → 未設定（最も一般的な失敗原因）

# 2. DOTNET_ROOTパスに実際のSDKがあるか確認
ls $DOTNET_ROOT/sdk/
# 10.0.101のようなディレクトリがあるはず

# 3. csharp-lsバイナリがPATHにあるか確認
which csharp-ls
# 出力なし → ~/.dotnet/toolsがPATHにない

# 4. PATHに~/.dotnet/toolsが含まれているか確認
echo $PATH | tr ':' '\n' | grep dotnet
```

### 4-4. .slnファイルの作成（Unityプロジェクト）

Unityプロジェクトの場合、`.sln`ファイルはUnity Editorで自動生成される：

1. Unity Editorを開く
2. **Edit → Preferences → External Tools**に移動
3. **External Script Editor**を設定（Visual Studio Codeなど）
4. **Regenerate project files**をクリック

手動で作成する場合：

```bash
cd /path/to/unity-project
dotnet new sln -n MyUnityProject

# Assembly-CSharp.csprojなどを追加
dotnet sln add Assembly-CSharp.csproj
```

### 4-5. プラグインの手動有効化確認

プラグインが正しく有効化されているか確認する方法：

```bash
# グローバル設定の確認
cat ~/.claude/settings.json | grep -A2 "enabledPlugins"

# プロジェクト別設定の確認
cat .claude/settings.json | grep -A2 "enabledPlugins"

# プラグインファイルがダウンロードされたか確認
ls ~/.claude/plugins/cache/claude-plugins-official/csharp-lsp/
```

---

## 5. トラブルシューティング

### Case 1: `csharp-ls: command not found`

**原因**: `~/.dotnet/tools`がPATHに含まれていない

**解決方法**:

```bash
# 1. バイナリの存在確認
ls ~/.dotnet/tools/csharp-ls

# 2. PATHに追加（~/.zshrc）
export PATH="$PATH:$HOME/.dotnet/tools"
source ~/.zshrc

# 3. 確認
which csharp-ls
```

### Case 2: csharp-ls実行時にSDKが見つからない

**原因**: DOTNET_ROOT環境変数が未設定（最も一般的な原因）

**解決方法**:

```bash
# Apple Silicon Mac
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# Intel Mac
export DOTNET_ROOT="/usr/local/share/dotnet"

# 確認 — SDKディレクトリが見えるはず
ls $DOTNET_ROOT/sdk/
```

### Case 3: OmniSharpとの競合

**症状**: csharp-lsがインストールされているがLSPが異常動作する

**原因**: OmniSharpが同時にインストールされていると競合する可能性がある

**解決方法**:

```bash
# OmniSharpのインストール確認
dotnet tool list -g | grep omnisharp

# インストールされている場合はアンインストール
dotnet tool uninstall -g omnisharp
```

> Mono（`/opt/homebrew/bin/mono`）はcsharp-lsと競合しない。Monoがインストールされていても問題ない。
{: .prompt-info }

### Case 4: .slnファイルがあるのにシンボルインデキシングができない

**原因**: `.sln`ファイルに`.csproj`が登録されていない、または`.csproj`のパスが間違っている

**解決方法**:

```bash
# .slnに登録されたプロジェクトを確認
cat MyProject.sln | grep "\.csproj"

# 空の結果なら → .csprojの登録が必要
dotnet sln add path/to/MyProject.csproj
```

### Case 5: Claude CodeでLSP機能が動作しない

**診断順序**:

```bash
# ステップ1: csharp-ls自体が動作するか確認
csharp-ls --version

# ステップ2: DOTNET_ROOTの確認
echo $DOTNET_ROOT

# ステップ3: プラグイン有効化の確認
cat ~/.claude/settings.json

# ステップ4: .slnファイルの存在確認
ls *.sln

# ステップ5: Claude Codeの再起動
# プラグイン設定変更後は必ずClaude Codeを再起動する必要がある
```

### Case 6: Homebrew dotnetと公式インストールスクリプトのdotnetが競合

**症状**: `dotnet`は実行されるがcsharp-lsがSDKを見つけられない

**原因**: Homebrewと公式スクリプトが異なるパスにSDKをインストールし、DOTNET_ROOTが間違ったSDKを指している

**解決方法**:

```bash
# どのdotnetが実行されているか確認
which dotnet
dotnet --info

# Homebrewバージョンの場合
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# 公式スクリプトバージョンの場合
export DOTNET_ROOT="$HOME/.dotnet"

# どちらか一方だけ残すことを推奨
# Homebrewバージョンを削除
brew uninstall dotnet

# または公式スクリプトバージョンを削除
rm -rf ~/.dotnet
```

---

## 6. 新しいMacセットアップチェックリスト

新しいMacで最初からセットアップする際のチェックリストだ。コピーしてそのまま実行すればよい。

```bash
# ✅ Step 1: .NET SDKのインストール
brew install dotnet

# ✅ Step 2: 環境変数の設定（~/.zshrcに追加）
echo '' >> ~/.zshrc
echo '# .NET & csharp-ls設定' >> ~/.zshrc
echo 'export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"' >> ~/.zshrc
echo 'export PATH="$PATH:$HOME/.dotnet/tools"' >> ~/.zshrc

# ✅ Step 3: シェルのリロード
source ~/.zshrc

# ✅ Step 4: csharp-lsのインストール
dotnet tool install --global csharp-ls

# ✅ Step 5: インストールの確認
which csharp-ls          # ~/.dotnet/tools/csharp-ls
csharp-ls --version      # 0.22.0

# ✅ Step 6: Claude Codeプラグインの有効化
# ~/.claude/settings.jsonに以下の内容を追加：
# {
#   "enabledPlugins": {
#     "csharp-lsp@claude-plugins-official": true
#   }
# }

# ✅ Step 7: プロジェクトルートの.slnファイルを確認
ls *.sln
```

> **Intel Macの場合**、Step 2のDOTNET_ROOTを以下に変更：
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

---

## 7. よくある質問

### Q. OmniSharpもインストールする必要がある？

**いいえ。** csharp-lsだけで十分だ。OmniSharpをインストールしない方がむしろクリーンだ。2つのLSPサーバーが共存すると競合の可能性がある。

### Q. Monoがインストールされているが大丈夫？

**大丈夫だ。** Mono（`/opt/homebrew/bin/mono`）はcsharp-lsとは独立して動作し、競合しない。

### Q. Apple Silicon MacでRosettaは必要？

**必須ではない。** csharp-lsはarm64ネイティブバイナリとしてインストールされる。ただし、一部の.NETツールがx64のみサポートする場合があるため、Rosettaがインストールされていると互換性が向上する。

### Q. プロジェクトごとにプラグイン設定が必要？

`~/.claude/settings.json`にグローバルで設定すれば全プロジェクトに適用される。特定のプロジェクトでのみ使用したい場合は、`<プロジェクト>/.claude/settings.json`にのみ設定すればよい。

### Q. csharp-lsのアップデートはどうする？

```bash
dotnet tool update --global csharp-ls
```

---

## 8. workspaceSymbol制限事項と代替手段

### workspaceSymbolとは？

`workspace/symbol`はLSPの標準リクエストで、**ワークスペース全体からシンボルを名前で検索**する機能である。

```
クライアント → サーバー: { method: "workspace/symbol", params: { query: "GamePauseLayer" } }
サーバー → クライアント: [ { name: "GamePauseLayer", kind: Class, location: {...} }, ... ]
```

IDEでは`Ctrl+T`（Go to Symbol in Workspace）として使用される機能だ。

### Claude Codeで動作しない理由

Claude CodeのLSPツール仕様には、`workspaceSymbol`に必要な`query`パラメータが**存在しない**：

```json
{
    "operation": "workspaceSymbol",
    "filePath": "string (required)",    // ← workspaceSymbolには不要
    "line": "integer (required)",       // ← workspaceSymbolには不要
    "character": "integer (required)"   // ← workspaceSymbolには不要
    // queryパラメータなし！
}
```

結果として空クエリ（`query: ""`）が送信され、全シンボルの**最大100件のみ返却**される。大規模プロジェクトでは目的のシンボルが含まれない。

> 例：Unityプロジェクト（18,500+シンボル）で`GamePauseLayer`を検索すると、proto自動生成ファイルがアルファベット順で先に出現し、100件の制限内にゲームコードシンボルが含まれなかった。
{: .prompt-warning }

### 他のLSP operationは正常動作

| Operation | クエリ必要？ | 状態 | 備考 |
| --- | --- | --- | --- |
| `documentSymbol` | いいえ（ファイル指定） | **正常** | ファイル構造把握 |
| `hover` | いいえ（位置指定） | **正常** | 型+ドキュメント豊富 |
| `findReferences` | いいえ（位置指定） | **正常** | セマンティック検索 |
| `goToDefinition` | いいえ（位置指定） | **正常** | 正確なジャンプ |
| `goToImplementation` | いいえ（位置指定） | **正常** | インターフェース→実装 |
| `incomingCalls` / `outgoingCalls` | いいえ（位置指定） | **正常** | 呼び出し追跡 |
| `workspaceSymbol` | **はい（クエリ必須）** | **使用不可** | クエリパラメータなし |

`workspaceSymbol`だけが唯一`query`文字列を必要とするoperationであり、Claude Codeツールではこれをサポートしていない。

### 代替手段：シンボル検索戦略

#### ファイル/クラスの位置検索

| 方法 | 速度 | 精度 |
| --- | --- | --- |
| **Rider実行時:** `find_files_by_name_keyword` → `documentSymbol` | 即座（~0.1s + ~0.5s） | 100% |
| **Rider未実行:** `Glob **/ClassName.cs` → `documentSymbol` | 即座（~0.1s + ~0.5s） | 100% |
| `Grep "class ClassName"` | 高速（~1s） | 100% |
| `workspaceSymbol` | 低速（~3s） | **0%**（大規模プロジェクト） |

#### シンボル名パターン検索

| 方法 | 例 |
| --- | --- |
| **Rider:** `search_in_files_by_text "class.*Pause"` → `documentSymbol` | セマンティック検索 + 構造分析 |
| **No Rider:** `Glob **/*Pause*.cs` → 各ファイルで`documentSymbol` | ファイル検索 + 構造分析 |
| `Grep "class.*Pause"` | テキストマッチング |

#### シンボル使用箇所の検索

| 方法 | 精度 |
| --- | --- |
| `LSP findReferences` | **最高**（コード参照のみ） |
| `Grep "ClassName"` | 文字列/コメント含む |

### 推奨ワークフロー

```
┌──────────────────────────────────────────────────────────┐
│  シンボル検索最適戦略                                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  「このクラスのファイルはどこ？」                             │
│  → [Rider] find_files_by_name_keyword "ClassName"        │
│  → [No Rider] Glob **/ClassName.cs                       │
│  → LSP documentSymbol（構造確認）                          │
│                                                          │
│  「Pause関連のクラスを全部探して」                            │
│  → [Rider] search_in_files_by_text "class.*Pause"        │
│  → [No Rider] Glob **/*Pause*.cs                         │
│  → 各ファイルで LSP documentSymbol                         │
│                                                          │
│  「このシンボルはどこで使われている？」                        │
│  → LSP findReferences（ファイル+位置指定）                  │
│                                                          │
│  「このファイルの構造は？」                                  │
│  → LSP documentSymbol                                    │
│                                                          │
│  ✗ workspaceSymbol → 使用しないこと                         │
│    （クエリパラメータ未対応、100件制限）                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## おわりに

C# LSPセットアップの要は**環境変数の2行**だ：

```bash
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"  # SDKパス
export PATH="$PATH:$HOME/.dotnet/tools"                # バイナリパス
```

この2行が`.zshrc`にあり、csharp-lsがインストールされ、プラグインが有効化されていれば、Claude CodeでC#コードを完璧に分析できる。

問題が発生したら[トラブルシューティングセクション](#5-トラブルシューティング)の診断順序に従えば、ほとんどの場合解決できる。最も一般的な原因は**DOTNET_ROOTの未設定**であることだけ覚えておこう。
