---
title: "Span<T> and ReadOnlySpan<T> — Viewing Memory Without Copying"
lang: en
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
  - "`Span<T>` is a **view** that points at an arbitrary region of memory. It treats array slices, substrings, and stack buffers with the same abstraction, letting you inspect a portion of data without copying it."
  - "The `ref struct` constraint is not a penalty — it is a contract. The single rule \"lives on the stack only\" blocks boxing, field storage, and async capture **at the compiler level**."
  - "`\"hello\".Substring(1, 3)` allocates a new 12-byte string; `\"hello\".AsSpan(1, 3)` allocates **0 bytes**. In parsing, logging, and validation code that frequently produces substrings, this drops GC pressure by an order of magnitude."
  - "On .NET 10 (Apple M4 Pro, Arm64 RyuJIT), replacing a `string.Substring` + `int.Parse` parser with a `Span<char>`-based one yields a **6× speedup** and zero allocations."
  - "The places `Span<T>` cannot go — fields, async methods, lambda captures — are handled by `Memory<T>` in the next episode. The two types are not rivals; they divide the work."
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Introduction: The Copy Cost Left Behind by the Boxing Episode

[Episode 1 (Value Types vs Reference Types and Boxing)](/posts/ValueTypeBoxing/) closed with one debt unpaid.

> "Boxing is avoided, but the **copy cost of the `struct` itself** remains."

One core rule from the Boxing episode is worth restating:

> Value types have **their entire contents copied when assigned, passed, or compared**.

Under normal circumstances this rule is intuitive and desirable. Passing a 6-byte `(short, int)` pair to a function incurs one copy — a cost that can safely be ignored. However, **when only a portion of data needs to be examined**, this copy rule creates a problem.

```csharp
string line = "ID=42,SCORE=1280,TIME=00:01:32";
string idPart = line.Substring(3, 2);    /* "42" — new string allocation */
int id = int.Parse(idPart);              /* parsed once more */
```

These two lines cause **two heap allocations**. `Substring` creates a new `string`, and once the result is no longer needed, it leaves GC overhead. Simple code that parses a single CSV line generates dozens of bytes of garbage on every call. In a game loop invoked every frame, that cost accumulates.

The root of the problem is that **a subset cannot be observed without copying**. The type that addresses this directly is the subject of this episode: `Span<T>` and `ReadOnlySpan<T>`.

Three goals for this episode:

1. Understand `Span<T>` through **a single definition** — "a pointer + length pinned as a ref struct"
2. See **why this type accepts the strong `ref struct` constraint**, and what problem that constraint solves
3. Verify with .NET 10 measurements how everyday substring/split/parse patterns can be **rewritten with zero allocations**

---

## Part 1. What `Span<T>` Actually Is

### 1.1 One-Line Definition — "A View of Memory"

`Span<T>` is summarized in one sentence:

> "A **pointer + length** that points at an arbitrary memory region, pinned into a type so it can be handled safely."

The internal representation is straightforward.

```csharp
public readonly ref struct Span<T>
{
    internal readonly ref T _reference;   /* managed reference to the starting position */
    internal readonly int _length;        /* length */
    /* ... */
}
```

`ref T _reference` is a form that could not be expressed directly before C# 11. It is not a plain reference to an object — it is a reference to **an arbitrary position inside an object**. The middle of an array, the fifth character of a string, the start of a stack buffer — it can point anywhere. Adding `_length` on top of that capability is enough to represent "a specific memory region."

This is precisely the shape of a tool for inspecting a subset without copying.

<div class="sp-anatomy-container">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Span internal structure — pointer + length pins a memory region">
  <text x="380" y="26" text-anchor="middle" class="sp-anatomy-title">Span&lt;T&gt; — A Memory Region Pinned as a ref struct</text>

  <g>
    <text x="160" y="60" text-anchor="middle" class="sp-anatomy-subtitle">Stack — Span&lt;char&gt; structure</text>
    <rect x="50" y="80" width="220" height="55" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="105" text-anchor="middle" class="sp-anatomy-text-bold">_reference</text>
    <text x="160" y="123" text-anchor="middle" class="sp-anatomy-text-sm">→ position inside array</text>

    <rect x="50" y="145" width="220" height="50" rx="6" class="sp-anatomy-box-stack"/>
    <text x="160" y="170" text-anchor="middle" class="sp-anatomy-text-bold">_length = 3</text>
    <text x="160" y="187" text-anchor="middle" class="sp-anatomy-text-sm">int</text>
  </g>

  <line x1="270" y1="107" x2="420" y2="155" class="sp-anatomy-arrow" marker-end="url(#sp-anatomy-ah)"/>

  <g>
    <text x="580" y="60" text-anchor="middle" class="sp-anatomy-subtitle">Heap — char[] = "hello"</text>
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
    <text x="565" y="205" text-anchor="middle" class="sp-anatomy-text-xs">⇧ Span covers indices 1–3 (3 elements) only</text>
  </g>

  <text x="380" y="250" text-anchor="middle" class="sp-anatomy-text-sm">"hello".AsSpan(1, 3) — exposes only 'e','l','l' without a new string</text>

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

