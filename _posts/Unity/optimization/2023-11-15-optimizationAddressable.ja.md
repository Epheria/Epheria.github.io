---
title: Unity Addressables 最適化ガイド
date: 2023-11-15 11:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [addressable, optimization, unity]

difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

## Addressables 最適化

#### Addressables の重複依存問題
- Addressables レポートで重複依存を確認できる。私は個人的に `Analyze` で対応している。

<br>

#### 重複依存とは？

- Addressables は `Assets` フォルダ内のどこにあるアセットでも登録できる。メモリアドレス参照ベースで扱うため可能。
- ただしこの便利さと同時に注意点があり、それがアセットの重複依存問題。

![Desktop View](/assets/img/post/unity/profileraddr02.png){: : width="700" .normal }

- Asset Group A, B があるとする。
- それぞれのグループ内アセット `a`, `b` がアセット `c` を参照しているケースを想定。

<br>

![Desktop View](/assets/img/post/unity/profileraddr03.png){: : width="700" .normal }

- この場合、生成される AssetBundle A と B の両方にアセット `c` が含まれてしまう。
- つまりメモリ上でアセット `c` が 2 回ロードされる。

<br>

![Desktop View](/assets/img/post/unity/profileraddr04.png){: : width="700" .normal }

- 解決方法はシンプル。
- Asset Group C を作成してアセット `c` をそこへ移す。
- そうすると AssetBundle A/B は AssetBundle C を参照する形になり、`c` の二重ロードを防げる。

<br>

#### まとめ

- 代表例は Shader。多くの Material が同じ Shader を参照するため発生しやすい。
- そのため Shader 専用グループを作って分離しておく（下の Shader Variant 話ともつながる）。
- 直接 Address を付けていなくても、複数グループから参照されるアセットは依存専用グループを明示的に作るとよい。
- Address を Catalog に含めないことで Catalog サイズも減らせる。
> `Include Addresses in Catalog` をオフにする。

<br>

![Desktop View](/assets/img/post/unity/profileraddr01.png){: : width="1800" .normal }

- Addressables には `Analyze` ツールがある。`Fixable Rules` を選び、上部ツールバーの `Analyze Selected Rules` を実行する。
- 重複依存を持つアセットを自動で `Duplicate Isolation` グループに分離してくれる。

<br>
<br>

#### Addressables 最適化 Tips

- `AssetReference` を使っていない場合、Catalog から GUID を除外できる。
> `Include GUIDs in Catalog` をオフにする。

![Desktop View](/assets/img/post/unity/profileraddr05.png){: : width="500" .normal }

<br>

- JSON Catalog ではなく Binary Catalog を使う。最近は Catalog を解析して更新内容を改ざんする方法もあるため、Binary は一次的な防御にもなる。

<br>

- モバイルでは同時処理できる Web Request 数に限界がある。
> `Max Concurrent Web Request` はデフォルト 500 なので、適切な低い値に下げる。

![Desktop View](/assets/img/post/unity/profileraddr06.png){: : width="500" .normal }

<br>
<br>


#### Shader Variant 最適化

#### Project Auditor

![Desktop View](/assets/img/post/unity/profileraddr07.png){: : width="1800" .normal }

