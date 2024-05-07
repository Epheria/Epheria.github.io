---
title: Unity Addressable 빌드 에러 해결 - Animator 실행이 되지 않는 이슈
date: 2023-08-30 21:38:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Addressable, Build, iOS, AOS]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차

- [1. 주요 현상 및 분석](#주요-현상-및-분석)
- [2. 해결 방법](#해결-방법)

---

## 유니티 iOS/AOS Addressable을 포함한 빌드 시 Animator가 실행이 되지 않는 이슈

<br>

## 주요 현상 및 분석

- Toyverse 프로젝트를 개발하던 도중 발생한 에러이다.
- Home Scene 에서는 Home Character, Wolrd Scene 에서는 World Character 프리팹을 사용중이다.
- Home Character의 애니메이터 및 애니메이션 클립은 잘 실행되나, World Character의 애니메이터 및 애니메이션 클립이 실행되지 않는 버그가 발생했었다.
- Addressable Groups의 프로필은 Default이고 Play Mode Script는 Use Asset DataBase(fastest) 상태이다.
> 즉 어드레서블 빌드한 어드레서블 번들들이 패치 시스템으로 받는 형식이 아니고 apk/ipa 빌드에 포함된 상태이다.
- Character Movement System은 FSM State를 사용중이며 Animator Controller 의 파라미터 및 Animation State를 기반으로 애니메이션과 캐릭터 상태를 실행중이다.
> 처음에 FSM 로직상 문제인줄 알았다. 왜냐하면 Idle 상태에서 Jump로 전환하면 GroundChecker를 무시하고 지속적으로 Jump 상태로 유지되었기 때문이다.   
하지만, 디버그를 찍어봐도 로직상 문제는 없었다. 삽질 끝에 어드레서블 빌드에 World Character의 Animator 에 할당되어야할 Animator Controller가 빠진 느낌이 들었다.

![Desktop View](/assets/img/post/unity/notwork.gif){: .normal }
- 위의 사진은 어드레서블 빌드가 정상적으로 이루어지지 않을 때의 모습이다.
- World Character의 Animator Controller를 확인해보니.. 어드레서블 체크가 안되어 있었다;; 하.. 부랴부랴 체크를 하고 다시 빌드를 해서 확인했으나 여전히 위 사진처럼 T-Pose를 유지한채로 였다.
- T-Pose 의 원인이 무엇일까? 고민하다가 설마..? Animator 에 할당된 Avatar가 빠진게 아닐까 의심하고 World Character의 Model 을 확인해보니..
- Model 하위에 Avatar가 있었는데 이것 역시 어드레서블 그룹에 등록이 안되어 있었던것이다..

<br>

## 해결 방법

1. 캐릭터 프리팹은 어드레서블 그룹에 잘 할당되어 있다.
![Desktop View](/assets/img/post/unity/addrbuild01.png){: .normal }

<br>

2. 이제 Animator 컴포넌트에 Animator Controller와 Avatar를 확인하자.

![Desktop View](/assets/img/post/unity/addrbuild02.png){: .normal }
![Desktop View](/assets/img/post/unity/addrbuild04.png){: .normal }

<br>
<br>

- 캐릭터의 모델 하위에 포함된 Avatar 의 모습..
<br>

![Desktop View](/assets/img/post/unity/addrbuild03.png){: .normal }

<br>

3. 또한 한가지 간과하는 것이 있었다. 이전에 Strip Engine Code 에 대해 설명했던 포스트인데 -> :: [링크](https://epheria.github.io/posts/UnityBuild/)
- 이때 유니티 빌드옵션에서 IL2CPP, Strip Engine Code를 활성화 해놓고 link.xml에 Animator, Animator Controller, Animation Clip, RuntimeAnimatorController, OverrideAnimatorController, Avatar 등을 최적화 작업에서 제외하는 preserve=all을 해주지 않았다.

- link.xml 코드

```
<type fullname="UnityEngine.AnimationClip" preserve="all" />
<type fullname="UnityEngine.Avatar" preserve="all" />
<type fullname="UnityEngine.AnimatorController" preserve="all" />
<type fullname="UnityEngine.RuntimeAnimatorController" preserve="all" />
<type fullname="UnityEngine.Animator" preserve="all" />
<type fullname="UnityEngine.AnimatorOverrideController" preserve="all" />
```

- IL2CPP, Strip Engine Code를 활성화 하면 유니티 빌드 시 불필요한 클래스들을 제외하는 최적화 작업을 포함하는데 이 때 위의 것들이 빌드에서 제외될 경우가 발생할 수 있기 때문에 link.xml에서 꼭 preserve=all을 해줘야한다.

<br>

#### 항상 로직은 완벽한데 이상하다 싶으면 일단 어드레서블을 의심하자.
> 솔직히 캐릭터 프리팹을 어드레서블에 등록할 때 캐릭터 프리팹에 종속된 에셋들이 왜 같이 어드레서블에 등록이 되지 않은 것인지 의문이다.

- 참고로 캐릭터의 Avatar와 Animator Controller는 어드레서블 에셋들을 보관하는 폴더인 Downloadable Assets 하위에 있지 않았고 아트에서 관리하는 폴더에 들어가 있다.
- 즉 어드레서블 폴더 하위에 없더라도 어드레서블 그룹에 등록이 가능한것같다. 이렇게 되면 중복되는 에셋이나 머테리얼이 존재하기 마련인데
- 이 부분은 Addressable Analyze 를 사용하여 중복 및 종속성을 체크하여 최적화가 가능하다.

![Desktop View](/assets/img/post/unity/work.gif){: .normal }
#### 수정 후 캐릭터 애니메이터가 정상적으로 작동하는 모습