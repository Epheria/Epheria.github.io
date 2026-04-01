---
title: "AIエージェントハーネスエンジニアリング深層解剖 — オーケストレーション設計原理とC#再構築"
lang: ja
date: 2026-04-01 18:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Harness Engineering, Agent Architecture, Tool System, Permission Model, Query Engine, AsyncGenerator, IAsyncEnumerable, Unity, CSharp, TypeScript, Orchestration, Concurrency]
difficulty: advanced
toc: true
toc_sticky: true
math: true
prerequisites:
  - /posts/ClaudeCodeInsights/
  - /posts/ClaudeCodeSourceLeak/
tldr:
  - "AIエージェントハーネスの核心はGeneratorベースのストリーミングクエリループ、Fail-Closedパーミッションパイプライン、同時性パーティショニングツール実行の3軸であり、これらのパターンは言語に依存しないオーケストレーション設計原理である"
  - "TypeScriptのAsyncGenerator → C#のIAsyncEnumerable、AbortController → CancellationTokenSource、Zod → DataAnnotationsで1:1対応し、.NET 8+コンソールアプリでコアオーケストレーションを約10,000行規模で再構築できる"
  - "Unity Editorパスではunity-cli-connectorの既存ツール発見/ルーティング/マーシャリングパターンをそのまま再利用し、ターミナルUIを完全に省略してUI Toolkitで代替できるため、オリジナルの約20%のコード量でMVP実装が可能である"
---

## はじめに

[前回のポスト](/posts/ClaudeCodeSourceLeak/)でClaude Codeのアーキテクチャ設計原理を分析した。今回の記事ではさらに一段深く入り、**ハーネスエンジニアリング（Harness Engineering）** — すなわちAIエージェントのオーケストレーション層がどのような設計原理で構築されるかを解剖する。

「ハーネス」という用語はもともとテストハーネス（test harness）に由来し、**実行対象をラップして入出力を制御するフレームワーク**を意味する。AIエージェントハーネスはLLMをラップしてツール呼び出し、権限管理、コンテキスト組立、セッション管理をオーケストレーションする層である。

この記事の目標は3つある：

1. AIエージェントハーネスの**8つのコア設計パターン**を抽出する
2. 各パターンが**なぜそのように設計されたのか**動機を分析する
3. このパターンを**C#/.NETおよびUnity Editorで再構築**する際の対応戦略を提示する

---

## 1. ハーネスエンジニアリングとは何か

### 1-1. AIエージェントハーネスの役割

AIエージェントは単にLLMにプロンプトを送って応答を受けるだけではない。実際のプロダクションレベルのエージェントは以下すべてを管理する必要がある：

| 層 | 責任 |
|----|------|
| **初期化** | 認証、設定、コンテキスト組立 |
| **会話ループ** | メッセージ管理、API呼び出し、ストリーミング |
| **ツール実行** | ツール発見、入力検証、実行、結果処理 |
| **権限制御** | パーミッション決定、セキュリティ分類、フック |
| **同時性** | 並列/直列バッチ、キャンセル伝播 |
| **復旧** | コンテキストコンパクション、トークン超過リトライ |
| **セッション** | 履歴保存、コスト追跡、テレメトリ |
| **UI** | 進捗表示、権限ダイアログ、ターミナルレンダリング |

この8つの層を統合するのがハーネスの役割である。ハーネスがなければLLMは単なるテキスト生成APIに過ぎない。

### 1-2. ハーネスの規模感

Claude Codeのようなプロダクションレベルのエージェントの場合、ハーネスコードはおよそ以下のような比重を占める：

```
典型的なAIエージェントCLI：
├── ハーネスコア（クエリループ、ツール、権限）：約15,000行
├── ツール実装（40+個）：約30,000行
├── ターミナルUI：約25,000行
├── サービス（OAuth、MCP、分析）：約20,000行
├── ユーティリティ：約30,000行
└── その他（テスト、設定、型）：約40,000行
```

この記事では**ハーネスコア約15,000行**に該当するオーケストレーションパターンに集中する。

---

## 2. パターン1 — Generatorベースストリーミングアーキテクチャ

### 2-1. 核心原理

プロダクションレベルのAIエージェントのすべての非同期フローは**Generator（非同期イテレータ）**パターンで実装するのが一般的である。ツール実行、クエリループ、フック実行すべてがこのパターンに従う。

```
// 擬似コード — Generatorベースのツール実行
Tool<Input, Output>:
  execute(input, context) → AsyncGenerator<ToolProgress<Output>>

// 擬似コード — Generatorベースのクエリループ
query(params) → AsyncGenerator<StreamEvent | Message>:
  loop:
    response = yield* callModel(...)    // モデル呼び出し（ストリーミング）
    for result in runTools(...):        // ツール実行（ストリーミング）
      yield result
    if isTerminal(response): return
```

