---
title: Unity Profiler Optimization
date: 2023-11-15 12:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [unity, optimization, profiler]

difficulty: intermediate
lang: en
toc: true
---

## Table of Contents
- [1. Unity Profiler structure](#unity-profiler-structure)
- [2. Profiler threads](#profiler---threads)
- [3. Sample stack vs call stack](#sample-stack-vs-call-stack)
- [4. About markers](#about-markers)
- [5. Finding bottlenecks](#finding-bottlenecks)
- [6. Graphics batching](#graphics-batching)

---

<br>
<br>

## Unity Profiler

- A tool that lets you optimize quickly either in the Editor or from development builds.

<br>

#### Unity Profiler structure

![Desktop View](/assets/img/post/unity/profiler01.png){: : width="1200" .normal }

<br>
<br>

#### Enable the Development Build option
- Most additional options are not necessary. They mainly support auto profiler connection and deep profiling.
- Auto-connect bakes the current PC's IP, so automatic connection works only from the machine used to build.

![Desktop View](/assets/img/post/unity/profiler02.png){: : width="400" .normal }
![Desktop View](/assets/img/post/unity/profiler03.png){: : width="400" .normal }

<br>
<br>

#### Profiler - CPU module
- You can inspect data per sample.
- You can verify how much CPU time each process consumes.

![Desktop View](/assets/img/post/unity/profiler04.png){: : width="1200" .normal }

<br>
<br>

#### Profiler - Chart view
- Check whether the frame is processed faster than your target FPS. For 60 FPS, most work should finish within 16ms. For 30 FPS, within 33ms.
- Check whether graph overload spikes occur.
- If VSync is on, charts are effectively clamped around 60 FPS / 16ms. For profiling, turn VSync off.

![Desktop View](/assets/img/post/unity/profiler05.png){: : width="500" .normal }

<br>
<br>

#### Profiler - Details window, Timeline view
- CPU usage time is easy to understand visually.
- You can inspect all threads at a glance.
- You can track timing and execution order relationships linearly.

![Desktop View](/assets/img/post/unity/profiler06.png){: : width="1600" .normal }

<br>
<br>

#### Profiler - Details window, Hierarchy view
- Understand parent-child call relationships.
- Sort by the metric you care about.

![Desktop View](/assets/img/post/unity/profiler07.png){: : width="1600" .normal }

<br>
<br>

- Start by fixing the longest-running samples first.

![Desktop View](/assets/img/post/unity/profiler08.png){: : width="1600" .normal }

<br>
<br>

#### Profiler - Threads

- Main Thread
> 1. Unity Player Loop runs (`Awake`, `Start`, etc.)  
> 2. `MonoBehaviour` scripts primarily run here

<br>

- Render Thread
> 1. Thread that assembles commands to send to GPU  
> Draw calls are issued on Main Thread, then executed through command assembly on Render Thread

<br>

- Worker Threads (Job Threads)
> 1. Asynchronous parallel work from Job System, etc.  
> 2. Compute-heavy tasks such as animation/physics run here  
> Jobs are scheduled on Main Thread and processed on Worker Threads

<br>

![Desktop View](/assets/img/post/unity/profiler09.png){: : width="400" .normal }

<br>
<br>

- There can be causality between methods across different threads even if they do not call each other directly.
> ex1. Job scheduled  > processed on worker thread  
> ex2. Main thread `MeshRenderer.Draw()` > graphics commands assembled on render thread  
> If main-thread work is delayed, the render thread can sit idle.

<br>
<br>

- Enable `Show Flow Events` to inspect execution order and causality.

![Desktop View](/assets/img/post/unity/profiler10.png){: : width="1600" .normal }

<br>
<br>

#### Sample stack vs call stack

![Desktop View](/assets/img/post/unity/profiler11.png){: : width="1600" .normal }

- Sample stack and call stack are different. Sample stacks are chunked and only include marked C# methods/code blocks.
- Because of that, sampling is grouped coarsely. Unity does not sample every C# method call by default; it samples marked methods/blocks.

<br>

##### Notes for deep profiling
> In Deep Profiling, every C# call (including constructors/properties) is marked.  
> This introduces heavy profiling overhead and can make data less accurate.

- So deep profiling should be used only in a very limited scope and short time window.

<br>
<br>

#### How to enable call stack

![Desktop View](/assets/img/post/unity/profiler12.png){: : width="400" .normal }

- You must enable the Call Stack button first (it becomes highlighted).
- In Call Stack dropdown, choose the marker you want.

![Desktop View](/assets/img/post/unity/profiler13.png){: : width="2400" .normal }

- For specific samples, you can record full call stacks.
> 1. `GC.Alloc`: managed allocation occurred  
> 2. `UnsafeUtility.Malloc`: unmanaged allocation that must be freed manually  
> 3. `JobHandle.Complete`: main thread force-synchronized job completion

- Not recommended for regular use; use only in limited cases.

<br>
<br>

#### About markers

<br>

#### 1. Main loop markers

- `PlayerLoop`: root of samples executed by player loop

- `BehaviourUpdate`: holder for `Update()` samples

- `FixedBehaviourUpdate`: holder for `FixedUpdate()` samples

- `EditorLoop`: editor-only loop

<br>

#### 2. Graphics markers (Main Thread)

- `WaitForTargetFPS`
> Time spent waiting for VSync / target framerate

- `Gfx.WaitForPresentOnGfxThread`
> Marker appears when render thread is waiting on GPU, and main thread also has to wait

- `Gfx.PresentFrame`
> Waiting for GPU to render current frame  
> If long, GPU-side processing is slow

- `GPU.WaitForCommands`
> Render thread is ready for new commands, but main thread is not feeding them yet, so it waits

<br>
<br>

#### Finding bottlenecks
- Graphics markers are useful for identifying CPU/GPU bounds.
- If Main Thread waits for Render Thread, bottleneck can be on thread handoff; render commands are generated around late player loop stages.
- In other words, do not only ask "GPU or CPU"; also check cross-thread bottlenecks.

<br>

![Desktop View](/assets/img/post/unity/profiler14.png){: : width="2400" .normal }

- CPU Main Thread bound
> Main thread is slow, so render thread waits

<br>

![Desktop View](/assets/img/post/unity/profiler15.png){: : width="2400" .normal }

- Render Thread bound
> Still sending draw-call commands for previous frame

<br>

![Desktop View](/assets/img/post/unity/profiler16.png){: : width="2400" .normal }

- Worker Thread bound
> Main thread is synchronously waiting for jobs to complete

<br>

- Xcode Frame Debugger and newer Unity profiler versions can show CPU/GPU bound hints.


<br>
<br>

#### There are 4 major bottleneck types

1. CPU Main Thread bound
2. CPU Worker Thread bound (physics, animation, job system)
3. CPU Render Thread bound (CPU-side command assembly/transfer to GPU, not GPU core bottleneck itself)
4. GPU bound

<br>

- Typical bottleneck triage flow
> Main thread bottleneck? Optimize player loop first  
> If not, focus on physics/animation/job system  
> If still not, inspect render-thread bottleneck and then separate GPU vs CPU factors

<br>

- If it is a render-thread CPU bottleneck
- CPU graphics optimization
> Camera/culling optimization  
> Reduce SetPass calls (batching)  
> Use graphics batching where possible: SRP batching, Dynamic batching, Static batching, GPU instancing

<br>

#### General facts
- Before batching, one important point.
- Graphics pipeline delays can come from:
> CPU-side delay while assembling commands (more common than pure GPU weakness today)  
> CPU->GPU command/resource upload delay  
> GPU internal processing delay

- Draw call means CPU sends render-execute command to GPU.
> In many cases, CPU cost/upload delay from render state changes is heavier than the draw call itself.

- Often the expensive part is just before "draw".
- GPU generally prefers fewer large meshes over many tiny meshes.
- Many rendering issues are not from weak GPU compute, but from inefficient GPU usage.
> Sending many tiny meshes wastes GPU execution units (Wavefront/Warp).  
> Example: if a unit processes 256 vertices and you keep feeding 128, utilization is wasted.

<br>
<br>

#### Graphics batching

#### 1. SRP batching (URP, HDRP)

- <span style="color:pink">Before draw commands, repeatedly setting different render states (different shaders) is often the bigger cost.</span>
- ***Group meshes using the same shader & material***
- **Bundle multiple draw calls under one SetPass Call (same shader variant)**
- Per-material data: upload once early in a large list
- Per-object data: upload every frame in a large list
- Select mesh from list using index/offset and call `Draw()`
- **Reducing the number of shaders used in the project helps optimization.**

<br>

#### 2. Static batching (Static)

- <span style="color:pink">GPU likes drawing large meshes at once. Concept: reduce transfer overhead.</span>
- ***Pre-merge non-moving meshes and bake -> upload to GPU ahead of time -> call `DrawIndexed()` per renderer***
- Very fast CPU/GPU processing
- Unity Editor bakes it only when building the app
- Downside: merged unique meshes increase memory usage

<br>

#### 3. Dynamic batching (Dynamic)

- <span style="color:pink">GPU likes large meshes at once. Concept: reduce transfer overhead.</span> -> generally not highly recommended.
- ***Merge meshes every frame > run one `Draw()`***
- Optimized from GPU perspective
> GPU receives one mesh/draw command, so processing is very fast
- But CPU must merge meshes every frame
> Fewer draw commands, but mesh-merging itself costs CPU
- Baked every frame
> In some cases, merging meshes costs more than having many draw calls

<br>

#### 4. GPU instancing

- <span style="color:pink">Reduce command delivery from CPU to GPU.</span>
- ***For identical mesh + identical shader/material***
- Upload mesh data to GPU once
> Per-instance unique data (object-to-world matrix) is sent as an array
- Very fast CPU-side when drawing many identical objects
- (<500 instances) very small-vertex meshes can be inefficient
> GPU prefers large meshes; meshes with <=256 vertices often gain less.

<br>

#### Summary

- ***Typical efficiency: SRP batching, Static batching > GPU instancing > Dynamic batching***
- CPU cost before draw calls, especially **render state setup**, is often larger than the **draw call** itself
- Focus on reducing SetPass calls (SRP batching) before anything else, while still optimizing draw calls as needed
- Before draw-call reductions (instancing/dynamic batching), enabling SRP batching and reducing shader variety is usually most effective
> Turning on SRP batching and reducing shader kinds is often the highest impact.

#### Reduce SetPass calls!!

![Desktop View](/assets/img/post/unity/profiler17.png){: : width="600" .normal }

- Use **Frame Debugger** to see why SetPass calls are not merged.
- ***Set a target below 300 SetPass calls.***


<br>
<br>

#### If GPU rendering is the bottleneck

![Desktop View](/assets/img/post/unity/profiler18.png){: : width="1800" .normal }

- ***Xcode GPU Frame Capture***
- Commands are listed in sequence; inspect time cost at each render stage.
- You can find draws with abnormal cost -> find the shader/mesh used by that draw and optimize them.

<br>
<br>

- Reference
> Notes from lecture by Je-min Lee (Retro Unity Partnership Engineer).  
> [IJEMIN GitHub](https://github.com/IJEMIN)