The key differences are summarized in the table below.

| Axis | `string.Substring(1, 3)` | `string.AsSpan(1, 3)` |
|--------|---------------------------|------------------------|
| New object | 1 `string` (12B + 6B) | None |
| Data copied | 3 chars | 0 |
| GC pressure | Yes | None |
| Pass cost | 8B reference | `ref T` + `int` = 16B |
| Lifetime | Determined by GC | Tied to source memory |

The only cost of `Span<T>` is that **its lifetime is bound to the source memory**. Accepting that single-line constraint makes the allocation disappear.

### 1.2 `Span<T>` vs `ReadOnlySpan<T>`

The only difference, as the name implies, is **whether writes are permitted**.

- `Span<T>` — the indexer returns `ref T`. Elements inside the slice can be modified directly.
- `ReadOnlySpan<T>` — the indexer returns `ref readonly T`. A read-only view.

`AsSpan()` obtained from a `string` always returns `ReadOnlySpan<char>`. Since `string` is immutable in .NET, a mutable view cannot be provided. Conversely, `AsSpan()` from a `char[]` returns `Span<char>`.

From an API design perspective, the standard pattern is to **accept input parameters as `ReadOnlySpan<T>` and output buffers as `Span<T>`**.

```csharp
/* input is read-only — accepts string, char[], or stackalloc buffers without conversion */
static int CountVowels(ReadOnlySpan<char> input)
{
    int count = 0;
    foreach (var c in input)
        if ("aeiou".Contains(c)) count++;
    return count;
}

/* call sites — any memory source passes without conversion cost */
CountVowels("hello world");                /* string as-is */
CountVowels("hello world".AsSpan(0, 5));  /* part of a string */
CountVowels(new char[]{'h','i'});          /* char[] */
Span<char> tmp = stackalloc char[8];       /* stack buffer */
CountVowels(tmp);                          /* passed without conversion */
```

There is no need to write separate APIs for `string`, `char[]`, and stack buffers. A single `ReadOnlySpan<char>` **accepts all memory sources through one unified interface**.

### 1.3 Why `ref struct`

`Span<T>` is declared not as a plain `struct` but as a **`ref struct`**. That single word imposes strong constraints on the compiler.

| Prohibition | Reason |
|------|------|
| Storing as a class or struct field | Cannot guarantee safety of `ref T` if it escapes to the heap |
| Boxing (casting to `object`) | Boxing is a heap allocation — same reason |
| Implementing ordinary interfaces such as `IDisposable` | Interface casting involves boxing |
| Using as a local variable in an `async` method | The async state machine is a heap object — same reason |
| Lambda capture | Captured variables are converted to a closure (class) and go to the heap |
| Embedding inside `ValueTuple` | Ordinary structs also have boxing paths — blocked |

All of these prohibitions share a common thread: **paths that leak onto the heap**. The memory a `Span<T>` points to (especially a `stackalloc` stack buffer) disappears the moment the method returns. A `Span` that points at vanished memory and survives inside a heap object becomes a **dangling reference** — the same lifetime bug that causes late-night debugging sessions in C++.

`ref struct` blocks that possibility **at the compiler level**. It is statically prevented without any runtime check. This is a further elevation of the "value type safety" emphasized in the Boxing episode.

> "The constraints on Span are not a cost — they are a guarantee. Every piece of code the compiler accepts is memory-safe."

In exchange for that guarantee, `Span<T>` cannot be stored in fields, used in `async`, or captured in lambdas. `Memory<T>`, covered in the next episode, fills those gaps.

---

## Part 2. Three Sources of Span — Arrays, Strings, and stackalloc

The power of `Span<T>` lies in **treating three memory sources with the same abstraction**. Regardless of where the data came from, the view inside looks identical.

### 2.1 Source ① — Arrays

The most common source. `AsSpan()` on a `T[]` creates a view over the entire array or a portion of it.

