---
title: Unity Animator Controller - 오버라이드 컨트롤러 사용법
date: 2023-09-10 18:15:00 +/-TTTT
categories: [Unity, Animator]
tags: [Unity, MechanimAnimator, Animator Controller, Animator Override Controller]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---
## 목차
[1. Animator Override Controller 개요](#1-animator-override-controller-의-장점)

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
