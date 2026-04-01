---
title: "AI 에이전트 하네스 엔지니어링 심층 해부 — 오케스트레이션 설계 원리와 C# 재구축"
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
  - "AI 에이전트 하네스의 핵심은 Generator 기반 스트리밍 쿼리 루프, Fail-Closed 퍼미션 파이프라인, 동시성 파티셔닝 도구 실행의 세 축이며, 이 패턴들은 언어에 독립적인 오케스트레이션 설계 원리다"
  - "TypeScript의 AsyncGenerator → C#의 IAsyncEnumerable, AbortController → CancellationTokenSource, Zod → DataAnnotations로 1:1 대응되며, .NET 8+ 콘솔 앱으로 핵심 오케스트레이션을 ~10,000줄 수준으로 재구축할 수 있다"
  - "Unity Editor 확장 경로에서는 unity-cli-connector의 기존 도구 발견/라우팅/마샬링 패턴을 그대로 재사용하면서, 터미널 UI를 완전히 생략하고 UI Toolkit으로 대체할 수 있어 원본의 ~20% 코드량으로 MVP 구현이 가능하다"
---

## 들어가며

[이전 포스트](/posts/ClaudeCodeSourceLeak/)에서 Claude Code의 아키텍처 설계 원리를 분석했다. 이번 글에서는 한 단계 더 깊이 들어가서, **하네스 엔지니어링(Harness Engineering)** — 즉 AI 에이전트의 오케스트레이션 계층이 어떤 설계 원리로 구축되는지를 해부한다.

"하네스"라는 용어는 원래 테스트 하네스(test harness)에서 온 것으로, **실행 대상을 감싸서 입출력을 제어하는 프레임워크**를 의미한다. AI 에이전트 하네스는 LLM을 감싸서 도구 호출, 권한 관리, 컨텍스트 조립, 세션 관리를 오케스트레이션하는 계층이다.

이 글의 목표는 세 가지다:

1. AI 에이전트 하네스의 **8가지 핵심 설계 패턴**을 추출한다
2. 각 패턴이 **왜 그렇게 설계되었는지** 동기를 분석한다
3. 이 패턴을 **C#/.NET 및 Unity Editor로 재구축**할 때의 대응 전략을 제시한다

---

## 1. 하네스 엔지니어링이란 무엇인가

### 1-1. AI 에이전트 하네스의 역할

AI 에이전트는 단순히 LLM에 프롬프트를 보내고 응답을 받는 것이 아니다. 실제 제품 수준의 에이전트는 다음을 모두 관리해야 한다:

| 계층 | 책임 |
|------|------|
| **초기화** | 인증, 설정, 컨텍스트 조립 |
| **대화 루프** | 메시지 관리, API 호출, 스트리밍 |
| **도구 실행** | 도구 발견, 입력 검증, 실행, 결과 처리 |
| **권한 제어** | 퍼미션 결정, 보안 분류, 훅 |
| **동시성** | 병렬/직렬 배치, 취소 전파 |
| **복구** | 컨텍스트 컴팩션, 토큰 초과 재시도 |
| **세션** | 히스토리 저장, 비용 추적, 텔레메트리 |
| **UI** | 진행 표시, 권한 다이얼로그, 터미널 렌더링 |

이 8개 계층을 통합하는 것이 하네스의 역할이다. 하네스가 없으면 LLM은 그저 텍스트를 생성하는 API에 불과하다.

### 1-2. 하네스의 규모감

Claude Code와 같은 제품 수준 에이전트의 경우, 하네스 코드는 대략 다음과 같은 비중을 차지한다:

```
전형적인 AI 에이전트 CLI:
├── 하네스 코어 (쿼리 루프, 도구, 권한): ~15,000줄
├── 도구 구현 (40+개): ~30,000줄
├── 터미널 UI: ~25,000줄
├── 서비스 (OAuth, MCP, 분석): ~20,000줄
├── 유틸리티: ~30,000줄
└── 기타 (테스트, 설정, 타입): ~40,000줄
```

이 글에서는 **하네스 코어 ~15,000줄**에 해당하는 오케스트레이션 패턴에 집중한다.

---

## 2. 패턴 1 — Generator 기반 스트리밍 아키텍처

### 2-1. 핵심 원리

제품 수준 AI 에이전트의 모든 비동기 흐름은 **Generator (비동기 이터레이터)** 패턴으로 구현하는 것이 일반적이다. 도구 실행, 쿼리 루프, 훅 실행 전부가 이 패턴을 따른다.

