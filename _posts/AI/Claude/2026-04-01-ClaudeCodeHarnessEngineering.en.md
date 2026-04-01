---
title: "Deep Dissection of AI Agent Harness Engineering — Orchestration Design Principles and C# Reconstruction"
lang: en
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
  - "The core of AI agent harnesses consists of three axes: Generator-based streaming query loops, Fail-Closed permission pipelines, and concurrency-partitioned tool execution — these patterns are language-independent orchestration design principles"
  - "TypeScript's AsyncGenerator maps 1:1 to C#'s IAsyncEnumerable, AbortController to CancellationTokenSource, Zod to DataAnnotations — the core orchestration can be reconstructed in ~10,000 lines as a .NET 8+ console app"
  - "For the Unity Editor path, you can reuse unity-cli-connector's existing tool discovery/routing/marshalling patterns while completely replacing the terminal UI with UI Toolkit, enabling MVP implementation with ~20% of the original code volume"
---

## Introduction

In the [previous post](/posts/ClaudeCodeSourceLeak/), we analyzed the architectural design principles of Claude Code. In this post, we go one level deeper to dissect **Harness Engineering** — the design principles behind how an AI agent's orchestration layer is constructed.

The term "harness" originally comes from test harness, meaning **a framework that wraps an execution target to control its input/output**. An AI agent harness is the layer that wraps the LLM to orchestrate tool calls, permission management, context assembly, and session management.

This post has three goals:

1. Extract **8 core design patterns** from AI agent harnesses
2. Analyze **why each pattern is designed that way** — the motivations
3. Present mapping strategies for **reconstructing these patterns in C#/.NET and Unity Editor**

---

## 1. What is Harness Engineering

### 1-1. The Role of an AI Agent Harness

An AI agent is not simply about sending prompts to an LLM and receiving responses. A production-level agent must manage all of the following:

| Layer | Responsibility |
|-------|---------------|
| **Initialization** | Authentication, configuration, context assembly |
| **Conversation Loop** | Message management, API calls, streaming |
| **Tool Execution** | Tool discovery, input validation, execution, result handling |
| **Permission Control** | Permission decisions, security classification, hooks |
| **Concurrency** | Parallel/serial batching, cancellation propagation |
| **Recovery** | Context compaction, token overflow retry |
| **Session** | History storage, cost tracking, telemetry |
| **UI** | Progress display, permission dialogs, terminal rendering |

Integrating these 8 layers is the harness's role. Without a harness, the LLM is merely a text-generating API.

### 1-2. Scale of a Harness

For a production-level agent like Claude Code, the harness code roughly accounts for the following proportions:

```
Typical AI Agent CLI:
├── Harness Core (query loop, tools, permissions): ~15,000 lines
├── Tool Implementations (40+): ~30,000 lines
├── Terminal UI: ~25,000 lines
├── Services (OAuth, MCP, analytics): ~20,000 lines
├── Utilities: ~30,000 lines
└── Other (tests, config, types): ~40,000 lines
```

This post focuses on the orchestration patterns corresponding to the **~15,000 lines of harness core**.

---

## 2. Pattern 1 — Generator-Based Streaming Architecture

### 2-1. Core Principle

All asynchronous flows in a production-level AI agent are typically implemented using the **Generator (async iterator)** pattern. Tool execution, query loops, and hook execution all follow this pattern.

```
// Pseudocode — Generator-based tool execution
Tool<Input, Output>:
  execute(input, context) → AsyncGenerator<ToolProgress<Output>>

// Pseudocode — Generator-based query loop
query(params) → AsyncGenerator<StreamEvent | Message>:
  loop:
    response = yield* callModel(...)    // Model call (streaming)
    for result in runTools(...):        // Tool execution (streaming)
      yield result
    if isTerminal(response): return
```

### 2-2. Why Generators

**Avoiding Callback Hell**: Instead of Promise chaining or event listeners, control flow is explicitly expressed with `yield`.

**Natural Backpressure Support**: `yield` automatically pauses the producer until the consumer is ready. No separate buffering/flow control code is needed.

**Composability**: `yield*` (delegation) allows delegating to sub-Generators, enabling natural composition of hierarchical streaming: query loop → tool execution → hook execution.

### 2-3. C# Mapping: IAsyncEnumerable

