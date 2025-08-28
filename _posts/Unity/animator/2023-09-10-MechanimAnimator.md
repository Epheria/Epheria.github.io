---
title: Unity Animator Controller - 오버라이드 컨트롤러 사용법
date: 2023-09-10 18:15:00 +/-TTTT
categories: [Unity, Animator]
tags: [Unity, MechanimAnimator, Animator Controller, Animator Override Controller]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

## 목차

[1. Animator Override Controller 개요](#1-animator-override-controller-의-장점)

[2. Animator Override Controller 사용 방법](#2-animator-override-controller-사용-방법)

[3. Animator Override Controller 스크립트로 제어하는 방법](#3-animator-override-controller-스크립트로-제어하는-방법)

[4. Animation Event 스크립트로 제어하는 방법](#4-animation-event-스크립트로-제어하기)

[5. Animator Controller 파라미터들을 코드로 제어하는 방법](#5-animator-controller-파라미터들을-코드로-제어하는-방법)

---

## Animator Override Controller

#### 1. Animator Override Controller 의 장점
1. 현재 아바타의 컨트롤러에 있는 애니메이션 클립들을 오버라이드 해서 사용할 수 있다.
2. 무기 바리에이션이 여러가지일 경우 공격,이동,대기 등 다양한 애니메이션을 무기별로 분리해서 사용하고 싶을 때, 혹은 댄스 애니메이션 스테이트 하나에 수많은 댄스를 오버라이드하여 사용하고 싶을 때 사용하면 아주 편리하다.
3. 동적으로 애니메이션 클립을 갈아 끼울 수 있기 때문에, 일일히 애니메이터를 수정하지 않아도 된다.

<br>
- Animator Override Controller 를 적용하기 전
> 각 무기에 맞게 State들을 확장하느라 애니메이터 컨트롤러가 정신이 없는 모습이다.. 정말 이대로 만들면 큰일난다..

![Desktop View](/assets/img/post/unity/uma01.png){: : width="800" .normal }

<br>

- Animator Override Controller 적용 후
> 예를 들어, ComboAttack1 의 경우 예전이였으면 도끼,창,한손검,양손검 모든 스테이트를 만들어줬어야 했으나
Override Controller 를 적용하면 하나의 스테이트만 사용하여 여러가지 무기에 대한 Animation Clip 들을 대응할 수 있다.

![Desktop View](/assets/img/post/unity/uma02.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/uma03.png){: : width="400" .normal }

<br>
<br>

#### 2. Animator Override Controller 사용 방법

- 우선 에디터상에서 Animator Override Controller 파일 생성 후 컨트롤러를 할당 해준다.
- 이후 원하는 애니메이션 클립들을 할당 해준다.

![Desktop View](/assets/img/post/unity/uma04.png){: : width="400" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma05.png){: : width="500" .normal }

<br>

- 나는 캐릭터에 쓰일 Animator Controller를 할당해주었고, 그 Animator Controller 안에 세팅된 모든 Animation State들에 대해 Override 를 진행할 수 있다.

![Desktop View](/assets/img/post/unity/uma06.png){: : width="500" .normal }

<br>
<br>

#### 3. Animator Override Controller 스크립트로 제어하는 방법

- Animator Override Controller 멤버변수를 생성 및 할당 후 현재 Animator의 runtimeAnimatorController를 할당 후 Animation Clip 이름을 오버라이드 해줘야한다.

<br>

- Animator 의 State 이름이 아니고

![Desktop View](/assets/img/post/unity/uma07.png){: : width="200" .normal }

<br>

- 내가 State에 할당한 Animation Clip의 이름을 key값으로 넣어줘야한다.

![Desktop View](/assets/img/post/unity/uma08.png){: : width="500" .normal }

<br>

#### 스크립트 예시
- animatorOverrideController 캐싱

``` csharp
    void Start()
    {
        animatorOverrideController = new AnimatorOverrideController(animator.runtimeAnimatorController);
     
        animator.runtimeAnimatorController = animatorOverrideController;
    }
```

<br>

- Animation Clip의 이름을 찾아 오버라이드 해주기
- 여기서 GetAnimationClip 은 데이터 테이블에서 어드레서블 로드를 통해 Animation Clip을 반환
- 반환한 Animation Clip을 오버라이드할 클립에 할당해주기.

```csharp
var animClip = await Managers.DataMgr._toyAnimationData[index_].GetAnimationClip();
animatorOverrideController["common@forspecialaction"] = animClip;
```

<br>

- 현재 실행중인 애니메이션 State의 시간을 판단하고 애니메이션이 완전히 종료되지 않았는데 실행되는 것을 방지하는 방법
> GetCurrentAnimatorStateInfo(int i)의 파라미터는 현재 애니메이터의 레이어를 의미한다.   
> 이름을 판단하거나 시간을 판단할 수도 있으므로 유용하게 사용이 가능하다.

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

#### 4. Animation Event 스크립트로 제어하기

- 에디터를 통해 Animation Clip에 Animation Event를 할당하는 방법과 스크립트를 통해 해당 프레임에 할당하는 방법이 있다.
> [Animation Event Reference](https://docs.unity3d.com/ScriptReference/AnimationEvent.html)

<br>

- 에디터를 통해 이벤트 할당하는 방법
- 기존의 방법은 Animation Clip 을 일일히 타고 들어가서 포인트를 생성해주고 실행하고 싶은 함수를 할당하여 진행을 했었다.
![Desktop View](/assets/img/post/unity/uma14.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/uma15.png){: : width="500" .normal }

<br>

- 스크립트를 통해 Animation Event를 동적 생성 후
- event.time, event.functionName, event.xxxParameter를 할당한 후
- animationClip.AddEvent(event) 애니메이션 클립의 이벤트로 등록 해주면 된다.

![Desktop View](/assets/img/post/unity/uma16.png){: : width="300" .normal }

<br>

![Desktop View](/assets/img/post/unity/uma17.png){: : width="600" .normal }

<br>

- functionName 에 할당해줄 함수들

![Desktop View](/assets/img/post/unity/uma18.png){: : width="400" .normal }

<br>

- float, int, string 등의 파라미터들 또한 동적으로 할당이 가능하다.

![Desktop View](/assets/img/post/unity/uma19.png){: : width="300" .normal }

![Desktop View](/assets/img/post/unity/uma20.png){: : width="300" .normal }

<br>
<br>

#### 5. Animator Controller 파라미터들을 코드로 제어하는 방법
- mono 스크립트들을 게임 오브젝트에 할당 하듯이 StateMachineBehaviour를 상속받은 스크립트들은 상태머신에 개별적으로 연결이 가능하다.
- ex. OnStateEnter, OnStateExit, OnStateIK, OnStateMove, OnStateUpdate
> [StateMachineBehaviour Reference](https://docs.unity3d.com/kr/530/ScriptReference/StateMachineBehaviour.html)

![Desktop View](/assets/img/post/unity/uma21.png){: : width="500" .normal }

![Desktop View](/assets/img/post/unity/uma22.png){: : width="500" .normal }

<br>

#### 코드 예시
- Animation State가 많은 경우 혹은 Event를 일일히 설정하기 귀찮거나 불가능한 작업일 때
- 상태머신 전환이 일어나는 시점, 종료 시점, 매프레임 호출하는 시점을 구분하여 파라미터 값을 수정할 수 있다.
- 아래 예시 코드는 ResetAnimationBool 컴포넌트를 수행하고 싶은 State에 할당해주고 bool 값을 true/false 할지 설정해주면 된다.
- 해당 State로 진입하면 bool 값을 true/false 로 바꾸는 작업을 수행하게 된다.

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