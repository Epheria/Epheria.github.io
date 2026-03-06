---
title: "WindowsでClaude Codeをインストールする完全ガイド — 実践トラブルシューティング付き"
lang: ja
date: 2026-03-04 16:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Windows, Installation Guide, PowerShell, Node.js, Git, Developer Tools, AI]

difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "Windows 11でClaude Codeをインストールするには、Node.js LTS、Git、Git Bashパス環境変数の設定が必要 — Quick Start 5ステップで完了"
  - "インストール後最もよくある失敗原因はターミナル未再起動（PATH未更新）とCLAUDE_CODE_GIT_BASH_PATH環境変数の未設定"
  - "PowerShell診断スクリプト1回で現在の環境の問題点を一目で把握できる"
---

## はじめに

Claude CodeはAnthropicが提供するCLIベースのAIコーディングエージェントだ。macOS/Linuxではインストールが比較的簡単だが、**WindowsではGit Bashパス設定、PowerShell実行ポリシー、PATH問題**など、いくつかの段階で詰まることがある。

このガイドはWindows環境でClaude Codeをインストールする際に**実際に遭遇した問題と解決方法**をまとめた実践ガイドだ。Quick Startで素早くインストールするか、問題が発生したらステップバイステップの詳細ガイドを参照しよう。

---

## 1. 検証済み環境

| 項目 | バージョン/値 |
|------|------------|
| OS | Windows 11 Home (10.0.26200) |
| Node.js | v24.12.0 (LTS) |
| npm | 11.6.2 |
| Git | 2.51.0.windows.2 |
| Claude Code | @anthropic-ai/claude-code@**2.1.63** |
| デフォルトモデル | Claude Opus 4.6 (`claude-opus-4-6`) |

### 使用可能なClaudeモデル

| モデル | モデルID | 特徴 |
|--------|---------|------|
| **Opus 4.6** | `claude-opus-4-6` | 最も強力、複雑なタスクに適合 **(デフォルト)** |
| Sonnet 4.6 | `claude-sonnet-4-6` | 高速応答、一般タスクに適合 |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | 最速、シンプルなタスクに適合 |

---

## 2. Quick Start（5ステップ）