### 2-2. なぜGeneratorなのか

**コールバック地獄回避**：Promiseチェイニングやイベントリスナーの代わりに`yield`で制御フローを明示的に表現する。

**バックプレッシャー自然対応**：`yield`はコンシューマが準備できるまでプロデューサを自動的に停止する。別途のバッファリング/フロー制御コードが不要である。

**合成可能性（Composability）**：`yield*`（委任）でサブGeneratorに委任でき、クエリループ → ツール実行 → フック実行の階層的ストリーミングが自然に合成される。

### 2-3. C#対応：IAsyncEnumerable

C# 8.0から導入された`IAsyncEnumerable<T>`はTypeScriptのAsyncGeneratorと正確に対応する。

```csharp
// TypeScript: AsyncGenerator<ToolProgress<TOutput>>
// C#: IAsyncEnumerable<ToolProgress<TOutput>>

public interface ITool<TInput, TOutput>
{
    async IAsyncEnumerable<ToolProgress<TOutput>> ExecuteAsync(
        TInput input,
        ToolUseContext context,
        [EnumeratorCancellation] CancellationToken ct)
    {
        yield return new ToolProgress<TOutput>("Starting...");

        var result = await DoWork(input, ct);

        yield return new ToolProgress<TOutput>(result);
    }
}

// クエリループも同じパターン
public async IAsyncEnumerable<StreamEvent> QueryAsync(
    QueryParams param,
    [EnumeratorCancellation] CancellationToken ct)
{
    var state = new QueryState(param.Messages);

    while (!ct.IsCancellationRequested)
    {
        // yield* 委任 → await foreach + yield return
        await foreach (var chunk in CallModelAsync(state, ct))
            yield return chunk;

        await foreach (var result in RunToolsAsync(state, ct))
            yield return result;

        if (IsTerminal(state)) yield break;

        state = ApplyRecovery(state);
    }
}
```

**差異点**：C#には`yield*`委任がないため`await foreach + yield return`で展開する必要がある。1行が3行になるが意味は同一である。

---

## 3. パターン2 — ステートマシンクエリループ

### 3-1. コア構造

AIエージェントのクエリループは明示的な状態オブジェクトを持つループ型ステートマシンとして設計するのが良い。状態オブジェクトが管理すべき主要フィールド：

```
QueryState:
  messages: Message[]           // 会話履歴
  toolUseContext: ToolUseContext // ツール実行コンテキスト
  recoveryCount: number         // 復旧試行回数
  hasAttemptedCompact: boolean  // コンパクション試行有無
  turnCount: number             // 現在のターン数
  transition: Continue | null   // 状態遷移制御
```

### 3-2. 状態遷移ダイアグラム

```
                    ┌──────────────────────┐
                    │     初期状態          │
                    │  messages = [user]    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
              ┌────→│   モデルAPI呼び出し    │
              │     │  callModel(state)    │
              │     └──────────┬───────────┘
              │                ↓
              │     ┌──────────────────────┐
              │     │  応答分析             │
              │     │  stop_reason確認      │
              │     └───┬──────┬──────┬────┘
              │         │      │      │
              │    end_turn  tool_use  max_tokens
              │         │      │      │
              │         ↓      ↓      ↓
              │     ┌──────┐ ┌────┐ ┌──────────┐
              │     │ 完了  │ │ツール│ │ 復旧戦略 │
              │     │return│ │実行 │ │コンパクション│
              │     └──────┘ └─┬──┘ │/リトライ  │
              │                │    └────┬─────┘
              │                ↓         │
              │     ┌──────────────────┐ │
              │     │ tool_result追加   │ │
              │     │ messagesに結果   │ │
              │     └────────┬─────────┘ │
              │              │           │
              └──────────────┴───────────┘
                    （次のイテレーション）
```

### 3-3. 復旧戦略の階層

| 状況 | 復旧戦略 | 動作 |
|------|----------|------|
| トークン超過（1回目） | Reactive Compact | 会話履歴を構造化された要約に圧縮 |
| トークン超過（2回目） | Max Output増加 | `maxOutputTokens`を段階的に増加 |
| トークン超過（3回目） | 強制終了 | `Terminal`状態返却 |
| コンテキストウィンドウ接近 | Auto Compact | 事前的に履歴を圧縮 |
| APIエラー | リトライ + Fallbackモデル | 指数バックオフ後、代替モデル試行 |

### 3-4. C#再構築ポイント

