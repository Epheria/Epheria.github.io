---
title: Value Types vs Reference Types — Stack, Heap, and the Hidden Cost of Boxing
lang: en
date: 2026-04-28 09:00:00 +0900
categories: [Csharp, memory]
tags: [csharp, dotnet, memory, value-type, boxing, performance, gc, il2cpp]
toc: true
toc_sticky: true
chart: true
difficulty: intermediate
prerequisites:
  - /posts/DotnetRuntimeVariants/
tldr:
  - The claim that "value types go on the stack" is only half right. The location of a field is determined by **the container that holds it**. A value type inside a class field lives on the heap, value types in array elements live on the heap, and a value type captured by a lambda lives inside a heap-allocated closure.
  - Boxing does not happen "when a value type becomes an object." It happens **the moment a value type meets a reference contract (object or non-generic interface)**. It hides everywhere in everyday code — `string.Format`, `Dictionary`, `foreach` over `IEnumerable`.
  - A boxed value is a **copy** of the original. Mutating the original does not affect the box. This asymmetry is the source of hard-to-debug bugs.
  - Measured on .NET 10 (Apple M4 Pro, Arm64 RyuJIT), a value type's `Equals` can differ by **more than 95×** depending on whether `IEquatable<T>` is implemented. Boxing is not just a GC problem — it is a **CPU performance problem**.
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: Why "stack vs heap" keeps misfiring

Every C# textbook opens with this sentence:

> "Value types (structs) are stored on the stack; reference types (classes) are stored on the heap."

This is **not wrong**, but it conceals nearly every counter-example encountered in real code. When you declare an `int` as a field of a class, that `int` lives not on the stack but **inside the object on the heap**. When a lambda captures a local `struct` variable, that `struct` ends up **inside the heap-allocated closure**. When the JIT handles a `struct` entirely in registers, it is not "stored" on the stack or the heap at all.

This is why care is warranted every time a sentence about "stack vs heap" appears. **"What container is it inside?" is the real question.**

Two goals for this episode:

1. **Redefine value types and reference types by their copy rules, not their storage location**
2. **Identify precisely where boxing occurs**, why it is expensive, and how to avoid it

All measurements are taken on .NET 10 using BenchmarkDotNet. IL is quoted directly from what RyuJIT actually emits. Boxing pitfalls that game programmers encounter with IL2CPP are covered in the final section.

---

## Part 1. The Real Difference Between Value Types and Reference Types

### 1.1 "Copy Rules," Not "Stack/Heap"

The decisive difference between value types and reference types is not **what happens at allocation** but **what happens on assignment, passing, and comparison**.

- **Value type**: on assignment, **the entire contents are copied**. The new variable holds an independent copy.
- **Reference type**: on assignment, **only the pointer (reference) pointing to the object is copied**. Both the original and the copy see the same object.

<div class="vt-copy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Copy semantics comparison: value type vs reference type">
  <text x="380" y="26" text-anchor="middle" class="vt-copy-title">Value Type vs Reference Type — Copy Semantics</text>

  <g class="vt-copy-left">
    <text x="180" y="60" text-anchor="middle" class="vt-copy-subtitle">struct Position — value type</text>

    <rect x="40" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="105" text-anchor="middle" class="vt-copy-text-bold">a</text>
    <text x="100" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <rect x="200" y="80" width="120" height="70" rx="6" class="vt-copy-box-struct"/>
    <text x="260" y="105" text-anchor="middle" class="vt-copy-text-bold">b = a</text>
    <text x="260" y="125" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>
    <text x="260" y="143" text-anchor="middle" class="vt-copy-text-xs">(independent copy)</text>

    <text x="180" y="180" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒</text>
    <rect x="40" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct"/>
    <text x="100" y="215" text-anchor="middle" class="vt-copy-text-sm">a.X = 1 (unchanged)</text>
    <rect x="200" y="195" width="120" height="50" rx="6" class="vt-copy-box-struct-alt"/>
    <text x="260" y="215" text-anchor="middle" class="vt-copy-text-sm">b.X = 999</text>
  </g>

  <g class="vt-copy-right">
    <text x="580" y="60" text-anchor="middle" class="vt-copy-subtitle">class Player — reference type</text>

    <rect x="420" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="470" y="110" text-anchor="middle" class="vt-copy-text-bold">a = 0x00AF</text>

    <rect x="540" y="80" width="100" height="50" rx="6" class="vt-copy-box-ref"/>
    <text x="590" y="110" text-anchor="middle" class="vt-copy-text-bold">b = 0x00AF</text>

    <rect x="620" y="150" width="120" height="70" rx="6" class="vt-copy-box-heap"/>
    <text x="680" y="175" text-anchor="middle" class="vt-copy-text-bold">Heap 0x00AF</text>
    <text x="680" y="195" text-anchor="middle" class="vt-copy-text-sm">X=1, Y=2, Z=3</text>

    <line x1="520" y1="130" x2="620" y2="155" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>
    <line x1="640" y1="130" x2="670" y2="150" class="vt-copy-arrow" marker-end="url(#vt-copy-ah)"/>

    <text x="580" y="250" text-anchor="middle" class="vt-copy-text-bold">b.X = 999 ⇒ a.X is also 999</text>
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

