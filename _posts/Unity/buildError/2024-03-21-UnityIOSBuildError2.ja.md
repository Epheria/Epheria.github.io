---
title: "Unity iOS TestFlightアップロードエラー解決 - Asset validation failed (90206) Invalid Bundle"
date: 2024-03-21 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 自動化, iOS, TestFlight, Asset validation failed, Invalid Bundle]
lang: ja
difficulty: intermediate
toc: true
---

## 主要エラー現象分析

- Transporterを使用してTestFlightにアップロードしようとしたところ、次のようなエラーが発生しました。

```
Asset validation failed (90206)
Invalid Bundle. The bundle at 'TOYVERSE.app/Frameworks/UnityFramework.framework' contains disallowed file 'Frameworks'.(ID: 54a900bb-b251-492a-bed7-ee556a02d857)
```

![Desktop View](/assets/img/post/unity/iosupload01.png){: : width="800" .normal }

- 惨憺たる痕跡...

![Desktop View](/assets/img/post/unity/iosupload02.png){: : width="800" .normal }

<br>
<br>

## 解決方法

- [stack overflowのスレッドを確認](https://stackoverflow.com/questions/25777958/validation-error-invalid-bundle-the-bundle-at-contains-disallowed-file-fr?lq=1)
- UnityプロジェクトをビルドしたXcodeプロジェクトの `xcworkspace` に入って、`Unity-iPhone app` と `UnityFramework` それぞれの **Build Settings** で `embed` を検索すると
- **Always Embed Swift Standard Libraries** が見えるはずです。これが **Yes** になっている場合、アップロードに失敗する可能性が非常に高いです。

![Desktop View](/assets/img/post/unity/iosupload03.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosupload04.png){: : width="800" .normal }

<br>

- したがって、Unityビルドスクリプトである [PostProcessBuild](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/) で後処理を通じてこの2つを無効化しましょう。

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

- 再度ビルドしてアップロードすれば成功！

![Desktop View](/assets/img/post/unity/iosupload05.png){: : width="800" .normal }


<br>
<br>


<details>
<summary>ビルド後処理の全コード</summary>
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
            manager.AddAssociatedDomains(new string[] { "applinks:nkmb.adj.st" });// Universal-Link対応。
            manager.WriteToFile();

            var mainTargetGuid = project.GetUnityMainTargetGuid();
            project.SetBuildProperty(mainTargetGuid, "ENABLE_BITCODE", "NO");
            
            // Enterprise でのみ一時的に追加しておいたコードです。
            // Sign In With Apple FrameworkはEnterpriseで有効化されないためXcodeビルドエラー発生
            
            // Supported Destinations にiPadサポートを除外するコード
            // 1 はiPhoneを意味する。
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
            // string entitlementsContents = System.IO.File.ReadAllText("/Users/YOUR_USERNAME/Xcode_dev/Entitlements.entitlements");
            //
            // // Make sure the debugging entitlement is present
            // if (!entitlementsContents.Contains("<key>get-task-allow</key>"))
            // {
            //     // Add the entitlement for debugging
            //     entitlementsContents = entitlementsContents.Replace("</dict>", "<key>get-task-allow</key><true/></dict>");
            //     System.IO.File.WriteAllText("/Users/YOUR_USERNAME/Xcode_dev/Entitlements.entitlements", entitlementsContents);
            // }
#endif
        }
    }
}
```

</div>
</details>