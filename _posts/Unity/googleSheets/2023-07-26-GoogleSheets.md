---
title: Unity Google Sheet 연동하기
date: 2023-07-26 18:47:00 +/-TTTT
categories: [Unity, GoogleSheet]
tags: [Unity, GoogleSheet, DataTable]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

<br>
<br>

## Google Sheet Sync 코드

<br>
<br>

#### 1. DataSheet 연동 코드

######  UnityWebRequest를 이용해서 GoogleSheet의 gid 를 통해 csv 파일로 저장을 할 수 있다.
######  * UnityEditor를 사용해서 Tool 처럼 만들어서 쓰시면 됩니다.   
추가적으로 설명하자면 Sheets[] 배열에 시트의 gid들을 넣어서 한꺼번에 csv 파일로 받아오는 형태

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

#### 2. DataSheet Editor 코드
``` csharp
    /// <summary>
    /// SpreadSheetSync 커스텀 Editor UI
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

#### 3. Table ID 및 Sheet gid 찾는 방법
###### 상단 툴바에 커스텀해서 추가해서 사용하셔도 됩니다. 주로 회사에서는 테이블 갱신을 텀을 길게 두면서 갱신하므로 귀찮아서 Scene 에 박아넣고 프리팹으로 사용하고있었습니다...ㅎㅎ   
대충 설명 드리자면, 인스펙터창의 Google Sheet Sync 컴포넌트에서 본인의 계정으로 만든 Google Spread Sheet 의 Table ID를 입력하고   
Sheets 배열에 각 Sheet들의 이름과 gid를 입력하면됩니다.
<img src="/assets/img/post/unity/googleSheet01.png" width="1920px" height="1080px" title="256" alt="sheet01">

<br>

###### Table ID는 url 링크에서 아래 사진처럼 드래그한 영역을 의미합니다.
<img src="/assets/img/post/unity/googleSheet02.png" width="1920px" height="1080px" title="256" alt="sheet02">

<br>

###### Sheet[] 배열에 들어갈 Sheet 정보들을 입력해줘야합니다. Sheet ID는 gid를 입력, name은 하단 툴바의 Sheet 이름을 입력

###### - ID
<img src="/assets/img/post/unity/googleSheet03.png" width="1920px" height="1080px" title="256" alt="sheet03">

###### - Name
<img src="/assets/img/post/unity/googleSheet04.png" width="1920px" height="1080px" title="256" alt="sheet04">

<br>
<br>

#### 4. 데이터 가져오기
###### 로드하고자 하는 테이블들을 다 입력했으면  "<span style="color:cyan">Get Data Sync</span>"버튼을 눌러줍니다.   
주의할 점은 스프레드 시트에 삭제된 테이블이 있으면 컴포넌트에도 반영을 해줘야 에러가 발생하지 않습니다.   
또한 Sheets의 변경점들이 생기면 그대로 유지하고 추가적인 시트만 추가해주는게 좋습니다.   
수정된 씬이나 프리팹은 SVN이나 협업툴로 동기화 해주는게 편함..
<img src="/assets/img/post/unity/googleSheet05.png" width="512px" height="512px" title="128" alt="sheet05">

###### 최종적으로 스프레드 시트에 있던 테이블을 csv 파일로 가져오기에 성공했습니다.   
다만 csv 파일은 너무 Raw Data 이기 때문에 따로 binary 파일로 파싱하여 보안처리를 해주는게 좋습니다.   
> (binary로 파싱해도 사실 뚫으려하면 다 뚫리는게 현실.. 그래도 아무에게나 다 뚫리는것을 방지 or 귀찮게 하기 위해 최소한의 안전장치는 해두자라는 마인드..)


<br>

#### 5. 스프레드 시트의 공유 설정은 꼭 "링크가 있는 모든 사용자"로 설정해줘야 합니다.. 안그러면 엑세스 거부되거나 오류가 발생합니다.
<img src="/assets/img/post/unity/googleSheet06.png" width="512px" height="512px" title="256" alt="sheet06">
> 이게 보안상 정말 단점이긴 한데.. 편하게 쓰려면 어쩔 수 없다..   
개발단계 or 업데이트 할 때만 공개 설정해두고 테이블을 로컬 작업환경에 받아오고 나서는 다시 제한한다거나 하는 조치를 취하면 되지싶네요