"Where something is stored" is merely a **consequence** of these copy rules. Value types are placed primarily on the stack (or inlined) because copies must be cheap; reference types are placed on the heap with reference management because their lifetimes are unpredictable. **Memorizing the cause-effect relationship backwards leaves you defenseless when counter-examples appear.**

### 1.2 Equality Comparison Differs Too

Different copy rules mean different equality semantics.

- **Value type `Equals`**: the default implementation **compares fields one by one via reflection** (`ValueType.Equals(object)`). Double cost: boxing + reflection.
- **Reference type `Equals`**: the default implementation checks **reference identity** (`ReferenceEquals`) — it only asks whether both sides point to the same object.

This difference shows up as concrete numbers in the Part 5 benchmarks. When a value type is used as a `Dictionary` key or located via `List.Contains`, failing to implement `IEquatable<T>` directly means **paying both boxing and reflection on every comparison**.

### 1.3 The Mutability Pitfall

The most common bug arising from value type copy semantics is **attempting to modify a mutable `struct` after inserting it into a collection**.

```csharp
/* mutable struct pitfall */
struct Counter
{
    public int Value;
    public void Increment() => Value++;
}

var list = new List<Counter> { new Counter() };
list[0].Increment();        /* compile error: list[0] is a value (copy) and cannot be modified */

var copy = list[0];
copy.Increment();            /* only copy changes; the original inside the list is untouched */
```

This is why most C# style guides recommend keeping **`struct`s immutable (`readonly struct`)**. A mutable `struct` produces defects where the "value" nature of the type clashes with programmer intuition. This topic returns in episode 4 with `readonly struct` and `ref struct`.

---

## Part 2. Three Cases Where "Value Types Go on the Stack" Is Wrong

Slightly rewriting the textbook sentence:

> "A value type is stored **in the same place as the container that holds it**."

This single line is far more accurate. Only a `struct` declared as a local variable goes on the stack; everything else follows its container.

### 2.1 Value Type Inside a Class Field → Heap

```csharp
class Enemy
{
    public Vector3 Position;   /* value type, but lives on the heap */
    public int Hp;              /* also on the heap */
}

var e = new Enemy();            /* e allocates an Enemy object on the heap */
                                /* Position and Hp are stored inline within that object */
```

<div class="vt-inline-container">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Value types inside a class field live on the heap">
  <text x="360" y="26" text-anchor="middle" class="vt-inline-title">Memory Layout of class Enemy</text>

  <g>
    <rect x="40" y="70" width="160" height="50" rx="6" class="vt-inline-box-stack"/>
    <text x="120" y="95" text-anchor="middle" class="vt-inline-text-bold">Stack</text>
    <text x="120" y="112" text-anchor="middle" class="vt-inline-text-sm">e (reference, 8 bytes)</text>
  </g>

  <line x1="200" y1="95" x2="340" y2="140" class="vt-inline-arrow" marker-end="url(#vt-inline-ah)"/>

  <g>
    <rect x="340" y="70" width="340" height="200" rx="8" class="vt-inline-box-heap"/>
    <text x="510" y="98" text-anchor="middle" class="vt-inline-text-bold">Heap — Enemy object</text>

    <rect x="360" y="115" width="300" height="40" rx="4" class="vt-inline-box-header"/>
    <text x="510" y="140" text-anchor="middle" class="vt-inline-text-sm">ObjectHeader + MethodTable (16 bytes)</text>

    <rect x="360" y="160" width="300" height="50" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="180" text-anchor="middle" class="vt-inline-text-sm">Position (struct Vector3)</text>
    <text x="510" y="198" text-anchor="middle" class="vt-inline-text-xs">X, Y, Z — inline on heap</text>

    <rect x="360" y="215" width="300" height="45" rx="4" class="vt-inline-box-field"/>
    <text x="510" y="240" text-anchor="middle" class="vt-inline-text-sm">Hp — inline on heap</text>
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

`Position` is a **value type (`Vector3`)**, but because it is **inlined inside the reference type `Enemy`**, it lives on the heap. The "value types go on the stack" rule breaks here.