- [Project Auditor Github](https://github.com/Unity-Technologies/ProjectAuditor.git)
- 静的解析ツール
> Unity アセット、プロジェクト設定、スクリプトを解析  
> Shader Variant 削減に有効

<br>

#### Shader Variant とは？

![Desktop View](/assets/img/post/unity/profileraddr08.png){: : width="500" .normal }

- キーワード組み合わせなどで派生する **Shader の派生バージョン**。
> OpenGL / Vulkan など複数キーワードを使うと、ビルド時に Shader Variant が乗算で増える。

<br>

![Desktop View](/assets/img/post/unity/profileraddr09.png){: : width="500" .normal }

- さらに Variant 数が多すぎると
- ***SetPass Call 増加***
- ***キーワードごとにメモリ使用量が増加（倍化しやすい）***

<br>

#### Shader Variant を整理する

- 基本として不要な Shader キーワードを使わない。似た役割の Shader(Variant) は統合する。
- 最もよくあるケース
> ***Addressables で Shader グループを分離していないと***、各 AssetBundle に重複 Variant が入ってしまい、重複依存が発生してメモリロードも増える。  
> Shader 専用 Asset Group を作る。

<br>

- Lighting 設定で使わない Lightmap モードを無効化すると、該当 Shader キーワードが明示的に削除される。

![Desktop View](/assets/img/post/unity/profileraddr10.png){: : width="600" .normal }

<br>

- 未使用 Graphics API を無効化する。Graphics API ごとに別 Variant が生成されるため。
> 個人的には Android モバイルでは Vulkan より OpenGL ES3 の方が安定していた（Particle のちらつき問題など）。  
> Apple の Graphics API は Metal。

![Desktop View](/assets/img/post/unity/profileraddr11.png){: : width="400" .normal }

<br>

- **ビルドに含まれない Material に注意**
> `shader_feature` で宣言したキーワードは、Material が使っていなければ Strip される。  
> ビルド時のキーワード Strip はプロジェクト全体 Material を基準に行われるが、ビルド対象外 Material がキーワード残存に影響する場合がある。

![Desktop View](/assets/img/post/unity/profileraddr12.png){: : width="500" .normal }

<br>

- URP 設定で Strip オプションを有効化
> デバッグ用キーワード  
> 未使用 Post-Process Variant キーワード  
> 未使用 URP Feature Variant

![Desktop View](/assets/img/post/unity/profileraddr13.png){: : width="300" .normal }

<br>

#### Project Auditor を使った消去法整理

- ***まず直前ビルドキャッシュを削除すること!!***
- **ビルドに含まれた全 Variant を収集**
- **プレイ中に実際使われた Variant をログから収集**
- **未使用 Variant を除去**
> Shader コードからキーワードを直接削除  
> Material 側のチェックを外す  
> `IPreprocessShaders` でフィルタリング

<br>

![Desktop View](/assets/img/post/unity/profileraddr14.png){: : width="900" .normal }

- Project Settings で Shader Compilation Log を有効化
> `Project Settings > Graphics > Log Shader Compilation` をチェック
- `Development Build` を有効化
- Addressables Build と Player Build を実行
> Addressables Build 実行時は、直前の Addressables Build キャッシュを先に削除する
- Project Auditor の Shader Variant 画面に、ビルドへ含まれた Shader が表示される

<br>

![Desktop View](/assets/img/post/unity/profileraddr15.png){: : width="900" .normal }

- ゲームをプレイしながら全コンテンツを巡回
- ロードされ GPU でコンパイルされた Shader Variant 名がログに残る
- そのログを Project Auditor 画面へドラッグ&ドロップ
> GPU がコンパイルした (= 実際に使った) Variant は `Compiled` としてチェックされる
- 未使用 Variant が特定できたので整理可能

<br>
<br>

#### 余談: Addressables パッチシステム実装時の CRC チェック

![Desktop View](/assets/img/post/unity/profileraddr16.png){: : width="500" .normal }

- Addressables Group 設定には CRC の有効/無効を切り替えるオプションがある。
- CRC チェックは簡単に言うと整合性検証で、AssetBundle が改ざんされたかを確認する。
- 私はラベル単位を一括ダウンロードする方式ではなく、`ResourceLocators` 全体を巡回してパッチシステムを実装した。
- その過程でリソースダウンロードのローディング表示に異常を確認した。（各 ResourceLocator のキー値を合算して進捗を出す方式）
- 例えば 200MB ダウンロード時、98%-99% 付近で、実際には最初の約 90% より残り 1%-2% の方が時間がかかった。
- これは CRC 整合性チェック処理の影響で終盤が遅くなる可能性があると、講師の李済民氏から助言を受けた。試す価値あり。
- あるいは CRC を切っても同じなら、Web Request の競合状態が原因かもしれないので `Max Web Request` を下げてみる。