```
// 의사코드 — Generator 기반 도구 실행
Tool<Input, Output>:
  execute(input, context) → AsyncGenerator<ToolProgress<Output>>

// 의사코드 — Generator 기반 쿼리 루프
query(params) → AsyncGenerator<StreamEvent | Message>:
  loop:
    response = yield* callModel(...)    // 모델 호출 (스트리밍)
    for result in runTools(...):        // 도구 실행 (스트리밍)
      yield result
    if isTerminal(response): return
```

### 2-2. 왜 Generator인가

**콜백 지옥 회피**: Promise 체이닝이나 이벤트 리스너 대신 `yield`로 제어 흐름을 명시적으로 표현한다.

**역압(Backpressure) 자연 지원**: `yield`는 소비자가 준비될 때까지 생산자를 자동으로 멈춘다. 별도의 버퍼링/흐름 제어 코드가 필요 없다.

**합성 가능성(Composability)**: `yield*`(위임)로 하위 Generator를 위임할 수 있어, 쿼리 루프 → 도구 실행 → 훅 실행의 계층적 스트리밍이 자연스럽게 합성된다.

### 2-3. C# 대응: IAsyncEnumerable

C# 8.0부터 도입된 `IAsyncEnumerable<T>`는 TypeScript의 AsyncGenerator와 정확히 대응한다.

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

// 쿼리 루프도 동일 패턴
public async IAsyncEnumerable<StreamEvent> QueryAsync(
    QueryParams param,
    [EnumeratorCancellation] CancellationToken ct)
{
    var state = new QueryState(param.Messages);

    while (!ct.IsCancellationRequested)
    {
        // yield* 위임 → await foreach + yield return
        await foreach (var chunk in CallModelAsync(state, ct))
            yield return chunk;

        await foreach (var result in RunToolsAsync(state, ct))
            yield return result;

        if (IsTerminal(state)) yield break;

        state = ApplyRecovery(state);
    }
}
```

**차이점**: C#에는 `yield*` 위임이 없으므로 `await foreach + yield return`으로 풀어야 한다. 한 줄이 세 줄이 되지만 의미는 동일하다.

---

## 3. 패턴 2 — 상태 머신 쿼리 루프

### 3-1. 핵심 구조

AI 에이전트의 쿼리 루프는 명시적 상태 객체를 가진 루프형 상태 머신으로 설계하는 것이 좋다. 상태 객체가 관리해야 할 주요 필드:

```
QueryState:
  messages: Message[]           // 대화 히스토리
  toolUseContext: ToolUseContext // 도구 실행 컨텍스트
  recoveryCount: number         // 복구 시도 횟수
  hasAttemptedCompact: boolean  // 컴팩션 시도 여부
  turnCount: number             // 현재 턴 수
  transition: Continue | null   // 상태 전이 제어
```

### 3-2. 상태 전이 다이어그램

```
                    ┌──────────────────────┐
                    │     초기 상태         │
                    │  messages = [user]    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
              ┌────→│   모델 API 호출       │
              │     │  callModel(state)    │
              │     └──────────┬───────────┘
              │                ↓
              │     ┌──────────────────────┐
              │     │  응답 분석            │
              │     │  stop_reason 확인     │
              │     └───┬──────┬──────┬────┘
              │         │      │      │
              │    end_turn  tool_use  max_tokens
              │         │      │      │
              │         ↓      ↓      ↓
              │     ┌──────┐ ┌────┐ ┌──────────┐
              │     │ 완료  │ │도구│ │ 복구 전략 │
              │     │return│ │실행│ │컴팩션/재시도│
              │     └──────┘ └─┬──┘ └────┬─────┘
              │                │         │
              │                ↓         │
              │     ┌──────────────────┐ │
              │     │ tool_result 추가  │ │
              │     │ messages에 결과   │ │
              │     └────────┬─────────┘ │
              │              │           │
              └──────────────┴───────────┘
                    (다음 반복)