### 2.2 Array Elements → Heap

```csharp
var positions = new Vector3[1000];
positions[0] = new Vector3(1, 2, 3);    /* 1000 values are inlined inside the heap array */
```

Arrays are reference types (`T[]`). Therefore array elements are inlined within the array object on the heap. `Vector3[1000]` is **not a stack buffer — it is a contiguous 12 KB region on the heap**. This **contiguous heap layout** is precisely the foundation on which `Span<T>`, covered in episode 3, delivers its benefits.

### 2.3 Lambda Capture → Heap (Closure)

```csharp
void Setup()
{
    var count = new Counter();              /* local value type */
    Action handler = () => count.Value++;   /* count is captured */
                                             /* compiler generates a hidden class and stores count in it */
                                             /* result: count lives inside a heap-allocated closure object */
}
```

When a lambda captures a local variable, the compiler generates a **hidden class** (display class) with the captured variables as fields. That class is a reference type and is allocated on the heap, so the `struct` that would otherwise have lived on the stack moves to the heap alongside it.

Understanding all three cases makes it clear why "value types go on the stack" keeps misfiring. The **"same place as the container that holds it"** rule is far more consistent.

### 2.4 The JIT's Final Reversal — Escape Analysis and Stack Allocation

Everything above is a **source-level rule**. At runtime, the JIT can flip it once more.

.NET's RyuJIT uses **Escape Analysis** to determine whether an object escapes outside a method. If it does not escape, the heap allocation is elided and the object is **stack-allocated**. This optimization, introduced in earnest with .NET 9, was extended in .NET 10 to cover generic and virtual-call boundaries.

This means that even if source code says `new SomeClass()`, if that object is only used within the method and never leaks out, it **may actually be stack-allocated at runtime**. Conversely, the moment a value type is boxed, the boxed object must go on the heap — the reference escapes.

**Reading source code alone is therefore not sufficient to determine allocation location in modern .NET.** The only reliable tool is **measurement**. This is precisely why `[MemoryDiagnoser]` in BenchmarkDotNet is essential.

---

## Part 3. The Boxing Mechanism

Now consider what happens when the boundary between value types and reference types is **forcibly crossed**. That event is called **boxing**.

### 3.1 Definition of Boxing

Boxing is the operation of **wrapping a copy of a value type inside a new heap object**. The reverse is **unboxing** — extracting the value from a heap box back onto the stack (or into a register).

<div class="vt-box-container">
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Boxing sequence diagram">
  <text x="380" y="26" text-anchor="middle" class="vt-box-title">Boxing — How a Stack Value Is Copied into a Heap Object</text>

  <g>
    <text x="130" y="70" text-anchor="middle" class="vt-box-subtitle">① Value type on stack</text>
    <rect x="60" y="85" width="140" height="55" rx="6" class="vt-box-stack"/>
    <text x="130" y="108" text-anchor="middle" class="vt-box-text-bold">int i = 42</text>
    <text x="130" y="126" text-anchor="middle" class="vt-box-text-sm">stack, 4 bytes</text>
  </g>

  <g>
    <text x="380" y="70" text-anchor="middle" class="vt-box-subtitle">② object reference required</text>
    <rect x="290" y="85" width="180" height="55" rx="6" class="vt-box-stack"/>
    <text x="380" y="108" text-anchor="middle" class="vt-box-text-bold">object o = i;</text>
    <text x="380" y="126" text-anchor="middle" class="vt-box-text-xs">compiler inserts box instruction</text>
  </g>

  <g>
    <text x="630" y="70" text-anchor="middle" class="vt-box-subtitle">③ box created on heap</text>
    <rect x="540" y="85" width="180" height="55" rx="6" class="vt-box-heap"/>
    <text x="630" y="106" text-anchor="middle" class="vt-box-text-bold">Heap: Box&lt;int&gt; = 42</text>
    <text x="630" y="124" text-anchor="middle" class="vt-box-text-sm">header 16B + value 4B ≈ 24B</text>
  </g>

  <line x1="200" y1="110" x2="290" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>
  <line x1="470" y1="110" x2="540" y2="110" class="vt-box-arrow" marker-end="url(#vt-box-ah)"/>

  <g>
    <text x="380" y="190" text-anchor="middle" class="vt-box-subtitle">④ what if the original is mutated after boxing?</text>

    <rect x="60" y="210" width="180" height="60" rx="6" class="vt-box-stack"/>
    <text x="150" y="235" text-anchor="middle" class="vt-box-text-bold">i = 999 (stack)</text>
    <text x="150" y="255" text-anchor="middle" class="vt-box-text-xs">only the original changes</text>

    <rect x="520" y="210" width="200" height="60" rx="6" class="vt-box-heap"/>
    <text x="620" y="235" text-anchor="middle" class="vt-box-text-bold">Box&lt;int&gt; = 42 (heap)</text>
    <text x="620" y="255" text-anchor="middle" class="vt-box-text-xs">box unchanged (independent copy)</text>

    <line x1="240" y1="240" x2="520" y2="240" class="vt-box-arrow-dotted"/>
    <text x="380" y="235" text-anchor="middle" class="vt-box-text-xs">independent</text>
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

