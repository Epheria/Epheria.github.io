---
title: Unity Localization 連携
date: 2023-09-04 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [unity, localization]
difficulty: intermediate
lang: ja
toc: true
---
---
## 目次
- [1. Localization の導入](#1-localization-の導入)
- [2. Localization 環境設定](#2-localization-環境設定)
- [3. Google Sheets 連携](#3-google-sheets-連携)
- [4. UGUI での使い方](#4-localization-を-ugui-で使う方法)
- [5. Asset Table 設定方法](#5-asset-table-設定方法)
- [6. Localization カスタマイズ](#6-localization-カスタマイズ)

---

## Localization 連携と使用方法

- Localization (ローカライズ) はゲーム運用で必須要素。TextMeshPro と String Event を組み合わせることで、UI テキストを選択言語に応じて切り替えられる。

<br>

## 1. Localization の導入

- Package Manager から Localization をインストールする。

![Desktop View](/assets/img/post/unity/localization01.png){: .normal }

## 2. Localization 環境設定

- `Window - Asset Management - Localization Tables` で String Table / Asset Table を作成・管理できる。

![Desktop View](/assets/img/post/unity/localization02.png){: : width="500" .normal }

<br>

- 上部タブの `NewTableCollection` は新規作成、`EditTableCollection` は編集。

![Desktop View](/assets/img/post/unity/localization03.png){: : width="700" .normal }

<br>

- String Table は string key を参照して locale ごとの翻訳を持つテーブル。  
Asset Table は Font / Font Material などを locale ごとに割り当てるテーブル。

![Desktop View](/assets/img/post/unity/localization04.png){: : width="700" .normal }

<br>

- Edit Table モードで `Add New Entry` を押すと行を追加できる。

![Desktop View](/assets/img/post/unity/localization05.png){: : width="500" .normal }

<br>

- `Locale Generator` で言語を追加でき、各国言語には固有 locale code がある。

![Desktop View](/assets/img/post/unity/localization06.png){: : width="400" .normal }

<br>
<br>

---

- `Create` を押すとテーブル生成先フォルダを指定できる。
- 指定フォルダに Table / Table Shared Data / Locale テーブルが生成される。

![Desktop View](/assets/img/post/unity/localization07.png){: : width="700" .normal }
![Desktop View](/assets/img/post/unity/localization08.png){: : width="700" .normal }

<br>

- String Collection Table を見ると、
- Extensions に CSV と Google Sheets を登録できる。
- ここでは Google Sheets 連携を扱う。

![Desktop View](/assets/img/post/unity/localization09.png){: : width="400" .normal }
![Desktop View](/assets/img/post/unity/localization10.png){: : width="400" .normal }

<br>
<br>

## 3. Google Sheets 連携

- Project タブで `Create - Localization - Google Sheet Service` を作成。

![Desktop View](/assets/img/post/unity/localization11.png){: : width="700" .normal }

<br>

- Inspector で Authentication 権限設定を確認できる。
- Google Cloud Service 経由で OAuth か API Key を選択する (私は OAuth を使用)。

![Desktop View](/assets/img/post/unity/localization12.png){: : width="500" .normal }

<br>

## OAuth 権限登録方法
- [Google Cloud Console](https://console.cloud.google.com/welcome?project=cogent-tide-354007) にアクセス。
- Google Cloud の登録/同意を進める。
- メニュー `API とサービス - OAuth 同意画面` を開く。

![Desktop View](/assets/img/post/unity/localization13.png){: : width="500" .normal }

<br>

- プロジェクト名横の `アプリを編集` を押す。

![Desktop View](/assets/img/post/unity/localization14.png){: : width="500" .normal }

<br>

- アプリ名とサポートメールを設定。
- テストユーザー項目まで進む。
- `+ ADD USERS` でテストユーザー登録が必要 (Google Sheets アクセス権付与のため)。

![Desktop View](/assets/img/post/unity/localization15.png){: : width="500" .normal }
![Desktop View](/assets/img/post/unity/localization16.png){: : width="500" .normal }

<br>

- ここまで完了したら `認証情報` タブへ移動。

![Desktop View](/assets/img/post/unity/localization17.png){: : width="300" .normal }

<br>

- OAuth Client ID / Secret が生成されていることを確認。
- クライアント名をクリック。

![Desktop View](/assets/img/post/unity/localization18.png){: : width="1980" .normal }

<br>

- 最終的に client ID と secret を確認できる。

![Desktop View](/assets/img/post/unity/localization19.png){: : width="1980" .normal }

<br>

- Unity に戻り、先ほど作成した Google Sheet Service の Authentication を OAuth に設定。
- 取得した Client ID / Secret を入力し、`Authorize...` でブラウザ認証を行う。

![Desktop View](/assets/img/post/unity/localization20.png){: : width="600" .normal }

<br>

- Localize Table (String Table Collection) の Inspector で Extensions に Google Sheets Extension を追加。
- 上で作成した Google Sheet Service Provider を登録する。

![Desktop View](/assets/img/post/unity/localization10.png){: : width="500" .normal }

<br>

- `Create New SpreadSheet` で Drive に新規 Spreadsheet を作成可能。
- 既存 Spreadsheet は Spreadsheet ID / Sheet ID を入力して連携可能。

![Desktop View](/assets/img/post/unity/localization21.png){: : width="700" .normal }

## 注意点

1. Google Sheets API を有効化する。
2. 連携する Spreadsheet の共有設定を公開 or ユーザー追加にする。

- これを満たさないと Unity 上で Localization Push/Pull は動作しない。

![Desktop View](/assets/img/post/unity/localization22.png){: : width="1200" .normal }

![Desktop View](/assets/img/post/unity/localization23.png){: : width="700" .normal }

<br>
<br>

- 連携した Google Spreadsheet を取り込む前に、
- 列マッピングを先に設定する。
- Key 列 + 各言語 locale 列を必要数追加する。

![Desktop View](/assets/img/post/unity/localization21.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization24.png){: : width="900" .normal }

![Desktop View](/assets/img/post/unity/localization25.png){: : width="400" .normal }

<br>

- 列/locale 列を追加した状態:

![Desktop View](/assets/img/post/unity/localization26.png){: : width="400" .normal }

<br>

- マッピング完了後に `Pull` を押すと Spreadsheet 情報を取得できる。
> Push は非推奨。誰が Push したかの履歴が残りにくく、Push/Pull 競合も起きやすい。  
実務では Spreadsheet 側を編集し、Pull だけでクライアント同期する運用が安定。
- Unity Editor 側で直接 Table を編集するのも基本非推奨。

![Desktop View](/assets/img/post/unity/localization27.png){: : width="400" .normal }

<br>

- Google Spreadsheet 側 Localization Table 例

![Desktop View](/assets/img/post/unity/localization28.png){: : width="1980" .normal }

<br>

- Unity Editor Table Collection 側表示

![Desktop View](/assets/img/post/unity/localization29.png){: : width="700" .normal }

<br>
<br>

---

## 4. Localization を UGUI で使う方法

#### 必須条件
1. UGUI テキストは `TextMeshPro - Text (UI)` であること。
2. `Localize String Event` コンポーネントが対象オブジェクトに付与されていること。
3. font material / font も切り替える場合は以下のようなクラスを作って使う。

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

### Component として使う方法

- `Localize String Event` を追加。

![Desktop View](/assets/img/post/unity/localization30.png){: : width="400" .normal }

<br>

- String Reference から table key を検索して割り当てる。
- Table Collection も自動割り当てされる。
- locale 切替時にどの文字列が入るか表示され、更新対象 TMP text も指定できる。

![Desktop View](/assets/img/post/unity/localization31.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization32.png){: : width="400" .normal }

<br>

- font / font material も切り替えたい場合は、
- Add Component または Localize Extension で追加する。

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

- エディタ/ゲーム内で言語変更すると UGUI テキストは自動更新される。

![Desktop View](/assets/img/post/unity/localization33.png){: : width="400" .normal }

<br>
<br>

### Script で使う方法

- UGUI が動的生成される場合、Inspector 直設定ではなくスクリプト呼び出しで処理できる。
- 下画像のように Update String を割り当てればよい。

![Desktop View](/assets/img/post/unity/localization34.png){: : width="400" .normal }

<br>

#### Script 例

![Desktop View](/assets/img/post/unity/localization35.png){: : width="400" .normal }

![Desktop View](/assets/img/post/unity/localization36.png){: : width="600" .normal }

<br>

- `LocalizeStringEvent` を `GetComponent` し、`SetEntry(key)` を呼ぶ。
- Table Collection の key を参照し、現在 locale に合わせて TMP text へ適用される。

<br>
<br>

#### さらに、動的な内部データ文字列の差し込み

- balance や username のような動的値は、
- key で Smart を有効化し、テーブル側で `{}` 引数名を入れ、コード側で `SetEntry` 前に Arguments を設定する。

<br>

![Desktop View](/assets/img/post/unity/localization37.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/localization38.png){: : width="600" .normal }

- CommonModal での使用例

<details>
<summary>例コード</summary>
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

## 5. Asset Table 設定方法

- New Table Collection では String Table とは別に Asset Table がある。
- Asset Table は locale code ごとに Font / Font Material を切り替えるテーブル。

![Desktop View](/assets/img/post/unity/localization39.png){: : width="400" .normal }

<br>

#### Font Asset Table

![Desktop View](/assets/img/post/unity/localization40.png){: : width="600" .normal }

<br>

- 例として NotoSans を使い、バリエーションを key として登録。
- Regular / Bold など生成した font を locale table に割り当てる。
- 言語変更時に kr/jp/en へ応じて font が切り替わる。

<br>
<br>

#### Font Material Asset Table
![Desktop View](/assets/img/post/unity/localization41.png){: : width="800" .normal }

<br>
<br>

## 6. Localization カスタマイズ
- 開発中、Localization 関連でいくつか課題があった。
- 1つ目は言語ごとの文字数差。改行が増えると text サイズ調整が必要になる。
- 2つ目は UI 要件に合わせた色/太字などの個別カスタマイズ。

> 1つ目は言語ごとに font を分ける手もあるが、font 容量負担が大きくなるため、実務では単一 font 統一が多い。

- 解決策として有効なのが **Rich Text**。
- Localization table 側に Rich Text 形式を入れるだけで簡単に対応できる。
- ただし TMP はオーバーヘッドと draw call 増加があるため、軽量なテキスト UI での利用を推奨 (フォント/サイズ/色変更用途中心)。

<br>

- Unity Rich Text ドキュメント
> [Unity Rich Text Documentation](https://docs.unity3d.com/kr/560/Manual/StyledText.html)

<br>

- 使用例

![Desktop View](/assets/img/post/unity/localization42.png){: : width="400" .normal }
