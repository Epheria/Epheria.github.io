---
title: "C#은 어떻게 실행되고, 어떻게 자기 자신을 읽는가"
date: 2026-06-02 09:00:00 +0900
categories: [Csharp, internals]
tags: [csharp, dotnet, il, jit, aot, il2cpp, reflection, roslyn, source-generator, metadata]
toc: true
toc_sticky: true
difficulty: advanced
prerequisites:
  - /posts/DotnetEcosystemMap/
  - /posts/DotnetRuntimeVariants/
tldr:
  - C# 코드는 한 번에 기계어가 되지 않습니다. 먼저 **IL(중간 언어)**이 되고, 그 IL을 **언제 번역하느냐**(실행 중 JIT / 빌드 때 AOT)에 따라 JIT·NativeAOT·IL2CPP 세 갈래로 갈립니다
  - IL은 레지스터 없는 **스택 머신**입니다. 박싱·가상 디스패치·문자열 연결처럼 소스가 가리던 비용이 명령어로 드러나고, `if`·`for`는 조건 분기로 평평하게 펼쳐집니다
  - 코드를 "텍스트가 아니라 의미로" 읽으려면 컴파일러의 단계(**어휘분석 → 구문 트리 → 의미 모델 → 심볼**)가 필요합니다. grep은 토큰조차 안 거친 생 텍스트만 봅니다. 이 일을 라이브러리로 떼어준 것이 **Roslyn**입니다
  - 결정적 긴장은 하나입니다. **"런타임에 새 코드를 만들 수 있는가."** JIT은 되고 AOT는 안 됩니다. 그래서 리플렉션의 동적 기능·Roslyn이 AOT와 충돌하고, **Source Generator**(컴파일 타임 메타프로그래밍)가 그 충돌을 비껴갑니다
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 이 글이 출발한 자리

언젠가 유니티 프로젝트의 C# 코드를 **분석하는 작은 도구**를 만들기로 했습니다. "이 프레젠터의 이 메서드가 실제로 어떤 구현을 호출하는가"를 따라가 주는 도구입니다. 코드를 짜기도 전에 두 가지 질문에 막혔습니다.

1. **이 도구 자체를 어떻게 빌드해서 배포하지?** — C#으로 만든 이 실행 파일을 어떤 형태로 내보내야 빠르고 가벼울까
2. **이 도구가 C# 코드를 어떻게 *읽게* 하지?** — 텍스트 검색으로는 안 될 것 같은데, 그럼 무엇으로

두 질문 모두 표면은 "도구 설계"였지만, 답을 찾으려니 결국 **"C# 코드가 대체 어떻게 실행되고, 어떻게 자기 자신을 이해하는가"**라는 밑바닥까지 내려가야 했습니다. 이 글은 그 한 바퀴의 기록입니다. 도구는 어디까지나 **질문을 던진 계기**일 뿐이고, 무게중심은 그 과정에서 만난 기술들 — IL·JIT·AOT·리플렉션·Roslyn — 의 **작동 원리**에 둡니다.

- **1부**는 첫 질문에서 출발합니다. C# 한 줄이 CPU에 도달하기까지 무슨 일이 일어나는가.
- **2부**는 두 번째 질문입니다. 코드를 텍스트가 아니라 *의미*로 읽는다는 게 무슨 뜻인가.
- **3부**에서 두 질문이 충돌합니다. 그 충돌이 도구의 설계를, 나아가 현대 .NET의 방향을 설명합니다.

> [Foundation 시리즈](/posts/DotnetEcosystemMap/)에서 .NET 스택의 **지도**(언어·IL·런타임의 층 구조)를 그렸습니다. 이 글은 그 지도의 칸들을 열어 **실제 메커니즘**으로 들어갑니다. 지도와 겹치는 개요는 짧게 짚고, 그 아래로 파고듭니다.

---

# 1부. 코드가 기계어가 되기까지

## 한 번에 기계어로 가지 않는다

C 언어는 컴파일러가 소스를 곧장 네이티브 코드로 번역합니다. `.c` 파일은 Windows x64용 `.exe`가 되거나 Linux ARM64용 바이너리가 됩니다. 한 번 컴파일한 결과물은 **특정 OS + 특정 CPU 조합**에 묶입니다.

C#은 이 구조를 한 번 쪼갰습니다. C# 소스는 Roslyn 컴파일러를 거쳐 일단 **IL(Intermediate Language)**이라는 중간 바이트코드로만 번역됩니다. IL은 하드웨어·OS에 독립적이고, `.dll`이나 `.exe` 안에 담깁니다. 실제 네이티브 번역은 **그 코드가 어느 기계에서 돌지 알게 된 뒤** 따로 수행됩니다.

이 "따로 수행되는 번역"의 **시점**이 1부의 핵심입니다. 시점은 두 가지입니다.

- **JIT (Just-In-Time)** — 프로그램이 실행되는 **그 기계에서, 그 순간** IL을 기계어로 번역
- **AOT (Ahead-Of-Time)** — 앱을 배포하기 **전에 미리** 네이티브 코드로 번역

같은 IL인데 번역 시점이 다른 것 — 이 한 갈래가 뒤에서 다룰 세 런타임을 가르고, 내 도구를 어떻게 배포할지까지 결정합니다. 그 갈래를 제대로 이해하려면, 먼저 **번역의 대상인 IL이 어떻게 생겼는지**부터 직접 봐야 합니다.

## IL은 스택 머신이다

IL을 처음 보면 어셈블리와 비슷해 보이지만, 결정적으로 다른 점이 하나 있습니다. **레지스터가 없습니다.**

x86·ARM 같은 실제 CPU는 **레지스터 머신**입니다. `add rax, rbx`처럼 "어느 레지스터의 값과 어느 레지스터의 값을 더해 어디에 넣어라"를 명시합니다. 피연산자의 위치를 명령어가 직접 가리킵니다.

IL은 **스택 머신**입니다. 피연산자를 가리키는 대신, **평가 스택(evaluation stack)**이라는 임시 작업대에 값을 올렸다 내렸다 하며 계산합니다. 모든 연산이 이 한 문장으로 환원됩니다.

> 필요한 값을 스택에 **올리고(push)**, 연산은 스택 위의 값을 **꺼내(pop) 계산한 뒤 결과를 다시 올린다.**

`a + b`를 IL이 어떻게 처리하는지 평가 스택의 상태 변화로 따라가 봅시다.