The key is step ④. **The boxed value is an independent copy of the original.** Mutating the original does not affect the box, and (where possible) mutating the box does not affect the original. This asymmetry is the source of the subtle bugs discussed in the next section.

### 3.2 Verifying at the IL Level

C#'s emitted IL makes boxing explicit through two instructions: **`box`** and **`unbox.any`**. Compiling the following two methods produces the IL shown below (.NET 10 Release build).

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

- **`box [T]`**: pops the value from the stack, allocates a box object for `T` on the heap, copies the value into it, then pushes the box reference onto the stack
- **`unbox.any [T]`**: extracts the `T` value from the heap box and pushes it onto the stack (throws `InvalidCastException` if the type does not match)

Saying "boxing happens when you cast to object" is correct, but knowing **which exact IL instruction does it** shifts the assessment from "this probably boxes" to "this definitively boxes."

### 3.3 Implicit Boxing — `Equals(object)`

Here is a less obvious example of boxing.

```csharp
public static bool CompareViaObject(int a, int b)
{
    object oa = a;
    object ob = b;
    return oa.Equals(ob);
}
```

The IL shows boxing occurring **twice**.

```text
CompareViaObject:
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32    /* box a onto the heap */
  IL_0006: ldarg.1
  IL_0007: box [System.Runtime]System.Int32    /* box b onto the heap */
  IL_000c: stloc.0
  IL_000d: ldloc.0
  IL_000e: callvirt instance bool [System.Runtime]System.Object::Equals(object)
  IL_0013: ret
```

Comparing two `int` values triggers **24 bytes × 2 = 48 bytes of heap allocation**. On top of that, `Equals(object)` internally invokes an unboxing + comparison routine, adding **CPU cost as well**. These costs reappear as concrete numbers in the Part 5 benchmarks.

### 3.4 The Boxed Copy Is Independent

The following confirms via IL that boxing produces an independent copy.

```csharp
public static object MutateAfterBox()
{
    var p = new Point2D(1, 2);
    object boxed = p;
    p.X = 999;
    return boxed;           /* is boxed.X 1 or 999? */
}
```

```text
IL_0000: ldloca.s 0                          /* &p (stack address) */
IL_0004: call Point2D::.ctor(int32, int32)   /* initialize p on the stack */
IL_0009: ldloc.0                             /* push value of p onto stack top */
IL_000a: box BoxingIL.Point2D                /* create an independent box copy on the heap */
IL_000f: ldloca.s 0                          /* &p (stack address again) */
IL_0011: stfld int32 Point2D::X              /* stack p.X = 999 */
IL_001b: ret                                 /* return the box (heap) */
```

The assignment `p.X = 999` touches only **`p` on the stack** (address retrieved via `ldloca.s 0`). The heap box is **completely independent** from the moment the `box` instruction executes, so `boxed.X` remains `1`.

This rule produces subtle bugs.

```csharp
/* anti-pattern */
var state = new GameState();
RegisterInterface((IStatefulObject)state);   /* boxing occurs (struct state → interface) */
state.Score = 100;                           /* only the stack-side state changes */
                                              /* the box passed to Register still has Score=0 */
```

Casting a struct to an interface triggers boxing, and at that moment the value's copy becomes independent — a **frozen copy**. The moment a `struct` is placed in an interface collection, mutations to the original are not reflected in the box. **This problem leads directly to the `readonly struct` and `ref struct` discussion in episode 4.**

---

## Part 4. Boxing Pitfalls in Everyday Code

Boxing hides in places **far more mundane** than an explicit `object` cast. Here are five common occurrences.

### 4.1 `Dictionary<TKey, TValue>` — When the Key Falls Through to `Equals(object)`

`Dictionary` handles key comparison via `EqualityComparer<TKey>.Default`. If `TKey` implements `IEquatable<TKey>`, `Equals(TKey)` is called directly — **no boxing**. If not, `ValueType.Equals(object)` is used — **boxing + reflection-based comparison**.

Composite keys built from multiple enums are a common pattern in leaderboard caches and similar structures. Keeping per-filter slices of the same cache naturally leads to a `struct` key with 3–4 enum fields.

