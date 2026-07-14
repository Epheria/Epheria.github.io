---
title: "How C# Runs — and How It Reads Itself"
lang: en
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
  - C# code does not become machine code in one step. It first becomes **IL (Intermediate Language)**, then splits into three paths — JIT, NativeAOT, and IL2CPP — depending on **when that IL is translated** (JIT at runtime / AOT at build time)
  - IL is a register-free **stack machine**. Costs that source hides — boxing, virtual dispatch, string concatenation — show up as instructions, and `if` / `for` flatten into conditional branches
  - To read code as meaning rather than text, you need the compiler's stages (**lexing → syntax tree → semantic model → symbols**). grep sees only raw text that has not even been tokenized. The library that exposes this work is **Roslyn**
  - The decisive tension is a single question. **"Can new code be created at runtime?"** JIT can; AOT cannot. That is why reflection's dynamic features and Roslyn collide with AOT, and why **Source Generators** (compile-time metaprogramming) step around that collision
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## Where This Post Started

At some point I decided to build a **small tool that analyzes C# code** in a Unity project — something that could follow "which implementation does this presenter's method actually call?" Before writing any code, I hit two questions.

1. **How do I build and ship the tool itself?** — In what form should I distribute this C# executable so it is fast and light?
2. **How does the tool *read* C# code?** — Text search alone would not be enough; then what?

Both questions looked like "tool design" on the surface, but finding answers meant going all the way down to **"how does C# code actually run, and how does it understand itself?"** This post is a record of that loop. The tool is only the **occasion that raised the questions**; the center of gravity is the **mechanics** of the technologies I met along the way — IL, JIT, AOT, reflection, Roslyn.

- **Part 1** starts from the first question: what happens between a line of C# and the CPU.
- **Part 2** is the second question: what it means to read code as *meaning*, not text.
- **Part 3** is where the two questions collide. That collision explains the tool's design — and, more broadly, the direction of modern .NET.

> The [Foundation series](/posts/DotnetEcosystemMap/) drew a **map** of the .NET stack (the layered structure of language · IL · runtime). This post opens those map cells and goes into the **actual mechanisms**. Overlaps with the map are kept short; then we dig below them.

---

# Part 1. Until Code Becomes Machine Code

## It Does Not Become Machine Code in One Step

In C, the compiler translates source straight into native code. A `.c` file becomes a Windows x64 `.exe` or a Linux ARM64 binary. Once compiled, the result is bound to a **specific OS + specific CPU combination**.

C# split that structure once. C# source goes through the Roslyn compiler and is translated only into an intermediate bytecode called **IL (Intermediate Language)**. IL is independent of hardware and OS, and lives inside a `.dll` or `.exe`. The real native translation happens **separately, after it is known which machine the code will run on**.

The **timing** of that separate translation is the core of Part 1. There are two timings.

- **JIT (Just-In-Time)** — translate IL to machine code **on that machine, at that moment**, while the program runs
- **AOT (Ahead-Of-Time)** — translate to native code **in advance, before** the app is shipped

Same IL, different translation timing — that single fork divides the three runtimes covered later, and even decides how I ship my tool. To understand that fork properly, you first have to look directly at **what the translation target — IL — looks like**.

## IL Is a Stack Machine

At first glance IL looks like assembly, but there is one decisive difference. **There are no registers.**

Real CPUs such as x86 and ARM are **register machines**. An instruction like `add rax, rbx` says "add this register's value to that register's value and put the result here." The instruction itself points at operand locations.

IL is a **stack machine**. Instead of pointing at operands, it computes by pushing and popping values on a temporary workbench called the **evaluation stack**. Every operation reduces to this one sentence.

> **Push** the needed values onto the stack; the operation **pops** the values on top, computes, and pushes the result back.

Let us follow how IL handles `a + b` as changes on the evaluation stack.

<div class="il-stk">
  <div class="il-stk-title">Evaluation stack — three steps to compute a + b</div>
  <div class="il-stk-row">
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.0</div>
      <div class="il-stk-note">Push a</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">ldarg.1</div>
      <div class="il-stk-note">Push b</div>
      <div class="il-stk-stack">
        <div class="il-stk-cell">b</div>
        <div class="il-stk-cell">a</div>
      </div>
    </div>
    <div class="il-stk-arrow">→</div>
    <div class="il-stk-step">
      <div class="il-stk-instr">add</div>
      <div class="il-stk-note">Pop both, add, push</div>
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