```csharp
public class QueryEngine
{
    public async IAsyncEnumerable<StreamEvent> RunAsync(
        QueryParams param,
        [EnumeratorCancellation] CancellationToken ct)
    {
        var state = new QueryState(param);

        while (!ct.IsCancellationRequested)
        {
            // 1. モデル呼び出し
            var response = await _apiClient.StreamAsync(
                state.BuildRequest(), ct);

            await foreach (var chunk in response)
                yield return new StreamEvent.Chunk(chunk);

            // 2. ツール抽出 + 実行
            var toolUses = state.ExtractToolUses();
            if (toolUses.Count > 0)
            {
                await foreach (var result in
                    _toolOrchestrator.RunAsync(toolUses, state.Context, ct))
                {
                    state.AddToolResult(result);
                    yield return new StreamEvent.ToolResult(result);
                }
                continue; // 次のイテレーション
            }

            // 3. 終了条件
            if (state.IsTerminal()) yield break;

            // 4. 復旧
            state = await _recoveryStrategy.ApplyAsync(state, ct);
        }
    }
}
```

---

## 4. パターン3 — ツール発見とレジストリ

### 4-1. 2つのツールソースの合成

AIエージェントは通常2つのツールソースを合成する：

```
ツールプール組立：
  1. 内蔵ツール（ビルトイン42+個） — 名前順ソート
  2. 外部ツール（MCPサーバーなど） — 名前順ソート、拒否ルールフィルタリング後追加
  → ビルトインを前方に維持（プロンプトキャッシュキーの安定性）
  → 名前衝突時ビルトイン優先
```

**ソート順序が重要な理由**：APIのプロンプトキャッシュキーは`(system_prompt, tools, model, messages_prefix)`の組み合わせで決定される。ツールリストの順序が変わるとキャッシュが壊れてコストが増加する。

### 4-2. Feature-Gated条件付きローディング

ビルドタイムフィーチャーフラグで特定ツールを条件付きで含めたり除外できる：

```
// 擬似コード — ビルドタイムフィーチャーゲーティング
cronTools = FEATURE('AGENT_TRIGGERS')
  ? [CronCreateTool, CronDeleteTool, CronListTool]
  : []

sleepTool = FEATURE('PROACTIVE') || FEATURE('ASSISTANT')
  ? loadModule('SleepTool')
  : null
```

バンドルタイムに`false`と評価されると関連コードが完全に除去（dead code elimination）される。

### 4-3. unity-cli-connectorの既存パターン

興味深いことに、**unity-cli-connectorはすでに類似したツール発見パターンを実装**している：

```csharp
// unity-cli-connectorのToolDiscovery.cs
// Reflectionベース自動発見 — [UnityCliTool]アトリビュートスキャン
[UnityCliTool(Description = "Manage Unity Editor state")]
public static class ManageEditor
{
    public class Parameters
    {
        [ToolParameter("Action to perform", Required = true)]
        public string Action { get; set; }
    }

    public static async Task<object> HandleCommand(JObject @params)
    {
        // 実装
    }
}
```

### 4-4. C#拡張設計：統合ツールレジストリ

unity-cliのパターンを拡張してエージェントレベルのツールレジストリを作成できる：

```csharp
// 統合ツールインターフェース — unity-cliの[UnityCliTool]パターン拡張
[AttributeUsage(AttributeTargets.Class)]
public class AgentToolAttribute : Attribute
{
    public string Description { get; set; }
    public string Category { get; set; }
    public bool IsConcurrencySafe { get; set; } = false;  // Fail-Closedデフォルト
    public bool IsReadOnly { get; set; } = false;
}

// Reflectionベース自動発見
public class ToolRegistry
{
    private readonly Dictionary<string, IToolHandler> _tools = new();

    public void DiscoverTools()
    {
        var toolTypes = AppDomain.CurrentDomain.GetAssemblies()
            .SelectMany(a => a.GetTypes())
            .Where(t => t.GetCustomAttribute<AgentToolAttribute>() != null);

        foreach (var type in toolTypes)
        {
            var attr = type.GetCustomAttribute<AgentToolAttribute>();
            var name = ToSnakeCase(type.Name);  // ManageEditor → manage_editor
            _tools[name] = CreateHandler(type, attr);
        }
    }

    // 既存unity-cliツール + 新しいエージェントツールを同じレジストリに統合
    public IReadOnlyList<IToolHandler> AssembleToolPool(PermissionContext ctx)
    {
        return _tools.Values
            .Where(t => !ctx.IsDenied(t.Name))
            .OrderBy(t => t.Name)    // キャッシュキーの安定性
            .ToList();
    }
}
```

---

## 5. パターン4 — Fail-Closedパーミッションパイプライン

### 5-1. 設計哲学

プロダクションレベルのAIエージェントのパーミッションシステムは**Fail-Closed**で設計すべきである — 明示的に許可されていないものはすべて拒否される。

```
// デフォルトはすべて「安全でない」
TOOL_DEFAULTS:
  isConcurrencySafe: false   // 同時実行不可
  isReadOnly: false           // 書き込み可能
  isDestructive: false
```

