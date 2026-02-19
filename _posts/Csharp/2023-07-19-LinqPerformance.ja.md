---
title: C# LINQ パフォーマンスについて
date: 2023-07-19 11:06:00 +/-TTTT
categories: [C#, C# Study]
tags: [csharp, linq]
difficulty: intermediate
lang: ja
toc: true
chart: true
tldr:
  - "LINQ の Count() は for/foreach に比べて大きなオーバーヘッドがある - 毎フレーム呼び出しでは使用禁止"
  - "フィルタリング (Where) と変換 (Select) は for/foreach とほぼ同等の性能"
  - "LINQ は中間バッファ (配列) を生成し GC 圧力を上げる - 頻繁な呼び出しは GC スパイクの原因"
  - "プロトタイプ・非クリティカルなコードでは LINQ、毎フレームや性能重視箇所では for/foreach"
---

## 目次

- [LINQ の利点](#linq-の利点)
- [使用時ルール](#使用時ルール)
- [ベンチマーク - 反復処理](#ベンチマーク---反復処理)
- [ベンチマーク - フィルタリング](#ベンチマーク---フィルタリング)
- [ベンチマーク - 変換](#ベンチマーク---変換)
- [LINQ はどれだけ GC を生成するか](#linq-はどれだけ-gc-を生成するか)
- [結論](#結論)

---

<br>
<br>

## LINQ の利点
> * LINQ (Language Integrated Query) は、簡潔で扱いやすいコードを書くための C# 機能セットです。  
クエリ構文を使うことで、最小限のコードでデータソースに対する  
フィルタリング、ソート、グルーピングを実行できます。

<br>

## LINQ 使用時の注意点
> * LINQ の多くの演算子は中間バッファ (配列のようなもの) を生成し、それがすべてガベージになります。👉 <span style="color:red">GC 発生</span>  
> * 1〜2 個の LINQ 演算子で済む場面でも、可読性目的で細かく分割しすぎると性能低下の原因になります。
> * Average、Count、OrderBy、Reverse などは元シーケンスを反復するため、性能面で不利です。

<br>

#### そのため、LINQ を使う前に以下のルールを考える必要があります。
<br>

## 使用時ルール
> 1. すばやい実装が必要か (プロトタイプ開発、TDD)? - <span style="color:green">LINQ を使う</span>
> 2. 性能に敏感でないコードか? - <span style="color:green">LINQ を使う</span>
> 3. LINQ の利便性や可読性が本当に必要か? - <span style="color:green">LINQ を使う</span>
> 4. 毎フレーム呼ばれる、または性能クリティカルな箇所か? - <span style="color:red">LINQ は使わない</span>

<br>
<br>

## LINQ パフォーマンスベンチマーク
> * ベンチマークライブラリ: [BenchMark](https://github.com/dotnet/BenchmarkDotNet)
> * テストコード: [TestCode](https://github.com/jamesvickers19/dotnet-linq-benchmarks)
> * 元記事: [LinqPerformance](https://medium.com/swlh/is-using-linq-in-c-bad-for-performance-318a1e71a732)

<br>
<br>

## ベンチマーク - 反復処理
> 年齢 18 歳未満の Customer 数を返す

<div class="code-compare">
  <div class="code-compare-pane">
    <div class="code-compare-label label-before">For / Foreach</div>
    <div class="highlight">
<pre><code class="language-csharp">// 性能: 高速 (GC なし)
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
<pre><code class="language-csharp">// 性能: 低速 (GC 発生)
// Count() は内部で
// シーケンス全体を走査する
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

for/foreach と比べると、LINQ には若干のオーバーヘッド (機能実行に伴う追加の時間・メモリ・リソース) があります。  
フィルタ後のカウントは比較的 for に近いですが、単純に要素数を返す `Count` は性能低下が大きいです。

<br>
<br>

## ベンチマーク - フィルタリング
> 年齢 18 歳以上の顧客配列サブセットを返す

1. For / Foreach
<img src="/assets/img/post/linq/linq04.png" width="1920px" height="1080px" title="256" alt="linq4">

2. LINQ
<img src="/assets/img/post/linq/linq05.png" width="1920px" height="1080px" title="256" alt="linq5">

<img src="/assets/img/post/linq/linq06.png" width="1920px" height="1080px" title="256" alt="linq6">

for/foreach 実装と非常に近い性能です。for/foreach より約 4ms 遅い結果でした。

<br>
<br>

##### 実際に RaycastAll でフィルタ後に tag チェックへ使ったコード
<img src="/assets/img/post/linq/linq07.png" width="1920px" height="1080px" title="256" alt="linq7">

フィルタリングのようなケースでは、通常の for/foreach よりも簡潔で可読性の高いコードにできます。

<br>

## ベンチマーク - 変換
> 年齢を年ではなく月で表現した顧客リストを返す

1. For / Foreach
<img src="/assets/img/post/linq/linq08.png" width="1920px" height="1080px" title="256" alt="linq8">

2. LINQ
<img src="/assets/img/post/linq/linq09.png" width="1920px" height="1080px" title="256" alt="linq9">

<img src="/assets/img/post/linq/linq10.png" width="1920px" height="1080px" title="256" alt="linq10">

<br>
<br>

## LINQ はどれだけ GC を生成するか?
> テスト条件は下記リンク参照
* 元記事: [Just How Much Garbage Does LINQ Create?](https://www.jacksondunstan.com/articles/4840)

#### 結果
1. GC Alloc Count
<img src="/assets/img/post/linq/linq11.png" width="1920px" height="1080px" title="256" alt="linq11">
<img src="/assets/img/post/linq/linq12.png" width="1920px" height="1080px" title="256" alt="linq12">
<br>
<br>

## Microsoft Docs の Unity 向けパフォーマンス推奨
[Unity に対するパフォーマンス推奨事項](https://learn.microsoft.com/ko-kr/windows/mixed-reality/develop/unity/performance-recommendations-for-unity?tabs=openxr)

<img src="/assets/img/post/linq/linq13.png" width="1920px" height="1080px" title="256" alt="linq13">

<br>
<br>

## LINQ vs For - パフォーマンス比較チャート

<div class="chart-wrapper">
  <div class="chart-title">相対実行時間比較 (低いほど高速、for = 1.0 基準)</div>
  <canvas id="linqBenchChart" class="chart-canvas" height="220"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'linqBenchChart',
  type: 'bar',
  data: {
    labels: ['反復処理 (Count)', 'フィルタリング (Where)', '変換 (Select)'],
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
        title: { display: true, text: '相対実行時間 (倍率)' }
      }
    }
  }
});
</script>

## 結論
1. LINQ の `Count` はかなり遅い。
2. フィルタリング (`Where`) と変換 (`Select`) は性能面で `for` とほぼ同等。
3. 1〜2 行の非常に簡潔なコードが書ける。
4. デバッグはやや難しい。
5. GC 発生があるため、乱用すると厳しくなる。
6. 毎フレーム呼び出しや性能影響が大きい箇所では使わないこと。
