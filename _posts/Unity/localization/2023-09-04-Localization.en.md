---
title: Unity Localization Integration
date: 2023-09-04 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [unity, localization]
difficulty: intermediate
lang: en
toc: true
---
---
## Table of Contents
- [1. Install Localization](#1-install-localization)
- [2. Localization environment setup](#2-localization-environment-setup)
- [3. Integrate Google Sheets](#3-integrate-google-sheets)
- [4. How to use in UGUI](#4-how-to-use-localization-in-ugui)
- [5. Asset Table setup](#5-how-to-configure-asset-table)
- [6. Localization customization](#6-localization-customization)

---

## Localization integration and usage

- Localization is essential for live game services. Combined with TextMeshPro and String Event, you can switch UI text automatically based on selected language.

<br>

## 1. Install Localization

- Install Localization from Package Manager.

![Desktop View](/assets/img/post/unity/localization01.png){: .normal }

## 2. Localization environment setup

- In `Window - Asset Management - Localization Tables`, you can create/manage String Table and Asset Table.

![Desktop View](/assets/img/post/unity/localization02.png){: : width="500" .normal }

<br>

- At the top, `NewTableCollection` means create, `EditTableCollection` means edit.

![Desktop View](/assets/img/post/unity/localization03.png){: : width="700" .normal }

<br>

- String Table references string keys and stores translated values per locale.  
Asset Table stores assets such as fonts and font materials.

![Desktop View](/assets/img/post/unity/localization04.png){: : width="700" .normal }

<br>

- In Edit Table mode, click `Add New Entry` to add rows.

![Desktop View](/assets/img/post/unity/localization05.png){: : width="500" .normal }

<br>

- With `Locale Generator`, you can add target languages/locales (each locale has a unique code).

![Desktop View](/assets/img/post/unity/localization06.png){: : width="400" .normal }

<br>
<br>

---

- Click `Create` to choose install folder path for tables.
- Then table assets, shared data, and locale tables are generated in that path.

![Desktop View](/assets/img/post/unity/localization07.png){: : width="700" .normal }
![Desktop View](/assets/img/post/unity/localization08.png){: : width="700" .normal }

<br>

- Looking inside String Collection Table:
- You can add Extensions such as CSV and Google Sheets.
- This post covers Google Sheets integration.

![Desktop View](/assets/img/post/unity/localization09.png){: : width="400" .normal }
![Desktop View](/assets/img/post/unity/localization10.png){: : width="400" .normal }

<br>
<br>

## 3. Integrate Google Sheets

- In Project tab: `Create - Localization - Google Sheet Service`.

![Desktop View](/assets/img/post/unity/localization11.png){: : width="700" .normal }

<br>

- In Inspector, configure Authentication.
- Choose either Google OAuth or API Key via Google Cloud Service. (I used OAuth.)

![Desktop View](/assets/img/post/unity/localization12.png){: : width="500" .normal }

<br>

## How to register OAuth credentials
- Open [Google Cloud Console](https://console.cloud.google.com/welcome?project=cogent-tide-354007).
- Complete signup/consent.
- Go to `API & Services - OAuth consent screen`.

![Desktop View](/assets/img/post/unity/localization13.png){: : width="500" .normal }

<br>

- Click `Edit App` next to project name.

![Desktop View](/assets/img/post/unity/localization14.png){: : width="500" .normal }

<br>

- In app settings, set app name and support email.
- Move to test users section.
- Add test users via `+ ADD USERS` (required for Sheets access).

![Desktop View](/assets/img/post/unity/localization15.png){: : width="500" .normal }
![Desktop View](/assets/img/post/unity/localization16.png){: : width="500" .normal }

<br>

- Then move to Credentials tab.

![Desktop View](/assets/img/post/unity/localization17.png){: : width="300" .normal }

<br>

- Confirm OAuth client ID and secret are created.
- Click client name.

![Desktop View](/assets/img/post/unity/localization18.png){: : width="1980" .normal }

<br>

- Finally copy client ID and secret.

![Desktop View](/assets/img/post/unity/localization19.png){: : width="1980" .normal }

<br>

- Back in Unity, in Google Sheet Service inspector select OAuth authentication.
- Paste client ID/secret and click `Authorize...` to complete account auth in browser.

![Desktop View](/assets/img/post/unity/localization20.png){: : width="600" .normal }

<br>

- In Localize Table (String Table Collection) inspector, add Google Sheets Extension to Extensions list.
- Register the Google Sheet Service Provider asset you created.

![Desktop View](/assets/img/post/unity/localization10.png){: : width="500" .normal }

<br>

- You can create a new spreadsheet in your Google Drive via `Create New SpreadSheet`.
- Or connect an existing spreadsheet by entering Spreadsheet ID and Sheet ID.

![Desktop View](/assets/img/post/unity/localization21.png){: : width="700" .normal }

## Important notes

1. Enable Google Sheets API for your credentials.
2. Spreadsheet sharing must be public or include authorized users.

- Only then can Localization Push/Pull work inside Unity.

![Desktop View](/assets/img/post/unity/localization22.png){: : width="1200" .normal }

![Desktop View](/assets/img/post/unity/localization23.png){: : width="700" .normal }

<br>
<br>

- Before pulling linked Google Spreadsheet,
- Map the columns first.
- Add one key column + one localized column per language.

![Desktop View](/assets/img/post/unity/localization21.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization24.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/localization25.png){: : width="400" .normal }

<br>

- Example after adding all columns/localized columns:

![Desktop View](/assets/img/post/unity/localization26.png){: : width="400" .normal }

<br>

- After mapping, click `Pull` to fetch data from Google Spreadsheet.
> Push is not recommended. There is no clear “who pushed” history, and Push/Pull can conflict.  
In practice, teams edit spreadsheet directly and only Pull into client/editor.
- Also, editing Table info directly in Unity Editor is usually not recommended.

![Desktop View](/assets/img/post/unity/localization27.png){: : width="400" .normal }

<br>

- Localization table on Google Spreadsheet:

![Desktop View](/assets/img/post/unity/localization28.png){: : width="1980" .normal }

<br>

- Corresponding view in Unity Table Collection:

![Desktop View](/assets/img/post/unity/localization29.png){: : width="700" .normal }

<br>
<br>

---

## 4. How to use Localization in UGUI

#### Requirements
1. UGUI text type must be `TextMeshPro - Text (UI)`.
2. `Localize String Event` component must be attached.
3. If you also want to localize font/font material, create and attach helper components like below.

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

### How to use as Components

- Add `Localize String Event` component.

![Desktop View](/assets/img/post/unity/localization30.png){: : width="400" .normal }

<br>

- Click String Reference to search/assign table key.
- Table Collection is auto-assigned.
- Inspector previews localized values by language and lets you assign TMP text target for update.

![Desktop View](/assets/img/post/unity/localization31.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization32.png){: : width="400" .normal }

<br>

- If you also want to localize font and font material,
- Register additional components via Add Component or Localize Extension.

```csharp
using System;
using Base;
using TMPro;
using UnityEditor;
using UnityEditor.Events;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Localization.Components;

static class TMProLocalizeExtension
{
    [MenuItem("CONTEXT/TextMeshProUGUI/Localize Extension")]
    static void LocalizeTMProTextWithFontAssets(MenuCommand command)
    {
        var target = command.context as TextMeshProUGUI;
        SetupForLocalizeString(target);
        SetupForLocalizeTmpFont(target);
        SetupForLocalizeTmpFontMaterial(target);
    }

    static void SetupForLocalizeString(TextMeshProUGUI target)
    {
        var comp = Undo.AddComponent(target.gameObject, typeof(LocalizeStringEvent)) as LocalizeStringEvent;
        comp.SetTable("LocalizeTable");
        var setStringMethod = target.GetType().GetProperty("text").GetSetMethod();
        var methodDelegate =
            Delegate.CreateDelegate(typeof(UnityAction<string>), target, setStringMethod) as UnityAction<string>;
        UnityEventTools.AddPersistentListener(comp.OnUpdateString, methodDelegate);
        comp.OnUpdateString.SetPersistentListenerState(0, UnityEventCallState.EditorAndRuntime);
    }

    static void SetupForLocalizeTmpFont(TextMeshProUGUI target)
    {
        var comp = Undo.AddComponent(target.gameObject, typeof(LocalizedTmpFontEvent)) as LocalizedTmpFontEvent;
        var setStringMethod = target.GetType().GetProperty("font").GetSetMethod();
        var methodDelegate =
            Delegate.CreateDelegate(typeof(UnityAction<TMP_FontAsset>), target, setStringMethod) as
                UnityAction<TMP_FontAsset>;

        UnityEventTools.AddPersistentListener(comp.OnUpdateAsset, methodDelegate);
        comp.OnUpdateAsset.SetPersistentListenerState(0, UnityEventCallState.EditorAndRuntime);
    }

    static void SetupForLocalizeTmpFontMaterial(TextMeshProUGUI target)
    {
        var comp = Undo.AddComponent(target.gameObject, typeof(LocalizedTmpFontMaterialEvent)) as LocalizedTmpFontMaterialEvent;
        var setStringMethod = target.GetType().GetProperty("fontMaterial").GetSetMethod();
        var methodDelegate =
            Delegate.CreateDelegate(typeof(UnityAction<Material>), target, setStringMethod) as
                UnityAction<Material>;

        UnityEventTools.AddPersistentListener(comp.OnUpdateAsset, methodDelegate);
        comp.OnUpdateAsset.SetPersistentListenerState(0, UnityEventCallState.EditorAndRuntime);
    }
}
```

- Changing language in-game or in editor updates UGUI text automatically.

![Desktop View](/assets/img/post/unity/localization33.png){: : width="400" .normal }

<br>
<br>

### How to use by Script

- If UGUI is created dynamically, you can localize by script instead of inspector component setup.
- Assign Update String dynamically as shown below.

![Desktop View](/assets/img/post/unity/localization34.png){: : width="400" .normal }

<br>

#### Script examples

![Desktop View](/assets/img/post/unity/localization35.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization36.png){: : width="600" .normal }

<br>

- Get `LocalizeStringEvent` via `GetComponent` and call `SetEntry(key)`.
- It finds key in Table Collection and applies localized text to current locale TMP text.

<br>
<br>

#### Additionally, dynamic text arguments

- For dynamic values (balance, username, etc.):
- Enable Smart on key entry, put argument token in `{}` in table, and assign args in code before `SetEntry`.

<br>

![Desktop View](/assets/img/post/unity/localization37.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/localization38.png){: : width="600" .normal }

- Example in CommonModal

<details>
<summary>Example code</summary>
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

## 5. Asset Table setup

- In New Table Collection, besides String Table there is Asset Table.
- Asset Table maps font/font material per locale code.

![Desktop View](/assets/img/post/unity/localization39.png){: : width="400" .normal }

<br>

#### Font Asset Table

![Desktop View](/assets/img/post/unity/localization40.png){: : width="600" .normal }

<br>

- Example uses `NotoSans` and registers variations as keys.
- Register generated font variants (Regular, Bold, etc.) per locale.
- Then switching language (kr/jp/en) automatically swaps fonts.

<br>
<br>

#### Font Material Asset Table
![Desktop View](/assets/img/post/unity/localization41.png){: : width="800" .normal }

<br>
<br>

## 6. Localization customization
- During development, several localization issues occurred.
- First, text lengths vary greatly by language, so line breaks happen and text size adjustments are often needed.
- Second, UI-specific font style customizations (color, bold, etc.) were required.

> For the first issue, you can set different fonts by language, but that increases font size footprint. In many cases, teams standardize to one font.

- The practical solution is using **Rich Text**.
- By adding rich text tags directly in localization table entries, many styling issues are solved simply.
- However, TMP itself has overhead and can increase draw calls, so use this mainly for lightweight text UI (font/size/color adjustments).

<br>

- Unity Rich Text docs:
> [Unity Rich Text Documentation](https://docs.unity3d.com/kr/560/Manual/StyledText.html)

<br>

- Example:

![Desktop View](/assets/img/post/unity/localization42.png){: : width="400" .normal }
