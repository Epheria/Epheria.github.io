---
title: Unity Cinemachine Jittering 이슈
date: 2023-07-20 15:59:00 +/-TTTT
categories: [Unity, Cinemachine]
tags: [Unity, Cinemachine, Jittering, Damping 알고리즘, CCD]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

<br>
<br>

## 1. Cinemachine Method Update 에 대해
<br>
<br>
## 주요 현상
- Cinemachine 카메라의 Damping 알고리즘 때문에 캐릭터나 비행선이 빠르게 움직이면 Jittering 현상이 발생

## 캐릭터의 Rigidbody 세팅
<img src="/assets/img/post/unity/cine01.png" width="512px" height="512px" title="256" alt="cine1">
<img src="/assets/img/post/unity/cine02.png" width="512px" height="512px" title="256" alt="cine2">

## Cinemachine Brain (Main Camera)
<img src="/assets/img/post/unity/cine03.png" width="512px" height="512px" title="256" alt="cine3">

## 원인 파악
- Rigidbody의 Interpolate는 물리기반 이동 캐릭터의 CCD 연산을 담당하는데   
Cinemachine Camera의 Follow나 LookAt 타겟을 지정해 CCD가 적용된 플레이어 위치를 따라    
Update Method를 통해 이동하는 Transform값과 카메라의 위치값을 자동으로 보간해주는   
Damping 알고리즘이 적용된 Transform값이 상이한 차이가 발생한다.

## 해결 방법
1. 물리 기반 이동 플레이어 캐릭터의 Rigidbody -> Interpolate 옵션을 꺼주기
2. 플레이어 캐릭터의 이동 관련 코드 rigidbody.velocity 또는 rigidbody.AddForce() 등을 FixedUpdate 에서 처리하기
3. Cinemachine Camera의 Update Method와 Blend Update Method를 Fixed Update로 설정하기
4. Virutal Camera의 Inherit Position 옵션 끄기