```

### 3-3. 복구 전략의 계층

| 상황 | 복구 전략 | 동작 |
|------|-----------|------|
| 토큰 초과 (1차) | Reactive Compact | 대화 히스토리를 구조화된 요약으로 압축 |
| 토큰 초과 (2차) | Max Output 증가 | `maxOutputTokens`를 단계적으로 증가 |
| 토큰 초과 (3차) | 강제 종료 | `Terminal` 상태 반환 |
| 컨텍스트 윈도우 임박 | Auto Compact | 사전적으로 히스토리 압축 |
| API 오류 | 재시도 + Fallback 모델 | 지수 백오프 후 대안 모델 시도 |

### 3-4. C# 재구축 포인트

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
            // 1. 모델 호출
            var response = await _apiClient.StreamAsync(
                state.BuildRequest(), ct);

            await foreach (var chunk in response)
                yield return new StreamEvent.Chunk(chunk);

            // 2. 도구 추출 + 실행
            var toolUses = state.ExtractToolUses();
            if (toolUses.Count > 0)
            {
                await foreach (var result in
                    _toolOrchestrator.RunAsync(toolUses, state.Context, ct))
                {
                    state.AddToolResult(result);
                    yield return new StreamEvent.ToolResult(result);
                }
                continue; // 다음 반복
            }

            // 3. 종료 조건
            if (state.IsTerminal()) yield break;

            // 4. 복구
            state = await _recoveryStrategy.ApplyAsync(state, ct);
        }
    }
}
```

---

## 4. 패턴 3 — 도구 발견과 레지스트리

### 4-1. 두 가지 도구 소스의 합성

AI 에이전트는 보통 두 가지 도구 소스를 합성한다:

```
도구 풀 조립:
  1. 내장 도구 (빌트인 42+개) — 이름순 정렬
  2. 외부 도구 (MCP 서버 등) — 이름순 정렬, 거부 규칙 필터링 후 추가
  → 빌트인을 앞쪽에 유지 (프롬프트 캐시 키 안정성)
  → 이름 충돌 시 빌트인 우선
```

**정렬 순서가 중요한 이유**: API의 프롬프트 캐시 키는 `(system_prompt, tools, model, messages_prefix)` 조합으로 결정된다. 도구 목록의 순서가 바뀌면 캐시가 깨져서 비용이 증가한다.

### 4-2. Feature-Gated 조건부 로딩

빌드 타임 피처 플래그로 특정 도구를 조건부 포함/제거할 수 있다:

```
// 의사코드 — 빌드 타임 피처 게이팅
cronTools = FEATURE('AGENT_TRIGGERS')
  ? [CronCreateTool, CronDeleteTool, CronListTool]
  : []

sleepTool = FEATURE('PROACTIVE') || FEATURE('ASSISTANT')
  ? loadModule('SleepTool')
  : null
```

번들 타임에 `false`로 평가되면 관련 코드가 완전히 제거(dead code elimination)된다.

### 4-3. unity-cli-connector의 기존 패턴

흥미롭게도 **unity-cli-connector는 이미 유사한 도구 발견 패턴을 구현**하고 있다:

```csharp
// unity-cli-connector의 ToolDiscovery.cs
// Reflection 기반 자동 발견 — [UnityCliTool] 어트리뷰트 스캔
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
        // 구현
    }
}
```

### 4-4. C# 확장 설계: 통합 도구 레지스트리

unity-cli의 패턴을 확장하여 에이전트 수준의 도구 레지스트리를 만들 수 있다:

```csharp
// 통합 도구 인터페이스 — unity-cli의 [UnityCliTool] 패턴 확장
[AttributeUsage(AttributeTargets.Class)]
public class AgentToolAttribute : Attribute
{
    public string Description { get; set; }
    public string Category { get; set; }
    public bool IsConcurrencySafe { get; set; } = false;  // Fail-Closed 기본값
    public bool IsReadOnly { get; set; } = false;
}

// Reflection 기반 자동 발견
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

    // 기존 unity-cli 도구 + 새 에이전트 도구를 동일한 레지스트리에 통합
    public IReadOnlyList<IToolHandler> AssembleToolPool(PermissionContext ctx)
    {
        return _tools.Values
            .Where(t => !ctx.IsDenied(t.Name))
            .OrderBy(t => t.Name)    // 캐시 키 안정성
            .ToList();
    }
}
```

---

## 5. 패턴 4 — Fail-Closed 퍼미션 파이프라인

### 5-1. 설계 철학

제품 수준 AI 에이전트의 퍼미션 시스템은 **Fail-Closed**로 설계해야 한다 — 명시적으로 허용되지 않은 것은 모두 거부된다.