What a register machine finishes in one line — `add r2, r0, r1` — IL spreads across three: `ldarg.0` / `ldarg.1` / `add`. It looks inefficient, but that is IL's core design. **Because operand physical locations (which register, how many registers) were erased from the instruction,** IL does not care whether the CPU has 16 registers or 32. Only the abstract promise "pop two from the stack and add" remains; actual register allocation is decided later by the translator (JIT or AOT compiler) for that machine. The reason IL can be platform-independent is exactly this "erasing of location."

## Reading the First Method

Enough abstraction. Let us translate one real C# method to IL and read it line by line. Anyone can see the same result on [sharplab.io](https://sharplab.io) by setting the output mode to `IL`.

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
    ldarg.0      // Push a onto the evaluation stack
    ldarg.1      // Push b onto the evaluation stack
    add          // Pop both, add, push the result
    ret          // Return the top-of-stack value as the return value
}
```

Four lines are everything.

- **`ldarg.0`** — load argument 0. Pushes argument 0 (`a`) onto the evaluation stack. Because this is a `static` method, 0 is the first parameter. (In an instance method, 0 would be `this` and `a` would be 1 — that one-slot difference is the most common confusion when first reading IL.)
- **`ldarg.1`** — pushes argument 1 (`b`). The stack now holds two values.
- **`add`** — pops the top two values, adds them, and pushes one result back. Note that operands are never named. It is always "the two on top of the stack."
- **`ret`** — takes the top-of-stack value as the method return value and returns to the caller.

`.maxstack 2` declares that this method will push **at most two** values onto the evaluation stack during execution. The translator uses that number to prepare stack verification and code generation.

## Control Flow Dissolves into Branches

`Add` was a one-liner that only showed the shape of the stack machine. Real code has locals and control flow — `if`, `for`, `while`. Here comes the first big jump when reading IL. **IL has neither `if` nor `for`.** Everything flattens into conditional branches and jump labels.

```csharp
static int Max(int a, int b)
{
    if (a > b)
        return a;
    return b;
}
```

Release-build IL looks roughly like this. (Label names and exact opcodes vary slightly by compiler version.)

```
ldarg.0
ldarg.1
ble.s      IL_0006     // If a <= b, jump to IL_0006
ldarg.0                 // (when a > b) push a
ret
IL_0006:
ldarg.1                 // Push b
ret
```

The most confusing point when reading this is that **the condition is flipped**. The source says `if (a > b)`, but IL uses `ble` ("branch if less or equal"). Instead of "if the condition is true, run the body," the compiler translates to **"if the condition is false, skip the body"** — which finishes in a single branch and is more efficient. When the `if` condition and the IL branch condition look opposite, that is not a mistake; it is this flip.

Loops are even more dramatic.

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
    br.s      CHECK    // Jump straight to the condition check
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
    blt.s     LOOP     // If i < n, go back to LOOP
    ldloc.0
    ret
```

`.locals init` pre-declares the locals the method uses (`total`, `i`). After that, `stloc.0` means "store to local 0" and `ldloc.0` means "push local 0" — the counterparts of `ldarg` for arguments. On loop entry, `br.s CHECK` jumps **to the condition first**, then the body → increment → condition cycle runs, and when the condition is true, `blt.s LOOP` jumps back up. When `n` is 0, the body never runs — that behavior falls out naturally from this structure.

Putting `if` and `for` together leaves one sentence. **All C# control flow ultimately reduces to branch instructions that evaluate a condition onto the stack and decide where to jump from that result.** Write the same code with `while` and the IL is nearly identical. Differences in high-level syntax mostly disappear at the IL stage.

For reference, all IL so far is **Release**. A Debug build inserts a `nop` per line and round-trips return values through locals (so the debugger can set breakpoints and inspect values). When analyzing performance, you must **always look at Release IL** to match what actually ships.

## Costs Invisible in Source Show Up in IL

