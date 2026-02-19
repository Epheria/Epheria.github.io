---
title: Unity & iOS メモリ構造について
date: 2023-11-20 19:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [ios, optimization, unity, memory structure]

difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

## **iOS メモリ構造**

#### **物理メモリ** (RAM)

![Desktop View](/assets/img/post/unity/profilerios01.png){: : width="500" .normal }

- 物理的にはこれ以上増やせない。
- この上限を超えて割り当てないこと。
- ***物理メモリ使用量 != アプリの VM 割り当て量***
> アプリは物理メモリを直接認識・直接使用しない。  
> アプリのメモリ割り当ては VM (Virtual Memory) 上で行われる。

<br>

#### **仮想メモリ** (VM - Virtual Memory)
- アプリは物理メモリを直接使わない。
- 割り当ては VM で行われる。

<br>

![Desktop View](/assets/img/post/unity/profilerios02.png){: : width="500" .normal }

- ページ単位に分割される (4KB / 16KB)。
- 各ページは物理メモリへマッピングされる。
- 通常、ページは Clean か Dirty の状態を取る。

<br>

![Desktop View](/assets/img/post/unity/profilerios03.png){: : width="500" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios04.png){: : width="500" .normal }

- エンジンが新規ページを Reserve し、OS に PM への **commit** を要求する。
- Unity ではこれを `Total **Committed** Memory` と呼ぶ。
- commit 要求した Reserve ページでも、実際に使わなければ PM に commit されない場合がある。

<br>

![Desktop View](/assets/img/post/unity/profilerios05.png){: : width="500" .normal }

- ***物理メモリ使用量 != VM 使用量***
- Resident memory: 318.0 MB, Total allocated: 1.76 GB
> 例: 1.78GB 割り当てても、実使用は約 380MB。

<br>
<br>

#### **VM の利点**

![Desktop View](/assets/img/post/unity/profilerios06.png){: : width="500" .normal }

- PM と VM 間で最適化が行われる。
- 単純化: アプリは物理メモリ層の最適化を直接意識しなくてよい。
- VM 使用量が大きくても、物理メモリ使用量は小さい場合がある。
- 本当に重要なのは **物理メモリをどれだけ使っているか**。

<br>
<br>

#### **メモリフットプリント** (Memory Footprint)

- メモリフットプリントはアプリの実質占有サイズを意味する。
> Resident 比率が高い割り当て領域の合算。
- **Resident Memory**: 割り当てメモリのうち、実際に物理メモリに常駐している部分。
- 例: 仮想メモリ 500MB 割り当て、Resident 比率 10%。
> 物理メモリ常駐 50MB + 仮想メモリ上のみ 450MB。

<br>
<br>

![Desktop View](/assets/img/post/unity/profilerios07.png){: : width="600" .normal }

- 一般的にアプリメモリプロファイルは Dirty / Compressed / Clean セグメントで構成される。
- **Dirty**: ヒープ割り当て、変更されたフレームワーク領域、使用中 Graphics API リソース (Metal)。
> アプリが書き込んだメモリ。デコード済み画像バッファも含まれる場合がある。
- **Dirty Compressed**: ほとんどアクセスされない Dirty ページ。
> ディスクスワップ可能。未アクセスページを圧縮して実効空間を増やし、アクセス時に解凍する。  
```
ディスクスワップとは?
物理メモリが不足した時に、ディスク領域を一時的にメモリのように使う仕組み。
```
- **Clean**: マップ済みファイル、読み取り専用フレームワーク、アプリバイナリ (静的コード)。物理メモリからいつでも外せる領域で、常駐率は低め。

<br>

![Desktop View](/assets/img/post/unity/profilerios08.png){: : width="600" .normal }

- Dirty と Dirty Compressed はメモリフットプリントであり、常駐率が高い。
- Clean は常駐率が低い。

#### **まとめ**

- 現在使っている物理メモリ全体 (Resident) がそのままフットプリントでない理由は?
> Clean の Resident はいつでも解放可能だから。  
> Dirty の Resident は解放しにくい。