すでにNode.jsとGitがインストールされているなら、以下の5ステップですぐにインストールできる。問題が発生したら[ステップバイステップ詳細ガイド](#3-ステップバイステップ詳細ガイド)を参照しよう。

### 事前確認

PowerShellを開いて以下のコマンドで現在の状態を確認する：

```powershell
node -v          # バージョンが出る → Step 2でNode.jsをスキップ
npm -v           # バージョンが出る → npm正常
git --version    # バージョンが出る → Step 2でGitをスキップ
claude --version # バージョンが出る → すでにインストール済み！「アップグレード」セクションのみ参照
```

### Step 1. 実行ポリシー設定（初回のみ）

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Step 2. 必須プログラムのインストール

```powershell
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```

> **インストール後は必ずPowerShellターミナルを完全に閉じて新しく開く必要がある。**新しいターミナルを開くことでPATHが更新され、`node`、`git`コマンドが認識される。
{: .prompt-warning }

### Step 3. Git Bashパス環境変数設定（初回のみ）

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

> 最後の引数`"User"`は実際のユーザー名ではない。Windows環境変数の**適用範囲（Scope）**を意味するキーワードだ。自分のユーザー名に置き換えてはいけない。
{: .prompt-info }

### Step 4. Claude Codeのインストール

```powershell
# 方法A：公式スクリプト（推奨）
irm https://claude.ai/install.ps1 | iex

# 方法B：npm直接インストール（方法Aがダメな時）
npm install -g @anthropic-ai/claude-code
```

### Step 5. インストール確認

```powershell
claude --version
# 例：2.1.63 (Claude Code) ← バージョン番号が出たら成功！
```

---

## 3. ステップバイステップ詳細ガイド

Quick Startで問題が発生した場合、このセクションで各ステップの詳細なトラブルシューティングを確認しよう。

### 3-1. PowerShell実行ポリシー設定

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

設定確認：

```powershell
Get-ExecutionPolicy -List
# CurrentUser項目がRemoteSignedである必要がある
```

| ポリシー | 説明 | 推奨 |
|---------|------|-----|
| Restricted | すべてのスクリプトをブロック（Windowsのデフォルト） | |
| **RemoteSigned** | ローカルスクリプト許可、リモートは署名必要 | **推奨** |
| Unrestricted | すべてのスクリプトを許可 | セキュリティリスク |

**なぜ必要か？** Windowsはデフォルトでpowerシェルスクリプトの実行をブロック（`Restricted`）する。Claude Codeインストールスクリプトを実行するには、このポリシーを`RemoteSigned`に変更する必要がある。

---

### 3-2. Node.jsのインストール

```powershell
winget install -e --id OpenJS.NodeJS.LTS
```

インストール確認（新しいターミナルで）：

```powershell
node -v  # 例：v24.12.0
npm -v   # 例：11.6.2
```

#### wingetが使えない場合

wingetがない古いバージョンのWindowsなら手動インストール：

1. [https://nodejs.org/](https://nodejs.org/) にアクセス
2. LTSバージョンをダウンロード
3. インストーラー（.msi）を実行
4. デフォルトオプションでインストール
5. 新しいターミナルを開く

#### `node -v`で「コマンドが見つかりません」

**原因：** PATHにNode.jsパスが登録されていない。

**解決手順：**

1. ターミナルを完全に閉じて新しく開く
2. それでもダメならシステムを再起動
3. それでもダメなら手動でPATHを追加：
   - スタート → 「環境変数」で検索 → 「ユーザー環境変数」
   - Pathを編集 → `C:\Program Files\nodejs\` を追加

---

### 3-3. Gitのインストール

```powershell
winget install -e --id Git.Git
```

インストール確認：

```powershell
git --version  # 例：git version 2.51.0.windows.2
```

#### wingetが使えない場合

1. [https://gitforwindows.org/](https://gitforwindows.org/) にアクセス
2. ダウンロード後、インストーラーを実行
3. インストールオプションはデフォルトのまま（Git Bashが含まれてインストールされる）
4. 新しいターミナルを開く

---

### 3-4. Git Bashパス環境変数設定

**なぜ必要か？** Claude Codeは内部的にbashシェルを使用する。WindowsではGit Bashを使うが、自動でパスを見つけられない場合があるため、手動で指定する必要がある。

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

設定確認（新しいターミナルで）：

```powershell
echo $env:CLAUDE_CODE_GIT_BASH_PATH
# 例：C:\Program Files\Git\bin\bash.exe
```

> `"User"`パラメータの説明
>
> | 値 | 意味 | 備考 |
> |---|------|-----|
> | `"User"` | 現在ログインしているユーザーの環境変数 | **推奨（そのまま使用）** |
> | `"Machine"` | システム全体の環境変数 | 管理者権限が必要 |
> | `"Process"` | 現在のターミナルセッションでのみ有効 | ターミナルを閉じると消える |
{: .prompt-info }

#### Gitが別のパスにインストールされている場合

```powershell
# Gitインストール場所の確認
where git
# 例：C:\Program Files\Git\cmd\git.exe
# → bash.exeは同じGitフォルダのbin内にある

# 一般的なGit Bashパス：
# C:\Program Files\Git\bin\bash.exe        ← 64ビット（ほとんど）
# C:\Program Files (x86)\Git\bin\bash.exe  ← 32ビット

# 確認されたパスで環境変数を設定
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "実際のパス", "User")
```

#### WSLを使う場合（代替）

```powershell
wsl --install  # WSLインストール（初回のみ、再起動必要）
```

WSLでも可能だが、Git Bashパス設定の方が簡単なので**Git Bash方式を推奨**する。

---

### 3-5. Claude Codeのインストール

#### 方法A：公式インストールスクリプト（推奨）

```powershell
irm https://claude.ai/install.ps1 | iex
```

上記コマンドがうまくいかない時：

```powershell
# バリエーション1：scriptblockとして実行
& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) latest

# バリエーション2：CMDスクリプトを使用
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

#### 方法B：npm直接インストール（方法A失敗時）

```powershell
npm install -g @anthropic-ai/claude-code
```