```csharp
/* leaderboard cache key for Unity/client — 3-axis enum combination */
public enum Region : byte { NA, EU, APAC, SA }
public enum Season : byte { Spring, Summer, Autumn, Winter }
public enum Mode : byte { Solo, Duo, Squad }

/* ❌ No IEquatable — every lookup calls ValueType.Equals(object) → boxing + reflection */
public readonly struct LeaderboardKeyBad
{
    public readonly Region Region;
    public readonly Season Season;
    public readonly Mode Mode;
}

/* ✅ IEquatable + GetHashCode override — boxing eliminated entirely */
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

/* usage — lookup path is completely boxing-free */
Dictionary<LeaderboardKey, LeaderboardCache> _caches;
var key = new LeaderboardKey(Region.APAC, Season.Summer, Mode.Squad);
if (_caches.TryGetValue(key, out var cache)) { /* ... */ }
```

Implementing `IEquatable<T>` is the **default requirement** whenever a value type is used as a `Dictionary` key. Marking struct fields `readonly` also eliminates defensive copies (covered in detail in episode 4 on `readonly struct`). `GetHashCode` must be overridden consistently — given `HashCode.Combine`, there is no reason to hand-roll shifts and XOR.

### 4.2 `foreach` over Non-Generic `IEnumerable`

Iterating over pre-generic collections (`ArrayList`, `Hashtable`) with `foreach` treats every element as `object`, causing **boxing and unboxing on every iteration**.

```csharp
var list = new ArrayList { 1, 2, 3 };
foreach (int i in list)          /* unbox.any on every iteration */
    Console.WriteLine(i);
```

Switching to generic `List<int>` eliminates the unboxing and allows the JIT to inline an int-specific loop. There is no reason to use `ArrayList`, `Hashtable`, or non-generic `Queue` in modern code, but **when such collections arrive from the boundary of a legacy library, promoting them to generic equivalents all at once is the easiest available optimization**.

### 4.3 `string.Format` and String Interpolation

```csharp
Console.WriteLine(string.Format("Score: {0}, Time: {1}", score, time));
/* if score and time are value types, both are boxed (passed as object[]) */

Console.WriteLine($"Score: {score}, Time: {time}");
/* before C# 10: same as string.Format → boxing */
/* C# 10+: DefaultInterpolatedStringHandler uses generic Append<T> → no boxing */
```

The **interpolated string handler** (`DefaultInterpolatedStringHandler`) introduced in C# 10 (.NET 6) eliminates boxing entirely. This feature depends on the compiler version — setting the correct `LangVersion` is all that is needed to receive the benefit automatically in any project. However, **calling `string.Format` directly** still goes through the `object[]` path, keeping boxing alive.

### 4.4 Boxing Cascade in Logs and Traces

When a logging library accepts `params object[]`, every value type argument in a log call produces one box.

```csharp
logger.LogInformation("Player {PlayerId} scored {Score} at {Time}", playerId, score, time);
```

In the ASP.NET ecosystem, **Source Generator-based `LoggerMessage`** eliminates boxing.

```csharp
[LoggerMessage(Level = LogLevel.Information,
    Message = "Player {PlayerId} scored {Score} at {Time}")]
partial void LogPlayerScore(long playerId, int score, DateTime time);
```

**Unity is a different story.** `Debug.Log` / `Debug.LogFormat` go through a `string.Format`-like path internally, making them a source of boxing plus heap string allocation on every call.

```csharp
/* ❌ Unity — if damageAmount is float, it is boxed; string allocated every call */
Debug.LogFormat("Damage dealt: {0}", damageAmount);

/* ❌ Unity 2022 LTS and earlier — interpolated strings are rewritten to string.Format → same cost */
Debug.Log($"Damage dealt: {damageAmount}");

/* ✅ Unity 6 (C# 11 LangVersion) — routes through DefaultInterpolatedStringHandler, boxing eliminated */
Debug.Log($"Damage dealt: {damageAmount}");   /* different internal implementation */

/* ✅ safest — compiled out entirely in release builds */
[System.Diagnostics.Conditional("UNITY_EDITOR"), System.Diagnostics.Conditional("DEVELOPMENT_BUILD")]
static void DevLog(string msg) => UnityEngine.Debug.Log(msg);
```

When a game runtime emits thousands of log lines per second, this difference meaningfully reduces GC.Alloc visible in the Profiler. In release builds, using the `[Conditional]` attribute to **have the compiler remove the call site entirely** is the best approach.

### 4.5 `List<T>.Contains` — Default Comparer Path

`List<T>.Contains` uses `EqualityComparer<T>.Default` internally. If `T` is a value type that does not implement `IEquatable<T>`, it takes the **boxing path**. This is the same situation as the `Dictionary` key case.

