---
title: Unity Animator Controller - How to Use Override Controller
date: 2023-09-10 18:15:00 +/-TTTT
categories: [Unity, Animator]
tags: [unity, mechanimanimator, animator controller, animator override controller]
difficulty: intermediate
lang: en
toc: true
---

## Table of Contents

[1. Animator Override Controller overview](#1-advantages-of-animator-override-controller)

[2. How to use Animator Override Controller](#2-how-to-use-animator-override-controller)

[3. How to control Animator Override Controller by script](#3-how-to-control-animator-override-controller-by-script)

[4. How to control Animation Event by script](#4-how-to-control-animation-event-by-script)

[5. How to control Animator Controller parameters in code](#5-how-to-control-animator-controller-parameters-in-code)

---

## Animator Override Controller

#### 1. Advantages of Animator Override Controller
1. You can override animation clips in current avatar controller.
2. If you have many weapon variations and want separate attack/move/idle clips per weapon, or want many dance clips on one dance state, this is very convenient.
3. Because clips can be swapped dynamically, you don't need to manually edit animator states one by one.

<br>
- Before applying Animator Override Controller
> Animator becomes chaotic if you expand states for every weapon variation. This quickly becomes unmanageable.

![Desktop View](/assets/img/post/unity/uma01.png){: : width="800" .normal }

<br>

- After applying Animator Override Controller
> For example, in `ComboAttack1`, previously you had to create states for axe/spear/one-hand/two-hand swords separately.  
With Override Controller, one state can map multiple weapon clips.

![Desktop View](/assets/img/post/unity/uma02.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/uma03.png){: : width="400" .normal }

<br>
<br>

#### 2. How to use Animator Override Controller

- First create Animator Override Controller asset in editor and assign base controller.
- Then assign target animation clips.

![Desktop View](/assets/img/post/unity/uma04.png){: : width="400" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma05.png){: : width="500" .normal }

<br>

- In my case, I assigned the character Animator Controller and overrode clips for all animation states defined in that controller.

![Desktop View](/assets/img/post/unity/uma06.png){: : width="500" .normal }

<br>
<br>

#### 3. How to control Animator Override Controller by script

- Create/assign AnimatorOverrideController variable, assign current Animator's `runtimeAnimatorController`, then override clip names.

<br>

- Not the Animator **state** name:

![Desktop View](/assets/img/post/unity/uma07.png){: : width="200" .normal }

<br>

- Use as key the name of the **Animation Clip assigned to that state**.

![Desktop View](/assets/img/post/unity/uma08.png){: : width="500" .normal }

<br>

#### Script examples
- Cache `animatorOverrideController`

``` csharp
    void Start()
    {
        animatorOverrideController = new AnimatorOverrideController(animator.runtimeAnimatorController);

        animator.runtimeAnimatorController = animatorOverrideController;
    }
```

<br>

- Find animation clip name and override it
- `GetAnimationClip` below returns clip from data table through Addressables.
- Assign returned clip into override key.

```csharp
var animClip = await Managers.DataMgr._toyAnimationData[index_].GetAnimationClip();
animatorOverrideController["common@forspecialaction"] = animClip;
```

<br>

- How to check current state timing to prevent triggering before animation fully ends
> Parameter of `GetCurrentAnimatorStateInfo(int i)` means layer index.
> Useful for checking state name or normalized time.

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

#### 4. Control Animation Event by script {#4-how-to-control-animation-event-by-script}

- There are two methods: assign animation events manually in editor, or create/assign them dynamically by script.
> [Animation Event Reference](https://docs.unity3d.com/ScriptReference/AnimationEvent.html)

<br>

- Editor method
- Traditional workflow is opening each Animation Clip, adding event point, and assigning function.
![Desktop View](/assets/img/post/unity/uma14.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/uma15.png){: : width="500" .normal }

<br>

- Script method
- Dynamically create AnimationEvent,
- assign `event.time`, `event.functionName`, `event.xxxParameter`,
- then register via `animationClip.AddEvent(event)`.

![Desktop View](/assets/img/post/unity/uma16.png){: : width="300" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma17.png){: : width="600" .normal }

<br>

- Functions assignable to `functionName`

![Desktop View](/assets/img/post/unity/uma18.png){: : width="400" .normal }

<br>

- Parameters like float/int/string can also be assigned dynamically.

![Desktop View](/assets/img/post/unity/uma19.png){: : width="300" .normal }

![Desktop View](/assets/img/post/unity/uma20.png){: : width="300" .normal }

<br>
<br>

#### 5. How to control Animator Controller parameters in code
- Like attaching mono scripts to GameObjects, scripts inheriting `StateMachineBehaviour` can be attached per state.
- ex: `OnStateEnter`, `OnStateExit`, `OnStateIK`, `OnStateMove`, `OnStateUpdate`
> [StateMachineBehaviour Reference](https://docs.unity3d.com/kr/530/ScriptReference/StateMachineBehaviour.html)

![Desktop View](/assets/img/post/unity/uma21.png){: : width="500" .normal }

![Desktop View](/assets/img/post/unity/uma22.png){: : width="500" .normal }

<br>

#### Code example
- When there are many animation states, or setting events one-by-one is difficult/impossible,
- you can handle transitions at enter/exit/update points and modify parameters.
- Example below: attach `ResetAnimationBool` to desired state and configure bool target + value.
- On entering that state, it sets bool true/false accordingly.

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
