---
title: Unity Addressable System
date: 2023-09-01 16:00:00 +/-TTTT
categories: [Unity, Addressable]
tags: [Unity, Addressable]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차

---

## 어드레서블 이란

- 내부적으로는 여전히 AssetBundle 단위로 그룹핑하여 사용중이다.
- AssetBundle을 Editor 레벨에서 랩핑함으로서 Addressable Group -> AssetBundle 로의 변환시 여러 커스터마이징이 가능함

- AssetBundle 의 가장 큰 단점이였던 의존성 문제였던 중복 참조 하지 않도록 설계됨


## Unity 에서 AssetBundle을 어떻게 식별하는가?

- AssetBundle 에는 고유한 Internal ID가 존재한다. (Unique Internal ID)
- 똑같은 AssetBundle을 두 번 로드하려고하면 Exception 이 발생.
- Internal ID 가 같은면 내용물이 다르더라도 중복된 내용이 되어버림.
- 하지만, 어드레서블에서는 Bundle 빌드시 고유한 Internal ID를 생성한다. (즉 같은번들이여도 이전 버전과는 달라진다)
- 이기능으로 인해 Internal ID가 달라진 업데이트된 번들은 새로 로드되는데 성공함

## Addressable 핵심 파일 및 플로우
- 어드레서블 빌드의 결과물
- settings.json, catalog.json -> 정보리스트 파일, 번들의 목록
- 1. settings.json 파일을 최우선으로 읽고 내부에 있는 고유 Path들을 읽어들여서 카탈로그를 읽어들임



## Addressable Download Progress

- max webrequest concurrent count = 5 가 적당하다.
- 어드레서블 기본 동시 요청 수는 3으로 설정되어 있다. 모바일에서 5개 이상의 동시 다운로드가 전체 다운로드 속도에 부정적인 영향을 미침. 데스크톱도 2-3개면 충분
- 원인은 다운로드가 너무 많으면 대역폭 공유로 인해 각 개별 다운로드 속도가 느려진다고 한다. 또한 실패한 UnityWebRequest 는 처음부터 다시 다운로드를 진행해야 한다 (0%) 부터.. 
- 동시에 완료된 다운로드가 많은 경우 번들을 캐싱하면 많은 메모리가 소모된다. 데이터를 캐시로 압축하고 다시 압축하는 작업을 포함해서..

https://forum.unity.com/threads/extremely-slow-download-via-addressables-downloaddependenciesasync-and-unity-cloud-content-delivery.1133434/