```csharp
int[] scores = { 92, 88, 75, 60, 100 };

Span<int> all   = scores.AsSpan();          /* entire array */
Span<int> top3  = scores.AsSpan(0, 3);      /* first 3 elements */
Span<int> tail  = scores.AsSpan(2);         /* from index 2 to end */

/* slices of slices are free — no new object created */
Span<int> middle = top3.Slice(1, 1);        /* { 88 } */

middle[0] = 99;                              /* scores[1] also becomes 99 */
```

`AsSpan()` **does not copy data**. It simply opens a different window into the same array. That is why `middle[0] = 99` affects the original array.

`ArraySegment<T>` did something similar, but `Span<T>` returns `ref T` from its indexer, enabling **zero-copy transformation** beyond simple reads and writes.

### 2.2 Source ② — Strings and `ReadOnlySpan<char>`

Strings are where `Span<T>` does the most work. `string.AsSpan()` returns `ReadOnlySpan<char>`.

```csharp
string log = "[2026-04-30 09:00:00] INFO  Player joined: id=42";

ReadOnlySpan<char> bracket = log.AsSpan(1, 19);   /* "2026-04-30 09:00:00" */
ReadOnlySpan<char> level   = log.AsSpan(22, 4);   /* "INFO" */
ReadOnlySpan<char> id      = log.AsSpan(45, 2);   /* "42" */

int playerId = int.Parse(id);   /* .NET Core 2.1+: ReadOnlySpan<char> overload exists */
```

Three `Substring` calls would produce **three new strings plus an equivalent GC burden**. Three `AsSpan` calls produce **zero allocations**. The two snippets have the same meaning, but their GC cost is in a different category entirely.

The immutability of `string` provides an additional benefit. Since the source never changes, the memory that `ReadOnlySpan<char>` points at never changes either — race conditions are not a concern.

### 2.3 Source ③ — stackalloc

The most attractive source. A temporary buffer can be created **without touching the heap at all**.

```csharp
static long Sum(ReadOnlySpan<int> xs)
{
    long s = 0;
    foreach (var x in xs) s += x;
    return s;
}

void DoWork()
{
    Span<int> buffer = stackalloc int[64];   /* 256 bytes reserved on the stack */
    for (int i = 0; i < 64; i++) buffer[i] = i * i;

    long total = Sum(buffer);                /* 0 alloc */
}
```

`stackalloc` does the same thing as C's `alloca`. It claims an on-the-spot buffer inside the method's stack frame, and that buffer disappears when the method returns. In earlier C#, `stackalloc` was a dangerous tool available only in `unsafe` contexts, but **since C# 7.2, combining it with `Span<T>`** made it a safe, first-class feature.

Two things are worth remembering.

**① Stack size limit** — The OS thread stack limit is typically around 1 MB. The main thread in a game client may be larger, but **stackalloc above a few KB is risky**. The recommendation is 1 KB or less; 256–512 bytes is the safe range.

```csharp
const int StackThreshold = 256;
Span<byte> buffer = size <= StackThreshold
    ? stackalloc byte[size]
    : new byte[size];
```

**② Zero-init cost** — Before .NET 6, memory claimed by `stackalloc` was entirely zeroed. For small buffers this can be ignored, but **above a few hundred bytes** the cost is measurable.

`[SkipLocalsInit]` can disable this zero-init in .NET 6+.

```csharp
using System.Runtime.CompilerServices;

[SkipLocalsInit]
static int FastParse(ReadOnlySpan<char> s)
{
    Span<char> tmp = stackalloc char[64];   /* zero-init skipped */
    /* tmp's initial content is garbage — every location must be written before use */
    s.CopyTo(tmp);
    /* ... */
}
```

`[SkipLocalsInit]` can only be used **when there is a guarantee that every location is written before it is read**. Otherwise, the contents of the previous stack frame are exposed — a security vulnerability.

### 2.4 A Single Function Accepts All Three Sources

Having a single function accept all three sources is the essence of the `Span<T>` design.

```csharp
/* single API that does not care about the source */
static double Average(ReadOnlySpan<double> values)
{
    double sum = 0;
    foreach (var v in values) sum += v;
    return values.Length == 0 ? 0 : sum / values.Length;
}

/* call sites — all three sources treated identically */
double[] heap = { 1.0, 2.0, 3.0 };
Average(heap);                                  /* array */

Span<double> stack = stackalloc double[3] { 1.0, 2.0, 3.0 };
Average(stack);                                 /* stack */

ReadOnlySpan<double> slice = heap.AsSpan(1, 2);
Average(slice);                                 /* slice of array */
```

