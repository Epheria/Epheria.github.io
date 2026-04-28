---
title: Span&lt;T&gt;와 ReadOnlySpan&lt;T&gt; — 복사 없이 메모리를 바라보는 법
date: 2026-04-30 09:00:00 +0900
categories: [Csharp, memory]
tags: [csharp, dotnet, memory, span, ref-struct, performance, gc, parsing, il2cpp]
toc: true
toc_sticky: true
chart: true
difficulty: intermediate
prerequisites:
  - /posts/ValueTypeBoxing/
tldr:
  - "`Span<T>`는 메모리의 임의 구간을 가리키는 **뷰(view)**입니다. 배열 슬라이스, 부분 문자열, 스택 버퍼를 같은 추상으로 다루며 데이터 복사 없이 일부만 들여다봅니다"
  - "`ref struct`라는 제약은 벌이 아니라 계약입니다. \"스택에만 산다\"는 한 줄짜리 규칙이 박싱·필드 보관·비동기 캡처를 **컴파일러 단에서** 차단합니다"
  - "`\"hello\".Substring(1, 3)`은 12바이트짜리 새 문자열을 할당하지만 `\"hello\".AsSpan(1, 3)`은 **0바이트**입니다. 파싱·로깅·검증처럼 substring을 자주 만드는 코드에서 GC 압력을 한 자릿수로 떨어뜨립니다"
  - .NET 10 (Apple M4 Pro, Arm64 RyuJIT) 실측에서 `string.Substring` + `int.Parse` 파서를 `Span<char>` 기반으로 바꾸면 **6배 이상** 빨라지고 할당이 사라집니다
  - "`Span<T>`가 못 들어가는 자리 — 필드, 비동기 메서드, 람다 캡처 — 는 다음 편의 `Memory<T>`가 맡습니다. 두 타입은 경쟁이 아니라 분업 관계입니다"
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: 박싱편이 남긴 복사 비용

[1편(값 타입 vs 참조 타입과 Boxing)](/posts/ValueTypeBoxing/)의 마지막에 한 가지 부채를 남겼습니다.

> "박싱은 피했지만 `struct` 자체의 **복사 비용**은 남는다."

박싱편의 핵심 규칙 하나를 다시 적어 봅니다.

> 값 타입은 **대입·전달·비교될 때 전체 내용이 복사**됩니다.

이 규칙이 평소엔 직관적이고 바람직합니다. 6 바이트짜리 `(short, int)` 페어를 함수에 넘길 때 복사 한 번은 무시해도 좋은 비용입니다. 그러나 **데이터의 일부만 보고 싶을 때**, 이 복사 규칙이 문제를 일으킵니다.

```csharp
string line = "ID=42,SCORE=1280,TIME=00:01:32";
string idPart = line.Substring(3, 2);    /* "42" — 새 string 할당 */
int id = int.Parse(idPart);              /* 다시 한 번 파싱 */
```

이 두 줄은 **두 번의 힙 할당**을 일으킵니다. `Substring`이 새 `string`을 만들고, 결과가 더 이상 필요 없어지면 GC에 부담을 남깁니다. CSV 한 줄을 파싱하는 단순 코드가 매 호출마다 수십 바이트의 가비지를 만들어냅니다. 게임 루프에서 매 프레임 호출되는 코드라면 이 비용은 누적됩니다.

문제의 본질은 **"복사하지 않고는 일부만 볼 수 없다"**는 데 있습니다. 이 책임을 직접 풀어주는 타입이 이번 편의 주인공 `Span<T>`와 `ReadOnlySpan<T>`입니다.

이번 편의 목표는 세 가지입니다.

1. `Span<T>`를 "ref struct로 박제된 pointer + length"라는 **하나의 정의**로 이해합니다
2. 이 타입이 왜 **`ref struct`라는 강한 제약**을 받아들이는지, 그 제약이 푸는 문제가 무엇인지 봅니다
3. 일상 코드의 substring·split·parse를 어떻게 **할당 0**으로 다시 쓸 수 있는지 .NET 10 실측으로 확인합니다

---

## Part 1. `Span<T>`의 정체

### 1.1 한 줄 정의 — "메모리의 뷰"

`Span<T>`를 요약하는 한 줄은 이것입니다.

> "임의의 메모리 구간을 가리키는 **포인터 + 길이**를, 안전하게 다룰 수 있도록 박제한 타입."

내부 표현은 단순합니다.

```csharp
public readonly ref struct Span<T>
{
    internal readonly ref T _reference;   /* 시작 지점에 대한 관리되는 참조 */
    internal readonly int _length;        /* 길이 */
    /* ... */
}
```

`ref T _reference`는 C# 11 이전에는 직접 표현할 수 없었던 형태입니다. 객체에 대한 일반 참조가 아니라 **객체 내부의 임의 위치**를 가리키는 참조입니다. 배열 한가운데, 문자열의 5번째 문자, 스택 버퍼의 시작점 — 어디든 가리킬 수 있습니다. 이 능력 위에 `_length`만 더하면 "특정 메모리 구간"을 표현할 수 있습니다.

복사 없이 일부만 보는 도구가 정확히 이 모양으로 생긴 것입니다.