C# 8.0's `IAsyncEnumerable<T>` maps exactly to TypeScript's AsyncGenerator.

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

// Query loop follows the same pattern
public async IAsyncEnumerable<StreamEvent> QueryAsync(
    QueryParams param,
    [EnumeratorCancellation] CancellationToken ct)
{
    var state = new QueryState(param.Messages);

    while (!ct.IsCancellationRequested)
    {
        // yield* delegation → await foreach + yield return
        await foreach (var chunk in CallModelAsync(state, ct))
            yield return chunk;

        await foreach (var result in RunToolsAsync(state, ct))
            yield return result;

        if (IsTerminal(state)) yield break;

        state = ApplyRecovery(state);
    }
}
```

**Difference**: C# doesn't have `yield*` delegation, so it must be expanded to `await foreach + yield return`. One line becomes three, but the semantics are identical.

---

## 3. Pattern 2 — State Machine Query Loop

### 3-1. Core Structure

An AI agent's query loop should be designed as a loop-based state machine with an explicit state object. Key fields the state object must manage:

```
QueryState:
  messages: Message[]           // Conversation history
  toolUseContext: ToolUseContext // Tool execution context
  recoveryCount: number         // Recovery attempt count
  hasAttemptedCompact: boolean  // Whether compaction was attempted
  turnCount: number             // Current turn count
  transition: Continue | null   // State transition control
```

### 3-2. State Transition Diagram

```
                    ┌──────────────────────┐
                    │    Initial State      │
                    │  messages = [user]    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
              ┌────→│   Model API Call      │
              │     │  callModel(state)    │
              │     └──────────┬───────────┘
              │                ↓
              │     ┌──────────────────────┐
              │     │  Response Analysis    │
              │     │  Check stop_reason   │
              │     └───┬──────┬──────┬────┘
              │         │      │      │
              │    end_turn  tool_use  max_tokens
              │         │      │      │
              │         ↓      ↓      ↓
              │     ┌──────┐ ┌────┐ ┌──────────┐
              │     │ Done  │ │Tool│ │ Recovery  │
              │     │return│ │Exec│ │Compact/   │
              │     └──────┘ └─┬──┘ │Retry     │
              │                │    └────┬─────┘
              │                ↓         │
              │     ┌──────────────────┐ │
              │     │ Add tool_result   │ │
              │     │ to messages       │ │
              │     └────────┬─────────┘ │
              │              │           │
              └──────────────┴───────────┘
                    (Next iteration)
```

### 3-3. Recovery Strategy Layers

| Situation | Recovery Strategy | Behavior |
|-----------|-------------------|----------|
| Token overflow (1st) | Reactive Compact | Compress conversation history into structured summary |
| Token overflow (2nd) | Increase Max Output | Gradually increase `maxOutputTokens` |
| Token overflow (3rd) | Forced termination | Return `Terminal` state |
| Context window approaching | Auto Compact | Proactively compress history |
| API error | Retry + Fallback model | Exponential backoff then try alternative model |

### 3-4. C# Reconstruction Points

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
            // 1. Model call
            var response = await _apiClient.StreamAsync(
                state.BuildRequest(), ct);

            await foreach (var chunk in response)
                yield return new StreamEvent.Chunk(chunk);

            // 2. Extract tools + execute
            var toolUses = state.ExtractToolUses();
            if (toolUses.Count > 0)
            {
                await foreach (var result in
                    _toolOrchestrator.RunAsync(toolUses, state.Context, ct))
                {
                    state.AddToolResult(result);
                    yield return new StreamEvent.ToolResult(result);
                }
                continue; // Next iteration
            }

            // 3. Termination condition
            if (state.IsTerminal()) yield break;

            // 4. Recovery
            state = await _recoveryStrategy.ApplyAsync(state, ct);
        }
    }
}
```

---

## 4. Pattern 3 — Tool Discovery and Registry

### 4-1. Composing Two Tool Sources

AI agents typically compose two tool sources:

```
Tool Pool Assembly:
  1. Built-in tools (42+ built-ins) — sorted by name
  2. External tools (MCP servers, etc.) — sorted by name, added after deny rule filtering
  → Keep built-ins at the front (prompt cache key stability)
  → On name collision, built-ins take priority
```