```
// 기본값은 모두 "안전하지 않음"
TOOL_DEFAULTS:
  isConcurrencySafe: false   // 동시 실행 불가
  isReadOnly: false           // 쓰기 가능
  isDestructive: false
```

### 5-2. 5단계 퍼미션 결정 흐름

```
도구 사용 요청
  ↓
① Config Rules (정적 규칙 — settings.json)
  ├── alwaysAllow: ["Read", "Glob", "Grep"]  → 즉시 허용
  ├── alwaysDeny: ["rm -rf"]                  → 즉시 거부
  └── alwaysAsk: ["BashTool"]                 → 다음 단계로
  ↓
② Hook Execution (외부 프로세스 훅)
  ├── permission_request 훅이 등록되어 있으면 실행
  └── 훅이 allow/deny 결정 → 즉시 반환
  ↓
③ Auto Classifier (추측적 병렬 실행)
  ├── AST 기반 정적 분석으로 위험도 분류
  └── 안전하다고 판단되면 자동 허용
  ↓
④ Coordinator (멀티 에이전트 위임)
  ├── 워커 에이전트 → 부모에게 결정 위임
  └── 부모가 자동 결정 또는 사용자에게 전달
  ↓
⑤ Interactive Dialog (최종 — 사용자에게 직접 질문)
  ├── 허용 (일회성 / 영구)
  ├── 거부 (피드백 포함 가능)
  └── 중단 (Ctrl+C)
```

### 5-3. 퍼미션 소스 추적

허용/거부가 "누가" 결정했는지를 추적하는 것이 중요하다:

```
허용 소스:
  - hook (훅 자동 허용)
  - user (사용자 수동 허용, 영구 여부)
  - classifier (분류기 자동 허용)

거부 소스:
  - hook (훅 차단)
  - user_abort (Ctrl+C)
  - user_reject (거부 + 이유 제공)
```

### 5-4. C# 재구축

```csharp
public class PermissionPipeline
{
    private readonly PermissionConfig _config;
    private readonly IHookRunner _hooks;
    private readonly IBashClassifier _classifier;

    public async Task<PermissionDecision> DecideAsync(
        IToolHandler tool, object input, CancellationToken ct)
    {
        // ① 정적 규칙
        var configResult = _config.Check(tool.Name, input);
        if (configResult.IsDecisive) return configResult.Decision;

        // ② 훅 실행
        var hookResult = await _hooks.RunPermissionHooksAsync(
            tool.Name, input, ct);
        if (hookResult != null) return hookResult;

        // ③ 분류기 (병렬 추측)
        using var cts = CancellationTokenSource
            .CreateLinkedTokenSource(ct);
        var classifierTask = _classifier.ClassifyAsync(
            tool, input, cts.Token);

        // ④ 사용자 다이얼로그 (분류기가 먼저 끝나면 스킵)
        var winner = await Task.WhenAny(
            classifierTask,
            ShowDialogAsync(tool, input, ct));

        cts.Cancel(); // 진 쪽 취소
        return await winner;
    }
}
```

**핵심 테크닉**: ③번 분류기와 ⑤번 다이얼로그를 `Task.WhenAny`로 **경쟁(race)** 시킨다. 분류기가 먼저 "안전"이라고 판단하면 사용자 다이얼로그를 보여주지 않는다. 사용자가 먼저 결정하면 분류기를 취소한다.

---

## 6. 패턴 5 — 동시성 파티셔닝

### 6-1. 문제: 도구 간 충돌

모델이 한 번에 여러 도구를 호출하는 경우가 흔하다:

```
Assistant Response:
  tool_use[1]: Read("config.json")      ← 읽기 전용
  tool_use[2]: Read("package.json")     ← 읽기 전용
  tool_use[3]: Edit("config.json", ...) ← config.json 수정!
  tool_use[4]: Grep("TODO", "src/")     ← 읽기 전용
```

1, 2, 4번은 병렬 실행 가능하지만, 3번은 1번과 충돌한다 (같은 파일을 읽고 쓰기).

### 6-2. 해법: 인접 배치 파티셔닝

도구 호출 목록을 순서대로 스캔하면서, 연속된 동시성 안전 도구들을 하나의 병렬 배치로 묶는다:

```
// 의사코드 — 인접 배치 파티셔닝
partitionToolCalls(toolUses):
  for each toolUse:
    isSafe = tool.isConcurrencySafe(input)
    if isSafe AND lastBatch.isSafe:
      lastBatch.add(toolUse)      // 이전 배치에 합침 (병렬)
    else:
      newBatch(isSafe, [toolUse]) // 새 배치 시작
```

위 예시에서 파티셔닝 결과:

```
Batch 1 [parallel]:  Read("config.json"), Read("package.json")
Batch 2 [serial]:    Edit("config.json", ...)
Batch 3 [parallel]:  Grep("TODO", "src/")
```

### 6-3. Fail-Closed 기본값

도구가 스스로를 `isConcurrencySafe: true`로 선언하지 않는 한, 기본적으로 직렬 배치에 들어간다. 새 도구를 추가할 때 동시성 안전성을 잊어도 **안전한 쪽으로 동작**한다.

### 6-4. C# 구현: Channel 기반 병렬 실행

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
            // 병렬 실행: Channel로 결과 수집
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
            // 직렬 실행
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

## 7. 패턴 6 — 계층적 취소 전파

### 7-1. AbortController 트리

AI 에이전트에서 취소는 계층적으로 전파되어야 한다:

```
sessionController (세션 수명)
  ↓
queryController (쿼리 수명)
  ↓
toolBatchController (배치 수명)
  ├── toolA.controller
  ├── toolB.controller
  └── toolC.controller
       ↓
  siblingController (형제 도구 — 하나가 실패하면 나머지 취소)
```

### 7-2. C# 대응: LinkedTokenSource

C#의 `CancellationTokenSource.CreateLinkedTokenSource`는 정확히 같은 역할을 한다.

```csharp
// 세션 레벨
using var sessionCts = new CancellationTokenSource();

// 쿼리 레벨 (세션에 연결)
using var queryCts = CancellationTokenSource
    .CreateLinkedTokenSource(sessionCts.Token);

// 배치 레벨 (쿼리에 연결)
using var batchCts = CancellationTokenSource
    .CreateLinkedTokenSource(queryCts.Token);

// 형제 도구 (배치에 연결)
using var siblingCts = CancellationTokenSource
    .CreateLinkedTokenSource(batchCts.Token);

// 하나의 도구가 실패하면 형제 취소
try { await toolA.ExecuteAsync(input, siblingCts.Token); }
catch { siblingCts.Cancel(); throw; }
```

**TypeScript vs C# 대응표:**

| TypeScript | C# |
|---|---|
| `new AbortController()` | `new CancellationTokenSource()` |
| `controller.signal` | `cts.Token` |
| `controller.abort()` | `cts.Cancel()` |
| `signal.aborted` | `token.IsCancellationRequested` |
| `signal.addEventListener('abort', ...)` | `token.Register(...)` |

---

## 8. 패턴 7 — 훅 파이프라인 (Pre/Post Tool Hooks)

### 8-1. 훅의 역할

훅은 도구 실행 전후에 **외부 프로세스를 실행**하여 도구의 동작을 관찰, 수정, 차단할 수 있는 확장 포인트다.

```
Pre-Tool Hook
  ↓ (차단 가능)
도구 실행
  ↓
Post-Tool Hook
  ↓ (결과 수정 가능, 계속 차단 가능)
다음 단계
```

### 8-2. 훅 이벤트 매처 유형

훅은 다양한 조건으로 트리거될 수 있다:

```
매처 유형:
  - event: 특정 이벤트 타입 (PreToolUse, PostToolUse 등)
  - tool: 특정 도구 이름 (BashTool, Edit 등)
  - always: 모든 도구 실행
  - prompt: 프롬프트 패턴 매칭
```

### 8-3. Post-Tool 훅의 결과 유형

Post-Tool 훅이 반환할 수 있는 결과:

```
- 차단 에러: 도구 실행을 에러로 처리
- 계속 차단: 추가 도구 실행 방지
- 추가 컨텍스트 주입: 모델에게 추가 정보 전달
- 결과 수정: 도구 출력을 변형
- 진행 메시지: UI에 메시지 표시
```

### 8-4. C# 구현: 이벤트 기반 훅 시스템

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

## 9. 패턴 8 — 의존성 주입과 테스트 가능성

### 9-1. QueryDeps — 테스트 경계

AI 에이전트 하네스 설계에서 가장 중요한 패턴 중 하나는 **쿼리 의존성 인터페이스**다:

```
// 의사코드 — 쿼리 의존성 분리
QueryDeps:
  callModel: (messages) → stream    // API 호출
  compact: (messages) → messages    // 컴팩션
  uuid: () → string                 // UUID 생성

// 프로덕션: 실제 API 클라이언트
productionDeps():
  callModel = realApiStreamer
  compact = realCompaction
  uuid = crypto.randomUUID

// 테스트: 모킹
testDeps(mockResponses):
  callModel = createMockStreamer(mockResponses)
  compact = identity
  uuid = sequentialUUID
```

이렇게 하면 **실제 API를 호출하지 않고 쿼리 루프의 상태 머신 로직을 테스트**할 수 있다.

### 9-2. ToolUseContext — 런타임 컨텍스트 주입

모든 도구가 받는 실행 컨텍스트는 런타임 의존성의 집합이다:

```
ToolUseContext:
  options:
    commands: Command[]          // 사용 가능한 커맨드
    tools: Tools                 // 전체 도구 목록
    mcpClients: MCPConnection[]  // MCP 서버 연결
    refreshTools: () → Tools     // 도구 목록 갱신 함수
  abortController               // 취소 제어
  fileCache                     // 파일 읽기 캐시
  getAppState() / setAppState() // 전역 상태 접근
```

### 9-3. C# 대응: VContainer 또는 MS DI

```csharp
// Unity Editor 경로 — VContainer 사용
public class AgentLifetimeScope : LifetimeScope
{
    protected override void Configure(IContainerBuilder builder)
    {
        // 코어 서비스
        builder.Register<IQueryEngine, QueryEngine>(Lifetime.Singleton);
        builder.Register<IToolRegistry, ToolRegistry>(Lifetime.Singleton);
        builder.Register<IPermissionPipeline, PermissionPipeline>(Lifetime.Singleton);
        builder.Register<IHookPipeline, HookPipeline>(Lifetime.Singleton);

        // API 클라이언트 (교체 가능)
        builder.Register<IAnthropicClient, HttpAnthropicClient>(Lifetime.Singleton);

        // 테스트 시 → MockAnthropicClient 로 교체
    }
}

// .NET 콘솔 경로 — Microsoft.Extensions.DependencyInjection
var services = new ServiceCollection()
    .AddSingleton<IQueryEngine, QueryEngine>()
    .AddSingleton<IToolRegistry, ToolRegistry>()
    .AddSingleton<IAnthropicClient, HttpAnthropicClient>()
    .BuildServiceProvider();
```

---

## 10. 전체 아키텍처 재구축 비교

### 10-1. 메시지 흐름 — 원본 vs C# 재구축

**원본 (TypeScript/Bun) 추정 흐름:**

```
stdin → Ink REPL → QueryEngine → generator 루프
  → callModel() → Anthropic API (SSE)
  → extractToolUses()
  → partitionByConcurrency()
  → runTools (parallel/serial)
    → checkPermissions() → permission pipeline
    → preToolHooks()
    → tool.execute() → AsyncGenerator
    → postToolHooks()
  → yield tool_result
  → 다음 반복 또는 Terminal
```

**C# 재구축 (경로 A — .NET CLI):**

```
stdin → Spectre.Console REPL → QueryEngine → IAsyncEnumerable
  → CallModelAsync() → HttpClient + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync() (Channel<T> 기반)
    → PermissionPipeline.DecideAsync()
    → HookPipeline.RunPreToolHooksAsync()
    → tool.ExecuteAsync() → IAsyncEnumerable
    → HookPipeline.RunPostToolHooksAsync()
  → yield return ToolResult
  → continue 또는 yield break
```

**C# 재구축 (경로 B — Unity Editor):**

```
EditorWindow UI → QueryEngine → UniTask
  → CallModelAsync() → UnityWebRequest + SSE
  → ExtractToolUses()
  → PartitionByConcurrency()
  → RunToolsAsync() (UniTask.WhenAll)
    → PermissionPipeline (EditorUtility.DisplayDialog)
    → HookPipeline
    → tool.HandleCommand() ← unity-cli-connector 도구 재사용!
    → PostToolHooks
  → ToolResult → EditorWindow 갱신
  → 다음 반복
```

### 10-2. 1:1 대응 매핑 테이블

