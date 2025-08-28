---
title: Unity Localization - Smart Strings 활용 방법
date: 2024-05-22 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [Unity, Localization, Smart Strings, Plural]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>
<br>

## Smart Strings 란?

- [Localization 활용 방법에 대한 포스트]()에서 설명한 Smart Option 을 의미하며 String.Format 과 유사하게 '{}' 블록 내부에 캡슐화된다.
- Smart Strings Document : (https://docs.unity3d.com/Packages/com.unity.localization@1.5/manual/Smart/SmartStrings.html)

<br>
<br>

## Plural - 복수형 포맷에 대해

- 언어마다 단수/복수형이 나뉘어져있다. (대표적으로 영어, 스페인어, 러시아어 등)
- 예를 들면, entry, entries / contestant, contestants 와 같이 단수형 복수형이 구분되어 있다.

<br>

- 토이버스에서도 역시 영어로 서비스를 했기 때문에 단수형 복수형을 구분할 필요성이 있었다.
- Smart Strings 에서 **[Plural Localization Formatter](https://docs.unity3d.com/Packages/com.unity.localization@1.5/manual/Smart/Plural-Formatter.html)** 를 사용하여 단수형/복수형을 구분할 수 있다.

<br>

![Desktop View](/assets/img/post/unity/localizeutil01_01.png){: : width="1200" .normal }     
_Localization Table 실제 예시_

<br>

#### Plural Format 설정 방법

![Desktop View](/assets/img/post/unity/localizeutil01_07.png){: : width="400" .normal }     

<br>

- 실사용 예시 그림

![Desktop View](/assets/img/post/unity/localizeutil01_02.png){: : width="400" .normal }     

<br>

- 텍스트로 풀어보면 다음과 같다.

```
{n : plural : 1 entry! | {s} entries! }
```

<br>

- n 의 자리에는 어떤 숫자를 집어 넣어도 되지만, 동적으로 값이 변경되는 변수를 집어 넣고 싶다면 n 을 집어 넣어도 된다. (복수형인지를 판단하는 기준이 될 수 있음)
- plural 혹은 p 가 오면 복수형 포맷으로 사용하겠다는 의미이다. (en) 등을 추가적으로 입력하여 특정 언어로 강제할 수 있다.
- 제일 처음 오는 "1 entry!" 는 n이 1일 때 출력되는 문자이다.
- {s} entries! 는 n이 2 이상일 때 출력되는 문자이다.

<br>

- 추가적으로 숫자를 더 나누고 싶다면 "|" 을 추가적으로 늘려주면 된다.

```
{n : plural : 1 tester | 2 testers | {s} testers }
```

- 1 tester 는 n 이 1일 때, 2 testers 는 n 이 2일 때, {s} testers 는 3 이상일 때 라고 생각하면 된다.

<br>
<br>

#### 스크립트에서 사용 방법

- 실제 사용 예시를 살펴보면,

```csharp

var count = Utils.GetNumberFormat(info_.EntryCnt, false);
_fashionShowEntryCountText.text = StringManager.GetLZString("LZ_FSS_002", new {n = info_.EntryCnt , s = count});

```

```csharp
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

- 주목해야할 부분은 입력한 로컬라이즈 키의 텍스트와 new 로 동적할당한 서버의 Entry Count 데이터와 실제 참가자를 출력해줄 포맷으로 바꾼 count이다.

<br>

- Localize Key "LZ_FSS_02" 는 아래 텍스트를 의미하며

```
{n : plural : 1 entry! | {s} entries! }
```

<br>

- Entry Count 는 실제 서버 API 를 호출하여 받은 실제 참가자 수 이며 위 plural 포맷에서 "n" 에 할당된다.
- 즉 plural 인지 아닌지 판단하는 기준이 되는 것

```
n = info_.EntryCnt
```

<br>

- 1K, 1M 등의 포맷으로 변환한 count 값을 마지막으로 {s} 에 할당해준다. count 는 string 임

```
s = count
```

<br>

- 따라서 최종적으로 다음과 같은 로컬라이제이션이 작동한다.

![Desktop View](/assets/img/post/unity/localizeutil01_04.png){: : width="400" .normal }     
_n = 1, 단수형일 때_

<br>

![Desktop View](/assets/img/post/unity/localizeutil01_03.png){: : width="400" .normal }     
_n >= 2, 복수형일 때_

<br>
<br>

## 텍스트 색상, 볼드체 지정 방법에 대해

- Smart Strings 포맷중에는 볼드체와 텍스트 색상을 지정할 수 있는 기능도 존재한다.
- 로컬라이즈 키 예시를 살펴보면,

![Desktop View](/assets/img/post/unity/localizeutil01_05.png){: : width="500" .normal }     

```
# 볼드체
<b> input your context </b>

# 색상
<color=#FF4040> input your context </color>

# 색상, 볼드체 혼합
<b><color=#FF4040> input your context </color></b>
```

- 위와 같이 활용할 수 있다.

<br>

![Desktop View](/assets/img/post/unity/localizeutil01_06.png){: : width="500" .normal }     
_실제 사용 예시_