---
title: Unity 빌드 자동화 - build pipeline & addressable
date: 2023-08-28 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, 자동화, Addressable, BuildPipeline, fastlane, Jenkins]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차
- [1. Unity Build Pipeline 에 대해](#서론)
- [2. AOS 빌드](#1-aos-빌드)
- [3. iOS 빌드](#2-ios-빌드)
- [4. Addressable 빌드](#3-addressable-빌드)

---

## 서론
- 유니티 프로젝트를 빌드할 때 batchmode로 CI/CD 툴(Jenkins, fastlane)을 사용하여 백그라운드에서 유니티를 실행시켜 빌드를 하는 방법을 의미한다.
- 앞의 fastlane 문서에서 설명한 FastFile 에서 사용중인 unity plugin 으로 execute_method 에서 실행하는 static 함수를 일반적으로 사용한다.
- arguments 즉 인자들을 빌드 스크립트로 따로 받아오려고 한다면 fastlane은 사용하기 힘들것같다.. Jenkins에서 shell script로 직접적으로 실행하는 방법을 사용해야함.

<br>

## 빌드 스크립트 구성
- BuildScript.cs 스크립트를 Unity 프로젝트 내부의 Assets - Editor 폴더 내부로 위치시킨다.
- Unity Build Pipeline용 클래스와 execute method로 실행시킬 함수들은 "static" 이어야한다.

```csharp
public static class ProjectBuilder
{
    public static void BuildAndroid()
    {

    }
}
```

<br>

#### 1. AOS 빌드
- .apk 파일인지 .aab 파일인지 구분해야한다. Development 용은 .apk , Google Console Play에 내부/공개 테스트 혹은 Release용은 .aab
- keystore 파일을 잘 생성하고 잘 보관하자. keystore 파일이 꼬이거나 없으면 유니티 프로젝트 빌드단에서 터지거나 Google Play Console에 업로드할 때 인증문제가 발생할 수 있다.
    > keystore 생성 관련 링크는 [>>이쪽으로<<](https://learnandcreate.tistory.com/1583)
- 생성한 keystore 는 프로젝트 내부에 폴더를 만들어서 SVN으로 관리해주는게 좋다. (project settings 경로지정 때문에)


#### aos execute method 전체 코드
- BuildPlayerOptions 구조체를 만들고 PlayerSettings와 EditorUserBuildSettings를 설정하고 BuildPipeline.BuildPlayer를 호출한다.
- System.Environment.GetCommandLineArgs()를 통해 인자들을 받아오는 부분이 있는데, 이는 Jenkins의 Shell script를 통해 인자 변수들을 받아오는 부분이다.   
하지만 fastlane으로 실행하면 log가 안보이거나 실행이 안되므로 fastlane의 fastfile로 빌드를 할 수 없다.
- 따라서 Jenkins의 인자를 받아오고 싶다면 Jenkins Shell script를 통해 batchmode를 실행시켜줘야한다.

```csharp
public static void BuildAndroid()
{
   // Jenkins 에서 세팅한 Arguments들을 받아오는 부분. 빌드 시 build_num 설정을 위해 추가했다. 자세한 내용은 Jenkins 문서에서 설명..
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

   // BuildPlayerOptions 설정하는 부분. 빌드 세팅에서 추가한 Scene들(이 Scene들은 어드레서블로 빼놓지 않았기 때문에 빌드에 포함됨)
   // 원격 빌드 시 지정한 경로인 locationPathName, 빌드 타겟 android, buildAppBundle은 .aab로 추출한것인지? 등이다.
   BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions();
   buildPlayerOptions.scenes = FindEnabledEditorScenes();
   buildPlayerOptions.locationPathName = "/Users/coconevbusan/Build/toyverse_apk/toyverse.aab";
   buildPlayerOptions.target = BuildTarget.Android;
   EditorUserBuildSettings.buildAppBundle = true;

   // PlayerSettings 설정하는 부분.
   // buildNum을 넣어주고 커스텀 keystore 사용여부, 생성한 keystore와 keyalias 이름과 비밀번호를 입력해준다.
   PlayerSettings.Android.bundleVersionCode = buildNum;
   PlayerSettings.Android.useCustomKeystore = true;
   PlayerSettings.Android.keystoreName = "Keystore/toyverse.keystore";
   PlayerSettings.Android.keystorePass = "toyverse";
   PlayerSettings.Android.keyaliasName = "com.coconev.toyverse";
   PlayerSettings.Android.keyaliasPass = "toyverse";

   // 항상 세팅이 잘되어 있는지 로그를 찍어보자.. 의외로 간단한 곳이 잘못된건데 엉뚱한 곳을 수정하는 경우가 많았음..
   Debug.Log("Build Player Started hhh");
   Debug.Log("PlayerSettings hhh keystoreName : " + PlayerSettings.Android.keystoreName);
   Debug.Log("PlayerSettings hhh keyaliasName : " + PlayerSettings.Android.keyaliasName);
   Debug.Log("PlayerSettings hhh keystorePass : " + PlayerSettings.Android.keystorePass);
   Debug.Log("PlayerSettings hhh keyaliasPass : " + PlayerSettings.Android.keyaliasPass);

   // 마지막으로 BuildPipeline.BuildPlayer 를 호출해준다.
   // 여기서 백그라운드를 통해 batchmode로 실제로 빌드가 실행된다. 자세한 로그는 fastlane cmd 나 Jenkins log에서 확인이 가능하다. (에러 터지면 얘네들로 찾아야함)
   var report = BuildPipeline.BuildPlayer(buildPlayerOptions)

   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded) Debug.Log("Build Success");
   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Failed) Debug.Log("Build Failed");
}

// Enable 처리된 Scene들 가져오는 부분
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

#### 2. iOS 빌드
- iOS 빌드 과정을 간략하게 설명하자면
1. Unity 프로젝트 빌드 -> Xcode로 xcworkspace (cocoapods 설치 필요) 및 xcodeproj 로 추출됨
2. Xcode 빌드 -> .ipa 파일로 추출

 <span style="color:red">AOS와 다르게 두 번 빌드해줘야한다..</span>

- 위와 같은 이유 때문에 iOS 빌드는 빌드 후처리가 무조건적으로 필요하다.
- 후처리를 위해 IPostprocessBuildWithReport 인터페이스를 상속시킨 PBR 클래스를 만들어준다.
- PBXProject 클래스와 ProjectCapabilityManager 와 같은 클래스를 생성하여 필요한 후처리를 진행해준다.   
- 특히 ENABLE_BITCODE 세팅, Entitlements 생성 및 적용, .framework 적용, Capability 자동화 등을 적용하기 위해 삽질했던 것을 생각하면 아직도 속이 쓰리다..

#### ios execute method 전체 코드

```csharp
public static void BuildIOS()
{
   // 이 부분까지는 AOS 와 똑같다.
   BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions();
   buildPlayerOptions.scenes = FindEnabledEditorScenes();
   buildPlayerOptions.locationPathName = "/Users/coconevbusan/Xcode";
   buildPlayerOptions.target = BuildTarget.iOS;

   var report = BuildPipeline.BuildPlayer(buildPlayerOptions);

   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded) Debug.Log("Build Success");
   if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Failed) Debug.Log("Build Failed");


// BuildPlayer 빌드가 끝난 후 빌드 후처리 실행하는 부분
#if UNITY_IPHONE
   PBR pbr = new PBR();
   pbr.OnPostprocessBuild(report);
#endif
}

#if UNITY_IPHONE // PBXProject 같은 클래스는 android build target 시 에러가 발생하므로.. 전처리는 필수로 해주자
class PBR : IPostprocessBuildWithReport
{
   // 빌드 후처리 함수
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

- projectPath는 빌드한 Xcode 경로로 들어가서 .xcodeproj 를 우클릭 - 패키지 내용 보기를 누르면 project.pbxproj가 존재한다. 그곳을 경로로 찍어준다.
- Entitlements는 Apple Developer에서 생성한 Identifier에 Push Notification, In App Purchase 등의 옵션을 체크 하고 Xcode 의 Signing&Capabilities 에 Capability 로 자동으로 추가하기 위해 만든 파일이다.
- ProjectCapabilityManager 를 통해 Entitlements의 경로를 지정하고 필요한 Capability를 Add 해준 뒤 Entitlements 파일을 생성해준다.
- PBXProject 클래스의 SetBuildProperty를 통해 entitlement와 framework를 세팅한다. 이는 firebase 기반의 푸쉬알림을 위해 추가했다.

<br>

## 참조 링크
[Entitlement 두 가지 세팅 방법](https://forum.unity.com/threads/how-to-add-entitlement-entry.1146173/)

<br>

#### 3. Addressable 빌드
- Addressable 빌드 역시 Unity 프로젝트를 fastlane 으로 빌드하는 방식과 똑같이 사용한다. 

```ruby
  desc "Build Addressable"
  lane :addrressable do
    unity(
      build_target: "iOS",
      execute_method: "ProjectBuilder.BuildAddressable_IOS",
      unity_path: "/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
      project_path: "/Users/coconevbusan/.jenkins/workspace/ios_fastlane"
    )
  end
```
- unity plugin을 사용하며 ProjectBuilder 클래스의 BuildAddressable_AOS / IOS static 함수를 백그라운드로 실행한다.

- Addressable 빌드를 하기 전 Addressable Profile 에 대해 확인해보자.
- Addressable Profile 은 모바일 개발 환경에서는 크게 3가지로 분류된다.
- Default (빌드에 Including), Remote_aos (android 용 Remote), Remote_ios (ios 용 Remote)

![Desktop View](/assets/img/post/unity/pipeline01.png){: .normal }

<br>

![Desktop View](/assets/img/post/unity/pipeline02.png){: .normal }

- Manage Profile 로 들어가면 Profile을 추가하거나 Variable 변수를 추가할 수 있다.
- 이 변수가 참 중요한데 BuildPath, LoadPath url 을 조합할 때 

```
# []
```
- 이 대괄호를 사용하면 무조건 최우선적으로 저 대괄호 내부의 변수를 판단하고 Variable로 추가한 변수들을 조합한다.
- 자 이제 이 프로필들의 이름들을 어드레서블 빌드 스크립트에서 사용해야한다.

#### Addressable 빌드 전체 코드

[Addressable Build Script 참조 링크](https://docs.unity3d.com/Packages/com.unity.addressables@1.20/manual/BuildPlayerContent.html)

```csharp
#region Build Addressable
    public static string build_script = "Assets/AddressableAssetsData/DataBuilders/BuildScriptPackedMode.asset";
    public static string profile_aos_name = "Remote_aos"; // Addressable Groups 에 있는 3가지 프로필 네임들을 세팅해줘야한다.
    public static string profile_ios_name = "Remote_ios"; // 빠른 빌드 및 테스트가 필요하다면 Default 를 사용해야 할 것이며
    public static string profile_default = "Default";     // 패치 시스템을 체크하고 싶다면 Remote를 써야하기 때문이다.
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

- 주의!!

```csharp
   settings.activeProfileId = settings.profileSettings.GetProfileId(profile_default);
```

- 어드레서블 빌드 스크립트에서 GetProfileId를 가져올 때 사용하는 프로필 네임과 어드레서블 그룹에 설정된 프로필이 같은지 꼭! 체크하고
- 프로필이 Default 면 fastest, 프로필이 Remote 면 Using Exists 로 설정해야한다!!

![Desktop View](/assets/img/post/unity/pipeline03.png){: .normal }
![Desktop View](/assets/img/post/unity/pipeline04.png){: .normal }

<br>

- Remote로 설정하고 빌드를 했다면, 프로필에서 설정한 BuildPath ( 여기서는 프로젝트 하위의 ServerData 폴더 내부 ) 에 정상적으로 카탈로그 json 과 hash 파일 그리고 어드레서블 번들 파일들이 생성이될 것이다.

- ServerData 하위에 생성된 Android, iOS 어드레서블 번들 및 카탈로그 폴더
![Desktop View](/assets/img/post/unity/pipeline05.png){: .normal }

- 생성된 번들 파일들과 카탈로그 파일들을 확인할 수 있다. 이것들을 이제 LoadPath를 설정하고 AWS S3에 올리면 패치 시스템이 구현할 수 있다.
![Desktop View](/assets/img/post/unity/pipeline06.png){: .normal }
