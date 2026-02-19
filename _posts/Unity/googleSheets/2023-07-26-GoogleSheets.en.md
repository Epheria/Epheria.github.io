---
title: Integrating Google Sheet with Unity
date: 2023-07-26 18:47:00 +/-TTTT
categories: [Unity, GoogleSheet]
tags: [unity, googlesheet, datatable]
difficulty: intermediate
lang: en
toc: true
---
---
## Table of Contents
- [1. DataSheet Integration Code](#1-datasheet-integration-code)
- [2. DataSheet Editor Code](#2-datasheet-editor-code)
- [3. How to Find Table ID and Sheet gid](#3-how-to-find-table-id-and-sheet-gid)

---

<br>
<br>

## Google Sheet Sync Code

<br>
<br>

#### 1. DataSheet Integration Code

###### You can use UnityWebRequest to download Google Sheet data by gid and save it as a csv file.
######  * You can build this as a UnityEditor tool and use it that way.  
Additional note: put each sheet gid into the `Sheets[]` array to fetch multiple csv files at once.

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

#### 2. DataSheet Editor Code
``` csharp
    /// <summary>
    /// SpreadSheetSync custom Editor UI
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

#### 3. How to Find Table ID and Sheet gid
###### You can also add this to the top toolbar as a custom menu and use it there. In many companies, table updates happen in longer cycles, so for convenience I usually placed it in the scene and used it as a prefab.  
In short: in the Google Sheet Sync component in Inspector, enter your Google Spreadsheet Table ID, then input each sheet's name and gid in the `Sheets` array.
<img src="/assets/img/post/unity/googleSheet01.png" width="1920px" height="1080px" title="256" alt="sheet01">

<br>

###### Table ID means the highlighted part in the URL, as shown below.
<img src="/assets/img/post/unity/googleSheet02.png" width="1920px" height="1080px" title="256" alt="sheet02">

<br>

###### You need to enter each Sheet info in the `Sheet[]` array. For Sheet ID, input `gid`; for Name, use the sheet name shown at the bottom tab.

###### - ID
<img src="/assets/img/post/unity/googleSheet03.png" width="1920px" height="1080px" title="256" alt="sheet03">

###### - Name
<img src="/assets/img/post/unity/googleSheet04.png" width="1920px" height="1080px" title="256" alt="sheet04">

<br>
<br>

#### 4. Fetching Data
###### After entering all tables you want to load, press the "<span style="color:cyan">Get Data Sync</span>" button.  
Important: if a table was deleted in the spreadsheet, reflect that deletion in the component as well to avoid errors.  
Also, if there are changes in Sheets, keep existing entries and only append additional sheets when possible.  
For modified scenes/prefabs, syncing through SVN or your collaboration tool is convenient.
<img src="/assets/img/post/unity/googleSheet05.png" width="512px" height="512px" title="128" alt="sheet05">

###### Finally, the tables in the spreadsheet were successfully imported as csv files.  
However, csv is very raw data, so it is better to parse to binary and add some security handling.  
> (Even if parsed to binary, if someone really wants to break it they usually can. Still, it is worth having minimum safeguards to prevent trivial access or raise the effort.)


<br>

#### 5. Spreadsheet sharing must be set to "Anyone with the link". Otherwise you may get access denied or request errors.
<img src="/assets/img/post/unity/googleSheet06.png" width="512px" height="512px" title="256" alt="sheet06">
> This is definitely a security downside, but for convenience there's often no choice.  
A practical approach is enabling public access only during development/update sync, downloading tables to local workspace, then restricting access again.