- Dirty は必ず必要な最小物理メモリを意味する。
> 実質的な物理メモリ制約は Dirty 基準なので、Dirty が実質フットプリントとなる。

- **Dirty メモリが最優先の最適化対象。**
> 例: 動的割り当て。  
> **ただし Clean が過大だとスワップ頻度が増え、オーバーヘッドで性能悪化する場合がある。**

Dirty メモリを最優先で最適化すること。  
Clean メモリ由来のスワップが頻発してもオーバーヘッドになる。

<br>

#### **iOS のメモリ制限**

![Desktop View](/assets/img/post/unity/profilerios09.png){: : width="1600" .normal }

- Xcode Debugger に表示されるメモリ使用量は Dirty メモリ使用量。
- 例の図では仮想メモリ割り当てが 2GB 超。

<br>

![Desktop View](/assets/img/post/unity/profilerios10.png){: : width="1600" .normal }

- あるアプリの Dirty が増えるとどうなるか?
> アプリの Clean 常駐メモリを解放して Dirty 用の物理メモリを確保。  
> 他のバックグラウンドプロセスのメモリ使用も削減される。

<br>

![Desktop View](/assets/img/post/unity/profilerios11.png){: : width="1600" .normal }

- **アプリが使える最大メモリは Dirty 基準で計算される。**

<br>
<br>

#### **Unity で何がメモリフットプリントを作るか?**

![Desktop View](/assets/img/post/unity/profilerios12.png){: : width="1600" .normal }

- **<span style="color:#FFC26A">Unity Native Memory</span>**
> Unity C++ レイヤー。C# で `Texture2D` をロードすると C++ 側 `Texture2D` オブジェクトもロードされる。  
> 多くは Dirty メモリ。
```
C# を使っているのに C++ が出てくる理由
Unity は .NET VM 上で動く C++ エンジン。
ネイティブコアは C++、それを制御するのが .NET/C# スクリプト。
```

- **<span style="color:#FFC26A">Graphics</span>**
> モバイルでは GPU/CPU がメモリを共有する (Unified Memory)。  
> Texture や Shader などの Graphics リソース (Metal リソース)。  
> Graphics ドライバ。  
> 多くは Dirty メモリ。

- **<span style="color:#75B8FF">Native Plugin</span>**
> コードバイナリは Clean メモリ。  
> Native Plugin の **ランタイム割り当て** は **Dirty** メモリ。

- **<span style="color:#FFC26A">Unity Managed Memory</span>**
> .NET VM が制御するメモリ。  
> Unity C# スクリプト層のメモリ。  
> 動的割り当ての多くは Dirty メモリ。

<br>
- <span style="color:#75B8FF">バイナリ/ネイティブプラグインバイナリ</span> -> Clean メモリ
- それ以外 -> 主に Dirty メモリ

<br>
<br>

#### **Unity メモリ構造**

#### **ネイティブと管理スクリプト**

- Unity は .NET 仮想マシンを使う C++ エンジン。
- 2 つのレイヤーがある。
> ネイティブコード C++  
> 管理スクリプト .NET/C#
- アセットをロードすると、C# 側と C++ 側の両方のメモリとして見えることが多い。

<br>

#### **ゲームオブジェクトのバインディング**

![Desktop View](/assets/img/post/unity/profilerios13.png){: : width="400" .normal }

- `UnityEngine.Object` を継承した .NET オブジェクト
- C++ ネイティブインスタンスとリンクされる

<br>

#### **メモリ領域**

- **Managed Memory**: 自動管理される領域。
- **Native Memory**: エンジン C++ レイヤーが使う領域。
- **C# Unmanaged Memory**: GC 管理対象外の C# メモリ -> Job System / Burst Compiler などで使用。

- 例: フォントアセット

![Desktop View](/assets/img/post/unity/profilerios14.png){: : width="400" .normal }

- ネイティブ 342.5 KB
- 管理スクリプト 32 B

<br>

#### **Managed Memory**