More broadly, **every case where a value type is an element or key in a generic collection that requires comparison** falls into this category: `HashSet<T>`, `Dictionary<TKey,TValue>`, `SortedSet<T>`, `List<T>.Contains/IndexOf/Remove` — all of them.

### 4.6 Game Event Structs and `in` Parameters

In a real-time game, hundreds to thousands of events flow through an event bus (observer, message pipe, etc.) every second. Making these events classes generates GC.Alloc proportional to their frequency. Making them structs introduces copy cost that, as the field count grows, can exceed the boxing cost. The answer is `readonly struct` combined with `in` parameters.

```csharp
/* input event — 6 fields, potentially fired multiple times per frame */
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

/* ❌ by value — 6 fields (roughly 36 bytes) copied on every call */
public interface IDragSubscriber { void OnDrag(DragEvent evt); }

/* ✅ by in — passed as a read-only reference, no copy */
public interface IDragSubscriber { void OnDrag(in DragEvent evt); }
```

When only a signal with **no payload** is needed (state-change notifications, etc.), a zero-byte marker struct suffices. Type-based dispatch is achievable without class singletons or `static event`.

```csharp
/* zero-byte markers — dispatch by type in an event bus without boxing */
public readonly struct StaminaChangedSignal { }
public readonly struct MatchEndedSignal { }

/* markers with data stay as readonly struct */
public readonly struct ItemStockChanged
{
    public readonly int ItemId;
    public readonly int NewStock;
    public ItemStockChanged(int id, int stock) { ItemId = id; NewStock = stock; }
}

/* with a generic event bus such as MessagePipe, the boxing path never exists */
_bus.Publish(new StaminaChangedSignal());
_bus.Publish(new ItemStockChanged(itemId, stock));
```

The core strategy is not **"value type = fast"** but rather **"value type until the field count grows; then `in` for reference semantics"**. The interaction between `in` parameters and `readonly struct` appears again with benchmarks in episode 4.

---

## Part 5. Benchmarks — How Expensive Is Boxing in Practice?

From here the data is empirical. Three scenarios were measured using **.NET 10.0.100** and **BenchmarkDotNet 0.14.0** on **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD**. Each benchmark is written as an independent game-domain example (leaderboard cache key, list summation, 3D coordinate comparison). The original measurement results and source are available in the benchmark project in the same commit as this post.

### 5.1 `Dictionary` Lookup — `IEquatable<T>` vs Default Comparison

**Scenario**: a leaderboard cache using a `readonly struct` with `Region × Season × Mode` enum fields as the key. Cost of looking up all 48 keys.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **IEquatable implemented** | 208.2 ns | 1.00 | 0 B |
| **No IEquatable (ValueType.Equals)** | 988.8 ns | 4.79 | 3,456 B |

Without `IEquatable<T>`, `Dictionary` **boxes** the key and calls `ValueType.Equals(object)` via reflection. The result is **4.79× slower** and adds 3.4 KB of heap allocation per 48 lookups. The gap widens linearly as lookup frequency increases.

### 5.2 `List<int>` vs `ArrayList` — Iteration and Unboxing

**Scenario**: insert 10,000 integers into a collection and sum them with `foreach`.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`List<int>` foreach** | 3.604 μs | 1.00 | 0 B |
| **`ArrayList` foreach** | 13.320 μs | 3.70 | 48 B |
| **`ArrayList` for loop** | 10.943 μs | 3.04 | 0 B |

The boxing cost of `ArrayList` is **not limited to the values themselves**. `foreach` goes through `IEnumerator`, allocating an extra 48-byte enumerator box and performing a type check plus unboxing on every iteration. Switching to a `for` loop eliminates the enumerator boxing but leaves element unboxing in place, which is why it is still 3× slower. **Migrating to generic collections is the only correct direction away from `ArrayList`.**

### 5.3 Value Type `Equals` — The Effect of `IEquatable<T>`

**Scenario**: count elements equal to a target in an array of 1,000 `Point3` (X, Y, Z float) values. Three variants.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Default `ValueType.Equals(object)`** | 30,540 ns | 1.00 | 160,096 B |
| **`override Equals` (object arg)** | 2,883 ns | 0.09 | 32,000 B |
| **`IEquatable<T>` implementation** | 321.4 ns | **0.01** | 0 B |

The three tiers illustrate the essence of value type performance.

