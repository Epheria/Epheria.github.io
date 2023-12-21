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

   - 실제로 젠킨스에 만들어진 잡들
   ![Desktop View](/assets/img/post/unity/jenkins002.png){: : width="800" .normal }

   - 젠킨스 잡들을 도식화
   ![Desktop View](/assets/img/post/unity/jenkins004.png){: : width="800" .normal }

<br>

- 클라는 Alpha,Dev,Real 용 aos/ios 프로젝트 빌드
- 서버는 서버 API, CMS, RealTime 빌드가 가능했다.

<br>

## 젠킨스 짚고 넘어가기
- 젠킨스가 설치된 로컬의 폴더 경로 : ./jenkins - workspace 
- 젠킨스 대시보드에서 만든 잡들은 빌드머신의 로컬 workspace 경로에 하나씩 늘어난다.
> 시스템 용량을 엄청나게 잡아먹는다.. 괜히 빌드머신을 전용으로 하나 두는게 아닐정도로 잡아먹는다. 젠킨스 백업, 젠킨스 플러그인, 젠킨스 캐싱 데이터, 잡 프로젝트들 까지 다합치면 600GB 까지 늘어날 정도.. fastlane 을 못쓰게된 주범이기도하다..

- 아래 사진은 맥 파인더에 생성되어 있는 젠킨스 잡 프로젝트들이다. 저것들이 전부 다 유니티 프로젝트들인 것을 감안하면 얼마나 많은 용량을 차지하는지 확인할 수 있다.

   ![Desktop View](/assets/img/post/unity/jenkins001.png){: : width="800" .normal }

- 근데 왜 이렇게 하나하나 분리해서 용량도 많이 차지하고 비효율적으로 쓰느냐고 생각이 들것이다.
- 하지만 이렇게 사용하는 여러가지 이유가 있는데


- 1.. 핫픽스 브랜치

   ![Desktop View](/assets/img/post/unity/jenkins008.png){: : width="800" .normal }

   - 라이브 서비스를 시작하면 QA팀에서 찾지 못한 버그들, 부하로 인한 버그 등 여러가지 버그들이 발생하게 되는데
   - 이 때 라이브 서비스를 빌드한 브랜치를 기반으로 핫픽스 브랜치를 생성해서 빠르게 대응해야 한다.
   - 다른 컨텐츠를 개발중인 develop 브랜치는 절대 라이브 서비스에 내면 안되므로 어쩔 수 없이 라이브 서비스 기반 브랜치를 기반으로 가져가는것..
   - 이런 연유로 Dev, Real, Alpha 로 잡들이 나뉘게 된 것이다.

<br>

- 2.. iOS Certificates,Identifiers,Profiles 
   - iOS 개발을 하다보면 Ad hoc/In House, Enterprise, Distribution, Development 등으로 구분해야하는데
   - In House 용과 Enterprise 에서 애플 로그인이라던가 인 앱 구매 등 여러가지 기능을 넣을 수 있냐 없냐 나뉜다.
   - Enterprise 에서는 애플로그인과 인앱구매가 안되고 In House 에서는 테스트 해볼 수 있고.. 등
   - 이러한 이슈 때문에 나뉘는 이유도 있다.

<br>

- 3.. 마지막으로는 가장 큰 이유인데 본방 서버, Dev 서버로 나뉘기 때문이다. DB도 다르고 API도 다르기 때문에 분리해서 가져갸아한다.

<br>
<br>

## 젠킨스 플러그인 및 환경변수
- 젠킨스를 처음부터 세팅하는 방법은 인터넷에 많으니 찾아보길 바라고
- 간단하게 필수적인 플러그인과 환경변수들을 세팅하는 방법을 적어놓고자 한다.
- 위치 : Jenkins Dashboard - Jenkins 관리 - System Configuration

   ![Desktop View](/assets/img/post/unity/jenkins003.png){: : width="800" .normal }


- #### 플러그인
   - 플러그인은 Jenkins 기능을 확장하기 위해 필수적으로 받아야한다.
   - 대표적으로 Xcode integration, Unity3d plugin, App Center, Slack Notifications, Gradle, GitLab, Github Branch Source, Ant 등이 있다.

   ![Desktop View](/assets/img/post/unity/jenkins005.png){: : width="800" .normal }

- #### 환경 변수
   - 환경변수는 젠킨스 전역으로 쓰일 키 값을 세팅한다던가, Slack 이나 Apple Developer 팀 ID 등을 세팅해놓는데 필요하다.
   - 전역으로 쓰일 키값들은 빌드머신 프로젝트의 경로, 유니티 설치 경로, 앱센터에 apk,ipa를 올릴 경로 등이 있다.

   ![Desktop View](/assets/img/post/unity/jenkins009.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins006.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins007.png){: : width="800" .normal }