`IEnumerable<T>` previously handled this unification, but at the cost of **interface dispatch plus an enumerator object**. `Span<T>` achieves the same unification with **zero allocations and direct indexing**.

---

## Part 3. The Deep Reason Behind `ref struct` Constraints

The following compile errors are what everyone encounters when first using `Span<T>`. Understanding why they exist once eliminates any confusion forever.

### 3.1 Why It Cannot Be a Class Field

```csharp
class Cache
{
    Span<byte> _buffer;   /* CS8345: ref struct fields are only allowed in ref structs */
}
```

What would happen if this were allowed?

```csharp
void Setup(byte[] data)
{
    var cache = new Cache();
    cache._buffer = data.AsSpan();
    /* looks fine up to here */
}

void Setup2()
{
    var cache = new Cache();
    Span<byte> tmp = stackalloc byte[256];
    cache._buffer = tmp;     /* tmp disappears when this method returns */
    /* if cache is still alive, _buffer is a dangling reference */
}
```

`stackalloc` memory disappears when the method exits. A `Span` pointing at that memory and surviving inside a class (on the heap) leads directly to **use-after-free**. C# blocks this possibility at compile time.

Fields of a `ref struct` can only be stored in another `ref struct`. Doing so means the container inherits the same constraints, and ultimately every path leads only to the stack.

### 3.2 Why It Cannot Enter `async` Methods or Lambdas

```csharp
async Task BadAsync(byte[] data)
{
    Span<byte> view = data.AsSpan();   /* CS4012: ref struct cannot be used in async methods */
    await Task.Yield();
    Console.WriteLine(view.Length);
}
```

An `async` method is transformed by the compiler into a **state machine class (or struct)**. Every local variable that must survive across an `await` becomes a **field** of that state machine. Since `Span<T>` cannot be a class field, it cannot survive past an `await`.

Lambdas fail for the same reason. Captured variables become fields of a **display class** generated by the compiler, and that class lives on the heap.

```csharp
void BadLambda()
{
    Span<int> nums = stackalloc int[4] { 1, 2, 3, 4 };
    Func<int> first = () => nums[0];   /* CS8175: cannot capture ref struct in a lambda */
}
```

Two solutions exist.

**(a) Extract into a synchronous helper** — process the data before the `await`.

```csharp
async Task GoodAsync(byte[] data)
{
    int sum = SyncSum(data.AsSpan());     /* Span lives only here */
    await SaveAsync(sum);
}

static int SyncSum(ReadOnlySpan<byte> view) { /* ... */ }
```

**(b) Use `Memory<T>`** — when crossing an asynchronous boundary is necessary, switch to `Memory<T>` from the next episode. `Memory<T>` is a plain `struct` and can freely appear in async methods, lambdas, and fields.

### 3.3 Interface Casting and Boxing Are Prohibited

```csharp
ReadOnlySpan<int> view = ...;
IEnumerable<int> seq = view;   /* CS0030: ref struct cannot be converted to an interface */
object o = view;               /* CS0029: boxing is prohibited */
```

This is the same situation seen in the Boxing episode. Interface casting and `object` casting involve boxing, and boxing is a heap allocation. Every path that would take `Span<T>` to the heap is blocked.

This is also why LINQ cannot be used with `Span<T>`. LINQ is based on `IEnumerable<T>`, and `Span<T>` cannot implement interfaces. The alternatives are **Span-specific methods** — `Sum`, `Contains`, `IndexOf`, and other extension methods accumulated in `MemoryExtensions` — or **manual `for`/`foreach` loops**.

### 3.4 The Workaround — `scoped` and Ref Safety Rules

The `scoped` keyword added in C# 11 allows lifetime rules for `ref struct` parameters to be expressed more precisely.

```csharp
/* guarantees that parameter view does not escape outside the method */
static int Sum(scoped ReadOnlySpan<int> view)
{
    int s = 0;
    foreach (var v in view) s += v;
    return s;   /* only int is returned — the Span itself does not escape */
}
```

A `ref struct` parameter marked `scoped` is strictly prevented from **intruding on the caller's lifetime**. When writing a library, this device lets callers pass a Span from a wider variety of sources (including `stackalloc`) with more freedom.

These rules do not need to be memorized in full. **When a compile error occurs, asking "where is this Span leaking to?" is all it takes.**

---

## Part 4. Span in Everyday Code

Theory comes first, then practice. Here is where and how to rewrite common daily code patterns.

### 4.1 `Substring` → `AsSpan().Slice()`

The most commonly encountered transformation.

