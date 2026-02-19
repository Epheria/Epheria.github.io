---
title: Unity Build イシュー解決まとめ - ID 238, Strip Engine Code, cs0246
date: 2023-07-20 15:15:00 +/-TTTT
categories: [Unity, Build Error]
tags: [unity, build, error id 238, stripenginecode, cs0246]
difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

## 1. Error: Could not produce class with ID 238. This could be caused by a class being stripped from the build even though it is needed. Try disabling 'Strip Engine Code' in Player Settings.

<br>
<br>

## 主な現象
- ビルド後に特定のアニメーションやプレハブが消える、またはエラーが発生する。

## 原因
- Addressable (Asset Bundle) を使っている場合、手動で保持しないといけないクラスが除去されて発生することがある。

## 解決方法
- `Strip Engine Code` はビルド時にサイズを減らす機能。
* [参考リンク](https://takoyaking.hatenablog.com/entry/strip_engine_code_unity)

上記リンクの通り、`Strip Engine Code` をオフにするのが最も簡単ですが、

私のケースではビルドサイズの問題が発生しました。

##### そのため最善策は、`link.xml` にビルドに必要なクラスを追加して保持すること。

<br>
 <span style="color:red">ただし注意点</span>

- `link.xml` に書いても、ケースによってはビルドに含まれないものがある。
- また .NET ランタイムを使う場合、レガシースクリプティングランタイムより大きい .NET クラスライブラリ API が提供されるため、コードサイズが増えることがある。  
このサイズ増加を抑えるには `Strip Engine Code` の有効化が必要。 (特に未使用のダミーコードも削除できるため、実運用では重要。)
* [参考リンク](https://docs.unity3d.com/kr/current/Manual/dotnetProfileLimitations.html)

<br>

##### 私が遭遇したケースではアニメーション同期が崩れていたため、`link.xml` に `AnimatorController` と `Animator` コンポーネントを追加した。

<img src="/assets/img/post/unity/unitybuild01.png" width="1920px" height="1080px" title="256" alt="build1">

クラッシュ時には該当 ID (例: ID 238) も出力される。  
この ID は YAML Class ID Reference に定義されたクラス ID。

したがって、発生したエラー ID を照合するには次のリンクを参照するとよい。
* [Class ID Reference](https://docs.unity3d.com/Manual/ClassIDReference.html)

<br>
<br>

-------

## 2. cs0246: The type or namespace name could not be found (are you missing a using directive or an assembly reference?)

<br>

## 主な現象
1. クラス作成時の名前空間問題。
2. `using UnityEditor` を使っている場合 -> UnityEditor クラスはビルドに含まれない。
3. `using xxxx` を書いたまま実際には使っていない場合。

-> ビルド時にエラーが発生し、ビルドが強制終了される。

## 原因
* 基本的には、クラスが正しく宣言されていないか `using` でインポートされていないと発生するエラー。

##### 発生時のビルド環境
- 作成したコードにタイプミスはない。
- エディタでは正常実行できる。
- 機能的な問題も発生しない。
- しかしビルド時にだけエラーで失敗する。

## 解決方法
1. UnityEditor コードをプリプロセッサで囲む。
2. 使っていない `using` 名前空間を削除する。