<br>

## 젠킨스 활용법
- 젠킨스를 빌드할 때 많은 젠킨스 파이프라인 스크립트, 잡 내부 구성에서 General에 플러그인들을 추가해서 빌드를 한다던가 등 여러가지 방법이 있지만
- 개인적으로 **Execute shell** 스크립트로 빌드하는게 가장 간편하고 쉬웠었다.
- 빌드 유발, 빌드 환경, 빌드 후 조치는 건드릴 필요가 없다. 왜냐하면 빌드의 PostProcess 처리는 전부 스크립트로 하기 있기 때문이다.
> [빌드 스크립트 참조](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/)   
  [fastlane 참조](https://epheria.github.io/posts/UnityBuildAuto/)

#### General 탭 - 파라미터 추가
- string, bool 값으로 파라미터를 생성하여 빌드할 때 활용이 가능하다.
- 예를 들어, 젠킨스 빌드 시 특정 브랜치를 빌드하고 싶다면 branch name 을 설정하여 해당 브랜치의 최신 버전 빌드가 가능하다.

   ![Desktop View](/assets/img/post/unity/jenkins010.png){: : width="400" .normal }

- bool 값의 경우 iOS 에서 Apple Login이 가능한 InHouse 일 때만 사용이 가능해서 (Enterprise 에서는 빌드가 터짐) 특정 환경에서 빌드할 때 필요한 파라미터를 설정할 수 있다.

   ![Desktop View](/assets/img/post/unity/jenkins011.png){: : width="400" .normal }

- 파라미터와 함께 빌드를 클릭하면 추가한 파라미터가 다음과 같이 세팅된다.
- 여기서 빌드를 진행하고 싶은 브랜치이름과 bool 값을 설정하면 된다.

   ![Desktop View](/assets/img/post/unity/jenkins014.png){: : width="400" .normal }


#### General 탭 - Git 브랜치
- 위에서 파라미터로 넣은 브랜치 이름을 해당 기능을 사용해서 깃 브랜치를 타고 들어가서 빌드를 진행한다.
- 리포지토리 URL을 제대로 넣어줘야한다.

   ![Desktop View](/assets/img/post/unity/jenkins012.png){: : width="400" .normal }
      
   ![Desktop View](/assets/img/post/unity/jenkins013.png){: : width="400" .normal }

#### Execute shell
- 프로젝트 빌드를 위해 shell script 를 실행한다. 백그라운드로 돌아가는 터미널 느낌..
- 명령어가 터미널에서 사용할 수 있는 명령어들이다.

   ![Desktop View](/assets/img/post/unity/jenkins015.png){: : width="700" .normal }

<br>

#### iOS 빌드 스크립트

- aos 빌드에 비해 복잡한 부분이 많다. 특히 유니티 프로젝트 -> Xcode 프로젝트 -> ipa 빌드 순서가 있어서 복잡하다.

```
rm -rf /Users/coconevbusan/Build/toyverse_ipa
mkdir /Users/coconevbusan/Build/toyverse_ipa
```
- 우선 최종적으로 ipa 파일로 뽑혀나오는 경로 내부에 있는 모든 파일을 삭제해주고 폴더를 생성한다.

```
pwd
locale
export LANG=en_US.UTF-8
locale
```
- [xcworkspace 생성되지 않는 이슈](https://epheria.github.io/posts/Unityxcworkspace/) 때문에 추가된 부분

```
XCODE_PATH=/Users/coconevbusan/Xcode
ENTITLEMENTS=Entitlements.entitlements
TMP_FILE=tmp.txt

rm -rf ${XCODE_PATH}
mkdir ${XCODE_PATH}
```
- 유니티 빌드도 진행하기 때문에 Xcode 프로젝트가 생성될 경로 역시 초기화해준다.

```
echo ------------------------------------- FASTLANE_SETTING
rm -rf "${WORKSPACE}/fastlane/Fastfile"
rm -rf "${WORKSPACE}/fastlane/Gymfile"
cp "${WORKSPACE}/fastlane/Fast/Fastfile_enterprise" "${WORKSPACE}/fastlane/Fastfile"
cp "${WORKSPACE}/fastlane/Gym/Gymfile_enterprise" "${WORKSPACE}/fastlane/Gymfile"
```
- fastlane 의 fastfile, gymfile 을 세팅해준다.
- 여기서 WORKSPACE 경로는 현재 젠킨스 잡의 로컬 경로를 의미한다. 따로 파라미터를 추가할 필요가 없음.

```
echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
```
- fastlane init 실행하여 fastlane 초기화

```
echo ------------------------------------- FIREBASE_SETTING
rm -rf "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
cp "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Config/GoogleService-Info_enterprise.plist" "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
echo ------------------------------------- UNITY IOS PROJECT BUILD 
/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity -projectPath "/Users/coconevbusan/.jenkins/workspace/(DEV)ios" -batchmode -nographics -quit -buildTarget iOS -executeMethod ProjectBuilder.BuildIOS_Dev -logfile "" build_num:${BUILD_NUMBER}
```
- 유니티 프로젝트 빌드를 batchmode 로 실행해준다.
- 원래 fastlane 에서 유니티 프로젝트 빌드를 하려고 했지만, 여러가지 제약사항이 많아서 유니티 프로젝트 빌드는 batchmode 로 변경했음.

```
echo ------------------------------------- Pod Install
cd /Users/coconevbusan/Xcode
/opt/homebrew/bin/pod install
cd "/Users/coconevbusan/.jenkins/workspace/(DEV)ios"
if "${DEL_APPLE_LOGIN}"; then
	echo ------------------------------------- Delete Sign in Apple
	/usr/bin/sed '7,10d' ${XCODE_PATH}/${ENTITLEMENTS} > ${XCODE_PATH}/${TMP_FILE}
	rm -rf ${XCODE_PATH}/${ENTITLEMENTS}
	cp ${XCODE_PATH}/${TMP_FILE} ${XCODE_PATH}/${ENTITLEMENTS}
fi
```
- pod install 을 해줘야 Xcode 프로젝트 빌드가 진행된다.

```
echo ------------------------------------- XCODE PROJECT BUILD
/opt/homebrew/bin/fastlane ios build_ios_gym
echo ------------------------------------- UPLOAD APPCENTER
/opt/homebrew/bin/fastlane ios upload_appcenter
```
- gym file 을 사용하여 xcode 빌드를 실행한다. 
- 앱센터에 업로드하는 부분은 fast file 안에 있음

<br>

#### AOS 빌드 스크립트

```
rm -rf /Users/coconevbusan/Build/toyverse_apk
mkdir /Users/coconevbusan/Build/toyverse_apk
pwd
chmod 755 ./fastlane/change_build_num.sh
./fastlane/change_build_num.sh ${BUILD_NUMBER}

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
#echo ------------------------------------- ADDRESSABLE
#/opt/homebrew/bin/fastlane android addrressable 
echo ------------------------------------- ANDROID BUILD 
#/opt/homebrew/bin/fastlane android android
/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity -projectPath "/Users/coconevbusan/.jenkins/workspace/(DEV)android" -batchmode -nographics -quit -buildTarget Android -executeMethod ProjectBuilder.BuildAndroid_Dev -logfile "" build_num:${BUILD_NUMBER}
echo ------------------------------------- UPLOAD APPCENTER
/opt/homebrew/bin/fastlane android upload_appcenter
```

<br>

#### 어드레서블 스크립트

- iOS

```
pwd
locale
export LANG=en_US.UTF-8
locale

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
echo ------------------------------------- CLEAR ADDRESSABLE
rm -rf ${WORKSPACE}/ServerData/iOS/*
echo ------------------------------------- ADDRESSABLE
"/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" -projectPath "/Users/coconevbusan/.jenkins/workspace/(DEV)ios_addressable" -batchmode -nographics -quit -buildTarget iOS -executeMethod ProjectBuilder.BuildAddressable_IOS_Dev -logfile
echo ------------------------------------- S3 UPLOAD
chmod 775 ${WORKSPACE}/fastlane/upload_addressable_s3.sh
${WORKSPACE}/fastlane/upload_addressable_s3.sh ${WORKSPACE}/ServerData/iOS ios ${RESOURCE_VERSION} dev alpha
```


- AOS

```
pwd

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
echo ------------------------------------- CLEAR ADDRESSABLE
rm -rf ${WORKSPACE}/ServerData/Android/*
echo ------------------------------------- ADDRESSABLE
"/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" -projectPath "/Users/coconevbusan/.jenkins/workspace/(DEV)android_addressable" -batchmode -nographics -quit -buildTarget Android -executeMethod ProjectBuilder.BuildAddressable_AOS_Dev -logfile
echo ------------------------------------- S3 UPLOAD
chmod 775 ${WORKSPACE}/fastlane/upload_addressable_s3.sh
${WORKSPACE}/fastlane/upload_addressable_s3.sh ${WORKSPACE}/ServerData/Android aos ${RESOURCE_VERSION} dev alpha
```