The real payoff of reading IL is here. Code that looks ordinary in C# source exposes its **hidden costs** as instructions once you drop to IL.

**① Boxing — `box`.** In the [memory series](/posts/ValueTypeBoxing/), boxing was described as happening "the moment a value type meets a reference contract." That moment is one line in IL.

```csharp
object o = 42;
```
```
ldc.i4.s   42
box        [System.Runtime]System.Int32   // Create a box on the heap and push the reference
stloc.0
```

That one `box` line is **one heap allocation**. Unboxing brings `unbox.any`. If you see those two words inside a loop, they are candidates for frame spikes.

**② Virtual dispatch — `call` vs `callvirt`.** `call` is used when the call target is fixed at compile time (`static` / `struct` methods); `callvirt` when the actual type is decided at runtime (class instance methods). The interesting point is that C# **usually emits `callvirt` even for non-`virtual` instance methods**. That is because `callvirt` also performs a **null check** just before the call. "Why callvirt for a non-virtual method?" is a spot every first-time IL reader hits once.

**③ String concatenation — the vanished `+`.** The IL for `"Hi, " + name` has neither `+` nor `add`. Instead there is `call ... System.String::Concat(string, string)`. Strings are immutable, so `+` cannot be arithmetic; the compiler translates it to a method call. The reason string `+` inside a loop is slower than `StringBuilder` is right there in the IL.

The common thread across the three cases is clear. **C# syntactic convenience (`object` assignment, dot calls, `+`) hides runtime cost.** IL strips that convenience and shows the instructions that actually run. There is also a discovery in the opposite direction. The IL for `static int Const() => 1 + 2;` is `ldc.i4.3 / ret` — no `add`. `1 + 2` was already **folded to `3` at compile time** (constant folding). So when experimenting with IL, use arguments or fields instead of constants so the compiler's folding does not hide what you want to see.

## Same IL, Three Fates — JIT · NativeAOT · IL2CPP

Now back to the first question. The IL we have seen is **not yet machine code.** Someone must translate that IL into CPU instructions before it can run. **When and how** that translation happens splits into three paths.

<div class="path3">
  <div class="path3-title">C# → IL is the same. After that, the paths diverge</div>
  <div class="path3-row">
    <div class="path3-col">
      <div class="path3-head path3-head-jit">JIT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ At the moment of execution</div>
      <div class="path3-box path3-box-end">Machine code</div>
      <div class="path3-foot">Runtime required · Only the first call is slow</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-aot">NativeAOT</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ At build time (ILC)</div>
      <div class="path3-box path3-box-end">Machine code</div>
      <div class="path3-foot">No runtime needed · Single binary</div>
    </div>
    <div class="path3-col">
      <div class="path3-head path3-head-il2cpp">IL2CPP</div>
      <div class="path3-box">C#</div>
      <div class="path3-down">↓ Roslyn</div>
      <div class="path3-box">IL</div>
      <div class="path3-down">↓ At build time (il2cpp)</div>
      <div class="path3-box">C++</div>
      <div class="path3-down">↓ Platform toolchain</div>
      <div class="path3-box path3-box-end">Machine code</div>
      <div class="path3-foot">iOS · consoles ban JIT → AOT forced</div>
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

- **JIT** — holds onto IL and translates a method to machine code the **first time it is called**. It can optimize for that machine's CPU and runtime statistics, but pays a translation cost (cold start) on the first call. Ordinary .NET servers and desktops, and Mono in the Unity editor, use this approach.
- **NativeAOT** — at build time, translates IL **directly to native** and freezes it into a single binary. It runs without a translator at execution time, and cold start is near zero. CLI tools and serverless are the main targets.
- **IL2CPP** — Unity's AOT. It **first converts IL to C++**, then builds natively with each platform's C++ toolchain (Xcode, NDK, console SDKs). iOS and consoles ban JIT for security reasons, so mobile builds require it.

### The Decisive Difference in One Line — "Can New Code Be Created at Runtime?"

The surface of the three paths is "translation timing," but the deeper difference is one thing. **JIT carries an engine that can still take IL and turn it into machine code while running; AOT has no such engine.** Everything was already frozen at build time.

