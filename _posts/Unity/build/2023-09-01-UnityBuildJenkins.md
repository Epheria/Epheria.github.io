---
title: Unity 빌드 자동화 - Jenkins
date: 2023-09-01 12:59:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Jenkins, 자동화]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 젠킨스에 대해
- 젠킨스는 클라/서버 모두 공통으로 프로젝트의 빌드를 지원해주는 툴이다.
- 특히 토이버스에서는 서버,클라 모두 젠킨스를 통해 빌드와 배포를 진행했다.
> 프로젝트는 Alpha, Dev, Real 로 나뉘는데   
Dev 는 말그대로 개발진행중인 브랜치   
Alpha 는 QA 팀 및 내부 테스트용 브랜치   
Real 은 본방, 스토어에 올라가는 브랜치로 설정.

- 클라는 Alpha,Dev,Real 용 aos/ios 프로젝트 빌드
- 서버는 서버 API, CMS, RealTime 빌드가 가능했다.

<br>

## 젠킨스 짚고 넘어가기
- 젠킨스가 설치된 로컬의 폴더 경로 : ./jenkins - workspace 
- 젠킨스 대시보드에서 만든 잡들은 빌드머신의 로컬 workspace 경로에 하나씩 늘어난다. (시스템 용량을 잡아먹는 주범, fastlane 을 못쓰게된 주범이기도하다..)


<br>

## 젠킨스 활용법
- 젠킨스를 빌드할 때 많은 방법이 있지만, Execute shell 로 빌드하는게 가장 마음 편하다..

