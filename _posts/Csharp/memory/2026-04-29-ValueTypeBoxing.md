---
title: 값 타입 vs 참조 타입 — 스택·힙과 Boxing의 숨은 비용
date: 2026-04-29 09:00:00 +0900
categories: [Csharp, memory]
tags: [csharp, dotnet, memory, value-type, boxing, performance, gc, il2cpp]
toc: true
toc_sticky: true
chart: true
difficulty: intermediate
prerequisites:
  - /posts/DotnetRuntimeVariants/
tldr:
  - 값 타입이 "스택에 간다"는 말은 반만 맞습니다. 필드의 위치는 **그 필드를 담은 컨테이너**가 결정합니다. 클래스 필드 안의 값 타입은 힙에 살고, 배열 요소의 값 타입도 힙에 살고, 람다가 캡처한 값 타입도 힙에 삽니다
  - Boxing은 "object로 바뀌는 순간"이 아니라 **값 타입이 참조 계약(object·non-generic interface)과 만나는 순간** 발생합니다. `string.Format`·`Dictionary`·`foreach` over `IEnumerable`까지 일상 코드 어디에나 숨어 있습니다
  - 박싱된 값은 원본의 **복사본**이므로 원본을 수정해도 박스는 바뀌지 않습니다. 이 비대칭이 디버깅하기 어려운 버그를 만듭니다
  - .NET 10 (Apple M4 Pro, Arm64 RyuJIT)에서 실측한 결과, 값 타입의 `Equals`는 `IEquatable<T>` 구현 여부에 따라 **95배 이상 속도 차이**가 납니다. 박싱은 단순한 GC 문제가 아니라 **CPU 성능 문제**이기도 합니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 서론: "스택 vs 힙"이라는 말은 왜 자꾸 어긋날까

C# 교과서의 첫 장에서 우리는 이렇게 배웁니다.

> "값 타입(struct)은 스택에, 참조 타입(class)은 힙에 저장됩니다."

이 문장은 **틀린 설명은 아니지만**, 실무에서 만나는 거의 모든 반례를 가립니다. 클래스의 필드로 `int`를 선언하면 그 `int`는 스택이 아니라 **객체가 사는 힙 안**에 있습니다. 람다가 지역 `struct` 변수를 캡처하면 그 `struct` 역시 **힙에 올라간 클로저 안**에 살게 됩니다. JIT이 `struct`를 **레지스터로만 다루면** 스택에도 힙에도 아예 "저장"되지 않습니다.

그래서 "스택 vs 힙"을 언급하는 문장을 만날 때마다 조심해야 할 것이 있습니다. **"어떤 컨테이너 안에 있느냐"가 진짜 질문**이라는 점입니다.

이번 편의 목표는 두 가지입니다.

1. **값 타입과 참조 타입을 "저장 위치"가 아닌 "복사 규칙"으로 재정의**합니다
2. **값 타입이 박싱되는 순간**이 어디인지, 왜 그것이 비싼지, 어떻게 피하는지 구체적으로 봅니다

측정은 .NET 10 위에서 BenchmarkDotNet으로 실측하고, IL은 RyuJIT이 실제로 내놓는 것을 그대로 인용합니다. 게임 프로그래머가 IL2CPP에서 만나는 박싱 함정도 마지막 섹션에서 정리합니다.

---

## Part 1. 값 타입과 참조 타입의 진짜 차이

### 1.1 "스택/힙"이 아니라 "복사 규칙"

값 타입과 참조 타입을 가르는 결정적 차이는 **할당 받았을 때 일어나는 일**이 아니라 **대입·전달·비교될 때 일어나는 일**입니다.

- **값 타입**: 대입 시 **전체 내용이 복사**됩니다. 새 변수는 독립된 복사본을 가집니다.
- **참조 타입**: 대입 시 **객체를 가리키는 포인터(참조)만 복사**됩니다. 원본과 복사본은 같은 객체를 봅니다.

<div class="vt-copy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="값 타입과 참조 타입의 복사 규칙 비교">
  <text x="380" y="26" text-anchor="middle" class="vt-copy-title">값 타입 vs 참조 타입 — 복사의 의미</text>

  <g class="vt-copy-left">
    <text x="180" y="60" text-anchor="middle" class="vt-copy-subtitle">struct Position — 값 타입</text>

    <rect x="40" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="105" text-anchor="middle" class="vt-copy-text-bold">a</text>
    <text x="100" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <rect x="200" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="260" y="105" text-anchor="middle" class="vt-copy-text-bold">b = a</text>
    <text x="260" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>
    <text x="260" y="143" text-anchor="middle" class="vt-copy-text-xs">(독립 복사본)</text>

    <text x="180" y="180" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒</text>
    <rect x="40" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="215" text-anchor="middle" class="vt-copy-text-sm">a.X = 1 (그대로)</text>
    <rect x="200" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct-alt"/>
    <text x="260" y="215" text-anchor="middle" class="vt-copy-text-sm">b.X = 999</text>
  </g>

  <g class="vt-copy-right">
    <text x="580" y="60" text-anchor="middle" class="vt-copy-subtitle">class Player — 참조 타입</text>

    <rect x="420" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="470" y="110" text-anchor="middle" class="vt-copy-text-bold">a = 0x00AF</text>

    <rect x="540" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="590" y="110" text-anchor="middle" class="vt-copy-text-bold">b = 0x00AF</text>

    <rect x="620" y="150" width="120" height="70" rx="6" class="vt-copy-box-heap"/>
    <text x="680" y="175" text-anchor="middle" class="vt-copy-text-bold">힙 0x00AF</text>
    <text x="680" y="195" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <line x1="520" y1="130" x2="620" y2="155" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>
    <line x1="640" y1="130" x2="670" y2="150" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>

    <text x="580" y="250" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒ a.X도 999</text>
  </g>

  <defs>
    <marker id="vt-copy-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-copy-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-copy-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-copy-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.vt-copy-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-copy-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.vt-copy-box-struct { fill: #dbeafe; stroke: #3b82f6; stroke-width: 1.3; }