```csharp
/* allocation on every call */
string GetExtension(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? "" : path.Substring(dot);
}

/* zero alloc — when the caller can accept ReadOnlySpan<char> */
ReadOnlySpan<char> GetExtensionSpan(string path)
{
    int dot = path.LastIndexOf('.');
    return dot < 0 ? ReadOnlySpan<char>.Empty : path.AsSpan(dot);
}
```

If the caller needs to **store the result long-term**, returning a Span is not appropriate. In that case, return a plain `string` (the original string is a GC candidate anyway) or switch to `Memory<T>`. Span is the right choice only for **substrings that are used immediately and discarded**.

### 4.2 `int.Parse` Evolution — string Argument → `ReadOnlySpan<char>` Argument

Since .NET Core 2.1, numeric parsing APIs accept `ReadOnlySpan<char>` overloads.

```csharp
string raw = "X=42,Y=88,Z=12";

/* Substring → Parse — three string allocations */
int x = int.Parse(raw.Substring(2, 2));
int y = int.Parse(raw.Substring(7, 2));
int z = int.Parse(raw.Substring(12, 2));

/* AsSpan → Parse(ReadOnlySpan<char>) — 0 alloc */
int x2 = int.Parse(raw.AsSpan(2, 2));
int y2 = int.Parse(raw.AsSpan(7, 2));
int z2 = int.Parse(raw.AsSpan(12, 2));
```

The same pattern applies consistently to `double.Parse`, `DateTime.Parse`, and `Guid.TryParse`. Every major parsing API in the standard BCL already has Span overloads.

### 4.3 `string.Split` → `MemoryExtensions.Split` (or `SpanSplitEnumerator`)

`string.Split` returns `string[]`, so it allocates **as many substrings as there are tokens plus the array itself**. Splitting a CSV line is one of the most expensive operations.

```csharp
/* 8 tokens → 9 objects (1 array + 8 strings) */
string line = "id,name,score,time,region,mode,season,build";
string[] tokens = line.Split(',');

/* .NET 8+ — 0 alloc parser */
ReadOnlySpan<char> view = line.AsSpan();
foreach (Range r in view.Split(','))
{
    ReadOnlySpan<char> token = view[r];   /* no new string */
    /* process token */
}
```

`MemoryExtensions.Split(ReadOnlySpan<T>, T)` added in .NET 8 returns a sequence of `Range` values. The caller retrieves each token by indexing the original Span. The result is a **0-alloc split**.

For .NET 7 and earlier, a short helper that manually iterates with `IndexOf` is sufficient.

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
/* WARNING: the code above does not work — ReadOnlySpan<char> as a parameter clashes with yield return */
/* Span cannot be a parameter in an iterator method — see the note below */
```

Here the `ref struct` constraint appears again. `yield return` is a place where the compiler generates a state machine — `Span<T>` cannot be inside one. In practice, either write a `ref struct` enumerator directly (e.g., `SpanSplitEnumerator`) or fill an index array in advance and let the caller iterate.

### 4.4 Encoding, Hashing, and Serialization

**Low-level conversion APIs** in the standard library have been almost entirely updated to accept Span.

```csharp
/* UTF-8 encoding */
ReadOnlySpan<char> text = "안녕하세요".AsSpan();
Span<byte> buffer = stackalloc byte[64];
int written = Encoding.UTF8.GetBytes(text, buffer);
/* buffer.Slice(0, written) holds the encoded UTF-8 bytes */

/* SHA256 */
ReadOnlySpan<byte> data = ...;
Span<byte> hash = stackalloc byte[32];
SHA256.HashData(data, hash);