Remember that one line. All of Parts 2 and 3 connect through this single sentence. "Creating new code at runtime" means **reflection's dynamic features** and metaprogramming — exactly the capabilities my tool would come to depend on, and exactly what AOT does not allow.

### So Where Does My Tool Sit?

Here the coordinates for answering the first question come into focus. My tool is easy to confuse with **two entirely different builds**.

- **[A] The build of the game being *analyzed*** — Unity C# goes through IL2CPP into an `.ipa` / `.apk`. It reaches players' hands and is subject to IL2CPP's AOT constraints.
- **[B] The build of my analysis *tool* itself** — a separate .NET program that runs in a terminal on a developer's PC. It does not ship inside the game, so it is **unrelated to IL2CPP / AOT constraints**.

The tool is [B], so it need not care about the game's IL2CPP constraints, and can choose JIT vs freezing with NativeAOT **purely on the tool's usability** — especially cold start. Code analysis tools are often invoked countless times in one session, so startup time per call accumulates. That makes "freeze with AOT and kill cold start?" a natural temptation. But that temptation has a trap. The line just emphasized — **AOT cannot create code at runtime** — can collide with the tool's core feature. To see that collision, we have to move to the second question.

## IL Is Only Half — Its Partner, Metadata

Before Part 2, one bridge. Looking back at the IL above, instructions **cite names and signatures directly**.

```
box   [System.Runtime]System.Int32
call  string [System.Runtime]System.String::Concat(string, string)
```

Whether `System.Int32` is a value type, which assembly and which method token `String.Concat` is — that information is **not inside the IL instruction stream.** IL only points and says "call token number N"; what that token actually is — type, method, field — is held by a separate structure called **metadata tables**. A `.dll` file is effectively a bundle of **IL stream + metadata tables**.

That metadata is the starting point of Part 2. The runtime can return type information via `typeof(int)` or `obj.GetType()`, and Roslyn can read code as meaning — both ultimately happen on top of these tables.

---

# Part 2. Reading Code as Meaning

## The Second Question — Why grep Is Not Enough

What my tool must do looks like this. When `HouseEditPresenter`'s `OnTapFooter` method calls `_model.UpdateFloor()`, **follow which implementation that call actually goes to**.

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

The first method that comes to mind is text search (grep). Search the whole project for `"UpdateFloor"` and you are done — or so it seems. But grep hits a wall immediately. Even when the string `UpdateFloor` appears, grep cannot tell whether it is

- an actual **method call**
- text inside a comment `// be careful calling UpdateFloor`
- a **variable** named `UpdateFloor`
- a **same-named method** on an entirely different class

More decisively, grep cannot build the **link** that `_model`'s type is the interface `IHouseEditModel` and its real implementation is `HouseEditModel`. To text search, code is just a **sequence of characters**. What we need is not characters but **meaning**.

To get meaning, you have to interpret the text upward step by step. Those interpretation stages are exactly **the process by which a compiler understands code**.

## How a Compiler Understands Code

The compiler frontend lifts source text through three stages. Those three stages are the core of compiler theory, and the identity of "reading as meaning."

<div class="sem">
  <div class="sem-title">Where grep stops, where the compiler climbs</div>
  <div class="sem-row">
    <div class="sem-stage sem-stage-dim">
      <div class="sem-stage-name">Raw text</div>
      <div class="sem-stage-ex">_model.UpdateFloor()</div>
      <div class="sem-stage-desc">A sequence of characters. grep only sees here</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">① Lexical analysis<br><span>Tokens</span></div>
      <div class="sem-stage-ex">[_model] [.] [UpdateFloor] [(] [)]</div>
      <div class="sem-stage-desc">Whitespace and comments removed. Comment text is filtered out</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage">
      <div class="sem-stage-name">② Syntax analysis<br><span>Syntax tree</span></div>
      <div class="sem-stage-ex">MemberAccess( target=_model, name=UpdateFloor )</div>
      <div class="sem-stage-desc">Knows structure. Distinguishes "call vs variable"</div>
    </div>
    <div class="sem-arrow">→</div>
    <div class="sem-stage sem-stage-goal">
      <div class="sem-stage-name">③ Semantic analysis<br><span>Semantic model</span></div>
      <div class="sem-stage-ex">_model : IHouseEditModel<br>→ impl HouseEditModel.UpdateFloor</div>
      <div class="sem-stage-desc">Knows meaning. Type · symbol links complete</div>
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

