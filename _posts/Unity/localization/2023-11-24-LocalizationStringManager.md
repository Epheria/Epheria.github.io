---
title: Unity Localization 좀 더 효율적으로 사용해보기
date: 2023-11-24 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [Unity, Localization, Util]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## Localization Manager (StringManager)

#### Localization 을 좀 더 편리하고 유틸화 시켜서 사용해보자

- [로컬라이제이션에 관한 글](https://epheria.github.io/posts/Localization/) 여기서 설명했던 방법은 UGUI 상에 StringEvent 컴포넌트에 직접 할당하거나
- StringEvent 그 자체를 받아와서 세팅하는 방법이 주 였다.
- 하지만, 이 방법은 좀 더 복잡하고 유연성있게 string 을 조합할 수 없었다. 
- 따라서 로컬라이즈의 smart 기능을 사용하여 StringManager라는 유틸리티 매니저를 통해 모두가 공통적으로 로컬라이제이션을 사용할 수 있게 시도했다.
- 사실 StringManager 내부에서는 string을 조합함으로 발생하는 박싱/언박싱 혹은 할당을 방지하기 위해 Cysharp 의 Zstring 기능과 비속어 필터를 처리하는 NGWord 등의 기능이 함께 내포되어있다.
- 즉, string 전용 Util 클래스인 셈

<br>

#### Unity Localize Table

- 우선 코드를 보기에 앞서 유니티 로컬라이제이션 테이블과 실제로 구글 스프레드 시트의 테이블을 짚고 넘어가자.

![Desktop View](/assets/img/post/unity/localizeutil01.png){: : width="1800" .normal }

- 사진을 보면 각 데이터들에 Smart 옵션이 체크되어 있는것을 확인할 수 있다.
- 테이블 데이터 내에 '{}' 로 표시하면 이 데이터에 각 작업자가 원하는 데이터를 할당할 수 있다. 예를 들어 시간,금액,날짜 등 과 같은 int값을 넣을 수도 있고 유저 네임과 같은 string 도 자유자재로 넣을 수 있다.

<br>

![Desktop View](/assets/img/post/unity/localizeutil02.png){: : width="1800" .normal }

- 실제 구글 스프레드 시트 내부의 모습

- 이 smart 기능을 사용하면 기존의 방법처럼 로컬라이즈된 텍스트를 받아와서 원하는 정보값을 더해 새로운 string 을 조합하거나 하는 수고를 덜 수 있다.

<br>

- 다음 코드는 로컬라이즈 키 값과 smart 데이터 값을 세팅하여 결과 값으로 로컬라이제이션이 된 텍스트를 받아오는 유틸 함수이다.
- values 배열 파라미터 내부에 테이블을 참조하여 어떤 데이터가 들어가는지 순서를 확인하고 넘겨주면 된다.
- 참고로 GetLZString 은 오버로딩된 실제로 기능을 수행하는 메인 함수임

``` csharp
/// <summary>
/// the given values replace indexed placeholders in the string.
/// e.g.) {0} is {1} old. -> He is 13 old.
/// </summary>
/// <param name="key">Key.</param>
/// <param name="values">Values for the replacing</param>
public static string GetLZString(string key, params object[] values)
{
	try
	{
		string txt = key;
		
		if (LocalizationSettings.StringDatabase.GetTable(LOCALIZE_TABLE_NAME).GetEntry(key).IsSmart)
		{
			txt = GetLZString(key, LOCALIZE_TABLE_NAME, values);
			return txt;
		}
		else
		{
			txt = GetLZString(key);
			if (txt != null)
			    return Smart.Format(txt, values);
			else
			    return txt;
		}
	}
	catch (Exception e)
	{
		Debug.LogError("The count of prameters is wrong!!!!! [" + key + "][" + e.ToString() + "]");
		return key;
	}
}
```
<br>

- 실제로 테이블 레퍼런스와 키를 참조하여 로컬라이즈 값을 가져오고 세팅하는 메인 함수
``` csharp
// main Localize string function
public static string GetLZString(string key, string table, params object[] values_)
{
	LocalizedString lzString = new LocalizedString() { TableReference = table, TableEntryReference = key };
	var stringOperation = values_ != null ? lzString.GetLocalizedStringAsync(values_) : lzString.GetLocalizedStringAsync();
	if (stringOperation.IsDone && stringOperation.Status == AsyncOperationStatus.Succeeded)
	{
		return stringOperation.Result;
	}
	else
	{
		Debug.LogError("GetLZString|stringOperation fail...key:" + key);
		return key;
	}
}
```

<br>

- 실사용 예시이다.
- TMP_Text 컴포넌트의 text 에 직접 string 값을 할당하는 모습이다. 두 번째 파라미터에 데이터를 세팅하는 부분을 확인하면 좋을거같다.
- 박싱/언박싱 그리고 동적할당으로 발생하는 GC가 걱정된다면 분명 다른 효율적인 방법도 있을 것이다.

``` csharp
 public async void Renew()
    {
		// ...

        switch (_data.RecentMessage.MessageType)
        {
			// ...
			case MsgType.MsgLoginbonusDaily:

                _recentMsgText.text = StringManager.GetLZString("LZ_LB_011", new { nn = _data.RecentMessage.Text });
                break;
			// ...
		}
		// ...
	}
```