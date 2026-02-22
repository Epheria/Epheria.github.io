---
title: Unity Localizationをより効率的に使ってみる
date: 2023-11-24 18:00:00 +/-TTTT
categories: [Unity, Localization]
tags: [unity, localization, util]

difficulty: intermediate
lang: ja
toc: true
---

## Localization Manager (StringManager)

#### Localizationをより便利に、ユーティリティとして使ってみる

- [Localizationに関する記事](https://epheria.github.io/posts/Localization/)で説明した方法は、UGUI上で`StringEvent`コンポーネントに直接割り当てるか、
- `StringEvent`自体を取得して設定する方法が中心でした。
- ただ、この方法だと文字列をより複雑かつ柔軟に組み立てるのが難しかったです。
- そこでLocalizationのSmart機能を使い、`StringManager`というユーティリティマネージャー経由で、全員が共通してLocalizationを使えるようにしました。
- 実際には`StringManager`の内部に、文字列結合時のボクシング/アンボクシングや不要な割り当てを抑えるため、Cysharpの`ZString`機能やNGワードフィルタなども含めています。
- つまり文字列専用のUtilクラスです。

<br>

#### Unity Localize Table: Smartオプション

- まずコードを見る前に、Unity Localizationテーブルと実際のGoogleスプレッドシートのテーブルを確認しておきます。

![Desktop View](/assets/img/post/unity/localizeutil01.png){: : width="1800" .normal }

- 画像を見ると、各データにSmartオプションが有効になっていることを確認できます。
- テーブルデータ内で`{}`のプレースホルダを使うと、担当者が必要な値を自由に入れられます。たとえば時間・金額・日付のような`int`値や、ユーザー名のような`string`も設定できます。

<br>

![Desktop View](/assets/img/post/unity/localizeutil02.png){: : width="1800" .normal }

- 実際のGoogleスプレッドシート内部の様子です。

- このSmart機能を使うと、従来のようにローカライズ済みテキストを受け取って、必要な情報値を追加し、新しい文字列を組み立てる手間を減らせます。

<br>

- 次のコードは、ローカライズキーとSmartデータ値を設定し、結果としてローカライズされたテキストを受け取るユーティリティ関数です。
- `values`配列パラメータでは、テーブルを参照してどの順序でデータが入るかを確認してから渡します。
- 参考までに、`GetLZString`はオーバーロードされた実処理側のメイン関数です。

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

- こちらは、実際にテーブル参照とキーを使ってローカライズ値を取得・設定するメイン関数です。
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

- 実使用例です。
- `TMP_Text`コンポーネントの`text`に直接文字列を代入しています。2つ目のパラメータでデータを設定している部分を見ると分かりやすいです。
- ボクシング/アンボクシングや動的割り当てで発生するGCが気になるなら、用途に応じてさらに効率的な方法もあります。

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