**① Lexical analysis (Lexing).** Splits the source string into a sequence of **tokens**. `_model.UpdateFloor()` becomes `[identifier _model]` `[dot]` `[identifier UpdateFloor]` `[open paren]` `[close paren]`. Whitespace and comments are removed at this stage. In other words, the **`UpdateFloor` inside a comment that grep could not filter is already dropped here**.

**② Syntax analysis (Parsing).** Assembles tokens into a **syntax tree** according to grammar rules. The **structure** "this is a member-access expression containing a method call" is formed. Now you can tell whether "`UpdateFloor` is a call or a variable." But the syntax tree still knows **structure only**. It does not know what type `_model` is.

**③ Semantic analysis.** Lays **type and symbol information** onto the syntax tree. It finds `_model`'s declaration and learns the type is `IHouseEditModel` (symbol binding), connects which interface member `UpdateFloor` refers to, and follows that the interface's implementation is `HouseEditModel`. The product of this stage is the **semantic model**. Only then can you answer "which implementation does this call actually go to?"

One sentence through all three stages: **grep stays at stage 0 (raw text); the answer my tool needs is at stage 3 (semantic model).** Implementing the gap yourself means rebuilding the entire C# compiler frontend — the C# language specification is a 1,500-page document that grows every year with generics, async, lambdas, pattern matching. It is not a scale one person can keep up with alone.

## Reflection — Reading the Meaning of Already-Compiled Code at Runtime

Here a natural question arises. Doesn't .NET already have **reflection** for looking into types and members? `obj.GetType()`, `type.GetMethods()` — wouldn't that do?

Reflection's identity is the **API that reads metadata tables at runtime**, which we saw at the end of Part 1. When the runtime loads a `.dll`, it parses the metadata tables inside and builds `Type` objects. The `Type` that `typeof(int)` returns is exactly the runtime representation of one metadata row. `GetMethods()` walks the method table attached to that type. In short, **reflection = looking back into the finished compilation product (IL + metadata)**.

But reflection cannot do my tool's job. It has decisive limits.

- What reflection sees is an **already-compiled assembly**. What a method **calls** (`_model.UpdateFloor()` inside the method body) lives in the **IL body**, not metadata, so ordinary reflection APIs struggle to follow it.
- **Source-level information** such as comments, local variable names, and "which source line this call is on" mostly disappears during compilation and is not in metadata.

In short, reflection is strong at **"what exists"** (which methods does this type have?) but weak at **"what calls what in source."** What my tool wants is the latter — the semantic structure of source code. So the answer is not reflection reading metadata, but the **compiler itself** interpreting source through stages ①②③.

## So Roslyn — the Compiler as a Library

**Roslyn** is Microsoft's official C# compiler. But it is not merely a compiler; the key is that it **exposes those ①②③ stages as a library (API) that external programs can call**. The same compiler `dotnet build` runs internally is something we can invoke from code.

What Roslyn gives is exactly what we needed in stages 1–3.

- **SyntaxTree** — ② syntax tree. Walk source structure as nodes
- **SemanticModel** — ③ semantic model. Answers "what is this node's type?" and "where was this symbol declared?"
- **ISymbol** — the semantic unit of types, methods, fields. The knot linking interfaces to implementations, calls to declarations

When my tool follows `_model.UpdateFloor()`, asking Roslyn "give me the symbol for this call node" yields the symbol `IHouseEditModel.UpdateFloor`, and asking "find implementations of this interface member" yields `HouseEditModel.UpdateFloor`. What would have been an entire compiler frontend if built by hand ends in **a few API calls**. That is why you use Roslyn when building a code analysis tool in C#.

### Why Roslyn Is Heavy (50MB+)

There is a cost. Roslyn dependencies run to tens of megabytes. It is not a light library. That weight exists because Roslyn carries **an entire compiler suite**.

