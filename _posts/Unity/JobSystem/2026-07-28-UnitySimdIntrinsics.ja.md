---
title: "SIMDを理解する - ベクトルレジスタの原理からUnity Burst Intrinsicsまで"
lang: ja
date: 2026-07-28 10:00:00 +0900
categories: [Unity, JobSystem]
tags: [simd, vector, intrinsics, neon, avx2, burst, unity-mathematics, vectorization, optimization, unity]
toc: true
toc_sticky: true
image: /assets/img/og/jobsystem.png
chart: true
difficulty: intermediate
prerequisites:
  - /posts/UnityJobSystemBurst/
  - /posts/SoAvsAoS/
tldr:
  - SIMDはベクトルレジスタ1つに複数の値を載せ、1命令で同時に演算するCPUの機能です。ARM NEONは128bitでfloat 4個、x86 AVX2は256bitで8個を一度に処理します
  - SIMDはGPUのような別デバイスではなく、CPUコア内部の実行ポートです。オフロードコストが0なので、マイクロ秒単位の処理にも使えるという点がGPUコンピュートとの決定的な違いです
  - i9-14900Kを含むIntelのコンシューマCPUにAVX-512はありません（AVX2 256bitまで）。Zen 5はネイティブ512bitに対応し、RadeonはCUあたりSIMD32ユニット2個で構成されたSIMDマシンそのものです
  - 64bit CPUにSIMDは必ずあります - x86-64はSSE2、AArch64はNEONがアーキテクチャの必須仕様です。UnrealのVectorRegister・ISPC、Jolt物理（Horizon Forbidden West）、Unity DOTSの商用ゲームまで、業界での検証も済んだ技法です
  - 明示的なSIMDループはいつでも同じ5段階です - 定数のブロードキャスト、ベクトル幅単位の走査、レーン並列演算、スカラーへのリダクション、余りの端数処理
  - .NET 10 + Apple M4 Proでの実測結果、float 100万個の合算はスカラー比3.6倍、一致カウントは2.7倍速くなりました。どちらもヒープ割り当ては0です
  - Unityで信頼できるSIMD経路はBurstだけです。基本は自動ベクトル化 + Unity.Mathematicsで、Burst Inspectorで検証したボトルネックにのみUnity.Burst.Intrinsicsのv128を使います
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

## 序論：SIMDは本当に専門家専用の技術か

Ghosttyターミナルを作ったMitchell Hashimotoが、最近「SIMDはすべてのプログラマが知っておくべき日常的な最適化手段だ」という記事を公開しました。Ghosttyのコードポイント検索ループをAVX2で書き直したところ約5倍速くなり、そのコードの構造はアセンブリの魔法ではなく、誰でも真似できる定型化された5段階のパターンだった、というのが要旨です。

> Mitchell Hashimoto, *"SIMD Basics"* — <https://mitchellh.com/writing/simd-basics>

このシリーズでSIMDはすでに何度も登場しています。[Burst Compiler 深掘り編](/posts/BurstCompilerDeepDive/)ではLLVMのLoop Vectorizerが**コンパイラ自身で**ループをベクトル化する過程を扱い、[SoA vs AoS編](/posts/SoAvsAoS/)ではベクトル化しやすいメモリレイアウトを扱いました。ところが2編とも1つの問いを飛ばしています。**SIMD命令がハードウェアで正確に何をするから速くなるのか**、そして**自動ベクトル化が失敗したとき自分で書くにはどうするのか**です。

今回の目標は3つです。

1. SIMDをベクトルレジスタとレーンのレベルで理解し、実際のハードウェア（Intel i9、Ryzen、Apple M、Radeon）でSIMDがどんな形で存在するのかを確認します
2. 明示的なSIMDループの5段階構造をC#の`Vector<T>`で自分で書いて実測します
3. その知識をUnityに持ち込み、自動ベクトル化 → Unity.Mathematics → Burst Intrinsicsへとつながる3階層の選択基準を整理します

計測は.NET 10 + Apple M4 ProでBenchmarkDotNetを使い、自分で実行した値です。

---

## Part 1: SIMDがハードウェアで行うこと

### スカラー命令とベクトル命令

SIMDは**S**ingle **I**nstruction, **M**ultiple **D**ataの略です。名前のとおり命令（instruction）は1つなのに、その命令が処理するデータは複数あります。

CPUには一般演算に使う汎用レジスタ（Arm64基準で`x0`~`x30`、64bit）のほかに、**ベクトルレジスタ**（`v0`~`v31`、128bit）が別にあります。`float`は32bitなので128bitのベクトルレジスタ1つに4個入り、こうして区切られた各枠を**レーン（lane）**と呼びます。ベクトル加算命令1つは、2つのレジスタの同じ位置のレーン同士で4組の加算を同時に実行します。

<div class="sml-wrap">
  <div class="sml-grid">
    <div class="sml-col">
      <div class="sml-head sml-head-scalar">スカラー - 命令4個</div>
      <div class="sml-row">
        <div class="sml-reg"><span class="sml-lane">a[i]</span></div>
        <span class="sml-op">+</span>
        <div class="sml-reg"><span class="sml-lane">b[i]</span></div>
        <span class="sml-op">=</span>
        <div class="sml-reg"><span class="sml-lane sml-lane-res">c[i]</span></div>
      </div>
      <div class="sml-loop">&#8635; i = 0, 1, 2, 3 - 同じ命令を4回反復</div>
      <code class="sml-asm">fadd s0, s1, s2</code>
    </div>
    <div class="sml-col">
      <div class="sml-head sml-head-simd">SIMD - 命令1個</div>
      <div class="sml-row">
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">a[0]</span><span class="sml-lane">a[1]</span><span class="sml-lane">a[2]</span><span class="sml-lane">a[3]</span>
        </div>
        <span class="sml-op">+</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane">b[0]</span><span class="sml-lane">b[1]</span><span class="sml-lane">b[2]</span><span class="sml-lane">b[3]</span>
        </div>
      </div>
      <div class="sml-row sml-row-eq">
        <span class="sml-op">=</span>
        <div class="sml-reg sml-reg4">
          <span class="sml-lane sml-lane-res">c[0]</span><span class="sml-lane sml-lane-res">c[1]</span><span class="sml-lane sml-lane-res">c[2]</span><span class="sml-lane sml-lane-res">c[3]</span>
        </div>
      </div>
      <div class="sml-loop">128bitレジスタの4レーンを同時に演算</div>
      <code class="sml-asm">fadd v0.4s, v1.4s, v2.4s</code>
    </div>
  </div>
  <p class="sml-cap">同じ加算4個を処理する2つの方法（Arm64 NEON基準）</p>
</div>