**Why ordering matters**: The API's prompt cache key is determined by the `(system_prompt, tools, model, messages_prefix)` combination. If the tool list order changes, the cache breaks and costs increase.

### 4-2. Feature-Gated Conditional Loading

Build-time feature flags can conditionally include/exclude specific tools:

```
// Pseudocode — Build-time feature gating
cronTools = FEATURE('AGENT_TRIGGERS')
  ? [CronCreateTool, CronDeleteTool, CronListTool]
  : []

sleepTool = FEATURE('PROACTIVE') || FEATURE('ASSISTANT')
  ? loadModule('SleepTool')
  : null
```

When evaluated as `false` at bundle time, the related code is completely removed (dead code elimination).

### 4-3. unity-cli-connector's Existing Pattern

Interestingly, **unity-cli-connector already implements a similar tool discovery pattern**:

```csharp
// unity-cli-connector's ToolDiscovery.cs
// Reflection-based auto-discovery — [UnityCliTool] attribute scan
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
        // Implementation
    }
}
```

### 4-4. C# Extension Design: Unified Tool Registry

We can extend unity-cli's pattern to create an agent-level tool registry:

```csharp
// Unified tool interface — extending unity-cli's [UnityCliTool] pattern
[AttributeUsage(AttributeTargets.Class)]
public class AgentToolAttribute : Attribute
{
    public string Description { get; set; }
    public string Category { get; set; }
    public bool IsConcurrencySafe { get; set; } = false;  // Fail-Closed default
    public bool IsReadOnly { get; set; } = false;
}

// Reflection-based auto-discovery
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

    // Unify existing unity-cli tools + new agent tools in the same registry
    public IReadOnlyList<IToolHandler> AssembleToolPool(PermissionContext ctx)
    {
        return _tools.Values
            .Where(t => !ctx.IsDenied(t.Name))
            .OrderBy(t => t.Name)    // Cache key stability
            .ToList();
    }
}
```

---

## 5. Pattern 4 — Fail-Closed Permission Pipeline

### 5-1. Design Philosophy

A production-level AI agent's permission system must be designed as **Fail-Closed** — everything not explicitly allowed is denied.

```
// Defaults are all "unsafe"
TOOL_DEFAULTS:
  isConcurrencySafe: false   // Concurrent execution not allowed
  isReadOnly: false           // Writable
  isDestructive: false
```

### 5-2. 5-Stage Permission Decision Flow

```
Tool Use Request
  ↓
① Config Rules (static rules — settings.json)
  ├── alwaysAllow: ["Read", "Glob", "Grep"]  → Immediate allow
  ├── alwaysDeny: ["rm -rf"]                  → Immediate deny
  └── alwaysAsk: ["BashTool"]                 → Next stage
  ↓
② Hook Execution (external process hooks)
  ├── Execute if permission_request hook is registered
  └── Hook decides allow/deny → Immediate return
  ↓
③ Auto Classifier (speculative parallel execution)
  ├── Risk classification via AST-based static analysis
  └── Auto-allow if determined safe
  ↓
④ Coordinator (multi-agent delegation)
  ├── Worker agent → delegates decision to parent
  └── Parent auto-decides or forwards to user
  ↓
⑤ Interactive Dialog (final — directly ask user)
  ├── Allow (one-time / permanent)
  ├── Deny (with feedback possible)
  └── Abort (Ctrl+C)
```

### 5-3. Permission Source Tracking

Tracking "who" made the allow/deny decision is important:

```
Allow Sources:
  - hook (hook auto-allow)
  - user (manual user allow, permanent or not)
  - classifier (classifier auto-allow)

Deny Sources:
  - hook (hook block)
  - user_abort (Ctrl+C)
  - user_reject (deny + reason provided)
```

### 5-4. C# Reconstruction

```csharp
public class PermissionPipeline
{
    private readonly PermissionConfig _config;
    private readonly IHookRunner _hooks;
    private readonly IBashClassifier _classifier;

    public async Task<PermissionDecision> DecideAsync(
        IToolHandler tool, object input, CancellationToken ct)
    {
        // ① Static rules
        var configResult = _config.Check(tool.Name, input);
        if (configResult.IsDecisive) return configResult.Decision;

        // ② Hook execution
        var hookResult = await _hooks.RunPermissionHooksAsync(
            tool.Name, input, ct);
        if (hookResult != null) return hookResult;

        // ③ Classifier (parallel speculation)
        using var cts = CancellationTokenSource
            .CreateLinkedTokenSource(ct);
        var classifierTask = _classifier.ClassifyAsync(
            tool, input, cts.Token);

        // ④ User dialog (skip if classifier finishes first)
        var winner = await Task.WhenAny(
            classifierTask,
            ShowDialogAsync(tool, input, ct));

        cts.Cancel(); // Cancel the loser
        return await winner;
    }
}
```

