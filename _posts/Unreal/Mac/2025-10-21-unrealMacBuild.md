---
title: Unreal Mac OS 에서 프로젝트 로드가 안될 때 해결 방법
date: 2025-10-21 00:25:00 +/-TTTT
categories: [Unreal, MacOS]
tags: [Unreal, Mac, Xcode, SDK]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>

## 깃허브에서 받은 .uproject 를 Unreal Mac OS 에서 열 때 에러가 발생했다.

- Xcode 를 앱스토어, 최신버전을 다운받아도 아래의 에러가 발생하면서 열리지 않았다.

<br>

```
선택된 소스 코드 접근자 'Xcode' 열기에 실패했습니다.
```

<br>

```
Setting up bundled DotNet SDK
/Users/son_sehyup/UE_5.6/Engine/Build/BatchFiles/Mac/../../../Binaries/ThirdParty/DotNet/8.0.300/mac-arm64
Running dotnet Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll Development Mac -Project=/Users/son_sehyup/Documents/Unreal Projects/dd/dd.uproject -TargetType=Editor -Progress -NoEngineChanges -NoHotReloadFromIDE
Log file: /Users/son_sehyup/Library/Application Support/Epic/UnrealBuildTool/Log.txt
Creating makefile for ddEditor (no existing makefile)
Platform Mac is not a valid platform to build. Check that the SDK is installed properly and that you have the necessary platform support files (DataDrivenPlatformInfo.ini, SDK.json, etc).

Result: Failed (OtherCompilationError)
Total execution time: 1.09 seconds
```

<br>
<br>

## 해결 방법

- 원인은 Xcode 가 너무 최신버전이기 때문에 언리얼에서 인식을 못해서 발생했다.
- [최근 배타버전은 Xcode 26 이상이므로 Xcode 16을 다운받아야한다.](https://forums.unrealengine.com/t/platform-mac-is-not-a-valid-platform-to-build-check-that-the-sdk-is-installed-properly-and-that-you-have-the-necessary-platorm-support-files-datadrivenplatforminfo-ini-sdk-json-etc/1846659/3)

<br>

[Xcode16 다운로드 링크](https://developer.apple.com/download/all/)

<br>

```
xcodebuild -version
xcode-select --print-path
```

우선 이 두 가지로 xcode 가 설치되었는지 확인하고

<br>

```
xcode-select --install
```

을 통해 혹시 모르니 Command Line Tools 가 설치되었는지 시도 -> 설치되어있으면 에러 뜸

<br>

설치된 Xcode 패키지 내용 보기 - Contents - Developer 경로 복사해서

<br>

```
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

- 경로 재지정해주기.

- `/Applications/Xcode.app/Contents/Developer` 문자열 내부에 본인의 Xcode 설치된 경로를 집어넣어주자.

<br>

프로젝트 위치에 .xcworkspace 가 제대로 생성되었는지 확인

<br>

프로젝트 위치의 .uproject 를 더블 클릭하여 프로젝트 열기

<br>

**주의 : 깃허브 LFS Initialize 는 꼭 해주자. 언리얼 에셋 파일들이 용향이 크기 때문에 LFS 로 업로드될 텐데 Initialize 안해주면 에셋 파일들이 없는 상태로 프로젝트가 열린다.**
