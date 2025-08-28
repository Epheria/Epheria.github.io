---
title: Unity iOS - Xcode Code Signing (Certificates and Provisioning Profile)
date: 2024-05-03 10:00:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Xcode, Code Signing, Certificates, Provisioning Profile, iOS]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true  
use_math: true
mermaid: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

## 목차
> [Apple Certificate](#apple-certificates---애플-인증서)      
> [App ID 생성 방법](#app-id-identifier-생성-방법)     
> [Device 등록 방법](#device-등록-방법)     
> [Provisioning Profile 생성 방법](#provisioning-profile-생성-방법)  

<br>
<br>

## Apple Certificates - 애플 인증서

- 애플이 출시한 기기들(하드웨어)에 소프트웨어(앱, 프로그램등)를 동작 시키기 위해 실제로 앱이 실행될 때 마다 애플로부터 인증을 받았는지 확인을 하는 절차를 거친다.
- 매번 요청하고 관리하기가 번거롭기 때문에 [Apple Developer](https://developer.apple.com/account) 에서 인증서를 받으면 애플이 개발자를 신뢰하여 앱을 실행할 수 있는 권한을 부여해준다.

<br>

## 인증서 받는 방법

#### 1. Key 만들기 (인증 사인 요청)

![Desktop View](/assets/img/post/unity/ioscodesigning01.png){: : width="800" .normal }

- 먼저 인증서를 받기 위해서는 cmd + space -> 키체인 접근을 검색하거나 애플리케이션 - 기타 - 키체인 접근 앱을 켜주자.

<br>

- 이후 **키체인 접근**에서 **CSR(Certificate Signing Request)** 를 먼저 생성해야한다.

![Desktop View](/assets/img/post/unity/ioscodesigning02.png){: : width="800" .normal }

- 상단 메뉴에서 키체인 접근 -> 인증서 지원 -> 인증 기관에서 인증서 요청을 클릭한다.

<br>

- **인증기관에 인증서 요청**을 하게되면 다음 작업을 수행한다.
> 1. 인증서의 **공개키**와 **개인키**를 자동으로 생성한다. 생성된 키는 키체인 앱에서 "키" 카테고리에서 확인할 수 있다. (잘 보관해야함)      
> ![Desktop View](/assets/img/post/unity/ioscodesigning05.png){: : width="500" .normal }       
> 2. 애플에 보낼 **CertificateSigningRequest.certSigningRequest** 파일을 생성한다. 이파일은 이름, 이메일 공개키를 포함하고 있고 개인키를 이용하여 Sign을 진행하게 된다.

<br>

![Desktop View](/assets/img/post/unity/ioscodesigning03.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/ioscodesigning04.png){: : width="500" .normal }

- 위 과정을 거치면 키체인 접근의 키에 방금 만든 일반 이름으로 공개키, 개인키가 만들어진다.

<br>
<br>

#### 2. Certificate 발급 받기

- [Apple Developer](https://developer.apple.com/account) -> 인증서 (Certificates) 클릭하기

![Desktop View](/assets/img/post/unity/ioscodesigning06.png){: : width="800" .normal }

<br>

---

![Desktop View](/assets/img/post/unity/ioscodesigning07.png){: : width="800" .normal }

- Certificates, Identifiers & Profiles 탭이 나온다.
- 좌측 탭에서 각종 Certificates, Identifiers, Profiles 들을 만들거나 테스트용 Device 들을 등록할 수 있다.
- "+" 버튼을 눌러 Certificates 를 먼저 생성해주자.

<br>

---

- 기본적으로 iOS Certificate 는 Enterprise 를 제외하고 Development(개발)용과 Distribution(배포)용으로 나뉜다.
> [Apple Developer Program(출시용), Apple Developer Enterprise Program(사내 테스트용) 에 관한 차이점](https://developer.apple.com/kr/support/roles/)      
> 요약하자면 Apple Developer Program(출시용)은 실제 앱스토어 등록용, Enterprise 는 회사 내부 테스트 목적으로 사용      
> 물론  Apple Developer Program 에서 Development 로 Certificate 를 만들면 테스트 플라이트를 통해 테스트가 가능하다! (꼭 출시 목적이 아니라는 말)

<br>

- Certificate 를 만들 때 Enterprise 와 Developer(출시용)의 차이점은 다음과 같다.

![Desktop View](/assets/img/post/unity/ioscodesigning22.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning23.png){: : width="800" .normal }

_Apple Developer Program_

<br>

---

- Apple Developer Program 에서만 Development(개발)용과 Distribution(배포)용으로 나뉘는 점을 확인하자.

![Desktop View](/assets/img/post/unity/ioscodesigning10.png){: : width="800" .normal }

<br>

---

- CSR(CertificateSigningRequest) 를 등록 후 Continue 를 통해 계속 진행

![Desktop View](/assets/img/post/unity/ioscodesigning11.png){: : width="800" .normal }

<br>

---

- 생성된 Certificate 를 다운로드 받은 뒤 **더블 클릭** 해주면 KeyChain 에 자동으로 등록된다.

![Desktop View](/assets/img/post/unity/ioscodesigning12.png){: : width="800" .normal }


![Desktop View](/assets/img/post/unity/ioscodesigning13.png){: : width="800" .normal }

- 위의 과정까지 완료하면 애플에서 인증을 한 개발자가 된 것이다.
- 하지만 앱을 Sign 할 수 있도록 허가만 받았을 뿐, 디바이스가 나를 개발자로서 신뢰하고 있는지 확인시켜줘야한다.
- 새로 생성한 Certificate 인증서와 iOS 기기를 연결 시켜줘야 하는데 이것을 **Provisioning Profile (프로비저닝 프로파일)** 이라고 한다.

<br>
<br>

---

## Provisioning Profile - 프로비저닝 프로파일

- Provisioning Profile은 App ID, Certificate, Device 정보를 가지고 있으며 iOS 기기와 애플 Certificate 를 연결시켜주는 역할을 한다.

![Desktop View](/assets/img/post/unity/ioscodesigning14.png){: : width="800" .normal }

- 1. App ID : 앱 스토어에 등록되는 Bundle ID 정보가 들어있음.
- 2. Certificate : Identifier 를 만들 때 위에서 만든 인증서를 넣어주면 됨 -> 그 Identifier 를 Provisioning Profile 을 만들 때 넣어주면 됨
- 3. Device : 테스트용으로 사용할 디바이스 UDID.

- Provisioning Profile 을 생성하기 전에 앞서 생성한 Certificate 를 기반으로 App ID(Identifier)와 Device 등록 절차가 필요하다.
- 우선 App ID 를 만들어보자.

<br>

---

#### App ID (Identifier) 생성 방법

- 좌측 탭에서 Identifier 를 클릭 -> "+" 버튼을 눌러 App ID 생성으로 진입하기

![Desktop View](/assets/img/post/unity/ioscodesigning15.png){: : width="800" .normal }

<br>

---

- App IDs 선택하여 Continue

![Desktop View](/assets/img/post/unity/ioscodesigning16.png){: : width="800" .normal }

<br>

---

- 원하는 형태의 타입 선택 (App, App Clip) - 여기서는 App
- 참고로 Enterprise 는 이 단계가 없음.

![Desktop View](/assets/img/post/unity/ioscodesigning17.png){: : width="800" .normal }

<br>

---

- Description 에 이 프로파일이 무슨 역할을 하는지 명시해주고 Bundle ID 를 적어준다.
- 애플 공식 추천 네이밍은 이렇다.
> We recommend using a reverse-domain name style string (i.e., com.domainname.appname). It cannot contain an asterisk (*).

![Desktop View](/assets/img/post/unity/ioscodesigning18.png){: : width="800" .normal }

<br>

---

- 사용할 Capabilities 를 꼭 체크해주자. (나중에 수정이 가능함)
- 주로 Push Notifications, Sign in with Apple 을 많이 사용한다. (앱 초기 세팅 시 자주 깜빡하고 안넣는 경향이 있음)

![Desktop View](/assets/img/post/unity/ioscodesigning19.png){: : width="800" .normal }

- Continue 를 누른 뒤 Register 를 해주면 Identifier에 App ID가 등록 된다!

<br>

---

#### Device 등록 방법

- Device 클릭 -> "+" 버튼을 눌러 디바이스 등록 진입

![Desktop View](/assets/img/post/unity/ioscodesigning20.png){: : width="800" .normal }

<br>

---

- Device Name 에는 기기 종류, 모델 같은 이름을 써주면 더 좋다.
- UDID 는 기기 고유 ID 로 설정에서 확인이 가능함

![Desktop View](/assets/img/post/unity/ioscodesigning21.png){: : width="800" .normal }

<br>

---

#### Provisioning Profile 생성 방법

- 이제 모든 준비 (Certificate, App ID, Device) 들이 끝났으니 Provisioning Profile 을 만들어야한다.
- Profiles 클릭 후 -> "+"를 눌러 Provisioning Profile 생성 진입

![Desktop View](/assets/img/post/unity/ioscodesigning24.png){: : width="800" .normal }

<br>

---

- Provisioning Profile 을 만들 때 Enterprise 와 Developer(출시용)의 차이점은 다음과 같다.

![Desktop View](/assets/img/post/unity/ioscodesigning08.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning09.png){: : width="800" .normal }

_Apple Developer Program_

<br>

- 참고로 Ad Hoc 은 내부 테스터들을 등록하여 배포가 가능하고, In House 는 App Center 같은 곳에 ipa 파일을 등록하여 배포가 가능하다.

<br>

---

- 개발용 or 배포용 선택 후 Continue

![Desktop View](/assets/img/post/unity/ioscodesigning25.png){: : width="800" .normal }

<br>

---

- 방금 만들었던 App ID 를 선택 후 Continue

![Desktop View](/assets/img/post/unity/ioscodesigning26.png){: : width="800" .normal }

<br>

---

- 초반에 만든 Certificate 인증서 선택 후 Continue

![Desktop View](/assets/img/post/unity/ioscodesigning27.png){: : width="800" .normal }

<br>

---

- Device 를 선택 해주고

![Desktop View](/assets/img/post/unity/ioscodesigning28.png){: : width="800" .normal }

<br>

---

- Provisioning Profile 이름을 적어주고 Generate 를 통해 만들면 된다.

![Desktop View](/assets/img/post/unity/ioscodesigning29.png){: : width="800" .normal }

<br>

---

- 이후 Provisioning Profile 을 다운로드하여 Unity Project 내부에 넣어주자!
- 토이버스는 Keystore 라는 폴더 내부에 Development, Enterprise, App Store 용 으로 구분하여 폴더링을 나눠놨다.

![Desktop View](/assets/img/post/unity/ioscodesigning31.png){: : width="500" .normal }

<br>

---

- 각 폴더 내부에는 Certificate, Provisioning Profile 이 들어가있다.

![Desktop View](/assets/img/post/unity/ioscodesigning30.png){: : width="800" .normal }

<br>

---

- Provisioning Profile 의 경우 유니티 프로젝트를 빌드 하고 Xcode 프로젝트로 뽑아 낼 때 Automatically Manage Signing 옵션을 체크할 때 Project Setting, Preference 에서 등록을 할 수 있기 때문에 이렇게 넣어놓은것임. 자세한 설명은 [Xcode 빌드 파이프라인 포스트를 참조](https://epheria.github.io/posts/UnityXcodeBuildPipeline/)

![Desktop View](/assets/img/post/unity/ioscodesigning32.png){: : width="800" .normal }

- 이로써 Code Signing 작업이 끝났다!

<br>

---

- 만약 에러가 난다면 Bundle Identifier 가 맞는지 확인해보자!
- 복수의 Provisioning Profile 을 가질 수 있기 때문에 연동한 App ID 와 실제 컴파일 하려는 프로젝트의 Bundle ID 가 일치해야한다.
