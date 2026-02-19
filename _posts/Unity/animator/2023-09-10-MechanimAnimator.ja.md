---
title: Unity Animator Controller - Override Controller の使い方
date: 2023-09-10 18:15:00 +/-TTTT
categories: [Unity, Animator]
tags: [unity, mechanimanimator, animator controller, animator override controller]
difficulty: intermediate
lang: ja
toc: true
---

## 目次

[1. Animator Override Controller 概要](#1-animator-override-controller-の利点)

[2. Animator Override Controller 使用方法](#2-animator-override-controller-使用方法)

[3. Animator Override Controller をスクリプト制御する方法](#3-animator-override-controller-をスクリプトで制御する方法)

[4. Animation Event をスクリプト制御する方法](#4-animation-event-をスクリプトで制御する方法)

[5. Animator Controller パラメータをコードで制御する方法](#5-animator-controller-パラメータをコードで制御する方法)

---

## Animator Override Controller

#### 1. Animator Override Controller の利点
1. 現在のアバターコントローラ内のアニメーションクリップを上書きして使える。
2. 武器バリエーションが多い場合、攻撃/移動/待機などを武器別に分けたい時や、1つのダンスステートに多数のダンスを割り当てたい時に便利。
3. 動的にクリップ差し替えできるため、Animator を都度修正しなくてよい。

<br>
- Animator Override Controller 適用前
> 武器ごとに State を増やすと Animator がすぐに破綻する。

![Desktop View](/assets/img/post/unity/uma01.png){: : width="800" .normal }

<br>

- Animator Override Controller 適用後
> 例えば `ComboAttack1` は以前なら斧/槍/片手剣/両手剣の全ステートが必要だったが、  
Override Controller なら 1 ステートで複数武器クリップを対応できる。

![Desktop View](/assets/img/post/unity/uma02.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/uma03.png){: : width="400" .normal }

<br>
<br>

#### 2. Animator Override Controller 使用方法

- まずエディタで Animator Override Controller ファイルを作成し、ベース controller を割り当てる。
- その後、上書きしたい animation clip を割り当てる。

![Desktop View](/assets/img/post/unity/uma04.png){: : width="400" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma05.png){: : width="500" .normal }

<br>

- 私のケースではキャラ用 Animator Controller を指定し、その中の全 Animation State に対して override を適用した。

![Desktop View](/assets/img/post/unity/uma06.png){: : width="500" .normal }

<br>
<br>

#### 3. Animator Override Controller をスクリプトで制御する方法

- Animator Override Controller 変数を作成して割り当て、現在 Animator の `runtimeAnimatorController` に設定した後、clip 名を override する。

<br>

- Animator の **State 名**ではなく、

![Desktop View](/assets/img/post/unity/uma07.png){: : width="200" .normal }

<br>

- State に割り当てた **Animation Clip 名**を key に使う。

![Desktop View](/assets/img/post/unity/uma08.png){: : width="500" .normal }

<br>

#### スクリプト例
- `animatorOverrideController` キャッシュ

``` csharp
    void Start()
    {
        animatorOverrideController = new AnimatorOverrideController(animator.runtimeAnimatorController);

        animator.runtimeAnimatorController = animatorOverrideController;
    }
```

<br>

- Animation Clip 名をキーに override
- ここで `GetAnimationClip` は DataTable から Addressable ロードで clip を返す。
- 返却 clip を override 対象に割り当てる。

```csharp
var animClip = await Managers.DataMgr._toyAnimationData[index_].GetAnimationClip();
animatorOverrideController["common@forspecialaction"] = animClip;
```

<br>

- 現在再生中 state の時間を見て、アニメ未終了時の重複実行を防ぐ方法
> `GetCurrentAnimatorStateInfo(int i)` の引数は layer index。  
> state 名・時間判定どちらにも使える。

![Desktop View](/assets/img/post/unity/uma12.png){: : width="200" .normal }

```csharp
if (fsm.Animator.GetCurrentAnimatorStateInfo(0).IsName("Dance"))
{
    // do something
}

if(fsm.Animator.GetCurrentAnimatorStateInfo(0).normalizedTime < 1.0f)
{
    // do something
}
```

<br>

#### 4. Animation Event をスクリプトで制御

- 方法は 2 つ: エディタで Animation Clip に直接追加する方法、スクリプトで該当フレームに動的追加する方法。
> [Animation Event Reference](https://docs.unity3d.com/ScriptReference/AnimationEvent.html)

<br>

- エディタで割り当てる方法
- 従来は各 Clip を開いてポイントを作り、呼びたい関数を指定していた。
![Desktop View](/assets/img/post/unity/uma14.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/uma15.png){: : width="500" .normal }

<br>

- スクリプトで動的生成する方法
- `event.time`, `event.functionName`, `event.xxxParameter` を設定し、
- `animationClip.AddEvent(event)` でイベント登録する。

![Desktop View](/assets/img/post/unity/uma16.png){: : width="300" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma17.png){: : width="600" .normal }

<br>

- `functionName` に設定する関数例

![Desktop View](/assets/img/post/unity/uma18.png){: : width="400" .normal }

<br>

- float/int/string パラメータも動的割り当て可能。

![Desktop View](/assets/img/post/unity/uma19.png){: : width="300" .normal }

![Desktop View](/assets/img/post/unity/uma20.png){: : width="300" .normal }

<br>
<br>

#### 5. Animator Controller パラメータをコード制御する方法
- Mono スクリプトを GameObject に付けるのと同様に、`StateMachineBehaviour` 継承スクリプトは状態ごとに接続可能。
- 例: `OnStateEnter`, `OnStateExit`, `OnStateIK`, `OnStateMove`, `OnStateUpdate`
> [StateMachineBehaviour Reference](https://docs.unity3d.com/kr/530/ScriptReference/StateMachineBehaviour.html)

![Desktop View](/assets/img/post/unity/uma21.png){: : width="500" .normal }

![Desktop View](/assets/img/post/unity/uma22.png){: : width="500" .normal }

<br>

#### コード例
- Animation State が多い場合、または Event を逐一設定するのが面倒/不可能な場合、
- state enter/exit/update の各タイミングでパラメータを更新できる。
- 以下は `ResetAnimationBool` を対象 state に付与し、bool 名と値を設定する例。
- state へ入る時に bool を true/false へ更新する。

```csharp
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Animations;

public class ResetAnimationBool : StateMachineBehaviour
{
    public string isInteractingBool;
    public bool isInteractingStatus;

    public override void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo, int layerIndex, AnimatorControllerPlayable controller)
    {
        base.OnStateEnter(animator, stateInfo, layerIndex, controller);
        animator.SetBool(isInteractingBool, isInteractingStatus);
    }
}

```
