---
title: Unity - xcworkspace 생성 되지 않는 이슈 해결
date: 2023-08-29 14:38:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, xcworkspace, iOS]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 유니티 iOS 프로젝트를 빌드하면 xcworkspace 가 생성 되지 않는 이슈 해결

<br>

## 주요 현상 및 분석

- **주요 현상** : 개발 환경은 mac OS 로 진행하였고 Jenkins 를 통해 fastlane 과 build script를 원격으로 빌드하던 도중 유니티 iOS 프로젝트를 빌드할 대 cocoapods 버젼 이슈가 발생하였고 Pods 폴더와 xcworkspace 파일이 생성되지 않았다.
- iOS Resolver를 체크해도 Integration이 xcworkspace로 잘 설정되어 있었고 Use Shell to Execute Cocoapod Tool 체크 박스를 해제 하든 안하든 xcworkspace 파일이 생성되지 않았다.

- iOS Resolver 경로
Assets - External Dependency Manager - iOS Resolver - Settings

<img src="/assets/img/post/unity/xcworkspaceissue01.png" width="500" height="700" title="256" alt="build1">

<br>

- 또한 이상했던 점은 이 이슈에 대해 파고들기 전에도 몇 번 xcworkspace 파일이 생성되지 않았던 적이 있었다. cocoapods 버전과 ruby gems 버전이 바뀐적이 없는데 왜 됬다 안됬다 했을까? 참 의문이다..
- 유니티 프로젝트를 수동으로 빌드하면 xcworkspace 파일이 정상적으로 잘 생성된다.. 참 골때린다

<br>

- Unity iOS Resolver 세팅이 잘못됬을 가능성
- mac-mini 에 설치된 cocoapods 의 버전과 ruby gems 버전 충돌 가능성

1. **cocoapods 버젼 충돌 가능성 체크**
- terminal 에 cocoapods가 설치된 bin 폴더로 이동하고 pod --version을 입력한다.
- 아래는 terminal 로그의 일부입니다.

```
# cocoapods bin 폴더 경로 확인 방법 (which something)
coconevbusan@coconevbusanui-Macmini Xcode % which pod
/opt/homebrew/bin/pod


# bin 폴더로 이동 (cd path)
coconevbusan@coconevbusanui-Macmini Xcode % cd /opt/homebrew/bin


# cocoapdos 버젼 체크 (pod --version)
coconevbusan@coconevbusanui-Macmini bin % pod --version
1.12.1

# gem 버전 체크
coconevbusan@coconevbusanui-Macmini Xcode % gem --version
3.4.19
```

<br>