- **Every version of C# syntax** (including features added each year)
- **MSBuild integration** — reading `.csproj`, resolving NuGet packages, resolving cross-project references
- **Workspace** abstraction — analyzing multiple projects in a solution at once
- A **metadata cache** for the entire standard library

So Roslyn's 50MB is not "because it has many features," but because **the work of understanding C# as meaning itself demands that much knowledge**. Semantic analysis cannot look at one file alone; it must know every type, assembly, and project that file references. Roslyn's weight is the weight of those "things it must know."

And here, the line emphasized in Part 1 returns. Roslyn **dynamically loads** analyzers and source generators from user projects at runtime, and uses **reflection extensively** internally. In other words, Roslyn has a deep foot in the "dynamically dealing with code at runtime" side. Exactly at that point, the first question (AOT for fast startup) and the second question (reading code with Roslyn) collide head-on.

---

# Part 3. Where the Two Worlds Collide

## Reflection.Emit — Stamping Out IL at Runtime

To see the nature of the collision, you need the other half of reflection. The reflection in Part 2 was **read** (introspection). Reflection also has **write**. `System.Reflection.Emit` is an API by which a program **generates a new method's IL byte by byte while running**, then hands it to the runtime saying "turn this into machine code and execute it."

Why use something like that? **Performance.** Serialization is the classic example. Converting a type to JSON by reading fields one by one via reflection every time is slow. Instead, **generate type-specific serialization code once as IL at runtime**, and afterward it is as fast as hand-written code. Dynamic constructor injection in DI containers, dynamic proxies, `Expression.Compile()` — all create code at runtime on the same principle to gain speed.

## So It Collides with AOT by Nature

Now Part 1's one line is fully recovered. **AOT has already frozen every IL into machine code at build time, so there is no JIT engine left to accept IL at runtime and translate it.**

So no matter how well `Reflection.Emit` produces IL at runtime, there is nowhere to turn it into machine code and run it. The code breaks. This is a constraint **shared** by IL2CPP and NativeAOT (both are AOT). The root cause of "things that break under AOT," tabulated in [Foundation episode 3](/posts/DotnetRuntimeVariants/), was exactly this one line.

One more thing breaks in chain. AOT deployments usually come with **trimming** (removing unused code to shrink the binary), and reflection that **looks up members by string** — like `type.GetMethod("UpdateFloor")` — cannot be analyzed statically. The trimmer decides the method is unused and deletes it; when reflection looks for it at runtime, it fails.

## The Tool's Dilemma, and the Conclusion as Mechanism

The place where the two questions meet is now visible.

- **The attractive answer to the first question**: Freeze the tool with NativeAOT and cold start disappears. Ideal for an analysis tool invoked repeatedly.
- **The inevitable answer to the second question**: The tool depends on Roslyn. But Roslyn depends deeply on dynamic loading and reflection.

Overlap the two, and **freezing Roslyn wholesale with NativeAOT is fundamentally hard.** "The ability to read code as meaning" and "fast startup" stand on different runtime assumptions. The former demands the runtime's dynamic capabilities; the latter is gained by giving those capabilities up. One tool cannot maximize both at once.

What matters here is not the detail of "so which option did I package the tool with." That is a per-project choice. The core is the **structural tension** that forces that choice — metaprogramming (the power to deal with code at runtime) and AOT (speed gained by giving that power up in advance) **compete over the same resource**. Understand that tension, and why some .NET tools drop lightly into AOT and others cannot is explained at a glance.

## Source Generators — a Path Around the Collision

So must metaprogramming be abandoned? Modern .NET's answer is not "abandon" but **move the timing**.

If `Reflection.Emit` creates code **at runtime**, a **Source Generator** does the same job **at compile time**.

<div class="emit">
  <div class="emit-title">Move when code is created</div>
  <div class="emit-row">
    <div class="emit-card emit-card-bad">
      <div class="emit-card-head">Reflection.Emit</div>
      <div class="emit-flow">Compile → Run → <b>Generate IL at runtime</b> → JIT translates</div>
      <div class="emit-verdict">Needs JIT · Breaks under AOT</div>
    </div>
    <div class="emit-card emit-card-good">
      <div class="emit-card-head">Source Generator</div>
      <div class="emit-flow"><b>Generate C# during compile</b> → Compile together → Already in IL</div>
      <div class="emit-verdict">No runtime generation · AOT-friendly</div>
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

