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
- [5. Asset Table 설정 방법](#5-asset-table-설정-방법)
- [6. Localization 텍스트 커스터마이징 방법](#6-로컬라이제이션-커스터마이징-방법)

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
using System;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Localization;
using UnityEngine.Localization.Components;

namespace Base
{
    [AddComponentMenu("Localization/Asset/" + nameof(LocalizedTmpFontEvent))]
    public class LocalizedTmpFontEvent : LocalizedAssetEvent<TMP_FontAsset, LocalizedTmpFont, UnityEventTmpFont> {}

    [Serializable]
    public class UnityEventTmpFont : UnityEvent<TMP_FontAsset> {}
}
```

```csharp
using System;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Localization;
using UnityEngine.Localization.Components;
using Cysharp.Threading.Tasks;

namespace Base
{
    [AddComponentMenu("Localization/Asset/" + nameof(LocalizedTmpFontMaterialEvent))]
    public class LocalizedTmpFontMaterialEvent : LocalizedAssetEvent<Material, LocalizedMaterial, UnityEventTmpFontMaterial>
    {
        private TextMeshProUGUI _targetText;

        private void Start()
        {
            _targetText = GetComponent<TextMeshProUGUI>();
        }

        protected override async void UpdateAsset(Material localizedAsset)
        {
            if (_targetText == null)
            {
                _targetText = GetComponent<TextMeshProUGUI>();
            }

            if (_targetText != null)
            {
                await UniTask.WaitUntil(() => localizedAsset);
                _targetText.fontMaterial = localizedAsset;    
            }
            else
            {
                Debug.LogError("[ LocalizedTmpFontMaterialEvent / UpdateAsset ] TextMeshPro is null");
            }
        }
    }

    [Serializable]
    public class UnityEventTmpFontMaterial : UnityEvent<Material> {}
}
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

- 만약 UGUI 가 동적으로 생성된다면 Compnent에서 직접 할당하지 않고 스크립트로 호출해서 처리가 가능하다.
- 아래 사진 처럼 Update String 을 할당해주면 된다. 동적으로도 가능

![Desktop View](/assets/img/post/unity/localization34.png){: : width="400" .normal }

<br>

#### Script 예시

![Desktop View](/assets/img/post/unity/localization35.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization36.png){: : width="600" .normal }

<br>

- LocalizeStringEvent 컴포넌트를 GetComponent 해서 SetEntry(key) 메소드를 사용해주면 된다.
- Table Collection 에 등록된 key 값을 찾아 현재 설정된 locale code 에 알맞게 UGUI TMP text 에 할당해주면된다.

<br>
<br>

#### 추가적으로 동적으로 텍스트의 내부 데이터 수정하는 방법

- balance, username 등 내부 데이터가 동적으로 바뀌는 경우 다음과 같이 
- 키값에 Smart 체크 후 Argument 명을 {} 안에 넣어주고 소스코드에서 arg 값을 SetEntry 이전에 넣어주면 된다.

<br>

![Desktop View](/assets/img/post/unity/localization37.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/localization38.png){: : width="600" .normal }

- CommonModal 에서의 사용 예시

<details>
<summary>예시코드</summary>
<div markdown="1">

```csharp
using System;
using System.Collections;
using TMPro;
using UniRx;
using UnityEngine;
using UnityEngine.Localization.Components;
using UnityEngine.UI;

public struct CommonModalContents
{
	public readonly string _titleTextKey;
	public readonly string _contentsTextKey;
	public readonly string _buttonTextKey;
	public readonly Action _buttonAction;
	public LocalizeArgBase _arg;

	public CommonModalContents(string contentsTextKey_, string buttonTextKey_, Action buttonAction_, string titleTextKey_ = "타이틀")
	{
		_titleTextKey = titleTextKey_;
		_contentsTextKey = contentsTextKey_;
		_buttonTextKey = buttonTextKey_;
		_buttonAction = buttonAction_;
		_arg = new LocalizeArgBase();

	}

	public CommonModalContents(string contentsTextKey_, LocalizeArgBase arg_, string buttonTextKey_, Action buttonAction_, string titleTextKey_ = "타이틀")
	{
		_titleTextKey = titleTextKey_;
		_contentsTextKey = contentsTextKey_;
		_buttonTextKey = buttonTextKey_;
		_buttonAction = buttonAction_;
		_arg = arg_;
	}

}
[Serializable]
public class LocalizeArgBase { };
public class LocalizeArg_PurchaseBalance : LocalizeArgBase
{
	public int balance;
}


public class CommonModal : UIPopup
{
	[SerializeField] private CanvasGroup _canvasGroup;
	[SerializeField] protected TextMeshProUGUI _titleText;
	[SerializeField] protected LocalizeStringEvent _titleTextLocalize;
	[SerializeField] protected TextMeshProUGUI _contentsText;
	[SerializeField] protected LocalizeStringEvent _contentTextLocalize;
	[SerializeField] private LocalizeStringEvent _buttonTextLocalize;
	[SerializeField] private Button _button;
	[SerializeField] private VerticalLayoutGroup _verticalLayoutGroup;

	private void Awake()
	{
		_contentTextLocalize.OnUpdateString.AsObservable().TakeUntilDestroy(this.gameObject).Select(value => value).Subscribe(value =>
		{
			_contentsText.text = _contentsText.text.Replace("\\n", "\n");
			Observable.FromCoroutine(RefreshCoroutine).TakeUntilDestroy(this.gameObject).Subscribe(_ => { }, () => { _canvasGroup.alpha = 1.0f; });
		});
	}

	public void SetCommonModal(CommonModalContents contents_)
	{
        // 어떤 팝업창인지 구분하기 위해 임시로 설정
        _titleText.text = contents_._titleTextKey;
        //_titleTextLocalize.SetEntry(contents_._titleTextKey);
		_contentTextLocalize.StringReference.Arguments = new[] { contents_._arg };
		_contentTextLocalize.SetEntry(contents_._contentsTextKey);
		_contentTextLocalize.RefreshString();
		_buttonTextLocalize.SetEntry(contents_._buttonTextKey);
		AdditionalFunction.SetSafeButtonActionOnlyOneCall(_button, contents_._buttonAction, this.gameObject);
	}

	private IEnumerator RefreshCoroutine()
	{
		Canvas.ForceUpdateCanvases();
		_verticalLayoutGroup.enabled = false;
		yield return null;
		_verticalLayoutGroup.enabled = true;
	}
}
```
</div>
</details>

<br>
<br>

## 5. Asset Table 설정 방법

- New Table Collection 에서 String Table과 별개로 Asset Table이 존재한다.
- Asset Table은 각종 Font와 Font Matrial을 locale code에 알맞게 변경해주는 Table 이다.

![Desktop View](/assets/img/post/unity/localization39.png){: : width="400" .normal }

<br>

#### 폰트 Asset Table

![Desktop View](/assets/img/post/unity/localization40.png){: : width="600" .normal }

<br>

- 폰트는 예시로 NotoSans 라고 정하고 NotoSans 폰트의 바리에이션들을 Key 값으로 등록해준다.
- 여기서는 Regular, Bold 등 이후 생성한 폰트들을 설정한 locale table 에 등록해준다.
- 이렇게 되면 설정에서 언어를 변경하면 kr, jp, en 등 알맞게 폰트가 변경된다.

<br>
<br>

#### 폰트 머테리얼 Asset Table
![Desktop View](/assets/img/post/unity/localization41.png){: : width="800" .normal }

<br>
<br>

## 6. 로컬라이제이션 커스터마이징 방법
- 개발하던 도중 로컬라이제이션과 관련하여 여러가지 이슈가 발생했다. 
- 첫째로, 각 나라 언어에 따라 글자 수가 많이 차이가 나는 점 이로 인해 줄바꿈이 어쩔 수 없이 들어가게 될 경우 text의 사이즈를 줄여야할 경우가 발생
- 둘째로, UI 에 맞춰서 폰트의 색상이나 볼드체 여부 등에 대한 커스터마이징이 필요한 경우가 발생했었다.

> 첫번째의 경우 각 나라 언어에 맞게 폰트를 달리하여 바꿔도 되지만, 나라별로 폰트를 다르게 설정하면 폰트의 용량이 부담이 된다는 점이 존재하기에 보통 하나의 폰트로 통일해서 사용

- 따라서 해결 방법으로는 바로 "Rich Text"를 사용하는 것이다.
- 로컬라이즈 테이블에 rich text 형식으로 커스터마이징을 추가하면 간단하게 해결 되는 문제였다.
- 하지만 TMP 자체가 성능 오버헤드를 발생시키고 많은 드로우콜을 발생시키기 때문에.. 간단한 텍스트 UI 에만 사용하는 것을 추천한다. (딱 글꼴, 크기, 색상 변경 용동로만..)

<br>

- 유니티 Rich Text 관련 명령어 등 도큐먼트
> [Unity Rich Text Documentation](https://docs.unity3d.com/kr/560/Manual/StyledText.html)

<br>

- 사용 예시

![Desktop View](/assets/img/post/unity/localization42.png){: : width="400" .normal }