> npmコマンドの文法に注意しよう：
> ```powershell
> npm install -g パッケージ名    # ✅ 正しい文法
> npm i -g パッケージ名          # ✅ 省略形
> npm --install パッケージ名     # ❌ 間違った文法
> npm -install パッケージ名      # ❌ 間違った文法
> ```
{: .prompt-warning }

---

### 3-6. インストール確認とPATH問題の解決

```powershell
claude --version
# 例：2.1.63 (Claude Code)
```

#### `claude`コマンドが見つからない場合

```powershell
# 1. ターミナルを閉じて新しく開く

# 2. npmグローバルパスを確認
npm config get prefix
# 例：C:\Users\ユーザー名\AppData\Roaming\npm

# 3. そのパスがPATHに含まれているか確認
echo $env:PATH

# 4. PATHになければ追加（$env:USERPROFILEでユーザーパスを自動補完）
[Environment]::SetEnvironmentVariable(
  "Path",
  [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:USERPROFILE\AppData\Roaming\npm",
  "User"
)

# 5. 新しいターミナルを開いて再試行
claude --version
```

#### Windowsユーザー名の確認方法

パスで`ユーザー名`を直接入力する必要がある場合：

```powershell
# 方法1：ユーザープロファイルフォルダのフルパス
echo $env:USERPROFILE
# 例：C:\Users\太郎  ← 「太郎」がユーザー名

# 方法2：ユーザー名のみ
echo $env:USERNAME
# 例：太郎

# 方法3：whoami
whoami
# 例：DESKTOP-ABC123\太郎  ← 「\」の後がユーザー名
```

> `$env:USERPROFILE`を活用すればユーザー名を知らなくてもパスを自動的に補完できるので、できるだけ直接入力の代わりにこの変数を使おう。
{: .prompt-tip }

---

## 4. インストール後の設定

### 設定ファイルの場所

| ファイル | パス | 用途 |
|---------|------|-----|
| グローバル設定 | `%USERPROFILE%\.claude\settings.json` | 言語、ステータスバーなど |
| プロジェクト設定 | `プロジェクトフォルダ\.claude\settings.local.json` | プロジェクト別権限など |
| プロジェクトコンテキスト | `プロジェクトフォルダ\CLAUDE.md` | AIに渡すルール/指示 |

### グローバル設定の例

`%USERPROFILE%\.claude\settings.json`：

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  },
  "language": "Korean"
}
```

`"language": "Korean"` 設定でClaude Codeが韓国語で応答する。

---

## 5. Claude Codeの基本的な使い方

### 実行コマンド

```powershell
# プロジェクトフォルダで対話型セッションを開始
cd C:\MyProject
claude

# 1行質問（対話型セッションなしで直接回答）
claude -p "このコードのバグを探して"

# パイプで入力を渡す
cat main.cpp | claude -p "このコードをレビューして"

# 特定モデルで実行
claude --model claude-sonnet-4-6

# 前の会話を続ける
claude --continue

# 最新の会話を再開
claude --resume
```

### 会話中のスラッシュコマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプを表示 |
| `/model` | モデルの確認/変更 |
| `/compact` | 会話コンテキストを圧縮（長い会話で便利） |
| `/clear` | 会話をリセット |
| `/cost` | 現在のセッションコストを確認 |
| `/fast` | Fastモードのトグル（同じモデル、より速い出力） |
| `/commit` | 変更をGitコミット |
| `/simplify` | 変更コードの自動レビューと改善 |
| `/batch` | 大規模コードベースの並列変更 |

> `/simplify`と`/batch`の詳細な説明は[Claudeメモリ無料開放と/simplify、/batch](/posts/ClaudeMemoryAndCodeSkills/)の記事を参照しよう。
{: .prompt-info }

---

## 6. アップグレード

### 方法A：npm update（推奨）

```powershell
npm update -g @anthropic-ai/claude-code
```

### 方法B：最新バージョンの強制インストール

```powershell
npm install -g @anthropic-ai/claude-code@latest
```

アップグレード後の確認：

```powershell
# 新しいターミナルを開いて
claude --version

# 既存の設定ファイルは自動的に維持される。
```

---

## 7. 全体診断スクリプト

どこで問題が発生したかわからない時、このスクリプトをPowerShellに貼り付ければ環境全体を一度に診断できる。

```powershell
Write-Host "=== Claude Code 環境診断 ===" -ForegroundColor Cyan