/* JSON Reader */
ReadOnlySpan<byte> json = ...;
Utf8JsonReader reader = new(json);
```

The **`stackalloc` + Span I/O combination** is the standard form of a zero-alloc serialization/hashing pipeline.

### 4.5 `ArrayPool<T>` Preview

The practical limit for `stackalloc` is around 1 KB. When a larger temporary buffer is needed — without triggering GC with `new byte[]` every time — **`ArrayPool<T>`** enters the picture.

```csharp
byte[] rented = ArrayPool<byte>.Shared.Rent(8192);
try
{
    Span<byte> view = rented.AsSpan(0, 8192);
    /* use view */
}
finally
{
    ArrayPool<byte>.Shared.Return(rented);
}
```

An array rented from `ArrayPool` is used through a `Span<T>` view and returned to the pool when done. This pattern is the **standard buffering approach in ASP.NET Core**. It is covered in depth in the next episode (`Memory<T>` + `ArrayPool<T>`).

---

## Part 5. Benchmarks — Substring-Based vs Span-Based

From here the data is empirical. **.NET 10.0.100** + **BenchmarkDotNet 0.14.0**, the same environment as the Boxing episode — **Apple M4 Pro, macOS 26.1, Arm64 RyuJIT AdvSIMD**. The measurement code uses game-domain examples (log parsing, partial extraction, temporary buffer comparison).

### 5.1 Log Parsing — `Substring` + `int.Parse` vs Span-Based

**Scenario**: extract PlayerId, Score, and Region from 1,000 log lines of the form `"[2026-04-30 09:00:00] PlayerId=42,Score=1280,Region=3"`.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + int.Parse(string)** | 142.6 μs | 1.00 | 144,000 B |
| **AsSpan + int.Parse(ReadOnlySpan&lt;char&gt;)** | 22.3 μs | **0.16** | 0 B |

Code with identical meaning runs **6.4× faster** and GC allocation **disappears entirely**. Parsing 1,000 lines drops from roughly 144 KB of allocation to 0 B — in code called every frame, that eliminates 4 MB of garbage in 30 frames.

### 5.2 Substring + Immediate Comparison — Equals vs SequenceEqual

**Scenario**: check whether the extension is `".png"` for 10,000 file paths.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **Substring + string.Equals** | 187.4 μs | 1.00 | 320,000 B |
| **EndsWith(string)** | 39.6 μs | 0.21 | 0 B |
| **AsSpan().EndsWith(span)** | 28.8 μs | **0.15** | 0 B |

`EndsWith` alone avoids creating a substring, but **when the call site already holds a `ReadOnlySpan`**, the Span version is additionally faster. The gap looks small, but it accumulates with call frequency.

### 5.3 Temporary Buffers — new vs ArrayPool vs stackalloc

**Scenario**: create a 256-byte temporary buffer inside a function, fill it, and sum it. 10,000 iterations.

| Method | Mean | Ratio | Allocated |
|--------|-----:|------:|----------:|
| **`new byte[256]`** | 6.42 ms | 1.00 | 2,640,000 B |
| **`ArrayPool.Rent(256)`** | 4.18 ms | 0.65 | 0 B |
| **`stackalloc byte[256]`** | 1.97 ms | **0.31** | 0 B |
| **`stackalloc` + `[SkipLocalsInit]`** | 1.42 ms | **0.22** | 0 B |

`stackalloc` not only avoids the GC — its **memory access pattern** is cache-friendly, making it faster. Disabling zero-init with `[SkipLocalsInit]` adds further acceleration.

Above 256 bytes, however, the risk rises. When 8 KB is needed temporarily, `ArrayPool` is the answer.

<div class="chart-wrapper">
  <div class="chart-title">Span-Based Transformations — Relative Execution Time vs Optimal (1.0x), Log Scale</div>
  <canvas id="spanBench" class="chart-canvas" height="300"></canvas>
</div>
<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'spanBench',
  type: 'bar',
  data: {
    labels: ['Log Parsing (1,000 lines)', 'EndsWith (10,000 paths)', 'Temp Buffer (10,000 runs)'],
    datasets: [
      {label:'Span / stackalloc', data:[0.16,0.15,0.22], backgroundColor:'rgba(76,175,80,0.75)', borderColor:'rgba(76,175,80,1)', borderWidth:1.5},
      {label:'Middle path', data:[null,0.21,0.65], backgroundColor:'rgba(255,152,0,0.75)', borderColor:'rgba(255,152,0,1)', borderWidth:1.5},
      {label:'Baseline (Substring / new)', data:[1.00,1.00,1.00], backgroundColor:'rgba(244,67,54,0.75)', borderColor:'rgba(244,67,54,1)', borderWidth:1.5}
    ]
  },
  options: {
    indexAxis: 'x',
    scales: {
      y: {type:'logarithmic', min:0.05, max:1.5, title:{display:true,text:'Multiple vs Baseline (log scale)'}, grid:{color:'rgba(128,128,128,0.15)'}, ticks:{callback:function(v){return v+'x';}}},
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

### 5.4 What These Numbers Say

Common patterns across all three benchmarks:

1. **One substring = one new string allocation.** If that substring is discarded immediately, the allocation is 100% waste. Receiving it as a Span eliminates that waste entirely.
2. **Span-based code is faster not only because it skips allocation, but because it skips data copying.** 1,000 substrings of 256 bytes each is 256 KB of additional memory writes — measurable as cache pressure as well.
3. **`stackalloc` is the answer for small, short-lived buffers.** Under 256 B, used entirely within the method — when both conditions hold, it is always the fastest option.

---

## Part 6. Unity / IL2CPP Perspective

`Span<T>` works in the Unity runtime, but it faces different pressures and limitations than CoreCLR.

### 6.1 Supported Versions and Backends

`Span<T>` entered the BCL with .NET Core 2.1 / .NET Standard 2.1. In Unity terms:

- **Before Unity 2021.2** — usable by adding the `System.Memory` NuGet package separately. Some Mono backend optimizations are absent.
- **Unity 2021.2 – 2022.2** — uses the standard BCL directly when the `.NET Standard 2.1` compatibility profile is enabled.
- **Unity 2022.3 LTS and later** — enabled by default. **`AsSpan`, `MemoryExtensions`, and `stackalloc` + Span all work as expected.**

`Span<T>` works correctly in IL2CPP builds as well. IL2CPP preserves the same semantics in C++-translated code by honoring the `ref struct` safety rules.

### 6.2 The Relationship Between `NativeArray<T>` and `Span<T>`

Unity's native collection `NativeArray<T>` manages memory **outside the GC**. It belongs to a different world from the managed C# memory series, but it has a bridge: `AsSpan()`.

```csharp
NativeArray<float> velocities = new(1024, Allocator.TempJob);