<div class="il-stk">
  <div class="il-stk-title">평가 스택 — a + b 를 계산하는 세 단계</div>
  <div class="il-stk-row">
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.0</div>
      <div class="il-stk-note">a 를 올린다</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.1</div>
      <div class="il-stk-note">b 를 올린다</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">b</div>
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">add</div>
      <div class="il-stk-note">둘을 꺼내 더해 올린다</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell il-stk-cell-result">a + b</div>
      </div>
    </div>
  </div>
</div>

<style>
.il-stk { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.il-stk-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.il-stk-row { display: flex; align-items: stretch; justify-content: center; gap: 0.5rem; flex-wrap: nowrap; }
.il-stk-step { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: center; padding: 0.75rem 0.5rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.5); }
.il-stk-instr { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 15px; font-weight: 700; color: #6366f1; }
.il-stk-note { font-size: 11px; color: #64748b; margin: 0.25rem 0 0.75rem; text-align: center; }
.il-stk-stack { display: flex; flex-direction: column; justify-content: flex-end; gap: 4px; min-height: 92px; width: 100%; max-width: 130px; }
.il-stk-cell { padding: 7px 0; text-align: center; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 600; color: #1e293b; background: #e0e7ff; border: 1.2px solid #6366f1; border-radius: 4px; }
.il-stk-cell-result { background: #d1fae5; border-color: #10b981; }
.il-stk-arrow { display: flex; align-items: center; color: #94a3b8; font-size: 22px; font-weight: 700; }
[data-mode="dark"] .il-stk { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .il-stk-title { color: #e5e7eb; }
[data-mode="dark"] .il-stk-step { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .il-stk-instr { color: #a5b4fc; }
[data-mode="dark"] .il-stk-note { color: #94a3b8; }
[data-mode="dark"] .il-stk-cell { color: #f1f5f9; background: rgba(99,102,241,0.25); border-color: #818cf8; }
[data-mode="dark"] .il-stk-cell-result { background: rgba(16,185,129,0.25); border-color: #34d399; }
[data-mode="dark"] .il-stk-arrow { color: #64748b; }
@media (max-width: 768px) {
  .il-stk-instr { font-size: 12px; }
  .il-stk-note { font-size: 9px; }
  .il-stk-cell { font-size: 11px; padding: 5px 0; }
  .il-stk-stack { min-height: 72px; }
  .il-stk-arrow { font-size: 16px; }
}
</style>

레지스터 머신이라면 `add r2, r0, r1` 한 줄이면 끝날 일을, IL은 `ldarg.0` / `ldarg.1` / `add` 세 줄로 풉니다. 비효율처럼 보이지만 이게 IL의 핵심 설계입니다. **피연산자의 물리적 위치(어느 레지스터, 몇 개의 레지스터)를 명령어에서 지워버렸기 때문에**, IL은 레지스터가 16개인 CPU든 32개인 CPU든 신경 쓰지 않습니다. "스택에서 둘 꺼내 더한다"는 추상적 약속만 남기고, 실제 레지스터 할당은 번역기(JIT 또는 AOT 컴파일러)가 그 기계에 맞춰 나중에 결정합니다. IL이 플랫폼 독립적일 수 있는 이유가 바로 이 "위치를 지운다"에 있습니다.

## 첫 메서드를 읽는다

추상적인 설명은 여기까지. 실제 C# 메서드 하나를 IL로 번역해 한 줄씩 읽어봅시다. [sharplab.io](https://sharplab.io)에서 출력 모드를 `IL`로 두면 누구나 같은 결과를 볼 수 있습니다.

```csharp
static int Add(int a, int b)
{
    return a + b;
}
```

```
.method private hidebysig static int32 Add(int32 a, int32 b) cil managed
{
    .maxstack 2
    ldarg.0      // a 를 평가 스택에 올린다
    ldarg.1      // b 를 평가 스택에 올린다
    add          // 둘을 꺼내 더한 결과를 올린다
    ret          // 스택 맨 위 값을 반환값으로 반환
}
```

네 줄이 전부입니다.

- **`ldarg.0`** — load argument 0. 0번 인자(`a`)를 평가 스택에 올립니다. `static` 메서드라 0번이 첫 파라미터입니다. (인스턴스 메서드였다면 0번은 `this`이고 `a`는 1번이 됩니다 — 이 한 칸 차이가 IL을 처음 읽을 때 가장 헷갈리는 지점입니다.)
- **`ldarg.1`** — 1번 인자(`b`)를 올립니다. 이제 스택에는 두 값이 쌓였습니다.
- **`add`** — 스택에서 위의 두 값을 꺼내 더하고, 결과 하나를 다시 올립니다. 피연산자를 명시하지 않는다는 점에 주목하세요. 항상 "스택 위 두 개"입니다.
- **`ret`** — 스택 맨 위의 값을 메서드 반환값으로 삼고 호출자에게 돌아갑니다.

`.maxstack 2`는 이 메서드가 실행 중 평가 스택에 **최대 2개**까지 쌓는다는 선언입니다. 번역기는 이 숫자를 보고 스택 검증과 코드 생성을 준비합니다.

## 제어 흐름은 분기로 사라진다

`Add`는 한 줄짜리라 스택 머신의 모양만 보여줬습니다. 실제 코드에는 지역변수가 있고 `if`·`for`·`while` 같은 제어 흐름이 있습니다. 여기서 IL을 읽는 첫 번째 큰 충격이 옵니다. **IL에는 `if`도 `for`도 없습니다.** 전부 조건 분기와 점프 라벨로 평평하게 펼쳐집니다.

```csharp
static int Max(int a, int b)
{
    if (a > b)
        return a;
    return b;
}
```

Release 빌드의 IL은 대략 이렇습니다. (라벨 이름·정확한 명령어는 컴파일러 버전마다 조금씩 다릅니다.)

```
ldarg.0
ldarg.1
ble.s      IL_0006     // a <= b 이면 IL_0006으로 점프
ldarg.0                 // (a > b 인 경우) a 를 올리고
ret
IL_0006:
ldarg.1                 // b 를 올리고
ret
```

읽을 때 가장 헷갈리는 지점은 **조건이 뒤집혀 있다**는 것입니다. 소스의 `if (a > b)`인데 IL은 `ble`("작거나 같으면 분기")를 씁니다. 컴파일러는 "조건이 참이면 본문을 실행"하는 대신, **"조건이 거짓이면 본문을 건너뛴다"**로 번역하는 쪽이 분기 한 번으로 끝나 효율적이기 때문입니다. `if`의 조건과 IL의 분기 조건이 정반대로 보이면, 틀린 게 아니라 이 뒤집기 때문입니다.

루프는 더 극적입니다.

```csharp
static int Sum(int n)
{
    int total = 0;
    for (int i = 0; i < n; i++)
        total += i;
    return total;
}
```

```
.locals init (int32 total, int32 i)
    ldc.i4.0
    stloc.0            // total = 0
    ldc.i4.0
    stloc.1            // i = 0
    br.s      CHECK    // 곧장 조건 검사로 점프
LOOP:
    ldloc.0
    ldloc.1
    add
    stloc.0            // total = total + i
    ldloc.1
    ldc.i4.1
    add
    stloc.1            // i = i + 1
CHECK:
    ldloc.1
    ldarg.0
    blt.s     LOOP     // i < n 이면 LOOP 로 되돌아감
    ldloc.0
    ret
```

`.locals init`은 메서드가 쓰는 지역변수(`total`, `i`)를 미리 선언합니다. 이후 `stloc.0`은 "0번 지역변수에 저장", `ldloc.0`은 "0번 지역변수를 올림"으로, 인자를 다루는 `ldarg`와 짝을 이룹니다. 그리고 루프 진입 시 `br.s CHECK`로 **조건 검사부터** 점프한 뒤, 본문 → 증가 → 조건의 순서로 돌며 조건이 참이면 `blt.s LOOP`로 위로 되돌아갑니다. `n`이 0이면 본문을 한 번도 안 도는 동작이 이 구조에서 자연스럽게 나옵니다.

`if`와 `for`를 종합하면 한 문장이 남습니다. **C#의 모든 제어 흐름은 결국 "조건을 평가해 스택에 올리고, 그 결과로 어디로 점프할지 정하는" 분기 명령어로 환원됩니다.** `while`로 같은 코드를 짜도 IL은 거의 같아집니다. 고수준 문법의 차이는 IL 단계에서 대부분 사라집니다.

참고로 지금까지의 IL은 모두 **Release** 기준입니다. Debug로 빌드하면 줄마다 `nop`이 끼고 반환값을 지역변수에 넣었다 빼는 왕복이 생깁니다(디버거가 중단점을 걸고 값을 들여다보기 위해서). 그래서 성능을 분석할 때는 **항상 Release IL**을 봐야 실제 배포본과 맞습니다.

## 소스에는 안 보이던 비용이 IL에서 드러난다

IL을 읽는 진짜 보람은 여기에 있습니다. C# 소스에서는 평범해 보이던 코드가, IL로 내려가면 **숨어 있던 비용**을 명령어로 노출합니다.

**① 박싱 — `box`.** [메모리 시리즈](/posts/ValueTypeBoxing/)에서 박싱이 "값 타입이 참조 계약과 만나는 순간" 일어난다고 했습니다. 그 순간이 IL에서는 한 줄입니다.

```csharp
object o = 42;
```
```
ldc.i4.s   42
box        [System.Runtime]System.Int32   // 힙에 박스를 만들고 참조를 올림
stloc.0
```

`box` 한 줄이 곧 **힙 할당 한 번**입니다. 꺼낼 때는 `unbox.any`가 등장합니다. 루프 안에서 이 두 단어가 보이면 프레임 스파이크의 후보입니다.

**② 가상 디스패치 — `call` vs `callvirt`.** `call`은 호출 대상이 컴파일 타임에 확정된 경우(`static`·`struct` 메서드), `callvirt`는 런타임에 실제 타입을 보고 정하는 경우(클래스 인스턴스 메서드)입니다. 흥미로운 점은 C#이 **`virtual`이 아닌 인스턴스 메서드도 보통 `callvirt`로 부른다**는 것입니다. `callvirt`가 호출 직전 **null 체크를 겸하기 때문**입니다. "비가상 메서드인데 왜 callvirt지?"는 IL을 처음 읽는 사람이 반드시 한 번 부딪히는 지점입니다.

**③ 문자열 연결 — 사라진 `+`.** `"Hi, " + name`의 IL에는 `+`도 `add`도 없습니다. 대신 `call ... System.String::Concat(string, string)`이 있습니다. 문자열은 불변이라 `+`가 산술일 수 없고, 컴파일러가 메서드 호출로 번역하기 때문입니다. 루프 안 문자열 `+`가 왜 `StringBuilder`보다 느린지의 근거가 IL에 그대로 있습니다.

세 사례의 공통점은 분명합니다. **C# 문법의 편의(`object` 대입, 점 호출, `+`)가 런타임 비용을 가립니다.** IL은 그 편의를 걷어내고 실제로 실행되는 명령어를 보여줍니다. 반대 방향의 발견도 있습니다. `static int Const() => 1 + 2;`의 IL은 `ldc.i4.3 / ret` — `add`가 없습니다. `1 + 2`가 **컴파일 타임에 이미 `3`으로 접혔기**(constant folding) 때문입니다. 그래서 IL을 실험할 때는 상수 대신 인자·필드를 써야 컴파일러의 접기에 가려지지 않습니다.

## 같은 IL, 세 갈래 운명 — JIT · NativeAOT · IL2CPP

이제 첫 질문으로 돌아옵니다. 지금까지 본 IL은 **아직 기계어가 아닙니다.** 누군가 이 IL을 CPU 명령어로 번역해줘야 실행됩니다. 그 번역을 **언제·어떻게** 하느냐가 세 갈래로 갈립니다.

<div class="path3">
  <div class="path3-title">C# → IL 까지는 같다. 그 다음이 갈린다</div>
  <div class="path3-row">
    <div class="path3-col">
      <div class="path3-head path3-head-jit">JIT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ 실행 그 순간</div>
      <div class="path3-box path3-box-end">기계어</div>
      <div class="path3-foot">런타임 필요 · 첫 호출만 느림</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-aot">NativeAOT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ 빌드 때 (ILC)</div>
      <div class="path3-box path3-box-end">기계어</div>
      <div class="path3-foot">런타임 불필요 · 단일 바이너리</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-il2cpp">IL2CPP</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ 빌드 때 (il2cpp)</div>
      <div class="path3-box">C++</div>
      <div class="path3-down">↓ 플랫폼 툴체인</div>
      <div class="path3-box path3-box-end">기계어</div>
      <div class="path3-foot">iOS·콘솔이 JIT 금지 → AOT 강제</div>
    </div>
  </div>
</div>

<style>
.path3 { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.path3-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.path3-row { display: flex; gap: 0.75rem; justify-content: center; align-items: flex-start; flex-wrap: wrap; }
.path3-col { flex: 1 1 180px; max-width: 230px; display: flex; flex-direction: column; align-items: center; padding: 0.75rem 0.5rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.5); }
.path3-head { font-weight: 700; font-size: 14px; padding: 4px 14px; border-radius: 999px; margin-bottom: 0.75rem; }
.path3-head-jit { background: #cffafe; color: #0e7490; }
.path3-head-aot { background: #d1fae5; color: #047857; }
.path3-head-il2cpp { background: #ecfccb; color: #4d7c0f; }
.path3-box { width: 100%; max-width: 130px; padding: 6px 0; text-align: center; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 600; color: #1e293b; background: #e0e7ff; border: 1.2px solid #818cf8; border-radius: 5px; }
.path3-box-end { background: #fce7f3; border-color: #ec4899; }
.path3-down { font-size: 11px; color: #64748b; margin: 4px 0; }
.path3-foot { margin-top: 0.75rem; font-size: 11px; color: #475569; text-align: center; line-height: 1.4; }
[data-mode="dark"] .path3 { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .path3-title { color: #e5e7eb; }
[data-mode="dark"] .path3-col { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .path3-head-jit { background: rgba(6,182,212,0.25); color: #67e8f9; }
[data-mode="dark"] .path3-head-aot { background: rgba(16,185,129,0.25); color: #6ee7b7; }
[data-mode="dark"] .path3-head-il2cpp { background: rgba(101,163,13,0.25); color: #bef264; }
[data-mode="dark"] .path3-box { color: #f1f5f9; background: rgba(99,102,241,0.25); border-color: #818cf8; }
[data-mode="dark"] .path3-box-end { background: rgba(236,72,153,0.25); border-color: #f472b6; }
[data-mode="dark"] .path3-down { color: #94a3b8; }
[data-mode="dark"] .path3-foot { color: #cbd5e1; }
@media (max-width: 768px) {
  .path3-box { font-size: 11px; }
  .path3-down, .path3-foot { font-size: 9px; }
}
</style>

- **JIT** — IL을 들고 있다가 메서드가 **처음 호출되는 순간** 기계어로 번역합니다. 그 기계의 CPU·실행 통계를 보고 최적화할 수 있는 대신, 첫 호출에 번역 비용(cold start)을 냅니다. 일반 .NET 서버·데스크톱, 유니티 에디터의 Mono가 이 방식입니다.
- **NativeAOT** — 빌드할 때 IL을 **네이티브로 직접** 번역해 단일 바이너리로 굳힙니다. 실행 시 번역기가 없어도 돌고, cold start가 거의 0입니다. CLI 도구·서버리스가 주 타깃입니다.
- **IL2CPP** — 유니티가 만든 AOT입니다. IL을 **일단 C++로 변환**한 뒤 플랫폼별 C++ 툴체인(Xcode·NDK·콘솔 SDK)으로 네이티브 빌드합니다. iOS·콘솔이 보안상 JIT를 금지하므로 모바일 빌드에서는 강제입니다.

### 결정적 차이 한 줄 — "런타임에 새 코드를 만들 수 있는가"

세 갈래의 표면은 "번역 시점"이지만, 더 깊은 차이는 하나입니다. **JIT은 실행 중에도 IL을 받아 기계어로 만들 엔진을 들고 있고, AOT는 그 엔진이 없습니다.** 빌드 때 다 굳혀버렸으니까요.

이 한 줄을 기억해 두십시오. 2부와 3부 전체가 이 문장 하나로 연결됩니다. "런타임에 새 코드를 만든다"는 건 곧 **리플렉션의 동적 기능**과 메타프로그래밍을 뜻하고, 그게 바로 내 도구가 의존하게 될 능력이며, 동시에 AOT가 허락하지 않는 능력이기 때문입니다.

### 그래서 내 도구는 어디에 있는가

여기서 첫 질문에 답할 좌표가 잡힙니다. 내 도구는 **두 개의 전혀 다른 빌드**와 헷갈리기 쉽습니다.

- **[A] 분석 *대상*인 게임의 빌드** — 유니티 C#이 IL2CPP를 거쳐 `.ipa`/`.apk`가 됩니다. 플레이어 손에 들어가고, IL2CPP의 AOT 제약을 받습니다.
- **[B] 내 분석 *도구* 자체의 빌드** — 개발자 PC의 터미널에서 도는 별도의 .NET 프로그램입니다. 게임 안에 들어가지 않으므로 **IL2CPP·AOT 제약과 무관**합니다.

도구는 [B]이므로 게임의 IL2CPP 제약을 신경 쓸 필요가 없고, JIT으로 배포할지 NativeAOT로 굳힐지를 **순수하게 도구의 사용성** — 특히 cold start — 기준으로 고를 수 있습니다. 코드 분석 도구는 한 작업에서 수없이 반복 호출되곤 하므로, 매 호출의 기동 시간이 누적됩니다. 그래서 "AOT로 굳혀 cold start를 없앨까?"가 자연스러운 유혹이 됩니다. 그런데 그 유혹에는 함정이 있습니다. 방금 강조한 한 줄 — **AOT는 런타임에 코드를 못 만든다** — 이 도구의 핵심 기능과 충돌할 수 있기 때문입니다. 그 충돌을 보려면 두 번째 질문으로 넘어가야 합니다.

## IL은 절반일 뿐 — 메타데이터라는 짝꿍

2부로 넘어가기 전 다리를 하나 놓습니다. 앞서 본 IL을 다시 보면, 명령어가 **이름과 시그니처를 그대로 인용**하고 있습니다.

```
box   [System.Runtime]System.Int32
call  string [System.Runtime]System.String::Concat(string, string)
```

`System.Int32`가 값 타입인지, `String.Concat`이 어느 어셈블리의 몇 번 메서드인지 — 이 정보는 **IL 명령어 스트림 안에 있지 않습니다.** IL은 "몇 번 토큰을 호출하라"고 가리킬 뿐이고, 그 토큰이 실제로 어떤 타입·메서드·필드인지는 **메타데이터 테이블(metadata tables)**이라는 별도 자료구조가 들고 있습니다. `.dll` 파일은 사실상 **IL 스트림 + 메타데이터 테이블**의 묶음입니다.

이 메타데이터가 2부의 출발점입니다. 런타임이 `typeof(int)`나 `obj.GetType()`으로 타입 정보를 돌려줄 수 있는 것도, Roslyn이 코드를 의미로 읽는 것도, 결국 이 테이블 위에서 일어납니다.

---

# 2부. 코드를 의미로 읽는다

## 두 번째 질문 — grep으로는 왜 안 되는가

내 도구가 해야 할 일은 이런 것입니다. `HouseEditPresenter`의 `OnTapFooter` 메서드가 `_model.UpdateFloor()`를 부를 때, **그 호출이 실제로 어떤 구현으로 가는지** 따라가기.

```csharp
public class HouseEditPresenter
{
    private IHouseEditModel _model;

    public void OnTapFooter()
    {
        _model.UpdateFloor();
    }
}
```

가장 먼저 떠오르는 방법은 텍스트 검색(grep)입니다. `"UpdateFloor"`를 프로젝트 전체에서 찾으면 되지 않을까. 하지만 grep은 곧장 벽에 부딪힙니다. `UpdateFloor`라는 문자열이 나와도, 그것이

- 실제 **메서드 호출**인지
- 주석 `// UpdateFloor 호출 주의` 속 글자인지
- `UpdateFloor`라는 이름의 **변수**인지
- 전혀 다른 클래스의 **동명이인 메서드**인지

grep은 구분하지 못합니다. 더 결정적으로, `_model`의 타입이 인터페이스 `IHouseEditModel`이고 그 실제 구현이 `HouseEditModel`이라는 **연결**을, grep은 만들 수 없습니다. 텍스트 검색에게 코드는 그저 **문자의 나열**입니다. 우리가 필요한 건 문자가 아니라 **의미**입니다.

의미를 얻으려면 텍스트를 한 단계씩 해석해 올라가야 합니다. 그 해석의 단계가 바로 **컴파일러가 코드를 이해하는 과정**입니다.

## 컴파일러는 코드를 어떻게 이해하는가

컴파일러 프론트엔드는 소스 텍스트를 세 단계로 끌어올립니다. 이 세 단계가 컴파일러 이론의 핵심이자, "의미로 읽는다"의 정체입니다.

<div class="sem">
  <div class="sem-title">grep이 멈추는 곳, 컴파일러가 올라가는 곳</div>
  <div class="sem-row">
    <div class="sem-stage sem-stage-dim">
      <div class="sem-stage-name">원본 텍스트</div>
      <div class="sem-stage-ex">_model.UpdateFloor()</div>
      <div class="sem-stage-desc">문자의 나열. grep은 여기만 본다</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">① 어휘 분석<br><span>토큰</span></div>
      <div class="sem-stage-ex">[_model] [.] [UpdateFloor] [(] [)]</div>
      <div class="sem-stage-desc">공백·주석 제거. 주석 속 글자가 걸러진다</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">② 구문 분석<br><span>구문 트리</span></div>
      <div class="sem-stage-ex">멤버호출( 대상=_model, 이름=UpdateFloor )</div>
      <div class="sem-stage-desc">구조를 안다. "호출인가 변수인가" 구분</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage sem-stage-goal">
      <div class="sem-stage-name">③ 의미 분석<br><span>의미 모델</span></div>
      <div class="sem-stage-ex">_model : IHouseEditModel<br>→ 구현 HouseEditModel.UpdateFloor</div>
      <div class="sem-stage-desc">의미를 안다. 타입·심볼 연결 완성</div>
    </div>
  </div>
</div>

<style>
.sem { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(16,185,129,0.04); }
.sem-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.sem-row { display: flex; gap: 0.4rem; justify-content: center; align-items: stretch; flex-wrap: wrap; }
.sem-stage { flex: 1 1 150px; max-width: 210px; display: flex; flex-direction: column; padding: 0.7rem 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.6); }
.sem-stage-dim { background: rgba(148,163,184,0.12); }
.sem-stage-goal { border-color: #10b981; background: rgba(16,185,129,0.1); }
.sem-stage-name { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 0.4rem; line-height: 1.3; }
.sem-stage-name span { font-weight: 600; color: #6366f1; font-size: 12px; }
.sem-stage-ex { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px; color: #334155; background: rgba(99,102,241,0.08); border-radius: 4px; padding: 5px 6px; margin-bottom: 0.4rem; line-height: 1.4; word-break: break-all; }
.sem-stage-desc { font-size: 11px; color: #64748b; margin-top: auto; line-height: 1.4; }
.sem-arrow { display: flex; align-items: center; color: #94a3b8; font-size: 20px; font-weight: 700; }
[data-mode="dark"] .sem { border-color: #334155; background: rgba(16,185,129,0.08); }
[data-mode="dark"] .sem-title { color: #e5e7eb; }
[data-mode="dark"] .sem-stage { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .sem-stage-dim { background: rgba(148,163,184,0.12); }
[data-mode="dark"] .sem-stage-goal { border-color: #34d399; background: rgba(16,185,129,0.15); }
[data-mode="dark"] .sem-stage-name { color: #f1f5f9; }
[data-mode="dark"] .sem-stage-name span { color: #a5b4fc; }
[data-mode="dark"] .sem-stage-ex { color: #cbd5e1; background: rgba(99,102,241,0.18); }
[data-mode="dark"] .sem-stage-desc { color: #94a3b8; }
[data-mode="dark"] .sem-arrow { color: #64748b; }
@media (max-width: 768px) {
  .sem-arrow { transform: rotate(90deg); }
  .sem-stage { max-width: none; }
}
</style>

**① 어휘 분석 (Lexing).** 소스 문자열을 **토큰**의 나열로 쪼갭니다. `_model.UpdateFloor()`는 `[식별자 _model]` `[점]` `[식별자 UpdateFloor]` `[여는 괄호]` `[닫는 괄호]`가 됩니다. 이 단계에서 공백과 주석이 제거됩니다. 곧, grep이 못 거르던 **주석 속 `UpdateFloor`가 여기서 이미 탈락**합니다.

**② 구문 분석 (Parsing).** 토큰을 문법 규칙에 맞춰 **구문 트리(Syntax Tree)**로 조립합니다. "이것은 멤버 접근 표현식이고, 그 안에 메서드 호출이 있다"는 **구조**가 만들어집니다. 이제 "`UpdateFloor`가 호출인지 변수인지"를 구분할 수 있습니다. 다만 구문 트리는 아직 **구조만** 압니다. `_model`이 무슨 타입인지는 모릅니다.

**③ 의미 분석 (Semantic Analysis).** 구문 트리에 **타입과 심볼 정보**를 입힙니다. `_model`의 선언을 찾아 타입이 `IHouseEditModel`임을 알아내고(symbol binding), `UpdateFloor`가 그 인터페이스의 어느 멤버를 가리키는지 연결하고, 그 인터페이스의 구현이 `HouseEditModel`임을 따라갑니다. 이 단계의 결과물이 **의미 모델(Semantic Model)**입니다. 비로소 "이 호출이 실제로 어떤 구현으로 가는가"에 답할 수 있습니다.

세 단계를 관통하는 한 문장은 이것입니다. **grep은 0단계(생 텍스트)에 머물고, 내 도구가 필요한 답은 3단계(의미 모델)에 있습니다.** 그 사이를 직접 구현한다는 건 C# 컴파일러의 프론트엔드를 통째로 다시 만든다는 뜻입니다 — C# 언어 사양은 제네릭·async·람다·패턴 매칭까지 매년 늘어나는 1,500페이지짜리 문서입니다. 혼자 따라갈 수 있는 규모가 아닙니다.

## 리플렉션 — 이미 컴파일된 코드의 의미를 런타임에 읽기

여기서 한 가지 의문이 생깁니다. .NET에는 이미 **리플렉션**이라는, 타입과 멤버를 들여다보는 기능이 있지 않나? `obj.GetType()`, `type.GetMethods()` — 이것으로 안 될까?

리플렉션의 정체는 1부 끝에서 본 **메타데이터 테이블을 런타임에 읽는 API**입니다. 런타임은 `.dll`을 로드할 때 그 안의 메타데이터 테이블을 파싱해 `Type` 객체를 만들어 둡니다. `typeof(int)`가 돌려주는 그 `Type`이 바로 메타데이터 한 행(行)의 런타임 표현입니다. `GetMethods()`는 그 타입에 딸린 메서드 테이블을 훑는 것이고요. 즉 **리플렉션 = 컴파일이 끝난 산출물(IL + 메타데이터)을 거꾸로 들여다보기**입니다.

그런데 리플렉션으로는 내 도구의 일을 할 수 없습니다. 결정적 한계가 있기 때문입니다.

- 리플렉션이 보는 것은 **이미 컴파일된 어셈블리**입니다. 메서드가 **무엇을 호출하는지**(메서드 본문 안의 `_model.UpdateFloor()`)는 메타데이터가 아니라 **IL 본문** 안에 있어, 일반적인 리플렉션 API로는 따라가기 어렵습니다.
- 주석·지역 변수명·"이 호출이 소스 몇 번째 줄인지" 같은 **소스 수준 정보**는 컴파일 과정에서 대부분 사라져 메타데이터에 없습니다.

정리하면, 리플렉션은 "**무엇이 존재하는가**"(이 타입에 어떤 메서드가 있는가)에는 강하지만, "**소스에서 무엇이 무엇을 부르는가**"에는 약합니다. 내 도구가 원하는 건 후자 — 소스 코드의 의미 구조입니다. 그래서 답은 메타데이터를 읽는 리플렉션이 아니라, 소스를 ①②③ 단계로 해석하는 **컴파일러 그 자체**여야 합니다.

## 그래서 Roslyn — 컴파일러를 라이브러리로

**Roslyn**은 Microsoft가 만든 C#의 공식 컴파일러입니다. 그런데 단순한 컴파일러가 아니라, 위의 ①②③ 단계를 **외부 프로그램이 호출할 수 있는 라이브러리(API)로 공개**한 것이 핵심입니다. `dotnet build`가 내부에서 돌리는 그 컴파일러를, 우리가 코드로 불러 쓸 수 있다는 뜻입니다.

Roslyn이 주는 것은 정확히 우리가 1~3단계에서 필요로 했던 것들입니다.

- **SyntaxTree** — ② 구문 트리. 소스의 구조를 노드로 순회
- **SemanticModel** — ③ 의미 모델. "이 노드의 타입은 무엇인가", "이 심볼은 어디 선언됐는가"에 답
- **ISymbol** — 타입·메서드·필드의 의미 단위. 인터페이스와 구현, 호출과 선언을 잇는 매듭

내 도구가 `_model.UpdateFloor()`를 따라갈 때, Roslyn에게 "이 호출 노드의 심볼을 줘"라고 물으면 `IHouseEditModel.UpdateFloor`라는 심볼이 나오고, "이 인터페이스 멤버의 구현을 찾아줘"라고 물으면 `HouseEditModel.UpdateFloor`가 나옵니다. 직접 구현하면 컴파일러 프론트엔드 전체였을 일이, **API 호출 몇 줄**로 끝납니다. 이것이 코드 분석 도구를 C#으로 만들 때 Roslyn을 쓰는 이유입니다.

### 왜 Roslyn은 무거운가 (50MB+)

대가가 있습니다. Roslyn 의존성은 수십 MB에 달합니다. 가벼운 라이브러리가 아닙니다. 그 무게의 정체는 Roslyn이 **컴파일러 한 벌을 통째로** 들고 있기 때문입니다.

- C# 언어 **모든 버전의 문법**(매년 추가되는 기능 포함)
- **MSBuild 통합** — `.csproj`를 읽고, NuGet 패키지를 해석하고, 프로젝트 간 참조를 해결
- **Workspace** 추상화 — 솔루션의 여러 프로젝트를 동시에 분석
- 표준 라이브러리 전체의 **메타데이터 캐시**

즉 Roslyn의 50MB는 "기능이 많아서"가 아니라, **C# 코드를 의미로 이해한다는 일 자체가 그만큼의 지식을 요구하기 때문**입니다. 의미 분석은 한 파일만 봐서는 안 되고, 그 파일이 참조하는 모든 타입·어셈블리·프로젝트를 알아야 가능합니다. Roslyn의 무게는 그 "알아야 할 것들"의 무게입니다.

그리고 여기서, 1부에 강조해 둔 한 줄이 다시 등장합니다. Roslyn은 사용자 프로젝트의 분석기(analyzer)와 소스 생성기를 **런타임에 동적으로 로드**하고, 내부에서 **리플렉션을 광범위하게** 사용합니다. 즉 Roslyn은 "런타임에 코드를 동적으로 다루는" 쪽에 깊이 발을 담그고 있습니다. 바로 그 지점에서, 첫 질문(빠른 기동을 위한 AOT)과 두 번째 질문(Roslyn으로 코드 읽기)이 정면으로 부딪힙니다.

---

# 3부. 두 세계가 충돌하는 곳

## Reflection.Emit — 런타임에 IL을 찍어낸다

충돌의 정체를 보려면, 리플렉션의 나머지 절반을 알아야 합니다. 2부에서 본 리플렉션은 **읽기**(introspection)였습니다. 리플렉션에는 **쓰기**도 있습니다. `System.Reflection.Emit`은 프로그램이 **실행 중에 새 메서드의 IL을 바이트 단위로 생성**해, 런타임에게 "이걸 기계어로 만들어 실행해줘"라고 넘기는 API입니다.

왜 이런 걸 쓸까요. **성능** 때문입니다. 대표적인 예가 직렬화입니다. 어떤 타입을 JSON으로 바꾸는 코드를, 매번 리플렉션으로 필드를 하나씩 읽어가며 처리하면 느립니다. 대신 그 타입 전용 직렬화 코드를 **런타임에 한 번 IL로 생성**해두면, 이후로는 손으로 짠 코드만큼 빠릅니다. DI 컨테이너의 동적 생성자 주입, 동적 프록시, `Expression.Compile()` — 모두 같은 원리로 런타임에 코드를 만들어 속도를 법니다.

## 그래서 AOT와 본질적으로 충돌한다

이제 1부의 한 줄이 완전히 회수됩니다. **AOT는 빌드 때 모든 IL을 미리 기계어로 굳혔기 때문에, 런타임에 IL을 받아 번역해 줄 JIT 엔진이 없습니다.**

그러니 `Reflection.Emit`이 런타임에 IL을 아무리 잘 만들어내도, 그것을 기계어로 바꿔 실행할 곳이 없습니다. 코드가 깨집니다. 이것은 IL2CPP와 NativeAOT가 **공유하는** 제약입니다(둘 다 AOT이므로). [Foundation 3편](/posts/DotnetRuntimeVariants/)에서 표로 정리한 "AOT에서 깨지는 것들"의 근본 원인이 바로 이 한 줄이었습니다.

연쇄적으로 또 하나가 깨집니다. AOT 배포는 보통 **트리밍**(쓰지 않는 코드 제거로 바이너리 축소)을 동반하는데, `type.GetMethod("UpdateFloor")`처럼 **문자열로 멤버를 찾는** 리플렉션은 정적 분석이 불가능합니다. 트리머는 그 메서드가 안 쓰인다고 판단해 지워버리고, 런타임에 리플렉션이 그것을 찾으면 실패합니다.

## 도구의 딜레마, 그리고 작동 원리로서의 결론

두 질문이 만나는 자리가 이제 보입니다.

- **첫 질문의 매력적인 답**: 도구를 NativeAOT로 굳히면 cold start가 사라진다. 반복 호출되는 분석 도구에 이상적이다.
- **두 번째 질문의 필연적인 답**: 도구는 Roslyn에 의존한다. 그런데 Roslyn은 동적 로딩과 리플렉션에 깊이 의존한다.

둘을 겹치면, **Roslyn을 통째로 NativeAOT로 굳히는 것은 본질적으로 어렵습니다.** "코드를 의미로 읽는 능력"과 "빠른 기동"이 서로 다른 런타임 가정 위에 서 있기 때문입니다. 전자는 런타임의 동적 능력을 요구하고, 후자는 그 능력을 포기하는 대가로 얻어집니다. 한 도구가 둘을 동시에 최대로 가질 수는 없습니다.

여기서 중요한 건 "그래서 도구를 어떤 옵션으로 패키징했는가" 하는 세부가 아닙니다. 그건 프로젝트마다 다른 선택일 뿐입니다. 핵심은 그 선택을 강제하는 **구조적 긴장**입니다 — 메타프로그래밍(런타임에 코드를 다루는 힘)과 AOT(런타임의 그 힘을 미리 포기하고 얻는 속도)는 **같은 자원을 두고 경쟁**합니다. 이 긴장을 이해하면, 왜 어떤 .NET 도구는 가볍게 AOT로 떨어지고 어떤 도구는 그러지 못하는지가 한눈에 설명됩니다.

## Source Generator — 충돌을 비껴가는 길

그렇다면 메타프로그래밍을 포기해야 할까요. 현대 .NET의 답은 "포기"가 아니라 **시점을 옮기는 것**입니다.

`Reflection.Emit`이 코드를 **런타임에** 만든다면, **Source Generator**는 같은 일을 **컴파일 타임에** 합니다.

<div class="emit">
  <div class="emit-title">코드를 만드는 시점을 옮긴다</div>
  <div class="emit-row">
    <div class="emit-card emit-card-bad">
      <div class="emit-card-head">Reflection.Emit</div>
      <div class="emit-flow">컴파일 → 실행 → <b>런타임에 IL 생성</b> → JIT가 번역</div>
      <div class="emit-verdict">JIT 필요 · AOT에서 깨짐</div>
    </div>
    <div class="emit-card emit-card-good">
      <div class="emit-card-head">Source Generator</div>
      <div class="emit-flow"><b>컴파일 중 C# 생성</b> → 함께 컴파일 → IL에 이미 포함</div>
      <div class="emit-verdict">런타임 생성 불필요 · AOT 친화</div>
    </div>
  </div>
</div>

<style>
.emit { margin: 1.5rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 10px; background: rgba(99,102,241,0.03); }
.emit-title { text-align: center; font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 1rem; }
.emit-row { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.emit-card { flex: 1 1 240px; max-width: 340px; padding: 0.9rem; border: 1px solid #cbd5e1; border-radius: 8px; background: rgba(255,255,255,0.6); }
.emit-card-bad { border-color: #f59e0b; }
.emit-card-good { border-color: #10b981; }
.emit-card-head { font-family: ui-monospace, SFMono-Regular, monospace; font-weight: 700; font-size: 14px; color: #1e293b; margin-bottom: 0.6rem; }
.emit-flow { font-size: 12.5px; color: #334155; line-height: 1.6; margin-bottom: 0.6rem; }
.emit-flow b { color: #6366f1; }
.emit-verdict { font-size: 12px; font-weight: 600; }
.emit-card-bad .emit-verdict { color: #b45309; }
.emit-card-good .emit-verdict { color: #047857; }
[data-mode="dark"] .emit { border-color: #334155; background: rgba(99,102,241,0.08); }
[data-mode="dark"] .emit-title { color: #e5e7eb; }
[data-mode="dark"] .emit-card { border-color: #475569; background: rgba(15,23,42,0.4); }
[data-mode="dark"] .emit-card-bad { border-color: #d97706; }
[data-mode="dark"] .emit-card-good { border-color: #34d399; }
[data-mode="dark"] .emit-card-head { color: #f1f5f9; }
[data-mode="dark"] .emit-flow { color: #cbd5e1; }
[data-mode="dark"] .emit-flow b { color: #a5b4fc; }
[data-mode="dark"] .emit-card-bad .emit-verdict { color: #fbbf24; }
[data-mode="dark"] .emit-card-good .emit-verdict { color: #6ee7b7; }
@media (max-width: 768px) {
  .emit-flow { font-size: 11.5px; }
}
</style>

Source Generator는 Roslyn 위에서 동작합니다. 컴파일이 진행되는 동안, 2부에서 본 구문 트리·의미 모델을 들여다보고 **추가 C# 소스 코드를 생성**해 컴파일에 끼워 넣습니다. 그 생성된 코드는 본래 코드와 함께 IL로 번역되므로, **결과 IL에는 필요한 코드가 이미 다 들어 있습니다.** 런타임에 `Emit`으로 만들 것이 없습니다. 그래서 AOT와 충돌하지 않습니다.

`System.Text.Json`이 이 방향으로 전환된 것이 대표적입니다. 과거에는 런타임 리플렉션으로 직렬화 코드를 만들었지만, 이제는 Source Generator로 컴파일 타임에 생성해 AOT에서도 온전히 동작합니다. **메타프로그래밍의 시점을 런타임에서 컴파일 타임으로 옮긴 것** — 이것이 현대 .NET이 "동적인 편리함"과 "AOT의 속도"를 화해시킨 방식입니다.

## 종합 — 작은 도구 하나가 건드린 다섯 도메인

처음의 두 질문으로 돌아봅니다. "도구를 어떻게 배포하지", "도구가 코드를 어떻게 읽지" — 표면은 소박했지만, 답을 따라가니 다섯 개의 지식 도메인을 차례로 지나야 했습니다.

- **바이트코드 가상 머신** — IL과 스택 머신 (1부)
- **런타임 시스템** — JIT·AOT의 번역 시점과 그 대가 (1부)
- **컴파일러 이론** — 어휘분석·구문분석·의미분석 (2부)
- **메타프로그래밍과 리플렉션** — 메타데이터, `Emit`, Source Generator (2·3부)
- **정적 프로그램 분석** — 소스의 의미 구조를 읽어 질문에 답하기, 곧 도구가 하려던 일 (전반)

이 다섯이 따로 노는 지식이 아니라 **하나의 질문 안에서 서로 맞물린다**는 것 — 그것이 이 한 바퀴의 결론입니다. IL을 모르면 메타데이터를 모르고, 메타데이터를 모르면 리플렉션을 모르고, 리플렉션과 JIT/AOT의 관계를 모르면 Roslyn이 왜 무거운지, 왜 AOT와 충돌하는지, Source Generator가 왜 등장했는지를 설명할 수 없습니다. 작은 분석 도구 하나를 제대로 만들려는 시도가, 결국 "C#이 어떻게 실행되고 어떻게 자기 자신을 읽는가" 전체를 묻게 만든 셈입니다.

---

## 요약

1. **C#은 한 번에 기계어가 되지 않습니다.** 먼저 IL이 되고, 번역 시점(실행 중 JIT / 빌드 때 AOT)이 JIT·NativeAOT·IL2CPP를 가릅니다. IL은 레지스터 없는 스택 머신이라, 박싱·가상 디스패치 같은 숨은 비용과 제어 흐름의 분기 구조가 명령어로 드러납니다.
2. **코드를 의미로 읽으려면 컴파일러의 세 단계**(어휘분석 → 구문 트리 → 의미 모델)가 필요합니다. grep은 생 텍스트에 머물고, 리플렉션은 이미 컴파일된 산출물만 봅니다. 소스의 의미 구조는 컴파일러 자신, 곧 **Roslyn**이 줍니다. Roslyn이 무거운(50MB+) 이유는 "의미를 안다"는 일이 그만큼의 지식을 요구하기 때문입니다.
3. **모든 것을 잇는 한 줄은 "런타임에 새 코드를 만들 수 있는가"**입니다. JIT은 되고 AOT는 안 됩니다. 그래서 `Reflection.Emit`과 동적 로딩에 의존하는 Roslyn은 AOT와 충돌하고, **Source Generator**가 코드 생성 시점을 컴파일 타임으로 옮겨 그 충돌을 비껴갑니다.
4. **작은 도구 하나가 다섯 도메인**(바이트코드 VM·런타임·컴파일러 이론·메타프로그래밍·정적 분석)을 관통합니다. 이들은 분리된 지식이 아니라 하나의 질문 안에서 맞물려 있습니다.

---

## 참고 자료

### 1차 출처

- [ECMA-335 — Common Language Infrastructure (CLI)](https://ecma-international.org/publications-and-standards/standards/ecma-335/) · IL 명령어 집합과 메타데이터 구조의 표준 사양
- [Roslyn (dotnet/roslyn) GitHub](https://github.com/dotnet/roslyn) · C# 컴파일러·분석 API의 공식 구현
- [Microsoft Learn — Source Generators](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/source-generators-overview) · 컴파일 타임 코드 생성 개요
- [Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · AOT가 깨뜨리는 기능들의 공식 목록
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · IL → C++ 변환의 실제 생성 코드

### 도구

- [SharpLab](https://sharplab.io) · C# ↔ IL ↔ JIT 어셈블리 실시간 변환
- [ILSpy](https://github.com/icsharpcode/ILSpy) · .dll 디스어셈블러·디컴파일러

### 서적

- 『CLR via C#』 (Jeffrey Richter) · IL·메타데이터·리플렉션·JIT 동작의 결정판
- 『Crafting Interpreters』 (Robert Nystrom) · 어휘분석·구문분석·트리 순회를 손으로 구현하는 입문서. 컴파일러 프론트엔드의 작동 원리를 이해하는 바탕 (온라인 무료 공개)
- 『C# in Depth』 (Jon Skeet) · C# 언어 기능이 IL로 어떻게 번역되는지의 동작 원리
