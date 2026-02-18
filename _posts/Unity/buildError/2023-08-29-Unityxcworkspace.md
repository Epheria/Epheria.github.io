---
title: Unity - xcworkspace 생성 되지 않는 이슈 해결
date: 2023-08-29 14:38:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, xcworkspace, iOS, pod install]     # TAG names should always be lowercase

difficulty: intermediate
toc: true
---

## 목차

- [1. 주요 현상 및 분석](#주요-현상-및-분석)
- [2. 해결 방법](#해결-방법)

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
YOUR_USERNAME@YOUR_MACHINE Xcode % which pod
/opt/homebrew/bin/pod


# bin 폴더로 이동 (cd path)
YOUR_USERNAME@YOUR_MACHINE Xcode % cd /opt/homebrew/bin


# cocoapdos 버젼 체크 (pod --version)
YOUR_USERNAME@YOUR_MACHINE bin % pod --version
1.12.1

# gem 버전 체크
YOUR_USERNAME@YOUR_MACHINE Xcode % gem --version
3.4.19
```

<br>

2. **cocoapods 버젼 및 ruby gem 최신 버전 업데이트**
- cocoapods 버전과 ruby gem 버전을 체크하여 최신 버전으로 업데이트 해준다.

```
# cocoapods 삭제 및 설치 (brew uninstall cocoapods)
# sudo 는 자꾸 권한 이슈가 발생해서 homebrew 를 사용했다.
# 삭제
YOUR_USERNAME@YOUR_MACHINE bin % brew uninstall cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
Warning: Calling the `appcast` stanza is deprecated! Use the `livecheck` stanza instead.
Please report this issue to the adoptopenjdk/openjdk tap (not Homebrew/brew or Homebrew/homebrew-core), or even better, submit a PR to fix it:
  /opt/homebrew/Library/Taps/adoptopenjdk/homebrew-openjdk/Casks/adoptopenjdk11.rb:9

Uninstalling /opt/homebrew/Cellar/cocoapods/1.12.1... (13,430 files, 27.8MB)
YOUR_USERNAME@YOUR_MACHINE bin % brew unstall cocoapods -v 1.10.1

#설치
YOUR_USERNAME@YOUR_MACHINE bin % brew install cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
==> Fetching cocoapods
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/manifests/1.12.1
Already downloaded: /Users/YOUR_USERNAME/Library/Caches/Homebrew/downloads/092af1d0eed5d8e2252554a1d84826de8e271bcb598c43452362a690991fa2bd--cocoapods-1.12.1.bottle_manifest.json
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/blobs/sha256:6f1fca1cb0df79912e10743a80522e666fe605a1eaa2aac1094c501608fb7ee4
Already downloaded: /Users/YOUR_USERNAME/Library/Caches/Homebrew/downloads/abfa7f252c7ffcc49894abb0d1afe0e47accb0b563df95a47f8f04ad93f8f681--cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
==> Pouring cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
🍺  /opt/homebrew/Cellar/cocoapods/1.12.1: 13,430 files, 27.8MB
==> Running `brew cleanup cocoapods`...
Disable this behaviour by setting HOMEBREW_NO_INSTALL_CLEANUP.
Hide these hints with HOMEBREW_NO_ENV_HINTS (see `man brew`).
```

<br>

3. **cocoapods 다운그레이드가 정답?**
- 구글링을 해보면 cocoapods 버전이 1.10.xx 가 되어야 한다는 말이 있는데 내가 해결한 방법과는 조금 달랐다.
- 대답은 NO! 1.10 버전으로 다운그레이드를 할 필요가 없다. 저 에러는 terminal 의 인코딩쪽 locale쪽 이슈인거같다.
- 하단 해결 방법에서 자세히 설명하겠다.
> [Unity iOS Resolver 에서 xcworkspace 가 생성되지 않는 이슈](https://phillip5094.github.io/ios/unity/Unity-iOS-Resolver%EC%97%90%EC%84%9C-xcworkspace-%EC%83%9D%EC%84%B1%EB%90%98%EC%A7%80-%EC%95%8A%EB%8A%94-%EC%9D%B4%EC%8A%88/)

- 아래는 Jenkins 로 pod install을 실행 했을 때 발생한 에러

```
#+ echo ------------------------------------- Pod Install
#------------------------------------- Pod Install
#+ cd /Users/YOUR_USERNAME/Xcode
#+ /opt/homebrew/bin/pod install
#    33mWARNING: CocoaPods requires your terminal to be using UTF-8 encoding.
#    Consider adding the following to ~/.profile:
#
#    export LANG=en_US.UTF-8
#    0m
#/opt/homebrew/Cellar/ruby/3.2.2_1/lib/ruby/3.2.0/unicode_normalize/normalize.rb:141:in `normalize': Unicode Normalization not #appropriate for ASCII-8BIT (Encoding::CompatibilityError)
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:166:in `unicode_normalize'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:166:in `installation_root'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:226:in `podfile_path'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/user_interface/error_report.rb:105:in #`markdown_podfile'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/user_interface/error_report.rb:30:in `report'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/command.rb:66:in `report_error'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/claide-1.1.0/lib/claide/command.rb:396:in `handle_exception'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/claide-1.1.0/lib/claide/command.rb:337:in `rescue in run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/claide-1.1.0/lib/claide/command.rb:324:in `run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/command.rb:52:in `run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/bin/pod:55:in `<top (required)>'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/bin/pod:25:in `load'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/bin/pod:25:in `<main>'
#/opt/homebrew/Cellar/ruby/3.2.2_1/lib/ruby/3.2.0/unicode_normalize/normalize.rb:141:in `normalize': Unicode Normalization not #appropriate for ASCII-8BIT (Encoding::CompatibilityError)
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:166:in `unicode_normalize'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:166:in `installation_root'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:226:in `podfile_path'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/config.rb:205:in `podfile'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/command.rb:160:in `verify_podfile_exists!'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/command/install.rb:46:in `run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/claide-1.1.0/lib/claide/command.rb:334:in `run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/lib/cocoapods/command.rb:52:in `run'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/gems/cocoapods-1.12.1/bin/pod:55:in `<top (required)>'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/bin/pod:25:in `load'
#	from /opt/homebrew/Cellar/cocoapods/1.12.1/libexec/bin/pod:25:in `<main>'
#Build step 'Execute shell' marked build as failure
#Finished: FAILURE
```

<br>

## 해결 방법
- cocoapods 최신 버전 및 ruby gem 최신 버전을 설치하고 Xcode 프로젝트가 있는 폴더에 pod install 을 하면 Pod 폴더와 xcworkspace 파일이 잘 생성되는것을 확인했다.
- 이것을 기반으로 Jenkins 에서 mac terminal 에 접근하여 pod install 을 호출하여 해결했다. 
> fastlane 에도 cocoapods 라는 명령어가 있으니 fastlane으로 해결하고 싶다면 이부분 참조  
[fastlane cocoapods](https://docs.fastlane.tools/actions/cocoapods/)

- 아래는 Jenkins Shell Script로 Xcode 가 설치된 폴더로 이동 -> pod install 실행 -> 유니티 프로젝트 폴더로 복귀하는 코드이다.

```
# Jenkins Shell Script 

echo ------------------------------------- Pod Install
cd /Users/YOUR_USERNAME/Xcode
/opt/homebrew/bin/pod install
cd /Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane

```

- 이렇게 하면 잘 될줄 알았지만.. 위에서 언급한 에러가 발생했었다.

- 우선 Jenkins 가 뱉은 에러를 파악해보자. terminal 의 locale을 살펴봐야한다.

```
# locale 입력
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="ko_KR.UTF-8"
LC_COLLATE="ko_KR.UTF-8"
LC_CTYPE="ko_KR.UTF-8"
LC_MESSAGES="ko_KR.UTF-8"
LC_MONETARY="ko_KR.UTF-8"
LC_NUMERIC="ko_KR.UTF-8"
LC_TIME="ko_KR.UTF-8"
LC_ALL=
```

- 전부 한국어로 되어 있었다..
- 영어로 바꿔서 확인 해보자.

```
# LC_ALL 을 en 으로 바꾸자
YOUR_USERNAME@YOUR_MACHINE bin % export LC_ALL=en_US.UTF-8
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="ko_KR.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL="en_US.UTF-8"

# LANG 도 바꿔야한다.
YOUR_USERNAME@YOUR_MACHINE bin % export LANG=en_US.UTF-8
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL="en_US.UTF-8"
```

- 위 처럼 해도 Jenkins 로 빌드하면 똑같은 에러가 그대로 발생했다.. mac mini 세팅을 바꿔도 안된다고?!
- Jenkins 의 환경설정과 mac-mini의 환경설정이 다르다는 것을 깨닫게 되었다.
- 따라서 Jenkins 의 Shell script에 다음과 같은 부분을 추가해줘야한다.

```
# Init 하기 전에 환경변수 세팅할 때 추가해줘도 됨.
locale
export LANG=en_US.UTF-8
locale
```

- 아래는 Jenkins 출력된 로그 

```
# locale 체크
+ locale
LANG=""
LC_COLLATE="C"
LC_CTYPE="C"
LC_MESSAGES="C"
LC_MONETARY="C"
LC_NUMERIC="C"
LC_TIME="C"
LC_ALL=

# 변환
+ export LANG=en_US.UTF-8
+ LANG=en_US.UTF-8

#locale 체크
+ locale
LANG="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL=

# pod install 이 정상적으로 실행되는 모습이다.
+ echo ------------------------------------- Pod Install
------------------------------------- Pod Install
+ cd /Users/YOUR_USERNAME/Xcode
+ /opt/homebrew/bin/pod install
Analyzing dependencies
Downloading dependencies
Installing Firebase (10.1.0)
Installing FirebaseAnalytics (10.1.0)
Installing FirebaseAuth (10.1.0)
Installing FirebaseCore (10.1.0)
Installing FirebaseCoreInternal (10.12.0)
Installing FirebaseInstallations (10.12.0)
Installing FirebaseMessaging (10.1.0)
Installing GTMSessionFetcher (2.3.0)
Installing GoogleAppMeasurement (10.1.0)
Installing GoogleDataTransport (9.2.3)
Installing GoogleUtilities (7.11.4)
Installing PromisesObjC (2.3.1)
Installing nanopb (2.30909.0)
Generating Pods project
Integrating client project

[!] Please close any current Xcode sessions and use `Unity-iPhone.xcworkspace` for this project from now on.
Pod installation complete! There are 4 dependencies from the Podfile and 13 total pods installed.
+ cd /Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane
Finished: SUCCESS
```

- xcworkspace 파일과 함께 Pod 폴더가 정상적으로 설치되는 것을 확인할 수 있다..!!
- Jenkins 와 mac에서 세팅한 환경설정이 다를줄은 진짜 꿈에도 생각못했다.. 하