<style>
.sml-wrap{margin:2rem 0}
.sml-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.sml-col{border-radius:14px;padding:1.1rem 1rem 1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15)}
.sml-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13.5px;font-weight:700;color:#fff;margin-bottom:1rem}
.sml-head-scalar{background:linear-gradient(135deg,#ef9a9a,#c62828)}
.sml-head-simd{background:linear-gradient(135deg,#81c784,#2e7d32)}
.sml-row{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:.5rem;flex-wrap:nowrap}
.sml-row-eq{margin-top:.1rem}
.sml-reg{display:flex;border:1.5px solid #90a4ae;border-radius:6px;overflow:hidden}
.sml-lane{display:flex;align-items:center;justify-content:center;min-width:40px;height:32px;font-size:12px;font-weight:600;background:#e3f2fd;color:#1565c0;border-right:1px dashed #90a4ae;padding:0 4px}
.sml-lane:last-child{border-right:none}
.sml-lane-res{background:#e8f5e9;color:#2e7d32}
.sml-op{font-size:16px;font-weight:700;color:#546e7a}
.sml-loop{text-align:center;font-size:12px;color:var(--text-muted-color,#6c757d);margin:.4rem 0}
.sml-asm{display:block;text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);background:rgba(128,128,128,.08);border-radius:6px;padding:3px 6px}
.sml-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sml-lane{background:#1a2a3a;color:#90caf9;border-right-color:#546e7a}
[data-mode="dark"] .sml-lane-res{background:#1a3320;color:#a5d6a7}
[data-mode="dark"] .sml-reg{border-color:#546e7a}
[data-mode="dark"] .sml-op{color:#b0bec5}
@media(max-width:768px){.sml-grid{grid-template-columns:1fr}}
</style>

### ベクトル幅 - プラットフォームごとに異なる理論上の上限

1命令が何個の値を処理するかは、命令セットが提供するベクトルレジスタの幅が決めます。

| 命令セット | レジスタ幅 | floatレーン | 主なプラットフォーム |
|------------|-----------|-----------|------------|
| **ARM NEON** | 128bit | 4個 | すべてのモバイル機器、Apple Silicon、Nintendo Switch |
| **x86 SSE4** | 128bit | 4個 | x86-64共通のベースライン |
| **x86 AVX2** | 256bit | 8個 | 2013年以降のデスクトップ、PS5、Xbox Series |
| **x86 AVX-512** | 512bit | 16個 | 一部のサーバー・最新デスクトップCPU |

ゲームプログラマの立場でこの表の結論は1つです。**クロスプラットフォームの保守的な基準線は128bit、つまり「float 4個 = 理論上4倍」**という点です。モバイルターゲットならNEON 128bitで固定です。デスクトップは事情が少しましです - Burstの64bitデスクトップ既定設定はSSE2とAVX2の2種類をコンパイルしておき、ランタイムにCPUを見て選ぶ（runtime dispatch）ので、AVX2に対応するCPUでは256bitが自動的に活用されます。AVX-512はゲームの配布対象から事実上外しても構いません。

### なぜいつも4倍にならないのか

レーンが4個だからといって、どんなコードでも4倍になるわけではありません。SIMDが利益を出すには3つの前提が必要です。

- **連続メモリ**：ベクトルロード命令はメモリから連続した128bitをまとめて取ってきます。データが散らばっているとレーンを埋めるコストが演算の利得を食い潰します
- **同一演算**：4つのレーンには同じ命令が適用されます。要素ごとに違う処理が必要なら、SIMDモデル自体が成立しません
- **分岐の最小化**：レーンごとの`if`は存在しません。条件処理は比較マスクと算術に置き換える必要があります（Part 3で実際にやってみます）

この3つの前提をコード構造で強制するのが、まさに[SoAレイアウト](/posts/SoAvsAoS/)です。「SoAがSIMDに有利だ」という前編の結論は、ベクトルロードが連続した128bitを要求するというハードウェア制約の、ソフトウェア側での表現だったわけです。

---

## Part 2: 実際のハードウェアのSIMD - i9、Ryzen、Apple M、そしてRadeon

### 専用パイプラインはあるのか - いいえ、コア内部の実行ポートです

「CPU→GPUのようにSIMDにも専用パイプラインがあるのか」という問いにまず答えると、**SIMDは別のデバイスや転送経路を持ちません**。ベクトルユニットはCPUコア内部の実行ポートの一部です。命令フェッチ・デコード・スケジューラといったフロントエンドをスカラー命令とそのまま共有し、スケジューラが命令の種類を見て整数ALUポートに送るかベクトルFMAポートに送るかを決めるだけです。データも同じL1キャッシュから直接読みます。

<div class="shw-wrap">
  <div class="shw-grid">
    <div class="shw-panel">
      <div class="shw-head shw-head-cpu">CPUコア内部 - SIMDは実行ポート</div>
      <div class="shw-box shw-box-wide">フロントエンド（フェッチ・デコード）</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">スケジューラ - 命令の種類でポート割当</div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-ports">
        <div class="shw-box shw-box-scalar">スカラー<br/>ALUポート</div>
        <div class="shw-box shw-box-vec">ベクトルFMA<br/>ポート&#215;2</div>
      </div>
      <div class="shw-varrow">&#8595;</div>
      <div class="shw-box shw-box-wide">L1キャッシュ（共有）</div>
      <div class="shw-note">オフロードコスト0 - µs単位の処理にも適用可能</div>
    </div>
    <div class="shw-panel">
      <div class="shw-head shw-head-gpu">GPU - 別デバイス</div>
      <div class="shw-box shw-box-wide">CPU - コマンドバッファ記録</div>
      <div class="shw-varrow shw-varrow-cost">&#8595; PCIe転送 + ディスパッチ遅延</div>
      <div class="shw-box shw-box-gpu">GPU<br/><span class="shw-sub">CU &#215; 数十個、CUごとにSIMD32ユニット2個</span></div>
      <div class="shw-varrow shw-varrow-cost">&#8595; 結果readback（同期待ち）</div>
      <div class="shw-box shw-box-wide">CPU - 結果受信</div>
      <div class="shw-note">往復遅延は数十µs~ms - 大量処理専用</div>
    </div>
  </div>
  <p class="shw-cap">同じ「並列演算」でも位置が違います - CPU SIMDはコアの中、GPUはバスの向こう側</p>
</div>

<style>
.shw-wrap{margin:2rem 0}
.shw-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:740px;margin:0 auto}
.shw-panel{border-radius:14px;padding:1rem;box-shadow:0 2px 12px rgba(0,0,0,.08);background:var(--card-bg,#fff);border:1px solid rgba(128,128,128,.15);display:flex;flex-direction:column}
.shw-head{text-align:center;border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700;color:#fff;margin-bottom:.8rem}
.shw-head-cpu{background:linear-gradient(135deg,#64b5f6,#1565c0)}
.shw-head-gpu{background:linear-gradient(135deg,#ba68c8,#6a1b9a)}
.shw-box{border-radius:8px;padding:.5rem .6rem;text-align:center;font-size:12px;font-weight:600;background:#eceff1;color:#37474f;line-height:1.5}
.shw-box-wide{width:100%}
.shw-ports{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.shw-box-scalar{background:#f5f5f5;color:#546e7a}
.shw-box-vec{background:#e8f5e9;color:#2e7d32;border:1.5px solid #66bb6a}
.shw-box-gpu{background:#f3e5f5;color:#6a1b9a;border:1.5px solid #ba68c8;padding:.7rem .6rem}
.shw-sub{font-size:11px;font-weight:500}
.shw-varrow{text-align:center;font-size:13px;color:#90a4ae;padding:2px 0}
.shw-varrow-cost{color:#e65100;font-size:11.5px;font-weight:600}
.shw-note{text-align:center;font-size:11.5px;color:var(--text-muted-color,#6c757d);margin-top:.7rem;font-style:italic}
.shw-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .shw-box{background:#2a2a2e;color:#cfd8dc}
[data-mode="dark"] .shw-box-scalar{background:#26262a;color:#90a4ae}
[data-mode="dark"] .shw-box-vec{background:#1a3320;color:#a5d6a7;border-color:#4caf50}
[data-mode="dark"] .shw-box-gpu{background:#31173a;color:#ce93d8;border-color:#8e24aa}
[data-mode="dark"] .shw-varrow-cost{color:#ffcc80}
@media(max-width:768px){.shw-grid{grid-template-columns:1fr}}
</style>

「実行ポート」という位置がSIMDの性格を決めます。別デバイスではないので**起動コストが0**です。GPUコンピュートはコマンドバッファ記録 → ディスパッチ → 結果readbackの往復が最低でも数十マイクロ秒からミリ秒単位なので、小さな処理では割に合いませんが、SIMDはループ1つをベクトル化するのに何の準備コストもかからないため、マイクロ秒単位の処理にもそのまま利得が出ます。代わりにコアのリソースを使うので、並列性の規模はコア数 × レーン数に制限されます。

ただし「タダの実行ポート」にも歴史的な例外が1つありました。初期のAVX-512実装（Skylake-X）は512bitユニットを回すとき電力の限界からコアクロックを大きく下げ、ベクトルコードが同じコアのスカラーコードまで遅くする副作用がありました。最新の実装ではこの問題が大きく減り、Zen 5（Ryzen 9950X）はAVX-512の電力ウイルス負荷でもクロック低下が5.7→5.3GHzと約10%にとどまります。

### ゲームPCの現在地 - i9にAVX-512はない

「Intel i9でSIMDが使えるか」への答えは「AVX2までは確実に、AVX-512はなし」です。2026年現在の主要なゲーム用CPUのSIMD対応状況です。

| CPU | 最大SIMD | ベクトル幅 | ベクトルレジスタ容量 | 備考 |
|-----|----------|--------|------------------|------|
| Intel i9-14900K (Raptor Lake) | AVX2 | 256bit | YMM 16個 = 512B | AVX-512ハードウェアはあるがヒューズで無効 |
| Intel Core Ultra 9 285K (Arrow Lake) | AVX2 | 256bit | YMM 16個 = 512B | コンシューマラインのAVX-512非対応が継続 |
| Intel Nova Lake (2026予定) | AVX10.2 | 512bit | ZMM 32個 = 2KB | P・Eコアとも512bit対応を予告 |
| AMD Ryzen 9 9950X (Zen 5) | AVX-512 | 512bit | ZMM 32個 = 2KB | ネイティブ512bitデータパス（Zen 4は256bitダブルポンプ） |
| Apple M4 | NEON | 128bit | V 32個 = 512B | 幅の代わりにパイプ数（Pコアあたり4個）でスループット確保 |

この表でゲーム開発者が覚えておくべきは順位表ではなく**経緯**です。Intelは第11世代（Rocket Lake）でコンシューマ向けAVX-512に対応しましたが、第12世代（Alder Lake）でEコアとの命令セット不一致のため無効化し、以降の世代でもコンシューマラインには戻っていません。逆にAMDはZen 4からAVX-512を入れ、Zen 5で完全な512bitに拡張しました。だから「最近のデスクトップならAVX-512は使えるだろう」という仮定は市場の半分で外れます - 配布対象全体をカバーする安全線はAVX2（256bit）です。Burstがデスクトップの既定設定でSSE2・AVX2の2種類をコンパイルしてランタイムに選ぶ方式を採ったのも、まさにこの対応の分断のためです。

「容量」の観点で見ると、ベクトルレジスタファイルはキロバイト単位と小さいです。AVX2のYMMレジスタ16個を全部合わせても512バイト、AVX-512のZMM 32個でも2KBです。ベクトルレジスタはデータを蓄えておく倉庫ではなく、**L1キャッシュから流れ込むデータが通過する窓口**であり、だからこそPart 1の「連続メモリ」という前提が再び重要になります。窓口がいくら広くても供給が途切れれば意味がありません。

幅がすべてではないということも、この表が示しています。実効スループットは**幅 × コアあたりのベクトルポート数**です。i9のPコアは256bit FMAポートが2個なので、サイクルあたりFP32基準で8レーン × 2ポート × 2演算（積+和）= 32 FLOPであり、Apple M4のPコアは128bitパイプ4個なので4レーン × 4パイプ × 2演算 = やはり32 FLOPです。NEONが「幅が半分だから遅い」という直感は、ポート数を忘れた計算です。

### SIMDがまったくないCPUは - 64bitなら必ずあります

対応の分断の話をすると「ではSIMD自体がないCPUもあるのではないか」という心配がついてきますが、64bitを配布対象にする限りそんなCPUはありません。SIMDの**有無**はアーキテクチャ標準が保証するからです。

- **x86-64**：SSE2（128bit）がアーキテクチャの必須仕様です。2003年の最初のx86-64 CPUから例外なく搭載され、コンパイラは通常の`float`演算すらx87ではなくSSEレジスタでコンパイルします
- **AArch64（64bit ARM）**：NEON（AdvSIMD）が必須仕様です。すべての64bitスマートフォン・タブレット・Apple Siliconが該当します
- **例外は過去と組み込みにあります**：32bit時代のARMv7ではNEONがオプション仕様だったため、これを外したチップ（初期のAndroidタブレットに使われたNVIDIA Tegra 2が有名です）が実際にあり、Cortex-M系のマイクロコントローラには今もベクトルユニットがありません

実はPart 1の図にこの保証がすでに隠れていました。スカラー命令`fadd s0, s1, s2`の`s0`は別のスカラーレジスタではなく、**ベクトルレジスタ`v0`の下位32bit**です。64bit CPUではスカラーの浮動小数点コードすらベクトルレジスタファイルの上で動いており、SIMDを使うということは、すでに敷かれているハードウェアの残りのレーンを使い切る作業に近いのです。ですから心配すべきは「あるか」ではなく、先の表が示した「幅はいくつか」の1点だけです。

### 最低スペック表の正体 - 幅の仮定が外れるとIllegal Instruction

その「幅」の仮定が外れるとどうなるかも見ておくべきです。結果は性能低下ではなく**即死**です。CPUがデコードできない命令に出会うとIllegal Instruction例外が発生し、プロセスがその場で終了します。上位の命令セットでビルドされたゲームを旧型CPUで実行すると、まさにこのクラッシュが起き、実際の事故事例も複数あります。

- **Cyberpunk 2077**（2020） - 実行ファイルにAVX命令が含まれ、AVX非対応CPU（AMD Phenom系など）でクラッシュ。ホットフィックス1.05でAVXの使用を取り除いて解決しました
- **Helldivers 2**（2024） - アップデートでAVX2が事実上必須となり、2013年より前のCPUを使うユーザーのゲームが一夜にして起動不可になった事件
- ソニー傘下のPC移植スタジオNixxesは、「このゲームはAVX2対応CPUが必要です」という公式のエラー案内ページまで運用しています

ゲームの最低スペック表のCPUモデル名は、事実上これを意味している場合が多いです。「Core i3-8100以上」という表記はクロックが足りないという意味ではなく、**命令セットの世代を指定している**に近いのです。

開発者側の標準的な解決策が、先に触れた**ランタイムディスパッチ**です。SSE2用とAVX2用のコードを両方とも実行ファイルに入れ、起動時にCPUIDでCPUの対応可否を確認して選ぶ方式で、Burstのデスクトップ既定設定（SSE2+AVX2の2種類をコンパイル）がまさにこれです。CyberpunkとHelldivers 2は、ディスパッチなしに上位命令を埋め込んで事故になったケースです。一方コンソールはハードウェアが固定なので（PS5・Xbox SeriesのZen 2はAVX2を保証）AVX2をハードコードしても安全です - コンソールゲームのPC移植でとりわけこの問題が起きる理由です。

### RadeonもSIMDなのか - GPUはSIMDで作られた機械です

「RadeonのようなGPUにもSIMDがあるのか」という問いは、方向を逆にすると正確になります。GPUにSIMDが「ある」どころか、**GPUは最初からSIMDユニットを大量に積み上げて作られた機械**です。

AMD RDNAアーキテクチャのCompute Unit（CU）1つは**SIMD32ユニット2個**で構成されます。SIMD32ユニットは32本のレーンが毎サイクル同じ命令を実行する、CPUのベクトルユニットの拡大版です。マーケティング用語の「ストリームプロセッサ64個」がまさにこの32レーン × 2ユニットを言い換えたもので、Radeon RX 7900 XTXのCU 96個を換算するとFP32レーンは6,144本になります。CPUコア1つの8~16レーンとは3桁の差です。

ところがGPUでは誰もintrinsicを使いません。プログラミングモデルが違うからです。

- **CPU SIMD**：プログラマがレーンを直接意識します。ブロードキャスト・マスク・リダクションをコードで書きます（Part 3の5段階）
- **GPU（SIMT）**：プログラマは「スレッド1本」のスカラーコード（HLSLなど）を書き、ハードウェアがスレッド32本をwavefrontにまとめてSIMD32ユニットのレーンに自動で割り当てます
- **分岐処理**：スレッドごとに`if`の方向が分かれると（divergence）、ハードウェアが両方の経路を実行してマスクで結果を選び出します - Part 3で私たちが手で書くマスク算術を、ハードウェアが代わりにやってくれるわけです

つまりSIMTはSIMDハードウェアの上に被せた利便レイヤであり、「分岐はマスクになる」というコストモデルはCPUとGPUで同一です。GPUシェーダで分岐が高くつくという常識の根は、CPU SIMDにレーンごとの`if`がないという事実と同じところにあります。

Unityの文脈でこの選択肢はCompute Shader vs Burst Jobです。判断基準は前節の図がすでに示しています - データがすでにGPUにあるか（レンダリングパイプラインとつながっている）、作業量が往復遅延を相殺するほど大きければCompute Shader、結果を毎フレームCPUロジックが消費する必要があり、作業がマイクロ秒~数百マイクロ秒の規模ならCPU SIMD（Burst）が適切です。6,144本のレーンが8本のレーンにいつも勝つわけではありません。勝つには、まずデータがバスを渡らなければならないからです。

---

## Part 3: 明示的なSIMDループの5段階構造

### いつでも同じ5つの段階

Mitchell Hashimotoの記事が良いのは、SIMDコードが言語と命令セットを問わず**常に同じ5段階**で構成されるという点を突いているからです。Zigで書こうと、Cのintrinsicで書こうと、以下で見るC#の`Vector<T>`で書こうと、構造は同じです。

<div class="sm5-wrap">
  <div class="sm5-flow">
    <div class="sm5-step">
      <div class="sm5-num">1</div>
      <div class="sm5-name">ブロードキャスト</div>
      <div class="sm5-desc">定数を全レーンに複製</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">2</div>
      <div class="sm5-name">ベクトル走査</div>
      <div class="sm5-desc">配列をベクトル幅で進む</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step sm5-step-core">
      <div class="sm5-num">3</div>
      <div class="sm5-name">並列演算</div>
      <div class="sm5-desc">全レーンに1命令を適用</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">4</div>
      <div class="sm5-name">リダクション</div>
      <div class="sm5-desc">レーン結果を1スカラーに</div>
    </div>
    <div class="sm5-arr">&#8594;</div>
    <div class="sm5-step">
      <div class="sm5-num">5</div>
      <div class="sm5-name">端数処理</div>
      <div class="sm5-desc">残りはスカラーループ</div>
    </div>
  </div>
  <p class="sm5-cap">明示的なSIMDループの5段階 - 成否を分けるのは③の並列演算の段階</p>
</div>

<style>
.sm5-wrap{margin:2rem 0}
.sm5-flow{display:flex;align-items:stretch;justify-content:center;gap:4px;max-width:760px;margin:0 auto;flex-wrap:nowrap}
.sm5-step{flex:1;min-width:0;border-radius:12px;padding:.8rem .5rem;text-align:center;background:linear-gradient(160deg,#e3f2fd,#bbdefb);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.sm5-step-core{background:linear-gradient(160deg,#fff8e1,#ffe082);box-shadow:0 2px 10px rgba(230,150,0,.25)}
.sm5-num{width:24px;height:24px;border-radius:50%;background:#1565c0;color:#fff;font-size:12.5px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto .4rem}
.sm5-step-core .sm5-num{background:#e65100}
.sm5-name{font-size:13px;font-weight:700;color:#0d47a1;margin-bottom:.25rem}
.sm5-step-core .sm5-name{color:#bf360c}
.sm5-desc{font-size:11px;line-height:1.5;color:#37474f}
.sm5-arr{display:flex;align-items:center;font-size:15px;color:#90a4ae;font-weight:700}
.sm5-cap{text-align:center;margin-top:.75rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sm5-step{background:linear-gradient(160deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sm5-step-core{background:linear-gradient(160deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sm5-name{color:#90caf9}
[data-mode="dark"] .sm5-step-core .sm5-name{color:#ffcc80}
[data-mode="dark"] .sm5-desc{color:#b0bec5}
@media(max-width:768px){.sm5-flow{flex-direction:column;align-items:stretch}.sm5-arr{justify-content:center;transform:rotate(90deg);padding:2px 0}}
</style>

### C# Vector&lt;T&gt;で自分で書いてみる

.NETの`System.Numerics.Vector<T>`は「現在のハードウェアのベクトル幅」を抽象化した型です。NEONでは`Vector<int>.Count`が4、AVX2では8になり、JITが各演算をそのプラットフォームのベクトル命令に変換します。Ghosttyのコードポイント検索と同じ構造である「配列から特定の値の個数を数える」を5段階そのままに移すと、こうなります。

```csharp
using System.Numerics;

int CountTarget(int[] data, int target)
{
    // ① ブロードキャスト — targetを全レーンに複製
    var targetVec = new Vector<int>(target);
    var acc = Vector<int>.Zero;

    int width = Vector<int>.Count;   // NEONでは4
    int i = 0;

    // ② ベクトル走査 — 4個ずつ進む
    for (; i <= data.Length - width; i += width)
    {
        var chunk = new Vector<int>(data, i);

        // ③ 並列演算 — 一致レーンは-1（全ビット1）、不一致は0
        acc += Vector.Equals(chunk, targetVec);
    }

    // ④ リダクション — 4レーンの累積値を1つのスカラーに
    int count = -Vector.Sum(acc);

    // ⑤ 端数処理 — 4で割り切れない残り
    for (; i < data.Length; i++)
        if (data[i] == target) count++;

    return count;
}
```

③の段階がこのコードの核心です。スカラー版なら`if (data[i] == target) count++`と書くところですが、SIMDにはレーンごとの分岐がないので、**比較結果をマスクとして受け取り算術で処理**します。`Vector.Equals`は一致したレーンを`-1`（全ビットが1）、一致しなかったレーンを`0`で埋めたベクトルを返し、これをそのまま累積すると各レーンに「一致回数 × (-1)」が溜まります。④で符号を反転させれば総個数です。分岐がマスク算術に変わるこの変換が、SIMD的な考え方のすべてと言っても過言ではありません。

残りの段階は定型化されたボイラープレートです。①②⑤はどんなSIMDコードを書いても形はほぼ同じで、④のリダクションも`Vector.Sum`の1行です。つまり新しい問題に出会ったとき悩むべき部分は、「③を分岐なしで構成できるか」の1点に絞られます。

---

## Part 4: 実測 - スカラー vs Vector&lt;T&gt;

### 計測環境と対象

理論上の4倍が実際にはどのくらい出るのか、私の開発マシンで実測しました。

- **環境**：.NET 10.0.0、Apple M4 Pro、Arm64 RyuJIT（AdvSIMD）、BenchmarkDotNet v0.14.0、`[MemoryDiagnoser]`
- **データ**：要素100万個の配列（float合算 / int一致カウント、シード固定の乱数）
- **比較ペア**：単純なスカラーループ vs 上の5段階構造の`Vector<T>`ループ（`Vector<float>.Count` = 4）

合算側のコードはカウントよりさらに単純です。

```csharp
[Benchmark(Baseline = true)]
public float SumScalar()
{
    float sum = 0f;
    for (int i = 0; i < _floats.Length; i++)
        sum += _floats[i];
    return sum;
}

[Benchmark]
public float SumVector()
{
    var acc = Vector<float>.Zero;
    int width = Vector<float>.Count;
    int i = 0;
    for (; i <= _floats.Length - width; i += width)
        acc += new Vector<float>(_floats, i);   // 4レーン同時累積

    float sum = Vector.Sum(acc);                // リダクション
    for (; i < _floats.Length; i++)             // 端数
        sum += _floats[i];
    return sum;
}
```

### 結果

| ベンチマーク | Mean | スカラー比 | Allocated |
|----------|-----:|-----------:|----------:|
| SumScalar (float 100万) | 585.5 µs | 1.00x | 0 B |
| **SumVector** | **163.0 µs** | **3.59x 速い** | 0 B |
| CountScalar (int 100万) | 331.1 µs | 1.00x | 0 B |
| **CountVector** | **124.3 µs** | **2.66x 速い** | 0 B |

<div class="chart-wrapper">
  <div class="chart-title">スカラー vs Vector&lt;T&gt; - 100万要素の処理時間（Apple M4 Pro, .NET 10）</div>
  <canvas id="simdBenchJa" class="chart-canvas" height="260"></canvas>
</div>

<script>
window.chartConfigs = window.chartConfigs || [];
window.chartConfigs.push({
  id: 'simdBenchJa',
  type: 'bar',
  data: {
    labels: ['float 100万個の合算', 'int 100万個の一致カウント'],
    datasets: [
      {label:'スカラーループ',data:[585.5,331.1],backgroundColor:'rgba(244,67,54,0.75)',borderColor:'rgba(244,67,54,1)',borderWidth:1.5},
      {label:'Vector<T> (NEON 128bit)',data:[163.0,124.3],backgroundColor:'rgba(76,175,80,0.75)',borderColor:'rgba(76,175,80,1)',borderWidth:1.5}
    ]
  },
  options: {
    scales: {
      y: {beginAtZero:true,title:{display:true,text:'平均実行時間 (µs) — 低いほど速い'},grid:{color:'rgba(128,128,128,0.15)'}},
      x: {grid:{display:false}}
    },
    plugins: {
      legend:{position:'bottom',labels:{padding:16,usePointStyle:true,pointStyleWidth:10}},
      tooltip:{callbacks:{label:function(ctx){return ctx.dataset.label+': '+ctx.parsed.y.toFixed(1)+' µs';}}}
    },
    responsive: true,
    maintainAspectRatio: true
  }
});
</script>

### 数字の解釈 - なぜ3.6倍と2.7倍なのか

2つの結果で倍率が違う理由が、このベンチマークで一番学ぶことの多い部分です。

**合算が3.59倍と理論上限（4倍）に近い理由**は、スカラー合算が最悪の条件だからです。`sum += x`は直前の加算が終わらないと次の加算を始められない直列依存チェーンなので、スカラーループの速度は浮動小数点加算のレイテンシにそのまま縛られます。ベクトル版はこのチェーンを4レーンに分割するので、幅の分の利得がほぼそのまま出ます。

**カウントが2.66倍にとどまった理由**は逆に、スカラー側がすでにかなり速いからです。テストデータでの一致確率は1/256なので`if (data[i] == target)`の分岐はほぼ常に「不一致」と予測され、分岐予測が当たり続けるループではパイプラインが途切れません。相手が速いほど倍率は縮みます - SIMDの利得の幅は、ベクトルコードではなく**比較対象であるスカラーコードが何に縛られているか**が決めます。

2つの注意点も実測から一緒に見えてきます。

- **浮動小数点の合算順序が変わります。** スカラーは左から1つずつ、ベクトルは4レーンに分けて入れてから最後に合わせるので結合の順序が違い、浮動小数点加算は結合法則が成り立たないためビット単位で同じ結果は保証されません。Burstでリダクションのベクトル化に`FloatMode.Fast`が必要な理由（[深掘り編 Part 2](/posts/BurstCompilerDeepDive/)）が、まさにこれです
- **この数字はRyuJITのものです。** 同じ`Vector<T>`コードをUnityに持っていってもこの倍率は出ません。UnityのMonoランタイムは`Vector<T>`をハードウェアアクセラレーションなしにソフトウェアで処理し、IL2CPPもベクトル命令の生成を保証しません

2つ目の注意点が次のパートのテーマです。UnityでSIMDを使う道は別にあります。

---

## Part 5: UnityのSIMD経路 - 3階層のはしご

### UnityでSystem.Numerics.Vectorが答えにならない理由

UnityランタイムでSIMD命令が実際に生成される経路は、事実上Burstの1つだけです。

- **Mono**：`Vector<T>` APIは動作しますが、ハードウェアアクセラレーションがありません。レーンごとの演算をソフトウェアループで真似るので、かえってスカラーより遅くなることがあります
- **IL2CPP**：ILをC++に変換するだけで、`System.Numerics`型をベクトル命令として特別扱いしません。残るのはC++コンパイラの自動ベクトル化ですが、[深掘り編](/posts/BurstCompilerDeepDive/)で見たとおり自動ベクトル化は条件1つで壊れる脆い最適化です
- **Burst**：JobコードをLLVMで直接コンパイルしながらNEON/SSE/AVX命令を生成します。ベクトル化されたかどうかをBurst Inspectorで検証でき、`Loop.ExpectVectorized()`でコンパイル時に強制することもできます

### BurstはC#をどうやってベクトル命令に変えるのか

BurstがSIMDを作り出す過程は4段階に要約されます。

1. **収集**：`[BurstCompile]`が付いたJobのIL（中間言語）を集めます
2. **変換**：独自のフロントエンドがILを**LLVM IRへ直接変換**します。C++を経由するIL2CPPと分かれる地点がここです - C++ソースという中間段階がないので、型・エイリアシング情報が損失なくLLVMに渡ります
3. **最適化**：LLVMのパスが回ります。SROAが`float4`のような構造体を丸ごとベクトルレジスタに載せ、Loop Vectorizerがループをベクトル幅単位で書き直します
4. **コード生成**：ターゲット別のバックエンドがNEON/SSE2/AVX2の機械語を作ります。デスクトップではPart 2で見たとおりSSE2・AVX2の2種類 + ランタイムディスパッチです

このパイプラインにおけるBurstの決定的な武器は、コンパイル技術ではなく**Job構造がタダでくれるエイリアシング保証**です。Jobの`NativeArray`フィールドはSafety Systemが重ならないことを保証するので、Burstはすべての入出力をalias-freeとみなしてベクトル化できます。C++コンパイラが「この2つのポインタが同じメモリを指したらどうしよう」とベクトル化を諦める地点を、Burstはそのまま通り過ぎます - [深掘り編](/posts/BurstCompilerDeepDive/)で扱った「BurstがC++より速くなりうる理由」の核心です。

たとえば`float4`配列にスカラーを掛けるJob（すぐ後に2階層目の例として出てくる`ScaleJob`）がこのパイプラインを通ると、ループ本体は概念的に次の3行に圧縮されます。

```
ldr  q0, [x0, x2]          ; inputから128bit（float 4個）をロード
fmul v0.4s, v0.4s, v1.4s   ; 4レーン同時乗算 — scaleはv1にブロードキャストされる
str  q0, [x1, x2]          ; outputに128bitをストア
```

C#の1行（`output[i] = input[i] * scale`）がロード・演算・ストアの各1命令に落ちたわけです。これが実際に出たかを確認する場所がBurst Inspectorであり、LLVMパスごとの詳細とアセンブリの読み方は[深掘り編 Part 1・3](/posts/BurstCompilerDeepDive/)にあります。

そういうわけで、UnityでSIMD最適化をするということは、Burstの上でどこまで降りるかを選ぶ作業になります。選択肢は3つの階層です。

<div class="sbi-wrap">
  <div class="sbi-ladder">
    <div class="sbi-tier sbi-tier1">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge1">1層 - 基本</span> 自動ベクトル化</div>
      <div class="sbi-tier-body">[BurstCompile] + Job + NativeArrayだけでLLVM Loop Vectorizerに任せます。コードは普通のC#ループのままで、ほとんどの場合ここで終わるのが正常です。</div>
    </div>
    <div class="sbi-tier sbi-tier2">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge2">2層 - 推奨</span> Unity.Mathematics</div>
      <div class="sbi-tier-body">float4・int4を使うとBurstが型をベクトルレジスタに直接マッピングします。自動ベクトル化の成否への依存を減らしながら、コードは移植性を保ちます。</div>
    </div>
    <div class="sbi-tier sbi-tier3">
      <div class="sbi-tier-head"><span class="sbi-badge sbi-badge3">3層 - 最終手段</span> Unity.Burst.Intrinsics</div>
      <div class="sbi-tier-body">v128型とNEON/SSE intrinsicで命令を直接指定します。プラットフォーム別の分岐が必要になるので、Burst Inspectorで1層・2層の失敗を確認したボトルネックにのみ使います。</div>
    </div>
  </div>
  <div class="sbi-axis">
    <span>&#9650; 移植性・保守性</span>
    <span>制御力・確実性 &#9660;</span>
  </div>
  <p class="sbi-cap">Unity SIMDの3階層 - 下るほど確実になりますが、コードがプラットフォームに縛られます</p>
</div>

<style>
.sbi-wrap{margin:2rem 0}
.sbi-ladder{max-width:680px;margin:0 auto;display:flex;flex-direction:column;gap:.6rem}
.sbi-tier{border-radius:12px;padding:.9rem 1.1rem;box-shadow:0 2px 10px rgba(0,0,0,.07)}
.sbi-tier1{background:linear-gradient(135deg,#e8f5e9,#dcedc8);border-left:5px solid #2e7d32}
.sbi-tier2{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-left:5px solid #1565c0}
.sbi-tier3{background:linear-gradient(135deg,#fff8e1,#ffecb3);border-left:5px solid #e65100}
.sbi-tier-head{font-size:14px;font-weight:700;color:#263238;margin-bottom:.35rem}
.sbi-badge{display:inline-block;border-radius:12px;padding:2px 10px;font-size:11.5px;font-weight:700;color:#fff;margin-right:8px}
.sbi-badge1{background:#2e7d32}
.sbi-badge2{background:#1565c0}
.sbi-badge3{background:#e65100}
.sbi-tier-body{font-size:13px;line-height:1.7;color:#37474f}
.sbi-axis{max-width:680px;margin:.6rem auto 0;display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-muted-color,#6c757d)}
.sbi-cap{text-align:center;margin-top:.6rem;font-size:12.5px;color:var(--text-muted-color,#6c757d);font-style:italic}
[data-mode="dark"] .sbi-tier1{background:linear-gradient(135deg,#1a3320,#20401f)}
[data-mode="dark"] .sbi-tier2{background:linear-gradient(135deg,#1a2a3a,#12395c)}
[data-mode="dark"] .sbi-tier3{background:linear-gradient(135deg,#3a2e10,#4d3a08)}
[data-mode="dark"] .sbi-tier-head{color:#eceff1}
[data-mode="dark"] .sbi-tier-body{color:#b0bec5}
</style>

### 1層・2層 - 自動ベクトル化とUnity.Mathematics

1層と2層はこのシリーズですでに詳しく扱ったので、要点だけ再掲します。自動ベクトル化の成功・失敗の条件と、Burst Inspectorでアセンブリを確認するワークフローは[Burst Compiler 深掘り編 Part 3・4](/posts/BurstCompilerDeepDive/)にあります。2層の核心は、`float4`演算が自動ベクトル化を待つまでもなく、それ自体でベクトル命令にマッピングされるという点です。

```csharp
[BurstCompile]
struct ScaleJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float4> input;
    public NativeArray<float4> output;
    public float scale;

    // float4の乗算1つがNEONのfmul v0.4s命令1つにコンパイルされます
    public void Execute(int i) => output[i] = input[i] * scale;
}
```

注意すべきは`float3`です。4レーンのレジスタに3個しか入らないので1レーンが無駄になり、配列にすると16バイトのアラインメントもずれます。SIMDを意識したデータなら最初から`float4`で取るか、[SoAレイアウト](/posts/SoAvsAoS/)でx・y・zをそれぞれの配列に分離する方がよいです。

### 3層 - Unity.Burst.Intrinsicsで直接書く

自動ベクトル化が失敗し、`float4`でも表現できないパターン - 代表的にはPart 3の「マスク累積」のようなリダクション - はintrinsicで直接書きます。Part 3のカウントループを`Unity.Burst.Intrinsics`のNEON版に移すとこうなります。

```csharp
using Unity.Burst;
using Unity.Burst.Intrinsics;
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;
using static Unity.Burst.Intrinsics.Arm.Neon;

[BurstCompile]
unsafe struct CountTargetJob : IJob
{
    [ReadOnly] public NativeArray<int> data;
    public int target;
    public NativeReference<int> result;

    public void Execute()
    {
        int* p = (int*)data.GetUnsafeReadOnlyPtr();
        int count = 0;
        int i = 0;

        if (IsNeonSupported)   // コンパイル時定数 — ランタイム分岐コスト0
        {
            v128 targetVec = new v128(target);        // ① ブロードキャスト
            v128 acc = new v128(0);

            for (; i <= data.Length - 4; i += 4)      // ② ベクトル走査
            {
                v128 chunk = vld1q_s32(p + i);        //    128bitロード
                v128 mask  = vceqq_s32(chunk, targetVec); // ③ 一致レーン = -1
                acc = vsubq_s32(acc, mask);           //    -(-1) = +1 累積
            }
            count = vaddvq_s32(acc);                  // ④ 水平和でリダクション
        }

        for (; i < data.Length; i++)                  // ⑤ 端数 + NEON非対応フォールバック
            if (p[i] == target) count++;

        result.Value = count;
    }
}
```

構造がPart 3の`Vector<T>`版とまったく同じである点に注目してほしいです。`Vector.Equals`が`vceqq_s32`に、`Vector.Sum`が`vaddvq_s32`に変わっただけで、5段階はそのままです。明示的なSIMDの学習コストは命令名の暗記ではなくこの構造を一度体得することにあり、一度体得すればどのプラットフォームのintrinsicでも同じ枠に嵌め込めるようになります。

`IsNeonSupported`の分岐は[深掘り編](/posts/BurstCompilerDeepDive/)で扱ったコンパイル時評価のメカニズムのおかげでタダです。Burstはターゲットプラットフォームごとにコードを別々にコンパイルするので、ARMビルドにはNEON経路だけが残り、x86ビルドにはスカラーフォールバックだけが残ります。逆に言えばx86でもSIMDが欲しければ`X86.Sse2`経路を別途書かなければならないということであり、このプラットフォーム別の重複が3層の実質的な保守コストです。

---

## Part 6: ゲームソフトウェアのSIMD活用事例

UnityのBurstが特別な経路ではないことを示す一番よい方法は、他のエンジンと商用ゲームを覗いてみることです。結論から言うとSIMDはゲーム業界で検証の済んだ標準的な技法であり、エンジンごとに「どう使わせるか」の答えが違うだけです。

### Unreal Engine ① - VectorRegister、エンジン数学の土台

Unrealの数学ライブラリは最初からSIMDの上に立っています。核心は`VectorRegister4Float`型です。名前のとおりfloat 4個分のベクトルレジスタの抽象化であり、プラットフォーム別の実装がヘッダのレベルで分かれます - x86では`UnrealMathSSE.h`がSSE intrinsicで、ARMでは`UnrealMathNeon.h`がNEON intrinsicで、同じ関数群（`VectorAdd`、`VectorMultiplyAdd`、`VectorCompareGT`...）を実装します。

構造に見覚えがあるはずです。**Burstの`v128`とまったく同じ「薄い抽象化」パターン**です。違いは位置です - Unityで`v128`は最適化が必要な人が選択的に降りていく3層ですが、Unrealで`VectorRegister4Float`は`FMatrix`の乗算、`FTransform`の合成、クォータニオン補間といったエンジン数学の全体が常に踏んでいる土台です。Unrealのゲームは開発者がSIMDを1行も書かなくても、毎フレームのトランスフォーム計算ですでにSIMDの恩恵を受けています。

### Unreal Engine ② - ISPC、「CPUのシェーダ」

明示的なSIMDが必要なところで、Unrealが選んだ答えはintrinsicではなく**専用コンパイラ**です。UE 4.23から統合されたIntel ISPC（Implicit SPMD Program Compiler）は、C風の言語で「要素1つ」のコードを書けばコンパイラがSSE4・AVX2・NEON用のベクトルコードをそれぞれ生成してくれるツールで、Chaos物理・クロスシミュレーション・アニメーションシステムに使われています。

```c
/* ISPC — スレッド1本のように書くとレーン幅の分だけ並列実行されます */
export void Scale(uniform float input[], uniform float scale,
                  uniform float output[], uniform int count)
{
    foreach (i = 0 ... count)
        output[i] = input[i] * scale;   /* この1行がAVX2では8レーン */
}
```

`foreach`の中のコードはGPUシェーダのように「1要素の視点」で書きますが、実際にはベクトルのレーン幅単位で実行されます - Part 2で見たGPUのSIMTモデルを、CPUのベクトルユニットの上にソフトウェアで再現したものです。Unityとアプローチを比べるとこう整理できます。

| | Unity Burst | Unreal ISPC |
|---|------------|-------------|
| 言語 | C#のまま | 専用言語（C類似） |
| ベクトル化の主体 | LLVM自動ベクトル化 + 選択的intrinsic | コンパイラがSPMDモデルで常にベクトル化 |
| マルチターゲット | プラットフォーム別コンパイル（SSE2・AVX2ディスパッチ） | ISA別にコード生成後ランタイム選択 |
| 適用範囲 | Jobコード全体 | 物理・クロスなど指定モジュール |

アプローチは違いますが到達点は同じです。両エンジンとも「ゲームプレイのコードは触らず、大量データを回すシステム層だけをベクトル化する」という同じ結論に収束しました。

### 物理ミドルウェア - Jolt PhysicsとHorizon Forbidden West

エンジンの外の事例で最良のものは**Jolt Physics**です。Horizon Forbidden WestとDeath Stranding 2が使うオープンソースの物理エンジンで、x86ではSSE4.1からAVX-512まで、ARM64ではNEONまでをコンパイルターゲットとして対応します - 衝突検出と剛体ソルバのホットループがすべてSIMDの上にあります。

Guerrilla GamesがGDC 2022で公開した数値が、SIMDを含むデータ指向設計の効果を要約しています。商用の物理エンジンからJoltに置き換えた結果、**メモリと実行ファイルのサイズを減らしながらシミュレーション周波数を2倍に上げ、CPU時間はむしろ少なく使いました**。物理は「同一演算 × 大量の連続データ」パターンの教科書的な標本であり、この記事で扱った条件がすべて揃ったドメインです。

### Unity - 自社パッケージから商用ゲームまで

Unity側の事例でまず見るべきは、**Unity自身がPart 5の3階層をそのまま実践している**という点です。

- **Unity Physics**：DOTSベースのステートレス物理エンジンで、衝突検出・ソルバの全体がUnity.Mathematicsの上のBurst Jobです - 2層（SIMDフレンドリーな型 + 自動ベクトル化）の大規模な実戦です。JoltがC++ intrinsicでやったことを、UnityはC# + Burstでやったわけです
- **Unity.CollectionsのxxHash3**：ハッシュ関数1つに実装が2種類入っています。Unity.Mathematicsベースの汎用実装と、AVX2対応プラットフォームで使われる**Burst intrinsicsベースの実装**です。公式ドキュメントによればintrinsics実装が大きなデータで30~50%の追加利得を出します - 「検証したボトルネックにのみ3層へ降りる」という原則と、「降りるならプラットフォーム別に2種類を維持する」というコストの両方を示す標本です

商用ゲーム側の検証事例としてはV Rising（2022、ECSベースでリリース）とCities: Skylines IIがあります。特にCS2は都市全体の市民・交通シミュレーションをECS + Burstで回す、現時点で最大のDOTS商用ゲームです。

CS2には反面教師の教訓もあります。リリース直後の性能論争を分析した資料を見ると、ボトルネックはBurstでコンパイルされたシミュレーションではなく**GPUレンダリング側**（過剰な頂点数、LODの不備など）でした。シミュレーション層をSIMDでいくら速くしても、フレームタイムは一番遅いボトルネックが決めます - 次のパートで整理する「ボトルネックは演算か」という問いを、商用ゲームのスケールで示した事例です。

これらの事例を貫く共通点は、SIMDが**システム層に集中している**ということです。物理（Jolt・Chaos・Unity Physics）、アニメーション（ISPC）、トランスフォーム数学（VectorRegister）、ハッシュのようなユーティリティ（xxHash3）、大量シミュレーション（DOTS） - すべてエンジン・ミドルウェアのレベルであり、その上のゲームプレイコードはどの事例でもベクトル化の対象ではありません。Part 7の判断基準が、業界全体の実践と一致しているわけです。

---

## Part 7: 適用の判断 - どこに使い、どこに使わないか

### 優先順位はレイアウトが先

SIMDは最適化のはしごの最後の段に近いです。適用を検討する時点で、すでに2つが終わっていなければなりません。

1. **データが連続メモリにSoAで配置されているか。** 散らばった`GameObject`のフィールドを走査するコードは、そもそもベクトル化の対象ではありません。レイアウト転換だけでキャッシュ効率からの利得が先に出て、SIMDはその上に掛け算される項です
2. **ボトルネックは演算か。** データがキャッシュを外れるほど大きければボトルネックはメモリ帯域幅に移り、ALUを4倍に増やしてもデータ供給が追いつきません。私のベンチマークの100万個（4MB）はM4 ProのL2キャッシュに収まるサイズなので、演算ボトルネックが維持されたケースです

この2つの条件を通過する作業は、ゲームではかなり明確に決まっています。パーティクルシミュレーション、プロシージャルメッシュ生成、大量ユニットの移動・距離計算、オーディオDSPのような「同一演算 × 大量の連続データ」パターンです。逆に一般的なゲームプレイロジック - 状態分岐が多く、オブジェクトごとに処理が違うコード - は前提条件である「同一演算」から成立しないので、検討対象ではありません。元記事に「すべてのプログラマが知るべきというのは誇張だ」という反論コメントが付きましたが、ゲームプログラマに限れば反論側が正しいと思います。知っておくべき人は上のリストのシステムを作る人であり、残りはBurstの自動ベクトル化で十分です。

### SIMD以前の問い - データ構造がポインタを追いかけていないか

先の条件1（「SoAで配置されているか」）は、実はもっと難しい問いを隠しています。**そもそも配列で表現できるデータ構造なのか**です。ツリーやグラフのようにノードが互いを参照する構造は、SoAへ「配置を変える」程度では解決しません。

ポインタ追跡（pointer chasing）がベクトル化と相容れない理由は明確です。次に読むアドレスが**いま読んでいる値の中に入っている**からです。ロードが完了しなければ次のロードのアドレスが決まらないためメモリアクセスが直列に縛られ、ハードウェアプリフェッチャは次のアドレスを予測できず、ベクトルロードが要求する「連続した128bit」は最初から存在しません。Part 4でスカラー合算が遅かった理由は浮動小数点加算のレイテンシに縛られたことでしたが、ポインタ追跡は同じ直列依存が**メモリレイテンシ**（キャッシュミス時に数百サイクル）に掛かった形です。ここにSIMDを載せても意味がありません。ボトルネックが演算ではないからです。

解法はSIMDではなく**線形化**です。ポインタを配列インデックスに置き換え、ノードを連続した配列（アリーナ）に収める変換であり、RendelloがHNで共有した経験 - ヒープに散らばったポインタベースのツリーを線形配列構造に変えてキャッシュ効率を上げた事例 - がまさにこれです。

```csharp
/* Before - ポインタ追跡: ノードごとにキャッシュミス、ベクトル化は不可能 */
class Node { Node left, right; float bound; }

/* After - インデックス参照: ノードが一つの配列に連続し、走査が線形スキャンになる */
struct Node { int left, right; float bound; }   /* インデックスはNativeArray<Node>の添字 */
```

この変換はSIMDと無関係にも利得があります。インデックスは32bitなので64bitポインタよりノードが小さくなり、配列ごと直列化・コピー・再配置ができ、GCが追跡する参照もなくなります。Unityで`NativeArray`の中にツリーを収めたいなら、そもそもこの形以外に選択肢はありません。

さらに一歩進むと、この記事で最も直感に反する地点が現れます。**ベクトル幅がデータ構造の分岐数を変えます。** 二分木を線形化するところで止めず、子を4つ持つツリーとして設計し直すのです。ノード一つを検査するとき、子4つの境界を4レーンで一度に比較するためです。

Unity PhysicsのBVHがまさにそう作られています。`BoundingVolumeHierarchy.Node`のフィールドは`FourTransposedAabbs Bounds`と`int4 Data`で、子は最大4つです。名前の「Transposed」が肝心な部分です - AABB 4つを並べて置く代わりに、xの最小値4つ、yの最小値4つ…と軸ごとに転置して収めます。ノードの中でSoAをやったわけで、おかげで子4つとの交差判定がレーン4つ分の比較数回で終わります。**二分BVHではなく4-way BVHである理由が、アルゴリズムではなくレジスタ幅にあります。**

Rendelloの「データ表現は教条ではなくアクセスパターンに結びつくべきだ」という原則は、ゲームエンジンではここまで押し進められます。アクセスパターンがハードウェアに縛られている以上、表現も結局ハードウェアに縛られます。

だから「早すぎる最適化」という警戒は半分だけ正しいのです。**SIMDコードを後から載せるのは確かに早すぎる最適化ですが、データ構造を何にするかは後回しにできる決定ではありません。** ポインタツリーを4-wayツリーのアリーナに変える作業は呼び出し側全体に触れる構造変更なので、プロファイラがボトルネックを指し示してから始めたのでは既に遅すぎます。HNコメントの「高性能レーシングタイヤをポンコツ車に履かせる」という比喩が的確なのはこのためです - 問題はタイヤをいつ履かせるかではなく、車体がそもそもそのタイヤを受けられるように設計されているかです。

### 検証なきSIMDはない

最後に、元記事の助言のうち最も実用的な一行をUnityの文脈に移すとこうなります。**ベクトル化されたと信じず、アセンブリで確認せよ。** 自動ベクトル化（1層）に頼るコードならBurst Inspectorで`fadd v0.4s`のようなベクトル命令が実際に生成されたかを確認し、リグレッションを防ぐには`Loop.ExpectVectorized()`を仕込んでコンパイル時に引っかかるようにします。明示的に書いたコード（3層）でも、前後のプロファイリングなしに利得は主張できません - この記事の3.6倍も、計測したから言える数字です。

---

## まとめ

| 問い | 答え |
|------|-----|
| SIMDが速い理由 | 128bitベクトルレジスタの4レーンを1命令で演算 - 理論上限はベクトル幅の倍数 |
| 専用パイプライン？ | なし。GPUのような別デバイスではなくコア内部の実行ポート - オフロードコスト0、規模はコア数 × レーン数に制限 |
| ハードウェアの現況 | IntelのコンシューマCPU（i9含む）はAVX2 256bitまで、Zen 5はネイティブ512bit、RadeonはCUあたりSIMD32 × 2で構成されたSIMDマシン（SIMTモデル） |
| SIMDのないCPU？ | 64bitなら必ずある - x86-64はSSE2、AArch64はNEONがアーキテクチャの必須仕様。有無ではなく幅だけが問題 |
| 業界事例 | UnrealはVectorRegister（数学の土台） + ISPC（Chaos・クロス）、Jolt物理（Horizon Forbidden West）はSSE4.1~AVX-512・NEON、UnityはUnity Physics・xxHash3（自社パッケージ）とV Rising・Cities: Skylines II（商用ゲーム） |
| 旧型CPUのリスク | 非対応命令 = Illegal Instructionで即死（Cyberpunk 2077のAVX、Helldivers 2のAVX2の事例）。解法はランタイムディスパッチ - Burstのデスクトップ既定値がこの方式 |
| 明示的SIMDの書き方 | ブロードキャスト → ベクトル走査 → 並列演算 → リダクション → 端数の固定5段階、分岐はマスク算術で |
| 実測の利得 (M4 Pro, .NET 10) | float 100万の合算が3.6倍、一致カウントが2.7倍 - 倍率はスカラー側のボトルネックが決める |
| Unityでの経路 | Burstが唯一の信頼できる経路。自動ベクトル化 → Unity.Mathematics float4 → Burst Intrinsics v128の順で降りるが、降りる前にBurst Inspectorで確認 |
| ツリー・グラフ構造 | ポインタ追跡はメモリレイテンシに直列で縛られベクトル化不可 → インデックス配列への線形化が先行。さらにベクトル幅が分岐数を決める（Unity PhysicsのBVHは4-way + `FourTransposedAabbs`） |

## シリーズリンク

- [Unity Job SystemとBurst](/posts/UnityJobSystemBurst/) - Job・NativeContainer・Burstの基礎とメモリアラインメント
- [SoA vs AoS](/posts/SoAvsAoS/) - SIMDの前提条件であるデータレイアウト
- [Burst Compiler 深掘り](/posts/BurstCompilerDeepDive/) - 自動ベクトル化の成功・失敗の条件とBurst Inspectorウォークスルー
- 今回 - SIMDハードウェアの原理と明示的SIMDの記述

## 参考資料

### 一次出典・公式ドキュメント

- Mitchell Hashimoto, *SIMD Basics* — <https://mitchellh.com/writing/simd-basics>
- .NET `Vector<T>` API — <https://learn.microsoft.com/dotnet/api/system.numerics.vector-1>
- Unity Burst Manual, *CPU Intrinsics* — <https://docs.unity3d.com/Packages/com.unity.burst@latest/manual/csharp-burst-intrinsics.html>
- Arm NEON Intrinsics Reference — <https://developer.arm.com/architectures/instruction-sets/intrinsics/>
- AMD, *RDNA Architecture Whitepaper* — <https://gpuopen.com/download/RDNA_Architecture_public.pdf>

### ハードウェア分析

- Phoronix, *Quantifying The AVX-512 Performance Impact With AMD Zen 5* — <https://www.phoronix.com/review/amd-zen5-avx-512-9950x>
- Chips and Cheese, *Zen 5's AVX-512 Frequency Behavior* — <https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior>
- Tom's Hardware, *Ryzen 9000 CPUs drop 10% frequency executing AVX-512* — <https://www.tomshardware.com/pc-components/cpus/ryzen-9000-cpus-drop-10-frequency-executing-avx-512-instructions-intel-cpus-typically-suffer-from-more-substantial-clock-speed-drops>
- TechPowerUp, *Intel Officially Confirms AVX10.2 and APX Support in "Nova Lake"* — <https://www.techpowerup.com/342881/intel-officially-confirms-avx10-2-and-apx-support-in-nova-lake>
- XDA, *A Helldivers 2 update is giving players with older CPUs hell* — <https://www.xda-developers.com/helldivers-2-update-avx2-bug/>
- Nixxes Support, *This game requires a CPU that supports the AVX2 instruction set* — <https://support.nixxes.com/hc/en-us/articles/24667980191645-This-game-requires-a-CPU-that-supports-the-AVX2-instruction-set>

### ゲーム業界の事例

- Intel, *Unreal Engine's New Chaos Physics System Screams With In-Depth Intel CPU Optimizations* — <https://www.intel.com/content/www/us/en/developer/articles/technical/unreal-engines-new-chaos-physics-system-screams-with-in-depth-intel-cpu-optimizations.html>
- GDC 2020, *Intel ISPC in Unreal Engine 4 — A Peek Behind the Curtain* — <https://gdcvault.com/play/1026686/Intel-ISPC-in-Unreal-Engine>
- Guerrilla Games, *Architecting Jolt Physics for Horizon Forbidden West* (GDC 2022) — <https://www.guerrilla-games.com/read/architecting-jolt-physics-for-horizon-forbidden-west>
- Jolt Physics (GitHub) — <https://github.com/jrouwe/JoltPhysics>
- paavohtl, *Why Cities: Skylines 2 performs poorly* — <https://blog.paavo.me/cities-skylines-2-performance/>
- Unity Physics Manual — <https://docs.unity3d.com/Packages/com.unity.physics@1.0/manual/index.html>
- Unity.Collections `xxHash3` API（二重実装の説明） — <https://docs.unity3d.com/Packages/com.unity.collections@2.6/api/Unity.Collections.xxHash3.html>
- Unity Physics `BoundingVolumeHierarchy.Node` API（`FourTransposedAabbs` + `int4`） — <https://docs.unity3d.com/Packages/com.unity.physics@0.3/api/Unity.Physics.BoundingVolumeHierarchy.Node.html>

### データ指向設計

- RendelloのData-Oriented Design関連 Hacker News コメント — <https://hn.algolia.com/?query=Data-Oriented%20Design%20author%3ARendello&sort=byPopularity&type=all>
- Richard Fabian, *Data-Oriented Design* — <https://www.dataorienteddesign.com/dodbook/>

### コミュニティ・議論

- GeekNewsの紹介およびコメントの論点 — <https://news.hada.io/topic?id=31734>
- Arm Learning Path, *Using NEON intrinsics to optimize Unity on Android* — <https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/using-neon-intrinsics-to-optimize-unity-on-android/>

### 計測ツール

- BenchmarkDotNet — <https://benchmarkdotnet.org/>
