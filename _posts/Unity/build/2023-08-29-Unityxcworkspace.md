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

2. **cocoapods 버젼 및 ruby gem 최신 버전 업데이트**
- cocoapods 버전과 ruby gem 버전을 체크하여 최신 버전으로 업데이트 해준다.

```
# cocoapods 삭제 및 설치 (brew uninstall cocoapods)
# sudo 는 자꾸 권한 이슈가 발생해서 homebrew 를 사용했다.
# 삭제
coconevbusan@coconevbusanui-Macmini bin % brew uninstall cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
Warning: Calling the `appcast` stanza is deprecated! Use the `livecheck` stanza instead.
Please report this issue to the adoptopenjdk/openjdk tap (not Homebrew/brew or Homebrew/homebrew-core), or even better, submit a PR to fix it:
  /opt/homebrew/Library/Taps/adoptopenjdk/homebrew-openjdk/Casks/adoptopenjdk11.rb:9

Uninstalling /opt/homebrew/Cellar/cocoapods/1.12.1... (13,430 files, 27.8MB)
coconevbusan@coconevbusanui-Macmini bin % brew unstall cocoapods -v 1.10.1

#설치
coconevbusan@coconevbusanui-Macmini bin % brew install cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
==> Fetching cocoapods
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/manifests/1.12.1
Already downloaded: /Users/coconevbusan/Library/Caches/Homebrew/downloads/092af1d0eed5d8e2252554a1d84826de8e271bcb598c43452362a690991fa2bd--cocoapods-1.12.1.bottle_manifest.json
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/blobs/sha256:6f1fca1cb0df79912e10743a80522e666fe605a1eaa2aac1094c501608fb7ee4
Already downloaded: /Users/coconevbusan/Library/Caches/Homebrew/downloads/abfa7f252c7ffcc49894abb0d1afe0e47accb0b563df95a47f8f04ad93f8f681--cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
==> Pouring cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
🍺  /opt/homebrew/Cellar/cocoapods/1.12.1: 13,430 files, 27.8MB
==> Running `brew cleanup cocoapods`...
Disable this behaviour by setting HOMEBREW_NO_INSTALL_CLEANUP.
Hide these hints with HOMEBREW_NO_ENV_HINTS (see `man brew`).
```

<br>