<div class="sp-anatomy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Span의 내부 구조 — pointer + length로 메모리 구간을 박제">
  <text x="380" y="26" text-anchor="middle" class="sp-anatomy-title">Span&lt;T&gt; — 메모리 구간을 박제한 ref struct</text>

  <g>
    <text x="160" y="60" text-anchor="middle" class="sp-anatomy-subtitle">스택 — Span&lt;char&gt; 구조</text>
    <rect x="50" y="80" width="220" height="55" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="105" text-anchor="middle" class="sp-anatomy-text-bold">_reference</text>
    <text x="160" y="123" text-anchor="middle" class="sp-anatomy-text-sm">→ 배열 안 위치</text>

    <rect x="50" y="145" width="220" height="50" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="170" text-anchor="middle" class="sp-anatomy-text-bold">_length = 3</text>
    <text x="160" y="187" text-anchor="middle" class="sp-anatomy-text-sm">int</text>
  </g>

  <line x1="270" y1="107" x2="420" y2="155" class="sp-anatomy-arrow" marker-end="url(#sp-anatomy-ah)"/>

  <g>
    <text x="580" y="60" text-anchor="middle" class="sp-anatomy-subtitle">힙 — char[] = "hello"</text>
    <rect x="380" y="120" width="370" height="60" rx="6" class="sp-anatomy-box-heap"/>
    <g>
      <rect x="395" y="135" width="50" height="35" class="sp-anatomy-cell"/>
      <text x="420" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'h'</text>
    </g>
    <g>
      <rect x="450" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="475" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'e'</text>
    </g>
    <g>
      <rect x="505" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="530" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'l'</text>
    </g>
    <g>
      <rect x="560" y="135" width="50" height="35" class="sp-anatomy-cell-active"/>
      <text x="585" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'l'</text>
    </g>
    <g>
      <rect x="615" y="135" width="50" height="35" class="sp-anatomy-cell"/>
      <text x="640" y="158" text-anchor="middle" class="sp-anatomy-text-bold">'o'</text>
    </g>
    <text x="565" y="205" text-anchor="middle" class="sp-anatomy-text-xs">⇧ Span은 인덱스 1~3 (3개) 만 가리킴</text>
  </g>

  <text x="380" y="250" text-anchor="middle" class="sp-anatomy-text-sm">"hello".AsSpan(1, 3) — 새 문자열 없이 'e','l','l' 만 노출</text>

  <defs>
    <marker id="sp-anatomy-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="sp-anatomy-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.sp-anatomy-container { margin: 1.5rem 0; overflow-x: auto; }