**Key Technique**: The classifier (③) and dialog (⑤) are **raced** with `Task.WhenAny`. If the classifier determines "safe" first, the user dialog is never shown. If the user decides first, the classifier is cancelled.

---

## 6. Pattern 5 — Concurrency Partitioning

### 6-1. Problem: Tool Conflicts

It's common for the model to call multiple tools at once:

```
Assistant Response:
  tool_use[1]: Read("config.json")      ← Read-only
  tool_use[2]: Read("package.json")     ← Read-only
  tool_use[3]: Edit("config.json", ...) ← Modifies config.json!
  tool_use[4]: Grep("TODO", "src/")     ← Read-only
```

Items 1, 2, and 4 can execute in parallel, but 3 conflicts with 1 (reading and writing the same file).

### 6-2. Solution: Adjacent Batch Partitioning

Scan the tool call list in order, grouping consecutive concurrency-safe tools into a single parallel batch:

```
// Pseudocode — Adjacent batch partitioning
partitionToolCalls(toolUses):
  for each toolUse:
    isSafe = tool.isConcurrencySafe(input)
    if isSafe AND lastBatch.isSafe:
      lastBatch.add(toolUse)      // Merge into previous batch (parallel)
    else:
      newBatch(isSafe, [toolUse]) // Start new batch
```

Partitioning result for the above example:

```
Batch 1 [parallel]:  Read("config.json"), Read("package.json")
Batch 2 [serial]:    Edit("config.json", ...)
Batch 3 [parallel]:  Grep("TODO", "src/")
```

### 6-3. Fail-Closed Defaults

Unless a tool declares itself as `isConcurrencySafe: true`, it goes into a serial batch by default. Even if you forget concurrency safety when adding a new tool, it **defaults to the safe side**.

### 6-4. C# Implementation: Channel-Based Parallel Execution

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
            // Parallel execution: collect results via Channel
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
            // Serial execution
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

## 7. Pattern 6 — Hierarchical Cancellation Propagation

### 7-1. AbortController Tree

Cancellation in an AI agent must propagate hierarchically:

```
sessionController (session lifetime)
  ↓
queryController (query lifetime)
  ↓
toolBatchController (batch lifetime)
  ├── toolA.controller
  ├── toolB.controller
  └── toolC.controller
       ↓
  siblingController (sibling tools — cancel others if one fails)
```

### 7-2. C# Mapping: LinkedTokenSource

C#'s `CancellationTokenSource.CreateLinkedTokenSource` serves exactly the same role.

```csharp
// Session level
using var sessionCts = new CancellationTokenSource();

// Query level (linked to session)
using var queryCts = CancellationTokenSource
    .CreateLinkedTokenSource(sessionCts.Token);

// Batch level (linked to query)
using var batchCts = CancellationTokenSource
    .CreateLinkedTokenSource(queryCts.Token);

// Sibling tools (linked to batch)
using var siblingCts = CancellationTokenSource
    .CreateLinkedTokenSource(batchCts.Token);

// Cancel siblings if one tool fails
try { await toolA.ExecuteAsync(input, siblingCts.Token); }
catch { siblingCts.Cancel(); throw; }
```

**TypeScript vs C# Mapping Table:**

| TypeScript | C# |
|---|---|
| `new AbortController()` | `new CancellationTokenSource()` |
| `controller.signal` | `cts.Token` |
| `controller.abort()` | `cts.Cancel()` |
| `signal.aborted` | `token.IsCancellationRequested` |
| `signal.addEventListener('abort', ...)` | `token.Register(...)` |

---

## 8. Pattern 7 — Hook Pipeline (Pre/Post Tool Hooks)

### 8-1. Role of Hooks

Hooks are extension points that can **execute external processes** before and after tool execution to observe, modify, or block tool behavior.