### 5-2. 5段階パーミッション決定フロー

```
ツール使用リクエスト
  ↓
① Config Rules（静的ルール — settings.json）
  ├── alwaysAllow: ["Read", "Glob", "Grep"]  → 即時許可
  ├── alwaysDeny: ["rm -rf"]                  → 即時拒否
  └── alwaysAsk: ["BashTool"]                 → 次の段階へ
  ↓
② Hook Execution（外部プロセスフック）
  ├── permission_requestフックが登録されていれば実行
  └── フックがallow/deny決定 → 即時返却
  ↓
③ Auto Classifier（投機的並列実行）
  ├── ASTベース静的分析で危険度分類
  └── 安全だと判断されれば自動許可
  ↓
④ Coordinator（マルチエージェント委任）
  ├── ワーカーエージェント → 親に決定委任
  └── 親が自動決定またはユーザーに転送
  ↓
⑤ Interactive Dialog（最終 — ユーザーに直接質問）
  ├── 許可（一回限り / 永久）
  ├── 拒否（フィードバック付き可能）
  └── 中断（Ctrl+C）
```

### 5-3. パーミッションソース追跡

許可/拒否が「誰が」決定したかを追跡することが重要である：

```
許可ソース：
  - hook（フック自動許可）
  - user（ユーザー手動許可、永久かどうか）
  - classifier（分類器自動許可）

拒否ソース：
  - hook（フックブロック）
  - user_abort（Ctrl+C）
  - user_reject（拒否 + 理由提供）
```

### 5-4. C#再構築

```csharp
public class PermissionPipeline
{
    private readonly PermissionConfig _config;
    private readonly IHookRunner _hooks;
    private readonly IBashClassifier _classifier;

    public async Task<PermissionDecision> DecideAsync(
        IToolHandler tool, object input, CancellationToken ct)
    {
        // ① 静的ルール
        var configResult = _config.Check(tool.Name, input);
        if (configResult.IsDecisive) return configResult.Decision;

        // ② フック実行
        var hookResult = await _hooks.RunPermissionHooksAsync(
            tool.Name, input, ct);
        if (hookResult != null) return hookResult;

        // ③ 分類器（並列投機）
        using var cts = CancellationTokenSource
            .CreateLinkedTokenSource(ct);
        var classifierTask = _classifier.ClassifyAsync(
            tool, input, cts.Token);

        // ④ ユーザーダイアログ（分類器が先に終われば​スキップ）
        var winner = await Task.WhenAny(
            classifierTask,
            ShowDialogAsync(tool, input, ct));

        cts.Cancel(); // 負けた方をキャンセル
        return await winner;
    }
}
```

**キーテクニック**：③番分類器と⑤番ダイアログを`Task.WhenAny`で**レース（race）**させる。分類器が先に「安全」と判断すればユーザーダイアログを表示しない。ユーザーが先に決定すれば分類器をキャンセルする。

---

## 6. パターン5 — 同時性パーティショニング

### 6-1. 問題：ツール間の衝突

モデルが一度に複数のツールを呼び出すことは一般的である：

```
Assistant Response:
  tool_use[1]: Read("config.json")      ← 読み取り専用
  tool_use[2]: Read("package.json")     ← 読み取り専用
  tool_use[3]: Edit("config.json", ...) ← config.jsonを修正！
  tool_use[4]: Grep("TODO", "src/")     ← 読み取り専用
```

1、2、4番は並列実行可能だが、3番は1番と衝突する（同じファイルの読み書き）。

### 6-2. 解法：隣接バッチパーティショニング

ツール呼び出しリストを順番にスキャンしながら、連続した同時性安全なツールを1つの並列バッチにまとめる：

```
// 擬似コード — 隣接バッチパーティショニング
partitionToolCalls(toolUses):
  for each toolUse:
    isSafe = tool.isConcurrencySafe(input)
    if isSafe AND lastBatch.isSafe:
      lastBatch.add(toolUse)      // 前のバッチに合流（並列）
    else:
      newBatch(isSafe, [toolUse]) // 新しいバッチ開始
```

上記の例でのパーティショニング結果：

```
Batch 1 [parallel]:  Read("config.json"), Read("package.json")
Batch 2 [serial]:    Edit("config.json", ...)
Batch 3 [parallel]:  Grep("TODO", "src/")
```

### 6-3. Fail-Closedデフォルト

ツールが自らを`isConcurrencySafe: true`と宣言しない限り、デフォルトで直列バッチに入る。新しいツールを追加する際に同時性安全性を忘れても**安全な方向で動作**する。

### 6-4. C#実装：Channelベース並列実行

