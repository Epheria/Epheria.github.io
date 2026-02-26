---
title: "Unity iOS TestFlight Upload Error Fix - Asset validation failed (90206) Invalid Bundle"
date: 2024-03-21 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Automation, iOS, TestFlight, Asset validation failed, Invalid Bundle]
lang: en
difficulty: intermediate
toc: true
---

## Error Analysis

- When attempting to upload to TestFlight using Transporter, the following error occurred:

```
Asset validation failed (90206)
Invalid Bundle. The bundle at 'TOYVERSE.app/Frameworks/UnityFramework.framework' contains disallowed file 'Frameworks'.(ID: 54a900bb-b251-492a-bed7-ee556a02d857)
```

![Desktop View](/assets/img/post/unity/iosupload01.png){: : width="800" .normal }

- Traces of disaster...

![Desktop View](/assets/img/post/unity/iosupload02.png){: : width="800" .normal }

<br>
<br>

## Solution

- [Checked StackOverflow thread](https://stackoverflow.com/questions/25777958/validation-error-invalid-bundle-the-bundle-at-contains-disallowed-file-fr?lq=1)
- Go to the `xcworkspace` of the Xcode project built from Unity.
- Search for `embed` in **Build Settings** for both `Unity-iPhone app` and `UnityFramework`.
- You will see **Always Embed Swift Standard Libraries**. If this is set to **Yes**, the upload is highly likely to fail.

![Desktop View](/assets/img/post/unity/iosupload03.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosupload04.png){: : width="800" .normal }

<br>

- Therefore, disable these two in the Unity build script [PostProcessBuild](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/) via post-processing.

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

- Build again and upload, and it succeeds!

![Desktop View](/assets/img/post/unity/iosupload05.png){: : width="800" .normal }


<br>
<br>


<details>
<summary>Full Build Post-processing Code</summary>
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
            manager.AddAssociatedDomains(new string[] { "applinks:nkmb.adj.st" });// Universal-Link Support.
            manager.WriteToFile();

            var mainTargetGuid = project.GetUnityMainTargetGuid();
            project.SetBuildProperty(mainTargetGuid, "ENABLE_BITCODE", "NO");
            
            // Code temporarily added only for Enterprise.
            // Xcode build error occurs because Sign In With Apple Framework is not activated in Enterprise
            
            // Code to exclude iPad support in Supported Destinations
            // 1 means iPhone.
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

            // UnityFramework separation support since Unity 2019.3
            project.AddFrameworkToProject(project.GetUnityMainTargetGuid(), "UnityFramework.framework", false);

            // iOS 14 support
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

                plistDoc.root.SetString("NSUserTrackingUsageDescription", "Please allow permission to provide service and personalized marketing. It will be used only for the purpose of providing personalized advertising based on Apple's policy.");

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
                // Set to Japanese
                //plistDoc.root.SetString("CFBundleDevelopmentRegion", "en");

                // For displaying iOS 14 AppTracking popup
                //var attMessage = StringManager.GetLZString("LZ_SRT_038") ?? "Localize is null";

                //var attMessage = "Please allow permission to provide service and personalized marketing. It will be used only for the purpose of providing personalized advertising based on Apple's policy.";
                //var attMessage = "att tracking test";
                //var attMessage = "If permitted, the information collected from you in this service will be used to improve the quality of the app." +
                //    "\nPlease configure tracking settings for future service improvement." +
                //    "\n*Tracking settings can be changed at any time from your device settings.";
                //var info = new UnityEngine.Localization.Platform.iOS.AppInfo();
                //UnityEngine.Localization.Platform.iOS.AppInfo appInfo = info;
                //var attMessage = info.UserTrackingUsageDescription.ToString();
                //plistDoc.root.SetString("NSUserTrackingUsageDescription", attMessage);



                // Background mode configuration required for Firebase
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