Source Generators run on top of Roslyn. While compilation proceeds, they look into the syntax trees and semantic models from Part 2 and **generate additional C# source** that is fed into the compile. That generated code is translated to IL together with the original code, so **the resulting IL already contains everything needed.** There is nothing left to create with `Emit` at runtime. So it does not collide with AOT.

`System.Text.Json`'s shift in this direction is representative. It used to build serialization code via runtime reflection; now it generates at compile time with Source Generators and works fully under AOT. **Moving metaprogramming's timing from runtime to compile time** — that is how modern .NET reconciled "dynamic convenience" with "AOT speed."

## Synthesis — Five Domains Touched by One Small Tool

Back to the original two questions. "How do I ship the tool," "how does the tool read code" — the surface was modest, but following the answers meant passing through five knowledge domains in turn.

- **Bytecode virtual machine** — IL and the stack machine (Part 1)
- **Runtime systems** — JIT · AOT translation timing and its costs (Part 1)
- **Compiler theory** — lexing · parsing · semantic analysis (Part 2)
- **Metaprogramming and reflection** — metadata, `Emit`, Source Generators (Parts 2 · 3)
- **Static program analysis** — reading source semantic structure to answer questions, i.e. what the tool set out to do (throughout)

That these five are not separate knowledge but **mesh inside a single question** — that is the conclusion of this loop. Without knowing IL you do not know metadata; without metadata you do not know reflection; without the relationship between reflection and JIT/AOT you cannot explain why Roslyn is heavy, why it collides with AOT, or why Source Generators appeared. An attempt to properly build one small analysis tool ended up asking the whole of "how C# runs and how it reads itself."

---

## Summary

1. **C# does not become machine code in one step.** It first becomes IL, and translation timing (JIT at runtime / AOT at build time) divides JIT · NativeAOT · IL2CPP. IL is a register-free stack machine, so hidden costs like boxing and virtual dispatch, and the branch structure of control flow, show up as instructions.
2. **To read code as meaning you need the compiler's three stages** (lexing → syntax tree → semantic model). grep stays on raw text; reflection only sees already-compiled products. Source semantic structure is given by the compiler itself — **Roslyn**. Roslyn is heavy (50MB+) because "knowing meaning" demands that much knowledge.
3. **The one line that ties everything is "Can new code be created at runtime?"** JIT can; AOT cannot. So Roslyn, which depends on `Reflection.Emit` and dynamic loading, collides with AOT, and **Source Generators** move code-generation timing to compile time to step around that collision.
4. **One small tool cuts through five domains** (bytecode VM · runtime · compiler theory · metaprogramming · static analysis). They are not separated knowledge but meshed inside a single question.

---

## References

### Primary sources

- [ECMA-335 — Common Language Infrastructure (CLI)](https://ecma-international.org/publications-and-standards/standards/ecma-335/) · Standard specification for the IL instruction set and metadata structure
- [Roslyn (dotnet/roslyn) GitHub](https://github.com/dotnet/roslyn) · Official implementation of the C# compiler and analysis APIs
- [Microsoft Learn — Source Generators](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/source-generators-overview) · Overview of compile-time code generation
- [Microsoft Learn — Native AOT limitations](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/) · Official list of features AOT breaks
- [Unity Blog — "IL2CPP Internals: A tour of generated code"](https://unity.com/blog/engine-platform/il2cpp-internals-a-tour-of-generated-code) · Actual generated code from IL → C++ conversion

### Tools

- [SharpLab](https://sharplab.io) · Live C# ↔ IL ↔ JIT assembly conversion
- [ILSpy](https://github.com/icsharpcode/ILSpy) · .dll disassembler and decompiler

### Books

- 『CLR via C#』 (Jeffrey Richter) · Definitive treatment of IL, metadata, reflection, and JIT behavior
- 『Crafting Interpreters』 (Robert Nystrom) · Hands-on introduction to implementing lexing, parsing, and tree walking. Foundation for understanding how a compiler frontend works (free online)
- 『C# in Depth』 (Jon Skeet) · How C# language features translate into IL