- スクリプティングバックエンド VM により割り当て/制御される領域。
- Managed Heap: 全 C# 割り当て (動的割り当て)。
- C# Scripting Stack: ローカル変数。
- Native VM memory: VM 本体、スクリプティング内部、リフレクション/ジェネリクス用メタデータ領域。
- 割り当ては GC (Garbage Collection) により管理/整理される。
- 管理対象割り当ては `GC Allocation` または `GC.Alloc` として表示される。

<br>

#### **Managed Memory: 実際の動作**

![Desktop View](/assets/img/post/unity/profilerios15.png){: : width="600" .normal }

- メモリプール確保 -> リージョン内で近いサイズのオブジェクト用ブロックに分割。
> サイズが近いものをまとめてブロック化。
- 新規オブジェクトはブロック内へ割り当て。

<br>

![Desktop View](/assets/img/post/unity/profilerios16.png){: : width="600" .normal }

- オブジェクト破棄時にブロックから除去される。
- メモリ断片化が発生し得る。

<br>

![Desktop View](/assets/img/post/unity/profilerios17.png){: : width="600" .normal }

- 完全に空のブロックは OS へ返却可能。
- **<span style="color:#FF0BB1">完全空ブロックは decommitted される</span>**
- **<span style="color:#FF0BB1">VM では予約状態だが物理メモリにはマップされない</span>**

<br>

![Desktop View](/assets/img/post/unity/profilerios18.png){: : width="600" .normal }

- 既存ブロックに新規割り当てが収まらない場合、新規メモリリージョンを予約。
- 既定ブロックより大きい割り当てはカスタムブロック生成。
- リージョン内の未割り当て領域は物理メモリへマップされない。

<br>

![Desktop View](/assets/img/post/unity/profilerios19.png){: : width="600" .normal }

- 既存ブロックは近いサイズのオブジェクト割り当てに再利用できる。
- メモリリージョン全体が解放されると、仮想メモリでは確保状態でも物理メモリ側は decommit 返却される場合がある。
- 新規割り当てが既存ブロックに入らない場合 -> カスタムブロック生成/割り当て。

<br>
<br>

#### **Unity Memory Profiler 分析**

![Desktop View](/assets/img/post/unity/profilerios20.png){: : width="1600" .normal }

<br>

#### **Summaries タブ**

![Desktop View](/assets/img/post/unity/profilerios21.png){: : width="600" .normal }

- `Memory Usage On Devices`: 実機メモリ使用量
- `Allocated Memory Distribution`: VM 割り当て分布
- `Managed Heap Utilization`: ヒープ利用率
- `Top Unity Objects`: メモリを多く使う Unity オブジェクト

<br>

- **Memory Usage On Devices**

![Desktop View](/assets/img/post/unity/profilerios22.png){: : width="400" .normal }

- `Total Resident`: 常駐メモリ
- `Total Allocated`: 割り当て量

<br>

- **Allocated Memory Distribution**

![Desktop View](/assets/img/post/unity/profilerios23.png){: : width="400" .normal }

- カテゴリ別 VM 割り当て分布。
- **Native**: Native C++
- **Graphics**: Metal 経由 GPU 割り当て
- **Managed**: C#
- **Executable & Mapped**: Clean メモリ、バイナリ、DLL
- **Untracked**: シンボル不明/カテゴリ曖昧な割り当て -> カテゴリ機能は完全ではない (例: Audio Clip)

- **カテゴリは完全ではない**
> 種類が曖昧な場合  
> 分類不能な場合  
> Unity バージョンで分類方針が異なる場合
- `Unknown` / `Others` / `Untracked` は Unity が分類できない割り当てを意味する。
> 例: プラグイン割り当て (Android ログイン機能実装時など)、Unity アプリ由来の一部割り当て。

![Desktop View](/assets/img/post/unity/profilerios25.png){: : width="400" .normal }

- 常駐メモリ比率も表示される。

![Desktop View](/assets/img/post/unity/profilerios27.png){: : width="400" .normal }

