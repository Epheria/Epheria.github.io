---
title: Unity ビルド自動化 - build pipeline & addressable
date: 2023-08-28 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, build, automation, addressable, buildpipeline, fastlane, jenkins]
difficulty: intermediate
lang: ja
toc: true
---

## 目次
- [1. Unity Build Pipeline について](#introduction)
- [2. AOS ビルド](#1-aos-ビルド)
- [3. iOS ビルド](#2-ios-ビルド)
- [4. Addressable ビルド](#3-addressable-ビルド)

---

## はじめに {#introduction}
- Unity プロジェクトをビルドする際に、batchmode で CI/CD ツール (Jenkins, fastlane) を使ってバックグラウンド実行する方法を指す。
- 前回の fastlane 記事で説明した FastFile の unity plugin では、`execute_method` で static 関数を呼ぶ形が一般的。
- 引数をビルドスクリプトで柔軟に受けたい場合、fastlane は制約があるため Jenkins shell 実行の方が向く場合がある。

<br>

## ビルドスクリプト構成
- `BuildScript.cs` は Unity プロジェクトの `Assets/Editor` に配置。
- Unity Build Pipeline 用クラスと execute method の関数は `static` 必須。

```csharp
public static class ProjectBuilder
{
    public static void BuildAndroid()
    {

    }
}
```

<br>

#### 1. AOS ビルド
- `.apk` か `.aab` かを区別する。開発向けは `.apk`、Google Play の内部/公開テストやリリースは `.aab`。
- keystore は生成/保管を厳密に。紛失・破損すると Unity 側ビルド失敗や Play Console 認証問題が発生する。
    > keystore 参考: [>>こちら<<](https://learnandcreate.tistory.com/1583)
- 生成した keystore はプロジェクト内フォルダで管理し、SVN 管理するのが安全。


#### aos execute method 全体コード
- `BuildPlayerOptions` を作成し、`PlayerSettings` と `EditorUserBuildSettings` を設定して `BuildPipeline.BuildPlayer` を呼ぶ。
- `System.Environment.GetCommandLineArgs()` で引数を受ける処理は Jenkins shell から変数を渡す想定。
- fastlane 実行ではログ確認や挙動が不安定なことがあるため、引数運用したい場合は Jenkins batchmode 実行が確実。

```csharp
public static void BuildAndroid()
{
   // Jenkins arguments. Added for build_num assignment.
   string[] args = System.Environment.GetCommandLineArgs();
   int buildNum = 0;
   foreach (string a in args)
   {
      if (a.StartsWith("build_num"))
      {
         var arr = a.Split(":");
         if (arr.Length == 2)
         {
            int.TryParse(arr[1], out buildNum);
         }
      }
   }

   Debug.Log("hhh args : " + string.Join(",", args));
   Debug.Log("Build Started hhh");

   // BuildPlayerOptions configuration
   BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions();
   buildPlayerOptions.scenes = FindEnabledEditorScenes();
   buildPlayerOptions.locationPathName = "/Users/YOUR_USERNAME/Build/toyverse_apk/toyverse.aab";
   buildPlayerOptions.target = BuildTarget.Android;
   EditorUserBuildSettings.buildAppBundle = true;

   // PlayerSettings configuration
   PlayerSettings.Android.bundleVersionCode = buildNum;
   PlayerSettings.Android.useCustomKeystore = true;
   PlayerSettings.Android.keystoreName = "Keystore/toyverse.keystore";
   PlayerSettings.Android.keystorePass = "toyverse";
   PlayerSettings.Android.keyaliasName = "com.coconev.toyverse";
   PlayerSettings.Android.keyaliasPass = "toyverse";

   Debug.Log("Build Player Started hhh");
   Debug.Log("PlayerSettings hhh keystoreName : " + PlayerSettings.Android.keystoreName);
   Debug.Log("PlayerSettings hhh keyaliasName : " + PlayerSettings.Android.keyaliasName);
   Debug.Log("PlayerSettings hhh keystorePass : " + PlayerSettings.Android.keystorePass);
   Debug.Log("PlayerSettings hhh keyaliasPass : " + PlayerSettings.Android.keyaliasPass);

   var report = BuildPipeline.BuildPlayer(buildPlayerOptions)

   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded) Debug.Log("Build Success");
   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Failed) Debug.Log("Build Failed");
}

private static string[] FindEnabledEditorScenes()
{
   List<string> EditorScenes = new List<string>();

   foreach (EditorBuildSettingsScene scene in EditorBuildSettings.scenes)
   {
      if (!scene.enabled) continue;
      EditorScenes.Add(scene.path);
   }

   return EditorScenes.ToArray();
}
```

<br>

#### 2. iOS ビルド
- iOS ビルド手順は簡潔に言うと:
1. Unity プロジェクトビルド -> `xcworkspace` (cocoapods 必須) と `xcodeproj` 出力
2. Xcode ビルド -> `.ipa` 出力

 <span style="color:red">AOS と違って実質 2 回ビルドが必要。</span>

- この理由で iOS はビルド後処理がほぼ必須。
- `IPostprocessBuildWithReport` を実装した PBR クラスを作る。
- `PBXProject` と `ProjectCapabilityManager` 等で後処理を適用する。  
- `ENABLE_BITCODE`、Entitlements 生成、framework 追加、Capability 自動化は特にハマりやすい。

#### ios execute method 全体コード

```csharp
public static void BuildIOS()
{
   // same pattern as AOS up to here
   BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions();
   buildPlayerOptions.scenes = FindEnabledEditorScenes();
   buildPlayerOptions.locationPathName = "/Users/YOUR_USERNAME/Xcode";
   buildPlayerOptions.target = BuildTarget.iOS;

   var report = BuildPipeline.BuildPlayer(buildPlayerOptions);

   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded) Debug.Log("Build Success");
   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Failed) Debug.Log("Build Failed");


// post process after BuildPlayer
#if UNITY_IPHONE
   PBR pbr = new PBR();
   pbr.OnPostprocessBuild(report);
#endif
}

#if UNITY_IPHONE // required to avoid Android target compile errors
class PBR : IPostprocessBuildWithReport
{
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
         manager.WriteToFile();

         var mainTargetGuid = project.GetUnityMainTargetGuid();
         project.SetBuildProperty(mainTargetGuid, "ENABLE_BITCODE", "NO");

         project.SetBuildProperty(mainTargetGuid, "CODE_SIGN_ENTITLEMENTS", entitlementFilePath);
         project.AddFrameworkToProject(mainTargetGuid, "UserNotifications.framework", false);
         project.WriteToFile(projectPath);
      }
   }
}
#endif
```

- `projectPath`: ビルド出力の `.xcodeproj` を右クリック -> Show Package Contents -> `project.pbxproj` を指定。
- `Entitlements` は Apple Developer 側設定 (Push Notification / IAP など) を Xcode Signing&Capabilities に反映するためのファイル。
- `ProjectCapabilityManager` で entitlements パス設定と capability 追加を行う。
- `PBXProject.SetBuildProperty` で entitlement / framework を設定 (Firebase Push 用)。

<br>

## 参考リンク
[Entitlement 2 種の設定方法](https://forum.unity.com/threads/how-to-add-entitlement-entry.1146173/)

<br>

#### 3. Addressable ビルド
- Addressable ビルドも Unity プロジェクトを fastlane から呼ぶ方式で同様に運用する。

```ruby
  desc "Build Addressable"
  lane :addrressable do
    unity(
      build_target: "iOS",
      execute_method: "ProjectBuilder.BuildAddressable_IOS",
      unity_path: "/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
      project_path: "/Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane"
    )
  end
```
- unity plugin から `ProjectBuilder.BuildAddressable_AOS / IOS` static 関数をバックグラウンド実行する。

- Addressable ビルド前に Addressable Profile を確認。
- モバイルでは主に 3 種で運用:
- `Default` (ビルド同梱), `Remote_aos` (Android remote), `Remote_ios` (iOS remote)

![Desktop View](/assets/img/post/unity/pipeline01.png){: .normal }

<br>

![Desktop View](/assets/img/post/unity/pipeline02.png){: .normal }

- Manage Profile で Profile / Variable を追加できる。
- BuildPath / LoadPath URL 組み立てでこの変数が重要。

```
# []
```
- `[]` を使うと、まず括弧内変数を優先解決し、その後 Variable 変数と組み合わせる。
- これら Profile 名をビルドスクリプト内で使う。

#### Addressable ビルド全体コード

[Addressable Build Script docs](https://docs.unity3d.com/Packages/com.unity.addressables@1.20/manual/BuildPlayerContent.html)

```csharp
#region Build Addressable
    public static string build_script = "Assets/AddressableAssetsData/DataBuilders/BuildScriptPackedMode.asset";
    public static string profile_aos_name = "Remote_aos"; // must match profile names in Addressable Groups
    public static string profile_ios_name = "Remote_ios";
    public static string profile_default = "Default";
    public static void BuildAddressable_AOS()
    {
        Debug.Log("Addressable Build Started haha");
        AddressableAssetSettings settings = AddressableAssetSettingsDefaultObject.Settings;

        settings.activeProfileId = settings.profileSettings.GetProfileId(profile_default);

        IDataBuilder builder = AssetDatabase.LoadAssetAtPath<ScriptableObject>(build_script) as IDataBuilder;
        Debug.Log("Addressable Load AssetPath haha");

        int index = settings.ActivePlayerDataBuilderIndex = settings.DataBuilders.IndexOf((ScriptableObject)builder);
        Debug.Log($"Addressable index number : {index}");

        if (index > 0)
        {
            settings.ActivePlayerDataBuilderIndex = index;
        }
        else if (AddressableAssetSettingsDefaultObject.Settings.AddDataBuilder(builder))
        {
            settings.ActivePlayerDataBuilderIndex = AddressableAssetSettingsDefaultObject.Settings.DataBuilders.Count - 1;
        }
        else
        {
            Debug.LogWarning($"{builder} could not be found");
        }

        Debug.Log($"Addressable Build Content Started!! hh");
        AddressableAssetSettings.BuildPlayerContent(out AddressablesPlayerBuildResult result);

        bool success = string.IsNullOrEmpty(result.Error);

        if (!success)
        {
            Debug.LogError("Addressable build error encountered : " + result.Error);
        }
        else
        {
            Debug.Log("Addressable Build Success!!!");
        }
    }

    public static void BuildAddressable_IOS()
    {
        Debug.Log("Addressable Build Started haha");
        AddressableAssetSettings settings = AddressableAssetSettingsDefaultObject.Settings;

        settings.activeProfileId = settings.profileSettings.GetProfileId(profile_default);

        IDataBuilder builder = AssetDatabase.LoadAssetAtPath<ScriptableObject>(build_script) as IDataBuilder;
        Debug.Log("Addressable Load AssetPath haha");

        int index = settings.ActivePlayerDataBuilderIndex = settings.DataBuilders.IndexOf((ScriptableObject)builder);
        Debug.Log($"Addressable index number : {index}");

        if (index > 0)
        {
            settings.ActivePlayerDataBuilderIndex = index;
        }
        else if (AddressableAssetSettingsDefaultObject.Settings.AddDataBuilder(builder))
        {
            settings.ActivePlayerDataBuilderIndex = AddressableAssetSettingsDefaultObject.Settings.DataBuilders.Count - 1;
        }
        else
        {
            Debug.LogWarning($"{builder} could not be found");
        }

        Debug.Log($"Addressable Build Content Started!! hh");
        AddressableAssetSettings.BuildPlayerContent(out AddressablesPlayerBuildResult result);

        bool success = string.IsNullOrEmpty(result.Error);

        if (!success)
        {
            Debug.LogError("Addressable build error encountered : " + result.Error);
        }
        else
        {
            Debug.Log("Addressable Build Success!!!");
        }
    }
```

<br>

- 注意:

```csharp
   settings.activeProfileId = settings.profileSettings.GetProfileId(profile_default);
```

- `GetProfileId` に渡すプロファイル名が Addressable Groups の設定と一致しているか必ず確認。
- `Default` は fastest、`Remote` は Use Existing Build を設定すること。

![Desktop View](/assets/img/post/unity/pipeline03.png){: .normal }
![Desktop View](/assets/img/post/unity/pipeline04.png){: .normal }

<br>

- Remote 設定でビルドすると、Profile の BuildPath (ここでは `ServerData`) に catalog json/hash と bundle が生成される。

- `ServerData` 配下に生成された Android / iOS Addressable bundle + catalog
![Desktop View](/assets/img/post/unity/pipeline05.png){: .normal }

- 生成物を確認し、LoadPath 設定後に AWS S3 へアップロードすればパッチ配信構成を作れる。

![Desktop View](/assets/img/post/unity/pipeline06.png){: .normal }