```
Pre-Tool Hook
  ↓ (can block)
Tool Execution
  ↓
Post-Tool Hook
  ↓ (can modify result, can still block)
Next Step
```

### 8-2. Hook Event Matcher Types

Hooks can be triggered by various conditions:

```
Matcher Types:
  - event: Specific event type (PreToolUse, PostToolUse, etc.)
  - tool: Specific tool name (BashTool, Edit, etc.)
  - always: All tool executions
  - prompt: Prompt pattern matching
```

### 8-3. Post-Tool Hook Result Types

Results that a Post-Tool hook can return:

```
- Block error: Treat tool execution as error
- Continue block: Prevent further tool execution
- Additional context injection: Pass additional info to model
- Result modification: Transform tool output
- Progress message: Display message in UI
```

### 8-4. C# Implementation: Event-Based Hook System

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

## 9. Pattern 8 — Dependency Injection and Testability

### 9-1. QueryDeps — Test Boundaries

One of the most important patterns in AI agent harness design is the **query dependency interface**:

```
// Pseudocode — Query dependency separation
QueryDeps:
  callModel: (messages) → stream    // API call
  compact: (messages) → messages    // Compaction
  uuid: () → string                 // UUID generation

// Production: Real API client
productionDeps():
  callModel = realApiStreamer
  compact = realCompaction
  uuid = crypto.randomUUID

// Test: Mocking
testDeps(mockResponses):
  callModel = createMockStreamer(mockResponses)
  compact = identity
  uuid = sequentialUUID
```

This allows **testing the query loop's state machine logic without making actual API calls**.

### 9-2. ToolUseContext — Runtime Context Injection

The execution context received by all tools is a collection of runtime dependencies:

```
ToolUseContext:
  options:
    commands: Command[]          // Available commands
    tools: Tools                 // Full tool list
    mcpClients: MCPConnection[]  // MCP server connections
    refreshTools: () → Tools     // Tool list refresh function
  abortController               // Cancellation control
  fileCache                     // File read cache
  getAppState() / setAppState() // Global state access
```

### 9-3. C# Mapping: VContainer or MS DI

```csharp
// Unity Editor path — using VContainer
public class AgentLifetimeScope : LifetimeScope
{
    protected override void Configure(IContainerBuilder builder)
    {
        // Core services
        builder.Register<IQueryEngine, QueryEngine>(Lifetime.Singleton);
        builder.Register<IToolRegistry, ToolRegistry>(Lifetime.Singleton);
        builder.Register<IPermissionPipeline, PermissionPipeline>(Lifetime.Singleton);
        builder.Register<IHookPipeline, HookPipeline>(Lifetime.Singleton);

        // API client (replaceable)
        builder.Register<IAnthropicClient, HttpAnthropicClient>(Lifetime.Singleton);

        // For testing → replace with MockAnthropicClient
    }
}

// .NET Console path — Microsoft.Extensions.DependencyInjection
var services = new ServiceCollection()
    .AddSingleton<IQueryEngine, QueryEngine>()
    .AddSingleton<IToolRegistry, ToolRegistry>()
    .AddSingleton<IAnthropicClient, HttpAnthropicClient>()
    .BuildServiceProvider();
```

---

## 10. Full Architecture Reconstruction Comparison

### 10-1. Message Flow — Original vs C# Reconstruction

**Original (TypeScript/Bun) Estimated Flow:**

```
stdin → Ink REPL → QueryEngine → generator loop
  → callModel() → Anthropic API (SSE)
  → extractToolUses()
  → partitionByConcurrency()
  → runTools (parallel/serial)
    → checkPermissions() → permission pipeline
    → preToolHooks()
    → tool.execute() → AsyncGenerator
    → postToolHooks()
  → yield tool_result
  → Next iteration or Terminal
```

**C# Reconstruction (Path A — .NET CLI):**

```
stdin → Spectre.Console REPL → QueryEngine → IAsyncEnumerable
  → CallModelAsync() → HttpClient + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync() (Channel<T> based)
    → PermissionPipeline.DecideAsync()
    → HookPipeline.RunPreToolHooksAsync()
    → tool.ExecuteAsync() → IAsyncEnumerable
    → HookPipeline.RunPostToolHooksAsync()
  → yield return ToolResult
  → continue or yield break
```