- **Default `ValueType.Equals(object)`**: reflection-based field comparison; the argument and the internal comparison routine are both boxed — 160 KB allocation for 1,000 comparisons
- **`override Equals(object)`**: reflection is gone, but the argument is still `object`, so **boxing remains** — 32 KB (32 B × 1,000), 10× faster
- **`IEquatable<T>.Equals(T)`**: boxing disappears entirely — **95× faster than the default**, 9× faster than the override. The JIT can also inline the comparison.

A ten-line `IEquatable<T>` implementation defines the performance ceiling for value types.

<div class="chart-wrapper">
  <div class="chart-title">Boxing Cost — 3 Scenarios: Relative Execution Time vs Optimal (1.0x), Log Scale</div>
  <canvas id="boxingBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'boxingBench',
  type: 'bar',
  data: {
    labels: ['Dictionary Lookup (IEquatable key)', 'List<int> vs ArrayList', 'struct Equals (3 variants)'],
    datasets: [
      {label:'Best',data:[1.00,1.00,1.00],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5},
      {label:'Medium',data:[null,3.04,8.97],backgroundColor:'rgba(255,152,0,0.75)',borderColor:'rgba(255,152,0,1)',borderWidth:1.5},
      {label:'Worst (Boxing path)',data:[4.79,3.70,95.02],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic',min:0.9,max:120,title:{display:true,text:'Multiple vs Baseline (log scale)'},grid:{color:'rgba(128,128,128,0.15)'},ticks:{callback:function(v){return v+'x';}}},
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

### 5.4 What These Numbers Say

Common patterns across all three benchmarks:

1. **Boxing is both a GC problem and a CPU problem.** Heap allocation increases, pointer dereferences multiply, and `callvirt` carries a type check — CPU cycles grow linearly.
2. **`IEquatable<T>` implementation is not "an optimization for later" — it is the default for value types.** Under ten lines of code produce order-of-magnitude performance differences.
3. **Before placing a value type in a collection**, ask once: "How does this collection compare, hash, and iterate over elements/keys?"

---

## Part 6. The Unity / IL2CPP Perspective

Value types and boxing operate under **different pressures in the Unity runtime (Mono / IL2CPP)** than in CoreCLR. The semantics are identical, but the way bottlenecks manifest differs.

### 6.1 Boxing Is Still `GC Alloc` in IL2CPP

IL2CPP translates IL to C++ and then compiles it to native code, but **the GC is still a conservative GC** (Boehm-based). Boxed objects are subject to heap allocation and appear as **`GC.Alloc` in the Unity Profiler**.

The problem is the mobile GC. Unity's default GC is **stop-the-world**: when a collection is triggered, the entire frame freezes. The typical cause of frame spikes on iOS and Android devices is **boxing that occurs every frame**.

### 6.2 Common Boxing Patterns in Unity Projects

The following are sources that frequently appear at the top of `Profiler → GC Alloc`, along with their fix patterns.

**① Missing `IEquatable<T>` on custom struct keys**

```csharp
/* ❌ Profiler detects: Hashtable.Equals → ValueType.Equals → boxing */
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

**② Value types as `UnityEvent<T>` arguments**

`UnityEvent<T>` internally mixes in an `object[]` path for Inspector bindings. Using value type arguments can cause boxing on every invocation.

```csharp
/* ❌ UnityEvent<int>.Invoke → boxing possible */
public UnityEvent<int> OnScoreChanged;
OnScoreChanged.Invoke(currentScore);

/* ✅ generic event bus (MessagePipe, UniRx Subject<T>, etc.) — no boxing */
readonly Subject<int> _scoreChanged = new();
_scoreChanged.OnNext(currentScore);
```

**③ `Debug.LogFormat` and high-frequency logging**

The concrete Unity version of the pattern covered in 4.4. In release builds, wrap calls with `[Conditional("UNITY_EDITOR")]` to compile them out entirely.

**④ `foreach` boxing in older Mono**

In Unity versions prior to 2020, certain paths caused `foreach` to box even when `List<T>.Enumerator` was a struct. This is mostly resolved in Mono from Unity 2022.3 LTS onward, but it can still occur with **third-party collections** distributed as DLLs outside of Unity. When suspected, using Deep Profile to inspect the `System.Collections.IEnumerator.MoveNext` call stack is the fastest diagnostic path.

**⑤ Casting `struct` to an interface**

The "frozen copy" pattern from section 3.4. In Unity code it is easy to leave implicit casts of value types to `IEnumerable`, `IComparable`, and similar interfaces, each of which produces a box and the accompanying independent-copy bug.

### 6.3 Hunting Boxing in the Profiler

A practical procedure for locating boxing in the Unity Profiler.

```csharp
/* ProfilerMarker to isolate a suspected scope — works in Editor and Development Build */
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

With this marker, the Profiler shows the **GC.Alloc byte count and call stack** for the marked scope. The following options significantly improve boxing-hunting efficiency.

- **Deep Profile + GC.Alloc filter** — traces the call stack directly responsible for boxing. Deep Profile has significant overhead, so **activate it only for the suspected scene or feature**
- **Allocation Callstacks** — records the full stack for every GC.Alloc with byte counts per method. Available since Unity 2020.2
- **Memory Profiler package** — snapshot diffs let you directly inspect the type of boxed objects (boxed `Int32`, `Vector3`, etc.) generated in a specific frame
- **IL2CPP build vs Mono build comparison** — the same boxing has different runtime costs per backend, so optimization verification must be measured on **the target deployment backend** to reflect actual impact

### 6.4 `readonly struct` and `in` Parameters — Preview of the Next Episode

In Unity code, when a large `struct` (e.g., an event data type with 6–10 fields) is passed to a handler every frame, **the copy cost exceeds the boxing cost**. This cost is eliminated with `in` parameters (.NET's **read-only by-reference passing**).

```csharp
/* by value — 6 fields copied on every call */
void OnDrag(DragEventData data) { ... }

/* by reference — no copy, read-only */
void OnDrag(in DragEventData data) { ... }
```

`in` is covered in depth alongside `readonly struct` and `ref struct` in episode 4. The goal of this episode ends at **recognizing boxing and verifying it at the IL level**.

---

## Summary

Four key takeaways from this episode:

1. **Remember "value type = follows its container," not "value type = stack."** Class fields, array elements, and lambda captures all place value types on the heap; the JIT's escape analysis can reverse the direction too.
2. **Boxing occurs explicitly via `box` / `unbox.any` IL instructions.** Judging based on **what is actually inserted in IL** is more reliable than vague source-level descriptions like "cast to object."
3. **A boxed value is an independent copy of the original.** Mutations to the original are not reflected in the box, so placing a `struct` in an interface collection creates a **frozen copy** — a source of subtle bugs.
4. **`IEquatable<T>` implementation is the default for value types, not an optional optimization.** It alone separates the performance of `Dictionary`, `HashSet`, and `List.Contains` by orders of magnitude.

---

## Series Connection: Preview of the Next Episodes

Two problems left open in this episode carry forward into the next:

- **Boxing avoided, but copy cost of the `struct` itself remains**: episode 3 on **`Span<T>` / `ReadOnlySpan<T>`** solves this with "views instead of copies"
- **Buffers that need long-term storage, asynchronous boundaries**: episode 4 on **`Memory<T>` + `ArrayPool<T>`** covers pooling and async compatibility
- **The paradigm that eliminates copy cost entirely**: episode 5 on **`readonly struct` / `ref struct` / `in` parameters**

This is the end of episode 1 of the C# Memory series.

---

## References

### Primary Sources — Official Documentation and Standards

- [ECMA-335 — Common Language Infrastructure (CLI) Partition III Section 4](https://ecma-international.org/publications-and-standards/standards/ecma-335/) — official definition of the `box` / `unbox.any` IL instructions
- [Microsoft Learn — box (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/user-defined-conversion-operators) — official explanation of value types and boxing
- [Microsoft Learn — IEquatable<T> Interface](https://learn.microsoft.com/en-us/dotnet/api/system.iequatable-1) — official `IEquatable<T>` reference
- [Microsoft Learn — EqualityComparer<T>.Default](https://learn.microsoft.com/en-us/dotnet/api/system.collections.generic.equalitycomparer-1.default) — the default comparer used by `Dictionary` / `HashSet`

### Blog Posts and In-Depth Analysis

- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) — Stephen Toub; includes escape analysis extension
- [.NET Blog — "Performance Improvements in .NET 9"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-9/) — initial stack allocation analysis
- [Microsoft Learn — "DefaultInterpolatedStringHandler"](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.defaultinterpolatedstringhandler) — C# 10 interpolated string handler

### Measurement Tools

- [BenchmarkDotNet official documentation](https://benchmarkdotnet.org/) — `[MemoryDiagnoser]`, `[SimpleJob]` usage
- [sharplab.io](https://sharplab.io/) — real-time C# → IL / JIT code conversion

### Game Runtime Perspective

- [Unity Manual — Understanding automatic memory management](https://docs.unity3d.com/Manual/performance-managed-memory.html) — how Unity's GC works
- [Unity Manual — Memory Profiler](https://docs.unity3d.com/Packages/com.unity.memoryprofiler@1.0/manual/) — tooling for tracking boxing
- [Unity Blog — "IL2CPP Internals"](https://unity.com/blog/engine-platform/an-introduction-to-ilcpp-internals) — boxing implementation in IL2CPP