/* borrow a view over NativeArray as a Span */
Span<float> view = velocities.AsSpan();

/* standard Span API works as-is */
view.Fill(0f);
view.Slice(0, 256).CopyTo(view.Slice(256));
```

`NativeArray<T>.AsSpan()` is available from Unity 2021.2+. **No allocation occurs** — it simply creates a Span over the unmanaged memory that `NativeArray` points to.

This means the same function can accept `T[]`, `NativeArray<T>`, and `stackalloc` buffers.

```csharp
static float Average(ReadOnlySpan<float> values) { /* ... */ }

/* all three called identically */
float[] heap = new float[1024];
Average(heap);

NativeArray<float> native = new(1024, Allocator.Temp);
Average(native.AsSpan());

Span<float> stack = stackalloc float[256];
Average(stack);
```

### 6.3 Burst and Span — Compatibility and Limits

The Burst compiler recognizes both `NativeArray<T>` and `Span<T>` and treats them as targets for SIMD optimization. A few things to keep in mind:

- **Spans of managed arrays cannot be used inside Burst Jobs.** Burst does not handle GC objects.
- `NativeArray<T>.AsSpan()` is fine.
- `stackalloc` works inside Burst as well — stack memory is unmanaged internally.

The most common form that gets **0-alloc + Burst SIMD acceleration simultaneously** in Job code is the combination of `NativeArray + AsSpan + stackalloc temporary buffer`.

### 6.4 `ref struct` Tracking in IL2CPP

IL2CPP translates IL to C++ while preserving `ref struct` lifetime rules. Code that the C# compiler accepts will also be accepted by IL2CPP — no additional validation is needed.

One thing to be aware of is **how the `_reference` field of `Span` is represented in IL2CPP**. A Span pointing at a managed array is represented in IL2CPP as a **GC handle + offset**, adding slight overhead on every indexing operation. In general, however, this is faster than the Mono backend.

From a benchmarking perspective, **the same measurement must be run in Editor, Mono, and IL2CPP** to understand the true cost. As with the Boxing episode — **always measure on the target deployment backend**.

### 6.5 Common Usage Patterns in Unity

**① String processing every frame**

```csharp
/* new string on every frame for TextMeshPro labels */
void Update()
{
    label.text = "HP: " + currentHp + " / " + maxHp;
    /* string.Concat → new string + potentially two boxed ints */
}

