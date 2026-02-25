---
title: "Unity Android Build Error Fix - DexArchiveMergerException & MultiDex"
date: 2024-02-26 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Automation, Android, DexArchiveMergerException, multiDexEnabled, mergeDexRelease, gradle build failed, Minify]
lang: en
difficulty: intermediate
toc: true
---

## Identifying the Cause

- Upgraded Unity version from 2022.3.4f1 to 2022.3.19f1.
- Updated Build Machine (Mac Mini) to MacOS Sonoma 14.3.1 and Xcode 15.2.
- An unknown error occurred during remote build for DEV Android via Jenkins.

<br>
<br>

## First Failure Cause and Solution: Enabling MultiDex

```
User
ERROR:/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/unityLibrary/build/.transforms/f5f2117adcaee1eb1097391e7bb3025e/transformed/classes/classes.dex: D8: Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: ...
com.android.builder.dexing.DexArchiveMergerException: Error while merging dex archives: 
Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: ...
```

- It seems the cause was a duplicate class definition: `com.google.firebase.MessagingUnityPlayerActivity`. Specifically, classes defined more than once cause conflicts in two dex archives.
- To resolve this, enabling **MultiDex** was required. Similar issues have been reported in Unity forums and discussions.
- Although some threads date back to 2014 or 2019, I decided to proceed with enabling the MultiDex option as I needed to try every possible solution to fix this build.

**[Reference: StackOverflow Answer](https://stackoverflow.com/questions/31141210/how-to-enable-multi-dex-option-for-android-in-unity3d/55960144#55960144)**

**[1. Unity Forum MultiDex](https://forum.unity.com/threads/multidex-support-on-android.325429/)**

**[2. Unity Discussion MultiDex](https://discussions.unity.com/t/too-many-method-references-when-i-export-android-build/120436/1)**

- According to the forums and discussions, setting `multiDexEnabled true` resolves the `DexArchiveMergerException`.
- I found the `mainTemplate.gradle` file inside the `Plugin - Android` folder and added the following code:

```gradle
android {
    ...

    defaultConfig {
        ...
        multiDexEnabled true
    }

    ...
}
```

![Desktop View](/assets/img/post/unity/unityaosbuilderror_01.png){: : width="500" .normal }

- Note: In the image below, `DISABLED` is appended to the filename, suggesting it might not be included in the build or is disabled. It's a mystery why it affects the build...

![Desktop View](/assets/img/post/unity/unityaosbuilderror_02.png){: : width="200" .normal }

#### Result: Enabling MultiDex resolved this error. However, another error occurred...

<br>
<br>

## Second Failure Cause and Solution: Execution failed for task ':launcher:mergeDexRelease' & gradle build failed

```
FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':launcher:mergeDexRelease'.
> A failure occurred while executing com.android.build.gradle.internal.tasks.DexMergingTaskDelegate
   > There was a failure while executing work items
      > A failure occurred while executing com.android.build.gradle.internal.tasks.DexMergingWorkAction
         > com.android.builder.dexing.DexArchiveMergerException: Error while merging dex archives: 
           Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: 
```

- The above log appeared during the Jenkins build. I suspect this error occurred due to enabling MultiDex.

**[Reference: app:mergeDexRelease Error](https://github.com/facebook/react-native/issues/33670)**

**[Reference: Gradle Build Failed Fix Blog](https://devparklibrary.tistory.com/20)**

- The referenced blog was also outdated, so the settings environment was quite different.
- ~~There is a checkbox in **ProjectSettings - Android - Publishing Settings - Minify - Release**. Enabling this checkbox solves it.~~
- However, be warned that like "Strip Engine Code," this might exclude specific binary files from the build. No one knows what issues that might cause...

- **Update 2024.3.6: It says it deletes or excludes Java Code binary files, and it actually did... Adjust was not included in the build, so I had to disable this option again.**

![Desktop View](/assets/img/post/unity/unityaosbuilderror_03.png){: : width="400" .normal }

- Warning text...

![Desktop View](/assets/img/post/unity/unityaosbuilderror_04.png){: : width="500" .normal }

#### Result: Enabling that option in Project Settings solved it!! But... yet another error occurred... (This part was due to internal project code issues)

<br>
<br>

## Third Failure Cause and Solution: Native Crash Reporting (Caused by Internal Project Code)

```
Filename: Assets/Editor/Build/ShaderCleanup.cs Line: 68


=================================================================
	Native Crash Reporting
=================================================================
Got a segv while executing native code. This usually indicates
a fatal error in the mono runtime or one of the native libraries 
used by your application.
=================================================================

=================================================================
	Native stacktrace:
=================================================================
```

- This code removes unnecessary shaders during build post-processing... Strangely, it had no issues before but started crashing now. `ImportAsset` seems to be the problem.
- Since it was a Native Crash, I couldn't see detailed error logs... It is presumed that it tried to remove a non-existent shader.

```csharp
public void OnPreprocessBuild(BuildReport report)
{
    // Logic to identify and disable unused shaders or assets

    // Example: Find and disable all unused shaders
    DeactivateUnusedShaders();
}

 private void DeactivateUnusedShaders()
{
  ...

     AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(shaderPath), ImportAssetOptions.ForceUpdate);

  ...
}
```

- Solved by commenting out this code and proceeding with the build...