```csharp
public async IAsyncEnumerable<ToolResult> RunToolsAsync(
    IReadOnlyList<ToolUseBlock> blocks,
    ToolUseContext context,
    [EnumeratorCancellation] CancellationToken ct)
{
    foreach (var batch in PartitionByConcurrency(blocks))
    {
        if (batch.IsConcurrencySafe)
        {
            // 並列実行：Channelで結果収集
            var channel = Channel.CreateUnbounded<ToolResult>();

            var tasks = batch.Blocks.Select(async block =>
            {
                var result = await ExecuteSingleToolAsync(block, context, ct);
                await channel.Writer.WriteAsync(result, ct);
            });

            _ = Task.WhenAll(tasks)
                .ContinueWith(_ => channel.Writer.Complete());

            await foreach (var result in channel.Reader.ReadAllAsync(ct))
                yield return result;
        }
        else
        {
            // 直列実行
            foreach (var block in batch.Blocks)
                yield return await ExecuteSingleToolAsync(
                    block, context, ct);
        }
    }
}

private static IEnumerable<ToolBatch> PartitionByConcurrency(
    IReadOnlyList<ToolUseBlock> blocks)
{
    var current = new ToolBatch();

    foreach (var block in blocks)
    {
        var isSafe = block.Tool.IsConcurrencySafe;

        if (current.Blocks.Count > 0 &&
            current.IsConcurrencySafe != isSafe)
        {
            yield return current;
            current = new ToolBatch();
        }

        current.IsConcurrencySafe = isSafe;
        current.Blocks.Add(block);
    }

    if (current.Blocks.Count > 0)
        yield return current;
}
```

---

## 7. パターン6 — 階層的キャンセル伝播

### 7-1. AbortControllerツリー

AIエージェントにおけるキャンセルは階層的に伝播されなければならない：

```
sessionController（セッション寿命）
  ↓
queryController（クエリ寿命）
  ↓
toolBatchController（バッチ寿命）
  ├── toolA.controller
  ├── toolB.controller
  └── toolC.controller
       ↓
  siblingController（兄弟ツール — 1つが失敗すると残りをキャンセル）
```

### 7-2. C#対応：LinkedTokenSource

C#の`CancellationTokenSource.CreateLinkedTokenSource`は正確に同じ役割を果たす。

```csharp
// セッションレベル
using var sessionCts = new CancellationTokenSource();

// クエリレベル（セッションにリンク）
using var queryCts = CancellationTokenSource
    .CreateLinkedTokenSource(sessionCts.Token);

// バッチレベル（クエリにリンク）
using var batchCts = CancellationTokenSource
    .CreateLinkedTokenSource(queryCts.Token);

// 兄弟ツール（バッチにリンク）
using var siblingCts = CancellationTokenSource
    .CreateLinkedTokenSource(batchCts.Token);

// 1つのツールが失敗したら兄弟をキャンセル
try { await toolA.ExecuteAsync(input, siblingCts.Token); }
catch { siblingCts.Cancel(); throw; }
```

**TypeScript vs C# 対応表：**

| TypeScript | C# |
|---|---|
| `new AbortController()` | `new CancellationTokenSource()` |
| `controller.signal` | `cts.Token` |
| `controller.abort()` | `cts.Cancel()` |
| `signal.aborted` | `token.IsCancellationRequested` |
| `signal.addEventListener('abort', ...)` | `token.Register(...)` |

---

## 8. パターン7 — フックパイプライン（Pre/Post Tool Hooks）

### 8-1. フックの役割

フックはツール実行前後に**外部プロセスを実行**してツールの動作を観察、修正、ブロックできる拡張ポイントである。

```
Pre-Tool Hook
  ↓（ブロック可能）
ツール実行
  ↓
Post-Tool Hook
  ↓（結果修正可能、継続ブロック可能）
次のステップ
```

### 8-2. フックイベントマッチャータイプ

フックは様々な条件でトリガーできる：

```
マッチャータイプ：
  - event: 特定イベントタイプ（PreToolUse、PostToolUseなど）
  - tool: 特定ツール名（BashTool、Editなど）
  - always: すべてのツール実行
  - prompt: プロンプトパターンマッチング
```

### 8-3. Post-Toolフックの結果タイプ

Post-Toolフックが返却できる結果：

```
- ブロックエラー：ツール実行をエラーとして処理
- 継続ブロック：追加ツール実行を防止
- 追加コンテキスト注入：モデルに追加情報を伝達
- 結果修正：ツール出力を変形
- 進捗メッセージ：UIにメッセージ表示
```

### 8-4. C#実装：イベントベースフックシステム