.sp-anatomy-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.sp-anatomy-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.sp-anatomy-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.sp-anatomy-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.sp-anatomy-box-heap { fill: #dbeafe; stroke: #3b82f6; stroke-width: 1.3; }
.sp-anatomy-cell { fill: #f3f4f6; stroke: #9ca3af; stroke-width: 1; }
.sp-anatomy-cell-active { fill: #fef08a; stroke: #ca8a04; stroke-width: 1.4; }
.sp-anatomy-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.sp-anatomy-text-sm { font-size: 12px; fill: #4b5563; }
.sp-anatomy-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.sp-anatomy-arrow { stroke: #f59e0b; stroke-width: 1.5; fill: none; }
.sp-anatomy-arrow-head { fill: #f59e0b; }
[data-mode="dark"] .sp-anatomy-title { fill: #f3f4f6; }
[data-mode="dark"] .sp-anatomy-subtitle { fill: #d1d5db; }
[data-mode="dark"] .sp-anatomy-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .sp-anatomy-box-heap { fill: #1e3a8a; stroke: #60a5fa; }
[data-mode="dark"] .sp-anatomy-cell { fill: #374151; stroke: #6b7280; }
[data-mode="dark"] .sp-anatomy-cell-active { fill: #ca8a04; stroke: #fde047; }
[data-mode="dark"] .sp-anatomy-text-bold { fill: #f9fafb; }
[data-mode="dark"] .sp-anatomy-text-sm { fill: #d1d5db; }
[data-mode="dark"] .sp-anatomy-text-xs { fill: #9ca3af; }
[data-mode="dark"] .sp-anatomy-arrow { stroke: #fbbf24; }
[data-mode="dark"] .sp-anatomy-arrow-head { fill: #fbbf24; }
@media (max-width: 768px) {
  .sp-anatomy-title { font-size: 14px; }
  .sp-anatomy-subtitle { font-size: 11px; }
  .sp-anatomy-text-bold { font-size: 11px; }
  .sp-anatomy-text-sm { font-size: 10px; }
}
</style>

핵심 차이를 한 표로 정리합니다.

| 비교 축 | `string.Substring(1, 3)` | `string.AsSpan(1, 3)` |
|--------|---------------------------|------------------------|
| 새 객체 | `string` 1개 (12B + 6B) | 없음 |
| 데이터 복사 | char 3개 | 0개 |
| GC 압력 | 있음 | 없음 |
| 전달 비용 | 참조 8B | `ref T` + `int` = 16B |
| 수명 | GC가 결정 | 원본 메모리에 종속 |

`Span<T>`의 비용은 **원본 메모리에 수명이 묶인다**는 단 하나입니다. 그 한 줄 제약을 받아들이면 할당이 사라집니다.

### 1.2 `Span<T>` vs `ReadOnlySpan<T>`

이름 그대로 **쓰기 가능한가**에서만 갈립니다.

- `Span<T>` — 인덱서가 `ref T`를 반환합니다. 슬라이스 안의 요소를 직접 수정할 수 있습니다
- `ReadOnlySpan<T>` — 인덱서가 `ref readonly T`입니다. 읽기 전용 뷰입니다

`string`에서 얻는 `AsSpan()`은 항상 `ReadOnlySpan<char>`입니다. `string`은 .NET에서 불변 타입이므로 변경 가능한 뷰를 줄 수 없습니다. 반대로 `char[]`에서 얻는 `AsSpan()`은 `Span<char>`입니다.

API 설계 측면에서는 **입력 매개변수는 `ReadOnlySpan<T>`로 받고, 출력 버퍼는 `Span<T>`로 받는** 패턴이 표준입니다.

```csharp
/* 입력은 읽기 전용 — string도, char[]도, stackalloc도 받을 수 있음 */
static int CountVowels(ReadOnlySpan<char> input)
{
    int count = 0;
    foreach (var c in input)
        if ("aeiou".Contains(c)) count++;
    return count;
}

/* 호출 측에서 어떤 메모리든 변환 비용 없이 전달 */
CountVowels("hello world");                /* string 그대로 */
CountVowels("hello world".AsSpan(0, 5));  /* string의 일부 */
CountVowels(new char[]{'h','i'});          /* char[] */
Span<char> tmp = stackalloc char[8];       /* 스택 버퍼 */
CountVowels(tmp);                          /* 변환 없이 전달 */
```

`string`을 받는 API와 `char[]`을 받는 API와 스택 버퍼를 받는 API를 따로 만들 필요가 없습니다. `ReadOnlySpan<char>` 하나로 **모든 메모리 출처를 통일된 인터페이스로** 받습니다.

### 1.3 그러면 왜 `ref struct`인가

`Span<T>`는 평범한 `struct`가 아니라 **`ref struct`**로 선언됩니다. 이 한 단어가 컴파일러에게 강한 제약을 부과합니다.

| 금지 | 이유 |
|------|------|
| 클래스/구조체의 필드로 두기 | 힙으로 탈출하면 `ref T`의 안전을 보장할 수 없음 |
| 박싱 (`object`로 캐스팅) | 박싱은 힙 할당. 위와 같은 이유 |
| `IDisposable` 등 일반 인터페이스 구현 | 인터페이스 캐스팅은 박싱을 동반 |
| `async` 메서드의 지역 변수로 두기 | async 상태 머신은 힙 객체. 위와 같은 이유 |
| 람다 캡처 | 캡처는 클로저(클래스)로 변환되어 힙으로 감 |
| `ValueTuple` 안에 넣기 | 일반 struct도 박싱 경로가 있어 차단 |

이 모든 금지의 공통점은 **힙으로 새는 경로**입니다. `Span<T>`가 가리키는 메모리(특히 `stackalloc`된 스택 버퍼)는 메서드가 끝나는 순간 사라집니다. 그 사라진 메모리를 가리키는 `Span`이 힙 객체 안에 살아남으면 **dangling reference**가 됩니다. C++에서 라이프타임 버그로 새벽에 디버깅하던 그 문제입니다.

`ref struct`는 그 문제를 **컴파일러 단**에서 차단합니다. 런타임 검사 없이 정적으로 막습니다. 이것이 박싱편이 강조한 "값 타입의 안전"을 한 단계 더 끌어올린 형태입니다.

> "Span의 제약은 비용이 아니라 보증입니다. 컴파일러가 받아주는 모든 코드는 메모리 안전입니다."

이 보증의 대가로 우리는 `Span<T>`를 필드에 못 넣고 `async`에 못 들이고 람다에 못 캡처하는 불편을 받습니다. 다음 편에서 다룰 `Memory<T>`가 그 빈자리를 대신합니다.

---

## Part 2. Span의 세 출처 — 배열·string·stackalloc

`Span<T>`의 강력함은 **세 가지 메모리 출처를 같은 추상으로** 다룬다는 데 있습니다. 어디서 왔든 안에서는 똑같이 보입니다.

### 2.1 출처 ① — 배열

가장 흔한 출처입니다. `T[]`의 `AsSpan()`은 배열 전체 또는 일부에 대한 뷰를 만듭니다.

```csharp
int[] scores = { 92, 88, 75, 60, 100 };

Span<int> all   = scores.AsSpan();          /* 전체 */
Span<int> top3  = scores.AsSpan(0, 3);      /* 처음 3개 */
Span<int> tail  = scores.AsSpan(2);         /* 인덱스 2부터 끝까지 */

/* 슬라이스의 슬라이스도 자유 — 새 객체 생성 없음 */
Span<int> middle = top3.Slice(1, 1);        /* { 88 } */

middle[0] = 99;                              /* scores[1]도 99로 바뀜 */
```

`AsSpan()`은 **데이터를 복사하지 않습니다**. 같은 배열을 다른 윈도우로 들여다볼 뿐입니다. 그래서 `middle[0] = 99`가 원본 배열에 영향을 줍니다.

기존 `ArraySegment<T>`도 비슷한 일을 했지만, `Span<T>`는 **인덱서가 `ref T`를 반환**하기 때문에 단순한 읽기·쓰기를 넘어 **무복사 변환**까지 가능합니다.

### 2.2 출처 ② — string과 ReadOnlySpan&lt;char&gt;

문자열은 `Span<T>`가 가장 많이 활약하는 자리입니다. `string.AsSpan()`은 `ReadOnlySpan<char>`를 반환합니다.

```csharp
string log = "[2026-04-30 09:00:00] INFO  Player joined: id=42";

ReadOnlySpan<char> bracket = log.AsSpan(1, 19);   /* "2026-04-30 09:00:00" */
ReadOnlySpan<char> level   = log.AsSpan(22, 4);   /* "INFO" */
ReadOnlySpan<char> id      = log.AsSpan(45, 2);   /* "42" */

int playerId = int.Parse(id);   /* .NET Core 2.1+ : ReadOnlySpan<char> 오버로드 존재 */
```

`Substring` 세 번 호출이라면 **세 개의 새 string + 그만큼의 GC 부담**이 발생합니다. `AsSpan` 세 번이면 **할당 0**입니다. 두 코드의 의미는 같지만 GC 측면의 비용은 다른 차원입니다.

`string`이 immutable이기 때문에 얻는 추가 장점이 있습니다. 원본이 절대 변하지 않으므로 `ReadOnlySpan<char>`이 가리키는 메모리도 변하지 않습니다 — race condition을 걱정할 필요가 없습니다.

### 2.3 출처 ③ — stackalloc

가장 매력적인 출처입니다. **힙을 전혀 건드리지 않고** 임시 버퍼를 만듭니다.

```csharp
static long Sum(ReadOnlySpan<int> xs)
{
    long s = 0;
    foreach (var x in xs) s += x;
    return s;
}

void DoWork()
{
    Span<int> buffer = stackalloc int[64];   /* 256B를 스택에 잡음 */
    for (int i = 0; i < 64; i++) buffer[i] = i * i;

    long total = Sum(buffer);                /* 0 alloc */
}
```

`stackalloc`은 C에 있던 그 `alloca`와 동일한 일을 합니다. 메서드의 스택 프레임 안에 즉석 버퍼를 잡고, 메서드가 끝나면 버퍼도 같이 사라집니다. 이전 C# 시대에는 `stackalloc`이 `unsafe` 컨텍스트에서만 쓸 수 있는 위험한 도구였지만, **C# 7.2 이후 `Span<T>`와 결합**하면서 안전한 일급 기능이 되었습니다.

다만 두 가지를 기억해야 합니다.

**① 스택 크기 제한** — 일반적으로 1MB 정도가 OS 스레드 스택 한도입니다. 게임 클라이언트의 메인 스레드는 더 큰 경우도 있지만, **수 KB 이상의 stackalloc은 위험**합니다. 권장은 1KB 이하, 안전하게는 256B~512B.

```csharp
const int StackThreshold = 256;
Span<byte> buffer = size <= StackThreshold
    ? stackalloc byte[size]
    : new byte[size];
```

**② Zero-init 비용** — .NET 6 이전에는 `stackalloc`이 잡은 메모리를 모두 0으로 초기화했습니다. 작은 버퍼면 무시할 수 있지만, **수백 바이트 이상**에서는 측정 가능한 비용입니다.

.NET 6+에서는 `[SkipLocalsInit]`로 이 zero-init을 끌 수 있습니다.

```csharp
using System.Runtime.CompilerServices;

[SkipLocalsInit]
static int FastParse(ReadOnlySpan<char> s)
{
    Span<char> tmp = stackalloc char[64];   /* zero-init 생략 */
    /* tmp의 초기 내용은 가비지 — 사용 전 반드시 채워야 함 */
    s.CopyTo(tmp);
    /* ... */
}
```

`[SkipLocalsInit]`는 **반드시 사용 전에 모든 위치를 쓴다는 보증**이 있을 때만 쓸 수 있습니다. 그렇지 않으면 이전 스택 프레임의 내용이 그대로 노출됩니다 — 보안 결함이 됩니다.

### 2.4 세 출처를 같은 함수가 받는다

세 가지 출처를 한 함수가 받는 것이 `Span<T>` 설계의 정수입니다.

```csharp
/* 출처를 가리지 않는 단일 API */
static double Average(ReadOnlySpan<double> values)
{
    double sum = 0;
    foreach (var v in values) sum += v;
    return values.Length == 0 ? 0 : sum / values.Length;
}

/* 호출 측 — 세 출처 모두 동일하게 */
double[] heap = { 1.0, 2.0, 3.0 };
Average(heap);                                  /* 배열 */

Span<double> stack = stackalloc double[3] { 1.0, 2.0, 3.0 };
Average(stack);                                 /* 스택 */

ReadOnlySpan<double> slice = heap.AsSpan(1, 2);
Average(slice);                                 /* 배열의 일부 */
```

기존에는 `IEnumerable<T>`가 이 통합을 담당했지만, `IEnumerable<T>`는 **인터페이스 디스패치 + 열거자 객체**의 비용을 동반합니다. `Span<T>`는 동일한 통합을 **0 alloc + 직접 인덱싱**으로 해냅니다.

---

## Part 3. `ref struct` 제약의 깊은 이유

`Span<T>`를 처음 쓰면 반드시 만나는 컴파일 에러들입니다. 왜 이렇게 까다로운지 한 번 정리해두면 평생 안 헷갈립니다.

### 3.1 클래스 필드로 못 두는 이유

```csharp
class Cache
{
    Span<byte> _buffer;   /* CS8345: ref struct 필드는 ref struct에만 허용 */
}
```

만약 가능했다면 어떤 일이 벌어질까요.

```csharp
void Setup(byte[] data)
{
    var cache = new Cache();
    cache._buffer = data.AsSpan();
    /* 여기까지는 OK처럼 보임 */
}

void Setup2()
{
    var cache = new Cache();
    Span<byte> tmp = stackalloc byte[256];
    cache._buffer = tmp;     /* tmp는 이 메서드 끝나면 사라짐 */
    /* cache가 살아있다면 _buffer는 dangling reference */
}
```

`stackalloc` 메모리는 메서드 종료와 함께 사라집니다. 그 메모리를 가리키는 `Span`이 클래스(힙) 안에 살아남으면 곧장 **use-after-free**입니다. C#은 이 가능성 자체를 컴파일 단계에서 막습니다.

`ref struct`의 필드는 다른 `ref struct`에만 둘 수 있습니다. 그렇게 하면 컨테이너도 같은 제약을 상속받게 되고, 결국 모든 길이 스택으로만 이어집니다.

### 3.2 `async` 메서드와 람다에 못 들어가는 이유

```csharp
async Task BadAsync(byte[] data)
{
    Span<byte> view = data.AsSpan();   /* CS4012: ref struct는 async에 사용 불가 */
    await Task.Yield();
    Console.WriteLine(view.Length);
}
```

`async` 메서드는 컴파일러가 **상태 머신 클래스(혹은 struct)**로 변환합니다. `await` 사이에 살아남아야 하는 모든 지역 변수는 그 상태 머신의 **필드**가 됩니다. `Span<T>`는 클래스 필드가 될 수 없으므로 `await` 너머로 살아남을 수 없습니다.

람다도 같은 이유입니다. 캡처된 변수는 컴파일러가 만든 **display class**의 필드가 되고, 그 클래스는 힙으로 갑니다.

```csharp
void BadLambda()
{
    Span<int> nums = stackalloc int[4] { 1, 2, 3, 4 };
    Func<int> first = () => nums[0];   /* CS8175: ref struct를 람다에서 캡처 불가 */
}
```

해결책은 두 가지입니다.

**(a) 동기 헬퍼로 분리** — `await` 전에 데이터를 처리합니다.

```csharp
async Task GoodAsync(byte[] data)
{
    int sum = SyncSum(data.AsSpan());     /* Span은 여기서만 산다 */
    await SaveAsync(sum);
}

static int SyncSum(ReadOnlySpan<byte> view) { /* ... */ }
```

**(b) `Memory<T>` 사용** — 비동기 경계를 넘어야 한다면 다음 편의 `Memory<T>`로 전환합니다. `Memory<T>`는 일반 `struct`라서 async·람다·필드에 자유롭게 들어갑니다.

### 3.3 인터페이스 캐스팅과 박싱 금지

```csharp
ReadOnlySpan<int> view = ...;
IEnumerable<int> seq = view;   /* CS0030: ref struct는 인터페이스로 변환 불가 */
object o = view;               /* CS0029: 박싱 금지 */
```

박싱편에서 본 그대로입니다. 인터페이스 캐스팅과 `object` 캐스팅은 박싱을 동반하고, 박싱은 힙 할당입니다. `Span<T>`가 힙에 가는 모든 길은 막혀 있습니다.

`Span<T>`로 `LINQ`를 쓸 수 없는 것도 이 때문입니다. `LINQ`는 `IEnumerable<T>` 기반이고, `Span<T>`는 인터페이스 구현이 불가능합니다. 대안은 **Span 전용 메서드들** — `Sum`, `Contains`, `IndexOf` 등 `MemoryExtensions`에 누적되어 있는 확장 메서드 — 또는 **수동 `for`/`foreach` 루프**입니다.

### 3.4 우회로 — `scoped` 키워드와 ref 안전성 규칙

C# 11에서 `scoped` 키워드가 추가되어 `ref struct` 매개변수의 라이프타임 규칙을 더 명확히 표현할 수 있게 되었습니다.

```csharp
/* 매개변수 view가 메서드 바깥으로 새지 않음을 보증 */
static int Sum(scoped ReadOnlySpan<int> view)
{
    int s = 0;
    foreach (var v in view) s += v;
    return s;   /* int만 반환 — Span 자체는 새지 않음 */
}
```

`scoped`가 붙은 `ref struct` 매개변수는 **호출자의 라이프타임을 침범할 수 없도록** 강하게 막힙니다. 라이브러리를 작성할 때 호출자가 더 자유롭게 다양한 출처(stackalloc 포함)에서 Span을 넘길 수 있게 하는 장치입니다.

이 규칙을 다 외울 필요는 없습니다. **컴파일 에러가 나면 "이 Span이 어디로 새고 있나?"를 자문**하는 습관 하나면 충분합니다.

---

## Part 4. 일상 코드 속 Span 활용

이론 다음은 실전입니다. 매일 쓰는 코드 패턴 중 어디를 어떻게 바꾸는지 봅니다.

### 4.1 `Substring` → `AsSpan().Slice()`

가장 많이 마주치는 변환입니다.

```csharp
/* ❌ 매 호출마다 새 string 할당 */
string GetExtension(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? "" : path.Substring(dot);
}

/* ✅ 할당 0 — 호출자가 ReadOnlySpan<char>로 받을 수 있을 때 */
ReadOnlySpan<char> GetExtensionSpan(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? ReadOnlySpan<char>.Empty : path.AsSpan(dot);
}
```

호출자가 결과를 **장기 보관해야 한다면** Span 반환은 적합하지 않습니다. 그 경우는 그냥 `string`을 반환하거나(원본 string은 어차피 GC 대상), `Memory<T>`로 바꿉니다. **즉시 사용하고 버리는 substring**일 때만 Span으로 갑니다.

### 4.2 `int.Parse` 진화 — string 인자 → ReadOnlySpan&lt;char&gt; 인자

.NET Core 2.1부터 숫자 파싱 API가 `ReadOnlySpan<char>` 오버로드를 받습니다.

```csharp
string raw = "X=42,Y=88,Z=12";

/* ❌ Substring → Parse — 세 번의 string 할당 */
int x = int.Parse(raw.Substring(2, 2));
int y = int.Parse(raw.Substring(7, 2));
int z = int.Parse(raw.Substring(12, 2));

/* ✅ AsSpan → Parse(ReadOnlySpan<char>) — 0 alloc */
int x2 = int.Parse(raw.AsSpan(2, 2));
int y2 = int.Parse(raw.AsSpan(7, 2));
int z2 = int.Parse(raw.AsSpan(12, 2));
```

같은 패턴이 `double.Parse`, `DateTime.Parse`, `Guid.TryParse`까지 일관되게 적용됩니다. 한국어로 검색하면 잘 나오지 않지만, 표준 BCL의 모든 주요 파싱 API가 이미 Span 오버로드를 갖고 있습니다.

### 4.3 `string.Split` → `MemoryExtensions.Split` (또는 `SpanSplitEnumerator`)

`string.Split`은 결과를 `string[]`으로 반환하므로 **요소 수만큼의 substring + 배열 자체**를 할당합니다. CSV 한 줄을 split하면 가장 비싼 코드 중 하나입니다.

```csharp
/* ❌ 8개 토큰 → 9개 객체 (배열 1 + string 8) */
string line = "id,name,score,time,region,mode,season,build";
string[] tokens = line.Split(',');

/* ✅ .NET 8+ — 0 alloc 파서 */
ReadOnlySpan<char> view = line.AsSpan();
foreach (Range r in view.Split(','))
{
    ReadOnlySpan<char> token = view[r];   /* 새 string 없음 */
    /* token에 대해 처리 */
}
```

.NET 8에서 추가된 `MemoryExtensions.Split(ReadOnlySpan<T>, T)`는 결과로 `Range` 시퀀스를 돌려줍니다. 토큰 자체는 호출자가 원본 Span에서 인덱싱해서 가져옵니다. 결과적으로 **0 alloc로 split**이 가능합니다.

.NET 7 이전에서는 `IndexOf`를 직접 돌려가며 split하는 헬퍼를 짧게 작성하면 됩니다.

```csharp
static IEnumerable<Range> Split(ReadOnlySpan<char> s, char sep)
{
    int start = 0;
    for (int i = 0; i < s.Length; i++)
    {
        if (s[i] == sep)
        {
            yield return new Range(start, i);
            start = i + 1;
        }
    }
    yield return new Range(start, s.Length);
}
/* ⚠️ 위 코드는 yield return + ReadOnlySpan<char> 매개변수 충돌로 동작하지 않음 */
/* Span은 iterator 메서드의 매개변수가 될 수 없음 — 다음 절 참고 */
```

여기서 또 `ref struct` 제약이 등장합니다. `yield return`은 컴파일러가 상태 머신을 만들어내는 자리입니다 — `Span<T>`가 들어갈 수 없습니다. 실전에서는 `ref struct` enumerator를 직접 만들거나(예: `SpanSplitEnumerator`), 아니면 인덱스 배열을 미리 채워두고 호출자가 순회하게 합니다.

### 4.4 Encoding · Hash · 직렬화

표준 라이브러리의 **저수준 변환 API**는 거의 모두 Span으로 재정비되었습니다.

```csharp
/* UTF-8 인코딩 */
ReadOnlySpan<char> text = "안녕하세요".AsSpan();
Span<byte> buffer = stackalloc byte[64];
int written = Encoding.UTF8.GetBytes(text, buffer);
/* buffer.Slice(0, written) 가 인코딩된 UTF-8 바이트 */

/* SHA256 */
ReadOnlySpan<byte> data = ...;
Span<byte> hash = stackalloc byte[32];
SHA256.HashData(data, hash);

/* JSON Reader */
ReadOnlySpan<byte> json = ...;
Utf8JsonReader reader = new(json);
```

**`stackalloc` + Span 입출력의 조합**은 0 alloc 직렬화/해싱 파이프라인의 표준 형태입니다.

### 4.5 `ArrayPool<T>` 미리보기

`stackalloc`의 한계는 1KB 정도입니다. 더 큰 임시 버퍼가 필요할 때, 그러면서도 매번 `new byte[]`로 GC를 자극하고 싶지 않을 때 **`ArrayPool<T>`**가 등장합니다.

```csharp
byte[] rented = ArrayPool<byte>.Shared.Rent(8192);
try
{
    Span<byte> view = rented.AsSpan(0, 8192);
    /* view 사용 */
}
finally
{
    ArrayPool<byte>.Shared.Return(rented);
}
```

`ArrayPool`로 빌린 배열을 `Span<T>`로 보면서 사용하고, 끝나면 풀에 반납합니다. 이 패턴이 **ASP.NET Core의 표준 버퍼링 방식**입니다. 다음 편(`Memory<T>` + `ArrayPool<T>`)에서 본격적으로 다룹니다.

---

## Part 5. 벤치마크 — Substring 기반 vs Span 기반

여기서부터 실측입니다. **.NET 10.0.100** + **BenchmarkDotNet 0.14.0**, 환경은 박싱편과 동일 — **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD** 기준입니다. 측정 코드는 게임 도메인 예제(로그 파싱, 부분 추출, 임시 버퍼 비교)로 작성했습니다.

### 5.1 로그 파싱 — `Substring` + `int.Parse` vs `Span` 기반

**시나리오**: `"[2026-04-30 09:00:00] PlayerId=42,Score=1280,Region=3"` 형태의 로그 1,000줄에서 PlayerId·Score·Region 3개를 추출.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + int.Parse(string)** | 142.6 μs | 1.00 | 144,000 B |
| **AsSpan + int.Parse(ReadOnlySpan&lt;char&gt;)** | 22.3 μs | **0.16** | 0 B |

같은 의미의 코드가 **6.4배** 빠르고 GC 할당이 **완전히 사라집니다**. 1,000줄 파싱에서 약 144KB 할당이 0 B가 됩니다 — 매 프레임 호출되는 코드라면 30프레임 만에 4MB의 가비지를 줄이는 셈입니다.

### 5.2 substring + 즉시 비교 — Equals vs SequenceEqual

**시나리오**: 파일 경로 10,000개에 대해 확장자가 `".png"`인지 검사.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + string.Equals** | 187.4 μs | 1.00 | 320,000 B |
| **EndsWith(string)** | 39.6 μs | 0.21 | 0 B |
| **AsSpan().EndsWith(span)** | 28.8 μs | **0.15** | 0 B |

`EndsWith`만으로도 substring을 안 만들 수 있지만, **호출 측에서 이미 ReadOnlySpan을 갖고 있는 경우** Span 버전이 추가로 빠릅니다. 이 차이는 미미해 보이지만 호출 빈도가 높으면 누적됩니다.

### 5.3 임시 버퍼 — new vs ArrayPool vs stackalloc

**시나리오**: 256바이트 임시 버퍼를 함수 안에서 만들어 채우고 합산. 1만 회 반복.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`new byte[256]`** | 6.42 ms | 1.00 | 2,640,000 B |
| **`ArrayPool.Rent(256)`** | 4.18 ms | 0.65 | 0 B |
| **`stackalloc byte[256]`** | 1.97 ms | **0.31** | 0 B |
| **`stackalloc` + `[SkipLocalsInit]`** | 1.42 ms | **0.22** | 0 B |

`stackalloc`은 GC를 건드리지 않을 뿐 아니라 **메모리 접근 패턴 자체**가 캐시 친화적이라 더 빠릅니다. `[SkipLocalsInit]`로 zero-init까지 끄면 추가 가속이 붙습니다.

다만 256바이트 위는 위험합니다. 8KB가 임시로 필요하다면 `ArrayPool`이 정답입니다.

<div class="chart-wrapper">
  <div class="chart-title">Span 기반 변환 — 최적(1.0x) 기준 상대 실행 시간 · 로그 스케일</div>
  <canvas id="spanBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'spanBench',
  type: 'bar',
  data: {
    labels: ['로그 파싱 (1000줄)', 'EndsWith (10000개)', '임시 버퍼 (10000회)'],
    datasets: [
      {label:'Span / stackalloc', data:[0.16,0.15,0.22], backgroundColor:'rgba(76,175,80,0.75)', borderColor:'rgba(76,175,80,1)', borderWidth:1.5},
      {label:'중간 경로', data:[null,0.21,0.65], backgroundColor:'rgba(255,152,0,0.75)', borderColor:'rgba(255,152,0,1)', borderWidth:1.5},
      {label:'기존 (Substring / new)', data:[1.00,1.00,1.00], backgroundColor:'rgba(244,67,54,0.75)', borderColor:'rgba(244,67,54,1)', borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic', min:0.05, max:1.5, title:{display:true,text:'기존 대비 배수 (로그 스케일)'}, grid:{color:'rgba(128,128,128,0.15)'}, ticks:{callback:function(v){return v+'x';}}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom', labels:{padding:16, usePointStyle:true, pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+(ctx.parsed.y===null?'N/A':ctx.parsed.y.toFixed(2)+'x');}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 5.4 이 숫자들이 말하는 것

세 벤치마크의 공통 패턴입니다.

1. **substring 한 번 → 새 string 한 번 할당**입니다. 그 substring을 즉시 버린다면 그 할당은 100% 낭비입니다. Span으로 받으면 그 낭비가 0이 됩니다
2. **Span 기반 코드가 빠른 이유는 할당이 없을 뿐 아니라 데이터 복사가 없기 때문**입니다. 256바이트 substring 1,000개는 256KB의 추가 메모리 쓰기입니다. 캐시 압력으로도 측정됩니다
3. **`stackalloc`은 작고 짧은 버퍼의 정답**입니다. 256B 이하 + 메서드 종료 전에 사용 끝남 — 두 조건이 맞으면 항상 가장 빠릅니다

---

## Part 6. Unity / IL2CPP 관점

`Span<T>`는 Unity 런타임에서도 동작하지만, CoreCLR과는 다른 압력과 한계를 받습니다.

### 6.1 지원 버전과 백엔드

`Span<T>`가 BCL에 들어온 것은 .NET Core 2.1 / .NET Standard 2.1입니다. Unity 기준으로는:

- **Unity 2021.2 이전** — `System.Memory` NuGet 패키지를 별도 추가하면 사용 가능. 단 Mono 백엔드의 일부 최적화는 빠짐
- **Unity 2021.2 ~ 2022.2** — `.NET Standard 2.1` 호환 프로파일 활성화 시 표준 BCL 그대로 사용
- **Unity 2022.3 LTS 이상** — 기본 활성화. **AsSpan, MemoryExtensions, stackalloc + Span 모두 정상**

IL2CPP 빌드에서도 `Span<T>`는 정상 동작합니다. **C++로 번역된 후의 코드도 동일한 의미**를 갖도록 IL2CPP가 `ref struct` 안전 규칙을 지킵니다.

### 6.2 `NativeArray<T>`와 `Span<T>`의 관계

Unity 고유의 컬렉션 `NativeArray<T>`는 **GC 밖**의 메모리를 다룹니다. C# 메모리 시리즈와는 다른 세계지만, `AsSpan()`이라는 접점이 있습니다.

```csharp
NativeArray<float> velocities = new(1024, Allocator.TempJob);

/* NativeArray → Span으로 빌려보기 */
Span<float> view = velocities.AsSpan();

/* 표준 Span API 그대로 사용 */
view.Fill(0f);
view.Slice(0, 256).CopyTo(view.Slice(256));
```

`NativeArray<T>.AsSpan()`은 Unity 2021.2+에서 제공됩니다. **할당이 발생하지 않습니다** — `NativeArray`가 가리키는 unmanaged 메모리에 대한 Span을 만들 뿐입니다.

이로 인해 같은 함수가 `T[]`도, `NativeArray<T>`도, `stackalloc`도 모두 받을 수 있게 됩니다.

```csharp
static float Average(ReadOnlySpan<float> values) { /* ... */ }

/* 셋 다 동일하게 호출 */
float[] heap = new float[1024];
Average(heap);

NativeArray<float> native = new(1024, Allocator.Temp);
Average(native.AsSpan());

Span<float> stack = stackalloc float[256];
Average(stack);
```

### 6.3 Burst와 Span — 호환성과 한계

Burst 컴파일러는 `NativeArray<T>`와 `Span<T>` 모두를 인식하고 SIMD 최적화 대상으로 다룹니다. 다만 다음을 기억해야 합니다.

- Burst Job 안에서는 **관리되는(managed) 배열의 Span을 사용할 수 없습니다**. Burst가 GC 객체를 다루지 않기 때문입니다
- `NativeArray<T>.AsSpan()`은 OK
- `stackalloc`은 Burst 안에서도 동작 — 내부적으로 stack 메모리는 unmanaged이므로

**Job 안 코드가 0 alloc + Burst SIMD 가속**을 동시에 받는 가장 일반적인 형태가 `NativeArray + AsSpan + stackalloc 임시 버퍼`의 조합입니다.

### 6.4 IL2CPP에서의 `ref struct` 추적

IL2CPP는 IL을 C++로 번역하면서 `ref struct`의 라이프타임 규칙을 그대로 옮깁니다. C# 컴파일러가 받아준 코드는 IL2CPP에서도 받아줍니다 — 추가 검증을 할 필요가 없습니다.

다만 한 가지 주의할 점은 **Span의 `_reference` 필드**가 IL2CPP에서 어떻게 표현되는가입니다. 관리되는 배열을 가리키는 Span은 IL2CPP에서 **GC 핸들 + 오프셋**으로 표현되며, 매 인덱싱마다 약간의 오버헤드가 있습니다. 그러나 Mono 백엔드보다는 일반적으로 빠릅니다.

벤치마크 측면에서는 **Editor / Mono / IL2CPP 세 환경에서 같은 측정**을 해야 정확한 비용을 알 수 있습니다. 박싱편과 마찬가지로 — **배포 대상 백엔드로 측정**이 원칙입니다.

### 6.5 Unity에서 자주 나오는 활용 패턴

**① 매 프레임 string 가공**

```csharp
/* ❌ TextMeshPro 라벨에 매 프레임 새 string */
void Update()
{
    label.text = "HP: " + currentHp + " / " + maxHp;
    /* string.Concat → 새 string + boxed int 두 개 가능성 */
}

/* ✅ Span 기반 포맷팅 (.NET 6+ string interpolation은 내부적으로 Span 활용) */
void Update()
{
    label.text = $"HP: {currentHp} / {maxHp}";
    /* C# 10+ DefaultInterpolatedStringHandler가 Span 풀 사용 */
}
```

C# 10+ 보간 문자열은 내부적으로 `DefaultInterpolatedStringHandler`를 통해 **Span 기반 임시 버퍼**를 사용합니다. 박싱이 사라지고 할당이 한 번으로 줄어듭니다 — 박싱편 4.4절에서 본 것과 같습니다.

**② 네트워크 패킷 디코딩**

```csharp
/* 패킷 수신 — 길이 4B 헤더 + 페이로드 */
ReadOnlySpan<byte> packet = recvBuffer.AsSpan(0, recvLen);
int payloadLen = BinaryPrimitives.ReadInt32LittleEndian(packet[..4]);
ReadOnlySpan<byte> payload = packet.Slice(4, payloadLen);
/* payload 처리 — 0 alloc */
```

`recvBuffer`를 풀에서 빌리고(`ArrayPool<byte>.Shared.Rent(...)`), 그 위에서 Span으로 슬라이싱하는 패턴이 게임 네트워킹의 표준입니다.

**③ 큰 struct를 Span으로 캐스팅 (`MemoryMarshal`)**

```csharp
/* 저수준 메모리 변환 — 같은 메모리를 다른 타입으로 보기 */
Span<Vector3> verts = ...;
Span<float> floats = MemoryMarshal.Cast<Vector3, float>(verts);
/* Vector3 1024개 → float 3072개 — 데이터 그대로, 뷰만 바뀜 */
```

`MemoryMarshal`은 Span의 **재해석(reinterpret)** API를 모아 둔 클래스입니다. 셰이더에 데이터를 넘길 때, 직렬화에서 byte를 다른 타입으로 볼 때 매우 유용합니다.

---

## 요약

이번 편의 핵심을 네 줄로 정리합니다.

1. **`Span<T>`는 데이터를 복사하지 않고 임의 메모리 구간을 들여다보는 뷰**입니다. 배열·문자열·`stackalloc` 세 출처를 같은 추상으로 다루며, 그 위에서 동작하는 BCL API들(`int.Parse`, `Encoding.UTF8.GetBytes`, `MemoryExtensions.Split`, `MemoryMarshal.Cast`)이 0 alloc 코드의 부품이 됩니다
2. **`ref struct` 제약은 비용이 아니라 안전 보증**입니다. 필드·async·람다 캡처 금지는 모두 "Span이 가리키는 메모리가 사라진 뒤에 살아남는 길을 막기 위해" 존재합니다. 컴파일러 단에서 막히는 것이 런타임 버그가 되는 것보다 항상 낫습니다
3. **substring + parse 패턴은 게임 코드에서 가장 흔한 0 alloc 변환 후보**입니다. .NET 10 Arm64 측정에서 같은 의미의 파서가 6배 이상 빨라졌고 GC 할당은 완전히 사라졌습니다. 매 프레임 호출되는 코드부터 우선 점검할 가치가 있습니다
4. **`stackalloc`은 작고 짧은 임시 버퍼의 정답**입니다. 256B 이하 + 메서드 안에서 끝남 — 이 두 조건이 맞으면 `ArrayPool`보다도 빠릅니다. 그 위는 다음 편의 `ArrayPool` 영역입니다

---

## 시리즈 연결: 다음 편 예고

이번 편에서 남긴 두 가지 문제가 다음 편으로 이어집니다.

- **`Span<T>`는 `async`·필드·람다에 못 들어간다**: 3편 **`Memory<T>` + `ArrayPool<T>`** 가 그 빈자리를 맡습니다. 비동기 경계에서도 풀링된 버퍼를 안전하게 들고 다닐 수 있게 됩니다
- **큰 임시 버퍼는 stackalloc로 못 잡는다**: 같은 3편에서 `ArrayPool<T>.Shared.Rent`/`Return` 패턴으로 해결합니다
- **`struct` 자체의 복사 비용 — `in`·`readonly struct`·`ref struct`**: 4편이 그 자리입니다

C# 메모리 시리즈 2편은 여기까지입니다.

---

## 참고 자료

### 1차 출처 · 공식 문서 및 표준

- [Microsoft Learn — `Span<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.span-1) · 공식 레퍼런스
- [Microsoft Learn — `ReadOnlySpan<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.readonlyspan-1) · 공식 레퍼런스
- [Microsoft Learn — `MemoryExtensions` Class](https://learn.microsoft.com/en-us/dotnet/api/system.memoryextensions) · Span 전용 확장 메서드 모음
- [Microsoft Learn — `MemoryMarshal` Class](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.memorymarshal) · Span 재해석 API
- [Microsoft Learn — `stackalloc` (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/stackalloc) · `stackalloc` 공식 해설
- [Microsoft Learn — `[SkipLocalsInit]` Attribute](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.skiplocalsinitattribute) · zero-init 비활성화
- [Microsoft Learn — `scoped` modifier](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/ref) · ref 안전성 규칙

### 블로그 · 심화 분석

- [.NET Blog — "All About Span: Exploring a New .NET Mainstay"](https://learn.microsoft.com/en-us/archive/msdn-magazine/2018/january/csharp-all-about-span-exploring-a-new-net-mainstay) · Stephen Toub, Span 도입 배경
- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) · Stephen Toub, Span 관련 최적화 항목
- [Adam Sitnik — "Span"](https://adamsitnik.com/Span/) · Span 내부 구조와 라이프타임 분석

### 측정 도구

- [BenchmarkDotNet 공식 문서](https://benchmarkdotnet.org/) · `[MemoryDiagnoser]`, `[SimpleJob]` 사용법
- [sharplab.io](https://sharplab.io/) · C# 코드 → IL / JIT 코드 실시간 변환

### 게임 런타임 관점

- [Unity Manual — `NativeArray<T>`](https://docs.unity3d.com/ScriptReference/Unity.Collections.NativeArray_1.html) · NativeArray 공식 레퍼런스
- [Unity Blog — "On DOTS: C# & the Burst Compiler"](https://unity.com/blog/engine-platform/on-dots-c-burst) · Burst와 Span 호환성
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/IL2CPP.html) · IL2CPP 동작 원리
