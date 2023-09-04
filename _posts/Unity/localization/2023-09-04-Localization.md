---
title: Unity Localization 연동
date: 2023-09-04 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [Unity, Localization]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---
## 목차
- [1. Localization 설치](#1-localization-설치)
- [2. Localization 환경 설정](#2-localization-환경-설정)
- [3. Google Sheets 연동하기](#3-google-sheets-연동하기)
- [4. UGUI 에서 사용방법](#4-localization을-ugui-에서-사용하는-방법)

---

## Localization 연동 및 사용 방법

- Localization (현지화)는 게임 서비스에 있어 필수적인 요소이다. Text Mesh Pro 와 결합하여 String Event로 UI 에서 사용하는 모든 텍스트를 설정한 언어에 따라 변경할 수 있는 기능을 가지고 있다.

<br>

## 1. Localization 설치

- Package Manager 에서 Localization을 설치 해주자.

![Desktop View](/assets/img/post/unity/localization01.png){: .normal }

## 2. Localization 환경 설정

- Window - Asset Management - Localization Table 을 통해 String Table과 Asset Table을 생성/관리 할 수 있다.

![Desktop View](/assets/img/post/unity/localization02.png){: : width="500" .normal }

<br>

- 상단 탭을 보면 NewTableCollection, EditTableCollection 두 개가 있는데 각각 생성/수정을 의미한다.

![Desktop View](/assets/img/post/unity/localization03.png){: : width="700" .normal }

<br>

- String Table은 string key 값을 참조해서 각 Locale 언어들을 번역한 테이블을 의미하고   
Asset Table은 Font, Font Material 등을 등록해서 사용이 가능하다.

![Desktop View](/assets/img/post/unity/localization04.png){: : width="700" .normal }

<br>

- Edit Table 모드에서 하단의 Add New Entry 를 클릭하여 테이블 row를 추가할 수 있다. 

![Desktop View](/assets/img/post/unity/localization05.png){: : width="500" .normal }

<br>

- 또한 Locale Generator 를 클릭하면 각 나라 언어들을 선택하여 추가할 수 있는데 각 나라별로 고유의 코드 또한 존재한다.

![Desktop View](/assets/img/post/unity/localization06.png){: : width="400" .normal }

<br>
<br>

---

- Create 를 누르면 테이블들의 설치 폴더 경로 지정을 할 수 있다.
- 그러면 지정한 폴더에 Table, Table Shared Data, Locale 테이블들이 생성된다.

![Desktop View](/assets/img/post/unity/localization07.png){: : width="700" .normal }
![Desktop View](/assets/img/post/unity/localization08.png){: : width="700" .normal }

<br>

- String Collection Table 파일을 자세히 살펴보자.
- Extensions 리스트를 추가하면 CSV 와 Google Sheets를 등록할 수 있다.
- 여기서 다루는 내용은 Google Sheet 를 등록하는 법이다.

![Desktop View](/assets/img/post/unity/localization09.png){: : width="400" .normal }
![Desktop View](/assets/img/post/unity/localization10.png){: : width="400" .normal }

<br>
<br>

## 3. Google Sheets 연동하기

- 먼저 Project 탭에서 - Create - Localization - Google Sheet Service 파일을 생성해준다.

![Desktop View](/assets/img/post/unity/localization11.png){: : width="700" .normal }

<br>

- 그러면 인스펙터창을 통해서 Authentication 권한을 설정하는 드랍다운이 확인할 수 있다.
- Google Cloud Service를 통해 구글 O Auth를 입력할지 or API Key를 입력할지 선택하면 된다. (난 O Auth를 사용함)

![Desktop View](/assets/img/post/unity/localization12.png){: : width="500" .normal }

<br>

## OAuth 권한 등록하는 방법
- 우선 [Google Cloud 링크](https://console.cloud.google.com/welcome?project=cogent-tide-354007) 로 접속해서
- Google Cloud 회원가입 및 동의를 진행하고 
- 메뉴창 - API 및 서비스 - OAuth 동의 화면을 클릭 해주자.

![Desktop View](/assets/img/post/unity/localization13.png){: : width="500" .normal }

<br>

- 그리고 프로젝트 이름 옆에 있는 "앱 수정"을 눌러준다.

![Desktop View](/assets/img/post/unity/localization14.png){: : width="500" .normal }

<br>

- 앱 등록 수정 화면에서 앱 이름과 사용자 지원 메일을 입력해주고
- 3번 항목 테스트 사용자까지 들어가준다.
- 3번 테스트 사용자에서 +ADD USERS를 통해 꼭! 테스트 사용자를 등록해줘야 한다. => 그래야 Google Sheets 접근 권한이 생긴다.

![Desktop View](/assets/img/post/unity/localization15.png){: : width="500" .normal }
![Desktop View](/assets/img/post/unity/localization16.png){: : width="500" .normal }

<br>

- 위의 단계를 완료하면 사용자 인증 정보 탭으로 이동해준다.

![Desktop View](/assets/img/post/unity/localization17.png){: : width="300" .normal }

<br>

- OAuth 클라이언트 ID 와 Password가 생성된 것을 확인할 수 있다.
- 클라이언트 이름을 클릭하면

![Desktop View](/assets/img/post/unity/localization18.png){: : width="1980" .normal }

<br>

- 최종적으로 클라이언트 ID와 Password가 생성된것을 확인할 수 있다.

![Desktop View](/assets/img/post/unity/localization19.png){: : width="1980" .normal }

<br>

- 다시 유니티로 돌아와서 아까 생성한 Google Sheet Service 인스펙터에서 Authentication 을 OAuth 로 선택해준다.
- 위에서 복사한 Client ID와 Secret 을 입력해주고 "Authorize..." 버튼을 누르면 자동으로 웹으로 연결되어 계정 인증을 진행한다.

![Desktop View](/assets/img/post/unity/localization20.png){: : width="600" .normal }

<br>

- 이후 생성했던 Localize Table (String Table Collection) 파일의 인스펙터에 생성한 Extensions 리스트에 Google Sheets Extension 을 추가하고
- Sheets Service Provide 위에서 생성한 Google Sheet Service 파일을 등록해준다.

![Desktop View](/assets/img/post/unity/localization10.png){: : width="500" .normal }

<br>

- Create New SpreadSheet를 통해서 내 구글 드라이브에 새로운 Google Spread Sheets 를 생성할 수도 있고
- SpreadSheet id 와 Sheet id를 입력해서 구글 드라이브에 이미 존재하는 Google Spread Sheets를 가져올 수도 있다.

![Desktop View](/assets/img/post/unity/localization21.png){: : width="700" .normal }

## 주의할점!!

1. 사용자 API에 Google Sheets API를 등록해줘야한다.
2. 생성한 Google Spread Sheets의 공유 설정을 모두에게 공개 or 사용자 추가를 해줘야한다.

- 위 과정을 진행해야만 유니티 상에서 Localization Push / Pull 이 가능해짐

![Desktop View](/assets/img/post/unity/localization22.png){: : width="1200" .normal }

![Desktop View](/assets/img/post/unity/localization23.png){: : width="700" .normal }

<br>
<br>

- 연동한 Google Spread Sheets 를 불러오기 전에
- 우선 칼럼들을 매핑해줘야한다.
- 매핑을 추가하는 형태는 Key 칼럼과 각종 언어별로 번역된 로컬 칼럼의 갯수만큼 추개해주면 된다.

![Desktop View](/assets/img/post/unity/localization21.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization24.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/localization25.png){: : width="400" .normal }

<br>

- 각 칼럼과 로컬 칼럼을 추가한 모습

![Desktop View](/assets/img/post/unity/localization26.png){: : width="400" .normal }

<br>

- 매핑이 완료되면 Pull 버튼을 눌러서 Google Spread Sheets 정보를 가져올 수 있다.
> Push는 비추천하는데.. 이유는 일단 누가 Push를 했는지 로그가 남지 않으며   
Push 와 Pull 이 꼬일 수도 있기에 Google Spread Sheets 상에서 수정한 것을 오로지 Pull로 가져와서 클라이언트에 동기화 시키는 방법을 주로 사용한다.
- 또한 Unity Editor 상에서 Table 정보를 수정하는 것도 권장하지 않음!

![Desktop View](/assets/img/post/unity/localization27.png){: : width="400" .normal }

<br>

- Google Spread Sheets 상의 Localization Table 사진

![Desktop View](/assets/img/post/unity/localization28.png){: : width="1980" .normal }

<br>

- Unity Editor Table Collection 상에서의 사진

![Desktop View](/assets/img/post/unity/localization29.png){: : width="700" .normal }

<br>
<br>

---

## 4. Localization을 UGUI 에서 사용하는 방법

#### 필수조건
1. UGUI의 텍스트 형태가 TextMeshPro - Text (UI) 이여야 한다.
2. Localize String Event Component 가 사용할 오브젝트에 등록되어 있어야한다.
3. 이외에 font material, font 등을 수정하고 싶으면 다음과 같은 클래스를 만들어 컴포넌트로 등록해주자.

```csharp
```

```csharp
```

<br>
<br>

### Component로 활용 하는 방법

- 컴포넌트에 Localize String Event 를 추가해준다.

![Desktop View](/assets/img/post/unity/localization30.png){: : width="400" .normal }

<br>

- String Reference 를 클릭하면 추가하고자 하는 테이블의 Key 값을 검색하고 할당할 수 있다.
- 등록하면 자동으로 Table Collection 까지 할당 된다.
- 또한 각 로컬 테이블에서 각 언어로 바뀌면 어떤 방식으로 할당될지도 간략하게 표시되고
- Update String 에 어느 TMP text 를 지정해서 업데이트 해줄지도 할당된다.

![Desktop View](/assets/img/post/unity/localization31.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization32.png){: : width="400" .normal }

<br>

- 추가적으로 font 와 font material 도 바꾸고 싶다면
- Add Component 혹은 Localize Extension을 사용하여 등록하면 된다.
- 인게임 설정 혹은 에디터상에서 언어변경을 해주면 해당 UGUI의 텍스트는 자동으로 바뀐다..

![Desktop View](/assets/img/post/unity/localization33.png){: : width="400" .normal }

<br>
<br>

### Script로 활용 하는 방법