```csharp
public class HookPipeline
{
    private readonly List<IHookHandler> _handlers = new();

    public async Task<HookResult> RunPreToolHooksAsync(
        string toolName, object input, CancellationToken ct)
    {
        foreach (var handler in _handlers.Where(h => h.Matches(toolName)))
        {
            var result = await handler.OnBeforeToolAsync(toolName, input, ct);

            if (result.IsBlocking)
                return HookResult.Block(result.Message);

            if (result.HasModifiedInput)
                input = result.ModifiedInput;
        }

        return HookResult.Continue(input);
    }

    public async Task<HookResult> RunPostToolHooksAsync(
        string toolName, object input, object output, CancellationToken ct)
    {
        foreach (var handler in _handlers.Where(h => h.Matches(toolName)))
        {
            var result = await handler.OnAfterToolAsync(
                toolName, input, output, ct);

            if (result.ShouldStopContinuation)
                return HookResult.StopContinuation(result.Message);

            if (result.HasModifiedOutput)
                output = result.ModifiedOutput;
        }

        return HookResult.Continue(output);
    }
}
```

---

## 9. パターン8 — 依存性注入とテスト可能性

### 9-1. QueryDeps — テスト境界

AIエージェントハーネス設計で最も重要なパターンの一つは**クエリ依存性インターフェース**である：

```
// 擬似コード — クエリ依存性分離
QueryDeps:
  callModel: (messages) → stream    // API呼び出し
  compact: (messages) → messages    // コンパクション
  uuid: () → string                 // UUID生成

// プロダクション：実際のAPIクライアント
productionDeps():
  callModel = realApiStreamer
  compact = realCompaction
  uuid = crypto.randomUUID

// テスト：モッキング
testDeps(mockResponses):
  callModel = createMockStreamer(mockResponses)
  compact = identity
  uuid = sequentialUUID
```

これにより**実際のAPIを呼び出さずにクエリループのステートマシンロジックをテスト**できる。

### 9-2. ToolUseContext — ランタイムコンテキスト注入

すべてのツールが受け取る実行コンテキストはランタイム依存性の集合である：

```
ToolUseContext:
  options:
    commands: Command[]          // 使用可能なコマンド
    tools: Tools                 // 全ツールリスト
    mcpClients: MCPConnection[]  // MCPサーバー接続
    refreshTools: () → Tools     // ツールリスト更新関数
  abortController               // キャンセル制御
  fileCache                     // ファイル読み込みキャッシュ
  getAppState() / setAppState() // グローバル状態アクセス
```

### 9-3. C#対応：VContainerまたはMS DI

```csharp
// Unity Editorパス — VContainer使用
public class AgentLifetimeScope : LifetimeScope
{
    protected override void Configure(IContainerBuilder builder)
    {
        // コアサービス
        builder.Register<IQueryEngine, QueryEngine>(Lifetime.Singleton);
        builder.Register<IToolRegistry, ToolRegistry>(Lifetime.Singleton);
        builder.Register<IPermissionPipeline, PermissionPipeline>(Lifetime.Singleton);
        builder.Register<IHookPipeline, HookPipeline>(Lifetime.Singleton);

        // APIクライアント（交換可能）
        builder.Register<IAnthropicClient, HttpAnthropicClient>(Lifetime.Singleton);

        // テスト時 → MockAnthropicClientに交換
    }
}

// .NETコンソールパス — Microsoft.Extensions.DependencyInjection
var services = new ServiceCollection()
    .AddSingleton<IQueryEngine, QueryEngine>()
    .AddSingleton<IToolRegistry, ToolRegistry>()
    .AddSingleton<IAnthropicClient, HttpAnthropicClient>()
    .BuildServiceProvider();
```

---

## 10. 全体アーキテクチャ再構築比較

### 10-1. メッセージフロー — オリジナル vs C#再構築

**オリジナル（TypeScript/Bun）推定フロー：**

```
stdin → Ink REPL → QueryEngine → generatorループ
  → callModel() → Anthropic API（SSE）
  → extractToolUses()
  → partitionByConcurrency()
  → runTools（parallel/serial）
    → checkPermissions() → permission pipeline
    → preToolHooks()
    → tool.execute() → AsyncGenerator
    → postToolHooks()
  → yield tool_result
  → 次のイテレーションまたはTerminal
```

**C#再構築（パスA — .NET CLI）：**

```
stdin → Spectre.Console REPL → QueryEngine → IAsyncEnumerable
  → CallModelAsync() → HttpClient + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync()（Channel<T>ベース）
    → PermissionPipeline.DecideAsync()
    → HookPipeline.RunPreToolHooksAsync()
    → tool.ExecuteAsync() → IAsyncEnumerable
    → HookPipeline.RunPostToolHooksAsync()
  → yield return ToolResult
  → continueまたはyield break
```

**C#再構築（パスB — Unity Editor）：**

```
EditorWindow UI → QueryEngine → UniTask
  → CallModelAsync() → UnityWebRequest + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync()（UniTask.WhenAll）
    → PermissionPipeline（EditorUtility.DisplayDialog）
    → HookPipeline
    → tool.HandleCommand() ← unity-cli-connectorツール再利用！
    → PostToolHooks
  → ToolResult → EditorWindow更新
  → 次のイテレーション
```

