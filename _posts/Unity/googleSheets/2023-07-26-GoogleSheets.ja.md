---
title: Unity で Google Sheet を連携する
date: 2023-07-26 18:47:00 +/-TTTT
categories: [Unity, GoogleSheet]
tags: [unity, googlesheet, datatable]
difficulty: intermediate
lang: ja
toc: true
---
---
## 目次
- [1. DataSheet 連携コード](#1-datasheet-連携コード)
- [2. DataSheet Editor コード](#2-datasheet-editor-コード)
- [3. Table ID と Sheet gid の探し方](#3-table-id-と-sheet-gid-の探し方)

---

<br>
<br>

## Google Sheet Sync コード

<br>
<br>

#### 1. DataSheet 連携コード

###### UnityWebRequest を使って GoogleSheet の gid から csv ファイルとして保存できます。
######  * UnityEditor を使ってツール化して運用できます。  
補足すると、`Sheets[]` 配列に各シートの gid を入れて、複数シートを一括で csv 取得する構成です。

``` csharp

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Networking;
using Cysharp.Threading.Tasks;

namespace DataSheets
{
    [Serializable]
    public struct Sheet
    {
        public string Name;
        public long Id;
    }	
    
    /// <summary>
    /// Downloads spritesheets from Google Spreadsheet and saves them to Resources.
    /// </summary>
    [ExecuteInEditMode]
    public class GoogleSheetSync : MonoBehaviour
    {
        /// <summary>
        /// Table id on Google Spreadsheet.
        /// Let's say your table has the following url https://docs.google.com/spreadsheets/d/1RvKY3VE_y5FPhEECCa5dv4F7REJ7rBtGzQg0Z_B_DE4/edit#gid=331980525
        /// So your table id will be "1RvKY3VE_y5FPhEECCa5dv4F7REJ7rBtGzQg9Z_B_DE4" and sheet id will be "331980525" (gid parameter)
        /// </summary>
        public string TableId;
        
        /// <summary>
        /// Table sheet contains sheet name and id. First sheet has always zero id. Sheet name is used when saving.
        /// </summary>
        public Sheet[] Sheets;
        
        /// <summary>
        /// Folder to save spreadsheets. Must be inside Resources folder.
        /// </summary>
        public UnityEngine.Object outPutFolder;
        
        private const string UrlPattern = "https://docs.google.com/spreadsheets/d/{0}/export?format=csv&gid={1}";

#if UNITY_EDITOR

        public void DataSync()
        {
            SyncSheetData().Forget();
        }
        
        public async UniTaskVoid SyncSheetData()
        {
            string folder = UnityEditor.AssetDatabase.GetAssetPath(outPutFolder);
            
            Debug.Log("<size=15><color=yellow>Sync started, please wait for confirmation message...</color></size>");
            
            var dict = new Dictionary<string, UnityWebRequest>();
            
            if(String.IsNullOrEmpty(TableId))
            {
                Debug.LogError("Table ID is Empty !!");
                return;
            }			
            
            try
            {
                Debug.Log("<size=15><color=yellow> Set Sheet URL Info....</color></size>");
                
                foreach (var sheet in Sheets)
                {
                    var url = string.Format(UrlPattern, TableId, sheet.Id);
                    
                    Debug.Log($"Downloading: {url}...");
                    
                    dict.Add(url, UnityWebRequest.Get(url));
                }
                
                if (dict.Count < 1)
                {
                    Debug.LogError("Sheet Count Zero !!");
                    return;
                }
                
                Debug.Log("<size=15><color=yellow> Request Sheet Data.... </color></size>");
                
                foreach (var entry in dict)
                {
                    var url = entry.Key;
                    var request = entry.Value;
                    
                    if (!request.isDone)
                    {
                        await request.SendWebRequest();
                    }
                    
                    if (request.error == null)
                    {
                        var sheet = Sheets.Single(i => url == string.Format(UrlPattern, TableId, i.Id));
                        var path = System.IO.Path.Combine(folder, sheet.Name + ".csv");
                        
                        System.IO.File.WriteAllBytes(path, request.downloadHandler.data);
                        
                        Debug.LogFormat("Sheet {0} downloaded to {1}", sheet.Id, path);
                    }
                    else
                    {
                        Debug.LogError("request.error:" + request.error);
                        
                        throw new Exception(request.error);						
                        }
                }
                
                UnityEditor.AssetDatabase.Refresh();
                
                Debug.Log("<size=15><color=green>Successfully Synced!</color></size>");
            }
            catch(Exception e)
            {
                Debug.LogError(e);
            }
        }

#endif
    }
}
```

<br>
<br>

#### 2. DataSheet Editor コード
``` csharp
    /// <summary>
    /// SpreadSheetSync カスタム Editor UI
    /// </summary>
    [CustomEditor(typeof(GoogleSheetSync))]
    public class GoogleSheetSyncEditor : Editor
    {        
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();

            GUIStyle style = new GUIStyle(GUI.skin.button);
            style.normal.textColor = Color.green;
            style.fontSize = 20;

            var component = (GoogleSheetSync)target;          

            if (GUILayout.Button("Get Data Sync", style))
            {
                component.DataSync();
            }
        }
    }
```

<br>
<br>

#### 3. Table ID と Sheet gid の探し方
###### これを上部ツールバーにカスタム追加して使っても構いません。実務ではテーブル更新の間隔が長いことが多いため、私はシーンに置いてプレハブ化して使っていました。  
ざっくり言うと、Inspector の Google Sheet Sync コンポーネントで自分の Google Spreadsheet の Table ID を入力し、`Sheets` 配列に各 Sheet の name と gid を入れれば動きます。
<img src="/assets/img/post/unity/googleSheet01.png" width="1920px" height="1080px" title="256" alt="sheet01">

<br>

###### Table ID は URL の中で、下の画像でドラッグしている領域です。
<img src="/assets/img/post/unity/googleSheet02.png" width="1920px" height="1080px" title="256" alt="sheet02">

<br>

###### `Sheet[]` 配列に入れる Sheet 情報を入力します。Sheet ID には gid、name には下部タブの Sheet 名を入力します。

###### - ID
<img src="/assets/img/post/unity/googleSheet03.png" width="1920px" height="1080px" title="256" alt="sheet03">

###### - Name
<img src="/assets/img/post/unity/googleSheet04.png" width="1920px" height="1080px" title="256" alt="sheet04">

<br>
<br>

#### 4. データ取得
###### 読み込みたいテーブルをすべて入力したら "<span style="color:cyan">Get Data Sync</span>" ボタンを押します。  
注意点として、スプレッドシート側で削除されたテーブルがある場合は、コンポーネント側にも反映しないとエラーになります。  
また Sheets に変更があった場合、既存項目は維持しつつ追加シートだけを増やす運用が安全です。  
変更したシーン/プレハブは SVN や協業ツールで同期すると楽です。
<img src="/assets/img/post/unity/googleSheet05.png" width="512px" height="512px" title="128" alt="sheet05">

###### 最終的に、スプレッドシート上のテーブルを csv ファイルとして取得できました。  
ただし csv はかなり Raw Data なので、別途バイナリ化して最低限の保護を入れるのが望ましいです。  
> (バイナリ化しても本気で解析されれば突破されるのが現実ですが、誰でも簡単に見られる状態を防ぐという意味で、最低限の安全策は入れておくべきという考えです。)


<br>

#### 5. スプレッドシートの共有設定は必ず「リンクを知っている全員」に設定してください。そうしないとアクセス拒否やエラーになります。
<img src="/assets/img/post/unity/googleSheet06.png" width="512px" height="512px" title="256" alt="sheet06">
> これはセキュリティ上のデメリットですが、運用のしやすさとのトレードオフです。  
開発時や更新時だけ公開設定にし、ローカルに取り込んだら再度制限する、といった運用で補うのが現実的です。