- `Untracked` が大きい = 必ず問題、ではない。
- 例: `MALLOC_NANO`
> **事前確保されたヒープ領域を示す。**  
> Allocated size: 502.1 MB  
> Resident memory: 3.3 MB

<br>
<br>

- **Managed Heap Utilization**

![Desktop View](/assets/img/post/unity/profilerios28.png){: : width="400" .normal }

- ヒープ利用率を示す。
> 直接制御しづらい領域。
- Virtual Machine
- Empty Heap Space
- Objects

<br>

- **Virtual Machine**
   - スクリプティング本体のための VM 割り当て。
   - ジェネリクス、型メタデータ、リフレクション。
   - **ランタイム中に増え続ける傾向。**
   - **減らす方法**
   > 1. **コードストリップ**   
   ```
   - エンジンコードストリップ: ビルドで未使用の Unity エンジンモジュールコードを除去
   - Managed Code Strip Level
   両方を使う。リフレクション使用時はエラー化し得るため、link.xml で必要クラスを明示保持する。
   ```
   > 2. **可能な範囲でリフレクションを使わない**   
   > 3. **ジェネリックシェアリング (Unity 2022+)**

- **Empty Heap Space**
   - 空きヒープ領域。
   - 新規割り当てに利用可能。
   - 次回 GC で回収される破棄済みオブジェクトが含まれる場合がある。
   - PM からアンマップされたページは除外。
   - `Empty Heap Size` が大きい場合、断片化が大きい可能性 -> 動的割り当て時の CPU オーバーヘッド増加、不要なメモリ占有増加。

   - 旧バージョン

      ![Desktop View](/assets/img/post/unity/profilerios29.png){: : width="400" .normal }

      ![Desktop View](/assets/img/post/unity/profilerios30.png){: : width="400" .normal }

      - 旧版では `Active` / `Fragmented` に分割。
      - `Active Empty Heap Space`: 連続ヒープブロックの空き領域 (優先度高)
      - `Fragmented Empty Heap Space`: 断片化ヒープブロックの空き領域
      - 断片化そのものをユーザーが直接解決できる手段は少ない。

<br>

- **GC 実行構造**
- 空きブロック形成にはアルゴリズムがある。
1. 新規割り当て発生
2. まず連続ヒープ空間 (`Active Empty Heap Space`) から割り当て試行 (高速)
3. 次に空きブロック一覧と残余ヒープ空間をスキャンして割り当て試行 (低速)
4. それでも空きがなければ GC Collection トリガー
- Incremental GC 使用時は GC Collection と同時にヒープ拡張できる。
> symbol `gc_call_with_alloc` として表示される。
- Incremental GC 未使用時は GC 後でも空き不足ならヒープ拡張。
> `gc_expand_hp_inner`

- **Incremental GC 設定を推奨。**

<br>

#### **Unity Objects タブ**

![Desktop View](/assets/img/post/unity/profilerios31.png){: : width="800" .normal }