/* Span-based formatting (.NET 6+ string interpolation uses Span internally) */
void Update()
{
    label.text = $"HP: {currentHp} / {maxHp}";
    /* C# 10+ DefaultInterpolatedStringHandler uses a Span pool */
}
```

C# 10+ interpolated strings use `DefaultInterpolatedStringHandler` internally, which uses a **Span-based temporary buffer**. Boxing disappears and allocations reduce to one — the same as seen in section 4.4 of the Boxing episode.

**② Network packet decoding**

```csharp
/* packet received — 4-byte length header + payload */
ReadOnlySpan<byte> packet = recvBuffer.AsSpan(0, recvLen);
int payloadLen = BinaryPrimitives.ReadInt32LittleEndian(packet[..4]);
ReadOnlySpan<byte> payload = packet.Slice(4, payloadLen);
/* process payload — 0 alloc */
```

Renting `recvBuffer` from a pool (`ArrayPool<byte>.Shared.Rent(...)`) and slicing over it with Span is the standard approach in game networking.

**③ Casting a large struct via Span (`MemoryMarshal`)**

```csharp
/* low-level memory reinterpretation — viewing the same memory as a different type */
Span<Vector3> verts = ...;
Span<float> floats = MemoryMarshal.Cast<Vector3, float>(verts);
/* 1024 Vector3s → 3072 floats — same data, only the view changes */
```

`MemoryMarshal` is the class that collects **reinterpretation** APIs for Span. It is very useful when passing data to a shader, or when viewing bytes as another type during serialization.

---

## Summary

Four key takeaways from this episode:

1. **`Span<T>` is a view that inspects an arbitrary memory region without copying data.** Arrays, strings, and `stackalloc` are all treated through the same abstraction, and the BCL APIs that operate on top of it — `int.Parse`, `Encoding.UTF8.GetBytes`, `MemoryExtensions.Split`, `MemoryMarshal.Cast` — become the building blocks of zero-alloc code.
2. **The `ref struct` constraint is a safety guarantee, not a cost.** The prohibitions on fields, async, and lambda captures all exist to block every path by which a Span could outlive the memory it points to. Being caught at the compiler level is always better than a runtime bug.
3. **The substring + parse pattern is the most common zero-alloc refactoring candidate in game code.** On .NET 10 Arm64, the same-meaning parser ran 6× faster and GC allocation disappeared entirely. Code called every frame is the first place to inspect.
4. **`stackalloc` is the answer for small, short-lived temporary buffers.** Under 256 B, finished within the method — when both conditions hold, it outperforms even `ArrayPool`. Above that threshold belongs to the `ArrayPool` territory covered in the next episode.

---

## Series Connection: Preview of the Next Episode

Two problems left open in this episode carry forward.

- **`Span<T>` cannot enter `async` methods, fields, or lambdas**: episode 3 on **`Memory<T>` + `ArrayPool<T>`** fills those gaps. Pooled buffers can be carried safely across asynchronous boundaries.
- **Large temporary buffers cannot be claimed with `stackalloc`**: the same episode 3 covers the `ArrayPool<T>.Shared.Rent`/`Return` pattern.
- **The copy cost of the `struct` itself — `in`, `readonly struct`, `ref struct`**: episode 4 addresses that.

This is the end of episode 2 of the C# Memory series.

---

## References

### Primary Sources — Official Documentation and Standards

- [Microsoft Learn — `Span<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.span-1) — official reference
- [Microsoft Learn — `ReadOnlySpan<T>` Struct](https://learn.microsoft.com/en-us/dotnet/api/system.readonlyspan-1) — official reference
- [Microsoft Learn — `MemoryExtensions` Class](https://learn.microsoft.com/en-us/dotnet/api/system.memoryextensions) — Span-specific extension methods
- [Microsoft Learn — `MemoryMarshal` Class](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.memorymarshal) — Span reinterpretation API
- [Microsoft Learn — `stackalloc` (C# reference)](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/stackalloc) — official `stackalloc` documentation
- [Microsoft Learn — `[SkipLocalsInit]` Attribute](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.skiplocalsinitattribute) — disabling zero-init
- [Microsoft Learn — `scoped` modifier](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/ref) — ref safety rules

### Blog Posts and In-Depth Analysis

- [.NET Blog — "All About Span: Exploring a New .NET Mainstay"](https://learn.microsoft.com/en-us/archive/msdn-magazine/2018/january/csharp-all-about-span-exploring-a-new-net-mainstay) — Stephen Toub, background on Span's introduction
- [.NET Blog — "Performance Improvements in .NET 10"](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/) — Stephen Toub, Span-related optimization items
- [Adam Sitnik — "Span"](https://adamsitnik.com/Span/) — analysis of Span internals and lifetime rules

### Measurement Tools

- [BenchmarkDotNet official documentation](https://benchmarkdotnet.org/) — `[MemoryDiagnoser]`, `[SimpleJob]` usage
- [sharplab.io](https://sharplab.io/) — real-time C# → IL / JIT code conversion

### Game Runtime Perspective

- [Unity Manual — `NativeArray<T>`](https://docs.unity3d.com/ScriptReference/Unity.Collections.NativeArray_1.html) — official NativeArray reference
- [Unity Blog — "On DOTS: C# & the Burst Compiler"](https://unity.com/blog/engine-platform/on-dots-c-burst) — Burst and Span compatibility
- [Unity Manual — IL2CPP overview](https://docs.unity3d.com/Manual/IL2CPP.html) — how IL2CPP works
