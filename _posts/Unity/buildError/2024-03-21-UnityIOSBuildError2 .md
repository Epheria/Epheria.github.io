---
title: Unity iOS TestFlight 업로드 에러 해결 - Asset validation failed (90206) Invalid Bundle. The bundle at .../Frameworks/UnityFramework.framework contains disallowed file 'Frameworks'.
date: 2024-03-21 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 자동화, iOS, BeeBuildPostProcessor, Microphone Usage Description]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 주요 에러 현상 분석

- Transporter 를 사용하여 TestFlight 에 업로드를 하려고 하니 다음과 같은 에러가 발생했다.

```
Asset validation failed (90206)
Invalid Bundle. The bundle at 'TOYVERSE.app/Frameworks/UnityFramework.framework' contains disallowed file 'Frameworks'.(ID: 54a900bb-b251-492a-bed7-ee556a02d857)
```

![Desktop View](/assets/img/post/unity/iosupload01.png){: : width="800" .normal }

- 참혹한 흔적들..

![Desktop View](/assets/img/post/unity/iosupload02.png){: : width="800" .normal }

<br>
<br>

## 해결 방법

- [stack overflow 스레드 확인](https://stackoverflow.com/questions/25777958/validation-error-invalid-bundle-the-bundle-at-contains-disallowed-file-fr?lq=1)
- 유니티 프로젝트를 빌드한 xcode 프로젝트의 xcworkspace 에 들어가서, Unity-iPhone app 과 UnityFrmaework 에 각각 Build Settings - embed 를 검색하면
- Always Embed Swift Standard Libraries 가 보일 것이다. 이게 Yes 가 되어 있다면 업로드에 실패할 가능성이 매우 높다.

![Desktop View](/assets/img/post/unity/iosupload03.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosupload04.png){: : width="800" .normal }

<br>

- 따라서 유니티 빌드 스크립트인 [PostProcessBuild](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/) 에서 후처리를 통해 이 둘을 비활성화 시켜주자.

```csharp
...
foreach (var targetGuid in new[] { mainTargetGuid, project.GetUnityFrameworkTargetGuid() })
{
  project.SetBuildProperty(targetGuid, "ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES", "No");

  project.SetBuildProperty(targetGuid, "LD_RUNPATH_SEARCH_PATHS", "$(inherited) /usr/lib/swift @executable_path/Frameworks");
  //project.AddBuildProperty(targetGuid, "LD_RUNPATH_SEARCH_PATHS", "/usr/lib/swift");
}

project.SetBuildProperty(mainTargetGuid, "ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES", "No");
...
```

<br>

- 다시 빌드하고 업로드하면 성공!

![Desktop View](/assets/img/post/unity/iosupload05.png){: : width="800" .normal }


<br>
<br>


<details>
<summary>빌드 후처리 전체 코드</summary>
<div markdown="1">

```csharp
class PBR : IPostprocessBuildWithReport
{
    public int callbackOrder { get { return 0; } }
    
    public void OnPostprocessBuild(BuildReport report)
    {
        if (report.summary.platform == BuildTarget.iOS)
        {
            Debug.Log("OnPostProceeBuild");
            string projectPath = report.summary.outputPath + "/Unity-iPhone.xcodeproj/project.pbxproj";
            var entitlementFilePath = "Entitlements.entitlements";
            var project = new PBXProject();

            project.ReadFromFile(projectPath);
            
            var manager = new ProjectCapabilityManager(projectPath, entitlementFilePath, null, project.GetUnityMainTargetGuid());
            manager.AddPushNotifications(true);
            manager.AddAssociatedDomains(new string[] { "applinks:nkmb.adj.st" });// Universal-Link대응/Universal-Link対応.
            manager.WriteToFile();

            var mainTargetGuid = project.GetUnityMainTargetGuid();
            project.SetBuildProperty(mainTargetGuid, "ENABLE_BITCODE", "NO");
            
            // Enterprise 에서만 임시로 추가해놓은 코드입니다.
            // Sign In With Apple Framework는 Enterprise에서 활성화가 되지 않기 때문에 Xcode 빌드에러 발생
            
            // Supported Destinations 에 아이패드 지원을 제외하는 코드
            // 1 은 아이폰을 의미.
            //project.SetBuildProperty(mainTargetGuid, "TARGETED_DEVICE_FAMILY", "1"); // 1 corresponds to iPhone

            project.RemoveFrameworkFromProject(mainTargetGuid, "SIGN_IN_WITH_APPLE");
            project.SetBuildProperty(mainTargetGuid, "CODE_SIGN_ENTITLEMENTS", entitlementFilePath);
            project.AddFrameworkToProject(mainTargetGuid, "UserNotifications.framework", false);

            foreach (var targetGuid in new[] { mainTargetGuid, project.GetUnityFrameworkTargetGuid() })
            {
                project.SetBuildProperty(targetGuid, "ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES", "No");

                project.SetBuildProperty(targetGuid, "LD_RUNPATH_SEARCH_PATHS", "$(inherited) /usr/lib/swift @executable_path/Frameworks");
                //project.AddBuildProperty(targetGuid, "LD_RUNPATH_SEARCH_PATHS", "/usr/lib/swift");
            }

            project.SetBuildProperty(mainTargetGuid, "ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES", "No");

#if DEV
            // // instrument test
            // // Enable 'get-task-allow' for Debug configuration
            // project.SetBuildProperty(target, "GCC_GENERATE_DEBUGGING_SYMBOLS", "YES");
            // project.SetBuildProperty(target, "ENABLE_TESTABILITY", "YES");
            //
            // project.WriteToFile(projectPath);
            //
            // // Fix the 'get-task-allow' error by enabling debugging in the entitlements file
            // string entitlementsContents = System.IO.File.ReadAllText("/Users/coconevbusan/Xcode_dev/Entitlements.entitlements");
            //
            // // Make sure the debugging entitlement is present
            // if (!entitlementsContents.Contains("<key>get-task-allow</key>"))
            // {
            //     // Add the entitlement for debugging
            //     entitlementsContents = entitlementsContents.Replace("</dict>", "<key>get-task-allow</key><true/></dict>");
            //     System.IO.File.WriteAllText("/Users/coconevbusan/Xcode_dev/Entitlements.entitlements", entitlementsContents);
            // }
#endif
        }
    }
}

 [PostProcessBuild(callbackOrder:999)]
    public static void OnPostprocessBuild(BuildTarget target, string pathToBuiltProject)
    {
#if UNITY_IPHONE
        if (target == BuildTarget.iOS)
        {
            var projectPath = PBXProject.GetPBXProjectPath(pathToBuiltProject);
            var project = new PBXProject();
            Debug.Log($"Post Process Build callback : {projectPath}");
            project.ReadFromString(File.ReadAllText(projectPath));

            // Unity2019.3以降のUnityFramework分離対応
            project.AddFrameworkToProject(project.GetUnityMainTargetGuid(), "UnityFramework.framework", false);

            // iOS14対応
            var frameworkTarget = project.GetUnityFrameworkTargetGuid();
            project.AddFrameworkToProject(frameworkTarget, "AppTrackingTransparency.framework", true);
            project.AddFrameworkToProject(frameworkTarget, "AdSupport.framework", true);

            string infoPlistPath = pathToBuiltProject + "/Info.plist";
            PlistDocument plistDoc = new PlistDocument();
            plistDoc.ReadFromFile(infoPlistPath);
            if (plistDoc.root != null)
            {
                plistDoc.root.SetBoolean("ITSAppUsesNonExemptEncryption", false);
            
                
                var locale = new string[] { "en", "ja" };
                var mainTargetGuid = project.GetUnityMainTargetGuid();
                var array = plistDoc.root.CreateArray("CFBundleLocalizations");
                foreach (var localization in locale)
                {
                    array.AddString(localization);
                } 
                
                plistDoc.root.SetString("NSUserTrackingUsageDescription", "Please allow permission to provide service and personalized marketing. It will be used only for the purpose of providing personalized advertising based on Apple’s policy.");

                // var entry = LocalizationSettings.StringDatabase.GetTableEntryAsync("LocalizeTable", "LZ_SRT_038");
                // if (entry.IsDone)
                // {
                //     var comment = entry.Result.Entry.GetMetadata<Comment>();
                //     var sharedEntry = entry.Result.Table.SharedData.GetEntry("LZ_SRT_038");
                //     var sharedComment = sharedEntry.Metadata.GetMetadata<Comment>();
                //     plistDoc.root.SetString("NSUserTrackingUsageDescription", sharedComment.CommentText);
                // }
                
                //plistDoc.root.SetString("NSUserTrackingUsageDescription", sharedComment);
                
                plistDoc.WriteToFile(projectPath);
                
                for (int i = 0; i < locale.Length; i++)
                {
                    var guid = project.AddFolderReference(Application.dataPath + string.Format("/Editor/iOS/Localization/{0}.lproj", locale[i]), string.Format("{0}.lproj", locale[i]), PBXSourceTree.Source);
                    project.AddFileToBuild(mainTargetGuid, guid);
                }
                // 日本語に設定
                //plistDoc.root.SetString("CFBundleDevelopmentRegion", "en");

                // iOS14 AppTrackingポップアップの表示用
                //var attMessage = StringManager.GetLZString("LZ_SRT_038") ?? "Localize is null";

                //var attMessage = "Please allow permission to provide service and personalized marketing. It will be used only for the purpose of providing personalized advertising based on Apple’s policy.";
                //var attMessage = "att tracking test";
                //var attMessage = "許可をした場合、本サービスで収集したお客様の情報をアプリの品質の向上に役立たせていただきます。" +
                //    "\n今後のサービス改善のため、トラッキングの設定をお願いします。" +
                //    "\n※トラッキングの設定は端末の設定からいつでも変更可能です。";
                //var info = new UnityEngine.Localization.Platform.iOS.AppInfo();
                //UnityEngine.Localization.Platform.iOS.AppInfo appInfo = info;
                //var attMessage = info.UserTrackingUsageDescription.ToString();
                //plistDoc.root.SetString("NSUserTrackingUsageDescription", attMessage);



                // Firebase利用のためBackgound mode設定が必要
                PlistElementArray backgroundModes;
                if (plistDoc.root.values.ContainsKey("UIBackgroundModes"))
                {
                    backgroundModes = plistDoc.root["UIBackgroundModes"].AsArray();
                }
                else
                {
                    backgroundModes = plistDoc.root.CreateArray("UIBackgroundModes");
                }
                backgroundModes.AddString("remote-notification");
                plistDoc.WriteToFile(infoPlistPath);
            }
            else
            {
                Debug.LogError("ERROR: Can't open " + infoPlistPath);
            }
            project.WriteToFile(projectPath);
        }
#endif
    }

```

</div>
</details>