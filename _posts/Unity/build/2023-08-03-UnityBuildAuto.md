---
title: Unity 빌드 자동화 - fastlane, build pipeline, Jenkins
date: 2023-08-03 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, BuildPipeline, 빌드 자동화, fastlane, Jenkins]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

-------

## 목차

- [fastlane 설정 방법](#1.-fastlane-설정-방법)
- [프로젝트 전반](#2.-Unity-Build-Pipeline-설정-방법)
- [내가 담당 했던 것들](#3.-Jenkins-설정-방법)
- [Toyverse 개요](#toyverse-개요)

------

<br>

## 1. fastlane 설정 방법

<br>
<br>

## 주요 현상
- 빌드 후 특정 애니메이션, 프리팹 등이 없어지거나 에러가 발생

## 원인
- Addressable(Asset Bundle)를 사용하고 있으면, 수동으로 포함하지 않으면 안되는 클래스가 있기 때문에 발생

## 해결 방법
- Strip Engine Code 는 빌드시 빌드 사이즈를 줄이기 위한 기능
* [참조 링크](https://takoyaking.hatenablog.com/entry/strip_engine_code_unity)

하지만 위 링크를 보면 Strip Engine Code를 끄는게 제일 간편하지만

빌드 사이즈에 있어 용량 이슈가 발생했고

##### 따라서 최선의 해결 방법은 link.xml 파일에 빌드에 필요한 클래스들을 추가해주는 것

<br>
 <span style="color:red">다만, 주의 할 점</span>

- link.xml 에 기술해도 빌드에 포함시켜주지 않는 것도 있다고 함
- 또한, Net 런타임을 사용하는 경우 레거시 스크립팅 런타임보다 크기가 큰 .NET 클래스 라이브러리 API가 함께 제공 되기 때문에 코드 크기가 더 큰 경우도 많다.   
이러한 코드 크기 증가를 완화하기 위해서는 Strip Engine Code를 활성화 해야함. (특히, 안쓰는 더미 코드들도 싹 빼주기 때문에 필수적으로 사용해야한다.)
* [참조링크](https://docs.unity3d.com/kr/current/Manual/dotnetProfileLimitations.html)

<br>

##### 내가 겪은 이슈는 애니메이션 동기화가 제대로 이루어지지 않았기 때문에, link.xml 에 AnimatorController와 Animator 컴포넌트를 추가했다.

<img src="/assets/img/post/unity/unitybuild01.png" width="1920px" height="1080px" title="256" alt="build1">

크래시가 났을 때 해당 ID 값을 같이 뿌려준다. (ex. ID 238 같이)
이 ID는 YAML Class ID Reference에 명시된 클래스들의 ID 이다.

따라서, 발생한 에러의 ID를 대조하려면 다음 링크를 참조하면 되겠다.
* [참조 링크 ClassIDReference](https://docs.unity3d.com/Manual/ClassIDReference.html)

<br>
<br>

-------

## 2. Unity Build Pipeline 설정 방법
<br>

## 주요현상
1. 클래스 작성 시 네임스페이스 문제..
2. using UnityEditor 사용 할 경우 -> UnityEditor 클래스는 빌드에 포함 X
3. using xxxx 코드에 적어놓고 사용하지 않을 경우

-> 빌드 시 에러 발생 후 빌드가 강제 종료됨

## 원인
* 기본적으로 Class 가 선언이 되어 있지 않거나 using 으로 임포트가 되지 않아서 발생하는 에러

##### 빌드 시 환경
- 작성한 코드에는 오탈자가 없음
- 에디터에서 정상적으로 실행이 가능
- 잘 실행될 뿐만 아니라 기능적 오류도 발생하지 않았음
- 하지만 빌드를 하려고 하면 에러가 발생하며 빌드가 실패함

## 해결 방법
1. UnityEditor 전처리 해버리기
2. 안쓰는 using namespace 지우기

<br>
<br>

-------

## 3. Jenkins 설정 방법