---
title: Unity 빌드 자동화 - fastlane
date: 2023-08-03 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, 자동화, BuildPipeline, fastlane, Jenkins]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차

> [1. fastlane 설치 방법](#fastlane-설치)      
> [2. Plugin 설치 방법](#plugin-설치)     
> [3. FastFile 설정 방법](#fastfile-설정)      

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

   - ~~주의할 점은 fastlane은 Xcode의 커맨드 라인 툴을 이용하기 때문에 유니티를 사용할 경우 유니티 프로젝트 ios로 빌드한 폴더에 fastlane을 설치 해줘야 한다.~~
   - ~~(다른방법이 있을수도 있음) 또한 실제로 빌드용으로 사용하는 Xcode 폴더와 fastlane으로 사용하는 Xcode 폴더를 구분해서 사용해야한다.   
   프로젝트 빌드를 매번 해야하므로.. 프로젝트 빌드를 하게 되면 Replace 로 빌드를 하게 될 것이고 그렇게 되면 분리 해놓지 않으면 FastFile이 날라가버린다..~~
   - 결국 소스트리같은 SVN 툴로 관리를 하기 때문에 프로젝트 내부에 fastlane 을 설치하고 develop 브랜치나 master 브랜치에 merge 해주면 된다.
   - 단, 빌드머신이 mac OS 를 사용하고 있다!!(mac-mini 사용중) 윈도우는 fastlane이 안됨..

<br>

4. fastlane 초기화
   - Xcode 프로젝트가 설치된 경로를 가리킨 후 "fastlane init" 입력
       <img src="/assets/img/post/unity/buildAuto02.png" width="1920px" height="1080px" title="256" alt="build1">
    - ```continue by pressing enter``` 를 계속 입력하다보면 Apple ID와 비밀번호를 입력하는 부분이 나온다. (이부분은 AppFile에서 수정가능)

<br>

#### fastlane 파일 구성
   - 모든 인증을 완료하면 지정한 경로에 "Gemfile", "Gemfile.lock", "fastlane/AppFile", "fastlane/FastFile" 파일들이 생성됩니다. 또한 추후에 설명할 플러그인을 설치하면 PluginFile 이 생성됩니다.
    <img src="/assets/img/post/unity/buildAuto03.png" width="1920px" height="1080px" title="256" alt="build1">
    <img src="/assets/img/post/unity/buildAuto04.png" width="1920px" height="1080px" title="256" alt="build1">
    
<br>

#### AppFile 설정
   - ```"#"```주석처리를 지운 뒤   
   app_identifier 를 입력해줍니다.  ```ex) com.companyname.projectname```   
   apple_id 또한 입력해줍니다.      ```ex) xxxx@coconev.co.jp```
    <img src="/assets/img/post/unity/buildAuto05.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### Plugin 설치

| 종류 | 링크 |
| ------------ | ------------- |
| Unity 빌드 | [fastlane-plugin-unity](https://github.com/safu9/fastlane-plugin-unity)  |
| AppCenter 업로드 | [fastlane-plugin-appcenter](https://github.com/microsoft/fastlane-plugin-appcenter)  |
| Slack 봇 | [fastlane-plugin-slack_bot](https://github.com/crazymanish/fastlane-plugin-slack_bot)  |

<br>
<br>

- "sudo fastlane add_plugin xxx"  입력 후 설치가 완료되면 아래 사진 처럼 Pluginfile이 생성됩니다.
   
<img src="/assets/img/post/unity/buildAuto06.png" width="500px" height="500px" title="256" alt="build1">

<br>

<img src="/assets/img/post/unity/buildAuto07.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### FastFile 설정
- fastlane 의 최종관문 **FastFile**이다.   
Jenkins 를 이용해서 빌드 머신에 설치된 Unity 프로젝트와 fastlane을 가지고 원격 빌드 및 배포를 할 수 있다.   
Jenkins 의 *Executes Shell* 을 통해 fastlane init -> Addressable Build -> Unity Project Build -> AppCenter Upload 까지 가능하다.

> fastlane의 자세한 문서는 이쪽으로 ==> [ fastlane doc](https://docs.fastlane.tools/)   
FastFile은 ruby 언어로 되어 있기 때문에 Visual Studio Code를 사용하여 편집하였다.

<br>

1. platform
   - platform 이란 말그대로 iOS, Android 플랫폼을 의미한다. 주로 수동으로 빌드하면 Terminal, CI/CD로 빌드하면 Execute Shell 을 통해 빌드를 하므로 누가봐도 파악하기 쉬운 이름으로 만들어주자.
   ```ruby
   platform :android do
   platform :ios do
   ```

2. desc
   - desc는 말그대로 description 주석이다. 물론 fastlane log에도 출력이 된다.
   ```ruby
   platform: android do
      desc "Build AOS"
   end
   ```

3. lane
   - fastlane 이름에서도 알 수 있듯이 우린 이 lane 안에서 어떤 플러그인을 가지고 작업을 할 것인지 작성해줘야한다.   
   또한 여러개의 lane으로 나누어서 다양한 빌드 세팅과 빌드 환경을 구축할 수 있다.
   ```ruby
   platform :android do
      desc "Build AOS"
      lane :aos_build do
      end
   end
   ```

4. lane - plugin   
위에서 설명한 Plugin을 설치를 했다면, 다음과 같이 작성하면 된다.

   - **unity** 플러그인

   ```ruby
   # unity plugin
   unity(
   build_target: "Android",
   execute_method: "ProjectBuilder.BuildAndroid", # Unity Build Pipeline으로 사용될 static 함수
   unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" # Unity 버젼이 설치된 경로 입력
   project_path: "/Users/Admin/.jenkins/workspace/android_fastlane" # Unity Project 경로 입력
   )
   ```
<br>

   - **upload_appcenter** 플러그인 

   ```ruby
   # appcenter_upload
   appcenter_upload(
      api_token: "82acdkgd92391kdfajdkfj", # 본인의 appcenter - settings - API Token 을 입력
      owner_name: "coconefk_dev", # appcenter 관리자 이름 입력 (All apps - Owner 정보 나와있음)
      app_name: "toyverse_alpha_android", # 앱 이름 (유니티 이름 x 앱센터 상의 이름)
      file: "/Users/Build/toyverse_apk/toyverse.aab", # 최종 결과물의 경로 입력  .apk / .aab 확장자 명까지 같이 입력
      destinations: "*", # 모든 그룹에 배포. 넣은 이유는 상단 링크 참조
      destination_type: "group", # 그룹전용 의미. "shop" 은 구글 플레이 스토어 or 앱스토어 전용
      notify_testers: false, # settings 쪽에 email 알림 기능을 의미
      mandatory_update: true # 문서 참조 바람
   )
   ```
   <br>

   - **Android 최종본**

   ```ruby
   platform :android do
     desc "Build AOS"
     lane :aos_build do
       unity(
         build_target: "Android",
         execute_method: "ProjectBuilder.BuildAndroid",
         unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
         project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
       )
    end
    
    desc "Upload AppCenter"
    lane :upload_appcenter do
       appcenter_upload(
         api_token: "82acdkgd92391kdfajdkfj",
         owner_name: "coconefk_dev",
         app_name: "toyverse_alpha_android",
         file: "/Users/Build/toyverse_apk/toyverse.aab",
         destinations: "*",
         destination_type: "group",
         notify_testers: false,
         mandatory_update: true
       )
    end

    desc "Build Addressable"
    lane :addressable do
       unity(
         build_target: "Android",
         execute_method: "ProjectBuilder.BuildAddressable",
         unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
         project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
       )
    end
   end
   ```
   <br>

   - **iOS 빌드**

   ```ruby
   # build ios 유니티 프로젝트 빌드
   desc "Build Unity Project iOS"
   lane :unity_ios do
    unity(
      build_target: "iOS",
      execute_method: "ProjectBuilder.BuildIOS",
      unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
      project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
    )
   ```
   <br>

   - **Xcode 빌드**
   
   ```ruby
   desc "Xcode build GYM"
   lane :build_ios_gym do
    clear_derived_data
    gym(
      scheme: "Unity-iPhone",
      export_method: "enterprise",
      clean: true,
      output_directory: "/Users/coconevbusan/Build/toyverse_ipa"
    )
   ```
   - Xcode 빌드는 build_app 등 여러가지 명령이 있지만, gym 을 사용하는게 제일 간단하고 신경써줘야할 것들이 없었다.   
   특히 Auto Signing과 BitCode, 라이브러리 버젼 이슈를 일일히 설정해줘야했는데 gym을 통해 상당수 그런 작업들이 줄어들게 되었다.
   - GymFile 예시   
   Gym 을 사용하기 위해서는 GymFile을 세팅해줘야 한다. scheme와 enterprise 인지 development인지 설정, 프로비져닝 프로필 설정, ipa 저장 위치 설정, 이름 설정 등을 할 수 있다. 뭔가 FastFile에서 프로비져닝 프로필 설정하는 함수를 쓰면 잘 안됬어서 GymFile에 설정하고 Gym을 실행시키면 ipa 빌드까지 문제없이 잘 됨.

   ``` ruby
   scheme("Unity-iPhone")
   
   clean(true)
   export_method("enterprise")
   export_options({
      provisioningProfiles:{
            "com.coconev.toyverse.enterprise" => "toyverse_inhouse"
         }
      })
   output_directory("/Users/coconevbusan/Build/toyverse_ipa")
   output_name("toyverse_ios")
   ```

   - Certificate 등록에 관해서 [>>링크 클릭<<](https://ios-development.tistory.com/247)
   - Unity 에서 Xcode Auto Signing 및 Provisioning Profile 세팅
      - #1. Player Settings - Other Settings 하위에 Identification에 아래와 같이 설정 해준다.
   <img src="/assets/img/post/unity/unityauto01.png" width="1920px" height="1080px" title="256" alt="build1">
      - #2. Preferences - External Tools 하위에 Xcode Default Settings를 아래와 같이 설정 해준다. (mac OS에서는 settings 로 타고들어가야함)
   <img src="/assets/img/post/unity/unityauto02.png" width="1920px" height="1080px" title="256" alt="build1">
      - Applde Developer 에서 받을 각종 Certificates와 Provisioning Profile은 다운 받고 프로젝트에서 관리를 해주면 편하다. 특히 Android의 Keystore도 포함시켜서..
   <img src="/assets/img/post/unity/unityauto03.png" width="1920px" height="1080px" title="256" alt="build1">
 
 <br>