.vt-copy-box-struct-alt { fill: #fde68a; stroke: #f59e0b; stroke-width: 1.3; }
.vt-copy-box-ref { fill: #e0e7ff; stroke: #6366f1; stroke-width: 1.3; }
.vt-copy-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-copy-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-copy-text-sm { font-size: 12px; fill: #4b5563; }
.vt-copy-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-copy-arrow { stroke: #6366f1; stroke-width: 1.4; fill: none; }
.vt-copy-arrow-head { fill: #6366f1; }
[data-mode="dark"] .vt-copy-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-copy-subtitle { fill: #d1d5db; }
[data-mode="dark"] .vt-copy-box-struct { fill: #1e3a8a; stroke: #60a5fa; }
[data-mode="dark"] .vt-copy-box-struct-alt { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-copy-box-ref { fill: #312e81; stroke: #a78bfa; }
[data-mode="dark"] .vt-copy-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-copy-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-copy-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-copy-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-copy-arrow { stroke: #a78bfa; }
[data-mode="dark"] .vt-copy-arrow-head { fill: #a78bfa; }
@media (max-width: 768px) {
  .vt-copy-title { font-size: 14px; }
  .vt-copy-subtitle { font-size: 11px; }
  .vt-copy-text-bold { font-size: 11px; }
  .vt-copy-text-sm { font-size: 10px; }
}
</style>

"저장 위치가 어디냐"는 이 복사 규칙의 **결과**일 뿐입니다. 값 타입은 복사가 저렴해야 하니까 주로 스택(또는 인라인)에 두는 것이고, 참조 타입은 수명이 불확실하니까 힙에 두고 참조로 관리하는 것입니다. **원인과 결과를 뒤집어 외우면 반례를 만났을 때 대처하지 못합니다.**

### 1.2 동등성 비교도 다릅니다

복사 규칙이 다르니 동등성 판정도 다릅니다.

- **값 타입의 `Equals`**: 기본 구현이 **리플렉션으로 필드를 하나씩 비교**합니다 (`ValueType.Equals(object)`). 박싱 + 리플렉션 이중 비용
- **참조 타입의 `Equals`**: 기본 구현이 **참조 동일성**(`ReferenceEquals`)을 확인합니다 — 같은 객체를 가리키는지만 봄

이 차이는 Part 5 벤치마크에서 수치로 확인하게 됩니다. 값 타입을 `Dictionary` 키로 쓰거나 `List.Contains`로 찾을 때, `IEquatable<T>`를 직접 구현하지 않으면 비교 한 번마다 **박싱과 리플렉션을 둘 다 지불**하게 됩니다.

### 1.3 가변성의 함정

값 타입이 복사된다는 규칙에서 가장 자주 나오는 버그는 **가변 `struct`를 컬렉션에 넣은 뒤 수정하려는 시도**입니다.

```csharp
/* 가변 struct 함정 */
struct Counter
{
    public int Value;
    public void Increment() => Value++;
}

var list = new List<Counter> { new Counter() };
list[0].Increment();        /* 컴파일 에러: list[0]은 값(복사본)이라 수정 불가 */

var copy = list[0];
copy.Increment();            /* copy만 바뀜, 리스트 안의 원본은 그대로 */
```

대부분의 C# 스타일 가이드가 **`struct`는 불변(`readonly struct`)으로** 쓰라고 말하는 이유입니다. 가변 `struct`는 "값"이라는 본질과 프로그래머의 직관이 충돌해 결함을 만듭니다. 이 주제는 4편에서 `readonly struct`와 `ref struct`로 돌아옵니다.

---

## Part 2. "값 타입은 스택" 이 틀린 세 경우

교과서 문장을 살짝 바꿔보겠습니다.

> "값 타입은 **자신을 담은 컨테이너와 같은 곳**에 저장됩니다."

이 한 줄이 훨씬 정확합니다. 지역 변수로 선언된 `struct`만 스택에 올라가고, 나머지 경우는 컨테이너를 따라갑니다.

### 2.1 클래스 필드 안의 값 타입 → 힙

```csharp
class Enemy
{
    public Vector3 Position;   /* 값 타입이지만 힙에 있음 */
    public int Hp;              /* 역시 힙 */
}

var e = new Enemy();            /* e는 힙에 Enemy 객체 할당 */
                                /* Position과 Hp는 그 객체 안에 인라인 저장 */
```

<div class="vt-inline-container">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="클래스 필드 안의 값 타입은 힙에 있음">
  <text x="360" y="26" text-anchor="middle" class="vt-inline-title">class Enemy의 메모리 레이아웃</text>

  <g>
    <rect x="40" y="70" width="160" height="50" rx="6" class="vt-inline-box-stack"/>
    <text x="120" y="95" text-anchor="middle" class="vt-inline-text-bold">스택</text>
    <text x="120" y="112" text-anchor="middle" class="vt-inline-text-sm">e (참조, 8바이트)</text>
  </g>

  <line x1="200" y1="95" x2="340" y2="140" class="vt-inline-arrow" marker-end="url(#vt-inline-ah)"/>

  <g>
    <rect x="340" y="70" width="340" height="200" rx="8" class="vt-inline-box-heap"/>
    <text x="510" y="98" text-anchor="middle" class="vt-inline-text-bold">힙 — Enemy 객체</text>

    <rect x="360" y="115" width="300" height="40" rx="4" class="vt-inline-box-header"/>
    <text x="510" y="140" text-anchor="middle" class="vt-inline-text-sm">ObjectHeader + MethodTable (16바이트)</text>

    <rect x="360" y="160" width="300" height="50" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="180" text-anchor="middle" class="vt-inline-text-sm">Position (struct Vector3)</text>
    <text x="510" y="198" text-anchor="middle" class="vt-inline-text-xs">X, Y, Z — 힙에 인라인</text>

    <rect x="360" y="215" width="300" height="45" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="240" text-anchor="middle" class="vt-inline-text-sm">Hp — 힙에 인라인</text>
  </g>

  <defs>
    <marker id="vt-inline-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-inline-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-inline-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-inline-container svg { width: 100%; max-width: 720px; height: auto; display: block; margin: 0 auto; }
.vt-inline-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-inline-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.vt-inline-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-inline-box-header { fill: #fbcfe8; stroke: #db2777; stroke-width: 1; }
.vt-inline-box-field { fill: #fde2e8; stroke: #f472b6; stroke-width: 1; }
.vt-inline-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-inline-text-sm { font-size: 12px; fill: #4b5563; }
.vt-inline-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-inline-arrow { stroke: #ec4899; stroke-width: 1.4; fill: none; }
.vt-inline-arrow-head { fill: #ec4899; }
[data-mode="dark"] .vt-inline-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-inline-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-inline-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-inline-box-header { fill: #9d174d; stroke: #f9a8d4; }
[data-mode="dark"] .vt-inline-box-field { fill: #9f1239; stroke: #fda4af; }
[data-mode="dark"] .vt-inline-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-inline-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-inline-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-inline-arrow { stroke: #f472b6; }
[data-mode="dark"] .vt-inline-arrow-head { fill: #f472b6; }
@media (max-width: 768px) {
  .vt-inline-title { font-size: 14px; }
  .vt-inline-text-bold { font-size: 11px; }
  .vt-inline-text-sm { font-size: 10px; }
}
</style>

`Position`은 **`Vector3`라는 값 타입**이지만, `Enemy`라는 **참조 타입 안에 인라인**되어 있으므로 힙 위에 놓입니다. 여기서 "값 타입은 스택"이라는 규칙은 깨집니다.

### 2.2 배열 요소 → 힙

```csharp
var positions = new Vector3[1000];
positions[0] = new Vector3(1, 2, 3);    /* 값 1000개가 힙 위 배열에 인라인 */
```

배열은 참조 타입입니다(`T[]`). 그러므로 배열 요소는 힙 위 배열 객체 안에 인라인됩니다. `Vector3[1000]`은 **스택 버퍼가 아니라 힙 위의 12KB 연속 영역**입니다. 이 **힙 위 연속 레이아웃**이야말로 3편에서 만날 `Span<T>`가 활약하는 토대가 됩니다.

### 2.3 람다 캡처 → 힙 (클로저)

```csharp
void Setup()
{
    var count = new Counter();              /* 지역 값 타입 */
    Action handler = () => count.Value++;   /* count를 캡처 */
                                             /* 컴파일러가 비밀 클래스를 만들어 count를 그 안에 담음 */
                                             /* 결과: count는 힙 위 클로저 객체 안 */
}
```

람다가 지역 변수를 캡처하면 컴파일러는 **캡처된 변수들을 필드로 가진 비밀 클래스**(display class)를 만듭니다. 그 클래스는 당연히 참조 타입이고 힙에 할당되므로, 원래 스택에 있었을 `struct`도 따라서 힙에 올라갑니다.

이 세 경우를 모두 안다면 "값 타입은 스택"이 왜 자꾸 어긋나는지 보입니다. **"자신을 담은 컨테이너와 같은 곳"** 규칙 하나가 훨씬 일관됩니다.

### 2.4 JIT의 최후 반전 — Escape Analysis와 Stack Allocation

여기까지는 **소스 레벨 규칙**입니다. 실제 실행 시에는 JIT이 한 번 더 뒤집습니다.

.NET의 RyuJIT은 **Escape Analysis**로 "이 객체가 메서드 바깥으로 탈출하는가?"를 판단합니다. 탈출하지 않으면 힙 할당을 생략하고 **스택에 할당**합니다. .NET 9부터 본격 도입된 이 최적화는 .NET 10에서 제네릭·가상 호출 경계까지 확장됐습니다.

즉 소스에 `new SomeClass()`라고 썼어도, 그 객체가 메서드 안에서만 쓰이고 다른 곳으로 새지 않는다면 **실제로는 스택에 할당**될 수 있습니다. 반대로 값 타입을 박싱하는 순간, 박싱된 객체는 반드시 힙에 가야 합니다 — 참조가 탈출하기 때문입니다.

**그래서 "소스 코드만 보고 할당 위치를 단정 지을 수 없다"**는 것이 현대 .NET의 현실입니다. 신뢰할 수 있는 건 **측정**뿐입니다. BenchmarkDotNet의 `[MemoryDiagnoser]`가 꼭 필요한 이유입니다.

---

## Part 3. Boxing 메커니즘

이제 값 타입과 참조 타입의 경계를 **억지로 넘길 때** 어떤 일이 벌어지는지 봅니다. 그 사건을 **박싱(boxing)**이라고 부릅니다.

### 3.1 박싱의 정의

박싱은 **값 타입의 복사본을 새 힙 객체 안에 감싸는** 연산입니다. 반대는 **언박싱(unboxing)** — 힙에 박스된 값을 꺼내 스택(혹은 레지스터)으로 가져오는 연산입니다.

<div class="vt-box-container">
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="박싱 시퀀스 다이어그램">
  <text x="380" y="26" text-anchor="middle" class="vt-box-title">Boxing — 스택의 값이 힙의 객체로 복사되는 과정</text>

  <g>
    <text x="130" y="70" text-anchor="middle" class="vt-box-subtitle">① 스택의 값 타입</text>
    <rect x="60" y="85" width="140" height="55" rx="6" class="vt-box-stack"/>
    <text x="130" y="108" text-anchor="middle" class="vt-box-text-bold">int i = 42</text>
    <text x="130" y="126" text-anchor="middle" class="vt-box-text-sm">스택, 4바이트</text>
  </g>

  <g>
    <text x="380" y="70" text-anchor="middle" class="vt-box-subtitle">② object 참조가 필요</text>
    <rect x="290" y="85" width="180" height="55" rx="6" class="vt-box-stack"/>
    <text x="380" y="108" text-anchor="middle" class="vt-box-text-bold">object o = i;</text>
    <text x="380" y="126" text-anchor="middle" class="vt-box-text-xs">컴파일러가 box 명령 삽입</text>
  </g>

  <g>
    <text x="630" y="70" text-anchor="middle" class="vt-box-subtitle">③ 힙에 박스 생성</text>
    <rect x="540" y="85" width="180" height="55" rx="6" class="vt-box-heap"/>
    <text x="630" y="106" text-anchor="middle" class="vt-box-text-bold">힙: Box&lt;int&gt; = 42</text>
    <text x="630" y="124" text-anchor="middle" class="vt-box-text-sm">헤더 16B + 값 4B ≈ 24B</text>
  </g>

  <line x1="200" y1="110" x2="290" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>
  <line x1="470" y1="110" x2="540" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>

  <g>
    <text x="380" y="190" text-anchor="middle" class="vt-box-subtitle">④ 박스된 이후 원본을 바꾸면?</text>

    <rect x="60" y="210" width="180" height="60" rx="6" class="vt-box-stack"/>
    <text x="150" y="235" text-anchor="middle" class="vt-box-text-bold">i = 999 (스택)</text>
    <text x="150" y="255" text-anchor="middle" class="vt-box-text-xs">원본만 바뀜</text>

    <rect x="520" y="210" width="200" height="60" rx="6" class="vt-box-heap"/>
    <text x="620" y="235" text-anchor="middle" class="vt-box-text-bold">Box&lt;int&gt; = 42 (힙)</text>
    <text x="620" y="255" text-anchor="middle" class="vt-box-text-xs">박스는 그대로 (복사본)</text>

    <line x1="240" y1="240" x2="520" y2="240" class="vt-box-arrow-dotted"/>
    <text x="380" y="235" text-anchor="middle" class="vt-box-text-xs">독립</text>
  </g>

  <defs>
    <marker id="vt-box-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="vt-box-arrow-head"/>
    </marker>
  </defs>
</svg>
</div>

<style>
.vt-box-container { margin: 1.5rem 0; overflow-x: auto; }
.vt-box-container svg { width: 100%; max-width: 760px; height: auto; display: block; margin: 0 auto; }
.vt-box-title { font-size: 17px; font-weight: 700; fill: #1f2937; }
.vt-box-subtitle { font-size: 13px; font-weight: 600; fill: #374151; }
.vt-box-stack { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1.3; }
.vt-box-heap { fill: #fce7f3; stroke: #ec4899; stroke-width: 1.3; }
.vt-box-text-bold { font-size: 13px; font-weight: 600; fill: #111827; }
.vt-box-text-sm { font-size: 12px; fill: #4b5563; }
.vt-box-text-xs { font-size: 11px; fill: #6b7280; font-style: italic; }
.vt-box-arrow { stroke: #6366f1; stroke-width: 1.4; fill: none; }
.vt-box-arrow-head { fill: #6366f1; }
.vt-box-arrow-dotted { stroke: #9ca3af; stroke-width: 1.2; fill: none; stroke-dasharray: 4 3; }
[data-mode="dark"] .vt-box-title { fill: #f3f4f6; }
[data-mode="dark"] .vt-box-subtitle { fill: #d1d5db; }
[data-mode="dark"] .vt-box-stack { fill: #78350f; stroke: #fbbf24; }
[data-mode="dark"] .vt-box-heap { fill: #831843; stroke: #f472b6; }
[data-mode="dark"] .vt-box-text-bold { fill: #f9fafb; }
[data-mode="dark"] .vt-box-text-sm { fill: #d1d5db; }
[data-mode="dark"] .vt-box-text-xs { fill: #9ca3af; }
[data-mode="dark"] .vt-box-arrow { stroke: #a78bfa; }
[data-mode="dark"] .vt-box-arrow-head { fill: #a78bfa; }
[data-mode="dark"] .vt-box-arrow-dotted { stroke: #6b7280; }
@media (max-width: 768px) {
  .vt-box-title { font-size: 14px; }
  .vt-box-subtitle { font-size: 11px; }
  .vt-box-text-bold { font-size: 11px; }
  .vt-box-text-sm { font-size: 10px; }
}
</style>

그림의 핵심은 ④ 단계입니다. **박싱된 값은 원본과 독립된 복사본**입니다. 원본을 수정해도 박스는 그대로이고, 박스를 수정해도(가능하다면) 원본은 그대로입니다. 이 비대칭이 다음 섹션에서 다룰 미묘한 버그의 원천입니다.

### 3.2 IL 레벨에서 확인

C#이 만든 IL에는 박싱이 **`box`**와 **`unbox.any`**라는 두 명령어로 명시적으로 남습니다. 다음 두 메서드를 컴파일하면 IL이 이렇게 나옵니다 (.NET 10 Release 빌드 기준).

```csharp
public static object BoxInt(int value) => value;
public static int UnboxInt(object boxed) => (int)boxed;
```

```text
BoxInt:
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32
  IL_0006: ret

UnboxInt:
  IL_0000: ldarg.0
  IL_0001: unbox.any [System.Runtime]System.Int32
  IL_0006: ret
```

- **`box [T]`**: 스택의 값을 꺼내 힙에 `T`용 박스 객체를 할당하고, 값을 복사해 넣은 뒤, 박스 참조를 스택에 올립니다
- **`unbox.any [T]`**: 힙의 박스 객체에서 `T` 값을 꺼내 스택에 올립니다 (타입이 다르면 `InvalidCastException`)

"object로 캐스팅하면 박싱된다"는 설명은 맞지만, **정확히 어느 IL 명령이 그걸 하는지** 알면 박싱이 "일어날 것 같다"가 아니라 "반드시 일어난다"고 확신할 수 있습니다.

### 3.3 숨은 박싱 — `Equals(object)`

한 번 더, 박싱이 덜 명시적으로 보이는 예시입니다.

```csharp
public static bool CompareViaObject(int a, int b)
{
    object oa = a;
    object ob = b;
    return oa.Equals(ob);
}
```

IL을 보면 박싱이 **두 번** 일어납니다.

```text
CompareViaObject:
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32    /* a를 힙에 박싱 */
  IL_0006: ldarg.1
  IL_0007: box [System.Runtime]System.Int32    /* b를 힙에 박싱 */
  IL_000c: stloc.0
  IL_000d: ldloc.0
  IL_000e: callvirt instance bool [System.Runtime]System.Object::Equals(object)
  IL_0013: ret
```

두 개의 `int`를 비교하는 데 **24바이트 × 2 = 48바이트 힙 할당**이 일어납니다. 게다가 `Equals(object)`가 호출될 때 내부에서 다시 언박싱 + 비교 루틴을 태우므로 **CPU 비용까지 동반**됩니다. 이런 비용은 Part 5 벤치마크에서 구체 수치로 다시 등장합니다.

### 3.4 박싱된 복사본은 독립적이다

박싱이 복사본을 만든다는 사실을 IL로 확인해 봅니다.

```csharp
public static object MutateAfterBox()
{
    var p = new Point2D(1, 2);
    object boxed = p;
    p.X = 999;
    return boxed;           /* boxed.X는 1일까 999일까? */
}
```

```text
IL_0000: ldloca.s 0                          /* &p (스택 주소) */
IL_0004: call Point2D::.ctor(int32, int32)   /* 스택의 p 초기화 */
IL_0009: ldloc.0                             /* p 값을 스택 top으로 */
IL_000a: box BoxingIL.Point2D                /* 힙에 복사본 박스 생성 */
IL_000f: ldloca.s 0                          /* &p (다시 스택 주소) */
IL_0011: stfld int32 Point2D::X              /* 스택 p.X = 999 */
IL_001b: ret                                 /* 박스(힙) 반환 */
```

`p.X = 999` 대입은 **스택의 `p`**만 건드립니다 (`ldloca.s 0`로 스택 주소를 꺼냄). 힙의 박스는 `box` 명령 직후부터 **완전히 독립**이므로 `boxed.X`는 여전히 `1`입니다.

이 규칙이 미묘한 버그를 만듭니다.

```csharp
/* 안티 패턴 */
var state = new GameState();
RegisterInterface((IStatefulObject)state);   /* 박싱 발생 (struct state → interface) */
state.Score = 100;                           /* 스택의 state만 바뀜 */
                                              /* Register에 들어간 박스는 Score=0 그대로 */
```

인터페이스 캐스팅은 박싱을 일으키고, 그 순간 값의 복사본이 독립됩니다. `struct`를 인터페이스 컬렉션에 넣는 순간, 원본 변경이 반영되지 않는 "얼어붙은 복사본"이 생기는 겁니다. **이 문제가 4편의 `readonly struct`·`ref struct`로 이어집니다.**

---

## Part 4. 일상 코드 속 Boxing 지뢰밭

박싱은 명시적 `object` 캐스팅보다 **훨씬 일상적인 곳**에 숨어 있습니다. 자주 마주치는 다섯 가지를 정리합니다.

### 4.1 `Dictionary<TKey, TValue>` — 키가 `Equals(object)`로 떨어지는 경우

`Dictionary`는 키 비교를 `EqualityComparer<TKey>.Default`로 처리합니다. `TKey`가 `IEquatable<TKey>`를 구현했다면 `Equals(TKey)` 직접 호출 — **박싱 없음**. 구현하지 않았다면 `ValueType.Equals(object)` 경로 — **박싱 + 리플렉션 기반 비교**.

리더보드 캐시처럼 **여러 enum을 조합한 복합 키**가 흔히 나오는 패턴입니다. 동일 캐시를 필터 축별로 나눠 보관하려면 enum 3~4개를 필드로 가진 `struct` 키가 자연스럽습니다.

```csharp
/* Unity/클라이언트에서 자주 쓰는 리더보드 캐시 키 — 3축 enum 조합 */
public enum Region : byte { NA, EU, APAC, SA }
public enum Season : byte { Spring, Summer, Autumn, Winter }
public enum Mode : byte { Solo, Duo, Squad }

/* ❌ IEquatable 없음 — 조회마다 ValueType.Equals(object) → 박싱 + 리플렉션 */
public readonly struct LeaderboardKeyBad
{
    public readonly Region Region;
    public readonly Season Season;
    public readonly Mode Mode;
}

/* ✅ IEquatable + GetHashCode 오버라이드 — 박싱 완전 제거 */
public readonly struct LeaderboardKey : IEquatable<LeaderboardKey>
{
    public readonly Region Region;
    public readonly Season Season;
    public readonly Mode Mode;

    public LeaderboardKey(Region r, Season s, Mode m) { Region = r; Season = s; Mode = m; }

    public bool Equals(LeaderboardKey other) =>
        Region == other.Region && Season == other.Season && Mode == other.Mode;

    public override bool Equals(object obj) => obj is LeaderboardKey o && Equals(o);
    public override int GetHashCode() => HashCode.Combine((int)Region, (int)Season, (int)Mode);
}

/* 사용 — 조회 경로가 완전히 박싱-프리 */
Dictionary<LeaderboardKey, LeaderboardCache> _caches;
var key = new LeaderboardKey(Region.APAC, Season.Summer, Mode.Squad);
if (_caches.TryGetValue(key, out var cache)) { /* ... */ }
```

값 타입을 `Dictionary` 키로 쓸 때는 **반드시 `IEquatable<T>` 구현**이 기본입니다. 구조체 필드를 `readonly`로 표시하면 방어 복사도 함께 제거됩니다(4편의 `readonly struct` 편에서 상세). `GetHashCode`도 일관되게 오버라이드해야 하는데, `HashCode.Combine`이 있는 이상 직접 시프트·XOR을 쓸 이유는 없습니다.

### 4.2 `foreach` over non-generic `IEnumerable`

제네릭이 도입되기 전의 컬렉션(`ArrayList`, `Hashtable`)을 `foreach`로 순회하면 모든 요소가 `object`로 취급돼 **순회할 때마다 박싱·언박싱**이 일어납니다.

```csharp
var list = new ArrayList { 1, 2, 3 };
foreach (int i in list)          /* 매 반복마다 unbox.any 발생 */
    Console.WriteLine(i);
```

제네릭 `List<int>`로 바꾸면 언박싱이 사라지고 JIT은 int 전용 루프를 인라이닝합니다. 현대 코드에 `ArrayList`·`Hashtable`·`Queue`(non-generic)를 쓸 이유는 없지만, **오래된 라이브러리 경계에서 이런 컬렉션이 넘어오면 한 번에 제네릭 버전으로 승격시키는 것**이 할 수 있는 가장 쉬운 최적화입니다.

### 4.3 `string.Format`과 보간문자열

```csharp
Console.WriteLine(string.Format("Score: {0}, Time: {1}", score, time));
/* score, time이 value type이면 둘 다 박싱 (object[]로 전달되므로) */

Console.WriteLine($"Score: {score}, Time: {time}");
/* C# 10 이전: string.Format과 동일 → 박싱 */
/* C# 10+: DefaultInterpolatedStringHandler가 제네릭 Append<T> 사용 → 박싱 없음 */
```

C# 10(.NET 6)부터 도입된 **보간문자열 핸들러**(`DefaultInterpolatedStringHandler`)는 박싱을 완전히 제거합니다. 이 기능은 컴파일러 버전에 의존하므로 `LangVersion` 설정만 맞추면 모든 프로젝트에서 자동으로 혜택을 받습니다. 그러나 **`string.Format`을 직접 호출**하면 여전히 `object[]` 경로를 타므로 박싱이 살아 있습니다.

### 4.4 이벤트 로그·트레이스에서 박싱 폭포

로깅 라이브러리가 `params object[]`를 받으면 로그 한 줄당 값 타입 개수만큼 박싱이 생깁니다.

```csharp
logger.LogInformation("Player {PlayerId} scored {Score} at {Time}", playerId, score, time);
```

ASP.NET 계열이라면 **Source Generator 기반 `LoggerMessage`**를 쓰면 박싱이 제거됩니다.

```csharp
[LoggerMessage(Level = LogLevel.Information,
    Message = "Player {PlayerId} scored {Score} at {Time}")]
partial void LogPlayerScore(long playerId, int score, DateTime time);
```

**Unity의 경우는 사정이 다릅니다.** `Debug.Log`/`Debug.LogFormat`은 내부적으로 `string.Format` 계열을 타므로 이 자체가 박싱 + 힙 문자열 할당의 원천입니다.

```csharp
/* ❌ Unity — score가 float이면 박싱, 문자열도 매 호출 할당 */
Debug.LogFormat("Damage dealt: {0}", damageAmount);

/* ❌ Unity 2022 LTS 이하 — 보간문자열도 string.Format로 리라이트 → 동일 비용 */
Debug.Log($"Damage dealt: {damageAmount}");

/* ✅ Unity 6 (C# 11 LangVersion) — DefaultInterpolatedStringHandler 경로로 박싱 제거 */
Debug.Log($"Damage dealt: {damageAmount}");   /* 내부 구현이 다름 */

/* ✅ 가장 안전 — 릴리즈 빌드에서 컴파일 아웃 */
[System.Diagnostics.Conditional("UNITY_EDITOR"), System.Diagnostics.Conditional("DEVELOPMENT_BUILD")]
static void DevLog(string msg) => UnityEngine.Debug.Log(msg);
```

게임 런타임이 초당 수천 줄 로그를 찍는다면 이 차이가 Profiler에 잡히는 GC.Alloc을 의미 있게 줄입니다. 릴리즈 빌드에서는 `[Conditional]` 속성으로 **호출 자체를 컴파일러가 제거**하는 것이 최선입니다.

### 4.5 `List<T>.Contains` — 기본 비교자 경로

`List<T>.Contains`는 내부적으로 `EqualityComparer<T>.Default`를 씁니다. `T`가 `IEquatable<T>`를 구현하지 않은 값 타입이면 역시 **박싱 경로**를 탑니다. `Dictionary` 키 케이스와 정확히 같은 이야기입니다.

더 넓게 보면 **값 타입이 "제네릭이지만 비교가 필요한 컬렉션"의 요소나 키로 들어가는 모든 경우**가 여기에 해당합니다. `HashSet<T>`, `Dictionary<TKey,TValue>`, `SortedSet<T>`, `List<T>.Contains/IndexOf/Remove`… 전부입니다.

### 4.6 게임 이벤트 구조체와 `in` 매개변수

실시간 게임에서 이벤트 버스(옵저버·메시지 파이프 등)를 통해 초당 수백~수천 개의 이벤트가 흐릅니다. 이런 이벤트를 `class`로 만들면 발생 빈도만큼 GC.Alloc이 생기고, `struct`로 만들어도 **필드가 많아지면 복사 비용**이 박싱 비용을 초과합니다. 정답은 `readonly struct` + `in` 매개변수 조합입니다.

```csharp
/* 입력 이벤트 — 6개 필드, 매 프레임 여러 번 발행 가능 */
public readonly struct DragEvent
{
    public readonly int PointerId;
    public readonly Vector2 ScreenPosition;
    public readonly Vector2 Delta;
    public readonly Vector2 TotalDelta;
    public readonly DragPhase Phase;        /* enum */
    public readonly float Timestamp;

    public DragEvent(int pid, Vector2 pos, Vector2 delta, Vector2 total, DragPhase phase, float ts)
    {
        PointerId = pid; ScreenPosition = pos; Delta = delta;
        TotalDelta = total; Phase = phase; Timestamp = ts;
    }
}

/* ❌ 값 전달 — 필드 6개(대략 36바이트)가 매 호출마다 복사 */
public interface IDragSubscriber { void OnDrag(DragEvent evt); }

/* ✅ in 전달 — 참조로 읽기 전용 전달, 복사 없음 */
public interface IDragSubscriber { void OnDrag(in DragEvent evt); }
```

이벤트 **본문이 없는** 시그널만 필요한 경우(상태 변경 알림 등)는 0바이트 마커 구조체를 씁니다. `class` 싱글턴이나 `static event`를 쓰지 않고도 타입 기반 디스패치가 가능합니다.

```csharp
/* 0바이트 마커 — 박싱 없이도 이벤트 버스에서 타입 식별만으로 디스패치 */
public readonly struct StaminaChangedSignal { }
public readonly struct MatchEndedSignal { }

/* 데이터가 있는 마커는 readonly struct로 */
public readonly struct ItemStockChanged
{
    public readonly int ItemId;
    public readonly int NewStock;
    public ItemStockChanged(int id, int stock) { ItemId = id; NewStock = stock; }
}

/* MessagePipe 같은 제네릭 이벤트 버스에서 쓰면 박싱 경로가 아예 없음 */
_bus.Publish(new StaminaChangedSignal());
_bus.Publish(new ItemStockChanged(itemId, stock));
```

이 패턴의 핵심은 **"값 타입 = 빠름"이 아니라 "필드 수가 불릴 때까지 값, 그 이후엔 `in`으로 참조"**라는 단계적 전략입니다. `in` 매개변수와 `readonly struct`의 상호작용은 4편에서 벤치마크와 함께 다시 등장합니다.

---

## Part 5. 벤치마크 — 박싱이 실제로 얼마나 비싼가

여기서부터는 실측 데이터입니다. **.NET 10.0.100** + **BenchmarkDotNet 0.14.0**으로 세 가지 시나리오를 측정했습니다. 환경은 **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD** 기준이며, 측정 코드는 각각 독립된 게임 도메인 예제(리더보드 캐시 키, 리스트 합산, 3D 좌표 비교)로 작성했습니다. 원본 측정 결과와 소스는 이 포스트와 같은 커밋의 벤치마크 프로젝트에서 확인할 수 있습니다.

### 5.1 `Dictionary` 조회 — `IEquatable<T>` vs 기본 비교

**시나리오**: `Region × Season × Mode` 3축 enum을 필드로 가진 `readonly struct`를 키로 쓰는 리더보드 캐시. 48개 키를 모두 조회하는 비용을 측정.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **IEquatable 구현** | 208.2 ns | 1.00 | 0 B |
| **IEquatable 없음 (ValueType.Equals)** | 988.8 ns | 4.79 | 3,456 B |

`IEquatable<T>`를 구현하지 않으면 `Dictionary`가 키를 **박싱**한 뒤 `ValueType.Equals(object)`를 리플렉션 기반으로 호출합니다. 결과는 48개 키 조회 단위에서 **4.79배 느리고** 3.4KB의 힙 할당이 추가로 생깁니다. 조회 빈도가 높아질수록 격차는 선형으로 벌어집니다.

### 5.2 `List<int>` vs `ArrayList` — 순회와 언박싱

**시나리오**: 정수 10,000개를 컬렉션에 넣고 `foreach`로 합산.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`List<int>` foreach** | 3.604 μs | 1.00 | 0 B |
| **`ArrayList` foreach** | 13.320 μs | 3.70 | 48 B |
| **`ArrayList` for loop** | 10.943 μs | 3.04 | 0 B |

`ArrayList`의 박싱 비용은 **값 자체에만 드는 게 아닙니다**. `foreach`는 `IEnumerator`를 거치며 열거자 박스(48바이트)를 추가로 할당하고, 매 반복마다 타입 체크와 언박싱을 거칩니다. `for` 루프로 바꾸면 열거자 박싱은 사라지지만 요소 언박싱은 남으므로 여전히 3배 느립니다. **제네릭 컬렉션으로 바꾸는 것**이 `ArrayList`에서 벗어나는 유일한 올바른 방향입니다.

### 5.3 값 타입 `Equals` — `IEquatable<T>`의 효과

**시나리오**: `Point3`(X, Y, Z float) 1,000개 배열에서 타깃과 같은 원소를 세기. 세 가지 변형.

| 메서드 | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **기본 `ValueType.Equals(object)`** | 30,540 ns | 1.00 | 160,096 B |
| **`override Equals` (object 인자)** | 2,883 ns | 0.09 | 32,000 B |
| **`IEquatable<T>` 구현** | 321.4 ns | **0.01** | 0 B |

세 단계의 차이가 값 타입 성능의 본질을 그대로 보여 줍니다.

- **기본 `ValueType.Equals(object)`**: 리플렉션으로 필드를 비교하면서 인자는 물론 내부 비교 루틴까지 박싱 — 1,000개 비교에서 160KB 할당
- **`override Equals(object)`**: 리플렉션은 없어지지만 인자가 `object`라서 **박싱은 그대로** — 32KB(값 32B × 1,000), 성능은 10배 빨라짐
- **`IEquatable<T>.Equals(T)`**: 박싱이 완전히 사라지면서 **기본 대비 95배**, `override` 대비 9배 추가 개선. JIT이 인라이닝까지 가능해짐

10줄 남짓한 `IEquatable<T>` 구현이 값 타입 성능의 궁극 한계를 정합니다.

<div class="chart-wrapper">
  <div class="chart-title">박싱 비용 3종 시나리오 — 최적(1.0x) 기준 상대 실행 시간 · 로그 스케일</div>
  <canvas id="boxingBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'boxingBench',
  type: 'bar',
  data: {
    labels: ['Dictionary 조회 (IEquatable 키)', 'List<int> vs ArrayList', 'struct Equals 3단계'],
    datasets: [
      {label:'최적',data:[1.00,1.00,1.00],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5},
      {label:'중간',data:[null,3.04,8.97],backgroundColor:'rgba(255,152,0,0.75)',borderColor:'rgba(255,152,0,1)',borderWidth:1.5},
      {label:'최악 (박싱 경로)',data:[4.79,3.70,95.02],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic',min:0.9,max:120,title:{display:true,text:'기준 대비 배수 (로그 스케일)'},grid:{color:'rgba(128,128,128,0.15)'},ticks:{callback:function(v){return v+'x';}}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom',labels:{padding:16,usePointStyle:true,pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+(ctx.parsed.y===null?'N/A':ctx.parsed.y.toFixed(2)+'x');}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 5.4 이 숫자들이 말하는 것

세 벤치마크의 공통 패턴입니다.

1. **박싱은 GC 문제이자 CPU 문제**입니다. 힙 할당이 추가되고, 포인터 역참조가 늘어나고, `callvirt`가 타입 체크를 동반하므로 CPU 사이클도 선형으로 증가합니다
2. **`IEquatable<T>` 구현은 "나중에 최적화할 것"이 아니라 "값 타입의 기본값"**입니다. 10줄도 안 되는 코드가 수 배의 성능 차이를 만듭니다
3. **컬렉션에 값 타입을 넣기 전**에 "이 컬렉션이 요소/키를 어떻게 비교·해시·순회하는가?"를 한 번은 점검해야 합니다

---

## Part 6. Unity / IL2CPP 관점 — 게임 프로그래머의 관점에서

값 타입과 박싱은 Unity 런타임(Mono · IL2CPP)에서 **CoreCLR과는 다른 압력**을 받습니다. 같은 코드가 같은 의미로 동작하지만, 병목이 생기는 방식이 다릅니다.

### 6.1 박싱은 IL2CPP에서도 여전히 `GC Alloc`

IL2CPP는 IL을 C++로 번역한 뒤 네이티브로 컴파일하지만, **GC는 여전히 보수적 GC**(Boehm-based)를 씁니다. 박싱된 객체는 힙 할당 대상이고, Unity Profiler에서 **`GC.Alloc`으로 잡힙니다**.

문제는 모바일의 GC입니다. Unity의 기본 GC는 **Stop-the-world** 방식이라 수집이 트리거되면 프레임 전체가 멈춥니다. iOS·Android 실기에서 프레임 스파이크로 이어지는 전형적 원인이 **매 프레임 발생하는 박싱**입니다.

### 6.2 Unity에서 자주 나오는 박싱 패턴

Unity 프로젝트에서 `Profiler → GC Alloc`을 열었을 때 상위에 자주 뜨는 원인들과, 각각의 수정 패턴입니다.

**① 사용자 정의 struct 키에 `IEquatable<T>` 누락**

```csharp
/* ❌ Profiler에서 Hashtable.Equals → ValueType.Equals → 박싱 탐지 */
public struct EnemyKey { public int Id; public int Level; }
Dictionary<EnemyKey, EnemyStats> _stats;

/* ✅ IEquatable<T> + HashCode.Combine */
public readonly struct EnemyKey : IEquatable<EnemyKey>
{
    public readonly int Id;
    public readonly int Level;
    public EnemyKey(int id, int lv) { Id = id; Level = lv; }
    public bool Equals(EnemyKey other) => Id == other.Id && Level == other.Level;
    public override bool Equals(object obj) => obj is EnemyKey o && Equals(o);
    public override int GetHashCode() => HashCode.Combine(Id, Level);
}
```

**② `UnityEvent<T>` 인자에 값 타입**

`UnityEvent<T>`는 인스펙터 바인딩을 위해 내부적으로 `object[]` 경로를 섞어 씁니다. 값 타입 인자를 쓸 때마다 박싱이 발생할 수 있습니다.

```csharp
/* ❌ UnityEvent<int>에 Invoke → 박싱 발생 가능 */
public UnityEvent<int> OnScoreChanged;
OnScoreChanged.Invoke(currentScore);

/* ✅ 제네릭 이벤트 버스(MessagePipe, UniRx Subject<T> 등) — 박싱 없음 */
readonly Subject<int> _scoreChanged = new();
_scoreChanged.OnNext(currentScore);
```

**③ `Debug.LogFormat`과 고빈도 로깅**

앞서 4.4에서 다룬 패턴의 Unity 구체화. 릴리즈 빌드에서는 `[Conditional("UNITY_EDITOR")]` 래퍼로 호출 자체를 컴파일 아웃.

**④ 구형 Mono의 `foreach` 박싱**

Unity 2020 이전 Mono에서는 `List<T>.Enumerator`가 구조체여도 특정 경로에서 `foreach`가 박싱을 일으키는 버전이 있었습니다. Unity 2022.3 LTS 이후 Mono에서는 대부분 해결됐지만, **서드파티 컬렉션**(예: Unity가 아닌 dll로 배포된 자료구조)에서는 여전히 발생 가능합니다. 의심되면 Deep Profile로 `System.Collections.IEnumerator.MoveNext` 호출 스택을 확인하는 것이 빠릅니다.

**⑤ `struct`를 인터페이스로 캐스팅**

3.4절에서 본 "얼어붙은 복사본" 패턴. Unity에서는 `IEnumerable`·`IComparable` 등에 값 타입을 암시적으로 캐스팅하는 코드가 남아있기 쉬운데, 이 순간 박싱이 생기고 복사본 독립성 버그까지 동반됩니다.

### 6.3 Profiler에서 박싱 사냥하는 법

Unity Profiler에서 박싱을 찾아내는 실무 절차입니다.

```csharp
/* ProfilerMarker로 의심 구간 격리 — Editor · Development Build에서 동작 */
using Unity.Profiling;

static readonly ProfilerMarker s_TickEnemies = new("Gameplay.TickEnemies");

void Update()
{
    using (s_TickEnemies.Auto())
    {
        foreach (var e in _enemies) e.Tick();
    }
}
```

위 마커를 달면 Profiler에서 해당 구간의 **GC.Alloc 바이트 수와 호출 스택**을 콜스택과 함께 볼 수 있습니다. 다음 옵션들을 켜 두면 박싱 사냥 효율이 크게 올라갑니다.

- **Deep Profile + GC.Alloc 필터** — 박싱의 직접 원인이 되는 호출 스택 추적. 단 Deep Profile 자체가 오버헤드가 크므로 **의심 씬·의심 기능에만 한정**해서 활성화
- **Allocation Callstacks** — GC.Alloc이 어느 메서드에서 몇 바이트 할당했는지 스택 전체 기록. Unity 2020.2+에서 제공
- **Memory Profiler 패키지** — 스냅샷 간 차이로 특정 프레임에서 발생한 박싱 객체 종류(박스된 `Int32`, `Vector3` 등)를 직접 확인 가능
- **IL2CPP 빌드 vs Mono 빌드 비교** — 같은 박싱도 백엔드별 비용 차이가 있으므로, 최적화 검증은 **배포 대상 백엔드로** 직접 측정해야 실제 효과를 확인할 수 있습니다

### 6.4 `readonly struct`와 `in` 매개변수 — 다음 편 예고

Unity 코드에서 큰 `struct`(예: 6~10개 필드 이벤트 데이터)를 매 프레임 핸들러에 넘길 때 **복사 비용이 박싱 비용을 초과**합니다. 이 비용은 `in` 매개변수(.NET의 **참조로 읽기 전용 전달**)로 제거합니다.

```csharp
/* 값 복사 — 6개 필드가 매 호출마다 복사 */
void OnDrag(DragEventData data) { ... }

/* 참조 전달 — 복사 없음, 읽기 전용 */
void OnDrag(in DragEventData data) { ... }
```

`in`은 4편에서 `readonly struct`·`ref struct`와 함께 본격적으로 다룹니다. 이번 편은 **박싱을 인지하고 IL 수준에서 확인하는 것**까지가 목표입니다.

---

## 요약

이번 편의 핵심을 네 줄로 정리합니다.

1. **"값 타입 = 스택" 대신 "값 타입 = 컨테이너를 따른다"**로 기억해야 반례를 만났을 때 흔들리지 않습니다. 클래스 필드·배열 요소·람다 캡처에서 값 타입은 힙에 살고, JIT의 escape analysis는 그 반대 방향으로도 뒤집습니다
2. **Boxing은 `box` / `unbox.any` IL 명령어**로 명시적으로 발생합니다. C# 소스에서 "object로 캐스팅" 같은 모호한 표현보다 **IL에서 실제로 무엇이 삽입되는가**를 기준으로 판단하는 것이 신뢰할 수 있습니다
3. **박싱된 값은 원본과 독립된 복사본**이라는 사실이 미묘한 버그를 만듭니다. 원본 수정이 박스에 반영되지 않기 때문에, `struct`를 인터페이스 컬렉션에 넣는 패턴은 **얼어붙은 복사본**을 만들어 냅니다
4. **`IEquatable<T>` 구현은 값 타입의 선택이 아니라 기본값**입니다. 이것 하나가 `Dictionary`·`HashSet`·`List.Contains`의 성능을 **수 배 단위**로 갈라놓습니다

---

## 시리즈 연결: 다음 편 예고

이번 편에서 남긴 두 가지 문제가 다음 편들로 이어집니다.

- **박싱은 피했지만 `struct` 자체의 복사 비용**: 3편 **`Span<T>` / `ReadOnlySpan<T>`** 에서 "복사 대신 뷰"로 해결합니다
- **장기 보관이 필요한 버퍼, 비동기 경계**: 4편 **`Memory<T>` + `ArrayPool<T>`** 에서 풀링과 비동기 호환을 다룹니다
- **복사 비용 자체를 없애는 패러다임**: 5편 **`readonly struct` / `ref struct` / `in` 매개변수**

C# 메모리 시리즈 1편은 여기까지입니다.

---

## 참고 자료

### 1차 출처 · 공식 문서 및 표준

- [ECMA-335 — Common Language Infrastructure (CLI) Partition III Section 4](https://ecma-international.org/publications-and-standards/standards/ecma-335/) · `box` / `unbox.any` IL 명령어 공식 정의
- [Microsoft Learn — box (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/user-defined-conversion-operators) · 값 타입과 박싱 공식 해설
- [Microsoft Learn — IEquatable<T> Interface](https://learn.microsoft.com/en-us/dotnet/api/system.iequatable-1) · `IEquatable<T>` 공식 레퍼런스
- [Microsoft Learn — EqualityComparer<T>.Default](https://learn.microsoft.com/en-us/dotnet/api/system.collections.generic.equalitycomparer-1.default) · `Dictionary`/`HashSet`이 사용하는 기본 비교자

### 블로그 · 심화 분석

- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) · Stephen Toub, escape analysis 확장 포함
- [.NET Blog — "Performance Improvements in .NET 9"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-9/) · Stack allocation 최초 도입 분석
- [Microsoft Learn — "DefaultInterpolatedStringHandler"](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.defaultinterpolatedstringhandler) · C# 10 보간문자열 핸들러

### 측정 도구

- [BenchmarkDotNet 공식 문서](https://benchmarkdotnet.org/) · `[MemoryDiagnoser]`, `[SimpleJob]` 사용법
- [sharplab.io](https://sharplab.io/) · C# 코드 → IL / JIT 코드 실시간 변환

### 게임 런타임 관점

- [Unity Manual — Understanding automatic memory management](https://docs.unity3d.com/Manual/performance-managed-memory.html) · Unity GC의 동작 원리
- [Unity Manual — Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@1.0/manual/) · 박싱 추적용 도구
- [Unity Blog — "IL2CPP Internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) · IL2CPP의 박싱 처리 구현
