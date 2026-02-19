---
title: Unity Addressable ビルドエラー解決 - Animator が動作しない問題
date: 2023-08-30 21:38:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, addressable, build, ios, aos]
difficulty: intermediate
lang: ja
toc: true
math: true
mermaid: true
---

## 目次

- [1. 主な症状と分析](#主な症状と分析)
- [2. 解決方法](#解決方法)

---

## Unity iOS/AOS + Addressable ビルド時に Animator が動かない問題

<br>

## 主な症状と分析

- Toyverse 開発中に発生したエラー。
- Home Scene では Home Character、World Scene では World Character prefab を使用。
- Home Character の Animator/Animation Clip は正常だが、World Character 側だけ動作しない。
- Addressable Groups の profile は `Default`、Play Mode Script は `Use Asset DataBase (fastest)`。
> つまり Addressable bundle は patch 取得方式ではなく apk/ipa 同梱状態。
- Character Movement System は FSM State を使用し、Animator Controller パラメータと Animation State ベースで遷移。
> 最初は FSM ロジック問題かと思った。Idle -> Jump 遷移時に GroundChecker を無視して Jump 継続に見えたため。  
しかしデバッグ上はロジック異常なし。検証を進めると、Addressable ビルドで World Character に必要な Animator Controller が抜けている疑いが強くなった。

![Desktop View](/assets/img/post/unity/notwork.gif){: .normal }
- 上の画像は Addressable ビルドが正常でない時の状態。
- World Character の Animator Controller を確認すると Addressable チェックが外れていた。チェックして再ビルドしても T-Pose のままだった。
- そこで Animator に割り当てた Avatar の欠落を疑って Model を見ると、
- Model 配下の Avatar も Addressable Group 未登録だった。

<br>

## 解決方法

1. Character prefab 自体は Addressable group に正常登録されている。
![Desktop View](/assets/img/post/unity/addrbuild01.png){: .normal }

<br>

2. Animator component の Animator Controller と Avatar を確認。

![Desktop View](/assets/img/post/unity/addrbuild02.png){: .normal }
![Desktop View](/assets/img/post/unity/addrbuild04.png){: .normal }

<br>
<br>

- Character model 配下にある Avatar。
<br>

![Desktop View](/assets/img/post/unity/addrbuild03.png){: .normal }

<br>

3. もうひとつ見落としていた点: 以前の Strip Engine Code 記事 -> [リンク](https://epheria.github.io/posts/UnityBuild/)
- IL2CPP と Strip Engine Code を有効にしていたのに、`link.xml` で Animator 関連クラスを preserve していなかった。

- link.xml コード

```
<type fullname="UnityEngine.AnimationClip" preserve="all" />
<type fullname="UnityEngine.Avatar" preserve="all" />
<type fullname="UnityEngine.AnimatorController" preserve="all" />
<type fullname="UnityEngine.RuntimeAnimatorController" preserve="all" />
<type fullname="UnityEngine.Animator" preserve="all" />
<type fullname="UnityEngine.AnimatorOverrideController" preserve="all" />
```

- IL2CPP + Strip Engine Code 有効時は不要クラス除去最適化が走る。上記が除去されるとアニメーション関連が壊れる可能性があるため、`link.xml` で `preserve="all"` を必ず指定する。

<br>

#### ロジックが正しいのに挙動がおかしい時は、まず Addressable を疑う。
> 正直、キャラ prefab を Addressable 登録した時に依存アセットが自動登録されないのは疑問だった。

- Character の Avatar / Animator Controller は Downloadable Assets 配下ではなく、アート管理フォルダ側にあった。
- つまり Addressable フォルダ配下でなくても Addressable Group には登録可能。
- ただし重複アセット/マテリアルが発生しやすいため、Addressable Analyze で重複と依存を確認して最適化する。

![Desktop View](/assets/img/post/unity/work.gif){: .normal }
#### 修正後、Animator が正常動作