Write-Host "`n[Node.js]" -ForegroundColor Yellow
try { node -v } catch { Write-Host "  ❌ 未インストール" -ForegroundColor Red }

Write-Host "`n[npm]" -ForegroundColor Yellow
try { npm -v } catch { Write-Host "  ❌ 未インストール" -ForegroundColor Red }

Write-Host "`n[Git]" -ForegroundColor Yellow
try { git --version } catch { Write-Host "  ❌ 未インストール" -ForegroundColor Red }

Write-Host "`n[Git Bashパス]" -ForegroundColor Yellow
$gitBash = [Environment]::GetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "User")
if ($gitBash) { Write-Host "  $gitBash" } else { Write-Host "  ❌ 未設定" -ForegroundColor Red }

Write-Host "`n[実行ポリシー]" -ForegroundColor Yellow
Get-ExecutionPolicy -Scope CurrentUser

Write-Host "`n[Claude Code]" -ForegroundColor Yellow
try { claude --version } catch { Write-Host "  ❌ 未インストール" -ForegroundColor Red }

Write-Host "`n[npmグローバルパス]" -ForegroundColor Yellow
npm config get prefix
```

実行結果の例：

```
=== Claude Code 環境診断 ===

[Node.js]
v24.12.0

[npm]
11.6.2

[Git]
git version 2.51.0.windows.2

[Git Bashパス]
  C:\Program Files\Git\bin\bash.exe

[実行ポリシー]
RemoteSigned

[Claude Code]
2.1.63 (Claude Code)

[npmグローバルパス]
C:\Users\ユーザー名\AppData\Roaming\npm
```

すべての項目が正常ならインストール完了だ。赤い`❌`が表示されたら、該当セクションのトラブルシューティングを参照しよう。

---

## 8. トラブルシューティングまとめ

| 症状 | 原因 | 解決 |
|------|------|------|
| `node -v`が動かない | Node.js未インストールまたはPATH未登録 | [3-2. Node.jsインストール](#3-2-nodejsのインストール) |
| `irm ... \| iex`がブロックされる | 実行ポリシーがRestricted | [3-1. 実行ポリシー設定](#3-1-powershell実行ポリシー設定) |
| `npm --install`エラー | 間違ったnpm文法 | `npm install -g`を使用 |
| `claude`実行時にシェルエラー | Git Bashパス未設定 | [3-4. Git Bashパス設定](#3-4-git-bashパス環境変数設定) |
| `claude`コマンドがない | npmグローバルパス未登録 | [3-6. PATH問題の解決](#3-6-インストール確認とpath問題の解決) |
| すべてのコマンドが動かない | ターミナル未再起動 | **ターミナルを閉じて新しく開く** |

---

## ファイルパスまとめ

| 項目 | パス |
|------|------|
| Claude実行ファイル | `%USERPROFILE%\AppData\Roaming\npm\claude.cmd` |
| npmグローバルパッケージ | `%USERPROFILE%\AppData\Roaming\npm\` |
| Claudeグローバル設定 | `%USERPROFILE%\.claude\settings.json` |
| Claudeプロジェクト設定 | `プロジェクト\.claude\settings.local.json` |
| Git Bash | `C:\Program Files\Git\bin\bash.exe` |

---

## おわりに

WindowsでClaude Codeをインストールする際に最も多く詰まる3つのポイント：

1. **ターミナル未再起動** — PATHが更新されず、インストールしたプログラムを認識しない
2. **`CLAUDE_CODE_GIT_BASH_PATH`未設定** — Claude Codeがbashを見つけられず実行失敗
3. **`"User"`パラメータの混同** — 環境変数のScopeキーワードを自分のユーザー名と勘違い

この3つに注意すれば、ほとんどのインストール問題を解決できる。問題が発生したら[診断スクリプト](#7-全体診断スクリプト)をまず実行してみよう。

---

## References

- Anthropic. (2026). *Claude Code Documentation*. [https://docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code)
- Anthropic. (2026). *Claude Code GitHub*. [https://github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
- Node.js. *Node.js公式サイト*. [https://nodejs.org/](https://nodejs.org/)
- Git for Windows. *Git for Windows*. [https://gitforwindows.org/](https://gitforwindows.org/)