### 10-2. 1:1対応マッピングテーブル

| エージェントパターン（TypeScript） | .NET CLI（C#） | Unity Editor（C#） |
|---|---|---|
| `AsyncGenerator<T>` | `IAsyncEnumerable<T>` | `UniTask` + callback |
| `AbortController` | `CancellationTokenSource` | `CancellationTokenSource` |
| `Zod Schema` | `DataAnnotations` + source gen | `[ToolParameter]`（既存） |
| `feature()`（ビルドタイム） | `#if FEATURE_X` | `#if UNITY_EDITOR` |
| `ToolUseContext` | `IServiceProvider` | `VContainer` |
| ターミナルUI（Ink） | `Spectre.Console` | **UI Toolkit**（ネイティブ） |
| `memoize()` | `Lazy<T>` | `Lazy<T>` |
| `process.env` | `Environment.GetEnvironmentVariable` | `EditorPrefs` |
| ファイルキャッシュ | `ConcurrentDictionary` | `Dictionary`（エディタシングルスレッド） |
| `Process`（外部プロセス） | `System.Diagnostics.Process` | `EditorCoroutineUtility` |

### 10-3. コード量推定

| モジュール | オリジナル（TS）推定 | .NET CLI | Unity Editor |
|---|---|---|---|
| クエリエンジン | 約1,700行 | 約1,200行 | 約800行 |
| ツールシステム（コア） | 約1,200行 | 約500行 | 約300行（既存再利用） |
| パーミッションシステム | 約2,500行 | 約800行 | 約500行 |
| フックシステム | 約1,000行 | 約400行 | 約300行 |
| 同時性制御 | 約500行 | 約300行 | 約200行 |
| ツール実装（42個） | 約30,000行 | 約4,000行 | 約1,000行（既存18個再利用） |
| ターミナルUI | 約25,000行 | 約2,000行 | **0行**（UI Toolkit） |
| コンテキスト/設定 | 約2,000行 | 約600行 | 約400行 |
| コスト/テレメトリ | 約800行 | 約300行 | 約200行 |
| **合計** | **約65,000行** | **約10,100行** | **約3,700行** |

---

## 11. Unity Editorパスの具体的なメリット

### 11-1. unity-cli-connectorがすでに提供しているもの

unity-cli-connector（`com.youngwoocho02.unity-cli-connector` v0.2.12）はハーネスの下部インフラをすでに備えている：

| ハーネスパターン | unity-cli-connector実装体 |
|---|---|
| **ツール発見** | `ToolDiscovery.cs` — Reflection + `[UnityCliTool]`スキャン |
| **コマンドルーティング** | `CommandRouter.cs` — SemaphoreSlim直列化 |
| **HTTPサーバー** | `HttpServer.cs` — ローカルPOST `/command` |
| **メインスレッドマーシャリング** | `ConcurrentQueue<WorkItem>` + `EditorApplication.update` |
| **パラメータスキーマ** | `[ToolParameter]`アトリビュートベース自動生成 |
| **内蔵ツール18個** | manage_editor、execute_csharp、read_console、run_testsなど |

### 11-2. 追加実装範囲

```
既存unity-cli-connector
  │
  ├── ToolDiscovery（あり） ← ツールレジストリの基盤
  ├── CommandRouter（あり） ← ツール実行パイプラインの基盤
  ├── 18 Built-in Tools（あり） ← ツール実装の基盤
  │
  └── 追加実装必要：
       ├── QueryEngine（クエリステートマシンループ）
       ├── AnthropicApiClient（SSEストリーミング）
       ├── PermissionManager（Config + Dialog）
       ├── HookPipeline（Pre/Postフック）
       ├── ConcurrencyPartitioner（バッチ分割）
       ├── ContextAssembler（CLAUDE.md + git）
       └── EditorWindow UI（会話インターフェース）
```

### 11-3. Unity固有のメリット

1. **Editor API直接アクセス** — `AssetDatabase.Refresh()`、`EditorApplication.isPlaying`などをHTTPプロキシなしで呼び出し
2. **コンパイルイベント購読** — `CompilationPipeline.compilationFinished`にフック接続
3. **Inspector統合** — ツール実行結果をInspectorで可視化
4. **ScriptableObject設定** — パーミッションルールをエディタで視覚的に編集
5. **Play Mode統合** — ランタイム検証をクエリループに自然に統合

---

## 12. 実践例：Unity Editor用最小クエリエンジン

このセクションでは実際に動作する最小クエリエンジンのスケルトンを示す。