| 에이전트 패턴 (TypeScript) | .NET CLI (C#) | Unity Editor (C#) |
|---|---|---|
| `AsyncGenerator<T>` | `IAsyncEnumerable<T>` | `UniTask` + callback |
| `AbortController` | `CancellationTokenSource` | `CancellationTokenSource` |
| `Zod Schema` | `DataAnnotations` + source gen | `[ToolParameter]` (기존) |
| `feature()` (빌드 타임) | `#if FEATURE_X` | `#if UNITY_EDITOR` |
| `ToolUseContext` | `IServiceProvider` | `VContainer` |
| 터미널 UI (Ink) | `Spectre.Console` | **UI Toolkit** (네이티브) |
| `memoize()` | `Lazy<T>` | `Lazy<T>` |
| `process.env` | `Environment.GetEnvironmentVariable` | `EditorPrefs` |
| 파일 캐시 | `ConcurrentDictionary` | `Dictionary` (에디터 단일 스레드) |
| `Process` (외부 프로세스) | `System.Diagnostics.Process` | `EditorCoroutineUtility` |

### 10-3. 코드량 추정

| 모듈 | 원본 (TS) 추정 | .NET CLI | Unity Editor |
|---|---|---|---|
| 쿼리 엔진 | ~1,700줄 | ~1,200줄 | ~800줄 |
| 도구 시스템 (코어) | ~1,200줄 | ~500줄 | ~300줄 (기존 재사용) |
| 퍼미션 시스템 | ~2,500줄 | ~800줄 | ~500줄 |
| 훅 시스템 | ~1,000줄 | ~400줄 | ~300줄 |
| 동시성 제어 | ~500줄 | ~300줄 | ~200줄 |
| 도구 구현 (42개) | ~30,000줄 | ~4,000줄 | ~1,000줄 (기존 18개 재사용) |
| 터미널 UI | ~25,000줄 | ~2,000줄 | **0줄** (UI Toolkit) |
| 컨텍스트/설정 | ~2,000줄 | ~600줄 | ~400줄 |
| 비용/텔레메트리 | ~800줄 | ~300줄 | ~200줄 |
| **합계** | **~65,000줄** | **~10,100줄** | **~3,700줄** |

---

## 11. Unity Editor 경로의 구체적 이점

### 11-1. unity-cli-connector가 이미 제공하는 것

unity-cli-connector(`com.youngwoocho02.unity-cli-connector` v0.2.12)는 하네스의 하부 인프라를 이미 갖추고 있다:

| 하네스 패턴 | unity-cli-connector 구현체 |
|---|---|
| **도구 발견** | `ToolDiscovery.cs` — Reflection + `[UnityCliTool]` 스캔 |
| **명령 라우팅** | `CommandRouter.cs` — SemaphoreSlim 직렬화 |
| **HTTP 서버** | `HttpServer.cs` — 로컬 POST `/command` |
| **메인 스레드 마샬링** | `ConcurrentQueue<WorkItem>` + `EditorApplication.update` |
| **파라미터 스키마** | `[ToolParameter]` 어트리뷰트 기반 자동 생성 |
| **내장 도구 18개** | manage_editor, execute_csharp, read_console, run_tests 등 |

### 11-2. 추가 구현 범위

```
기존 unity-cli-connector
  │
  ├── ToolDiscovery (있음) ← 도구 레지스트리의 기반
  ├── CommandRouter (있음) ← 도구 실행 파이프라인의 기반
  ├── 18 Built-in Tools (있음) ← 도구 구현의 기반
  │
  └── 추가 구현 필요:
       ├── QueryEngine (쿼리 상태 머신 루프)
       ├── AnthropicApiClient (SSE 스트리밍)
       ├── PermissionManager (Config + Dialog)
       ├── HookPipeline (Pre/Post 훅)
       ├── ConcurrencyPartitioner (배치 분할)
       ├── ContextAssembler (CLAUDE.md + git)
       └── EditorWindow UI (대화 인터페이스)
```

### 11-3. Unity 고유의 이점

1. **Editor API 직접 접근** — `AssetDatabase.Refresh()`, `EditorApplication.isPlaying` 등을 HTTP 프록시 없이 호출
2. **컴파일 이벤트 구독** — `CompilationPipeline.compilationFinished`에 훅 연결
3. **Inspector 통합** — 도구 실행 결과를 Inspector에 시각화
4. **ScriptableObject 설정** — 퍼미션 규칙을 에디터에서 시각적으로 편집
5. **Play Mode 통합** — 런타임 검증을 쿼리 루프에 자연스럽게 통합

---

## 12. 실전 예제: Unity Editor용 최소 쿼리 엔진

이 섹션에서는 실제로 동작하는 최소 쿼리 엔진의 골격을 보여준다.

```csharp
/// <summary>
/// AI 에이전트 하네스의 핵심 패턴을 Unity Editor로 포팅한 최소 쿼리 엔진
/// 패턴: Generator 기반 루프, 동시성 파티셔닝, Fail-Closed 퍼미션
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
            // ── 1. 모델 호출 (SSE 스트리밍) ──
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

            // ── 2. 도구 사용 추출 ──
            var toolUses = response.ExtractToolUses();
            if (toolUses.Count == 0) break; // 도구 없음 → 대화 종료

            // ── 3. 동시성 파티셔닝 ──
            var batches = PartitionByConcurrency(toolUses);
            var toolResults = new List<ToolResultBlock>();

            foreach (var batch in batches)
            {
                if (batch.IsConcurrencySafe)
                {
                    // 병렬 실행
                    var tasks = batch.Blocks.Select(block =>
                        ExecuteToolWithPipelineAsync(block, ct));
                    var results = await UniTask.WhenAll(tasks);
                    toolResults.AddRange(results);
                }
                else
                {
                    // 직렬 실행
                    foreach (var block in batch.Blocks)
                    {
                        var result = await ExecuteToolWithPipelineAsync(
                            block, ct);
                        toolResults.Add(result);
                    }
                }
            }

            // ── 4. 결과를 메시지에 추가 ──
            messages.Add(new Message
            {
                Role = "user",
                Content = toolResults.Select(r => r.ToContentBlock()).ToList()
            });

            // ── 5. 다음 반복 ──
        }
    }

    private async UniTask<ToolResultBlock> ExecuteToolWithPipelineAsync(
        ToolUseBlock block, CancellationToken ct)
    {
        var tool = _tools.FindByName(block.Name);

        // ① 퍼미션 결정 (Fail-Closed)
        var permission = await _permissions.DecideAsync(tool, block.Input, ct);
        if (permission.IsDenied)
            return ToolResultBlock.Error(block.Id, permission.DenyMessage);

        // ② Pre-tool 훅
        var preHook = await _hooks.RunPreToolHooksAsync(
            block.Name, block.Input, ct);
        if (preHook.IsBlocking)
            return ToolResultBlock.Error(block.Id, preHook.BlockMessage);

        // ③ 도구 실행
        try
        {
            var result = await tool.HandleCommand(
                preHook.ModifiedInput ?? block.Input, ct);

            // ④ Post-tool 훅
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

## 13. 정리 — 하네스 엔지니어링의 8가지 원칙

AI 에이전트 하네스에서 추출한 설계 원칙을 정리한다. 이 원칙들은 **언어와 프레임워크에 독립적**이다.

| # | 원칙 | 핵심 이유 |
|---|------|-----------|
| 1 | **Generator 스트리밍** | 역압 자연 지원, 합성 가능 |
| 2 | **상태 머신 쿼리 루프** | 복구 전략, 디버깅 용이 |
| 3 | **Reflection 도구 발견** | 플러그인 확장, dead code 제거 |
| 4 | **Fail-Closed 퍼미션** | 보안 기본값, 점진적 완화 |
| 5 | **동시성 파티셔닝** | 안전성과 성능의 균형 |
| 6 | **계층적 취소 전파** | 자원 누수 방지, 깨끗한 종료 |
| 7 | **Pre/Post 훅 파이프라인** | 관심사 분리, 외부 확장성 |
| 8 | **의존성 주입 경계** | 테스트 가능성, 교체 용이 |

이 8가지 패턴을 이해하면, **어떤 AI 에이전트 하네스든** 그 구조를 읽고, 확장하고, 재구축할 수 있다.

---

## 참고 자료

- [Claude Code 아키텍처 분석](/posts/ClaudeCodeSourceLeak/) — 설계 원리 추론 분석
- [Claude Code 인사이트](/posts/ClaudeCodeInsights/) — Claude Code의 기본 활용법
- [Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — 공식 도구 사용 가이드
- [unity-cli-connector](https://github.com/youngwoocho02/unity-cli) — Unity Editor 원격 제어 CLI
- [IAsyncEnumerable in .NET](https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/generate-consume-asynchronous-stream) — C# 비동기 스트림 가이드
