---
title: Unity 빌드 자동화 - fastlane, build pipeline, Jenkins
date: 2023-08-03 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, 자동화, BuildPipeline, fastlane, Jenkins]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차
- [1. fastlane 설정 방법](#1-fastlane-설정-방법)
- [2. Unity Build Pipeline 설정 방법](#2-unity-build-pipeline-설정-방법)
- [3. Jenkins 설정 방법](#3-jenkins-설정-방법)

---

## 서론
> 회사에서 프로젝트의 iOS, AOS 빌드에 대한 전반적인 부분을 맡게 되었고 초반엔 Jenkins 만을 사용하여 Unity Build Pipeline을 통해 AOS 빌드 자동화 - AppCenter 업로드 - Slack Notification 까지는 성공했지만, iOS 빌드 자동화를 진행하면서 Certificates, Provisioning Signing, BitCode on/off, Auto Signing 등 Xcode 세팅에 대한 자동화에 애를 먹게 되었다.   
하지만 회사에 개발 CTO 님이 fastlane 이라는 자동화 툴에 대해 소개를 해주셨고, Jenkins Pipeline에 비해 훨씬 편하다는 것을 느끼게 되었다. 필요한 플러그인들을 선택적으로 terminal을 통해 설치가 가능했고 Fastfile을 수정하여 커스텀하게 lane을 구성해서 다양한 빌드환경에 대응이 가능했다. fastlane과 Jenkins 그리고 Unity Build Pipeline에 대한 전반적인 세팅 방법과 연동하는 방법에 대해 기록했다.

<br>

## 준비물 및 참고
1. Mac OS
2. Terminal 을 통해 HomeBrew와 Bundler가 설치되어야 함.
3. Xcode 및 Unity 설치

<br>
<br>

## 1. fastlane 설정 방법

#### fastlane 설치
1. HomeBrew로 fastlane 설치
   - Terminal을 켜고 "brew install fastlane"을 입력
   - 권한이 없을 경우 "sudo brew install fastlane" 입력

<br>

2. bundler 설치
   - 위의 경로에 그대로 "gem install bundler" 입력
   - gem 이 없다고 뜨면 gem을 설치해줘야 함.

<br>

<img src="/assets/img/post/unity/buildAuto01.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

3. 이후 fastlane을 설치할 폴더를 지정해준다.
   - cd 입력할 경로를 Terminal에 우선 입력해준다.
   ``` terminal
   //"cd 경로"
   cd /Users/..../GitLab/YourProject
   ```

   - 주의할 점은 fastlane은 Xcode의 커맨드 라인 툴을 이용하기 때문에 유니티를 사용할 경우 유니티 프로젝트 ios로 빌드한 폴더에 fastlane을 설치 해줘야 한다.
   - (다른방법이 있을수도 있음) 또한 실제로 빌드용으로 사용하는 Xcode 폴더와 fastlane으로 사용하는 Xcode 폴더를 구분해서 사용해야한다.   
   프로젝트 빌드를 매번 해야하므로.. 프로젝트 빌드를 하게 되면 Replace 로 빌드를 하게 될 것이고 그렇게 되면 분리 해놓지 않으면 FastFile이 날라가버린다..

<br>

4. fastlane 초기화
   - Xcode 프로젝트가 설치된 경로를 가리킨 후 "fastlane init" 입력
       <img src="/assets/img/post/unity/buildAuto02.png" width="1920px" height="1080px" title="256" alt="build1"><center>fastlane init 실행 결과물</center>
    - ```continue by pressing enter``` 를 계속 입력하다보면 Apple ID와 비밀번호를 입력하는 부분이 나온다. (이부분은 AppFile에서 수정가능)

<br>

#### fastlane 파일 구성
   - 모든 인증을 완료하면 지정한 경로에 "Gemfile", "Gemfile.lock", "fastlane/AppFile", "fastlane/FastFile" 파일들이 생성됩니다. 또한 추후에 설명할 플러그인을 설치하면 PluginFile 이 생성됩니다.
    <img src="/assets/img/post/unity/buildAuto03.png" width="1920px" height="1080px" title="256" alt="build1"><center>빌드한 Xcode 폴더 내부(fastlane설치되어있는곳)</center>   
    <img src="/assets/img/post/unity/buildAuto04.png" width="1920px" height="1080px" title="256" alt="build1"><center>fastlane 폴더 내부</center>
    
<br>

#### AppFile 설정
   - ```"#"```주석처리를 지운 뒤   
   app_identifier 를 입력해줍니다.  ```ex) com.companyname.projectname```   
   apple_id 또한 입력해줍니다.      ```ex) xxxx@coconev.co.jp```
    <img src="/assets/img/post/unity/buildAuto05.png" width="1920px" height="1080px" title="256" alt="build1"><center>AppFile</center>   

<br>

#### Plugin 설치

Unity 빌드  [fastlane-plugin-unity](https://github.com/safu9/fastlane-plugin-unity)  
AppCenter 업로드  [fastlane-plugin-appcenter](https://github.com/microsoft/fastlane-plugin-appcenter)  
Slack 봇  [fastlane-plugin-slack_bot](https://github.com/crazymanish/fastlane-plugin-slack_bot)  

<br>
<br>

- "sudo fastlane add_plugin xxx"  입력 후 설치가 완료되면 아래 사진 처럼 Pluginfile이 생성됩니다.
   
<img src="/assets/img/post/unity/buildAuto06.png" width="500px" height="500px" title="256" alt="build1"><center>Plugin File</center>   

<br>

<img src="/assets/img/post/unity/buildAuto07.png" width="1920px" height="1080px" title="256" alt="build1"><center>Plugin 설치시 보이는 Terminal 화면</center>   


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