```csharp
/// <summary>
/// AIエージェントハーネスのコアパターンをUnity Editorにポーティングした最小クエリエンジン
/// パターン：Generatorベースループ、同時性パーティショニング、Fail-Closedパーミッション
/// </summary>
public class UnityQueryEngine
{
    private readonly IAnthropicClient _api;
    private readonly ToolRegistry _tools;
    private readonly PermissionPipeline _permissions;
    private readonly HookPipeline _hooks;

    public async UniTask RunQueryLoopAsync(
        List<Message> messages,
        string systemPrompt,
        CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            // ── 1. モデル呼び出し（SSEストリーミング） ──
            var response = await _api.CreateMessageAsync(
                new Request
                {
                    Model = "claude-sonnet-4-6",
                    System = systemPrompt,
                    Messages = messages,
                    Tools = _tools.GetToolSchemas(),
                    MaxTokens = 8192,
                },
                ct);

            messages.Add(response.ToAssistantMessage());

            // ── 2. ツール使用抽出 ──
            var toolUses = response.ExtractToolUses();
            if (toolUses.Count == 0) break; // ツールなし → 会話終了

            // ── 3. 同時性パーティショニング ──
            var batches = PartitionByConcurrency(toolUses);
            var toolResults = new List<ToolResultBlock>();

            foreach (var batch in batches)
            {
                if (batch.IsConcurrencySafe)
                {
                    // 並列実行
                    var tasks = batch.Blocks.Select(block =>
                        ExecuteToolWithPipelineAsync(block, ct));
                    var results = await UniTask.WhenAll(tasks);
                    toolResults.AddRange(results);
                }
                else
                {
                    // 直列実行
                    foreach (var block in batch.Blocks)
                    {
                        var result = await ExecuteToolWithPipelineAsync(
                            block, ct);
                        toolResults.Add(result);
                    }
                }
            }

            // ── 4. 結果をメッセージに追加 ──
            messages.Add(new Message
            {
                Role = "user",
                Content = toolResults.Select(r => r.ToContentBlock()).ToList()
            });

            // ── 5. 次のイテレーション ──
        }
    }

    private async UniTask<ToolResultBlock> ExecuteToolWithPipelineAsync(
        ToolUseBlock block, CancellationToken ct)
    {
        var tool = _tools.FindByName(block.Name);

        // ① パーミッション決定（Fail-Closed）
        var permission = await _permissions.DecideAsync(tool, block.Input, ct);
        if (permission.IsDenied)
            return ToolResultBlock.Error(block.Id, permission.DenyMessage);

        // ② Pre-toolフック
        var preHook = await _hooks.RunPreToolHooksAsync(
            block.Name, block.Input, ct);
        if (preHook.IsBlocking)
            return ToolResultBlock.Error(block.Id, preHook.BlockMessage);

        // ③ ツール実行
        try
        {
            var result = await tool.HandleCommand(
                preHook.ModifiedInput ?? block.Input, ct);

            // ④ Post-toolフック
            var postHook = await _hooks.RunPostToolHooksAsync(
                block.Name, block.Input, result, ct);

            return ToolResultBlock.Success(
                block.Id, postHook.ModifiedOutput ?? result);
        }
        catch (Exception ex)
        {
            return ToolResultBlock.Error(block.Id, ex.Message);
        }
    }
}
```

---

## 13. まとめ — ハーネスエンジニアリングの8つの原則

AIエージェントハーネスから抽出した設計原則をまとめる。これらの原則は**言語とフレームワークに独立**している。

| # | 原則 | 核心的な理由 |
|---|------|-------------|
| 1 | **Generatorストリーミング** | バックプレッシャー自然対応、合成可能 |
| 2 | **ステートマシンクエリループ** | 復旧戦略、デバッグ容易 |
| 3 | **Reflectionツール発見** | プラグイン拡張、dead code除去 |
| 4 | **Fail-Closedパーミッション** | セキュリティデフォルト、段階的緩和 |
| 5 | **同時性パーティショニング** | 安全性とパフォーマンスのバランス |
| 6 | **階層的キャンセル伝播** | リソースリーク防止、クリーンな終了 |
| 7 | **Pre/Postフックパイプライン** | 関心事の分離、外部拡張性 |
| 8 | **依存性注入境界** | テスト可能性、交換容易 |

この8つのパターンを理解すれば、**どのAIエージェントハーネスでも**その構造を読み、拡張し、再構築できる。

---

## 参考資料

- [Claude Code アーキテクチャ分析](/posts/ClaudeCodeSourceLeak/) — 設計原理推論分析
- [Claude Code インサイト](/posts/ClaudeCodeInsights/) — Claude Codeの基本活用法
- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — 公式ツール使用ガイド
- [unity-cli-connector](https://github.com/youngwoocho02/unity-cli) — Unity Editorリモート制御CLI
- [IAsyncEnumerable in .NET](https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/generate-consume-asynchronous-stream) — C#非同期ストリームガイド
