---
title: Mac 에서 배포한 iOS 앱 디버깅 로그 확인하는 방법 - Instruments
date: 2023-11-01 11:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [Mac, Instruments, iOS, Log]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

<br>
<br>

## 맥OS Instruments 로 TestFlight 로 배포한 앱 디버깅하기

>보통 ios 개발 단계에서는   
 Unity Project 빌드 -> Xcode 프로젝트 빌드 -> 연결한 테스트 폰에 직접 빌드해서 로그를 보면서 디버깅을 하거나 혹은 iap 로 추출하여 앱센터/테스트 플라이트에 배포 후 SRDebugger 같은 에셋으로 로그를 파악할 수 있었다.   
하지만, Instruments를 통해 아이폰을 연결하고 즉각적으로 로그를 볼 수 있는 방법이 있었다..!!

<br>

### 1. ⌘ (Command) + Space 를 입력하여 SpotLight 검색을 켜준다.

- instruments 검색 후 실행 해주기

![Desktop View](/assets/img/post/common/instruments01.png){: : width="600" .normal }

<br>
<br>

### 2. Instruments 프로파일링 템플릿을 Blank 혹은 Logging 으로 선택하기

![Desktop View](/assets/img/post/common/instruments02.png){: : width="600" .normal }

<br>
<br>

### 3. Blank 로 선택했다면, 우측애 + 버튼을 누르고 필터 목록을 켠다.

![Desktop View](/assets/img/post/common/instruments03.png){: : width="1900" .normal }

<br>
<br>

### 4. log 를 입력하고 os_log를 선택해서 등록해준다.

![Desktop View](/assets/img/post/common/instruments04.png){: : width="1900" .normal }

<br>
<br>

### 5. 상단 툴 바에 테스트할 Device 를 지정 -> 로그를 확인할 앱을 선택

- 테스트 디바이스에서 앱을 실행하고 instruments에서 좌측 상단에 빨간색 Record 버튼을 클릭해주면 로그 분석을 시작한다.

![Desktop View](/assets/img/post/common/instruments05_1.png){: : width="100" .normal }

<br>

![Desktop View](/assets/img/post/common/instruments05.png){: : width="1900" .normal }

<br>
<br>

### 6. os_log 를 펼쳐보면 하단에 앱에 포함된 플러그인, 프레임워크 들을 확인할 수 있다.

![Desktop View](/assets/img/post/common/instruments06.png){: : width="500" .normal }

<br>
<br>

### 7. 여기서 우리가 필요한 부분은 UnityFramework!   

- UnityFramework를 선택하면 하단 Messages에서 로그들이 출력된다.

![Desktop View](/assets/img/post/common/instruments07.png){: : width="1900" .normal }

<br>
<br>

### 8. 에디터 로그처럼 호출 스택은 파악할 수 없으니 로그를 잘 찍어놓고 테스트를 진행하자.

- 에러 메세지를 통해 각종 에러들을 파악할 수 있다.

![Desktop View](/assets/img/post/common/instruments08.png){: : width="1900" .normal }