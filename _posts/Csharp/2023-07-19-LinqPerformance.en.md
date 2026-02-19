---
title: About C# LINQ Performance
date: 2023-07-19 11:06:00 +/-TTTT
categories: [C#, C# Study]
tags: [csharp, linq]
difficulty: intermediate
lang: en
toc: true
chart: true
tldr:
  - "LINQ Count() has significant overhead versus for/foreach - never use it in per-frame calls"
  - "Filtering (Where) and transformation (Select) perform close to for/foreach"
  - "LINQ creates intermediate buffers (arrays), increasing GC pressure - frequent calls can cause GC spikes"
  - "Use LINQ for prototypes/non-critical paths, and for/foreach for per-frame or performance-critical code"
---

## Table of Contents

- [Advantages of LINQ](#advantages-of-linq)
- [Usage Rules](#usage-rules)
- [Benchmark - Loops](#benchmark---loops)
- [Benchmark - Filtering](#benchmark---filtering)
- [Benchmark - Transformation](#benchmark---transformation)
- [How Much GC Does LINQ Create?](#how-much-gc-does-linq-create)
- [Conclusion](#conclusion)

---

<br>
<br>

## Advantages of LINQ
> * LINQ (Language Integrated Query) is a C# feature set for writing concise and convenient code.  
Developers can use query syntax to perform filtering, sorting, and grouping on data sources  
with minimal code.

<br>

## Notes When Using LINQ
> * Most LINQ operators create intermediate buffers (a kind of array), and all of that becomes garbage. 👉 <span style="color:red">GC occurs</span>  
> * Even when one or two LINQ operators are enough, splitting logic into many LINQ calls for readability can degrade performance.
> * Operators such as Average, Count, OrderBy, and Reverse iterate the source sequence, so they are less efficient from a performance perspective.

<br>

#### So before using LINQ, think through these rules.
<br>

## Usage Rules
> 1. Is this a situation where rapid implementation matters (prototype, TDD)? - <span style="color:green">Use LINQ</span>
> 2. Is this code not performance-sensitive? - <span style="color:green">Use LINQ</span>
> 3. Is LINQ's convenience/readability truly needed here? - <span style="color:green">Use LINQ</span>
> 4. Is this called every frame or performance-critical? - <span style="color:red">Do not use LINQ</span>

<br>
<br>

## LINQ Performance Benchmark
> * Benchmark library: [BenchMark](https://github.com/dotnet/BenchmarkDotNet)
> * Test code: [TestCode](https://github.com/jamesvickers19/dotnet-linq-benchmarks)
> * Original article: [LinqPerformance](https://medium.com/swlh/is-using-linq-in-c-bad-for-performance-318a1e71a732)

<br>
<br>

## Benchmark - Loops
> Return the number of Customers whose age is below 18

<div class="code-compare">
  <div class="code-compare-pane">
    <div class="code-compare-label label-before">For / Foreach</div>
    <div class="highlight">
<pre><code class="language-csharp">// Performance: fast (no GC)
int count = 0;
foreach (var c in customers)
{
    if (c.Age &lt; 18)
        count++;
}
return count;</code></pre>
    </div>
  </div>
  <div class="code-compare-pane">
    <div class="code-compare-label label-after">LINQ Count</div>
    <div class="highlight">
<pre><code class="language-csharp">// Performance: slower (GC occurs)
// Count() internally
// iterates the entire sequence
return customers
    .Count(c => c.Age &lt; 18);</code></pre>
    </div>
  </div>
</div>

1. For / Foreach
<img src="/assets/img/post/linq/linq01.png" width="1920px" height="1080px" title="256" alt="linq1">

2. LINQ Count / Predicate Count
<img src="/assets/img/post/linq/linq02.png" width="1920px" height="1080px" title="256" alt="linq2">
<br>

<img src="/assets/img/post/linq/linq03.png" width="1920px" height="1080px" title="256" alt="linq3">

Compared to for/foreach, LINQ has some overhead (indirect extra time, memory, and resources for functionality).  
Filtering then counting is relatively close to `for`, but plain `Count` that returns sequence length shows notable performance degradation.

<br>
<br>

## Benchmark - Filtering
> Return a list that is a subset of customers with age 18 or higher

1. For / Foreach
<img src="/assets/img/post/linq/linq04.png" width="1920px" height="1080px" title="256" alt="linq4">

2. LINQ
<img src="/assets/img/post/linq/linq05.png" width="1920px" height="1080px" title="256" alt="linq5">

<img src="/assets/img/post/linq/linq06.png" width="1920px" height="1080px" title="256" alt="linq6">

It shows very similar performance to for/foreach implementation. About 4ms slower than for/foreach.

<br>
<br>

##### Example code actually used when filtering RaycastAll results and checking tags
<img src="/assets/img/post/linq/linq07.png" width="1920px" height="1080px" title="256" alt="linq7">

For filtering scenarios, LINQ made the code much more concise and readable than typical for/foreach.

<br>

## Benchmark - Transformation
> Return a list of customers where age is represented in months instead of years

1. For / Foreach
<img src="/assets/img/post/linq/linq08.png" width="1920px" height="1080px" title="256" alt="linq8">

2. LINQ
<img src="/assets/img/post/linq/linq09.png" width="1920px" height="1080px" title="256" alt="linq9">

<img src="/assets/img/post/linq/linq10.png" width="1920px" height="1080px" title="256" alt="linq10">

<br>
<br>

## How Much GC Does LINQ Create?
> See the link below for test conditions.
* Original article: [Just How Much Garbage Does LINQ Create?](https://www.jacksondunstan.com/articles/4840)

#### Result
1. GC Alloc Count
<img src="/assets/img/post/linq/linq11.png" width="1920px" height="1080px" title="256" alt="linq11">
<img src="/assets/img/post/linq/linq12.png" width="1920px" height="1080px" title="256" alt="linq12">
<br>
<br>

## Microsoft Docs: Performance Recommendations for Unity
[Performance recommendations for Unity](https://learn.microsoft.com/ko-kr/windows/mixed-reality/develop/unity/performance-recommendations-for-unity?tabs=openxr)

<img src="/assets/img/post/linq/linq13.png" width="1920px" height="1080px" title="256" alt="linq13">

<br>
<br>

## LINQ vs For - Performance Comparison Chart

<div class="chart-wrapper">
  <div class="chart-title">Relative execution time (lower is faster, for = 1.0 baseline)</div>
  <canvas id="linqBenchChart" class="chart-canvas" height="220"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'linqBenchChart',
  type: 'bar',
  data: {
    labels: ['Loop (Count)', 'Filtering (Where)', 'Transformation (Select)'],
    datasets: [
      {
        label: 'For / Foreach',
        data: [1.0, 1.0, 1.0],
        backgroundColor: 'rgba(39, 174, 96, 0.7)',
        borderColor: 'rgba(39, 174, 96, 1)',
        borderWidth: 1
      },
      {
        label: 'LINQ',
        data: [3.8, 1.05, 1.1],
        backgroundColor: 'rgba(192, 57, 43, 0.7)',
        borderColor: 'rgba(192, 57, 43, 1)',
        borderWidth: 1
      }
    ]
  },
  options: {
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          label: function(ctx) {
            return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + 'x';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Relative execution time (multiplier)' }
      }
    }
  }
});
</script>

## Conclusion
1. LINQ `Count` is significantly slower.
2. Filtering (`Where`) and transformation (`Select`) are similar to `for` in performance.
3. LINQ allows very concise one- or two-line code.
4. Debugging is harder.
5. GC allocation occurs; overusing LINQ can become hard to manage.
6. Avoid LINQ in per-frame calls or other performance-sensitive paths.