**C# Reconstruction (Path B — Unity Editor):**

```
EditorWindow UI → QueryEngine → UniTask
  → CallModelAsync() → UnityWebRequest + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync() (UniTask.WhenAll)
    → PermissionPipeline (EditorUtility.DisplayDialog)
    → HookPipeline
    → tool.HandleCommand() ← Reuse unity-cli-connector tools!
    → PostToolHooks
  → ToolResult → EditorWindow refresh
  → Next iteration
```

### 10-2. 1:1 Mapping Table

| Agent Pattern (TypeScript) | .NET CLI (C#) | Unity Editor (C#) |
|---|---|---|
| `AsyncGenerator<T>` | `IAsyncEnumerable<T>` | `UniTask` + callback |
| `AbortController` | `CancellationTokenSource` | `CancellationTokenSource` |
| `Zod Schema` | `DataAnnotations` + source gen | `[ToolParameter]` (existing) |
| `feature()` (build-time) | `#if FEATURE_X` | `#if UNITY_EDITOR` |
| `ToolUseContext` | `IServiceProvider` | `VContainer` |
| Terminal UI (Ink) | `Spectre.Console` | **UI Toolkit** (native) |
| `memoize()` | `Lazy<T>` | `Lazy<T>` |
| `process.env` | `Environment.GetEnvironmentVariable` | `EditorPrefs` |
| File cache | `ConcurrentDictionary` | `Dictionary` (editor single-threaded) |
| `Process` (external process) | `System.Diagnostics.Process` | `EditorCoroutineUtility` |

### 10-3. Code Volume Estimate

| Module | Original (TS) Est. | .NET CLI | Unity Editor |
|---|---|---|---|
| Query Engine | ~1,700 lines | ~1,200 lines | ~800 lines |
| Tool System (core) | ~1,200 lines | ~500 lines | ~300 lines (reuse existing) |
| Permission System | ~2,500 lines | ~800 lines | ~500 lines |
| Hook System | ~1,000 lines | ~400 lines | ~300 lines |
| Concurrency Control | ~500 lines | ~300 lines | ~200 lines |
| Tool Implementations (42) | ~30,000 lines | ~4,000 lines | ~1,000 lines (reuse existing 18) |
| Terminal UI | ~25,000 lines | ~2,000 lines | **0 lines** (UI Toolkit) |
| Context/Config | ~2,000 lines | ~600 lines | ~400 lines |
| Cost/Telemetry | ~800 lines | ~300 lines | ~200 lines |
| **Total** | **~65,000 lines** | **~10,100 lines** | **~3,700 lines** |

---

## 11. Specific Benefits of the Unity Editor Path

### 11-1. What unity-cli-connector Already Provides

unity-cli-connector (`com.youngwoocho02.unity-cli-connector` v0.2.12) already has the harness's lower-level infrastructure in place:

| Harness Pattern | unity-cli-connector Implementation |
|---|---|
| **Tool Discovery** | `ToolDiscovery.cs` — Reflection + `[UnityCliTool]` scan |
| **Command Routing** | `CommandRouter.cs` — SemaphoreSlim serialization |
| **HTTP Server** | `HttpServer.cs` — Local POST `/command` |
| **Main Thread Marshalling** | `ConcurrentQueue<WorkItem>` + `EditorApplication.update` |
| **Parameter Schema** | `[ToolParameter]` attribute-based auto generation |
| **18 Built-in Tools** | manage_editor, execute_csharp, read_console, run_tests, etc. |

### 11-2. Additional Implementation Scope

```
Existing unity-cli-connector
  │
  ├── ToolDiscovery (exists) ← Foundation for tool registry
  ├── CommandRouter (exists) ← Foundation for tool execution pipeline
  ├── 18 Built-in Tools (exist) ← Foundation for tool implementations
  │
  └── Additional implementation needed:
       ├── QueryEngine (query state machine loop)
       ├── AnthropicApiClient (SSE streaming)
       ├── PermissionManager (Config + Dialog)
       ├── HookPipeline (Pre/Post hooks)
       ├── ConcurrencyPartitioner (batch splitting)
       ├── ContextAssembler (CLAUDE.md + git)
       └── EditorWindow UI (conversation interface)
```

### 11-3. Unity-Specific Benefits

1. **Direct Editor API Access** — Call `AssetDatabase.Refresh()`, `EditorApplication.isPlaying`, etc. without HTTP proxy
2. **Compilation Event Subscription** — Connect hooks to `CompilationPipeline.compilationFinished`
3. **Inspector Integration** — Visualize tool execution results in the Inspector
4. **ScriptableObject Configuration** — Visually edit permission rules in the editor
5. **Play Mode Integration** — Naturally integrate runtime validation into the query loop

---

## 12. Practical Example: Minimal Query Engine for Unity Editor

This section shows the skeleton of a minimal working query engine.

```csharp
/// <summary>
/// Minimal query engine porting the core patterns of AI agent harness to Unity Editor
/// Patterns: Generator-based loop, concurrency partitioning, Fail-Closed permissions
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
            // ── 1. Model call (SSE streaming) ──
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

            // ── 2. Extract tool uses ──
            var toolUses = response.ExtractToolUses();
            if (toolUses.Count == 0) break; // No tools → End conversation

            // ── 3. Concurrency partitioning ──
            var batches = PartitionByConcurrency(toolUses);
            var toolResults = new List<ToolResultBlock>();

            foreach (var batch in batches)
            {
                if (batch.IsConcurrencySafe)
                {
                    // Parallel execution
                    var tasks = batch.Blocks.Select(block =>
                        ExecuteToolWithPipelineAsync(block, ct));
                    var results = await UniTask.WhenAll(tasks);
                    toolResults.AddRange(results);
                }
                else
                {
                    // Serial execution
                    foreach (var block in batch.Blocks)
                    {
                        var result = await ExecuteToolWithPipelineAsync(
                            block, ct);
                        toolResults.Add(result);
                    }
                }
            }

            // ── 4. Add results to messages ──
            messages.Add(new Message
            {
                Role = "user",
                Content = toolResults.Select(r => r.ToContentBlock()).ToList()
            });

            // ── 5. Next iteration ──
        }
    }

    private async UniTask<ToolResultBlock> ExecuteToolWithPipelineAsync(
        ToolUseBlock block, CancellationToken ct)
    {
        var tool = _tools.FindByName(block.Name);

        // ① Permission decision (Fail-Closed)
        var permission = await _permissions.DecideAsync(tool, block.Input, ct);
        if (permission.IsDenied)
            return ToolResultBlock.Error(block.Id, permission.DenyMessage);

        // ② Pre-tool hook
        var preHook = await _hooks.RunPreToolHooksAsync(
            block.Name, block.Input, ct);
        if (preHook.IsBlocking)
            return ToolResultBlock.Error(block.Id, preHook.BlockMessage);

        // ③ Tool execution
        try
        {
            var result = await tool.HandleCommand(
                preHook.ModifiedInput ?? block.Input, ct);

            // ④ Post-tool hook
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

## 13. Summary — 8 Principles of Harness Engineering

Here we summarize the design principles extracted from AI agent harnesses. These principles are **language and framework independent**.

| # | Principle | Key Reason |
|---|-----------|------------|
| 1 | **Generator Streaming** | Natural backpressure support, composable |
| 2 | **State Machine Query Loop** | Recovery strategies, easy debugging |
| 3 | **Reflection Tool Discovery** | Plugin extensibility, dead code elimination |
| 4 | **Fail-Closed Permissions** | Secure defaults, gradual relaxation |
| 5 | **Concurrency Partitioning** | Balance of safety and performance |
| 6 | **Hierarchical Cancellation Propagation** | Resource leak prevention, clean shutdown |
| 7 | **Pre/Post Hook Pipeline** | Separation of concerns, external extensibility |
| 8 | **Dependency Injection Boundaries** | Testability, easy replacement |

Understanding these 8 patterns enables you to read, extend, and reconstruct **any AI agent harness**.

---

## References

- [Claude Code Architecture Analysis](/posts/ClaudeCodeSourceLeak/) — Design principle inference analysis
- [Claude Code Insights](/posts/ClaudeCodeInsights/) — Basic usage of Claude Code
- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — Official tool use guide
- [unity-cli-connector](https://github.com/youngwoocho02/unity-cli) — Unity Editor remote control CLI
- [IAsyncEnumerable in .NET](https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/generate-consume-asynchronous-stream) — C# async stream guide