- Unity オブジェクトごとの割り当て量を表示。
- `Native Size` (C++)、`Managed Size` (C#)、`Graphics Size` の 3 軸で表示。
- 常駐メモリ比率も表示。

<br>

#### **All of Memory タブ**

![Desktop View](/assets/img/post/unity/profilerios32.png){: : width="800" .normal }

- VM 全体の割り当てオブジェクトを表示。
- `Untracked`, `Reserved` を含む。

<br>

#### **Memory Map**

![Desktop View](/assets/img/post/unity/profilerios33.png){: : width="800" .normal }

- 隠れ機能。
- ページ単位メモリマップ。
- どの主体が該当ページを占有しているか確認できる。
> `Device + IOACCELERATOR`: GPU 向け割り当て  
> `Native Allocation`: Unity ネイティブコード由来割り当て
- 具体的オブジェクト名は見えないが、どのフレームワーク/バイナリが占有しているか把握可能。

<br>

![Desktop View](/assets/img/post/unity/profilerios34.png){: : width="800" .normal }

- 512x512 テクスチャの割り当てが 2.7MB?
- Native 1.3MB + Graphics 1.3MB?
- いつ/なぜこの割り当てが起きたかを調べるには iOS ネイティブプロファイラが有効。
- Memory Profiler はスナップショットなので Call Stack 追跡は難しい。

<br>
<br>

## **ネイティブプロファイラを使う: Xcode Instruments**

- [Xcode Instruments 使用方法](https://epheria.github.io/posts/instruments/)
- **または Xcode から直接 Instruments 起動。**

![Desktop View](/assets/img/post/unity/profilerios35.png){: : width="600" .normal }

- **Xcode Build Settings で Debug Symbol を必ず含める。**

![Desktop View](/assets/img/post/unity/profilerios36.png){: : width="400" .normal }

- **Xcode -> Open Developer Tools を選択**

![Desktop View](/assets/img/post/unity/profilerios37.png){: : width="600" .normal }

- **Instruments テンプレートで `Allocations` を選択**

<br>

#### **VM Tracker**

![Desktop View](/assets/img/post/unity/profilerios38.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/profilerios39.png){: : width="600" .normal }

- **アプリの VM 割り当て全体を確認できる。**

![Desktop View](/assets/img/post/unity/profilerios40.png){: : width="800" .normal }

- **Binaries/Code (Clean): `_LINKEDIT`, `_TEXT`, `_DATA`, `_DATA_CONST`**
- **"GPU": Unity GPU 処理領域 (`IOKit`, `IOSurface`, `IOAccelerate`)**
- **App Allocations: Unity CPU 側処理 (`Malloc_*`, `VM_ALLOCATE`)**
- **Performance tool data**

![Desktop View](/assets/img/post/unity/profilerios41.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/profilerios42.png){: : width="800" .normal }

- **`IOSurface` Graphics 割り当ての常駐率は 100% -> 物理メモリへ 100% 割り当て。**
- **この物理メモリ上限を超えるとアプリは落ちる。**


![Desktop View](/assets/img/post/unity/profilerios43.png){: : width="800" .normal }

- **`0x10da50000` オブジェクトはどこにあるか?**

![Desktop View](/assets/img/post/unity/profilerios44.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/profilerios45.png){: : width="800" .normal }

- **IL2CPP VM のジェネリックメタデータテーブル初期化過程での割り当てだと確認できる。**

<br>

#### **Call Stack 検索**

![Desktop View](/assets/img/post/unity/profilerios46.png){: : width="800" .normal }

- **下部検索欄で検索可能。**

<br>

![Desktop View](/assets/img/post/unity/profilerios47.png){: : width="800" .normal }

- **dirty size: 仮想メモリ内で dirty な領域 (resident から外しづらい領域)**
- **swapped: スワップ済み領域**
- **resident: 常駐メモリ**

![Desktop View](/assets/img/post/unity/profilerios48.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios49.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios50.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios51.png){: : width="800" .normal }

- `Allocations` でも常駐メモリ比率を確認できる。

<br>

- **追加情報**
- `Memory Graph`: ネイティブメモリスナップショットツール
- WWDC 2022 - `Profile and optimize your game's memory`

- **アプリ終了原因の切り分け: メモリ問題か?**

- アプリが落ちない間に Memory Profiler スナップショットを取り、過剰メモリ使用か確認。

- iOS Xcode debugger 接続状態でプレイ -> クラッシュ -> 原因を捕まえやすい。

- クラッシュがメモリ原因か、別エラーかを判定。

- **メモリ問題なら:**

- Memory Profiler の `Unity Objects` / `Summaries` で `Total Committed` の大きい領域から順に整理・分析。

- **レイアウト処理について**
- 循環レイアウト問題のため、
- dirty 判定を見てフレーム終端でレイアウト更新。
- 毎フレーム末尾へ押し出され続けるなら、レイアウト強制更新 API があるか検討。

- **その他メモ**
- Mobile -> Unified memory
- Windows -> VRAM
- Texture read/write 設定 -> CPU メモリ側にもコピーが載る




